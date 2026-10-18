"""One real GLM call with wholly synthetic feedback; never touches the oracle."""

import argparse
import json

from .glm_api import GLMAPIError, OfficialGLMDecisionClient
from .llm_controller import ToolChoiceLLMController
from .numerical_tools import NumericalTools


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="glm-4.7-flash")
    args = parser.parse_args()
    client = OfficialGLMDecisionClient(model_name=args.model)
    controller = ToolChoiceLLMController(client, model_name=args.model)
    state = {"candidate_pool": [{"compound_key": "synthetic_" + str(i).zfill(3),
                                  "standardized_smiles": "C" * (i + 1)} for i in range(1, 7)],
             "revealed": [{"compound_key": "synthetic_001", "outcome": 0}],
             "queried_count": 1, "remaining_budget": 4,
             "next_round": 1, "next_batch_size": 1}
    state["numerical_summary"] = NumericalTools(state["candidate_pool"]).describe_state(state)
    try:
        decision = controller.choose(state, ("knn_greedy", "knn_diverse", "uniform_random"))
    except GLMAPIError as exc:
        print(json.dumps({"probe_only": True, "uses_real_labels": False,
                          "request_succeeded": False, "model": args.model,
                          "api_error": exc.public_diagnostic()}, indent=2))
        return
    print(json.dumps({"probe_only": True, "uses_real_labels": False, "model": args.model,
                      "request_succeeded": True, "decision": decision, "usage": client.last_usage,
                      "request_id": client.last_request_id,
                      "api_attempt_log": client.last_attempt_log}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
