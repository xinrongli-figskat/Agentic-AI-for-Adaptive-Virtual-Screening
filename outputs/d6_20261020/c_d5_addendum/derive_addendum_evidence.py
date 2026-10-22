"""Recompute the public numerical evidence used by the D6-C D5 addendum.

This script only reads locked D5 public summaries.  It never reads private
campaign trajectories or writes outside its own D6-C directory.
"""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
D5 = ROOT / "outputs" / "d5_20261020"
REPORT = D5 / "d5_report.md"
RESULTS = D5 / "e_menu_results.json"
D4_SYNTHESIS = ROOT / "outputs" / "d4_tnap_glm_20261019" / "d4_cross_pool_synthesis.md"

EXPECTED_REPORT_SHA256 = "67529249605a1efceff3f4e90e4a09a3a1907388ba4b6a98acfab3a395c1ec5f"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def paired_bootstrap(differences: list[float], seed: int, n: int = 10_000) -> list[float]:
    rng = random.Random(seed)
    size = len(differences)
    draws = sorted(
        sum(differences[rng.randrange(size)] for _ in range(size)) / size
        for _ in range(n)
    )
    return [draws[int(n * 0.025)], draws[int(n * 0.975)]]


def main() -> None:
    assert sha256(REPORT) == EXPECTED_REPORT_SHA256, "D5 report hash differs from the D6 card"
    results = json.loads(RESULTS.read_text(encoding="utf-8"))

    fixed = (
        "fixed:knn_greedy",
        "fixed:knn_diverse",
        "fixed:uniform_random",
        "fixed:persistent_random_until_first_hit",
        "fixed:diverse_random_coldstart",
        "fixed:logreg_greedy",
        "fixed:ens_one_step_proxy",
    )
    table = {}
    for pool in ("tnap", "dyrk3"):
        table[pool] = {}
        for representation in ("bit", "count"):
            metrics = results["metrics"][pool][representation]
            table[pool][representation] = {
                "glm_extended": metrics.get("glm_extended", {}).get("mean"),
                **{arm: metrics[arm]["mean"] for arm in fixed},
            }

    equivalence = {}
    for representation in ("bit", "count"):
        persistent = results["metrics"]["tnap"][representation][
            "fixed:persistent_random_until_first_hit"
        ]["values_by_seed"]
        forced = results["comparisons"][representation]["forced_random_coldstart"]["values_by_seed"]
        assert persistent == forced, f"{representation}: cold-start values differ"
        equivalence[representation] = {
            "values_by_seed": persistent,
            "mean": sum(persistent) / len(persistent),
            "exactly_equal": True,
        }

    bit_fixed = results["metrics"]["tnap"]["bit"]
    tied = [arm for arm in fixed if bit_fixed[arm]["mean"] == 25.8]
    assert tied == [
        "fixed:persistent_random_until_first_hit",
        "fixed:logreg_greedy",
        "fixed:ens_one_step_proxy",
    ]

    bootstrap_recalculation = {}
    maximum_seed_change = 0.0
    for representation in ("bit", "count"):
        for name, comparison in results["comparisons"][representation]["comparisons"].items():
            differences = comparison["differences_by_seed"]
            d5_interval = paired_bootstrap(differences, 20261020)
            old_interval = paired_bootstrap(differences, 20261018)
            assert d5_interval == comparison["bootstrap_95_percent_descriptive"]
            change = max(abs(a - b) for a, b in zip(d5_interval, old_interval))
            maximum_seed_change = max(maximum_seed_change, change)
            bootstrap_recalculation[f"{representation}:{name}"] = {
                "d5_seed_20261020": d5_interval,
                "prior_seed_20261018": old_interval,
                "max_absolute_endpoint_change": change,
            }
    assert maximum_seed_change <= 0.10 + 1e-12

    result = {
        "post_exposure": True,
        "source_files": {
            "d5_report.md": {"sha256": sha256(REPORT), "expected_sha256": EXPECTED_REPORT_SHA256},
            "e_menu_results.json": {"sha256": sha256(RESULTS)},
            "d5_menu_spec.md": {"sha256": sha256(D5 / "d5_menu_spec.md")},
            "d4_cross_pool_synthesis.md": {"sha256": sha256(D4_SYNTHESIS)},
        },
        "full_eight_arm_table": table,
        "persistent_equals_forced_random_coldstart": equivalence,
        "tnap_bit_three_way_tie": {
            "mean_H50": 25.8,
            "arms_in_locked_menu_order": tied,
            "tie_rule_source": "d5_menu_spec.md: fixed-best ties resolve by locked menu order",
        },
        "tnap_uniform_random": {
            "bit_mean_H50": bit_fixed["fixed:uniform_random"]["mean"],
            "count_mean_H50": results["metrics"]["tnap"]["count"]["fixed:uniform_random"]["mean"],
            "analytic_random_expected_H50": 50 * 53 / 462,
            "analytic_basis": {"pool_size": 462, "hit_count": 53, "formula": "50 * K / N"},
        },
        "bootstrap_seeds": {
            "d5": 20261020,
            "project_customary_prior": 20261018,
            "scope": "The D6 card specifies that the visible interval changes are only resampling jitter of at most ±0.10.",
            "recomputed_intervals": bootstrap_recalculation,
            "maximum_absolute_endpoint_change": maximum_seed_change,
        },
    }
    target = OUT / "addendum_evidence.json"
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"evidence_sha256": sha256(target), "report_sha256": sha256(REPORT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
