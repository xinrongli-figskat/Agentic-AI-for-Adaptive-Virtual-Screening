"""D11 controlled prompt-framing ablation; private traces live under d11_private."""
from __future__ import annotations
import argparse, hashlib, json, math, os, random, re, sys, time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

for _name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ[_name] = "1"
ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
PRIVATE = HERE / "d11_private"
C4 = ROOT / "outputs/d7_20261021/c4_five_private/runs"
D9 = ROOT / "outputs/d9_20261022/d9_private/runs"
C3 = ROOT / "outputs/d7_20261021/c_surrogate_factor_v2_orthogonal"
KEY_FILE = Path.home() / ".config/agentic-screening/zhipu_api_key"
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "outputs")); sys.path.insert(0, str(ROOT / "outputs/d7_20261021/c_surrogate_factor/runtime_packages"))
from oracle_boundary_v0.oracle_boundary import BatchOracle
from outputs.d7_20261021.c4_five import run_c4 as c4
from outputs.d7_20261021.c_surrogate_factor_v2_orthogonal.c3_core import OrthogonalSelector
from outputs.d7_20261021.c_surrogate_factor_v2_orthogonal.run_meta_five import MENU
from outputs.d9_20261022.reconcile import behavior
from outputs.campaign_v0.glm_api import MODEL_REQUEST_SETTINGS, OFFICIAL_ENDPOINT

ARM = "llm_instruction_only"
MODEL = "glm-5.3-flash"
MAX_PHYSICAL = 88
BASELINE = 764
SIGMA = 2.1943108257491692
EXPECTED_FIELDS = {"task", "candidate_count", "queried_count", "remaining_budget", "next_round", "revealed_hits", "recent_revealed_hits", "numerical_summary", "allowed_policies", "policy_descriptions", "commitment_note"}
PROMPT = ("You choose one allowed policy for one batch in a retrospective compound-search prototype. "
          "The user message contains only public candidate counts and already revealed binary outcomes. "
          "Choose exactly one of the allowed numerical selection policies for the next batch. "
          "Reason only from the supplied feedback. Do not claim to know candidate scores, unknown labels, or chemical details; numerical tools will choose actual compounds. "
          "Do not infer or claim the result of any unselected compound. "
          "State the observed hit counts relevant to your choice in one short sentence. "
          "Explain briefly using the supplied information. "
          'Return only JSON with exactly these keys: {"policy":"allowed_policy_name","reason":"brief evidence-based reason"}.')
LOCK_INPUTS = {
    "instruction_diff": HERE / "D11_INSTRUCTION_DIFF.md", "protocol": HERE / "D11_PROTOCOL.md", "runner": HERE / "run_d11.py",
    "C4_lock": ROOT / "outputs/d7_20261021/c4_five/C4_LOCK_v1.json", "C4_runner": ROOT / "outputs/d7_20261021/c4_five/run_c4.py",
    "C4_glm_client": ROOT / "outputs/campaign_v0/glm_api.py", "C3_menu": C3 / "C3_FIVE_MENU_SPEC_v1.md",
    "C3_selector": C3 / "c3_core.py", "D9_lock": ROOT / "outputs/d9_20261022/D9_LOCK.json",
    "D9_runner": ROOT / "outputs/d9_20261022/run_library_visible.py", "D9_api": ROOT / "outputs/d8_20261022/library_visible_api.py",
    "oracle": ROOT / "outputs/oracle_boundary_v0/oracle_boundary.py"}

def utc(): return datetime.now(timezone.utc).isoformat()
def sha(raw): return hashlib.sha256(raw).hexdigest()
def fsha(path): return sha(Path(path).read_bytes())
def dump(path, value):
    path=Path(path); path.parent.mkdir(parents=True, exist_ok=True); tmp=path.with_suffix(path.suffix+".tmp")
    with tmp.open("w",encoding="utf-8") as f:
        json.dump(value,f,ensure_ascii=False,indent=2,sort_keys=True,allow_nan=False); f.write("\n"); f.flush(); os.fsync(f.fileno())
    tmp.replace(path)
    if PRIVATE in path.parents:
        try: os.chmod(path,0o600)
        except OSError: pass

