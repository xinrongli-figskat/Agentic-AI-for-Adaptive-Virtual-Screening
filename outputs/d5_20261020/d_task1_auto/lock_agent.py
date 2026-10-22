"""Seal D5 Task 1 code, packet, and protocol before any GLM request."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILES = ("agent_protocol.json", "inputs_locked.json", "input_lock.json",
         "evidence_inputs.json", "gates.py", "run_agent.py", "test_gates.py")


def main():
    if (HERE / "progress.json").exists() or (HERE / "llm_receipts").exists():
        raise ValueError("Agent already started; cannot relock code or inputs")
    files = {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest() for name in FILES}
    result = {"locked_at_utc": datetime.now(timezone.utc).isoformat(),
              "file_sha256": files, "api_calls_before_lock": 0,
              "scope": "six fixed reference assays; no seventh candidate",
              "human_verdicts_in_prompt": False}
    (HERE / "agent_lock.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
