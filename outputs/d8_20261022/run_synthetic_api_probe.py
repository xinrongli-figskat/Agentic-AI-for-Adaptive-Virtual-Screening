from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

from library_visible_api import LibraryVisibleGLMClient
from library_visible_controller import make_library_visible_payload, parse_policy, payload_text, s_strong_scores


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
MENU = ["greedy", "diverse", "random", "persistent_random_until_first_hit",
        "diverse_random_coldstart"]
KEY_FILE = Path.home() / ".config/agentic-screening/zhipu_api_key"


def main():
    pool_path = ROOT / "data/benchmarks/tnap_chembl1738510_v1/public/candidates.jsonl"
    candidates = [json.loads(line) for line in pool_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    keys = [row["compound_key"] for row in candidates]
    revealed = [{"compound_key": keys[i], "outcome": value}
                for i, value in enumerate((1, 0, 1, 0))]
    scores = s_strong_scores(candidates, revealed)
    payload = make_library_visible_payload(candidates, revealed, scores, MENU)
    text = payload_text(payload)
    estimate = (len(text) + 3) // 4
    if estimate > 80000:
        raise SystemExit("Prompt estimate exceeded locked cap; no API request made")
    key = KEY_FILE.read_text(encoding="utf-8").strip()
    if not key:
        raise SystemExit("Configured key file is empty")
    client = LibraryVisibleGLMClient(api_key=key)
    del key
    started = time.perf_counter()
    status = "success"
    error_type = None
    error_message = None
    decision = None
    try:
        raw = client(payload)
        decision = parse_policy(raw, MENU)
    except Exception as exc:
        status = "error"
        error_type = type(exc).__name__
        error_message = str(exc)[:500]
    elapsed = time.perf_counter() - started
    receipt = {
        "status": status,
        "synthetic_only": True,
        "campaign_oracle_calls": 0,
        "model": client.model_name,
        "request_config": {"do_sample": False, "thinking": "enabled",
                           "reasoning_effort": "low", "max_tokens": 1024,
                           "timeout_seconds": 120},
        "candidate_count": len(candidates),
        "synthetic_revealed_count": len(revealed),
        "prompt_utf8_bytes": len(text.encode("utf-8")),
        "prompt_characters": len(text),
        "estimated_tokens_one_per_four_characters": estimate,
        "prompt_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "request_id": client.last_request_id,
        "usage": client.last_usage,
        "elapsed_seconds": round(elapsed, 3),
        "decision": decision,
        "error_type": error_type,
        "error": error_message,
        "api_key_recorded": False,
        "raw_response_recorded": False,
    }
    out = OUT / "LIBRARY_VISIBLE_API_PROBE.json"
    out.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, ensure_ascii=False))
    if status != "success":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
