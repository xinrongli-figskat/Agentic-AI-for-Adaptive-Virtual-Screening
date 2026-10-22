"""D9 library-visible TNAP/S_strong arm. Private trajectories stay in d9_private."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[name] = "1"
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PRIVATE = HERE / "d9_private"
KEY_FILE = Path.home() / ".config/agentic-screening/zhipu_api_key"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "outputs"))
sys.path.insert(0, str(ROOT / "outputs/d7_20261021/c_surrogate_factor/runtime_packages"))

from oracle_boundary_v0.oracle_boundary import BatchOracle
from outputs.d7_20261021.c4_five.run_c4 import DESCRIPTIONS, candidates_and_labels
from outputs.d7_20261021.c_surrogate_factor_v2_orthogonal.c3_core import OrthogonalSelector
from outputs.d7_20261021.c_surrogate_factor_v2_orthogonal.run_meta_five import MENU
from outputs.d8_20261022.library_visible_controller import make_library_visible_payload, parse_policy, s_strong_scores
from outputs.d8_20261022.library_visible_api import LibraryVisibleGLMClient
from outputs.d9_20261022.reconcile import behavior

ARM = "llm_library_visible"
MAX_PHYSICAL = 88
PROJECT_BASELINE_PHYSICAL = 683
MODEL = "glm-5.3-flash"
COMMITMENT_NOTE = (
    "With zero hits, persistent_random_until_first_hit commits later zero-hit batches "
    "to seeded random without another model call; each batch still spends ten queries. "
    "All scored actions use random fallback when only one class has been revealed."
)
LOCK_FILES = {
    "D9_protocol": HERE / "D9_PROTOCOL.md",
    "D9_runner": HERE / "run_library_visible.py",
    "D8_payload": ROOT / "outputs/d8_20261022/library_visible_controller.py",
    "D8_api": ROOT / "outputs/d8_20261022/library_visible_api.py",
    "C3_selector": ROOT / "outputs/d7_20261021/c_surrogate_factor_v2_orthogonal/c3_core.py",
    "C3_five_menu": ROOT / "outputs/d7_20261021/c_surrogate_factor_v2_orthogonal/C3_FIVE_MENU_SPEC_v1.md",
    "C4_runner": ROOT / "outputs/d7_20261021/c4_five/run_c4.py",
    "oracle": ROOT / "outputs/oracle_boundary_v0/oracle_boundary.py",
}
PAYLOAD_FIELDS = {"task", "candidate_count", "queried_count", "remaining_budget",
                  "next_batch_size", "candidate_library", "already_measured_active_keys",
                  "already_measured_inactive_keys", "allowed_policies",
                  "policy_descriptions", "information_boundary", "commitment_note"}


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def hash_file(path):
    return sha(Path(path).read_bytes())


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as out:
        json.dump(value, out, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        out.write("\n")
        out.flush()
        os.fsync(out.fileno())
    temp.replace(path)


def c4_path(seed):
    return ROOT / f"outputs/d7_20261021/c4_five_private/runs/rep1/seed{seed}/run.json"


def physical_count():
    return len(list((PRIVATE / "http").glob("http_*.json")))


def lock():
    path = HERE / "D9_LOCK.json"
    if path.exists():
        raise FileExistsError("D9 lock already exists")
    if tuple(DESCRIPTIONS) != MENU or len(MENU) != 5 or "ens_one_step_proxy" in MENU:
        raise RuntimeError("Five-action menu mismatch")
    candidates, labels = candidates_and_labels()
    if len(candidates) != 462 or sum(labels.values()) != 53:
        raise RuntimeError("Frozen TNAP cardinality mismatch")
    c4_hashes = {}
    for seed in range(20):
        run = json.loads(c4_path(seed).read_text(encoding="utf-8"))
        if not run["complete"] or run["H50"] < 0:
            raise RuntimeError("C4 reference incomplete")
        oracle = BatchOracle(candidates, labels, seed=seed, total_budget=50,
                             initialization_queries=10, batch_size=10)
        if oracle.proposed_initial_ids() != run["trajectory"][0]["selection"]:
            raise RuntimeError("C4 initialization differs")
        c4_hashes[str(seed)] = hash_file(c4_path(seed))
    value = {"utc": utc(), "status": "locked_before_D9_provider_calls",
             "post_exposure": True, "arm": ARM, "pool": "TNAP", "surrogate": "S_strong",
             "representation": "bit", "menu": MENU, "seeds": list(range(20)),
             "repeats": 1, "query_budget": 50, "initialization": 10,
             "feedback_batches": 4, "max_physical_calls": MAX_PHYSICAL,
             "project_physical_baseline": PROJECT_BASELINE_PHYSICAL,
             "model": MODEL, "bootstrap_seed": 20261018,
             "file_sha256": {name: hash_file(p) for name,p in LOCK_FILES.items()},
             "C4_rep1_run_sha256": c4_hashes,
             "public_candidate_sha256": sha(json.dumps(candidates, sort_keys=True).encode()),
             "private_label_sha256": sha(json.dumps(labels, sort_keys=True).encode())}
    save(path, value)
    return value


def verify_lock(candidates=None, labels=None):
    path = HERE / "D9_LOCK.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    if value["status"] != "locked_before_D9_provider_calls" or tuple(value["menu"]) != MENU:
        raise RuntimeError("D9 lock invalid")
    for name,p in LOCK_FILES.items():
        if hash_file(p) != value["file_sha256"][name]:
            raise RuntimeError(f"D9 locked input changed: {name}")
    if candidates is None or labels is None:
        candidates, labels = candidates_and_labels()
    if (sha(json.dumps(candidates, sort_keys=True).encode()) != value["public_candidate_sha256"] or
        sha(json.dumps(labels, sort_keys=True).encode()) != value["private_label_sha256"]):
        raise RuntimeError("TNAP frozen pool changed")
    for seed in range(20):
        if hash_file(c4_path(seed)) != value["C4_rep1_run_sha256"][str(seed)]:
            raise RuntimeError("C4 reference changed")
    return value


def public_payload(candidates, state, scores):
    payload = make_library_visible_payload(candidates, state["revealed"], scores, MENU)
    # Keep C4 action descriptions and commitment semantics, changing only the
    # candidate information surface for this new arm.
    payload["policy_descriptions"] = DESCRIPTIONS
    payload["commitment_note"] = COMMITMENT_NOTE
    return payload


def assert_information_boundary(payload, candidates, state):
    """Four required assertions, checked again against serialized request bytes."""
    if set(payload) != PAYLOAD_FIELDS:
        raise AssertionError("Unexpected D9 prompt field")
    keys = {row["compound_key"] for row in candidates}
    lib = payload["candidate_library"]
    if len(keys) != 462 or len(lib) != 462 or {r["compound_key"] for r in lib} != keys:
        raise AssertionError("Prompt candidate set differs from full library")
    if any(set(r) != {"compound_key", "standardized_smiles", "predicted_active_probability"} for r in lib):
        raise AssertionError("Unqueried outcome field or extra candidate field")
    if set(payload["allowed_policies"]) != set(MENU) or payload["allowed_policies"] != list(MENU):
        raise AssertionError("Policy menu differs")
    forbidden = {"outcome", "label", "is_hit", "measured_result", "pool_hit_rate",
                 "global_prevalence", "near_threshold", "measurement_effort", "assay_tids",
                 "hidden_labels", "standard_value"}
    if forbidden & set(payload):
        raise AssertionError("Hidden-label aggregate in top-level prompt")
    queried = {r["compound_key"] for r in state["revealed"]}
    active = set(payload["already_measured_active_keys"])
    inactive = set(payload["already_measured_inactive_keys"])
    if active & inactive or active | inactive != queried:
        raise AssertionError("Revealed result key set differs from selected compounds")
    if active != {r["compound_key"] for r in state["revealed"] if r["outcome"] == 1}:
        raise AssertionError("Revealed active keys differ from oracle state")
    if inactive != {r["compound_key"] for r in state["revealed"] if r["outcome"] == 0}:
        raise AssertionError("Revealed inactive keys differ from oracle state")
    if payload["candidate_count"] != 462 or payload["queried_count"] != len(queried):
        raise AssertionError("Prompt counts differ from public state")
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    if any('"'+f+'"' in serialized for f in forbidden):
        raise AssertionError("Forbidden field present in serialized prompt")
    return {"full_library_462": True, "no_unqueried_outcome_field": True,
            "no_hidden_pool_aggregates": True, "revealed_results_selected_only": True}


def state_marker(seed, state):
    return sha(json.dumps({"seed": seed, "round": state["next_round"],
                           "revealed": state["revealed"]}, sort_keys=True).encode())


class PhysicalCap(RuntimeError):
    pass


class BudgetedOpener:
    def __init__(self, seed, marker, boundary):
        self.seed, self.marker, self.boundary = seed, marker, boundary
        self.last_index = None
        self.last_digest = None

    def __call__(self, request, timeout):
        if physical_count() >= MAX_PHYSICAL:
            raise PhysicalCap("D9 88-call physical cap reached")
        body = json.loads(request.data)
        user_payload = json.loads(body["messages"][1]["content"])
        if user_payload != self.boundary["payload"]:
            raise AssertionError("Network request differs from boundary-checked payload")
        if body.get("model") != MODEL or body.get("do_sample") is not False or body.get("response_format") != {"type": "json_object"}:
            raise AssertionError("D9 provider settings changed")
        index = physical_count()+1
        digest = sha(request.data)
        self.last_index, self.last_digest = index, digest
        path = PRIVATE / "http" / f"http_{index:04d}.json"
        receipt = {"index": index, "utc": utc(), "status": "reserved_before_network",
                   "seed": self.seed, "state_marker": self.marker,
                   "request_body_sha256": digest, "timeout_seconds": timeout,
                   "information_boundary_assertions": self.boundary["checks"]}
        save(path, receipt)
        start = time.perf_counter()
        try:
            response = urlopen(request, timeout=timeout)
            receipt.update(status="response_headers_received", http_status=getattr(response,"status",200),
                           elapsed_seconds=time.perf_counter()-start)
            save(path, receipt)
            return response
        except Exception as exc:
            receipt.update(status="transport_or_http_error", error_type=type(exc).__name__,
                           http_status=getattr(exc,"code",None), elapsed_seconds=time.perf_counter()-start)
            save(path, receipt)
            raise


def key_from_file():
    if not KEY_FILE.is_file():
        raise FileNotFoundError("Local API key file unavailable; no provider call")
    key = KEY_FILE.read_text(encoding="utf-8").strip()
    if not key or "\n" in key:
        raise ValueError("Local API key malformed")
    return key


def choose(seed, state, candidates, selector, key):
    revealed = state["revealed"]
    full_scores = s_strong_scores(candidates, revealed)
    unqueried_scores = selector.proxy.score("S_strong", revealed)
    selected_keys = {r["compound_key"] for r in revealed}
    for compound in candidates:
        k = compound["compound_key"]
        if k not in selected_keys:
            if (unqueried_scores is None and full_scores[k] is not None) or (unqueried_scores is not None and abs(full_scores[k]-unqueried_scores[k]) > 1e-10):
                raise AssertionError("Visible score differs from locked C4 S_strong proxy")
    payload = public_payload(candidates, state, full_scores)
    checks = assert_information_boundary(payload, candidates, state)
    marker = state_marker(seed, state)
    folder = PRIVATE / "runs" / f"seed{seed}"
    start_attempt = 1
    previous_digest = None
    for attempt in (1, 2):
        path = folder / f"decision_round{state['next_round']}_try{attempt}.json"
        if not path.exists():
            break
        receipt = json.loads(path.read_text(encoding="utf-8"))
        if receipt["state_marker"] != marker or receipt["payload"] != payload:
            raise RuntimeError("Saved D9 decision differs from resumed public state")
        if previous_digest and receipt["request_body_sha256"] != previous_digest:
            raise RuntimeError("Saved D9 format retry changed request bytes")
        previous_digest = receipt["request_body_sha256"]
        if receipt["status"] == "valid_decision":
            return receipt["decision"], receipt
        if receipt["status"] != "invalid_format":
            raise RuntimeError("Unexpected saved D9 decision status")
        start_attempt = attempt+1
    if start_attempt > 2:
        raise RuntimeError("D9 two format attempts exhausted")
    for attempt in range(start_attempt,3):
        opener = BudgetedOpener(seed, marker, {"payload": payload, "checks": checks})
        client = LibraryVisibleGLMClient(model_name=MODEL, api_key=key, opener=opener, timeout_seconds=120)
        started = time.perf_counter()
        try:
            raw = client(payload)
        except Exception as exc:
            save(folder / f"failure_round{state['next_round']}_try{attempt}.json",
                 {"utc": utc(), "seed": seed, "round": state["next_round"],
                  "error_type": type(exc).__name__, "message": str(exc),
                  "state_marker": marker, "physical_calls": physical_count(),
                  "http_index": opener.last_index})
            raise
        try:
            decision = parse_policy(raw, MENU)
            status = "valid_decision"
        except (ValueError, KeyError, TypeError):
            decision, status = None, "invalid_format"
        receipt = {"utc": utc(), "status": status, "seed": seed,
                   "round": state["next_round"], "state_marker": marker,
                   "format_attempt": attempt, "request_body_sha256": opener.last_digest,
                   "http_index": opener.last_index, "raw_response": raw,
                   "request_id": client.last_request_id, "usage": client.last_usage,
                   "elapsed_seconds": time.perf_counter()-started,
                   "payload": payload, "information_boundary_assertions": checks,
                   "decision": decision}
        if previous_digest and opener.last_digest != previous_digest:
            raise RuntimeError("D9 format retry did not resend identical request")
        previous_digest = opener.last_digest
        save(folder / f"decision_round{state['next_round']}_try{attempt}.json", receipt)
        if decision is not None:
            return decision, receipt
    raise RuntimeError("D9 two invalid format attempts at one decision")


def run_one(seed, key, candidates, labels):
    oracle = BatchOracle(candidates, labels, seed=seed, total_budget=50,
                         initialization_queries=10, batch_size=10)
    selector = OrthogonalSelector(candidates)
    path = PRIVATE / "runs" / f"seed{seed}" / "run.json"
    if path.exists():
        saved = json.loads(path.read_text(encoding="utf-8"))
        if saved.get("seed") != seed or saved.get("arm") != ARM:
            raise RuntimeError("D9 resume identity mismatch")
        trajectory = saved["trajectory"]
        for stage in trajectory:
            answer = oracle.query_batch_tool({"compound_keys": stage["selection"]})
            if answer["observations"] != stage["observations"]:
                raise RuntimeError("D9 saved trajectory differs from frozen oracle")
        if saved.get("complete"):
            return {"seed": seed, "status": "already_complete", "H50": saved["H50"]}
    else:
        initial = oracle.proposed_initial_ids()
        c4 = json.loads(c4_path(seed).read_text(encoding="utf-8"))
        if initial != c4["trajectory"][0]["selection"]:
            raise RuntimeError("D9 initialization differs from C4")
        first = oracle.query_batch_tool({"compound_keys": initial})
        trajectory = [{"stage": 0, "policy": "initialization", "mode": "label_blind",
                       "selection": initial, "observations": first["observations"]}]
        save(path, {"status": "in_progress", "complete": False, "arm": ARM,
                    "seed": seed, "trajectory": trajectory, "lock_sha256": hash_file(HERE/"D9_LOCK.json")})
    while oracle.public_state()["remaining_budget"]:
        state = oracle.public_state()
        hits = sum(int(r["outcome"]) for r in state["revealed"])
        committed = hits == 0 and any(s.get("policy") == "persistent_random_until_first_hit" for s in trajectory[1:])
        if committed:
            decision = {"policy": "persistent_random_until_first_hit",
                        "reason": "Automatic zero-hit commitment from earlier revealed choice."}
            receipt = None
        else:
            decision, receipt = choose(seed, state, candidates, selector, key)
        if decision["policy"] not in MENU:
            raise RuntimeError("Out-of-menu D9 policy")
        selection, mode = selector.select(state, "S_strong", decision["policy"], seed)
        answer = oracle.query_batch_tool({"compound_keys": selection})
        trajectory.append({"stage": state["next_round"], "policy": decision["policy"],
                           "reason": decision["reason"], "mode": mode,
                           "realized_behavior": behavior(mode), "revealed_hits_before": hits,
                           "automatic_commitment": receipt is None,
                           "selection": selection, "observations": answer["observations"],
                           "glm_call": None if receipt is None else
                           {k: receipt[k] for k in ("request_id", "usage", "http_index",
                                                        "elapsed_seconds", "request_body_sha256", "format_attempt",
                                                        "information_boundary_assertions")}})
        keys = [k for stage in trajectory for k in stage["selection"]]
        if len(set(keys)) != len(keys) or len(keys)>50:
            raise RuntimeError("D9 duplicate query or budget overrun")
        complete = len(keys)==50
        h50 = sum(int(o["outcome"]) for stage in trajectory for o in stage["observations"])
        save(path, {"status": "complete" if complete else "in_progress",
                    "complete": complete, "arm": ARM, "seed": seed,
                    "pool": "TNAP", "surrogate": "S_strong", "representation": "bit",
                    "queried_count": len(keys), "H50": h50, "trajectory": trajectory,
                    "lock_sha256": hash_file(HERE/"D9_LOCK.json")})
    return {"seed": seed, "status": "complete", "H50": h50}


def preflight():
    candidates, labels = candidates_and_labels()
    verify_lock(candidates, labels)
    selector = OrthogonalSelector(candidates)
    checks = 0
    for seed in range(20):
        oracle = BatchOracle(candidates, labels, seed=seed, total_budget=50,
                             initialization_queries=10, batch_size=10)
        initial = oracle.proposed_initial_ids()
        if initial != json.loads(c4_path(seed).read_text(encoding="utf-8"))["trajectory"][0]["selection"]:
            raise RuntimeError("Initialization regression failed")
        oracle.query_batch_tool({"compound_keys": initial})
        state = oracle.public_state()
        scores = s_strong_scores(candidates, state["revealed"])
        payload = public_payload(candidates, state, scores)
        assert_information_boundary(payload, candidates, state)
        for key, value in (selector.proxy.score("S_strong",state["revealed"]) or {}).items():
            if abs(scores[key]-value)>1e-10:
                raise RuntimeError("D8 score differs from C4 S_strong score")
        checks += 1
    result = {"utc":utc(), "status":"pass", "seeds_checked":checks,
              "initializations_equal_C4":True,"score_equivalence_to_C4":True,
              "four_information_boundary_assertions":True,"provider_calls":0}
    save(HERE/"D9_PREFLIGHT.json",result)
    return result


def status():
    completed=[]
    for seed in range(20):
        path=PRIVATE/"runs"/f"seed{seed}"/"run.json"
        if path.exists():
            run=json.loads(path.read_text(encoding="utf-8"))
            if run.get("complete"):
                completed.append({"seed":seed,"H50":run["H50"]})
    return {"utc":utc(),"completed":completed,"completed_count":len(completed),
            "physical_calls":physical_count(),"physical_cap":MAX_PHYSICAL,
            "project_cumulative_estimate":PROJECT_BASELINE_PHYSICAL+physical_count()}


def run(start,end):
    candidates,labels=candidates_and_labels()
    verify_lock(candidates,labels)
    pre=json.loads((HERE/"D9_PREFLIGHT.json").read_text(encoding="utf-8"))
    if pre["status"]!="pass":
        raise RuntimeError("D9 preflight not passed")
    key=key_from_file()
    for seed in range(start,end):
        if physical_count()>=MAX_PHYSICAL:
            raise PhysicalCap("D9 physical cap exhausted")
        row=run_one(seed,key,candidates,labels)
        print(json.dumps({**row,"physical_calls":physical_count()},ensure_ascii=False),flush=True)
    return status()


def main():
    p=argparse.ArgumentParser()
    p.add_argument("command",choices=("lock","preflight","run","status"))
    p.add_argument("--start",type=int,default=0)
    p.add_argument("--end",type=int,default=10)
    args=p.parse_args()
    if args.command=="lock": result=lock()
    elif args.command=="preflight": result=preflight()
    elif args.command=="run": result=run(args.start,args.end)
    else: result=status()
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)


if __name__=="__main__":
    main()
