"""Offline-only D3-6 aggregation of already saved 280 campaign trajectories."""
import csv
import hashlib
import json
import random
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "outputs/d3_tnap_20261019"
RUNS = BASE / "d3_6_runs_private_20261019"
REPORT = BASE / "d3_6_report"
FROZEN = BASE / "freeze_tnap_v1"
LABELS = BASE / "freeze_tnap_v1_private_labels/oracle_labels.jsonl"
ARMS = ("random", "structure_prior", "label_shuffle", "fixed", "fixed_schedule", "rule_adaptive_v2", "forced_random_coldstart")
REPS = ("bit", "count")
PROTOCOL_SHA = "8384797c0348b51e0b0bb2547b77520b36981d81af4b1320be4e6adb49b17943"
RECEIPT_SHA = "f8801efbe28f73ddbcf9c5a2d493d862cbf124f311b6659e9224f2161b5bf662"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def paired(values):
    rng = random.Random(20261018)
    draws = sorted(statistics.mean(rng.choice(values) for _ in values) for _ in range(10000))
    return {"mean": statistics.mean(values), "ci_low": draws[249],
            "ci_high": draws[9750], "paired_sd": statistics.stdev(values)}


def main():
    assert sha(BASE / "tnap_v1_campaign_protocol.md") == PROTOCOL_SHA
    assert sha(FROZEN / "freeze_receipt.json") == RECEIPT_SHA
    receipt = json.loads((FROZEN / "freeze_receipt.json").read_text())
    assert sha(LABELS) == next(f["sha256"] for f in receipt["files"] if f["snapshot"] == str(LABELS))
    assert not REPORT.exists() or not any(REPORT.iterdir()), "Existing report artifacts must be preserved"
    labels = {r["compound_key"]: r["outcome"] for r in (json.loads(line) for line in LABELS.read_text().splitlines())}
    assert len(labels) == 462 and sum(labels.values()) == 53
    paths = sorted(RUNS.glob("*.json"))
    assert len(paths) == 280
    rows, file_hashes = [], []
    for rep in REPS:
        for seed in range(20):
            init = None
            for arm in ARMS:
                path = RUNS / f"{arm}_{rep}_seed{seed}.json"
                saved = json.loads(path.read_text())
                row, result = saved["summary"], saved["result"]
                assert (row["representation"], row["seed"], row["arm"]) == (rep, seed, arm)
                steps = result["trajectory"]
                assert len(steps) == 5 and all(len(s["selection"]) == 10 for s in steps)
                chosen = [k for step in steps for k in step["selection"]]
                assert len(chosen) == len(set(chosen)) == 50 and set(chosen) <= labels.keys()
                init = chosen[:10] if init is None else init
                assert chosen[:10] == init
                truth = []
                cumulative = 0
                for step in steps:
                    cumulative += sum(labels[k] for k in step["selection"])
                    truth.append(cumulative)
                assert truth == row["cumulative_true"] and truth[-1] == row["H50"]
                expected_first = next((i for i,k in enumerate(chosen,1) if labels[k]), None)
                assert row["queries_to_first_hit"] == expected_first
                assert row["initialization_hits"] == truth[0]
                rows.append(row)
                file_hashes.append({"file": path.name, "sha256": sha(path), "bytes": path.stat().st_size})
    assert len(rows) == 280
    expected = 50 * 53 / 462
    arm_stats, contrasts, triggers, zero_stats = {}, {}, {}, {}
    zero_seeds = [s for s in range(20) if next(r for r in rows if r["representation"]=="bit" and r["seed"]==s and r["arm"]=="fixed")["initialization_hits"] == 0]
    pairs = [("fixed", "structure_prior"), ("fixed", "label_shuffle"), ("rule_adaptive_v2", "fixed"),
             ("fixed_schedule", "fixed"), ("forced_random_coldstart", "fixed")]
    pairs.extend((arm, "random") for arm in ARMS if arm != "random")
    for rep in REPS:
        by = {(r["arm"],r["seed"]):r for r in rows if r["representation"]==rep}
        arm_stats[rep] = {}
        for arm in ARMS:
            subset = [by[arm,s] for s in range(20)]
            first = [r["queries_to_first_hit"] for r in subset]
            observed = [v for v in first if v is not None]
            arm_stats[rep][arm] = {
                "mean_H50": statistics.mean(r["H50"] for r in subset),
                "sd_H50": statistics.stdev(r["H50"] for r in subset),
                "mean_curve": [statistics.mean(r["cumulative_true"][i] for r in subset) for i in range(5)],
                "mean_average_cumulative_hits_10_50": statistics.mean(r["average_cumulative_hits_10_50"] for r in subset),
                "enrichment_vs_random_expectation": statistics.mean(r["H50"] for r in subset)/expected,
                "first_hit_observed_runs": len(observed), "first_hit_censored_at_50": len(first)-len(observed),
                "mean_first_hit_among_observed": statistics.mean(observed) if observed else None,
                "restricted_first_hit_mean_51_code": statistics.mean(51 if v is None else v for v in first),
                "mean_wall_seconds": statistics.mean(r["wall_seconds"] for r in subset),
                "mean_feature_build_seconds": statistics.mean(r["feature_build_seconds"] for r in subset),
                "mean_selection_seconds": statistics.mean(r["selection_seconds"] for r in subset),
                "mean_analysis_seconds": statistics.mean(r["analysis_seconds"] for r in subset),
            }
        contrasts[rep] = {f"{a}-{b}": paired([by[a,s]["H50"]-by[b,s]["H50"] for s in range(20)]) for a,b in pairs}
        adaptive = [by["rule_adaptive_v2",s] for s in range(20)]
        triggers[rep] = {"seeds_with_trigger": sum(bool(r["trigger_rounds"]) for r in adaptive),
                         "total_trigger_rounds": sum(len(r["trigger_rounds"]) for r in adaptive),
                         "round_counts": dict(Counter(x for r in adaptive for x in r["trigger_rounds"]))}
        zero_stats[rep] = {}
        for arm in ARMS:
            subset = [by[arm,s] for s in zero_seeds]
            zero_stats[rep][arm] = {"H50_by_seed": {str(r["seed"]):r["H50"] for r in subset},
                "mean_H50": statistics.mean(r["H50"] for r in subset) if subset else None,
                "queries_to_first_hit_by_seed": {str(r["seed"]):r["queries_to_first_hit"] for r in subset},
                "fallback_batches": sum(len(r["fallback_rounds"]) for r in subset)}
    REPORT.mkdir(exist_ok=True)
    aggregate = {"schema":"tnap_d3_cpu_aggregate_v1", "created_utc":datetime.now(timezone.utc).isoformat(),
        "protocol_sha256":PROTOCOL_SHA,"freeze_receipt_sha256":RECEIPT_SHA,
        "campaign_runs":280,"glm_calls":0,"random_expected_H50":expected,
        "zero_hit_initialization_seeds":zero_seeds,"zero_hit_seed_count":len(zero_seeds),
        "arm_stats":arm_stats,"paired_contrasts":contrasts,"adaptive_triggers":triggers,
        "zero_hit_subgroup":zero_stats,
        "limitations":"Post-exposure limited source; variable measurement depth is strongly associated with labels; construct unspecified; no GLM arm; no cross-target inference."}
    dump(REPORT / "aggregate.json", aggregate)
    with (RUNS / "run_index.csv").open("w",encoding="utf-8",newline="") as out:
        writer=csv.DictWriter(out,fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({k:json.dumps(v) if isinstance(v,list) else v for k,v in row.items()})
    run_manifest = {"schema":"tnap_d3_private_run_manifest_v1","files":file_hashes,
        "run_index_sha256":sha(RUNS / "run_index.csv"),"self_excluded":True}
    dump(RUNS / "MANIFEST.json",run_manifest)
    table = ["# TNAP v1 D3 CPU controls", "", f"Protocol SHA-256 `{PROTOCOL_SHA}`; frozen pool receipt `{RECEIPT_SHA}`. 280 completed campaigns, 0 GLM calls.", "",
             f"Unlabeled 10-query initialization had zero hits in {len(zero_seeds)}/20 seeds: {zero_seeds}. Random expected H@50: {expected:.3f}.", "",
             "| Representation | Arm | Mean H@50 | SD | First-hit censored (>50) |", "|---|---|---:|---:|---:|"]
    for rep in REPS:
        for arm in ARMS:
            v=arm_stats[rep][arm]
            table.append(f"| {rep} | {arm} | {v['mean_H50']:.2f} | {v['sd_H50']:.2f} | {v['first_hit_censored_at_50']}/20 |")
    table.extend(["", "Main paired bit contrasts (10,000 paired bootstrap resamples, seed 20261018):", "",
                  "| Contrast | Mean difference | 95% percentile interval | Paired SD |", "|---|---:|---:|---:|"])
    for contrast in ("fixed-structure_prior","fixed-label_shuffle"):
        v=contrasts["bit"][contrast]
        table.append(f"| {contrast} | {v['mean']:.2f} | [{v['ci_low']:.2f}, {v['ci_high']:.2f}] | {v['paired_sd']:.2f} |")
    table.extend(["", "A missing first hit by query 50 is right-censored, not zero or an observed query 51. The aggregate reports conditional means among observed first hits and a separately labeled 51-coded restricted mean.",
                  "", f"Zero-hit seed details, forced fallback versus fixed, adaptive trigger rounds, curves, costs, and secondary contrasts are in `aggregate.json`. Bit adaptive trigger: {triggers['bit']}; count: {triggers['count']}.",
                  "", "**Scientific limit:** TNAP remains `limited`: the protein construct is unspecified; characterization depth varies by compound (1–21 fitted curves, median 1) and is strongly associated with the assay-defined label (AUC 0.879, r 0.495). This is not direct-binding evidence or a uniform-effort screen. Results cannot be generalized to other targets. GLM was not evaluated in D3.",
                  "", "The original locked runner completed all 280 trajectories but failed while averaging a right-censored first-hit field. `DEVIATION_20261019_D3_REPORTING_CENSOR.md` records the offline-only repair. No campaign was rerun."])
    (REPORT / "d3_summary.md").write_text("\n".join(table)+"\n",encoding="utf-8",newline="\n")
    (REPORT / "STATUS").write_text("done\n",encoding="utf-8",newline="\n")
    manifest={"schema":"tnap_d3_report_manifest_v1","created_utc":aggregate["created_utc"],
        "protocol_sha256":PROTOCOL_SHA,"freeze_receipt_sha256":RECEIPT_SHA,
        "private_run_manifest_sha256":sha(RUNS / "MANIFEST.json"),"glm_calls":0,
        "files":[{"path":p.name,"sha256":sha(p),"bytes":p.stat().st_size} for p in sorted(REPORT.iterdir()) if p.is_file() and p.name!="MANIFEST.json"],"self_excluded":True}
    dump(REPORT / "MANIFEST.json",manifest)
    print(json.dumps({"status":"done","aggregate_sha256":sha(REPORT / "aggregate.json"),
        "report_manifest_sha256":sha(REPORT / "MANIFEST.json"),"zero_hit_seeds":zero_seeds,
        "first_hit_censored_total":sum(r["queries_to_first_hit"] is None for r in rows)}))


if __name__ == "__main__":
    main()
