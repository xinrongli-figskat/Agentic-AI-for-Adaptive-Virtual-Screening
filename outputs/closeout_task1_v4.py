"""Read-only Task 1 v4 closeout: verify, summarize and archive the exhausted run."""
from __future__ import annotations

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

from curation_agent_v3.integrity import verify_inputs
from curation_agent_v4.run import inventory, load_v4_engine


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path: Path, value) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@contextmanager
def read_guard(root: Path):
    lock = root / ".writer.lock"
    if not lock.exists():
        yield
        return
    with lock.open("rb") as handle:
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


def _source_run_summary(root: Path, before: dict[str, str], state: dict) -> dict:
    if state.get("protocol", {}).get("version") != "task1_agent_v4.0":
        raise ValueError("Expected Task 1 v4 protocol")
    if state.get("pending_action") is not None:
        raise ValueError("Pending action exists; closeout requires a stable checkpoint")
    if state.get("shortlist"):
        raise ValueError("Nonempty shortlist requires a separate scientific review")
    ledger = read(root / "v4_experiment.json")
    experiment = state.get("v4_experiment") or {}
    if digest(root / "v4_experiment.json") != experiment.get("ledger_sha256"):
        raise ValueError("v4 ledger hash mismatch")
    old_llm = int(experiment["inherited_llm_attempts"])
    old_http = int(experiment["inherited_http_requests"])
    if old_llm != ledger["inherited_llm_attempts"] or old_http != ledger["inherited_http_requests"]:
        raise ValueError("Inherited budget ledger mismatch")
    used = int(state["llm_attempts"])
    http_used = len(state["requests"])
    protocol = state["protocol"]
    if used >= protocol["maximum_llm_attempts"]:
        closure = "llm_budget_exhausted"
    elif http_used >= protocol["maximum_http_requests"]:
        closure = "http_budget_exhausted"
    elif state["status"] == "finished":
        closure = "agent_finished"
    else:
        raise ValueError("Run has not finished or exhausted a declared budget")

    keys = ("prompt_tokens", "completion_tokens", "total_tokens")
    usage = {key: 0 for key in keys}
    new_usage = dict(usage)
    missing_usage = []
    receipt_statuses = Counter()
    for number in range(1, used + 1):
        receipt = read(root / "llm" / f"{number:04d}.json")
        returned = receipt.get("usage") or {}
        if not returned:
            missing_usage.append(number)
        if number > old_llm:
            receipt_statuses[receipt.get("status", "unknown")] += 1
        for key in keys:
            amount = int(returned.get(key) or 0)
            usage[key] += amount
            if number > old_llm:
                new_usage[key] += amount
    if usage != state["usage"]:
        raise ValueError("Receipt usage totals disagree with state")
    inherited = {key: usage[key] - new_usage[key] for key in keys}
    if inherited != ledger["inherited_usage"]:
        raise ValueError("Inherited receipt usage disagrees with v4 ledger")

    events = [event for event in state["events"] if event.get("kind") == "tool_action"
              and event.get("llm_attempt", 0) > old_llm]
    queue = []
    for assay_id, item in sorted(state.get("assays", {}).items()):
        if item.get("summary") and not item.get("decision"):
            queue.append({
                "assay_id": assay_id,
                "target_id": item["summary"].get("target_id"),
                "metadata_evidence_id": item.get("metadata"),
                "acquisition_evidence_id": (item.get("acquisition") or {}).get("evidence_id"),
                "curation_completed": bool(item.get("curation")),
                "source_status": (item.get("source_assessment") or {}).get("status"),
                "next_status": "unresolved_not_approved",
            })
    s1 = state.get("assays", {}).get("CHEMBL5734042") or {}
    if not s1.get("summary") or s1.get("decision") is not None:
        raise ValueError("Expected inspected, undecided S1PR1 assay at v4 closeout")
    profile = state.get("profiles", {}).get("CHEMBL4333") or {}
    preview = next((row for row in profile.get("top_assays_in_window", [])
                    if row.get("assay_chembl_id") == "CHEMBL5734042"), None)
    if preview is None:
        raise ValueError("S1PR1 preview missing from target profile")

    summary = {
        "source_run": str(root), "stored_status": state["status"],
        "effective_closure_reason": closure, "state_status_rewritten": False,
        "lifetime_llm_attempts": used, "new_v4_llm_attempts": used - old_llm,
        "lifetime_http_attempts": http_used, "new_v4_http_attempts": http_used - old_http,
        "lifetime_returned_usage": usage, "new_v4_returned_usage": new_usage,
        "attempts_without_returned_usage": missing_usage,
        "new_v4_receipt_statuses": dict(receipt_statuses),
        "new_v4_tool_statuses": dict(Counter(event.get("status") for event in events)),
        "new_v4_tool_actions": dict(Counter((event.get("decision") or {}).get("action") for event in events)),
        "review_shortlist": state["shortlist"], "campaign_ready": False,
        "pending_assays": queue,
        "s1pr1_preview_source_id_support": preview,
        "s1pr1_scientific_status": "metadata_inspected; source and endpoint unresolved; no qualification decision",
        "run_file_count": len(before),
        "units_note": "Preview counts are source-ID supports, not curated compound labels; returned tokens are not charges.",
        "scientific_note": "This closeout performs no new ChEMBL request, GLM call, source review, curation or campaign.",
    }
    return {"summary": summary, "new_tool_events": events}


