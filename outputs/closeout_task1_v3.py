"""Audit and archive one budget-closed Task1 v3 run without changing it."""
import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import uuid
import zipfile

from curation_agent_v3.integrity import inventory, verify_inputs


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@contextmanager
def read_guard(root):
    path = root / ".writer.lock"
    if not path.exists():
        yield
        return
    with path.open("rb") as handle:
        if os.name == "posix":
            import fcntl
            fcntl.flock(handle, fcntl.LOCK_SH | fcntl.LOCK_NB)
        else:
            import msvcrt
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBRLCK, 1)
        try:
            yield
        finally:
            if os.name == "posix":
                fcntl.flock(handle, fcntl.LOCK_UN)
            else:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def closeout(run_dir, output_root):
    root = Path(run_dir).resolve(strict=True)
    output_root = Path(output_root).resolve()
    if output_root.is_relative_to(root) or root.is_relative_to(output_root):
        raise ValueError("Use a separate sibling output directory outside the input run")
    with read_guard(root):
        before = inventory(root)
        state = read(root / "state.json")
        if state.get("schema") != "task1_agent_v3.0" or not state.get("revision"):
            raise ValueError("Expected a versioned Task1 v3 revision")
        if state.get("pending_action") is not None:
            raise ValueError("Pending action exists; do not archive as a closed experiment")
        protocol = state["protocol"]
        used = state["llm_attempts"]
        http_used = len(state["requests"])
        if used >= protocol["maximum_llm_attempts"]:
            effective = "llm_budget_exhausted"
        elif http_used >= protocol["maximum_http_requests"]:
            effective = "http_budget_exhausted"
        elif state["status"] == "finished":
            effective = "agent_finished"
        else:
            raise ValueError("Run has not finished or exhausted a declared budget")
        checked, _ = verify_inputs(root, state)
        revision = read(root / "revision.json")
        boundary = state["revision"]["inherited_llm_attempts"]
        keys = ("prompt_tokens", "completion_tokens", "total_tokens")
        usage = {key: 0 for key in keys}
        new_usage = dict(usage)
        missing_usage = []
        receipt_statuses = Counter()
        for number in range(1, used + 1):
            receipt = read(root / "llm" / f"{number:04d}.json")
            returned = receipt.get("usage")
            if not returned:
                missing_usage.append(number)
            if number > boundary:
                receipt_statuses[receipt.get("status", "unknown")] += 1
            for key in keys:
                amount = int((returned or {}).get(key) or 0)
                usage[key] += amount
                if number > boundary:
                    new_usage[key] += amount
        if usage != state["usage"]:
            raise ValueError("Receipt usage totals disagree with state")
        inherited = {key: usage[key] - new_usage[key] for key in keys}
        if inherited != revision["inherited_usage"]:
            raise ValueError("Inherited receipt usage disagrees with revision ledger")
        events = [event for event in state["events"]
                  if event.get("kind") == "tool_action" and event["llm_attempt"] > boundary]
        assays = []
        for aid, item in sorted(state["assays"].items()):
            curation = item.get("curation") or {}
            budget = curation.get("budget") or {}
            source = item.get("source_assessment") or {}
            assays.append({
                "assay_id": aid, "metadata": item.get("summary"),
                "acquisition": item.get("acquisition"),
                "usable_compounds": budget.get("provisional_pool_size"),
                "hits": budget.get("hit_support_count"),
                "nonhits": budget.get("nonhit_support_count"),
                "qualification": curation.get("qualification"),
                "source_assessment": source, "decision": item.get("decision"),
            })
        summary = {
            "source_run": str(root), "stored_status": state["status"],
            "effective_closure_reason": effective,
            "state_status_rewritten": False,
            "lifetime_llm_attempts": used, "lifetime_http_attempts": http_used,
            "revision_llm_attempts": used - boundary,
            "revision_http_attempts": http_used - state["revision"]["inherited_http_attempts"],
            "lifetime_returned_usage": usage, "revision_returned_usage": new_usage,
            "attempts_without_returned_usage": missing_usage,
            "revision_receipt_statuses": dict(receipt_statuses),
            "revision_tool_statuses": dict(Counter(event["status"] for event in events)),
            "revision_tool_actions": dict(Counter(event["decision"]["action"] for event in events)),
            "revision_successful_curation_actions": sum(event["decision"]["action"] == "curate_assay"
                and event["status"] == "success" for event in events),
            "review_shortlist": state["shortlist"], "campaign_ready": False,
            "remaining_llm_attempts": max(0, protocol["maximum_llm_attempts"] - used),
            "remaining_http_attempts": max(0, protocol["maximum_http_requests"] - http_used),
            "units_note": "HTTP attempts include failures; known assay IDs are not activity records. Returned tokens are not cash charges.",
            "scientific_note": "Tool success and source assessment states do not independently validate scientific rationales. No new source review or campaign was performed by this closeout.",
        }
        output_root.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out = output_root / ("task1_v3_closeout_" + stamp + "_" + uuid.uuid4().hex[:8])
        out.mkdir()
        save(out / "summary.json", summary)
        save(out / "new_tool_events.json", events)
        save(out / "assays.json", assays)
        save(out / "integrity.json", {"hash_checks": len(checked),
            "unique_declared_files_checked": len(set(checked)), "input_files_sha256": before})
        report_files = ["summary.json", "new_tool_events.json", "assays.json", "integrity.json"]
        manifest = {"format": "task1_v3_closeout_v1", "files": {
            **{"run/" + name: value for name, value in before.items()},
            **{"review/" + name: digest(out / name) for name in report_files},
        }}
        save(out / "EXPORT_MANIFEST.json", manifest)
        archive = out / "task1_v3_evidence.zip"
        with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as bundle:
            for name in before:
                bundle.write(root / name, "run/" + name)
            for name in report_files:
                bundle.write(out / name, "review/" + name)
            bundle.write(out / "EXPORT_MANIFEST.json", "EXPORT_MANIFEST.json")
        with zipfile.ZipFile(archive) as bundle:
            if set(bundle.namelist()) != set(manifest["files"]) | {"EXPORT_MANIFEST.json"}:
                raise ValueError("Archive member mismatch")
            for name, wanted in manifest["files"].items():
                if hashlib.sha256(bundle.read(name)).hexdigest() != wanted:
                    raise ValueError("Archive hash mismatch: " + name)
        if inventory(root) != before:
            raise ValueError("Input run changed during closeout; archive is not validated")
        receipt = {"status": "verified_offline_closeout", "run_files_unchanged": len(before),
            "archive": str(archive), "archive_sha256": digest(archive),
            "archive_bytes": archive.stat().st_size, "output_dir": str(out), "summary": summary}
        save(out / "archive_receipt.json", receipt)
        return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(closeout(args.run_dir, args.output_root), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
