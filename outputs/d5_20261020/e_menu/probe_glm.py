"""One synthetic D5 menu probe; no real pool or oracle labels are loaded."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path("/driveA/xinrong/agentic-screening")
sys.path.insert(0, str(ROOT))
from campaign_v0.glm_api import OfficialGLMDecisionClient
from outputs.d5_20261020.e_menu.expanded_tools import MENU
from outputs.d5_20261020.e_menu.run_extended import BASE, DESCRIPTIONS, sha, utc, validate_sources


SUMMARY = {
    "task": "Synthetic-only menu schema test; choose one numerical policy.",
    "candidate_count": 20,
    "queried_count": 10,
    "remaining_budget": 10,
    "next_round": 1,
    "revealed_hits": 0,
    "recent_revealed_hits": 0,
    "numerical_summary": {"unqueried_count": 10, "predicted_hit_score_min": 0.1,
                          "predicted_hit_score_median": 0.2, "predicted_hit_score_max": 0.3},
    "allowed_policies": list(MENU),
    "policy_descriptions": DESCRIPTIONS,
    "commitment_note": "Synthetic test only; no real labels supplied.",
}


class Response:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps({"id": "synthetic-mock", "usage": {"total_tokens": 0},
                           "choices": [{"message": {"content":
                               '{"policy":"uniform_random","reason":"synthetic schema"}'}}]}).encode()


def main():
    validate_sources()
    captured = []

    def opener(request, timeout):
        captured.append(json.loads(request.data.decode("utf-8")))
        return Response()

    mock = OfficialGLMDecisionClient(model_name="glm-5.3-flash", api_key="synthetic-only",
                                     opener=opener)
    json.loads(mock(SUMMARY))
    body = captured[0]
    assert body["model"] == "glm-5.3-flash" and body["do_sample"] is False
    assert body["thinking"] == {"type": "enabled"}
    assert body["reasoning_effort"] == "low" and body["max_tokens"] == 1024
    assert body["response_format"] == {"type": "json_object"}
    assert "ZAI_API_KEY" not in json.dumps(body)
    real = OfficialGLMDecisionClient(model_name="glm-5.3-flash")
    raw = real(SUMMARY)
    decision = json.loads(raw)
    assert set(decision) == {"policy", "reason"} and decision["policy"] in MENU
    result = {"utc": utc(), "probe_only": True, "uses_real_labels": False,
              "model": "glm-5.3-flash", "request_succeeded": True,
              "request_settings_mock_validated": True,
              "do_sample": False, "decision": decision,
              "usage": real.last_usage, "request_id": real.last_request_id,
              "api_attempt_log": real.last_attempt_log}
    output = BASE / "e_menu_synthetic_glm_probe.json"
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"probe_only": True, "request_succeeded": True,
                      "policy": decision["policy"], "probe_sha256": sha(output)}))


if __name__ == "__main__":
    main()
