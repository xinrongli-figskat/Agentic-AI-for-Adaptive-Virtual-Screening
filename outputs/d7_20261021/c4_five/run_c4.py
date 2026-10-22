"""C4: one authorized TNAP/S_strong five-policy LLM cell, resumable and capped."""
from __future__ import annotations

import os
for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "1"
import argparse
import hashlib
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PRIVATE = ROOT / "outputs/d7_20261021/c4_five_private"
C3 = ROOT / "outputs/d7_20261021/c_surrogate_factor_v2_orthogonal"
KEY_FILE = Path.home() / ".config" / "agentic-screening" / "zhipu_api_key"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "outputs"))
sys.path.insert(0, str(ROOT / "outputs/d7_20261021/c_surrogate_factor/runtime_packages"))
import numpy as np
from rdkit import DataStructs
from oracle_boundary_v0.oracle_boundary import BatchOracle
from outputs.campaign_v0.glm_api import OfficialGLMDecisionClient, MODEL_REQUEST_SETTINGS
from outputs.d7_20261021.c_surrogate_factor_v2.run_c2v2 import load_inputs, read_jsonl
from outputs.d7_20261021.c_surrogate_factor_v2_orthogonal.c3_core import OrthogonalSelector
from outputs.d7_20261021.c_surrogate_factor_v2_orthogonal.run_meta_five import (
    MENU, META, jobs as c3_jobs, path_for as c3_path,
)

ARM = "llm_policy_only_five"
MODEL = "glm-5.3-flash"
MAX_PHYSICAL = 160
EXPECTED_FIELDS = {"task", "candidate_count", "queried_count", "remaining_budget",
                   "next_round", "revealed_hits", "recent_revealed_hits",
                   "numerical_summary", "allowed_policies", "policy_descriptions",
                   "commitment_note"}
DESCRIPTIONS = {
    "greedy": "Use the fixed S_strong score; select the ten highest predictions. One-class fit falls back to seeded random.",
    "diverse": "Use S_strong score minus 0.2 times the maximum Morgan Tanimoto similarity to queried or current-batch choices; one-class fit falls back to seeded random.",
    "random": "Seeded uniform random selection without replacement for this batch.",
    "persistent_random_until_first_hit": "Use seeded random batches until a first measured hit; then use S_strong greedy. While still at zero hits, commitment avoids another GLM call but each batch costs ten queries.",
    "diverse_random_coldstart": "Use seeded random when no hit is known; otherwise S_strong diverse. A one-class fit still falls back to random.",
}
LOCKED_FILES = {
    "protocol": HERE / "C4_PROTOCOL_v1.md",
    "runner": HERE / "run_c4.py",
    "C3_five_spec": C3 / "C3_FIVE_MENU_SPEC_v1.md",
    "C3_five_lock": C3 / "C3_FIVE_MENU_LOCK_v1.json",
    "C3_five_summary": C3 / "C3_FIVE_PUBLIC_SUMMARY.json",
    "C3_five_tie_corrected_summary": C3 / "C3_FIVE_PUBLIC_SUMMARY_v1_1.json",
    "C3_five_tie_addendum": C3 / "C3_FIVE_MENU_ADDENDUM_20261021.md",
    "C3_five_audit": C3 / "C3_FIVE_AUDIT.json",
    "C3_core": C3 / "c3_core.py",
    "C3_proxy": C3 / "orthogonal_proxy.py",
    "C3_meta_runner": C3 / "run_meta_five.py",
    "GLM_client": ROOT / "outputs/campaign_v0/glm_api.py",
    "oracle": ROOT / "outputs/oracle_boundary_v0/oracle_boundary.py",
    "B_analysis": ROOT / "outputs/d7_20261021/b_model_variance/B_ANALYSIS.json",
    "C3_original_summary": C3 / "C3_PUBLIC_SUMMARY.json",
}


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def file_sha(path):
    return sha(Path(path).read_bytes())


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2,
                  sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    temp.replace(path)
    if PRIVATE in path.parents:
        os.chmod(path, 0o600)


