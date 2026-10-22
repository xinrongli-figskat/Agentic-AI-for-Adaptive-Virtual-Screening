"""D6-B1: lock prompt variants and an entirely synthetic state library.

No provider request is made by this script.  The state records contain only
synthetic compound keys and synthetic outcomes, never a key from either pool.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/driveA/xinrong/agentic-screening")
BASE = ROOT / "outputs/d6_20261020/b_menu_description"
MENU = ["knn_greedy", "knn_diverse", "uniform_random", "persistent_random_until_first_hit",
        "diverse_random_coldstart", "logreg_greedy", "ens_one_step_proxy"]
V0 = {
    "knn_greedy": "Frozen weighted kNN; pick highest predicted hit scores.",
    "knn_diverse": "Frozen weighted kNN plus 0.2 Tanimoto batch-diversity penalty; old definition unchanged.",
    "uniform_random": "Seeded random selection without replacement for this batch.",
    "persistent_random_until_first_hit": "Commit to random batches while no hit is known; resume choosing after first hit.",
    "diverse_random_coldstart": "Random for a zero-hit state; otherwise frozen kNN-diverse. No commitment.",
    "logreg_greedy": "Second model: logistic regression fitted only to revealed Morgan features; random if single class.",
    "ens_one_step_proxy": "Bounded one-step 0/1-fantasy lookahead with weighted-kNN posterior approximation.",
}
V1 = {
    "knn_greedy": "knn_greedy. Select candidates with the highest frozen weighted-kNN hit scores. With zero revealed hits, use this same scoring rule.",
    "knn_diverse": "knn_diverse. Select candidates by frozen weighted-kNN score after the diversity penalty. With zero revealed hits, use this same scoring rule.",
    "uniform_random": "uniform_random. Select a seeded uniform random batch without replacement. With zero revealed hits, use seeded random selection.",
    "persistent_random_until_first_hit": "persistent_random_until_first_hit. Select seeded random batches until the first revealed hit, then return control to the menu. With zero revealed hits, continue seeded random selection.",
    "diverse_random_coldstart": "diverse_random_coldstart. Select seeded random batches at zero hits, otherwise use frozen kNN-diverse. With zero revealed hits, use seeded random selection.",
    "logreg_greedy": "logreg_greedy. Select by a logistic model fitted only to revealed Morgan features. With zero revealed hits, use seeded random selection.",
    "ens_one_step_proxy": "ens_one_step_proxy. Select by bounded one-step 0/1-fantasy weighted-kNN lookahead. With zero revealed hits, use the same lookahead rule.",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def save(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def real_keys() -> set[str]:
    from outputs.d5_20261020.e_menu import run_extended
    tnap, _ = run_extended.load_pool("tnap")
    dyrk3, _ = run_extended.load_pool("dyrk3")
    return {row["compound_key"] for row in tnap + dyrk3}


def state(identifier: int, n: int, hit_count: int) -> dict:
    keys = [f"SYN_D6B_{identifier:03d}_{i:03d}" for i in range(462)]
    revealed = [{"compound_key": key, "outcome": int(i < hit_count)} for i, key in enumerate(keys[:n])]
    return {
        "state_id": f"synthetic_{identifier:03d}", "synthetic_only": True,
        "candidate_pool": [{"compound_key": key, "standardized_smiles": ""} for key in keys],
        "revealed": revealed, "queried_count": n, "remaining_budget": 50 - n,
        "next_round": n // 10, "next_batch_size": 10, "closed": False,
        "numerical_summary": {"synthetic_state": True, "no_structure_or_real_pool_data": True},
    }


def main() -> None:
    if (BASE / "variant_lock.json").exists() or (BASE / "synthetic_states.json").exists():
        raise SystemExit("Refusing to overwrite an existing B1 lock")
    variants = {
        "V0": {"menu_order": MENU, "policy_descriptions": V0,
               "statement": "D5 descriptions copied byte-for-byte."},
        "V1": {"menu_order": MENU, "policy_descriptions": V1,
               "statement": "Neutral templates: name, selection rule, and zero-hit behavior only."},
        "V2": {"menu_order": ["persistent_random_until_first_hit"] + [p for p in MENU if p != "persistent_random_until_first_hit"],
               "policy_descriptions": V0,
               "statement": "V0 descriptions copied byte-for-byte; only the locked menu order changes."},
    }
    states = []
    identifier = 0
    for n in (10, 20, 30, 40):
        for _ in range(15):
            states.append(state(identifier, n, 0)); identifier += 1
    for hit_count, repetitions in ((1, 8), (3, 8), (6, 7), (10, 7)):
        n = 20 if hit_count <= 3 else 30
        for _ in range(repetitions):
            states.append(state(identifier, n, hit_count)); identifier += 1
    assert len(states) == 90 and identifier == 90
    assert all(s["remaining_budget"] in (10, 20, 30, 40) for s in states)
    synthetic = {r["compound_key"] for s in states for r in s["candidate_pool"]}
    overlap = sorted(synthetic & real_keys())
    assert not overlap, overlap[:3]
    lock = {"task": "D6-B1", "locked_at_utc": utc(), "post_exposure": True,
            "variants": variants,
            "probe_gate": {"metric": "persistent_random_until_first_hit zero-hit selection rate",
                            "enter_B4_if": "max(V1, V2) - V0 >= 0.15"},
            "synthetic_state_design": {"count": 90, "zero_hit": 60, "has_hit": 30,
                                       "candidate_pool_size": 462, "real_key_overlap": 0}}
    save(BASE / "variant_lock.json", lock)
    save(BASE / "synthetic_states.json", {"task": "D6-B1", "post_exposure": True,
                                            "states": states})
    hashes = {p.name: sha(p) for p in (BASE / "variant_lock.json", BASE / "synthetic_states.json")}
    save(BASE / "b1_lock_receipt.json", {"locked_at_utc": utc(), "sha256": hashes,
                                          "synthetic_real_key_overlap": 0})
    print(json.dumps({"variants": list(variants), "state_count": len(states), "sha256": hashes}, ensure_ascii=False))


if __name__ == "__main__":
    main()
