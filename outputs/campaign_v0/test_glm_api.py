"""Offline contract tests; they do not contact a real GLM service."""

import json
import io
import unittest
from urllib.error import HTTPError, URLError

from .glm_api import GLMAPIError, OFFICIAL_ENDPOINT, OfficialGLMDecisionClient
from .llm_controller import ToolChoiceLLMController


class FakeHTTPResponse:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return json.dumps({"id": "fake_request", "usage": {"total_tokens": 42},
                           "choices": [{"message": {"content":
                                        '{"policy":"knn_diverse","reason":"low recent recovery"}'}}]}).encode()


class GLMAdapterTest(unittest.TestCase):
    def test_only_public_summary_sent_to_official_endpoint(self):
        inspected = []

        def fake_opener(request, *, timeout):
            inspected.append((request, timeout))
            return FakeHTTPResponse()

        client = OfficialGLMDecisionClient(api_key="test_key_not_real", opener=fake_opener)
        controller = ToolChoiceLLMController(client, model_name="glm-4.7-flash")
        state = {"candidate_pool": [{"compound_key": "x", "standardized_smiles": "CC"},
                                     {"compound_key": "y", "standardized_smiles": "CCC"}],
                 "revealed": [{"compound_key": "x", "outcome": 0}], "queried_count": 1,
                 "remaining_budget": 1, "next_round": 1, "next_batch_size": 1}
        decision = controller.choose(state, ("knn_greedy", "knn_diverse", "uniform_random"))
        self.assertEqual(decision["policy"], "knn_diverse")
        request, timeout = inspected[0]
        self.assertEqual(request.full_url, OFFICIAL_ENDPOINT)
        self.assertEqual(timeout, 60)
        body = json.loads(request.data)
        sent = json.loads(body["messages"][1]["content"])
        self.assertEqual(sent["recent_observations"], [{"compound_key": "x", "outcome": 0}])
        self.assertNotIn("candidate_pool", sent)
        self.assertNotIn("private_labels", sent)
        self.assertEqual(body["response_format"], {"type": "json_object"})
        self.assertFalse(body["do_sample"])
        self.assertEqual(body["thinking"], {"type": "disabled"})
        self.assertEqual(body["max_tokens"], 256)
        self.assertEqual(controller.decision_log[0]["api_usage"], {"total_tokens": 42})

    def test_429_business_code_distinguishes_rate_limit_from_other_causes(self):
        def fake_opener(request, *, timeout):
            body = io.BytesIO(b'{"error":{"code":"1302","message":"private provider text"}}')
            raise HTTPError(request.full_url, 429, "Too Many Requests",
                            {"Retry-After": "60"}, body)

        client = OfficialGLMDecisionClient(api_key="test_key_not_real", opener=fake_opener)
        with self.assertRaises(GLMAPIError) as caught:
            client({"allowed_policies": ["knn_greedy"]})
        self.assertEqual(caught.exception.public_diagnostic(),
                         {"http_status": 429, "business_code": "1302",
                          "category": "account_rate_limit", "retry_after_seconds": 60,
                          "attempt_log": [{"http_status": 429, "business_code": "1302"}]})
        self.assertNotIn("private provider text", str(caught.exception))
        self.assertNotIn("test_key_not_real", str(caught.exception))

    def test_5_3_flash_uses_its_supported_thinking_settings(self):
        requests = []

        def fake_opener(request, *, timeout):
            requests.append((json.loads(request.data), timeout))
            return FakeHTTPResponse()

        client = OfficialGLMDecisionClient(model_name="glm-5.3-flash",
                                            api_key="test_key_not_real", opener=fake_opener)
        client({"allowed_policies": ["knn_greedy"]})
        body, timeout = requests[0]
        self.assertEqual(timeout, 120)
        self.assertEqual(body["model"], "glm-5.3-flash")
        self.assertEqual(body["thinking"], {"type": "enabled"})
        self.assertEqual(body["reasoning_effort"], "low")
        self.assertEqual(body["max_tokens"], 1024)
        self.assertEqual(body["response_format"], {"type": "json_object"})
        self.assertFalse(body["do_sample"])

    def test_unreviewed_model_is_rejected_before_request(self):
        with self.assertRaisesRegex(ValueError, "reviewed request settings"):
            OfficialGLMDecisionClient(model_name="unreviewed-model", api_key="test_key_not_real")

    def test_1305_retries_same_request_with_bounded_waits(self):
        attempts, waits, bodies = [], [], []

        def fake_opener(request, *, timeout):
            attempts.append(timeout)
            bodies.append(request.data)
            if len(attempts) < 3:
                raise HTTPError(request.full_url, 429, "Too Many Requests", {},
                                io.BytesIO(b'{"error":{"code":"1305"}}'))
            return FakeHTTPResponse()

        client = OfficialGLMDecisionClient(api_key="test_key_not_real", opener=fake_opener,
                                            sleeper=waits.append)
        client({"allowed_policies": ["knn_greedy"]})
        self.assertEqual(attempts, [60, 60, 60])
        self.assertEqual(waits, [5, 15])
        self.assertEqual(len(set(bodies)), 1)
        self.assertEqual([row["business_code"] for row in client.last_attempt_log],
                         ["1305", "1305", None])

    def test_1305_exhaustion_returns_attempt_history(self):
        waits = []

        def fake_opener(request, *, timeout):
            raise HTTPError(request.full_url, 429, "Too Many Requests", {},
                            io.BytesIO(b'{"error":{"code":"1305"}}'))

        client = OfficialGLMDecisionClient(api_key="test_key_not_real", opener=fake_opener,
                                            sleeper=waits.append)
        with self.assertRaises(GLMAPIError) as caught:
            client({"allowed_policies": ["knn_greedy"]})
        self.assertEqual(waits, [5, 15])
        self.assertEqual(len(caught.exception.attempt_log), 3)
        self.assertTrue(all(row["business_code"] == "1305"
                            for row in caught.exception.attempt_log))

    def test_socket_timeout_stops_without_retry_and_preserves_attempt(self):
        attempts, waits = [], []

        def fake_opener(request, *, timeout):
            attempts.append(timeout)
            raise TimeoutError("private network detail")

        client = OfficialGLMDecisionClient(api_key="test_key_not_real", opener=fake_opener,
                                            sleeper=waits.append)
        with self.assertRaises(GLMAPIError) as caught:
            client({"allowed_policies": ["knn_greedy"]})
        self.assertEqual(attempts, [60])
        self.assertEqual(waits, [])
        self.assertEqual(caught.exception.category, "request_timeout")
        self.assertEqual(caught.exception.attempt_log,
                         [{"http_status": None, "business_code": None,
                           "transport_error": "timeout"}])
        self.assertNotIn("private network detail", str(caught.exception))

    def test_wrapped_url_timeout_is_classified(self):
        def fake_opener(request, *, timeout):
            raise URLError(TimeoutError("private network detail"))

        client = OfficialGLMDecisionClient(api_key="test_key_not_real", opener=fake_opener)
        with self.assertRaises(GLMAPIError) as caught:
            client({"allowed_policies": ["knn_greedy"]})
        self.assertEqual(caught.exception.category, "request_timeout")
        self.assertEqual(len(caught.exception.attempt_log), 1)


if __name__ == "__main__":
    unittest.main()