def c3_private_tree_hash():
    paths = []
    private_root = ROOT / "outputs/d7_20261021/c_surrogate_factor_v2_orthogonal_five_private"
    for job in c3_jobs():
        path = c3_path(job)
        paths.append(f"{path.relative_to(private_root).as_posix()} {file_sha(path)}")
    return sha(("\n".join(sorted(paths)) + "\n").encode())


def lock_path():
    return HERE / "C4_LOCK_v1.json"


def create_lock():
    if lock_path().exists():
        raise FileExistsError("C4 lock already exists")
    if tuple(DESCRIPTIONS) != MENU or len(MENU) != 5 or "ens_one_step_proxy" in MENU:
        raise RuntimeError("C4 menu mismatch")
    c3_audit = json.loads((C3 / "C3_FIVE_AUDIT.json").read_text(encoding="utf-8"))
    if c3_private_tree_hash() != c3_audit["private_tree_sha256"]:
        raise RuntimeError("C3 five-menu private reference changed")
    pools = load_inputs()  # Frozen input verification; no labels are released to the model.
    tnap = pools["TNAP"]
    b_analysis = json.loads(LOCKED_FILES["B_analysis"].read_text(encoding="utf-8"))
    sigma = float(b_analysis["pooled_within_seed_sd_model"])
    if not math.isclose(sigma, 2.1943108257491692, rel_tol=0, abs_tol=1e-10):
        raise RuntimeError("B-line model variance changed")
    summary = json.loads(LOCKED_FILES["C3_five_tie_corrected_summary"].read_text(encoding="utf-8"))
    cell = summary["cells"]["TNAP"]["S_strong"]
    best_meta = max(cell["five_menu_meta_mean_H50"],
                    key=cell["five_menu_meta_mean_H50"].get)
    if best_meta != "bandit_thompson" or summary["C4_TNAP_cell_gate_eligible_order"] != ["S_strong"]:
        raise RuntimeError("C4 target/reference gate changed")
    value = {"status": "locked_before_C4_provider_calls", "utc": utc(),
             "post_exposure": True, "arm": ARM, "pool": "TNAP", "surrogate": "S_strong",
             "representation": "bit", "menu": MENU, "repeats": 2, "seeds": list(range(20)),
             "max_physical_calls": MAX_PHYSICAL, "nominal_decisions": 160,
             "best_meta_primary": best_meta, "B_model_sd": sigma,
             "file_sha256": {name: file_sha(path) for name, path in LOCKED_FILES.items()},
             "TNAP_public_sha256": sha(tnap[0]), "TNAP_private_sha256": sha(tnap[1]),
             "C3_five_private_tree_sha256": c3_audit["private_tree_sha256"]}
    save(lock_path(), value)
    return value


def verify_lock():
    lock = json.loads(lock_path().read_text(encoding="utf-8"))
    if (lock["status"] != "locked_before_C4_provider_calls" or tuple(lock["menu"]) != MENU
        or lock["max_physical_calls"] != MAX_PHYSICAL):
        raise RuntimeError("C4 lock identity mismatch")
    for name, path in LOCKED_FILES.items():
        if file_sha(path) != lock["file_sha256"][name]:
            raise RuntimeError("Locked C4 input changed: " + name)
    pools = load_inputs()
    if sha(pools["TNAP"][0]) != lock["TNAP_public_sha256"] or \
       sha(pools["TNAP"][1]) != lock["TNAP_private_sha256"]:
        raise RuntimeError("TNAP frozen pool changed")
    if c3_private_tree_hash() != lock["C3_five_private_tree_sha256"]:
        raise RuntimeError("C3 five-menu private reference changed")
    return lock


