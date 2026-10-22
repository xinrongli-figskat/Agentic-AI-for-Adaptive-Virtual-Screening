"""Offline, aggregate-only analysis of the locked C4 five-menu TNAP cell."""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
C3 = ROOT / "outputs/d7_20261021/c_surrogate_factor_v2_orthogonal"
PRIVATE = ROOT / "outputs/d7_20261021/c4_five_private"
OLD_PRIVATE = ROOT / "outputs/d7_20261021/c_surrogate_factor_v2_orthogonal_private"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "outputs"))
sys.path.insert(0, str(ROOT / "outputs/d7_20261021/c_surrogate_factor/runtime_packages"))
import numpy as np
from oracle_boundary_v0.oracle_boundary import BatchOracle
from outputs.d7_20261021.c_surrogate_factor_v2.run_c2v2 import load_inputs, read_jsonl
from outputs.d7_20261021.c_surrogate_factor_v2_orthogonal.run_meta_five import MENU, META, path_for as meta_path
from outputs.d7_20261021.c4_five.run_c4 import (
    ARM, MAX_PHYSICAL, file_sha, physical_count, run_path, save, verify_lock,
)


def utc():
    return datetime.now(timezone.utc).isoformat()


def behavior(mode):
    if mode == "scored_greedy":
        return "greedy_like"
    if mode == "scored_diverse":
        return "diverse_like"
    if mode in ("policy_random", "policy_coldstart_random", "one_class_random_fallback"):
        return "random"
    raise RuntimeError("Unexpected selector mode: " + str(mode))


def frozen_labels():
    pub, private = load_inputs()["TNAP"]
    candidates = read_jsonl(pub)
    labels = {row["compound_key"]: int(row["outcome"]) for row in read_jsonl(private)}
    return candidates, labels


def reference_vector(arm):
    values = []
    for seed in range(20):
        if arm in META:
            path = meta_path(("TNAP", "S_strong", arm, seed))
        else:
            path = OLD_PRIVATE / "runs" / "TNAP" / "S_strong" / arm / f"seed{seed}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        if any(data.get(k) != v for k, v in (("pool", "TNAP"), ("surrogate", "S_strong"),
                                           ("arm", arm), ("seed", seed))):
            raise RuntimeError("Reference run identity mismatch")
        values.append(int(data["H50"]))
    return np.asarray(values, dtype=float)


def compare(llm_seed_mean, reference, sigma, rng):
    diff = llm_seed_mean - reference
    draws = rng.integers(0, 20, size=(10000, 20))
    sampled = diff[draws].mean(axis=1)
    augmented = sampled + rng.normal(0, sigma / np.sqrt(40), size=10000)
    return {"paired_mean_difference_H50": float(diff.mean()),
            "paired_seed_bootstrap_CI95": [float(x) for x in np.quantile(sampled, [.025, .975])],
            "B_model_sd_augmented_sensitivity_CI95":
                [float(x) for x in np.quantile(augmented, [.025, .975])],
            "reference_mean_H50": float(reference.mean()),
            "seed_count": 20, "llm_repeats_per_seed": 2}


