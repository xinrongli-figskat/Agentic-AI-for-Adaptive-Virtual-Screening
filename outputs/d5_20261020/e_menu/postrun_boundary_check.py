"""Late synthetic-only audit of label-responsive and label-free D5 tools.

This check was omitted from the original synthetic preflight. Its timing is
recorded as a deviation; it does not retroactively change that preflight.
"""

from __future__ import annotations

import json

from outputs.d5_20261020.e_menu.expanded_tools import ExpandedTools
from outputs.d5_20261020.e_menu.preflight import public_rows
from outputs.d5_20261020.e_menu.run_extended import BASE, sha, utc, validate_sources


def make_state(rows, pattern):
    revealed = [{"compound_key": row["compound_key"], "outcome": pattern[i]}
                for i, row in enumerate(rows[:10])]
    return {"candidate_pool": rows, "revealed": revealed, "queried_count": 10,
            "remaining_budget": 40, "next_batch_size": 10, "next_round": 1}


def main():
    validate_sources()
    results = []
    for pool in ("tnap", "dyrk3"):
        rows = public_rows(pool)
        state_a = make_state(rows, [1, 0, 1, 0, 1, 0, 0, 0, 0, 0])
        state_b = make_state(rows, [0, 1, 0, 1, 0, 1, 0, 0, 0, 0])
        for rep in ("bit", "count"):
            tools = ExpandedTools(rows, rep)
            random_a = tools.select(state_a, "uniform_random", 3, 1)
            random_b = tools.select(state_b, "uniform_random", 3, 1)
            assert random_a == random_b
            score_a = tools.legacy.score_knn(state_a)
            score_b = tools.legacy.score_knn(state_b)
            changed = sum(abs(score_a[key] - score_b[key]) > 1e-12 for key in score_a)
            assert changed > 0
            results.append({"pool": pool, "representation": rep,
                            "label_free_uniform_random_invariant": True,
                            "label_responsive_knn_scores_changed": changed,
                            "public_fields_only": all(set(row) == {"compound_key", "standardized_smiles"} for row in rows),
                            "structure_prior_used_by_D5": False})
    path = BASE / "e_menu_postrun_boundary_check.json"
    value = {"utc": utc(), "status": "pass", "late_check": True,
             "preflight_not_retroactively_amended": True,
             "structure_prior_note": "No D5 menu implementation or prompt consumes a structure_prior field; its permutation test is inapplicable to this D5 version.",
             "synthetic_only": True, "results": results}
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "pass", "sha256": sha(path), "late_check": True}))


if __name__ == "__main__":
    main()
