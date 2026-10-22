from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'outputs'));sys.path.insert(0,str(ROOT/'outputs/d7_20261021/c_surrogate_factor/runtime_packages'))
from outputs.d7_20261021.c4_five import run_c4 as c4
from outputs.d7_20261021.c_surrogate_factor_v2_orthogonal.c3_core import OrthogonalSelector
from outputs.d7_20261021.c_surrogate_factor_v2_orthogonal.run_meta_five import MENU
from oracle_boundary_v0.oracle_boundary import BatchOracle
from run_d11 import PROMPT,MODEL,EXPECTED_FIELDS,PRIVATE,physical_count
from outputs.campaign_v0.glm_api import MODEL_REQUEST_SETTINGS

def sha(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
candidates,labels=c4.candidates_and_labels(); selector=OrthogonalSelector(candidates)
checks=[]
for path in sorted((PRIVATE/'http').glob('http_*.json')):
    rec=read(path); seed=rec['seed']; round_no=rec['round']
    run=read(PRIVATE/'runs'/f'seed{seed}'/'run.json')
    oracle=BatchOracle(candidates,labels,seed=seed,total_budget=50,initialization_queries=10,batch_size=10)
    for step in run['trajectory']:
        if step['stage']>=round_no: break
        answer=oracle.query_batch_tool({'compound_keys':step['selection']})
        if answer['observations']!=step['observations']:raise RuntimeError(f'oracle replay mismatch {path}')
    summary=c4.public_summary(selector,oracle.public_state())
    if set(summary)!=EXPECTED_FIELDS or tuple(summary['allowed_policies'])!=tuple(MENU):raise RuntimeError(f'summary schema/menu mismatch {path}')
    payload={'model':MODEL,'messages':[{'role':'system','content':PROMPT},{'role':'user','content':json.dumps(summary,ensure_ascii=False,sort_keys=True)}],'response_format':{'type':'json_object'},'do_sample':False,'stream':False}
    payload.update(MODEL_REQUEST_SETTINGS[MODEL]); digest=sha(json.dumps(payload).encode('utf-8'))
    if digest!=rec['request_body_sha256']:raise RuntimeError(f'body digest mismatch {path}')
    if not all(rec.get('information_boundary_assertions',{}).values()):raise RuntimeError(f'assertion false/missing {path}')
    checks.append({'http_index':rec['index'],'seed':seed,'round':round_no,'status':rec['status'],'request_body_matches_reconstructed_C4_summary':True,'four_information_boundary_assertions':rec['information_boundary_assertions']})
if len(checks)!=82:raise RuntimeError(f'expected 82 physical attempts, got {len(checks)}')
result={'status':'pass','physical_attempts_checked':len(checks),'provider_responses':sum(x['status']=='response_received' for x in checks),'transport_failures':sum(x['status']=='transport_error' for x in checks),'all_attempts_used_exact_D11_prompt_and_reconstructed_C4_payload':True,'all_four_assertions_passed_for_every_attempt':True,'per_attempt':checks}
out=HERE/'D11_RUNTIME_AUDIT.json';out.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8');print(json.dumps({k:v for k,v in result.items() if k!='per_attempt'},ensure_ascii=False,indent=2))
