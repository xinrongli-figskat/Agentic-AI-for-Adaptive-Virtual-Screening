"""Private-side read-only evaluation of complete frozen DYRK3 campaign runs."""

import argparse
import json
from pathlib import Path

from oracle_boundary_v0.oracle_boundary import read_json, read_jsonl

from .evaluation import compare_paired, summarize_run
from .real_campaign import load_frozen_manifest


def threshold_diagnostic(run, private_by_key):
    near_count = near_hits = far_exact_count = far_exact_hits = censored_count = 0
    for step in run["trajectory"]:
        for observation in step["observations"]:
            row = private_by_key[observation["compound_key"]]
            low, high = row.get("exact_min_nM"), row.get("exact_max_nM")
            if low is None or high is None or float(low) != float(high):
                censored_count += 1
            elif 800 <= float(low) <= 1250:
                near_count += 1
                near_hits += observation["outcome"]
            else:
                far_exact_count += 1
                far_exact_hits += observation["outcome"]
    if near_count + far_exact_count + censored_count != 50:
        raise ValueError("Threshold diagnostic did not account for all 50 queries")
    return {"near_exact_count": near_count, "near_exact_hits": near_hits,
            "far_exact_count": far_exact_count, "far_exact_hits": far_exact_hits,
            "censored_or_not_exact_count": censored_count,
            "interpretation": "descriptive_re_scoring_only_not_a_new_campaign"}


def evaluate(frozen_dir):
    manifest = load_frozen_manifest(frozen_dir)
    run_root = Path(manifest["run_root"])
    private_rows = read_jsonl(Path(manifest["private_dir"]) / "oracle_labels.jsonl")
    private_by_key = {row["compound_key"]: row for row in private_rows}
    if len(private_by_key) != len(private_rows):
        raise ValueError("Duplicate private compound key")
    collected, summaries, missing = [], [], []
    for representation in manifest["campaign_spec"]["representations"]:
        for seed in manifest["campaign_spec"]["seeds"]:
            for controller in ("llm", "fixed", "random"):
                path = run_root / f"{controller}_{representation}_seed{seed}" / "run.json"
                if not path.exists():
                    missing.append(str(path))
                    continue
                stored = read_json(path)
                if stored.get("status") != "complete":
                    missing.append(str(path))
                    continue
                run = stored["result"]
                if run["seed"] != seed or run["representation"] != representation:
                    raise ValueError("Run metadata differs from its frozen slot")
                summary = summarize_run(run)
                failure_path = path.parent / "failure_events.json"
                failures = read_json(failure_path) if failure_path.exists() else []
                failed_attempts = [attempt for event in failures
                                   for attempt in (event.get("public_api_diagnostic") or {}).get("attempt_log", [])]
                summary["failed_decision_count"] = len(failures)
                summary["failed_api_attempts_total"] = len(failed_attempts)
                summary["failed_api_overload_rejections"] = sum(
                    attempt.get("business_code") == "1305" for attempt in failed_attempts)
                summary["failed_decision_seconds_total"] = sum(
                    event.get("decision_seconds") or 0.0 for event in failures)
                summary["threshold_diagnostic"] = threshold_diagnostic(run, private_by_key)
                summaries.append(summary)
                collected.append(run)
    return {"status": "complete" if not missing else "incomplete",
            "missing_run_count": len(missing), "missing_run_paths": missing,
            "run_summaries": summaries,
            "paired_comparison": compare_paired(collected) if not missing else None,
            "limitations": ["single DYRK3 assay and chemical series",
                            "assay-defined inhibition is not direct binding",
                            "threshold diagnostic is descriptive only"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frozen-dir", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(args.frozen_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