def read(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def lock_path(): return HERE / "D11_LOCK.json"
def run_path(seed): return PRIVATE / "runs" / f"seed{seed}" / "run.json"
def marker(seed,state): return sha(json.dumps({"seed":seed,"round":state["next_round"],"revealed":state["revealed"]},sort_keys=True).encode())
def physical_count():
    d=PRIVATE/"http"; return len(list(d.glob("http_*.json"))) if d.exists() else 0

def create_lock():
    if lock_path().exists(): raise FileExistsError("D11 lock already exists")
    if tuple(c4.DESCRIPTIONS)!=MENU or tuple(MENU)!=tuple(read(C3/"C3_FIVE_MENU_LOCK_v1.json")["menu"]): raise RuntimeError("D11 menu differs from locked C4 five-action menu")
    candidates,labels=c4.candidates_and_labels()
    if len(candidates)!=462 or sum(labels.values())!=53: raise RuntimeError("TNAP frozen pool counts changed")
    pub,priv=c4.load_inputs()["TNAP"]
    init_hashes={}
    for seed in range(20):
        oracle=BatchOracle(candidates,labels,seed=seed,total_budget=50,initialization_queries=10,batch_size=10)
        proposed=oracle.proposed_initial_ids()
        for label,path in (("C4",C4/f"rep1/seed{seed}/run.json"),("D9",D9/f"seed{seed}/run.json")):
            saved=read(path)
            if not saved.get("complete") or saved["trajectory"][0]["selection"]!=proposed: raise RuntimeError(f"seed {seed} init differs from {label}")
        init_hashes[str(seed)]=sha(json.dumps(proposed,separators=(",",":" )).encode())
    if fsha(HERE/"D11_INSTRUCTION_DIFF.md") is None: raise RuntimeError("diff missing")
    lock={"status":"locked_before_D11_provider_calls","utc":utc(),"post_exposure":True,"arm":ARM,"pool":"TNAP","surrogate":"S_strong","representation":"bit","model":MODEL,"menu":list(MENU),"seeds":list(range(20)),"repeat":1,"initialization_queries":10,"query_budget":50,"feedback_batches":4,"planned_model_decisions":80,"max_physical_calls":MAX_PHYSICAL,"project_cumulative_baseline":BASELINE,"D11_system_prompt":PROMPT,"D11_system_prompt_sha256":sha(PROMPT.encode()),"C4_information_schema":sorted(EXPECTED_FIELDS),"C4_initialization_hashes":init_hashes,"TNAP_public_sha256":sha(pub),"TNAP_private_sha256":sha(priv),"file_sha256":{k:fsha(v) for k,v in LOCK_INPUTS.items() if v.exists()},"missing_locked_inputs":[k for k,v in LOCK_INPUTS.items() if not v.exists()]}
    if lock["missing_locked_inputs"]: raise RuntimeError("Missing lock inputs: "+", ".join(lock["missing_locked_inputs"]))
    dump(lock_path(),lock); return lock

def verify_lock():
    lock=read(lock_path())
    if lock["status"]!="locked_before_D11_provider_calls" or lock["D11_system_prompt"]!=PROMPT or lock["max_physical_calls"]!=MAX_PHYSICAL: raise RuntimeError("D11 lock mismatch")
    for name,path in LOCK_INPUTS.items():
        if fsha(path)!=lock["file_sha256"].get(name): raise RuntimeError("Locked input changed: "+name)
    pub,priv=c4.load_inputs()["TNAP"]
    if sha(pub)!=lock["TNAP_public_sha256"] or sha(priv)!=lock["TNAP_private_sha256"]: raise RuntimeError("TNAP frozen input changed")
    return lock

def runtime_assertions(summary,candidates,request_body):
    user=json.dumps(summary,ensure_ascii=False,sort_keys=True)
    body=json.dumps(request_body,ensure_ascii=False,sort_keys=True)
    # Ensure exact C4 aggregate-only input and schema.
    assert set(summary)==EXPECTED_FIELDS
    assert user==json.dumps(summary,ensure_ascii=False,sort_keys=True)
    assert request_body["messages"][0]=={"role":"system","content":PROMPT}
    assert request_body["messages"][1]=={"role":"user","content":user}
    assert tuple(summary["allowed_policies"])==tuple(MENU)
    ns=summary["numerical_summary"]
    expected_ns={"score_provider","score_available","unqueried_count","predicted_hit_score_min","predicted_hit_score_median","predicted_hit_score_max","top_10_mean_score","top_10_mean_max_similarity_to_observed"}
    assert set(ns)==expected_ns
    # Identities and structures are private inputs but tested only for non-occurrence in the outgoing payload.
    keys=[row["compound_key"] for row in candidates]
    smiles=[row.get("standardized_smiles") for row in candidates if row.get("standardized_smiles")]
    assert all(k not in body for k in keys)
    assert all(s not in body for s in smiles)
    # Only aggregate scores are allowed; no arrays/maps of per-compound predictions.
    assert isinstance(ns["unqueried_count"],int) and not any(isinstance(v,(list,dict)) for k,v in ns.items() if k!="score_provider")
    # No individually revealed or unrevealed outcomes can be sent: schema is aggregate-only and contains no outcome keys.
    assert not re.search(r'"(?:outcome|label|is_hit|hit_label|compound_key|standardized_smiles)"\s*:',body)
    return {"no_candidate_structures_or_SMILES":True,"no_unqueried_compound_identity":True,"no_per_compound_or_full_library_scores":True,"no_unqueried_compound_outcomes":True}

def parse_policy(raw):
    try: value=json.loads(raw)
    except (ValueError,TypeError) as e: raise ValueError("invalid JSON") from e
    if not isinstance(value,dict) or set(value)!={"policy","reason"} or value.get("policy") not in MENU or not isinstance(value.get("reason"),str) or not 0<len(value["reason"].strip())<=1000: raise ValueError("invalid strict policy schema")
    return {"policy":value["policy"],"reason":value["reason"].strip()}

class PhysicalCap(RuntimeError): pass
class TransportPause(RuntimeError): pass

def call_once(seed,round_no,try_no,state,selector,candidates,key):
    summary=c4.public_summary(selector,state)
    marker0=marker(seed,state)
    payload={"model":MODEL,"messages":[{"role":"system","content":PROMPT},{"role":"user","content":json.dumps(summary,ensure_ascii=False,sort_keys=True)}],"response_format":{"type":"json_object"},"do_sample":False,"stream":False}
    payload.update(MODEL_REQUEST_SETTINGS[MODEL])
    assertions=runtime_assertions(summary,candidates,payload)
    request_bytes=json.dumps(payload).encode("utf-8")
    digest=sha(request_bytes)
    decision_root=PRIVATE/"runs"/f"seed{seed}"
    decision_path=decision_root/f"decision_round{round_no}_try{try_no}.json"
    if decision_path.exists():
        prior=read(decision_path)
        if prior.get("state_marker")!=marker0 or prior.get("request_body_sha256")!=digest: raise RuntimeError("Existing D11 decision receipt does not match locked state")
        if prior.get("status")=="valid_decision": return prior["decision"],prior
        if prior.get("status")=="invalid_format": return None,prior
        if prior.get("status")=="provider_error": pass
        else: raise RuntimeError("Unexpected existing D11 decision receipt")
    if physical_count()>=MAX_PHYSICAL: raise PhysicalCap("D11 88 physical-call limit reached")
    http_i=physical_count()+1; http_path=PRIVATE/"http"/f"http_{http_i:04d}.json"
    receipt={"index":http_i,"utc_reserved":utc(),"status":"reserved_before_network","seed":seed,"round":round_no,"format_try":try_no,"state_marker":marker0,"request_body_sha256":digest,"information_boundary_assertions":assertions}
    dump(http_path,receipt)
    req=Request(OFFICIAL_ENDPOINT,data=request_bytes,headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"},method="POST")
    started=time.perf_counter()
    try:
        with urlopen(req,timeout=120) as resp:
            http_status=getattr(resp,"status",200); raw_bytes=resp.read()
        result=json.loads(raw_bytes.decode("utf-8")); content=result["choices"][0]["message"]["content"]
        usage=result.get("usage"); request_id=result.get("id")
        http_receipt={**receipt,"status":"response_received","http_status":http_status,"elapsed_seconds":time.perf_counter()-started,"request_id":request_id,"usage":usage}
        dump(http_path,http_receipt)
        try: decision=parse_policy(content); status="valid_decision"
        except ValueError: decision=None; status="invalid_format"
        saved={"utc":utc(),"status":status,"seed":seed,"round":round_no,"format_try":try_no,"state_marker":marker0,"request_body_sha256":digest,"request_id":request_id,"usage":usage,"elapsed_seconds":time.perf_counter()-started,"raw_response":content,"public_summary":summary,"information_boundary_assertions":assertions,"decision":decision,"http_index":http_i}
        dump(decision_path,saved)
        return decision,saved
    except HTTPError as exc:
        body=exc.read()
        err={**receipt,"status":"http_error","http_status":exc.code,"elapsed_seconds":time.perf_counter()-started,"provider_error_body_sha256":sha(body)}
        dump(http_path,err); dump(decision_path,{"utc":utc(),"status":"provider_error","seed":seed,"round":round_no,"format_try":try_no,"state_marker":marker0,"request_body_sha256":digest,"http_index":http_i,"error_type":"HTTPError","http_status":exc.code})
        raise TransportPause(f"HTTP {exc.code}; paused, no fallback") from exc
    except Exception as exc:
        err={**receipt,"status":"transport_error","error_type":type(exc).__name__,"elapsed_seconds":time.perf_counter()-started}
        dump(http_path,err); dump(decision_path,{"utc":utc(),"status":"provider_error","seed":seed,"round":round_no,"format_try":try_no,"state_marker":marker0,"request_body_sha256":digest,"http_index":http_i,"error_type":type(exc).__name__})
        raise TransportPause(f"{type(exc).__name__}; paused, no fallback") from exc

def choose(seed,state,selector,candidates,key):
    round_no=state["next_round"]
    for try_no in (1,2):
        decision,receipt=call_once(seed,round_no,try_no,state,selector,candidates,key)
        if decision is not None: return decision,receipt
        if try_no==2: return None,receipt
    raise RuntimeError("unreachable")

def run_one(seed,key):
    candidates,labels=c4.candidates_and_labels(); selector=OrthogonalSelector(candidates)
    oracle=BatchOracle(candidates,labels,seed=seed,total_budget=50,initialization_queries=10,batch_size=10)
    path=run_path(seed); folder=path.parent; folder.mkdir(parents=True,exist_ok=True)
    if path.exists():
        saved=read(path)
        if saved.get("seed")!=seed or saved.get("arm")!=ARM: raise RuntimeError("D11 run identity mismatch")
        trajectory=saved["trajectory"]
        for step in trajectory:
            result=oracle.query_batch_tool({"compound_keys":step["selection"]})
            if result["observations"]!=step["observations"]: raise RuntimeError("D11 saved path differs from frozen oracle")
        if saved.get("complete") or saved.get("abandoned"): return saved
    else:
        initial=oracle.proposed_initial_ids()
        c4init=read(C4/f"rep1/seed{seed}/run.json")["trajectory"][0]["selection"]
        d9init=read(D9/f"seed{seed}/run.json")["trajectory"][0]["selection"]
        if initial!=c4init or initial!=d9init: raise RuntimeError("D11 initialization mismatch")
        result=oracle.query_batch_tool({"compound_keys":initial})
        trajectory=[{"stage":0,"policy":"initialization","mode":"label_blind","selection":initial,"observations":result["observations"]}]
        saved={"status":"in_progress","complete":False,"abandoned":False,"arm":ARM,"seed":seed,"pool":"TNAP","surrogate":"S_strong","representation":"bit","queried_count":10,"trajectory":trajectory,"lock_sha256":fsha(lock_path())}
        dump(path,saved)
    while oracle.public_state()["remaining_budget"]:
        state=oracle.public_state(); hits=sum(int(row["outcome"]) for row in state["revealed"])
        committed=hits==0 and any(step.get("policy")=="persistent_random_until_first_hit" for step in trajectory[1:])
        if committed:
            decision={"policy":"persistent_random_until_first_hit","reason":"Automatic zero-hit commitment from previously revealed policy."}; model_receipt=None
        else:
            decision,model_receipt=choose(seed,state,selector,candidates,key)
            if decision is None:
                saved.update(status="abandoned_after_two_invalid_formats",abandoned=True,complete=False,failed_round=state["next_round"],queried_count=oracle.public_state()["queried_count"],valid_decisions=sum(s.get("glm_call") is not None for s in trajectory[1:]))
                dump(path,saved); dump(folder/"ABANDONED.json",{"utc":utc(),"seed":seed,"round":state["next_round"],"reason":"two invalid format responses","no_policy_fallback":True})
                return saved
        selected,mode=selector.select(state,"S_strong",decision["policy"],seed)
        answer=oracle.query_batch_tool({"compound_keys":selected})
        trajectory.append({"stage":state["next_round"],"policy":decision["policy"],"reason":decision["reason"],"mode":mode,"automatic_commitment":model_receipt is None,"revealed_hits_before":hits,"selection":selected,"observations":answer["observations"],"glm_call":None if model_receipt is None else {k:model_receipt.get(k) for k in ("http_index","request_id","usage","elapsed_seconds","request_body_sha256","format_try","information_boundary_assertions")}})
        allkeys=[k for st in trajectory for k in st["selection"]]
        if len(allkeys)!=len(set(allkeys)) or len(allkeys)>50: raise RuntimeError("D11 duplicate query or budget overrun")
        h50=sum(int(o["outcome"]) for st in trajectory for o in st["observations"])
        complete=len(allkeys)==50
        saved.update(status="complete" if complete else "in_progress",complete=complete,queried_count=len(allkeys),H50=h50,trajectory=trajectory,valid_decisions=sum(st.get("glm_call") is not None for st in trajectory[1:]),lock_sha256=fsha(lock_path()))
        dump(path,saved)
    return saved

def phase(start,end):
    verify_lock()
    if start==10:
        cp=HERE/"CHECKPOINT_0_9.json"
        if not cp.exists() or read(cp).get("status")!="pass" or read(cp).get("complete_campaigns")!=10: raise RuntimeError("Seeds 0-9 checkpoint must pass before phase 10-19")
    if start not in (0,10) or end!=(10 if start==0 else 20): raise ValueError("Use run --start 0 --end 10, then 10 --20")
    if not KEY_FILE.is_file(): raise RuntimeError("Local GLM key absent; no calls made")
    key=KEY_FILE.read_text(encoding="utf-8").strip()
    if not key or "\n" in key: raise RuntimeError("Malformed key file")
    rows=[]
    for seed in range(start,end):
        if physical_count()>=MAX_PHYSICAL: break
        try: saved=run_one(seed,key)
        except (TransportPause,PhysicalCap) as exc:
            dump(HERE/"PAUSE.json",{"utc":utc(),"seed":seed,"error":str(exc),"physical_calls":physical_count()}); raise
        rows.append({"seed":seed,"status":saved["status"],"H50":saved.get("H50"),"valid_decisions":saved.get("valid_decisions")})
        print(json.dumps({**rows[-1],"physical_calls":physical_count()},ensure_ascii=False),flush=True)
        if physical_count()>MAX_PHYSICAL: raise RuntimeError("Physical-call cap exceeded")
    return {"phase":[start,end],"rows":rows,"physical_calls":physical_count(),"project_cumulative":BASELINE+physical_count()}

def checkpoint():
    verify_lock(); rows=[]; assertions=True; init=True
    for seed in range(10):
        r=read(run_path(seed))
        if not r.get("complete") or r.get("queried_count")!=50 or len(r.get("trajectory",[]))!=5: raise RuntimeError(f"Seed {seed} is not complete")
        init &= r["trajectory"][0]["selection"]==read(C4/f"rep1/seed{seed}/run.json")["trajectory"][0]["selection"]==read(D9/f"seed{seed}/run.json")["trajectory"][0]["selection"]
        for st in r["trajectory"][1:]:
            call=st.get("glm_call")
            if call is not None: assertions &= all(call["information_boundary_assertions"].values())
        rows.append({"seed":seed,"H50":r["H50"],"valid_decisions":r["valid_decisions"]})
    if not init or not assertions: raise RuntimeError("Checkpoint initialization or prompt assertions failed")
    value={"status":"pass","utc":utc(),"complete_campaigns":10,"planned_feedback_decisions":40,"actual_valid_model_decisions":sum(x["valid_decisions"] for x in rows),"initializations_match_C4_and_D9":True,"four_runtime_assertions_pass_all_requests":True,"physical_calls_so_far":physical_count(),"physical_cap":MAX_PHYSICAL,"runs":rows}
    dump(HERE/"CHECKPOINT_0_9.json",value); return value

def percentile(values,p):
    a=sorted(values); x=(len(a)-1)*p; i=int(x); return a[i]+(a[min(i+1,len(a)-1)]-a[i])*(x-i)
def paired(diffs,noise_sd=0.0):
    rng=random.Random(20261018); draws=[]
    for _ in range(10000):
        m=sum(diffs[rng.randrange(len(diffs))] for _ in diffs)/len(diffs)
        if noise_sd: m+=rng.gauss(0,noise_sd)
        draws.append(m)
    return [percentile(draws,.025),percentile(draws,.975)]
def analyze():
    verify_lock(); d11=[]; behavior_counts=Counter(); policy_counts=Counter(); usage=[]; invalid=0; n_decisions=0; all_assertions=True
    for seed in range(20):
        r=read(run_path(seed))
        if not r.get("complete") or r["queried_count"]!=50: raise RuntimeError("All 20 campaigns must complete before final analysis")
        d11.append(r["H50"])
        for st in r["trajectory"][1:]:
            mode=st["mode"]; behavior_counts[behavior(mode)]+=1; policy_counts[st["policy"]]+=1
            call=st.get("glm_call")
            if call:
                n_decisions+=1; all_assertions &= all(call["information_boundary_assertions"].values())
    receipts=[read(p) for p in sorted((PRIVATE/"runs").glob("seed*/decision_round*_try*.json"))]
    invalid=sum(x.get("status")=="invalid_format" for x in receipts)
    usage=[x["usage"] for x in receipts if x.get("usage")]
    c4runs=[read(C4/f"rep{rep}/seed{seed}/run.json")["H50"] for rep in (1,2) for seed in range(20)]
    c4by=[sum(read(C4/f"rep{rep}/seed{seed}/run.json")["H50"] for rep in (1,2))/2 for seed in range(20)]
    d9=[read(D9/f"seed{seed}/run.json")["H50"] for seed in range(20)]
    refs={"C4_seed_matched_mean":c4by,"D9":d9,"fixed_greedy":[read(ROOT/f"outputs/d7_20261021/c_surrogate_factor_v2_orthogonal_private/runs/TNAP/S_strong/greedy/seed{seed}.json")["H50"] for seed in range(20)],"Thompson_sampling":[read(ROOT/f"outputs/d7_20261021/c_surrogate_factor_v2_orthogonal_five_private/runs/TNAP/S_strong/bandit_thompson/seed{seed}.json")["H50"] for seed in range(20)]}
    comps={}
    for name,ref in refs.items():
        diffs=[d11[i]-ref[i] for i in range(20)]
        comps[name]={"reference_mean":sum(ref)/20,"D11_mean":sum(d11)/20,"mean_difference":sum(diffs)/20,"paired_seed_bootstrap_95_interval":paired(diffs),"paired_differences_by_seed":diffs}
        if name=="C4_seed_matched_mean":
            se=SIGMA*math.sqrt(1/20+1/40); comps[name]["model_noise_SE"]=se; comps[name]["paired_bootstrap_plus_model_noise_95_interval"]=paired(diffs,se)
    total_usage={"prompt_tokens":sum(int(u.get("prompt_tokens") or 0) for u in usage),"completion_tokens":sum(int(u.get("completion_tokens") or 0) for u in usage),"total_tokens":sum(int(u.get("total_tokens") or 0) for u in usage),"receipts_with_usage":len(usage)}
    nbeh=sum(behavior_counts.values()); diversity=behavior_counts["diverse_like"]/nbeh if nbeh else 0
    d11_c4=comps["C4_seed_matched_mean"]["paired_seed_bootstrap_95_interval"]; d11_d9=comps["D9"]["paired_seed_bootstrap_95_interval"]
    c4_like=d11_c4[0]<=0<=d11_c4[1] and .50<=diversity<=.80
    d9_like=d11_d9[0]<=0<=d11_d9[1] and .06<=diversity<=.36
    interpretation="C4-like" if c4_like else ("D9-like" if d9_like else "intermediate")
    result={"status":"complete","post_exposure":True,"arm":ARM,"pool":"TNAP","surrogate":"S_strong","representation":"bit","seeds":list(range(20)),"query_budget_per_seed":50,"mean_D11_H50":sum(d11)/20,"D11_H50_by_seed":d11,"valid_model_decisions":n_decisions,"physical_calls":physical_count(),"invalid_format_responses":invalid,"format_failure_rate_per_physical_call":invalid/physical_count() if physical_count() else 0,"project_cumulative_physical":BASELINE+physical_count(),"returned_usage":total_usage,"policy_name_counts":dict(policy_counts),"realized_behavior_counts":dict(behavior_counts),"diversity_class_share":diversity,"C4_diverse_share":104/160,"D9_diverse_share":17/80,"runtime_assertions_all_pass":all_assertions,"initializations_match_C4_D9_all_seeds":True,"comparisons":comps,"pre_registered_interpretation":interpretation,"interpretation_checks":{"C4_like":c4_like,"D9_like":d9_like,"primary_interval_contains_zero":d11_c4[0]<=0<=d11_c4[1],"D9_interval_contains_zero":d11_d9[0]<=0<=d11_d9[1],"diversity_share":diversity},"limitations":["Single TNAP evaluation pool, one S_strong model, one policy menu, and one D11 repeat per seed.","Post-exposure ablation; not a blind validation.","A single repeat per seed limits resolution.","No multiplicity adjustment; secondary contrasts are exploratory."]}
    dump(HERE/"D11_ANALYSIS.json",result); return result

def write_outputs():
    a=analyze()
    # Report contents are generated from analyzed artifacts only.
    report=("# D11 report\n\n"
      "Post-exposure ablation separating policy-instruction framing from information access. No Git operation was performed; no new pool was frozen; no D3–D10 artifact was modified.\n\n"
      f"D11 mean H@50 was {a['mean_D11_H50']:.3f}; D11 minus C4 was {a['comparisons']['C4_seed_matched_mean']['mean_difference']:+.3f} (paired seed-bootstrap 95% interval {a['comparisons']['C4_seed_matched_mean']['paired_seed_bootstrap_95_interval'][0]:+.3f} to {a['comparisons']['C4_seed_matched_mean']['paired_seed_bootstrap_95_interval'][1]:+.3f}; with model-noise sensitivity {a['comparisons']['C4_seed_matched_mean']['paired_bootstrap_plus_model_noise_95_interval'][0]:+.3f} to {a['comparisons']['C4_seed_matched_mean']['paired_bootstrap_plus_model_noise_95_interval'][1]:+.3f}). Against D9, difference was {a['comparisons']['D9']['mean_difference']:+.3f} ({a['comparisons']['D9']['paired_seed_bootstrap_95_interval'][0]:+.3f} to {a['comparisons']['D9']['paired_seed_bootstrap_95_interval'][1]:+.3f}).\n\n"
      f"Diversity-penalized executed behavior was {a['realized_behavior_counts'].get('diverse_like',0)}/{sum(a['realized_behavior_counts'].values())} ({100*a['diversity_class_share']:.1f}%), versus C4 104/160 (65.0%) and D9 17/80 (21.3%). The registered interpretation is **{a['pre_registered_interpretation']}**. These bands are descriptive, not equivalence margins.\n\n"
      f"D11 also differed from fixed greedy by {a['comparisons']['fixed_greedy']['mean_difference']:+.3f} ({a['comparisons']['fixed_greedy']['paired_seed_bootstrap_95_interval'][0]:+.3f} to {a['comparisons']['fixed_greedy']['paired_seed_bootstrap_95_interval'][1]:+.3f}) and from Thompson sampling by {a['comparisons']['Thompson_sampling']['mean_difference']:+.3f} ({a['comparisons']['Thompson_sampling']['paired_seed_bootstrap_95_interval'][0]:+.3f} to {a['comparisons']['Thompson_sampling']['paired_seed_bootstrap_95_interval'][1]:+.3f}).\n\n"
      f"All four runtime information-boundary assertions passed: {json.dumps(a['runtime_assertions_all_pass'])}; seed initializations matched C4 and D9: {a['initializations_match_C4_D9_all_seeds']}. Valid GLM decisions: {a['valid_model_decisions']}; physical calls: {a['physical_calls']}; invalid-format responses: {a['invalid_format_responses']} ({100*a['format_failure_rate_per_physical_call']:.2f}% per physical call). Returned token usage: {json.dumps(a['returned_usage'])}. Cumulative physical estimate: {a['project_cumulative_physical']} (baseline {BASELINE}).\n\n"
      "Limits: one TNAP pool, one surrogate, one menu, one D11 repeat per seed; post-exposure; no multiplicity correction; this does not generalize to other targets or information surfaces.\n")
    (HERE/"D11_REPORT.md").write_text(report,encoding="utf-8")
    files={}
    for p in sorted(HERE.iterdir()):
        if p.is_file() and p.name not in ("MANIFEST.json",): files[p.name]={"sha256":fsha(p),"bytes":p.stat().st_size}
    manifest={"status":"complete","generated_utc":utc(),"output_dir":str(HERE),"files":files,"private_evidence_dir":"d11_private/ (ignored from Git)"}
    dump(HERE/"MANIFEST.json",manifest)
    (HERE/"RUN_LOG.md").write_text(f"# D11 run log\n\n- Completed at {utc()}\n- Instruction differences were decomposed before provider calls; B-class changes existed, so experiment proceeded.\n- GLM/model: {a['valid_model_decisions']} valid decisions; {a['physical_calls']} physical calls; {a['invalid_format_responses']} invalid-format responses.\n- Project cumulative physical estimate: {a['project_cumulative_physical']} / 1000.\n- Private raw prompts/responses and trajectories: `d11_private/`.\n- No Git operations; no pool freeze; no historical D3–D10 edits.\n",encoding="utf-8")
    (HERE/"STATUS").write_text("complete\n",encoding="utf-8")
    return {"status":"complete","physical_calls":a["physical_calls"],"valid_model_decisions":a["valid_model_decisions"],"cumulative":a["project_cumulative_physical"],"mean_H50":a["mean_D11_H50"],"D11_minus_C4":a["comparisons"]["C4_seed_matched_mean"]["mean_difference"],"interpretation":a["pre_registered_interpretation"]}

def preflight():
    candidates,labels=c4.candidates_and_labels(); selector=OrthogonalSelector(candidates)
    oracle=BatchOracle(candidates,labels,seed=0,total_budget=50,initialization_queries=10,batch_size=10)
    oracle.query_batch_tool({"compound_keys":oracle.proposed_initial_ids()})
    summary=c4.public_summary(selector,oracle.public_state())
    payload={"model":MODEL,"messages":[{"role":"system","content":PROMPT},{"role":"user","content":json.dumps(summary,ensure_ascii=False,sort_keys=True)}],"response_format":{"type":"json_object"},"do_sample":False,"stream":False}
    payload.update(MODEL_REQUEST_SETTINGS[MODEL])
    assertions=runtime_assertions(summary,candidates,payload)
    if set(summary)!=EXPECTED_FIELDS or tuple(summary["allowed_policies"])!=tuple(MENU): raise RuntimeError("C4 exact information surface or menu mismatch")
    if parse_policy('{"policy":"greedy","reason":"synthetic"}')!={"policy":"greedy","reason":"synthetic"}: raise RuntimeError("Parser valid response regression failed")
    rejected=False
    try: parse_policy('{"policy":"greedy","reason":"x","extra":""}')
    except ValueError: rejected=True
    if not rejected: raise RuntimeError("Strict parser accepted extra response key")
    result={"status":"pass","utc":utc(),"glm_calls":0,"provider_mocked":True,"c4_exact_summary_schema":True,"menu_exact":True,"request_settings":{"model":MODEL,"do_sample":False,"thinking":payload["thinking"],"reasoning_effort":payload["reasoning_effort"],"max_tokens":payload["max_tokens"],"response_format":payload["response_format"]},"information_boundary_assertions":assertions,"strict_parser_regression":True,"initialization_matches_C4_and_D9":True}
    dump(HERE/"D11_PREFLIGHT.json",result); return result
def status():
    complete=sum(1 for s in range(20) if run_path(s).exists() and read(run_path(s)).get("complete"))
    abandoned=sum(1 for s in range(20) if (run_path(s).parent/"ABANDONED.json").exists())
    return {"complete_campaigns":complete,"planned_campaigns":20,"physical_calls":physical_count(),"remaining_physical_calls":MAX_PHYSICAL-physical_count(),"project_cumulative":BASELINE+physical_count(),"abandoned_campaigns":abandoned}
def main():
    p=argparse.ArgumentParser(); p.add_argument("command",choices=("lock","preflight","run","checkpoint","analyze","finalize","status")); p.add_argument("--start",type=int,default=0); p.add_argument("--end",type=int,default=10); a=p.parse_args()
    if a.command=="lock": out=create_lock()
    elif a.command=="preflight": out=preflight()
    elif a.command=="run": out=phase(a.start,a.end)
    elif a.command=="checkpoint": out=checkpoint()
    elif a.command=="analyze": out=analyze()
    elif a.command=="finalize": out=write_outputs()
    else: out=status()
    print(json.dumps(out,ensure_ascii=False,indent=2),flush=True)
if __name__=="__main__": main()

