"""Post-exposure D8 controller: the preset library is visible, labels are not.

This module receives only public candidate rows and outcomes already revealed
by selection. It has no private-label, filesystem, shell, or retrieval access.
"""
from __future__ import annotations

import json
import time


def make_library_visible_payload(candidates, revealed, scores, allowed_policies):
    candidates = list(candidates)
    revealed = list(revealed)
    allowed_policies = list(allowed_policies)
    if not candidates or len(allowed_policies) != 5:
        raise ValueError("Expected a nonempty library and the locked five-policy menu")
    if any(set(row) != {"compound_key", "standardized_smiles"} for row in candidates):
        raise ValueError("Candidate rows must contain only the public interface fields")
    keys = [row["compound_key"] for row in candidates]
    if len(keys) != len(set(keys)):
        raise ValueError("Candidate keys must be unique")
    if any(not isinstance(row["standardized_smiles"], str) or
           not row["standardized_smiles"].strip() for row in candidates):
        raise ValueError("Each candidate must have a nonempty standardized SMILES")
    if any(set(row) != {"compound_key", "outcome"} or
           row["outcome"] not in (0, 1) for row in revealed):
        raise ValueError("Only already revealed binary measurements are allowed")
    revealed_keys = [row["compound_key"] for row in revealed]
    if len(revealed_keys) != len(set(revealed_keys)) or not set(revealed_keys) <= set(keys):
        raise ValueError("Revealed observations must be unique members of the public library")
    if set(scores) != set(keys):
        raise ValueError("A current prediction or explicit null is required for every candidate")
    for score in scores.values():
        if score is not None and (not isinstance(score, (int, float)) or not 0 <= score <= 1):
            raise ValueError("Predicted scores must be probabilities or null")
    if len(set(allowed_policies)) != 5:
        raise ValueError("Policy names must be unique")

    active = sorted(row["compound_key"] for row in revealed if row["outcome"] == 1)
    inactive = sorted(row["compound_key"] for row in revealed if row["outcome"] == 0)
    library = []
    for row in sorted(candidates, key=lambda x: x["compound_key"]):
        library.append({"compound_key": row["compound_key"],
                        "standardized_smiles": row["standardized_smiles"],
                        "predicted_active_probability": scores[row["compound_key"]]})
    payload = {
        "task": "Choose one policy for the next batch in a retrospective active-search run.",
        "candidate_count": len(candidates),
        "queried_count": len(revealed),
        "remaining_budget": 50 - len(revealed),
        "next_batch_size": min(10, max(0, 50 - len(revealed))),
        "candidate_library": library,
        "already_measured_active_keys": active,
        "already_measured_inactive_keys": inactive,
        "allowed_policies": allowed_policies,
        "policy_descriptions": {
            "greedy": "Rank by the current measured-label model prediction and select the top batch.",
            "diverse": "Rank by the model prediction with a penalty for similarity to selected compounds.",
            "random": "Select remaining candidates uniformly without replacement.",
            "persistent_random_until_first_hit": "Select randomly until a measured active is found, then use the model ranking.",
            "diverse_random_coldstart": "Select randomly until a measured active is found, then use the diversity-penalized ranking.",
        },
        "information_boundary": (
            "The full preset candidate library and current model scores are visible. "
            "Only measurements for selected compounds are disclosed. No unselected "
            "compound's measured result or pool-wide label statistic is provided."
        ),
    }
    return payload


def payload_text(payload):
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def parse_policy(response, allowed_policies):
    if isinstance(response, str):
        response = json.loads(response)
    if (not isinstance(response, dict) or set(response) != {"policy", "reason"} or
            response.get("policy") not in allowed_policies or
            not isinstance(response.get("reason"), str) or
            not response["reason"].strip() or len(response["reason"].strip()) > 1000):
        raise ValueError("Library-visible LLM response failed the strict policy schema")
    return {"policy": response["policy"], "reason": response["reason"].strip()}


class LibraryVisibleController:
    name = "llm_library_visible"

    def __init__(self, decision_client, model_name, candidates, score_provider):
        if not callable(decision_client) or not callable(score_provider) or not model_name:
            raise ValueError("Client, model name, and score provider are required")
        self._client = decision_client
        self._score_provider = score_provider
        self.model_name = model_name
        self.candidates = list(candidates)
        self.decision_log = []

    def choose(self, public_state, allowed_policies):
        revealed = list(public_state["revealed"])
        scores = self._score_provider(self.candidates, revealed)
        payload = make_library_visible_payload(self.candidates, revealed, scores,
                                               allowed_policies)
        started = time.perf_counter()
        response = self._client(payload)
        elapsed = time.perf_counter() - started
        decision = parse_policy(response, allowed_policies)
        self.decision_log.append({"model": self.model_name, "payload": payload,
                                  "decision": decision, "decision_seconds": elapsed,
                                  "api_usage": getattr(self._client, "last_usage", None),
                                  "api_request_id": getattr(self._client, "last_request_id", None)})
        return decision


def s_strong_scores(candidates, revealed):
    """Refit the locked D7 S_strong model from revealed labels; score every row."""
    from sklearn.ensemble import GradientBoostingClassifier
    from outputs.d7_20261021.c_surrogate_factor.c1_surrogates import (
        SurrogateBank, _fill_from_training,
    )

    bank = SurrogateBank(candidates)
    observed_keys = [row["compound_key"] for row in revealed]
    if len(set(observed_keys)) != len(observed_keys) or not set(observed_keys) <= set(bank.index):
        raise ValueError("Revealed records do not match the supplied public pool")
    if any(set(row) != {"compound_key", "outcome"} or row["outcome"] not in (0, 1)
           for row in revealed):
        raise ValueError("Score fitting accepts only selected, revealed binary results")
    labels = [int(row["outcome"]) for row in revealed]
    if not labels or len(set(labels)) < 2:
        return {key: None for key in bank.keys}
    train_idx = [bank.index[key] for key in observed_keys]
    features = bank.features["S_strong"]
    x_train, x_all, _ = _fill_from_training(features[train_idx], features)
    model = GradientBoostingClassifier(n_estimators=200, max_depth=3,
                                       learning_rate=0.1, random_state=0)
    model.fit(x_train, labels)
    positive = list(model.classes_).index(1)
    probabilities = model.predict_proba(x_all)[:, positive]
    return {key: float(probabilities[bank.index[key]]) for key in bank.keys}
