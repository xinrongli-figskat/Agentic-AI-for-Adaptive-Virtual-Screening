"""Narrow official Zhipu chat-completions adapter for public campaign summaries.

Only the injected summary is sent. No file, shell, retrieval, or oracle tool is
offered to the model. This module never reads a label file or prints the API key.
"""

import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


OFFICIAL_ENDPOINT = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
SYSTEM_PROMPT = (
    "You control one batch of a retrospective compound-search prototype. "
    "The user message contains only public candidate counts and already revealed binary outcomes. "
    "Choose exactly one of the allowed numerical selection policies for the next batch. "
    "Reason only from the supplied feedback. Do not claim to know candidate scores, "
    "unknown labels, or chemical details; numerical tools will choose actual compounds. "
    "State the observed hit counts relevant to your choice in one short sentence. "
    'Return only JSON: {"policy":"allowed_policy_name","reason":"brief evidence-based reason"}.'
)

ERROR_CATEGORIES = {
    "1210": "invalid_request_parameters",
    "1113": "account_payment_required",
    "1302": "account_rate_limit",
    "1305": "model_overloaded",
    "1308": "usage_limit_wait_for_reset",
    "1309": "coding_plan_expired",
    "1310": "weekly_or_monthly_limit",
    "1311": "model_not_in_subscription",
    "1313": "fair_use_restriction",
    "1314": "enterprise_plan_expired",
    "1315": "wrong_api_key_product_type",
    "1316": "five_hour_limit_and_insufficient_balance",
    "1317": "seven_day_limit_and_insufficient_balance",
    "1318": "subaccount_monthly_spending_limit",
    "1319": "subaccount_monthly_spending_limit",
    "1320": "enterprise_monthly_spending_limit",
    "1321": "enterprise_monthly_spending_limit",
}

MODEL_REQUEST_SETTINGS = {
    "glm-4.7-flash": {"thinking": {"type": "disabled"}, "max_tokens": 256},
    "glm-5.3-flash": {"thinking": {"type": "enabled"},
                      "reasoning_effort": "low", "max_tokens": 1024},
}


class GLMAPIError(RuntimeError):
    def __init__(self, http_status, business_code=None, retry_after_seconds=None,
                 category_override=None):
        self.http_status = http_status
        self.business_code = business_code
        self.category = category_override or ERROR_CATEGORIES.get(business_code,
                                                                   "unclassified_api_error")
        self.retry_after_seconds = retry_after_seconds
        self.attempt_log = []
        self.decision_seconds = None
        status = f"HTTP {http_status}" if http_status is not None else self.category
        super().__init__(f"GLM API {status}, business code {business_code or 'unavailable'}; "
                         "no new oracle query was made for this decision")

    def public_diagnostic(self):
        return {"http_status": self.http_status, "business_code": self.business_code,
                "category": self.category, "retry_after_seconds": self.retry_after_seconds,
                "attempt_log": self.attempt_log}


def parse_http_error(exc):
    """Extract only allowlisted diagnostics; never echo provider text or credentials."""
    try:
        payload = json.loads(exc.read().decode("utf-8"))
        raw_code = payload.get("error", {}).get("code")
        code = str(raw_code) if str(raw_code).isdigit() else None
    except (ValueError, AttributeError, UnicodeDecodeError):
        code = None
    retry_header = exc.headers.get("Retry-After") if exc.headers else None
    retry_after = int(retry_header) if retry_header and retry_header.isdigit() else None
    return GLMAPIError(exc.code, code, retry_after)


class OfficialGLMDecisionClient:
    def __init__(self, *, model_name="glm-4.7-flash", api_key=None, timeout_seconds=None,
                 opener=urlopen, sleeper=time.sleep):
        if model_name not in MODEL_REQUEST_SETTINGS:
            raise ValueError("Model has no reviewed request settings")
        self.model_name = model_name
        self._api_key = api_key or os.environ.get("ZAI_API_KEY")
        if not self._api_key:
            raise ValueError("ZAI_API_KEY is not set")
        self._timeout = timeout_seconds if timeout_seconds is not None else (
            120 if model_name == "glm-5.3-flash" else 60)
        self._opener = opener
        self._sleeper = sleeper
        self.last_usage = None
        self.last_request_id = None
        self.last_attempt_log = []

    def __call__(self, public_summary):
        if not isinstance(public_summary, dict) or "allowed_policies" not in public_summary:
            raise ValueError("Expected a public policy-choice summary")
        payload = {"model": self.model_name,
                   "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                                {"role": "user", "content": json.dumps(public_summary,
                                                                         ensure_ascii=False,
                                                                         sort_keys=True)}],
                   "response_format": {"type": "json_object"},
                   "do_sample": False,
                   "stream": False}
        payload.update(MODEL_REQUEST_SETTINGS[self.model_name])
        request = Request(OFFICIAL_ENDPOINT,
                          data=json.dumps(payload).encode("utf-8"),
                          headers={"Authorization": "Bearer " + self._api_key,
                                   "Content-Type": "application/json"},
                          method="POST")
        self.last_usage = None
        self.last_request_id = None
        self.last_attempt_log = []
        for attempt in range(3):
            try:
                with self._opener(request, timeout=self._timeout) as response:
                    result = json.loads(response.read().decode("utf-8"))
                self.last_attempt_log.append({"http_status": 200, "business_code": None})
                break
            except HTTPError as exc:
                error = parse_http_error(exc)
                self.last_attempt_log.append({"http_status": error.http_status,
                                              "business_code": error.business_code})
                if error.business_code == "1305" and attempt < 2:
                    self._sleeper((5, 15)[attempt])
                    continue
                error.attempt_log = list(self.last_attempt_log)
                raise error from exc
            except TimeoutError as exc:
                self.last_attempt_log.append({"http_status": None, "business_code": None,
                                              "transport_error": "timeout"})
                error = GLMAPIError(None, category_override="request_timeout")
                error.attempt_log = list(self.last_attempt_log)
                raise error from exc
            except URLError as exc:
                category = ("request_timeout" if isinstance(exc.reason, TimeoutError)
                            else "connection_failed")
                self.last_attempt_log.append({"http_status": None, "business_code": None,
                                              "transport_error": category})
                error = GLMAPIError(None, category_override=category)
                error.attempt_log = list(self.last_attempt_log)
                raise error from exc
        self.last_usage = result.get("usage")
        self.last_request_id = result.get("id")
        try:
            return result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError("GLM API response lacks message content") from exc
