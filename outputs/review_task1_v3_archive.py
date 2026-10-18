"""Verify a closed v3 evidence archive and audit saved decisions offline."""
import argparse
from collections import Counter
import csv
import hashlib
from io import BytesIO
import json
from pathlib import Path, PurePosixPath
import stat
import zipfile

from curation_agent_v3.integrity import inventory, verify_inputs


EXPECTED_SHA256 = "f3c68276c985082729b194ef6cedf6f864b99a4993eb9237798beef87d5a8792"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def verified_payloads(archive, expected_sha):
    raw = Path(archive).read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected_sha.lower():
        raise ValueError("Archive SHA256 mismatch")
    with zipfile.ZipFile(BytesIO(raw)) as bundle:
        entries = bundle.infolist()
        names = [entry.filename for entry in entries]
        if len(entries) > 10000 or sum(entry.file_size for entry in entries) > 512 * 1024**2:
            raise ValueError("Archive exceeds this audit's size limit")
        if len(set(name.casefold() for name in names)) != len(names):
            raise ValueError("Duplicate or case-colliding archive member")
        for entry in entries:
            name = entry.filename
            relative = PurePosixPath(name)
            if (entry.is_dir() or relative.is_absolute() or ".." in relative.parts
                    or ":" in name or "\\" in name or relative.as_posix() != name
                    or not (name.startswith("run/") or name.startswith("review/")
                            or name == "EXPORT_MANIFEST.json")):
                raise ValueError("Unsafe archive path: " + name)
            if stat.S_IFMT(entry.external_attr >> 16) not in (0, stat.S_IFREG):
                raise ValueError("Non-regular archive member: " + name)
        manifest = json.loads(bundle.read("EXPORT_MANIFEST.json"))
        if manifest.get("format") != "task1_v3_closeout_v1":
            raise ValueError("Unexpected export manifest format")
        if set(names) != set(manifest["files"]) | {"EXPORT_MANIFEST.json"}:
            raise ValueError("Manifest/member set mismatch")
        payloads = {name: bundle.read(name) for name in names}
        for name, wanted in manifest["files"].items():
            if hashlib.sha256(payloads[name]).hexdigest() != wanted:
                raise ValueError("Member hash mismatch: " + name)
    return payloads, {"archive_sha256": actual, "archive_bytes": len(raw),
                      "archive_members": len(entries), "verified_manifest_files": len(manifest["files"]),
                      "uncompressed_bytes": sum(len(value) for value in payloads.values())}


def extract_new(payloads, destination):
    destination = Path(destination).resolve()
    if destination.exists():
        raise ValueError("Extraction destination already exists; preserve earlier evidence")
    destination.mkdir(parents=True)
    for name, value in payloads.items():
        path = destination.joinpath(*PurePosixPath(name).parts)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)
    return destination


def model_context(receipt):
    message = next(item for item in reversed(receipt["request"]["messages"]) if item["role"] == "user")
    return json.loads(message["content"])


