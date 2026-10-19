"""Hard-gated D2-2 preflight. Runs one synthetic GLM probe, no real labels."""
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/driveA/xinrong/agentic-screening")
ATTEMPT = ROOT / "outputs/d2_controls_20261019/attempt2_20261019"
OUT = ATTEMPT / "d2_preflight"
FROZEN = ROOT / "data/curation_private/frozen_dyrk3_v1"
EXPECTED_SPEC = "6d7d54a8ae84a53916f151c74249451d486993ccd6e7814818c1d18df126951a"
EXPECTED_D2_MANIFEST = "3cb895e3fe9a18ddfc17d91564cd0103febc90861e13d4f139e03328011b40ac"
EXPECTED_FROZEN = "3866c7bfc99e92b8e0d6f92b98955d5e68a7ae202f609eac90d0e7a201f98235"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def check_v1_hashes():
    log = (ROOT / "data/curation_private/r5_matched_order_private_20261018/RUN_LOG.md").read_text()
    references = {}
    for rep in ("bit", "count"):
        for seed in range(5):
            path = ROOT / f"data/curation_private/runs_dyrk3_v1/llm_{rep}_seed{seed}/run.json"
            match = re.search(re.escape(str(path)) + r": ([0-9a-f]{64})", log)
            assert match, f"Missing preregistered old-run hash: {rep} {seed}"
            actual = sha(path)
            assert actual == match.group(1), f"Old GLM run changed: {rep} {seed}"
            saved = json.loads(path.read_text())
            assert saved["status"] == "complete" and saved["result"]["queried_count"] == 50
            references[f"{rep}_seed{seed}"] = actual
    return references


def manifest(directory):
    rows = []
    for path in sorted(directory.iterdir()):
        if path.is_file() and path.name != "MANIFEST.json":
            rows.append({"path": path.name, "sha256": sha(path), "bytes": path.stat().st_size})
    write_json(directory / "MANIFEST.json", {"files": rows, "self_excluded": True})


