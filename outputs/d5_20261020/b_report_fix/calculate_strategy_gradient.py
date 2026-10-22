"""Recompute D4 strategy gradients from read-only, locally backed-up run.json files.

This is an observational, post-exposure addendum.  No labels are loaded beyond
the outcomes already revealed in each campaign trajectory.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
D4 = PROJECT / "outputs" / "d4_tnap_glm_20261019"
BACKUP = D4 / "remote_backup_private_20261019" / "d4_tnap_glm_20261019"
RUNS = BACKUP / "d4_glm_private_20261019" / "runs"
ANALYSIS = BACKUP / "attempt2_20261019" / "d4_analysis_private_20261019" / "analysis.json"
EXPECTED_ANALYSIS_SHA = "2e7ac7fd2e2ee3f43e0444fe5e132a6a6be3ce06d08706b326dbd3db9298881f"
BUCKETS = ("0", "1-2", "3-5", "6+")
POLICIES = ("knn_greedy", "knn_diverse", "uniform_random")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bucket(hits: int) -> str:
    assert 0 <= hits <= 10
    if hits == 0:
        return "0"
    if hits <= 2:
        return "1-2"
    if hits <= 5:
        return "3-5"
    return "6+"


def fisher_two_sided(table: list[list[int]]) -> float:
    """Two-sided Fisher probability using SciPy's probability-order convention."""
    a, b = table[0]
    c, d = table[1]
    r1, r2, col1 = a + b, c + d, a + c
    n = r1 + r2
    low, high = max(0, col1 - r2), min(r1, col1)

    def prob(x: int) -> float:
        return math.comb(r1, x) * math.comb(r2, col1 - x) / math.comb(n, col1)

    observed = prob(a)
    return sum(prob(x) for x in range(low, high + 1) if prob(x) <= observed * (1 + 1e-12))


def cochran_armitage(counts: dict[str, Counter], policy: str) -> dict[str, float]:
    """Two-sided 1-df linear trend test with ordinal bin scores 0,1,2,3."""
    ns = [sum(counts[b].values()) for b in BUCKETS]
    yes = [counts[b][policy] for b in BUCKETS]
    n = sum(ns)
    m = sum(yes)
    scores = (0, 1, 2, 3)
    mean_score = sum(count * score for count, score in zip(ns, scores)) / n
    contrast = sum(score * (observed - count * m / n)
                   for score, observed, count in zip(scores, yes, ns))
    weighted_ss = sum(count * (score - mean_score) ** 2 for count, score in zip(ns, scores))
    variance = m * (n - m) / (n * (n - 1)) * weighted_ss
    z = contrast / math.sqrt(variance)
    return {"z": z, "chi_square_1df": z * z, "two_sided_p": math.erfc(abs(z) / math.sqrt(2))}


def pearson_independence(counts: dict[str, Counter], policy: str) -> dict[str, float]:
    """2x4 Pearson independence test (df=3); this is not a linear trend test."""
    observed = [[counts[b][policy], sum(counts[b].values()) - counts[b][policy]] for b in BUCKETS]
    n = sum(sum(row) for row in observed)
    columns = [sum(row[j] for row in observed) for j in range(2)]
    stat = sum((value - sum(row) * columns[j] / n) ** 2 / (sum(row) * columns[j] / n)
               for row in observed for j, value in enumerate(row))
    half = stat / 2
    p = math.erfc(math.sqrt(half)) + 2 * math.sqrt(half / math.pi) * math.exp(-half)
    return {"chi_square_3df": stat, "two_sided_p": p}