def candidates_and_labels():
    pub, private = load_inputs()["TNAP"]
    candidates = read_jsonl(pub)
    labels = {row["compound_key"]: int(row["outcome"]) for row in read_jsonl(private)}
    if len(candidates) != len(labels) or len(candidates) != 462 or sum(labels.values()) != 53:
        raise RuntimeError("TNAP frozen pool cardinality changed")
    return candidates, labels


def score_summary(selector, state):
    scores = selector.proxy.score("S_strong", state["revealed"])
    available = {row["compound_key"] for row in state["candidate_pool"]} - \
                {row["compound_key"] for row in state["revealed"]}
    if scores is None:
        return {"score_provider": "S_strong", "score_available": False,
                "unqueried_count": len(available), "predicted_hit_score_min": None,
                "predicted_hit_score_median": None, "predicted_hit_score_max": None,
                "top_10_mean_score": None,
                "top_10_mean_max_similarity_to_observed": None}
    if set(scores) != available:
        raise RuntimeError("S_strong score identities differ from unqueried pool")
    values = sorted(float(x) for x in scores.values())
    top = sorted(scores, key=lambda key: (-scores[key], key))[:10]
    observed = [row["compound_key"] for row in state["revealed"]]
    fps = selector.legacy.legacy.fingerprints
    similarities = [max((DataStructs.TanimotoSimilarity(fps[key], fps[ref])
                         for ref in observed), default=0.0) for key in top]
    return {"score_provider": "S_strong", "score_available": True,
            "unqueried_count": len(scores), "predicted_hit_score_min": values[0],
            "predicted_hit_score_median": values[len(values)//2],
            "predicted_hit_score_max": values[-1],
            "top_10_mean_score": sum(scores[key] for key in top)/len(top),
            "top_10_mean_max_similarity_to_observed": sum(similarities)/len(similarities)}


def public_summary(selector, state):
    hits = sum(int(row["outcome"]) for row in state["revealed"])
    result = {"task": "Choose one S_strong numerical policy for the next retrospective batch of 10.",
              "candidate_count": len(state["candidate_pool"]),
              "queried_count": state["queried_count"],
              "remaining_budget": state["remaining_budget"],
              "next_round": state["next_round"],
              "revealed_hits": hits,
              "recent_revealed_hits": sum(int(row["outcome"]) for row in state["revealed"][-10:]),
              "numerical_summary": score_summary(selector, state),
              "allowed_policies": list(MENU), "policy_descriptions": DESCRIPTIONS,
              "commitment_note": "With zero hits, persistent_random_until_first_hit commits later zero-hit batches to seeded random without more model calls; each batch still spends 10 oracle queries. All scored actions use random fallback when only one class has been revealed."}
    if set(result) != EXPECTED_FIELDS:
        raise RuntimeError("D5 eleven-field summary schema changed")
    serialized = json.dumps(result, ensure_ascii=False, sort_keys=True)
    if any(token in serialized for token in ('"compound_key"', '"standardized_smiles"', '"outcome"')):
        raise RuntimeError("Individual candidate or label leaked into prompt")
    return result


def parse_policy(raw):
    try:
        value = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise ValueError("Invalid D5 GLM policy JSON; no oracle query was made") from exc
    if (not isinstance(value, dict) or set(value) != {"policy", "reason"}
        or value.get("policy") not in MENU or not isinstance(value.get("reason"), str)
        or not 0 < len(value["reason"].strip()) <= 1000):
        raise ValueError("Invalid D5 GLM policy JSON; no oracle query was made")
    return {"policy": value["policy"], "reason": value["reason"].strip()}


def state_marker(rep, seed, state):
    return sha(json.dumps({"repeat": rep, "seed": seed, "round": state["next_round"],
                           "revealed": state["revealed"]}, sort_keys=True).encode())


def physical_count():
    return len(list((PRIVATE / "http").glob("http_*.json")))


class PhysicalBudgetReached(RuntimeError):
    pass


class BudgetedOpener:
    def __init__(self, rep, seed, marker):
        self.rep, self.seed, self.marker = rep, seed, marker

    def __call__(self, request, timeout):
        before = physical_count()
        if before >= MAX_PHYSICAL:
            raise PhysicalBudgetReached("C4 physical-call cap reached before network")
        index = before + 1
        path = PRIVATE / "http" / f"http_{index:04d}.json"
        receipt = {"index": index, "utc": utc(), "status": "reserved_before_network",
                   "repeat": self.rep, "seed": self.seed, "state_marker": self.marker,
                   "request_body_sha256": sha(request.data), "timeout_seconds": timeout}
        save(path, receipt)
        started = time.perf_counter()
        try:
            response = urlopen(request, timeout=timeout)
            receipt.update(status="response_headers_received",
                           http_status=getattr(response, "status", 200),
                           elapsed_seconds=time.perf_counter() - started)
            save(path, receipt)
            return response
        except HTTPError as exc:
            receipt.update(status="http_error", http_status=exc.code,
                           elapsed_seconds=time.perf_counter() - started)
            save(path, receipt)
            raise
        except Exception as exc:
            receipt.update(status="transport_error", error_type=type(exc).__name__,
                           elapsed_seconds=time.perf_counter() - started)
            save(path, receipt)
            raise


def api_key():
    # A secure local file is deliberately separate from the repository and outputs.
    if not KEY_FILE.is_file():
        raise FileNotFoundError("Local Zhipu key file is absent; no network request made")
    key = KEY_FILE.read_text(encoding="utf-8").strip()
    if not key or "\n" in key:
        raise ValueError("Local Zhipu key file is empty or malformed")
    return key


class FormatRetryExhausted(RuntimeError):
    pass


def choose_llm(rep, seed, state, selector, key):
    summary = public_summary(selector, state)
    marker = state_marker(rep, seed, state)
    root = PRIVATE / "runs" / f"rep{rep}" / f"seed{seed}"
    first_digest = None
    start_attempt = 1
    for prior_attempt in (1, 2):
        prior_path = root / f"decision_round{state['next_round']}_try{prior_attempt}.json"
        if not prior_path.exists():
            break
        prior = json.loads(prior_path.read_text(encoding="utf-8"))
        if prior.get("state_marker") != marker or prior.get("public_summary") != summary:
            raise RuntimeError("Saved format attempt differs from resumed public state")
        if first_digest is None:
            first_digest = prior["request_body_sha256"]
        elif prior["request_body_sha256"] != first_digest:
            raise RuntimeError("Saved format retry changed prompt bytes")
        if prior["status"] == "valid_decision":
            return prior["decision"], {k: prior[k] for k in (
                "request_id", "usage", "api_attempt_log", "elapsed_seconds",
                "request_body_sha256", "http_indices", "format_attempt")}
        if prior["status"] != "invalid_format":
            raise RuntimeError("Unexpected saved format-attempt status")
        start_attempt = prior_attempt + 1
    if start_attempt > 2:
        raise FormatRetryExhausted("Two saved invalid D5 JSON responses at one decision")
    for attempt in range(start_attempt, 3):
        opener = BudgetedOpener(rep, seed, marker)
        client = OfficialGLMDecisionClient(model_name=MODEL, api_key=key,
                                           opener=opener, timeout_seconds=120)
        before = physical_count()
        started = time.perf_counter()
        try:
            raw = client(summary)
            elapsed = time.perf_counter() - started
            after = physical_count()
            receipts = [json.loads((PRIVATE / "http" / f"http_{i:04d}.json").read_text(encoding="utf-8"))
                        for i in range(before + 1, after + 1)]
            digest = receipts[-1]["request_body_sha256"]
            if first_digest is None:
                first_digest = digest
            if digest != first_digest or any(r["request_body_sha256"] != digest for r in receipts):
                raise RuntimeError("Format retry or internal HTTP retry changed prompt bytes")
            try:
                decision = parse_policy(raw)
                status = "valid_decision"
            except ValueError:
                decision = None
                status = "invalid_format"
            receipt = {"utc": utc(), "status": status, "repeat": rep, "seed": seed,
                       "state_marker": marker, "format_attempt": attempt,
                       "request_body_sha256": digest, "http_indices": list(range(before+1, after+1)),
                       "raw_response": raw, "request_id": client.last_request_id,
                       "usage": client.last_usage, "api_attempt_log": client.last_attempt_log,
                       "elapsed_seconds": elapsed, "public_summary": summary,
                       "decision": decision}
            save(root / f"decision_round{state['next_round']}_try{attempt}.json", receipt)
            if decision is not None:
                return decision, {k: receipt[k] for k in ("request_id", "usage", "api_attempt_log",
                                                      "elapsed_seconds", "request_body_sha256",
                                                      "http_indices", "format_attempt")}
            if attempt == 2:
                raise FormatRetryExhausted("Two invalid D5 JSON responses at one decision")
        except (FormatRetryExhausted, PhysicalBudgetReached):
            raise
        except Exception as exc:
            save(root / f"failure_round{state['next_round']}_try{attempt}.json",
                 {"utc": utc(), "status": "provider_or_validation_failure",
                  "error_type": type(exc).__name__, "message": str(exc),
                  "state_marker": marker, "physical_calls_before": before,
                  "physical_calls_after": physical_count(),
                  "request_id": client.last_request_id, "usage": client.last_usage,
                  "api_attempt_log": client.last_attempt_log})
            raise
    raise RuntimeError("Unreachable format loop")


def run_path(rep, seed):
    return PRIVATE / "runs" / f"rep{rep}" / f"seed{seed}" / "run.json"


def run_one(rep, seed, key):
    candidates, labels = candidates_and_labels()
    selector = OrthogonalSelector(candidates)
    oracle = BatchOracle(candidates, labels, seed=seed, total_budget=50,
                         initialization_queries=10, batch_size=10)
    path = run_path(rep, seed)
    pending_path = path.parent / "pending.json"
    if path.exists():
        saved = json.loads(path.read_text(encoding="utf-8"))
        if any(saved.get(k) != v for k, v in (("arm", ARM), ("repeat", rep),
            ("seed", seed), ("pool", "TNAP"), ("surrogate", "S_strong"))):
            raise RuntimeError("Saved C4 run identity mismatch")
        trajectory = saved["trajectory"]
        for step in trajectory:
            answer = oracle.query_batch_tool({"compound_keys": step["selection"]})
            if answer["observations"] != step["observations"]:
                raise RuntimeError("Saved trajectory differs from frozen oracle")
        if saved.get("complete"):
            return {"repeat": rep, "seed": seed, "status": "already_complete", "H50": saved["H50"]}
    else:
        initial = oracle.proposed_initial_ids()
        first = oracle.query_batch_tool({"compound_keys": initial})
        trajectory = [{"stage": 0, "policy": "initialization", "mode": "label_blind",
                       "selection": initial, "observations": first["observations"]}]
        save(path, {"status": "in_progress", "complete": False, "arm": ARM,
                    "repeat": rep, "seed": seed, "pool": "TNAP", "surrogate": "S_strong",
                    "trajectory": trajectory, "queried_count": 10,
                    "lock_sha256": file_sha(lock_path())})
    while oracle.public_state()["remaining_budget"]:
        state = oracle.public_state()
        marker = state_marker(rep, seed, state)
        hits = sum(int(row["outcome"]) for row in state["revealed"])
        committed = hits == 0 and any(step.get("policy") == "persistent_random_until_first_hit"
                                      for step in trajectory[1:])
        if pending_path.exists():
            pending = json.loads(pending_path.read_text(encoding="utf-8"))
            if pending["state_marker"] != marker:
                raise RuntimeError("Pending decision does not match resumed oracle state")
            decision, call = pending["decision"], pending["call"]
        elif committed:
            decision = {"policy": "persistent_random_until_first_hit",
                        "reason": "Automatic zero-hit commitment from earlier revealed decision."}
            call = None
            save(pending_path, {"state_marker": marker, "decision": decision, "call": call})
        else:
            decision, call = choose_llm(rep, seed, state, selector, key)
            save(pending_path, {"state_marker": marker, "decision": decision, "call": call})
        if decision["policy"] not in MENU or decision["policy"] == "ens_one_step_proxy":
            raise RuntimeError("Out-of-menu policy before oracle")
        selected, mode = selector.select(state, "S_strong", decision["policy"], seed)
        answer = oracle.query_batch_tool({"compound_keys": selected})
        trajectory.append({"stage": state["next_round"], "policy": decision["policy"],
                           "reason": decision["reason"], "mode": mode,
                           "automatic_commitment": call is None, "revealed_hits_before": hits,
                           "selection": selected, "observations": answer["observations"],
                           "glm_call": call})
        keys = [key for step in trajectory for key in step["selection"]]
        if len(keys) != len(set(keys)) or len(keys) > 50:
            raise RuntimeError("Duplicate query or budget overrun")
        complete = len(keys) == 50
        h50 = sum(int(row["outcome"]) for step in trajectory for row in step["observations"])
        save(path, {"status": "complete" if complete else "in_progress",
                    "complete": complete, "arm": ARM, "repeat": rep, "seed": seed,
                    "pool": "TNAP", "surrogate": "S_strong", "representation": "bit",
                    "queried_count": len(keys), "H50": h50, "trajectory": trajectory,
                    "glm_valid_decisions": sum(step.get("glm_call") is not None for step in trajectory),
                    "lock_sha256": file_sha(lock_path())})
        pending_path.unlink()
    return {"repeat": rep, "seed": seed, "status": "complete",
            "H50": h50, "valid_model_decisions": sum(step.get("glm_call") is not None for step in trajectory)}


def status():
    done, abandoned = [], []
    for rep in (1, 2):
        for seed in range(20):
            path = run_path(rep, seed)
            if path.exists() and json.loads(path.read_text(encoding="utf-8")).get("complete"):
                done.append((rep, seed))
            if (path.parent / "ABANDONED.json").exists():
                abandoned.append((rep, seed))
    return {"utc": utc(), "complete_campaigns": len(done), "abandoned_campaigns": abandoned,
            "physical_calls": physical_count(), "physical_remaining": MAX_PHYSICAL - physical_count(),
            "planned_campaigns": 40, "C4_scope": "TNAP/S_strong/bit only"}


def run(max_campaigns):
    verify_lock()
    preflight_file = HERE / "C4_SYNTHETIC_PREFLIGHT.json"
    if not preflight_file.exists() or json.loads(preflight_file.read_text(encoding="utf-8"))["status"] != "pass":
        raise RuntimeError("Synthetic preflight missing or failed")
    key = api_key()
    attempted = 0
    for rep in (1, 2):
        for seed in range(20):
            if max_campaigns is not None and attempted >= max_campaigns:
                return status()
            if (run_path(rep, seed).parent / "ABANDONED.json").exists():
                continue
            if run_path(rep, seed).exists() and json.loads(run_path(rep, seed).read_text(encoding="utf-8")).get("complete"):
                continue
            if physical_count() >= MAX_PHYSICAL:
                save(HERE / "C4_STOP_PHYSICAL_CAP.json", status())
                return status()
            try:
                row = run_one(rep, seed, key)
            except FormatRetryExhausted as exc:
                save(run_path(rep, seed).parent / "ABANDONED.json",
                     {"utc": utc(), "repeat": rep, "seed": seed, "reason": str(exc),
                      "physical_calls_at_abandonment": physical_count(),
                      "no_fallback_policy": True})
                row = {"repeat": rep, "seed": seed, "status": "abandoned_after_two_invalid_formats"}
            except PhysicalBudgetReached:
                save(HERE / "C4_STOP_PHYSICAL_CAP.json", status())
                return status()
            except Exception as exc:
                save(HERE / "C4_PAUSE_ERROR.json", {"utc": utc(), "repeat": rep, "seed": seed,
                     "error_type": type(exc).__name__, "message": str(exc),
                     "physical_calls": physical_count()})
                raise
            attempted += 1
            print(json.dumps({**row, "physical_calls": physical_count()}, ensure_ascii=False), flush=True)
    return status()


def mock_preflight():
    verify_lock()
    candidates = read_jsonl(load_inputs()["TNAP"][0])
    selector = OrthogonalSelector(candidates)
    keys = [row["compound_key"] for row in candidates]
    zero = {key: 0 for key in keys}
    init = BatchOracle(candidates, zero, seed=0, total_budget=50,
                       initialization_queries=10, batch_size=10).proposed_initial_ids()
    init_set = set(init)
    labels_a = {key: int(i % 2 == 0) if key in init_set else 0 for i, key in enumerate(keys)}
    labels_b = {key: labels_a[key] if key in init_set else 1 for key in keys}
    summaries = []
    for labels in (labels_a, labels_b):
        oracle = BatchOracle(candidates, labels, seed=0, total_budget=50,
                             initialization_queries=10, batch_size=10)
        oracle.query_batch_tool({"compound_keys": init})
        summaries.append(public_summary(selector, oracle.public_state()))
    if summaries[0] != summaries[1]:
        raise RuntimeError("Unrevealed synthetic labels affected GLM summary")
    captured = []
    class MockResponse:
        status = 200
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self):
            return json.dumps({"id": "synthetic", "usage": {"total_tokens": 0},
                "choices": [{"message": {"content":
                    '{"policy":"greedy","reason":"synthetic revealed summary"}'}}]}).encode()
    def opener(request, timeout):
        captured.append(json.loads(request.data.decode("utf-8")))
        return MockResponse()
    client = OfficialGLMDecisionClient(model_name=MODEL, api_key="synthetic-only", opener=opener)
    decision = parse_policy(client(summaries[0]))
    body = captured[0]
    if (body["model"] != MODEL or body["do_sample"] is not False or
        body["thinking"] != {"type": "enabled"} or body["reasoning_effort"] != "low" or
        body["max_tokens"] != 1024 or body["response_format"] != {"type": "json_object"} or
        set(json.loads(body["messages"][1]["content"])) != EXPECTED_FIELDS):
        raise RuntimeError("Mock provider request differs from locked GLM configuration")
    try:
        parse_policy('{"policy":"greedy","reason":"x","extra":""}')
    except ValueError:
        pass
    else:
        raise RuntimeError("Strict D5 parser accepted an extra key")
    selections = []
    for labels in (labels_a, labels_b):
        oracle = BatchOracle(candidates, labels, seed=0, total_budget=50,
                             initialization_queries=10, batch_size=10)
        oracle.query_batch_tool({"compound_keys": init})
        selected, mode = selector.select(oracle.public_state(), "S_strong",
                                         decision["policy"], 0)
        selections.append((selected, mode))
    if selections[0] != selections[1]:
        raise RuntimeError("Unrevealed synthetic labels affected the chosen batch")
    value = {"status": "pass", "utc": utc(), "synthetic_outcomes_only": True,
             "unrevealed_label_perturbation_invariant": True,
             "D5_exact_JSON_parser": True, "D5_eleven_top_level_fields": True,
             "model_request_settings_mock_validated": True,
             "selected_policy": decision["policy"], "glm_calls": 0}
    save(HERE / "C4_SYNTHETIC_PREFLIGHT.json", value)
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("lock", "preflight", "run", "status"))
    parser.add_argument("--max-campaigns", type=int)
    args = parser.parse_args()
    if args.command == "lock":
        result = create_lock()
    elif args.command == "preflight":
        result = mock_preflight()
    elif args.command == "run":
        result = run(args.max_campaigns)
    else:
        result = status()
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
