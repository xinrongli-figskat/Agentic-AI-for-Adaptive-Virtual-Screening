"""Record or verify unchanged pre-existing D2 evidence and frozen files."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/driveA/xinrong/agentic-screening")
DEST = ROOT / "outputs/d2_controls_20261019/attempt2_20261019/d2_2_protected_baseline.json"


def files():
    roots = [ROOT / "data/curation_private/frozen_dyrk3_v1",
             ROOT / "outputs/d_discrimination_20261018",
             ROOT / "campaign_v0"]
    selected = [p for base in roots for p in base.rglob("*")
                if p.is_file() and "__pycache__" not in p.parts]
    selected.append(ROOT / "data/curation_private/r5_cpu_controls_private_20261018/control_summary.csv")
    for controller in ("fixed", "random", "llm"):
        for rep in ("bit", "count"):
            for seed in range(5):
                selected.append(ROOT / f"data/curation_private/runs_dyrk3_v1/{controller}_{rep}_seed{seed}/run.json")
    assert len(selected) == len(set(selected))
    assert all(p.is_file() for p in selected)
    return sorted(selected)


def snapshot():
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files()}


def main():
    arg = argparse.ArgumentParser()
    arg.add_argument("mode", choices=("record", "verify"))
    mode = arg.parse_args().mode
    current = snapshot()
    if mode == "record":
        assert not DEST.exists(), "Baseline already recorded; cannot overwrite"
        DEST.write_text(json.dumps({"recorded_utc": datetime.now(timezone.utc).isoformat(),
                                    "files": current}, indent=2, sort_keys=True) + "\n")
    else:
        saved = json.loads(DEST.read_text())
        assert current == saved["files"], "Protected evidence changed"
    print(json.dumps({"mode": mode, "protected_files": len(current),
                      "baseline_sha256": hashlib.sha256(DEST.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