def compute():
    assert sha256(ANALYSIS) == EXPECTED_ANALYSIS_SHA
    prior = json.loads(ANALYSIS.read_text(encoding="utf-8"))
    verification = json.loads((D4 / "post_glm_verification.json").read_text(encoding="utf-8"))
    assert verification["status"] == "pass" and verification["run_count"] == 40
    tables = {}
    run_hashes = {}
    for representation in ("bit", "count"):
        counts = {b: Counter() for b in BUCKETS}
        for seed in range(20):
            path = RUNS / f"llm_{representation}_seed{seed}" / "run.json"
            run_hashes[f"{representation}_seed{seed}"] = sha256(path)
            assert run_hashes[f"{representation}_seed{seed}"] == verification["run_hashes"][f"{representation}_seed{seed}"]
            saved = json.loads(path.read_text(encoding="utf-8"))
            run = saved["result"]
            assert len(run["trajectory"]) == 5 and saved["status"] == "complete"
            for round_index in range(1, 5):
                previous = run["trajectory"][round_index - 1]
                step = run["trajectory"][round_index]
                assert len(previous["observations"]) == len(step["observations"]) == 10
                previous_hits = sum(int(row["outcome"]) for row in previous["observations"])
                policy = step["decision"]["policy"]
                assert policy in POLICIES
                counts[bucket(previous_hits)][policy] += 1
        assert sum(sum(row.values()) for row in counts.values()) == 80
        assert {b: dict(counts[b]) for b in BUCKETS} == prior["strategy"][representation]["by_previous_batch_hits"]
        first = prior["strategy"][representation]["fisher_zero_vs_nonzero"]
        original_table = [
            [counts["0"]["knn_diverse"], sum(counts["0"].values()) - counts["0"]["knn_diverse"]],
            [sum(counts[b]["knn_diverse"] for b in BUCKETS[1:]),
             sum(sum(counts[b].values()) - counts[b]["knn_diverse"] for b in BUCKETS[1:])],
        ]
        original_p = fisher_two_sided(original_table)
        assert first["table_diverse_vs_other"] == original_table
        assert math.isclose(first["two_sided_p"], original_p, abs_tol=1e-12)
        table = [
            [counts["0"]["knn_greedy"], sum(counts["0"].values()) - counts["0"]["knn_greedy"]],
            [counts["6+"]["knn_greedy"], sum(counts["6+"].values()) - counts["6+"]["knn_greedy"]],
        ]
        tables[representation] = {
            "counts": counts,
            "greedy_trend": cochran_armitage(counts, "knn_greedy"),
            "random_trend": cochran_armitage(counts, "uniform_random"),
            "greedy_pearson_independence": pearson_independence(counts, "knn_greedy"),
            "random_pearson_independence": pearson_independence(counts, "uniform_random"),
            "greedy_zero_vs_six_plus": {"table": table, "two_sided_p": fisher_two_sided(table)},
            "greedy_zero_to_two": {
                "chosen": sum(counts[b]["knn_greedy"] for b in ("0", "1-2")),
                "total": sum(sum(counts[b].values()) for b in ("0", "1-2")),
            },
            "original_diverse_zero_vs_nonzero": {"table": original_table, "two_sided_p": original_p},
        }
    return tables, run_hashes


def write_table(tables: dict):
    path = HERE / "strategy_gradient_tables.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("representation", "previous_batch_hits_bin", "bin_ordinal_score",
                                                   "decision_count", "knn_greedy_count", "knn_greedy_fraction",
                                                   "knn_diverse_count", "knn_diverse_fraction",
                                                   "uniform_random_count", "uniform_random_fraction"))
        writer.writeheader()
        for representation in ("bit", "count"):
            for score, b in enumerate(BUCKETS):
                counts = tables[representation]["counts"][b]
                n = sum(counts.values())
                row = {"representation": representation, "previous_batch_hits_bin": b,
                       "bin_ordinal_score": score, "decision_count": n}
                for policy in POLICIES:
                    row[policy + "_count"] = counts[policy]
                    row[policy + "_fraction"] = f"{counts[policy] / n:.12f}"
                writer.writerow(row)


if __name__ == "__main__":
    results, source_hashes = compute()
    write_table(results)
    print(json.dumps({
        "analysis_sha256": sha256(ANALYSIS),
        "run_count": len(source_hashes),
        "runs_sha256": source_hashes,
        "tests": {rep: {key: value for key, value in result.items() if key != "counts"}
                  for rep, result in results.items()},
    }, ensure_ascii=False, indent=2))