def analyze(destination, review_dir, verification):
    root = Path(destination) / "run"
    review_dir = Path(review_dir)
    if review_dir.exists():
        raise ValueError("Review output directory already exists")
    before = inventory(root)
    state = read(root / "state.json")
    checked, _ = verify_inputs(root, state)
    local_sources = Path(__file__).parent / "curation_agent_v3"
    for name, wanted in state["code_sha256"].items():
        if hashlib.sha256((local_sources / name).read_bytes()).hexdigest() != wanted:
            raise ValueError("Installed v3 source differs from the archived source: " + name)
    ledger = read(root / "revision.json")
    boundary = state["revision"]["inherited_llm_attempts"]
    parent = read(root / "history_v21/state.json")
    keys = ("prompt_tokens", "completion_tokens", "total_tokens")
    total_usage = {key: 0 for key in keys}
    new_usage = dict(total_usage)
    contexts, receipts = {}, {}
    for number in range(1, state["llm_attempts"] + 1):
        receipt = read(root / "llm" / f"{number:04d}.json")
        if not receipt.get("usage"):
            raise ValueError("A model receipt has no returned usage: " + str(number))
        for key in keys:
            amount = int(receipt["usage"].get(key) or 0)
            total_usage[key] += amount
            if number > boundary:
                new_usage[key] += amount
        if number > boundary:
            receipts[number] = receipt
            contexts[number] = model_context(receipt)
    if total_usage != state["usage"]:
        raise ValueError("Model receipt totals do not match state")
    if {key: total_usage[key] - new_usage[key] for key in keys} != ledger["inherited_usage"]:
        raise ValueError("Inherited receipt totals do not match the revision ledger")
    events = [event for event in state["events"]
              if event.get("kind") == "tool_action" and event["llm_attempt"] > boundary]
    if len({event["llm_attempt"] for event in events}) != len(events):
        raise ValueError("More than one scientific action for a model attempt")
    citations, rows = [], []
    for event in events:
        decision = event["decision"]
        number = event["llm_attempt"]
        context = contexts[number]
        active = (context.get("active_assay_progress") or {}).get("assay") or {}
        required = set()
        if decision["action"] == "decide_assay" and active.get("assay_id") == decision["arguments"]["assay_id"]:
            required.add(active.get("metadata_evidence_id"))
            required.add((active.get("curation") or {}).get("evidence_id"))
            required.add((active.get("source_assessment") or {}).get("evidence_id"))
            required.discard(None)
            citations.append({"attempt": number, "required_ids": sorted(required),
                "supplied_ids": decision["arguments"]["evidence_ids"],
                "missing_ids": sorted(required - set(decision["arguments"]["evidence_ids"]))})
        rows.append({"attempt": number, "action": decision["action"],
            "assay_id": decision["arguments"].get("assay_id"), "status": event["status"],
            "basis": decision["arguments"].get("basis"), "error": event.get("error"),
            "available_suggested_tools": json.dumps((context.get("active_assay_progress") or {}).get("suggested_tools"), ensure_ascii=False),
            "reason": decision["reason"]})
    http = state["requests"][state["revision"]["inherited_http_attempts"]:]
    http_resources = Counter(request["url"].split("/api/data/", 1)[-1].split("?", 1)[0] for request in http)
    window_entry = state["evidence"]["E0097"]
    window = read(root / window_entry["path"])
    if not window["complete"] or len(window["records"]) != window["total"]:
        raise ValueError("The p300 target window is not complete")
    p300_counts = Counter(record["assay_chembl_id"] for record in window["records"])
    summary = {
        "archive_verification": verification, "input_files_unchanged": len(before),
        "declared_hash_checks": len(checked), "local_v3_source_matches_archived_source": True,
        "stored_status": state["status"],
        "effective_closure_reason": "llm_budget_exhausted" if state["llm_attempts"] >= state["protocol"]["maximum_llm_attempts"] else state["status"],
        "lifetime_returned_usage": total_usage, "revision_returned_usage": new_usage,
        "revision_llm_attempts": state["llm_attempts"] - boundary,
        "revision_http_attempts": len(http), "revision_http_resources": dict(http_resources),
        "revision_receipt_statuses": dict(Counter(receipt["status"] for receipt in receipts.values())),
        "revision_requested_models": dict(Counter(receipt["request"]["model"] for receipt in receipts.values())),
        "revision_tool_statuses": dict(Counter(event["status"] for event in events)),
        "revision_tool_actions": dict(Counter(event["decision"]["action"] for event in events)),
        "revision_tool_error_types": dict(Counter(event.get("error_type") for event in events if event["status"] == "tool_error")),
        "new_assay_metadata_ids": sorted(set(state["assays"]) - set(parent["assays"])),
        "new_curated_assay_ids": sorted(aid for aid, item in state["assays"].items()
            if item.get("curation") and not parent["assays"].get(aid, {}).get("curation")),
        "new_target_profile_ids": sorted(set(state["profiles"]) - set(parent["profiles"])),
        "new_assay_count_ids": sorted(set(state["assay_counts"]) - set(parent["assay_counts"])),
        "contexts_with_unprofiled_data_rich_targets": sum(bool(context.get("unprofiled_data_rich_targets")) for context in contexts.values()),
        "p300_complete_window_records": len(window["records"]),
        "CHEMBL5629827_exact_record_count_in_complete_window": p300_counts["CHEMBL5629827"],
        "p300_assays_with_at_least_250_raw_records": {aid: count for aid, count in p300_counts.items() if count >= 250},
        "review_shortlist": state["shortlist"], "campaign_ready": False,
        "limits": "Offline inspection only; no new model calls, data retrieval, curation, source full-text review or campaign. No counterfactual performance claim.",
    }
    remote_summary = read(Path(destination) / "review/summary.json")
    for key in ("lifetime_returned_usage", "revision_returned_usage", "revision_llm_attempts",
                "revision_http_attempts", "revision_receipt_statuses", "revision_tool_statuses", "revision_tool_actions"):
        if remote_summary[key] != summary[key]:
            raise ValueError("Local audit and remote summary disagree: " + key)
    if inventory(root) != before:
        raise ValueError("Original evidence changed during analysis")
    review_dir.mkdir(parents=True)
    save(review_dir / "verification_and_findings.json", summary)
    save(review_dir / "decision_citation_checks.json", citations)
    save(review_dir / "original_input_hashes.json", before)
    with (review_dir / "new_decisions.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--review-dir", required=True, type=Path)
    args = parser.parse_args()
    payloads, verification = verified_payloads(args.archive, EXPECTED_SHA256)
    destination = extract_new(payloads, args.destination)
    summary = analyze(destination, args.review_dir, verification)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
