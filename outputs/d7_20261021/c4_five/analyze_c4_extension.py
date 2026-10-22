"""Run the unchanged locked C4 analysis under the authorized 164-call guard."""

import argparse
import json
from pathlib import Path

import analyze_c4
import extend_c4_one_decision as extension
import run_c4 as c4


HERE = Path(__file__).resolve().parent
LOCK = HERE / "C4_EXTENSION_ANALYSIS_LOCK.json"
ORIGINAL_ANALYSIS_LOCK = HERE / "C4_ANALYSIS_CODE_LOCK.json"


def create_lock():
    if LOCK.exists():
        raise FileExistsError("Extension analysis already locked")
    extension.verify_extension()
    result = json.loads(extension.RESULT.read_text(encoding="utf-8"))
    if result["status"] != "complete" or c4.physical_count() != 161:
        raise RuntimeError("Extension has not completed with the expected single extra call")
    if not json.loads(c4.run_path(2, 19).read_text(encoding="utf-8"))["complete"]:
        raise RuntimeError("Final campaign incomplete")
    lock = {"status": "locked_before_complete_C4_analysis", "utc": c4.utc(),
            "original_analysis_code_lock_sha256": c4.file_sha(ORIGINAL_ANALYSIS_LOCK),
            "original_analysis_code_sha256": c4.file_sha(HERE / "analyze_c4.py"),
            "extension_analysis_launcher_sha256": c4.file_sha(Path(__file__)),
            "extension_lock_sha256": c4.file_sha(extension.LOCK),
            "extension_result_sha256": c4.file_sha(extension.RESULT),
            "authorized_physical_ceiling": 164,
            "observed_physical_calls": 161}
    c4.save(LOCK, lock)
    return lock


def analyze():
    extension.verify_extension()
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    expected = {"original_analysis_code_lock_sha256": c4.file_sha(ORIGINAL_ANALYSIS_LOCK),
                "original_analysis_code_sha256": c4.file_sha(HERE / "analyze_c4.py"),
                "extension_analysis_launcher_sha256": c4.file_sha(Path(__file__)),
                "extension_lock_sha256": c4.file_sha(extension.LOCK),
                "extension_result_sha256": c4.file_sha(extension.RESULT)}
    if lock["status"] != "locked_before_complete_C4_analysis" or any(
        lock[key] != value for key, value in expected.items()
    ) or lock["authorized_physical_ceiling"] != 164:
        raise RuntimeError("Extension analysis lock mismatch")
    analyze_c4.MAX_PHYSICAL = 164  # Analysis guard only; original code/lock stay unchanged.
    result = analyze_c4.analyze()
    if result["status"] != "complete" or result["physical_provider_attempts"] != 161:
        raise RuntimeError("Full matrix analysis did not complete")
    return {"status": "complete", "campaigns": result["campaigns"],
            "physical_calls": result["physical_provider_attempts"],
            "primary_mean_difference": result["comparisons"]["bandit_thompson"]["paired_mean_difference_H50"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lock", "execute"))
    args = parser.parse_args()
    value = create_lock() if args.mode == "lock" else analyze()
    print(json.dumps(value, ensure_ascii=False, indent=2))