def closeout(run_dir: Path, output_root: Path, check_only: bool = False) -> dict:
    root = Path(run_dir).resolve(strict=True)
    destination = Path(output_root).resolve()
    if destination.is_relative_to(root) or root.is_relative_to(destination):
        raise ValueError("Output root must be a separate sibling, outside the input run")
    with read_guard(root):
        for path in root.rglob("*"):
            if path.is_symlink():
                raise ValueError("Symlink in run: " + str(path))
        before = inventory(root)
        state = read(root / "state.json")
        # This loader checks v4 snapshots, inherited parent files and v3 evidence.
        load_v4_engine(root)
        checked, _ = verify_inputs(root, state)
        material = _source_run_summary(root, before, state)
        if check_only:
            return {"status": "ready_to_archive_no_files_written",
                    "run_files_verified": len(before), "evidence_references_checked": len(checked),
                    "summary": material["summary"]}
        destination.mkdir(parents=True, exist_ok=True)
        out = destination / ("task1_v4_closeout_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                             + "_" + uuid.uuid4().hex[:8])
        out.mkdir()
        report_files = ("summary.json", "new_tool_events.json", "integrity.json")
        save(out / "summary.json", material["summary"])
        save(out / "new_tool_events.json", material["new_tool_events"])
        save(out / "integrity.json", {"input_file_sha256": before,
             "evidence_references_checked": len(checked),
             "unique_evidence_files_checked": len(set(checked))})
        manifest = {"format": "task1_v4_closeout_v1", "files": {
            **{"run/" + name: value for name, value in before.items()},
            **{"review/" + name: digest(out / name) for name in report_files},
        }}
        save(out / "EXPORT_MANIFEST.json", manifest)
        archive = out / "task1_v4_evidence.zip"
        with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as bundle:
            for name in before:
                bundle.write(root / name, "run/" + name)
            for name in report_files:
                bundle.write(out / name, "review/" + name)
            bundle.write(out / "EXPORT_MANIFEST.json", "EXPORT_MANIFEST.json")
        with zipfile.ZipFile(archive) as bundle:
            if set(bundle.namelist()) != set(manifest["files"]) | {"EXPORT_MANIFEST.json"}:
                raise ValueError("Archive member mismatch")
            for name, expected in manifest["files"].items():
                if hashlib.sha256(bundle.read(name)).hexdigest() != expected:
                    raise ValueError("Archive member hash mismatch: " + name)
        if inventory(root) != before:
            raise ValueError("Input run changed during archive; reject the export")
        receipt = {"status": "verified_offline_closeout", "run_files_unchanged": len(before),
                   "archive": str(archive), "archive_sha256": digest(archive),
                   "archive_bytes": archive.stat().st_size, "output_dir": str(out),
                   "summary": material["summary"]}
        save(out / "archive_receipt.json", receipt)
        return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    print(json.dumps(closeout(args.run_dir, args.output_root, args.check_only), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
