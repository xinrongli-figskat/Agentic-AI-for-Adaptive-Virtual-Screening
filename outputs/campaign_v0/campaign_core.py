"""Feedback-batch runner that exposes only public state to controllers."""

import time

from oracle_boundary_v0.oracle_boundary import BatchOracle

from .numerical_tools import NumericalTools, POLICIES


class FixedController:
    name = "prescribed_knn_greedy"

    def choose(self, public_state, allowed_policies):
        if "knn_greedy" not in allowed_policies:
            raise ValueError("Fixed controller lost its declared tool")
        return {"policy": "knn_greedy", "reason": "Prescribed greedy kNN selection on revealed outcomes"}


class RandomController:
    name = "uniform_random_reference"

    def choose(self, public_state, allowed_policies):
        return {"policy": "uniform_random", "reason": "Prescribed label-blind random continuation"}


class SyntheticAdaptiveStub:
    """Only for dry runs; this is NOT an LLM controller."""

    name = "synthetic_adaptive_stub_not_llm"

    def choose(self, public_state, allowed_policies):
        recent = public_state["revealed"][-10:]
        fraction = sum(row["outcome"] for row in recent) / len(recent)
        policy = "knn_diverse" if fraction < 0.3 else "knn_greedy"
        return {"policy": policy, "reason": f"Synthetic feedback rule; recent hit fraction={fraction:.3f}"}


def run_campaign(candidates, oracle, controller, *, seed, representation="bit",
                 existing_trajectory=None, on_checkpoint=None, prior_feature_seconds=0.0):
    """Run through a narrow oracle; controller sees only `public_state`."""
    tools = NumericalTools(candidates, representation=representation)
    trajectory = list(existing_trajectory or [])
    for old in trajectory:
        replay = oracle.query_batch_tool({"compound_keys": old["selection"]})
        if replay["observations"] != old["observations"] or \
           sum(r["outcome"] for r in oracle.public_state()["revealed"]) != old["cumulative_hits"]:
            raise ValueError("Stored checkpoint differs from the fixed oracle outcomes")
    if not trajectory:
        first_ids = oracle.proposed_initial_ids()
        first = oracle.query_batch_tool({"compound_keys": first_ids})
        trajectory.append({"stage": "initialization", "selection": first_ids,
                           "observations": first["observations"],
                           "cumulative_hits": sum(r["outcome"] for r in first["observations"]),
                           "selection_seconds": 0.0})
        if on_checkpoint:
            on_checkpoint(trajectory, prior_feature_seconds + tools.feature_build_seconds)
    while oracle.public_state()["remaining_budget"]:
        state = oracle.public_state()
        analysis_started = time.perf_counter()
        state["numerical_summary"] = tools.describe_state(state)
        analysis_elapsed = time.perf_counter() - analysis_started
        decision = controller.choose(state, POLICIES)
        if not isinstance(decision, dict) or decision.get("policy") not in POLICIES or not decision.get("reason"):
            raise ValueError("Controller did not provide an allowed policy and rationale")
        started = time.perf_counter()
        chosen = tools.select_batch(state, policy=decision["policy"], seed=seed,
                                    round_number=state["next_round"])
        elapsed = time.perf_counter() - started
        response = oracle.query_batch_tool({"compound_keys": chosen})
        trajectory.append({"stage": "feedback_round_" + str(response["round"]),
                           "decision": decision, "information_available": {
                               "revealed_count": len(state["revealed"]),
                               "revealed_hits": sum(r["outcome"] for r in state["revealed"]),
                               "remaining_budget": state["remaining_budget"],
                               "numerical_summary": state["numerical_summary"]},
                           "llm_call": (controller.decision_log[-1] if hasattr(controller, "decision_log")
                                        and controller.decision_log else None),
                           "selection": chosen, "observations": response["observations"],
                           "cumulative_hits": sum(r["outcome"] for r in oracle.public_state()["revealed"]),
                           "selection_seconds": elapsed,
                           "analysis_seconds": analysis_elapsed})
        if on_checkpoint:
            on_checkpoint(trajectory, prior_feature_seconds + tools.feature_build_seconds)
    return {"controller": controller.name, "seed": seed, "representation": representation,
            "queried_count": len(oracle.public_state()["revealed"]),
            "hits_at_budget": trajectory[-1]["cumulative_hits"],
            "hit_recovery_checkpoints": [row["cumulative_hits"] for row in trajectory],
            "feature_build_seconds": prior_feature_seconds + tools.feature_build_seconds,
            "analysis_seconds_total": sum(row.get("analysis_seconds", 0.0) for row in trajectory),
            "selection_seconds_total": sum(row["selection_seconds"] for row in trajectory),
            "decision_seconds_total": sum(row.get("llm_call", {}).get("decision_seconds", 0.0)
                                          for row in trajectory if row.get("llm_call")),
            "trajectory": trajectory}


def run_synthetic_campaign(candidates, synthetic_labels, controller, *, seed, total_budget=50,
                           initialization_queries=10, batch_size=10, representation="bit"):
    """Dry-run a full campaign schedule with synthetic labels only."""
    oracle = BatchOracle(candidates, synthetic_labels, seed=seed, total_budget=total_budget,
                         initialization_queries=initialization_queries, batch_size=batch_size)
    return run_campaign(candidates, oracle, controller, seed=seed,
                        representation=representation)
