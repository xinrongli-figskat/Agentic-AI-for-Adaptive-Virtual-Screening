"""Constrained policy-choice interface; the caller supplies the LLM API client.

This module has no filesystem, network, oracle, or chemistry-data access. The
model receives a small public feedback summary and chooses one numerical tool.
"""

import json
import time


class ToolChoiceLLMController:
    name = "llm_policy_choice"

    def __init__(self, decision_client, *, model_name):
        if not callable(decision_client) or not model_name:
            raise ValueError("A callable decision client and model name are required")
        self._client = decision_client
        self.model_name = model_name
        self.decision_log = []
        self.total_decision_seconds = 0.0

    def choose(self, public_state, allowed_policies):
        revealed = public_state["revealed"]
        candidates = public_state["candidate_pool"]
        candidate_ids = [row["compound_key"] for row in candidates]
        revealed_ids = [row["compound_key"] for row in revealed]
        unqueried_count = len(candidates) - len(revealed)
        if len(candidate_ids) != len(set(candidate_ids)) or \
           len(revealed_ids) != len(set(revealed_ids)) or \
           not set(revealed_ids).issubset(candidate_ids) or \
           public_state["queried_count"] != len(revealed) or \
           public_state["next_batch_size"] <= 0 or \
           public_state["next_batch_size"] > min(unqueried_count, public_state["remaining_budget"]):
            raise ValueError("Inconsistent public campaign state; LLM was not called")
        recent = revealed[-10:]
        summary = {
            "candidate_count": len(candidates),
            "unqueried_count": unqueried_count,
            "queried_count": public_state["queried_count"],
            "remaining_budget": public_state["remaining_budget"],
            "next_round": public_state["next_round"],
            "next_batch_size": public_state["next_batch_size"],
            "revealed_hits": sum(row["outcome"] for row in revealed),
            "recent_revealed_hits": sum(row["outcome"] for row in recent),
            "recent_revealed_count": len(recent),
            "recent_observations": [{"compound_key": row["compound_key"],
                                     "outcome": row["outcome"]} for row in recent],
            "revealed_observations": [{"compound_key": row["compound_key"],
                                       "outcome": row["outcome"]} for row in revealed],
            "numerical_summary": public_state.get("numerical_summary"),
            "allowed_policies": list(allowed_policies),
            "policy_descriptions": {
                "knn_greedy": "Select the top predicted hit probabilities from observed-label kNN.",
                "knn_diverse": "Use the same kNN scores with a Tanimoto diversity penalty.",
                "uniform_random": "Choose remaining compounds uniformly without replacement.",
            },
        }
        started = time.perf_counter()
        try:
            response = self._client(summary)
        except Exception as exc:
            if hasattr(exc, "public_diagnostic"):
                exc.decision_seconds = time.perf_counter() - started
            raise
        elapsed = time.perf_counter() - started
        self.total_decision_seconds += elapsed
        if isinstance(response, str):
            response = json.loads(response)
        if not isinstance(response, dict) or set(response) != {"policy", "reason"}:
            raise ValueError("LLM decision must be JSON with exactly policy and reason")
        if response["policy"] not in allowed_policies or not isinstance(response["reason"], str) \
           or not response["reason"].strip() or len(response["reason"]) > 1000:
            raise ValueError("LLM chose an invalid policy or reason")
        decision = {"policy": response["policy"], "reason": response["reason"].strip()}
        self.decision_log.append({"model": self.model_name, "public_summary": summary,
                                  "decision": decision, "decision_seconds": elapsed,
                                  "api_usage": getattr(self._client, "last_usage", None),
                                  "api_request_id": getattr(self._client, "last_request_id", None),
                                  "api_attempt_log": getattr(self._client, "last_attempt_log", None)})
        return decision
