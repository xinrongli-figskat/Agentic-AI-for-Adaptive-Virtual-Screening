"""Check feature construction using only the public pre-freeze candidate list."""

import argparse
import hashlib
import json
from pathlib import Path

from .campaign_core import FixedController, run_synthetic_campaign
from .numerical_tools import NumericalTools


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--public-dir", type=Path, required=True)
    parser.add_argument("--full-synthetic", action="store_true",
                        help="Also run a complete 50-query dry run with generated labels")
    args = parser.parse_args()
    candidates = [json.loads(line) for line in (args.public_dir / "candidates.jsonl").read_text(
        encoding="utf-8").splitlines() if line]
    tools = NumericalTools(candidates)
    report = {"public_only": True, "real_labels_loaded": False,
              "candidate_count": len(candidates),
              "feature_count": len(tools.fingerprints),
              "feature_build_seconds": tools.feature_build_seconds}
    if args.full_synthetic:
        labels = {row["compound_key"]: hashlib.sha256(
            ("synthetic_label|" + row["compound_key"]).encode("utf-8")).digest()[0] % 2
            for row in candidates}
        runs = []
        for representation in ("bit", "count"):
            run = run_synthetic_campaign(candidates, labels, FixedController(), seed=0,
                                         representation=representation)
            runs.append({"representation": representation,
                         "queried_count": run["queried_count"],
                         "completed_batches": len(run["trajectory"]),
                         "distinct_compounds": len({key for step in run["trajectory"]
                                                     for key in step["selection"]})})
        report["synthetic_full_campaigns"] = runs
        report["synthetic_outcomes_only"] = True
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
