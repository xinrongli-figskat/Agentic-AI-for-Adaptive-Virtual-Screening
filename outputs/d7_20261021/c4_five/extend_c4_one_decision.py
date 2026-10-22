"""Additive, bounded continuation of C4's sole unfinished decision."""

import argparse
import json
from pathlib import Path

import run_c4 as c4


HERE = Path(__file__).resolve().parent
AUDIT = HERE / "C4_BUDGET_HALT_AUDIT.json"
PROTOCOL = HERE / "C4_EXTENSION_PROTOCOL_v1.md"
LOCK = HERE / "C4_EXTENSION_LOCK_v1.json"
RESULT = HERE / "C4_EXTENSION_RESULT.json"
EXTRA_CAP = 164


def base_checks():
    c4.verify_lock()  # Still uses the original 160-call lock.
    audit = json.loads(AUDIT.read_text(encoding="utf-8"))
    if (audit["status"] != "physical_budget_exhausted_before_full_matrix"
        or audit["physical_provider_calls"] != 160
        or audit["complete_campaigns"] != 39
        or audit["partial_campaigns"] != [{"repeat": 2, "seed": 19,
            "queries": 40, "completed_feedback_batches": 3}]):
        raise RuntimeError("Base C4 checkpoint is not the authorized state")
    saved = json.loads(c4.run_path(2, 19).read_text(encoding="utf-8"))
    if (saved["lock_sha256"] != c4.file_sha(c4.lock_path())
        or saved["queried_count"] not in (40, 50)):
        raise RuntimeError("Pending run differs from original C4 lock")
    for index in range(161, c4.physical_count() + 1):
        receipt = json.loads((c4.PRIVATE / "http" / f"http_{index:04d}.json").read_text(encoding="utf-8"))
        if receipt["index"] != index or receipt["repeat"] != 2 or receipt["seed"] != 19:
            raise RuntimeError("Extension call outside the sole authorized campaign")
    if not 160 <= c4.physical_count() <= EXTRA_CAP:
        raise RuntimeError("Physical attempt count outside extension allowance")
    return audit


def create_lock():
    if LOCK.exists():
        raise FileExistsError("Extension already locked")
    if c4.physical_count() != 160:
        raise RuntimeError("Extension must be locked before any added call")
    base_checks()
    value = {"status": "locked_before_extension_provider_calls", "utc": c4.utc(),
             "scope": "TNAP/S_strong/bit/rep2/seed19/final_decision_only",
             "original_physical_calls": 160, "extended_physical_ceiling": EXTRA_CAP,
             "original_lock_sha256": c4.file_sha(c4.lock_path()),
             "budget_halt_audit_sha256": c4.file_sha(AUDIT),
             "extension_protocol_sha256": c4.file_sha(PROTOCOL),
             "extension_runner_sha256": c4.file_sha(Path(__file__))}
    c4.save(LOCK, value)
    return value


def verify_extension():
    base_checks()
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    expected = {"original_lock_sha256": c4.file_sha(c4.lock_path()),
                "budget_halt_audit_sha256": c4.file_sha(AUDIT),
                "extension_protocol_sha256": c4.file_sha(PROTOCOL),
                "extension_runner_sha256": c4.file_sha(Path(__file__))}
    if (lock["status"] != "locked_before_extension_provider_calls"
        or lock["extended_physical_ceiling"] != EXTRA_CAP
        or lock["scope"] != "TNAP/S_strong/bit/rep2/seed19/final_decision_only"
        or any(lock[key] != value for key, value in expected.items())):
        raise RuntimeError("Extension lock mismatch")
    return lock


def execute():
    verify_extension()
    before = c4.physical_count()
    if before == EXTRA_CAP:
        return {"status": "extension_budget_exhausted", "physical_calls": before}
    if json.loads(c4.run_path(2, 19).read_text(encoding="utf-8"))["complete"]:
        return {"status": "already_complete", "physical_calls": before}
    key = c4.api_key()
    c4.MAX_PHYSICAL = EXTRA_CAP  # In-memory guard only; locked runner file is untouched.
    try:
        row = c4.run_one(2, 19, key)
    except c4.FormatRetryExhausted as exc:
        value = {"status": "abandoned_after_two_invalid_formats", "utc": c4.utc(),
                 "message": str(exc), "physical_calls": c4.physical_count()}
        c4.save(RESULT, value)
        return value
    except Exception as exc:
        value = {"status": "paused_after_provider_or_validation_error", "utc": c4.utc(),
                 "error_type": type(exc).__name__, "message": str(exc),
                 "physical_calls": c4.physical_count()}
        c4.save(RESULT, value)
        return value
    finally:
        c4.MAX_PHYSICAL = 160
    if not json.loads(c4.run_path(2, 19).read_text(encoding="utf-8"))["complete"]:
        raise RuntimeError("Continuation returned without completing the sole campaign")
    value = {"status": "complete", "utc": c4.utc(),
             "scope": "TNAP/S_strong/bit/rep2/seed19/final_decision_only",
             "physical_calls_before_extension": before,
             "physical_calls_after_extension": c4.physical_count(),
             "last_campaign_H50": row["H50"],
             "extension_lock_sha256": c4.file_sha(LOCK)}
    c4.save(RESULT, value)
    return value


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("lock", "check-only", "execute"))
    args = parser.parse_args()
    result = create_lock() if args.mode == "lock" else (verify_extension() if args.mode == "check-only" else execute())
    print(json.dumps(result, ensure_ascii=False, indent=2))
