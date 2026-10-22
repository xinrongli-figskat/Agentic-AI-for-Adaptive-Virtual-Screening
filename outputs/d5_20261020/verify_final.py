"""Final D5 evidence verification; no campaign or model calls."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from outputs.d5_20261020.e_menu.run_extended import BASE, PRIVATE_OUT, ROOT, sha, utc, validate_sources


def main():
    validate_sources()
    report = BASE / "d5_report.md"
    result = BASE / "e_menu_results.json"
    assert report.exists() and result.exists()
    data = json.loads(result.read_text(encoding="utf-8"))
    assert data["runs_verified"] == 760
    assert data["glm_calls"] == data["http_attempts"] == 160
    assert data["initialization_mismatches"] == []
    paths = sorted((PRIVATE_OUT / "runs").rglob("run.json"))
    pending = sorted((PRIVATE_OUT / "runs").rglob("pending.json"))
    failures = sorted((PRIVATE_OUT / "runs").rglob("failure_events.json"))
    assert len(paths) == 760 and not pending and not failures
    for path in paths:
        run = json.loads(path.read_text(encoding="utf-8"))
        assert run["complete"] and run["queried_count"] == 50
        assert len({key for step in run["trajectory"] for key in step["selection"]}) == 50
        if run["arm"] == "glm_extended":
            assert run["pool"] == "tnap"
            for step in run["trajectory"][1:]:
                call = step.get("glm_call")
                if call:
                    assert call["request_id"] and call["api_attempt_log"]
                    assert not any(key in call["public_summary"] for key in
                                   ("compound_key", "standardized_smiles", "oracle_labels", "private_labels"))
    gate_check = subprocess.run([sys.executable, "-B", "-m", "unittest", "test_gates"],
                                cwd=BASE / "d_task1_auto", capture_output=True, text=True)
    menu_check = subprocess.run([sys.executable, "-B", "-m", "unittest",
                                 "outputs.d5_20261020.e_menu.test_expanded"],
                                cwd=ROOT, capture_output=True, text=True)
    assert gate_check.returncode == 0, gate_check.stdout + gate_check.stderr
    assert menu_check.returncode == 0, menu_check.stdout + menu_check.stderr
    receipt = {"utc": utc(), "status": "pass", "no_model_or_oracle_calls": True,
               "source_hash_lock_passed": True,
               "public_report_sha256": sha(report), "results_sha256": sha(result),
               "run_count": len(paths), "pending_count": len(pending),
               "failure_event_files": len(failures), "glm_calls": data["glm_calls"],
               "http_attempts": data["http_attempts"],
               "tests": [gate_check.stderr.strip(), menu_check.stderr.strip()],
               "postrun_boundary_sha256": sha(BASE / "e_menu_postrun_boundary_check.json"),
               "private_run_file_hashes": {str(path.relative_to(ROOT)): sha(path) for path in paths}}
    target = BASE / "d5_final_verification.json"
    target.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "pass", "runs": len(paths),
                      "tests": [gate_check.stderr.strip(), menu_check.stderr.strip()],
                      "receipt_sha256": sha(target)}))


if __name__ == "__main__":
    main()