def main():
    OUT.mkdir(parents=True, exist_ok=False)
    assert (ATTEMPT / "STATUS").read_text().strip() == "done"
    assert sha(ATTEMPT / "d2_rule_adaptive_private_20261019/MANIFEST.json") == EXPECTED_D2_MANIFEST
    regression = json.loads((ATTEMPT / "d2_rule_adaptive_private_20261019/regression_protection.json").read_text())
    assert regression == {"existing_rows_recomputed_identical": 280,
                          "v1_fixed_random_0_4_exact_replays": 20,
                          "synthetic_boundary_tests": "passed",
                          "label_shuffle_model_sees_permuted": True,
                          "label_shuffle_true_evaluation_separate": True,
                          "source_hashes_unchanged": True}
    trigger = json.loads((ATTEMPT / "d2_rule_adaptive_private_20261019/trigger_report.json").read_text())
    assert trigger["bit"]["first_trigger_round_distribution"] == {"3": 6, "4": 4}
    assert trigger["count"]["first_trigger_round_distribution"] == {"2": 2, "3": 7, "4": 5}
    assert sha(ROOT / "outputs/d2_controls_20261019/d2_rule_adaptive_spec.md") == EXPECTED_SPEC
    assert sha(FROZEN / "manifest.json") == EXPECTED_FROZEN
    lock = json.loads((ATTEMPT / "pre_real_declarations_lock.json").read_text())
    for row in lock["files"]:
        assert sha(ROOT / row["path"]) == row["sha256"], row["path"]
    frozen = json.loads((FROZEN / "manifest.json").read_text())
    spec = frozen["campaign_spec"]
    assert {k: spec[k] for k in ("model", "thinking", "reasoning_effort", "max_output_tokens", "api_timeout_seconds", "do_sample")} == {
        "model": "glm-5.3-flash", "thinking": "enabled", "reasoning_effort": "low",
        "max_output_tokens": 1024, "api_timeout_seconds": 120, "do_sample": False}
    assert spec["policies"] == ["knn_greedy", "knn_diverse", "uniform_random"]
    module_hashes = {}
    for name in ("glm_api.py", "llm_controller.py", "campaign_core.py", "numerical_tools.py"):
        current = ROOT / "campaign_v0" / name
        snapshot = FROZEN / "source_snapshot/campaign_v0" / name
        expected = frozen["source_sha256"][str(current)]
        module_hashes[name] = {"current_sha256": sha(current),
                               "v1_frozen_sha256": expected,
                               "v1_snapshot_sha256": sha(snapshot),
                               "identical": sha(current) == sha(snapshot) == expected}
    parity = {"checked_utc": utc(), "frozen_manifest_sha256": EXPECTED_FROZEN,
              "module_hashes": module_hashes, "frozen_request_spec": spec,
              "prompt_and_request_config_identical": all(x["identical"] for x in module_hashes.values())}
    write_json(OUT / "prompt_config_parity.json", parity)
    assert parity["prompt_and_request_config_identical"], "Frozen prompt or request-config source differs"
    old = check_v1_hashes()
    write_json(OUT / "old_glm_run_hashes.json", old)
    # The existing probe uses the exact frozen adapter and prompt builder, with synthetic labels only.
    sys.path.insert(0, str(ROOT))
    from campaign_v0.glm_api import OfficialGLMDecisionClient
    from campaign_v0.llm_controller import ToolChoiceLLMController
    from campaign_v0.numerical_tools import NumericalTools

    client = OfficialGLMDecisionClient(model_name="glm-5.3-flash")
    controller = ToolChoiceLLMController(client, model_name="glm-5.3-flash")
    state = {"candidate_pool": [{"compound_key": "synthetic_" + str(i).zfill(3),
                                  "standardized_smiles": "C" * (i + 1)} for i in range(1, 7)],
             "revealed": [{"compound_key": "synthetic_001", "outcome": 0}],
             "queried_count": 1, "remaining_budget": 4, "next_round": 1,
             "next_batch_size": 1}
    state["numerical_summary"] = NumericalTools(state["candidate_pool"]).describe_state(state)
    started = time.perf_counter()
    decision = controller.choose(state, tuple(spec["policies"]))
    elapsed = time.perf_counter() - started
    probe = {"probe_only": True, "uses_real_labels": False, "checked_utc": utc(),
             "request_succeeded": True, "model": client.model_name,
             "policy": decision["policy"], "request_id": client.last_request_id,
             "usage": client.last_usage, "decision_seconds_including_retries": elapsed,
             "api_attempt_log": client.last_attempt_log}
    assert probe["request_id"] and probe["policy"] in spec["policies"]
    write_json(OUT / "synthetic_probe.json", probe)
    (OUT / "RUN_LOG.md").write_text(
        f"# D2-2 preflight\n\nUTC: {utc()}\nD2-1 and D2-4: passed.\n"
        f"Rule SHA-256: {EXPECTED_SPEC}\nPower declaration SHA-256: {lock['files'][1]['sha256']}\n"
        "Frozen prompt and request-config modules matched byte for byte.\n"
        "Ten old GLM run hashes matched the prior R5 log. Synthetic GLM probe succeeded.\n"
        "No real label was used by the probe and no D2-2 campaign query occurred.\n")
    (OUT / "STATUS").write_text("done\n")
    manifest(OUT)
    print(json.dumps({"status": "done", "parity": True, "probe_request_id": client.last_request_id,
                      "probe_policy": decision["policy"], "probe_attempts": len(client.last_attempt_log),
                      "manifest_sha256": sha(OUT / "MANIFEST.json")}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "BLOCKER.md").write_text(f"# D2-2 hard stop\n\nUTC: {utc()}\n"
                                        f"Error: {type(exc).__name__}: {exc}\n"
                                        "No real D2-2 GLM campaign call was made.\n")
        (OUT / "STATUS").write_text("blocked\n")
        manifest(OUT)
        raise
