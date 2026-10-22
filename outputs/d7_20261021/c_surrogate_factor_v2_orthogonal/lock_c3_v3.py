"""Lock the authorized regression revision before any new C3 campaign."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    target = HERE / "C3_V3_LOCK.json"
    if target.exists():
        raise FileExistsError(target)
    files = {"addendum": HERE / "C3_REGRESSION_ADDENDUM_v3.md",
             "core": HERE / "c3_core.py", "runner": HERE / "run_revised_regression.py",
             "C1_v2_lock": HERE / "C1_LOCK_v2.json",
             "C2_six_public": HERE / "C2_SIX_PUBLIC.json",
             "original_blocker": HERE / "BLOCKED_C3_REGRESSION.md",
             "original_gate": HERE / "C3_REGRESSION_GATE.json"}
    c2 = json.loads(files["C2_six_public"].read_text())
    if c2["TNAP_tier_b_pass"] is not True:
        raise RuntimeError("C2 strength gate failed")
    result = {"status": "C3_V3_REGRESSION_PRE_RUN_LOCK", "utc": datetime.now(timezone.utc).isoformat(),
              "post_exposure": True, "labels_read_by_this_lock": False,
              "user_decision": "retain C1 one-class random fallback and revise seven exact D5 regressions",
              "file_sha256": {key: sha(path) for key, path in files.items()},
              "glm_calls_authorized": 0}
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"lock": str(target), "sha256": sha(target), "utc": result["utc"]}))


if __name__ == "__main__":
    main()
