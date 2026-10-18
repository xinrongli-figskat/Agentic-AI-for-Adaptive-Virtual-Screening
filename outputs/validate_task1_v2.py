"""Local delivery validation; does not call GLM, change old runs, or start campaigns."""
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'outputs'))
from curation_agent_v2.engine import read,save,sha
from curation_agent_v2.run import prepare,load_engine,source_hashes


def verify_tree(folder,wanted):
    actual={p.relative_to(folder).as_posix():sha(p) for p in folder.rglob('*') if p.is_file()}
    if actual!=wanted:raise ValueError('Historical tree changed: '+str(folder))
    return len(wanted)


def main():
    out=ROOT/'outputs/task1_v2_validation';out.mkdir(exist_ok=True)
    prior=ROOT/'outputs/results/task1_v1_finished_evidence/curation_20261015T034434Z_d2828e13'
    original=read(ROOT/'outputs/source_alignment_20261015/final_audit/input_sha256.json')['historical_run']
    unchanged_old_run=verify_tree(prior,original)
    wanted=read(ROOT/'.sync_audit/task1_v2_development/v1_source_hashes_before.json')
    if any(sha(ROOT/k)!=v for k,v in wanted.items()):raise ValueError('Old Task1 v1 source changed')
    syntax_count=0
    for path in (ROOT/'outputs/curation_agent_v2').rglob('*.py'):
        ast.parse(path.read_text(encoding='utf-8'),feature_version=(3,10));syntax_count+=1
    env=dict(os.environ);env['PYTHONPATH']=str(ROOT/'outputs')+os.pathsep+env.get('PYTHONPATH','')
    temp=ROOT/'.cache/task1-v2-tests';temp.mkdir(parents=True,exist_ok=True)
    env['TMP']=env['TEMP']=str(temp);env['PYTHONIOENCODING']='utf-8'
    tested=subprocess.run([sys.executable,'-B','-m','unittest','-v','curation_agent_v2.test_agent'],
        cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8')
    log=tested.stdout+tested.stderr
    (out/'unittest.log').write_text(log,encoding='utf-8')
    if tested.returncode:raise RuntimeError(log)
    folder=prepare(prior,ROOT/'.cache/task1_v2_validated_prepare')
    engine=load_engine(folder);context=engine.context()
    context_characters=len(json.dumps(context,ensure_ascii=False,sort_keys=True))
    if context_characters>24000 or engine.state['requests'] or engine.state['llm_attempts']:
        raise ValueError('Offline preparation or compact context check failed')
    old_context=read(prior/'llm/0025.json')['request']['messages'][1]['content']
    probe=out/'api_probe_20261015';requests=read(probe/'requests.json')
    for r in requests:
        if sha(probe/r['raw_file'])!=r['sha256'] or r['http_status']!=200:
            raise ValueError('Public interface probe receipt hash/status mismatch')
    verify_tree(prior,original)
    if any(sha(ROOT/k)!=v for k,v in wanted.items()):raise ValueError('Old Task1 v1 source changed during validation')
    receipt={'status':'LOCAL_V2_DELIVERY_VALIDATION_PASSED','offline_tests':15,
        'test_log_sha256':sha(out/'unittest.log'),'python_310_syntax_files':syntax_count,
        'historical_run_files_unchanged':unchanged_old_run,'historical_v1_code_files_unchanged':len(wanted),
        'imported_profiles':len(engine.state['seed_profiles']),'known_assays':len(engine.state['known_assays']),
        'catalog_size':len(engine.catalog),'offline_prepare_http_requests':0,'offline_prepare_llm_requests':0,
        'compact_context_characters':context_characters,'prior_last_context_characters':len(old_context),
        'context_comparison_limitation':'Different stages/runs; illustration of default state size only, not a paired cost or discovery-effect experiment.',
        'source_hashes':source_hashes(),'environment':engine.state['environment'],
        'public_api_probe':read(probe/'result.json'),'real_glm_search_started':False,'campaign_ready':False}
    save(out/'validation_receipt.json',receipt)
    print(json.dumps({k:v for k,v in receipt.items() if k not in ['source_hashes','public_api_probe']},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
