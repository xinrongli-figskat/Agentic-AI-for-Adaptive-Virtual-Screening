"""D8-only GLM client with a system instruction matching the visible library."""
import json
import os
from urllib.request import Request, urlopen


ENDPOINT = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
SYSTEM_PROMPT = (
    "You choose one allowed policy for a retrospective active-search run. "
    "The complete preset candidate library, public molecular structures, and "
    "current model scores are visible. Results are available only for the "
    "listed already measured active and inactive compounds. Do not infer or "
    "claim the result of any unselected compound. Select exactly one allowed "
    "policy and explain briefly using the supplied information. Return only "
    'JSON with exactly these keys: {"policy":"...","reason":"..."}.'
)


class LibraryVisibleGLMClient:
    def __init__(self, model_name="glm-5.3-flash", *, api_key=None, opener=urlopen,
                 timeout_seconds=120):
        self.model_name = model_name
        self._api_key = api_key or os.environ.get("ZAI_API_KEY")
        if not self._api_key:
            raise ValueError("ZAI_API_KEY is not set")
        self._opener = opener
        self._timeout = timeout_seconds
        self.last_usage = None
        self.last_request_id = None

    def __call__(self, payload):
        user_text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        body = {
            "model": self.model_name,
            "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                         {"role": "user", "content": user_text}],
            "response_format": {"type": "json_object"},
            "do_sample": False,
            "stream": False,
            "thinking": {"type": "enabled"},
            "reasoning_effort": "low",
            "max_tokens": 1024,
        }
        request = Request(ENDPOINT, data=json.dumps(body).encode("utf-8"),
                          headers={"Authorization": "Bearer " + self._api_key,
                                   "Content-Type": "application/json"}, method="POST")
        with self._opener(request, timeout=self._timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
        self.last_usage = result.get("usage")
        self.last_request_id = result.get("id")
        return result["choices"][0]["message"]["content"]
