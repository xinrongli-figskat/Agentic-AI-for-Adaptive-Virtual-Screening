"""Run D2-2 GLM seed 5–19, reusing frozen v1 modules without modifying them.

The private directory stores revealed labels. Never pass a path or a private
record to the LLM; the unchanged frozen controller builds its public summary.
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/driveA/xinrong/agentic-screening")
sys.path.insert(0, str(ROOT))

from campaign_v0.campaign_core import run_campaign
from campaign_v0.glm_api import GLMAPIError, OfficialGLMDecisionClient
from campaign_v0.llm_controller import ToolChoiceLLMController
from oracle_boundary_v0.oracle_boundary import BatchOracle, read_jsonl
from d2_protected_hashes import snapshot as protected_snapshot

ATTEMPT = ROOT / "outputs/d2_controls_20261019/attempt2_20261019"
PREFLIGHT = ATTEMPT / "d2_preflight"
OUT = ROOT / "outputs/d2_controls_20261019/d2_glm_private_20261019"
FROZEN = ROOT / "data/curation_private/frozen_dyrk3_v1"
EXPECTED_FROZEN_SHA = "3866c7bfc99e92b8e0d6f92b98955d5e68a7ae202f609eac90d0e7a201f98235"
EXPECTED_PREFLIGHT_SHA = "cce3b4eca1a4e83701ae404847db27fd39a55a8577b665e20db1b3764ca35513"
EXPECTED_PROTECTED_BASELINE_SHA = "b787a45fa83315b681a485d135b6988a03b003c94498d8ce64e6da448ed20717"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    tmp.replace(path)


def check_preflight():
    baseline = ATTEMPT / "d2_2_protected_baseline.json"
    assert sha(baseline) == EXPECTED_PROTECTED_BASELINE_SHA
    assert protected_snapshot() == json.loads(baseline.read_text())["files"]
    assert (PREFLIGHT / "STATUS").read_text().strip() == "done"
    assert sha(PREFLIGHT / "MANIFEST.json") == EXPECTED_PREFLIGHT_SHA
    for row in json.loads((PREFLIGHT / "MANIFEST.json").read_text())["files"]:
        path = PREFLIGHT / row["path"]
        assert path.is_file() and sha(path) == row["sha256"]
    parity = json.loads((PREFLIGHT / "prompt_config_parity.json").read_text())
    assert parity["prompt_and_request_config_identical"]
    assert sha(FROZEN / "manifest.json") == EXPECTED_FROZEN_SHA
    frozen = json.loads((FROZEN / "manifest.json").read_text())
    for name in ("glm_api.py", "llm_controller.py", "campaign_core.py", "numerical_tools.py"):
        current = ROOT / "campaign_v0" / name
        assert sha(current) == frozen["source_sha256"][str(current)]
    lock = json.loads((ATTEMPT / "pre_real_declarations_lock.json").read_text())
    for row in lock["files"]:
        assert sha(ROOT / row["path"]) == row["sha256"]
    spec = frozen["campaign_spec"]
    assert spec["model"] == "glm-5.3-flash" and spec["total_budget"] == 50
    assert spec["initialization_queries"] == 10 and spec["batch_size"] == 10
    assert spec["representations"] == ["bit", "count"]
    return frozen


class JournalledController:
    """Write a successful decision before selection, to avoid duplicate GLM calls."""
    name = "llm_policy_choice"

    def __init__(self, model, pending_path):
        self.client = OfficialGLMDecisionClient(model_name=model)
        self.base = ToolChoiceLLMController(self.client, model_name=model)
        self.pending_path = pending_path
        self.decision_log = []

    def choose(self, state, allowed):
        marker = {"next_round": state["next_round"],
                  "revealed_compounds": [r["compound_key"] for r in state["revealed"]],
                  "revealed_outcomes": [r["outcome"] for r in state["revealed"]]}
        state_sha = hashlib.sha256(json.dumps(marker, sort_keys=True).encode()).hexdigest()
        if self.pending_path.exists():
            pending = json.loads(self.pending_path.read_text())
            assert pending["state_sha256"] == state_sha, "Pending decision state changed"
            assert pending["decision"]["policy"] in allowed
            self.decision_log.append(pending["llm_call"])
            return pending["decision"]
        try:
            decision = self.base.choose(state, allowed)
        except Exception as exc:
            atomic_json(self.pending_path.parent / "failed_decision.json", {
                "at_utc": utc(), "state_sha256": state_sha,
                "error_type": type(exc).__name__,
                "api_attempt_log": self.client.last_attempt_log,
                "api_request_id": self.client.last_request_id,
                "api_usage": self.client.last_usage,
                "decision_seconds": getattr(exc, "decision_seconds", None)})
            raise
        llm_call = self.base.decision_log[-1]
        atomic_json(self.pending_path, {"created_utc": utc(), "state_sha256": state_sha,
                                        "decision": decision, "llm_call": llm_call})
        self.decision_log.append(llm_call)
        return decision


def manifest(directory):
    entries = []
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.name != "MANIFEST.json":
            entries.append({"path": path.relative_to(directory).as_posix(),
                            "bytes": path.stat().st_size, "sha256": sha(path)})
    atomic_json(directory / "MANIFEST.json", {"files": entries, "self_excluded": True})


def initialize_out():
    if OUT.exists():
        return
    OUT.mkdir(parents=True, mode=0o700)
    os.chmod(OUT, 0o700)
    (OUT / "runs").mkdir(mode=0o700)
    (OUT / "STATUS").write_text("in_progress\n")
    (OUT / "RUN_LOG.md").write_text(
        f"# D2-2 GLM extension\n\nFirst real-call run started UTC: {utc()}\n"
        f"Frozen manifest SHA-256: {EXPECTED_FROZEN_SHA}\n"
        f"Preflight manifest SHA-256: {EXPECTED_PREFLIGHT_SHA}\n"
        "The old 10 GLM runs are referenced read-only. New seeds: 5–19, bit/count.\n"
        "Budget: 120 successful decision slots, four per new run.\n"
        "Failures checkpoint before oracle queries. No model substitution.\n")


def run_one(frozen, seed, rep):
    assert seed in range(5, 20) and rep in ("bit", "count")
    spec = frozen["campaign_spec"]
    run_dir = OUT / "runs" / f"llm_{rep}_seed{seed}"
    run_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(run_dir, 0o700)
    run_path, pending_path = run_dir / "run.json", run_dir / "pending_decision.json"
    identity = {"frozen_manifest_sha256": EXPECTED_FROZEN_SHA,
                "preflight_manifest_sha256": EXPECTED_PREFLIGHT_SHA,
                "controller": "llm_policy_choice", "representation": rep, "seed": seed}
    if run_path.exists():
        saved = json.loads(run_path.read_text())
        assert all(saved.get(k) == v for k, v in identity.items())
        if saved["status"] == "complete":
            assert not pending_path.exists(), "Completed run has pending decision"
            return saved["result"]
        trajectory = saved["trajectory"]
        prior_feature_seconds = saved["feature_build_seconds"]
    else:
        trajectory, prior_feature_seconds = [], 0.0
    assert len(trajectory) <= 4
    if pending_path.exists():
        pending = json.loads(pending_path.read_text())
        assert pending["llm_call"]["api_request_id"], "Pending decision lacks request ID"
        assert pending["decision"]["policy"] in spec["policies"]
    public = read_jsonl(Path(frozen["public_dir"]) / "candidates.jsonl")
    private = read_jsonl(Path(frozen["private_dir"]) / "oracle_labels.jsonl")
    labels = {row["compound_key"]: row["outcome"] for row in private}
    assert len(public) == len(labels) == 231 and sum(labels.values()) == 116
    oracle = BatchOracle(public, labels, seed=seed, total_budget=50,
                         initialization_queries=10, batch_size=10)
    controller = JournalledController(spec["model"], pending_path)

    def checkpoint(rows, feature_seconds):
        atomic_json(run_path, {**identity, "status": "in_progress", "trajectory": rows,
                               "feature_build_seconds": feature_seconds,
                               "updated_utc": utc()})
        os.chmod(run_path, 0o600)
        if pending_path.exists():
            pending_path.unlink()

    try:
        result = run_campaign(public, oracle, controller, seed=seed, representation=rep,
                              existing_trajectory=trajectory, on_checkpoint=checkpoint,
                              prior_feature_seconds=prior_feature_seconds)
    except Exception as exc:
        event = {"at_utc": utc(), "error_type": type(exc).__name__,
                 "public_api_diagnostic": exc.public_diagnostic() if isinstance(exc, GLMAPIError) else None,
                 "decision_seconds": exc.decision_seconds if isinstance(exc, GLMAPIError) else None,
                 "completed_batches": len(json.loads(run_path.read_text())["trajectory"]) if run_path.exists() else 0,
                 "pending_successful_decision": pending_path.exists()}
        history_path = run_dir / "failure_events.json"
        history = json.loads(history_path.read_text()) if history_path.exists() else []
        history.append(event)
        atomic_json(history_path, history)
        atomic_json(run_dir / "last_error.json", event)
        raise
    assert result["queried_count"] == 50 and len(result["trajectory"]) == 5
    assert len({key for row in result["trajectory"] for key in row["selection"]}) == 50
    assert sum(labels[key] for row in result["trajectory"] for key in row["selection"]) == result["hits_at_budget"]
    assert all(row["llm_call"]["decision"]["policy"] == row["decision"]["policy"]
               for row in result["trajectory"][1:])
    atomic_json(run_path, {**identity, "status": "complete", "result": result,
                           "updated_utc": utc()})
    os.chmod(run_path, 0o600)
    assert not pending_path.exists()
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--representation", choices=("bit", "count"), required=True)
    parser.add_argument("--seed-start", type=int, required=True)
    parser.add_argument("--seed-stop", type=int, required=True, help="Exclusive")
    args = parser.parse_args()
    assert 5 <= args.seed_start < args.seed_stop <= 20
    frozen = check_preflight()
    initialize_out()
    if not os.environ.get("ZAI_API_KEY"):
        raise ValueError("ZAI_API_KEY not set")
    for seed in range(args.seed_start, args.seed_stop):
        result = run_one(frozen, seed, args.representation)
        print(json.dumps({"representation": args.representation, "seed": seed,
                          "hits_at_budget": result["hits_at_budget"], "status": "complete"}), flush=True)
    manifest(OUT)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        if OUT.exists():
            (OUT / "STATUS").write_text("paused_failure\n")
            manifest(OUT)
        raise
