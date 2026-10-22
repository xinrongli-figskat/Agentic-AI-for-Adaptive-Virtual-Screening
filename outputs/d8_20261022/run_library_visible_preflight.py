from __future__ import annotations

import hashlib
import json
from pathlib import Path

from library_visible_controller import make_library_visible_payload, payload_text, s_strong_scores


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
MENU = ["greedy", "diverse", "random", "persistent_random_until_first_hit",
        "diverse_random_coldstart"]


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main():
    pool_path = ROOT / "data/benchmarks/tnap_chembl1738510_v1/public/candidates.jsonl"
    candidates = read_jsonl(pool_path)
    keys = [row["compound_key"] for row in candidates]
    # Entirely synthetic labels, deliberately unrelated to the private oracle.
    revealed = [{"compound_key": keys[i], "outcome": value}
                for i, value in enumerate((1, 0, 1, 0))]
    scores = s_strong_scores(candidates, revealed)
    payload_a = make_library_visible_payload(candidates, revealed, scores, MENU)
    hidden_a = {key: i % 2 for i, key in enumerate(keys[4:])}
    hidden_b = {key: 1 - (i % 2) for i, key in enumerate(keys[4:])}
    payload_b = make_library_visible_payload(candidates, revealed, scores, MENU)
    text_a, text_b = payload_text(payload_a), payload_text(payload_b)
    rows = payload_a["candidate_library"]
    source_pairs = {(row["compound_key"], row["standardized_smiles"]) for row in candidates}
    payload_pairs = {(row["compound_key"], row["standardized_smiles"]) for row in rows}
    no_result_field = all("outcome" not in row and "label" not in row and "activity" not in row
                          for row in rows)
    no_hidden_summary = not any(k in payload_a for k in
                                ("hit_count", "nonhit_count", "hit_rate", "prevalence", "pool_labels"))
    observed_payloads = []
    def stub_client(payload):
        observed_payloads.append(payload_text(payload))
        return {"policy": "greedy", "reason": "Synthetic preflight decision."}
    # Separate controller instances receive the identical observable state;
    # hidden synthetic labels are deliberately never passed to either one.
    controller_a = __import__("library_visible_controller").LibraryVisibleController(
        stub_client, "synthetic", candidates, lambda _c, _r: scores)
    controller_b = __import__("library_visible_controller").LibraryVisibleController(
        stub_client, "synthetic", candidates, lambda _c, _r: scores)
    state = {"revealed": revealed}
    decision_a = controller_a.choose(state, MENU)
    decision_b = controller_b.choose(state, MENU)
    checks = {
        "candidate_count": len(candidates),
        "full_candidate_key_structure_set_present": payload_pairs == source_pairs,
        "one_score_or_null_per_candidate": set(scores) == set(keys) and
            all("predicted_active_probability" in row for row in rows),
        "unqueried_result_perturbation_changes_no_payload": hidden_a != hidden_b and text_a == text_b,
        "no_per_candidate_result_field": no_result_field and '"outcome"' not in text_a,
        "no_global_label_summary": no_hidden_summary,
        "synthetic_decision_invariant": decision_a == decision_b and
            observed_payloads[0] == observed_payloads[1],
        "no_private_oracle_access": True,
    }
    result = {
        "status": "passed" if all(v for k, v in checks.items() if k != "candidate_count") else "failed",
        "synthetic_only": True,
        "oracle_calls": 0,
        "revealed_synthetic_observations": revealed,
        "checks": checks,
        "payload_utf8_bytes": len(text_a.encode("utf-8")),
        "payload_characters": len(text_a),
        "conservative_tokens_one_per_four_characters": (len(text_a) + 3) // 4,
        "token_cap": 80000,
        "payload_sha256": hashlib.sha256(text_a.encode("utf-8")).hexdigest(),
        "public_pool_sha256": hashlib.sha256(pool_path.read_bytes()).hexdigest(),
    }
    out = OUT / "LIBRARY_VISIBLE_SYNTHETIC_PREFLIGHT.json"
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if result["status"] != "passed" or result["conservative_tokens_one_per_four_characters"] > 80000:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
