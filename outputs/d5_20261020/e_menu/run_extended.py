"""D5 post-exposure campaign runner with a shared expanded numerical menu.

Only this runner reads a private oracle file. Controllers and numerical tools
receive public structures plus already revealed outcomes from BatchOracle.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/driveA/xinrong/agentic-screening")
sys.path.insert(0, str(ROOT))
from campaign_v0.glm_api import OfficialGLMDecisionClient
from oracle_boundary_v0.oracle_boundary import BatchOracle, read_jsonl
from outputs.d5_20261020.e_menu.expanded_tools import MENU, ExpandedTools

BASE = ROOT / "outputs/d5_20261020"
PRIVATE_OUT = BASE / "e_menu_private"
SPEC_SHA = "8c88799469e193046a404a91bf8fcfb67b71313a46c777dbe983994f87f5252d"
DYRK3_MANIFEST_SHA = "3866c7bfc99e92b8e0d6f92b98955d5e68a7ae202f609eac90d0e7a201f98235"
TNAP_RECEIPT_SHA = "f8801efbe28f73ddbcf9c5a2d493d862cbf124f311b6659e9224f2161b5bf662"

DESCRIPTIONS = {
    "knn_greedy": "Frozen weighted kNN; pick highest predicted hit scores.",
    "knn_diverse": "Frozen weighted kNN plus 0.2 Tanimoto batch-diversity penalty; old definition unchanged.",
    "uniform_random": "Seeded random selection without replacement for this batch.",
    "persistent_random_until_first_hit": "Commit to random batches while no hit is known; resume choosing after first hit.",
    "diverse_random_coldstart": "Random for a zero-hit state; otherwise frozen kNN-diverse. No commitment.",
    "logreg_greedy": "Second model: logistic regression fitted only to revealed Morgan features; random if single class.",
    "ens_one_step_proxy": "Bounded one-step 0/1-fantasy lookahead with weighted-kNN posterior approximation.",
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc():
    return datetime.now(timezone.utc).isoformat()


def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temp.replace(path)
    os.chmod(path, 0o600)


def validate_sources():
    assert sha(BASE / "d5_menu_spec.md") == SPEC_SHA
    lock = json.loads((BASE / "d5_menu_spec_lock.json").read_text())
    assert lock["spec_sha256"] == SPEC_SHA and lock["old_policies_unchanged"]
    assert sha(ROOT / "data/curation_private/frozen_dyrk3_v1/manifest.json") == DYRK3_MANIFEST_SHA
    assert sha(ROOT / "outputs/d3_tnap_20261019/freeze_tnap_v1/freeze_receipt.json") == TNAP_RECEIPT_SHA
    baseline = json.loads((BASE / "d5_baseline.json").read_text())
    for relative, expected in baseline["remote_frozen_and_legacy_hashes"].items():
        assert sha(ROOT / relative) == expected, relative
    code_lock_path = BASE / "e_menu_code_lock.json"
    assert code_lock_path.exists(), "Code must be locked before real runs"
    code_lock = json.loads(code_lock_path.read_text())
    for relative, expected in code_lock["source_sha256"].items():
        assert sha(BASE / relative) == expected, relative
    return code_lock


def load_pool(pool):
    validate_sources()
    if pool == "tnap":
        receipt = json.loads((ROOT / "outputs/d3_tnap_20261019/freeze_tnap_v1/freeze_receipt.json").read_text())
        candidate_path = Path(receipt["public_pool_path"])
        label_path = Path(receipt["private_label_path"])
        expected = {row["snapshot"]: row["sha256"] for row in receipt["files"]}
        assert sha(candidate_path) == expected[str(candidate_path)]
        assert sha(label_path) == expected[str(label_path)]
        n, hits = 462, 53
    elif pool == "dyrk3":
        manifest = json.loads((ROOT / "data/curation_private/frozen_dyrk3_v1/manifest.json").read_text())
        candidate_path = Path(manifest["public_dir"]) / "candidates.jsonl"
        label_path = Path(manifest["private_dir"]) / "oracle_labels.jsonl"
        assert sha(candidate_path) == manifest["data_sha256"]["public_candidates"]
        assert sha(label_path) == manifest["data_sha256"]["private_labels"]
        n, hits = 231, 116
    else:
        raise ValueError(pool)
    candidates = read_jsonl(candidate_path)
    labels = {row["compound_key"]: row["outcome"] for row in read_jsonl(label_path)}
    assert len(candidates) == len(labels) == n and sum(labels.values()) == hits
    assert all(set(row) == {"compound_key", "standardized_smiles"} for row in candidates)
    return candidates, labels


class Controller:
    def __init__(self, arm, seed, mix_weights=None, client=None):
        self.arm = arm
        self.seed = seed
        self.mix_weights = mix_weights
        self.client = client
        self.commit_random = False
        self.call_count = 0

    def _mixture(self, round_number):
        if self.arm == "random_mixture_extended":
            weights = [1] * len(MENU)
        else:
            assert self.arm == "matched_proportion_extended" and self.mix_weights is not None
            weights = [int(self.mix_weights.get(policy, 0)) for policy in MENU]
            assert sum(weights) > 0
        digest = hashlib.sha256(f"d5mix|{self.arm}|{self.seed}|{round_number}".encode()).digest()
        draw = int.from_bytes(digest[:8], "big") % sum(weights)
        for policy, weight in zip(MENU, weights):
            if draw < weight:
                return policy
            draw -= weight
        raise AssertionError("Mixture weights exhausted")

    def choose(self, state):
        hits = sum(row["outcome"] for row in state["revealed"])
        round_number = state["next_round"]
        if self.commit_random and hits == 0:
            return {"policy": "persistent_random_until_first_hit", "reason": "Earlier menu commitment: continue seeded random until a hit is revealed.",
                    "automatic_commitment": True}, None
        if hits:
            self.commit_random = False
        if self.arm.startswith("fixed:"):
            policy = self.arm.split(":", 1)[1]
            assert policy in MENU
            decision = {"policy": policy, "reason": "Predeclared fixed single-menu-item control."}
            call = None
        elif self.arm in ("random_mixture_extended", "matched_proportion_extended"):
            policy = self._mixture(round_number)
            decision = {"policy": policy, "reason": "Predeclared seeded shared-menu mixture."}
            call = None
        elif self.arm == "glm_extended":
            assert self.client is not None
            summary = {
                "task": "Choose one shared numerical policy for the next retrospective batch of 10.",
                "candidate_count": len(state["candidate_pool"]),
                "queried_count": state["queried_count"],
                "remaining_budget": state["remaining_budget"],
                "next_round": round_number,
                "revealed_hits": hits,
                "recent_revealed_hits": sum(row["outcome"] for row in state["revealed"][-10:]),
                "numerical_summary": state.get("numerical_summary"),
                "allowed_policies": list(MENU),
                "policy_descriptions": DESCRIPTIONS,
                "commitment_note": "If you choose persistent_random_until_first_hit with zero hits, subsequent zero-hit rounds automatically stay random; they still spend 10 oracle queries each, but no extra model call.",
            }
            started = time.perf_counter()
            raw = self.client(summary)
            elapsed = time.perf_counter() - started
            self.call_count += 1
            try:
                parsed = json.loads(raw)
                assert set(parsed) == {"policy", "reason"}
                assert parsed["policy"] in MENU
                assert isinstance(parsed["reason"], str) and 0 < len(parsed["reason"].strip()) <= 1000
            except (ValueError, TypeError, AssertionError) as exc:
                raise ValueError("Invalid D5 GLM policy JSON; no oracle query was made") from exc
            policy = parsed["policy"]
            decision = {"policy": policy, "reason": parsed["reason"].strip()}
            call = {"public_summary": summary, "raw_response": raw,
                    "usage": self.client.last_usage, "request_id": self.client.last_request_id,
                    "api_attempt_log": self.client.last_attempt_log,
                    "decision_seconds": elapsed}
        else:
            raise ValueError(self.arm)
        if policy == "persistent_random_until_first_hit" and hits == 0:
            self.commit_random = True
        return decision, call


def run_one(pool, representation, seed, arm, mix_weights=None, client=None):
    assert seed in range(20) and representation in ("bit", "count")
    if arm == "glm_extended":
        assert pool == "tnap", "GLM is authorized only for TNAP in D5"
    candidates, labels = load_pool(pool)
    oracle = BatchOracle(candidates, labels, seed=seed, total_budget=50,
                         initialization_queries=10, batch_size=10)
    tools = ExpandedTools(candidates, representation)
    controller = Controller(arm, seed, mix_weights, client)
    run_dir = PRIVATE_OUT / "runs" / pool / representation / f"{arm.replace(':', '_')}_seed{seed}"
    run_path, pending_path = run_dir / "run.json", run_dir / "pending.json"
    identity = {"pool": pool, "representation": representation, "seed": seed,
                "arm": arm, "spec_sha256": SPEC_SHA}
    if run_path.exists():
        saved = json.loads(run_path.read_text())
        assert all(saved.get(k) == value for k, value in identity.items())
        trajectory = saved["trajectory"]
        if saved.get("complete"):
            return {"pool": pool, "representation": representation, "seed": seed,
                    "arm": arm, "complete": True, "H50": saved["H50"],
                    "glm_calls": saved.get("glm_calls", 0), "already_saved": True}
        for step in trajectory:
            response = oracle.query_batch_tool({"compound_keys": step["selection"]})
            assert response["observations"] == step["observations"]
            if step.get("decision", {}).get("policy") == "persistent_random_until_first_hit" and \
                    step["decision"].get("automatic_commitment") is not True and \
                    step["information_available"]["revealed_hits"] == 0:
                controller.commit_random = True
            if sum(r["outcome"] for r in response["observations"]):
                controller.commit_random = False
        controller.call_count = saved.get("glm_calls", 0)
    else:
        trajectory = []
        first = oracle.proposed_initial_ids()
        response = oracle.query_batch_tool({"compound_keys": first})
        trajectory.append({"stage": "initialization", "selection": first,
                           "observations": response["observations"],
                           "cumulative_hits": sum(row["outcome"] for row in response["observations"])})
        save_json(run_path, {**identity, "complete": False, "trajectory": trajectory,
                             "glm_calls": 0})
    while oracle.public_state()["remaining_budget"]:
        state = oracle.public_state()
        state["numerical_summary"] = tools.legacy.describe_state(state)
        state_marker = hashlib.sha256(json.dumps({"seed": seed, "round": state["next_round"],
            "revealed": state["revealed"]}, sort_keys=True).encode()).hexdigest()
        if pending_path.exists():
            pending = json.loads(pending_path.read_text())
            assert pending["state_marker"] == state_marker
            decision, call = pending["decision"], pending["glm_call"]
            if decision["policy"] == "persistent_random_until_first_hit" and \
                    sum(row["outcome"] for row in state["revealed"]) == 0:
                controller.commit_random = True
        else:
            try:
                decision, call = controller.choose(state)
            except Exception as exc:
                error_path = run_dir / "failure_events.json"
                events = json.loads(error_path.read_text()) if error_path.exists() else []
                events.append({"utc": utc(), "error_type": type(exc).__name__,
                               "message": str(exc), "state_marker": state_marker,
                               "request_id": getattr(client, "last_request_id", None),
                               "usage": getattr(client, "last_usage", None),
                               "api_attempt_log": getattr(client, "last_attempt_log", None)})
                save_json(error_path, events)
                raise
            save_json(pending_path, {"state_marker": state_marker, "decision": decision,
                                     "glm_call": call})
        started = time.perf_counter()
        selected = tools.select(state, decision["policy"], seed, state["next_round"])
        select_seconds = time.perf_counter() - started
        response = oracle.query_batch_tool({"compound_keys": selected})
        if any(row["outcome"] for row in response["observations"]):
            controller.commit_random = False
        trajectory.append({"stage": f"feedback_round_{response['round']}",
                           "decision": decision,
                           "information_available": {"revealed_count": len(state["revealed"]),
                               "revealed_hits": sum(row["outcome"] for row in state["revealed"]),
                               "recent_hits": sum(row["outcome"] for row in state["revealed"][-10:])},
                           "glm_call": call, "selection": selected,
                           "observations": response["observations"],
                           "cumulative_hits": sum(row["outcome"] for row in oracle.public_state()["revealed"]),
                           "selection_seconds": select_seconds})
        controller.call_count = sum(int(step.get("glm_call") is not None) for step in trajectory)
        flattened = [r for step in trajectory for r in step["observations"]]
        assert len(flattened) == len({r["compound_key"] for r in flattened})
        complete = len(flattened) == 50
        first_hit = next((i for i, row in enumerate(flattened, 1) if row["outcome"]), None)
        saved = {**identity, "complete": complete, "trajectory": trajectory,
                 "queried_count": len(flattened), "H50": sum(row["outcome"] for row in flattened),
                 "queries_to_first_hit": first_hit,
                 "first_hit_right_censored": first_hit is None,
                 "glm_calls": controller.call_count,
                 "selection_seconds_total": sum(step.get("selection_seconds", 0) for step in trajectory)}
        save_json(run_path, saved)
        pending_path.unlink()
    assert saved["complete"]
    return {"pool": pool, "representation": representation, "seed": seed, "arm": arm,
            "complete": True, "H50": saved["H50"], "glm_calls": saved["glm_calls"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pool", choices=("tnap", "dyrk3"), required=True)
    parser.add_argument("--representation", choices=("bit", "count"), required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--arm", required=True)
    parser.add_argument("--weights")
    args = parser.parse_args()
    assert args.arm == "glm_extended" or args.arm in ("random_mixture_extended", "matched_proportion_extended") \
        or args.arm.startswith("fixed:") and args.arm.split(":", 1)[1] in MENU
    weights = json.loads(Path(args.weights).read_text()) if args.weights else None
    client = OfficialGLMDecisionClient(model_name="glm-5.3-flash") if args.arm == "glm_extended" else None
    print(json.dumps(run_one(args.pool, args.representation, args.seed, args.arm, weights, client),
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