def analyze():
    lock = verify_lock()
    candidates, labels = frozen_labels()
    runs = {}
    named, realized, auto = Counter(), Counter(), 0
    usage = Counter()
    decision_files = []
    for rep in (1, 2):
        for seed in range(20):
            path = run_path(rep, seed)
            if not path.exists():
                return {"status": "partial", "reason": "missing_campaign",
                        "complete_campaigns": len(runs), "physical_calls": physical_count()}
            data = json.loads(path.read_text(encoding="utf-8"))
            if not data.get("complete"):
                return {"status": "partial", "reason": "incomplete_campaign",
                        "complete_campaigns": len(runs), "physical_calls": physical_count()}
            if any(data.get(k) != v for k, v in (("repeat", rep), ("seed", seed),
                ("arm", ARM), ("pool", "TNAP"), ("surrogate", "S_strong"),
                ("queried_count", 50), ("lock_sha256", file_sha(HERE / "C4_LOCK_v1.json")))):
                raise RuntimeError("C4 run identity, budget, or lock mismatch")
            steps = data["trajectory"]
            keys = [key for step in steps for key in step["selection"]]
            expected = BatchOracle(candidates, labels, seed=seed,
                                   total_budget=50, initialization_queries=10,
                                   batch_size=10).proposed_initial_ids()
            if len(steps) != 5 or len(keys) != 50 or len(set(keys)) != 50 or steps[0]["selection"] != expected:
                raise RuntimeError("Invalid C4 trajectory or initialization")
            for step in steps:
                if step["observations"] != [
                    {"compound_key": key, "outcome": labels[key]} for key in step["selection"]]:
                    raise RuntimeError("C4 observation mismatch")
            if any(step["policy"] not in MENU for step in steps[1:]):
                raise RuntimeError("C4 out-of-menu decision")
            if data["H50"] != sum(row["outcome"] for step in steps for row in step["observations"]):
                raise RuntimeError("C4 H50 mismatch")
            for step in steps[1:]:
                named[step["policy"]] += 1
                realized[behavior(step["mode"])] += 1
                auto += int(step["automatic_commitment"])
            runs[rep, seed] = data
            decision_files.extend(path.parent.glob("decision_round*_try*.json"))
    if len(runs) != 40 or sum(named.values()) != 160 or sum(realized.values()) != 160:
        raise RuntimeError("C4 matrix or behavior tally incomplete")
    status_counts = Counter()
    for path in decision_files:
        receipt = json.loads(path.read_text(encoding="utf-8"))
        status_counts[receipt["status"]] += 1
        if receipt["status"] not in ("valid_decision", "invalid_format"):
            raise RuntimeError("Unexpected model receipt status")
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            value = (receipt.get("usage") or {}).get(key)
            if isinstance(value, int):
                usage[key] += value
    if status_counts["valid_decision"] != 160 - auto:
        raise RuntimeError("Valid decision receipt count differs from logged automatic commitments")
    if physical_count() > MAX_PHYSICAL:
        raise RuntimeError("C4 exceeded physical provider-call cap")
    per_seed = np.asarray([
        (runs[1, seed]["H50"] + runs[2, seed]["H50"]) / 2 for seed in range(20)], dtype=float)
    sigma = float(lock["B_model_sd"])
    references = {arm: reference_vector(arm) for arm in META + ("greedy",)}
    cpu = json.loads((C3 / "C3_FIVE_PUBLIC_SUMMARY.json").read_text(encoding="utf-8"))
    fixed = cpu["cells"]["TNAP"]["S_strong"]["fixed_mean_H50"]
    if max(fixed, key=fixed.get) != "greedy" or lock["best_meta_primary"] != "bandit_thompson":
        raise RuntimeError("Preselected comparisons changed")
    for arm in META:
        expected_mean = cpu["cells"]["TNAP"]["S_strong"]["five_menu_meta_mean_H50"][arm]
        if not np.isclose(references[arm].mean(), expected_mean):
            raise RuntimeError("CPU reference aggregate differs from locked C3 summary")
    rng = np.random.default_rng(20261018)
    comparisons = {arm: compare(per_seed, values, sigma, rng)
                   for arm, values in references.items()}
    one_class = sum(step["mode"] == "one_class_random_fallback"
                    for data in runs.values() for step in data["trajectory"][1:])
    result = {"status": "complete", "utc": utc(), "post_exposure": True,
              "scope": "TNAP/S_strong/bit", "arm": ARM, "campaigns": 40,
              "seeds": 20, "repeats": 2, "llm_mean_H50": float(per_seed.mean()),
              "llm_seed_means_H50": [float(x) for x in per_seed],
              "primary_reference": "bandit_thompson",
              "comparisons": comparisons,
              "policy_name_counts": dict(sorted(named.items())),
              "realized_behavior_counts": dict(sorted(realized.items())),
              "automatic_commitment_batches": auto,
              "one_class_random_fallback_batches": one_class,
              "valid_model_decisions": status_counts["valid_decision"],
              "invalid_format_responses": status_counts["invalid_format"],
              "format_failure_fraction_of_decision_responses":
                  status_counts["invalid_format"] / sum(status_counts.values()) if status_counts else None,
              "physical_provider_attempts": physical_count(),
              "provider_usage_returned": dict(usage),
              "model_sd_from_B": sigma, "bootstrap_seed": 20261018,
              "bootstrap_resamples": 10000,
              "augmented_interval_note": "Conservative sensitivity; may double-count model noise represented in two-repeat seed means.",
              "multiple_comparison_correction": "none; secondary contrasts exploratory",
              "C3_tie_corrected_spearman": -0.2898855178262242,
              "not_mentor_question_ii": True,
              "not_directly_comparable_to_D5_or_D7A": True}
    save(HERE / "C4_PUBLIC_ANALYSIS.json", result)
    private_hashes = sorted(f"{path.relative_to(PRIVATE).as_posix()} {file_sha(path)}"
                            for path in PRIVATE.rglob("*.json"))
    audit = {"status": "pass", "utc": utc(), "campaigns": 40,
             "unique_queries_per_campaign": 50, "ENS_decisions": 0,
             "lock_sha256": file_sha(HERE / "C4_LOCK_v1.json"),
             "private_tree_sha256": hashlib.sha256(("\n".join(private_hashes)+"\n").encode()).hexdigest(),
             "physical_provider_attempts": physical_count(),
             "valid_model_decisions": status_counts["valid_decision"],
             "invalid_format_responses": status_counts["invalid_format"]}
    save(HERE / "C4_AUDIT.json", audit)
    return result


if __name__ == "__main__":
    result = analyze()
    print(json.dumps({"status": result["status"],
                      "campaigns": result.get("campaigns"),
                      "physical_calls": result.get("physical_provider_attempts",
                                                    result.get("physical_calls")),
                      "primary_mean_difference":
                          result.get("comparisons", {}).get("bandit_thompson", {}).get(
                              "paired_mean_difference_H50")}, ensure_ascii=False))
