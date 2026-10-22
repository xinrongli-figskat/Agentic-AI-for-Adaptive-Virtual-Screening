"""C5-v2: compare B's five-repeat TNAP-bit GLM means to two CPU bandits."""
from __future__ import annotations

import hashlib
import io
import json
import random
import statistics
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
OUT = HERE / "C5_SUMMARY.json"
PRIVATE = ROOT / "outputs/d7_20261021/c_surrogate_factor_v2_private"
B_ARCHIVE = ROOT / "outputs/d7_20261021/b_model_variance_private/b_full_evidence.zip"
D6_ROOT = ROOT / "outputs/d6_20261020/b_menu_description_private/runs_v0_replay/runs/tnap/bit"
A1_SUMMARY = ROOT / "outputs/d7_20261021/a_headroom_bandit/revision_11field/cpu_summary.json"
SEEDS = tuple(range(20))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_run(blob: bytes, seed: int) -> int:
    obj = json.loads(blob)
    if not obj.get("complete") or obj.get("seed") != seed or obj.get("pool") != "tnap":
        raise ValueError(f"Invalid or incomplete GLM run for seed {seed}")
    if obj.get("representation") != "bit" or obj.get("arm") != "glm_extended":
        raise ValueError(f"Unexpected GLM run identity for seed {seed}")
    if obj.get("queried_count") != 50 or len(obj.get("trajectory", [])) != 5:
        raise ValueError(f"Unexpected campaign budget for seed {seed}")
    return int(obj["H50"])


def percentile_ci(values: list[float], n=10_000, seed=20261018):
    rng = random.Random(seed)
    draws = []
    for _ in range(n):
        ix = [rng.randrange(len(values)) for _ in values]
        draws.append(sum(values[i] for i in ix) / len(ix))
    draws.sort()
    return [draws[250], draws[9750]]


def main():
    with ZipFile(B_ARCHIVE) as archive:
        glm = {seed: [] for seed in SEEDS}
        for seed in SEEDS:
            for rep in range(1, 6):
                if rep == 1 and seed < 10:
                    path = D6_ROOT / f"glm_extended_seed{seed}" / "run.json"
                    value = load_run(path.read_bytes(), seed)
                else:
                    name = f"rep{rep}/runs/tnap/bit/glm_extended_seed{seed}/run.json"
                    value = load_run(archive.read(name), seed)
                glm[seed].append(value)

    cpu = json.loads(A1_SUMMARY.read_text(encoding="utf-8"))
    bandits = {arm: {} for arm in ("bandit_thompson", "bandit_ucb1")}
    for row in cpu["rows"]:
        if (row.get("pool") == "tnap" and row.get("representation") == "bit"
                and row.get("granularity") == "g4" and row.get("arm") in bandits):
            bandits[row["arm"]][int(row["seed"])] = int(row["H50"])
    for arm, by_seed in bandits.items():
        if set(by_seed) != set(SEEDS):
            raise ValueError(f"{arm}: expected exactly 20 TNAP-bit seeds")

    per_seed_glm = {s: sum(glm[s]) / 5 for s in SEEDS}
    private = {"post_exposure": True, "utc": datetime.now(timezone.utc).isoformat(),
               "seed": 20261018, "resamples": 10000,
               "B_archive_sha256": sha(B_ARCHIVE), "A1_cpu_summary_sha256": sha(A1_SUMMARY),
               "D6_replay_run_sha256": {str(s): sha(D6_ROOT / f"glm_extended_seed{s}" / "run.json") for s in range(10)},
               "glm_h50_by_repeat_private": {str(s): glm[s] for s in SEEDS},
               "glm_h50_by_seed_mean_private": {str(s): per_seed_glm[s] for s in SEEDS},
               "bandit_h50_by_seed_private": {arm: {str(s): bandits[arm][s] for s in SEEDS} for arm in bandits}}
    summary = {"status": "C5_COMPLETE", "post_exposure": True,
               "utc": private["utc"], "bootstrap": {"method": "paired seed bootstrap",
               "seed": 20261018, "resamples": 10000, "percentile_indices_zero_based": [250, 9750]},
               "glm_mean_h50": sum(per_seed_glm.values()) / 20,
               "comparisons": {}}
    for arm in bandits:
        diffs = [per_seed_glm[s] - bandits[arm][s] for s in SEEDS]
        summary["comparisons"][arm] = {
            "glm_minus_bandit_mean": sum(diffs) / 20,
            "paired_bootstrap_ci95": percentile_ci(diffs),
            "bandit_mean_h50": sum(bandits[arm].values()) / 20,
            "seeds": 20,
        }
    summary["limitations"] = [
        "TNAP bit only; post-exposure descriptive comparison.",
        "The bandit_ucb1 menu has only four decision points for seven arms and is close to a strawman; bandit_thompson is the more credible bandit comparator.",
        "Count-format bandits have no matching five-repeat GLM matrix; those historical comparisons retain the single-run plus variance-component basis and are not mixed with this analysis."
    ]
    PRIVATE.mkdir(parents=True, exist_ok=True)
    (PRIVATE / "C5_PER_SEED_PRIVATE.json").write_text(json.dumps(private, indent=2) + "\n", encoding="utf-8")
    OUT.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print("private_sha256:", sha(PRIVATE / "C5_PER_SEED_PRIVATE.json"))
    print("public_sha256:", sha(OUT))


if __name__ == "__main__":
    main()
