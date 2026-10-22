"""Reconstruct the failed decision input offline, without an API request."""
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path('/driveA/xinrong/agentic-screening')
sys.path.insert(0,str(ROOT))
PUB = ROOT/'outputs/d7_20261021/b_model_variance'
PRIV = ROOT/'outputs/d7_20261021/b_model_variance_private'

from outputs.d5_20261020.e_menu import run_extended as frozen
from outputs.d5_20261020.e_menu.expanded_tools import ExpandedTools
from oracle_boundary_v0.oracle_boundary import BatchOracle
from campaign_v0.glm_api import SYSTEM_PROMPT, MODEL_REQUEST_SETTINGS


class CaptureOnly(Exception):
    pass


class CaptureClient:
    def __init__(self): self.summary=None
    def __call__(self,summary): self.summary=summary; raise CaptureOnly()


def main():
    frozen.validate_sources()
    path=PRIV/'rep2/runs/tnap/bit/glm_extended_seed13'
    saved=json.loads((path/'run.json').read_text())
    assert not saved['complete'] and len(saved['trajectory'])==2
    candidates,labels=frozen.load_pool('tnap')
    oracle=BatchOracle(candidates,labels,seed=13,total_budget=50,
                       initialization_queries=10,batch_size=10)
    for step in saved['trajectory']:
        response=oracle.query_batch_tool({'compound_keys':step['selection']})
        assert response['observations']==step['observations']
    state=oracle.public_state()
    state['numerical_summary']=ExpandedTools(candidates,'bit').legacy.describe_state(state)
    marker=hashlib.sha256(json.dumps({'seed':13,'round':state['next_round'],
                                     'revealed':state['revealed']},sort_keys=True).encode()).hexdigest()
    failures=json.loads((path/'failure_events.json').read_text())
    assert len(failures)==1 and failures[0]['state_marker']==marker
    capture=CaptureClient()
    try: frozen.Controller('glm_extended',13,client=capture).choose(state)
    except CaptureOnly: pass
    else: raise AssertionError('No captured prompt')
    summary=capture.summary
    assert summary and set(summary)=={'task','candidate_count','queried_count',
        'remaining_budget','next_round','revealed_hits','recent_revealed_hits',
        'numerical_summary','allowed_policies','policy_descriptions','commitment_note'}
    assert summary['queried_count']==20 and summary['next_round']==2
    payload={'model':'glm-5.3-flash','messages':[
        {'role':'system','content':SYSTEM_PROMPT},
        {'role':'user','content':json.dumps(summary,ensure_ascii=False,sort_keys=True)}],
        'response_format':{'type':'json_object'},'do_sample':False,'stream':False}
    payload.update(MODEL_REQUEST_SETTINGS['glm-5.3-flash'])
    body=json.dumps(payload).encode('utf-8')
    prompt_digest=hashlib.sha256(body).hexdigest()
    result={'seed':13,'repeat':2,'failed_decision':2,'saved_queries':20,
        'state_marker':marker,'failure_event_state_marker_matches':True,
        'locked_controller_source_sha256':frozen.sha(ROOT/'outputs/d5_20261020/e_menu/run_extended.py'),
        'public_summary_keys':sorted(summary),'request_body_sha256_reconstructed':prompt_digest,
        'reconstruction_note':'The original HTTP request body was not separately retained. Its state marker matches the checkpoint; unchanged D5 code deterministically regenerates this payload. A bytewise historical request-body comparison is unavailable.'}
    output=PUB/'B_PROMPT_RECONSTRUCTION.json'
    assert not output.exists()
    output.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    private=PRIV/'failed_prompt_reconstruction.json'
    assert not private.exists()
    private.write_text(json.dumps({'summary':summary,'payload_without_authorization_header':payload,
                                   'reconstruction':result},indent=2,ensure_ascii=False,sort_keys=True)+'\n')
    os.chmod(private,0o600)
    print(json.dumps(result))

if __name__=='__main__': main()
