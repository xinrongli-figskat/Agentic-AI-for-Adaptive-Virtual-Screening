"""Authorized D7-B recovery with a 380-physical-request cap and one format retry."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT=Path('/driveA/xinrong/agentic-screening')
sys.path.insert(0,str(ROOT))
from outputs.d7_20261021.b_model_variance import b_repeat as old
from outputs.d5_20261020.e_menu import run_extended as frozen
from campaign_v0.glm_api import SYSTEM_PROMPT,MODEL_REQUEST_SETTINGS

BASE=old.BASE
PRIVATE=old.PRIVATE
MAX_PHYSICAL=380
PROMPT_DIGEST='cc8f7d110338cc71bad7ed5f5cd5ca1b6ea0ab5f05282cb4a0cd48c1efae9698'
MARKER='3dc0bc7579c9faf376f2c8818f1c7546d9b22db549d167080b04c099ae18c462'


class PhysicalBudgetReached(RuntimeError): pass
class FormatRetryExhausted(RuntimeError): pass


def physical_count():
    return len(list(PRIVATE.glob('rep*/seed*/http_*.json')))


def request_digest(summary):
    payload={'model':'glm-5.3-flash','messages':[
        {'role':'system','content':SYSTEM_PROMPT},
        {'role':'user','content':json.dumps(summary,ensure_ascii=False,sort_keys=True)}],
        'response_format':{'type':'json_object'},'do_sample':False,'stream':False}
    payload.update(MODEL_REQUEST_SETTINGS['glm-5.3-flash'])
    return hashlib.sha256(json.dumps(payload).encode('utf-8')).hexdigest()


def state_marker(seed,state):
    return hashlib.sha256(json.dumps({'seed':seed,'round':state['next_round'],
        'revealed':state['revealed']},sort_keys=True).encode()).hexdigest()


def lock():
    old.verify_lock()
    prompt=json.loads((BASE/'B_PROMPT_RECONSTRUCTION.json').read_text())
    assert prompt['failure_event_state_marker_matches'] and prompt['state_marker']==MARKER
    assert prompt['request_body_sha256_reconstructed']==PROMPT_DIGEST
    assert physical_count()==94
    historic=json.loads((PRIVATE/'PRIVATE_MANIFEST_TIER_B.json').read_text())
    for relative,digest in historic['files'].items():
        assert old.sha(PRIVATE/relative)==digest,relative
    files=['B_ADDENDUM_AFTER_TIER_B.md','b_resume_v2.py','B_PROMPT_RECONSTRUCTION.json',
           'B_LOCK.json','CLOSEOUT_TIER_B.json','MANIFEST_TIER_B.json']
    out={'utc':old.utc(),'status':'locked_before_resumption','max_new_physical_requests':380,
         'existing_physical_requests':94,'failed_state_marker':MARKER,
         'failed_prompt_reconstruction_sha256':PROMPT_DIGEST,
         'historic_private_manifest_sha256':old.sha(PRIVATE/'PRIVATE_MANIFEST_TIER_B.json'),
         'files':{name:old.sha(BASE/name) for name in files}}
    old.save(BASE/'B_ADDENDUM_LOCK.json',out)
    return {'status':out['status'],'lock_sha256':old.sha(BASE/'B_ADDENDUM_LOCK.json'),
            'utc':out['utc'],'physical_requests':physical_count()}


def verify_lock():
    lock_data=json.loads((BASE/'B_ADDENDUM_LOCK.json').read_text())
    for name,digest in lock_data['files'].items():
        assert old.sha(BASE/name)==digest,name
    assert old.sha(PRIVATE/'PRIVATE_MANIFEST_TIER_B.json')==lock_data['historic_private_manifest_sha256']
    assert 94<=physical_count()<=MAX_PHYSICAL
    old.verify_lock()
    return lock_data


class BudgetClient(old.TrackedClient):
    def __init__(self,receipt_dir,seed,rep):
        super().__init__(receipt_dir)
        self.seed,self.rep=seed,rep
        self.marker=None

    def _opener(self,request,timeout):
        if physical_count()>=MAX_PHYSICAL:
            raise PhysicalBudgetReached('D7-B 380 physical HTTP requests reached before network')
        return super()._opener(request,timeout)

    def __call__(self,summary):
        if physical_count()>=MAX_PHYSICAL:
            raise PhysicalBudgetReached('D7-B 380 physical HTTP requests reached before network')
        self.last_summary=summary
        digest=request_digest(summary)
        if (self.seed,self.rep,self.marker)==(13,2,MARKER):
            assert digest==PROMPT_DIGEST,'Resumed prompt differs from locked reconstruction'
        self.decision_idx+=1
        target=self.receipt_dir/f'decision_{self.decision_idx:03d}.json'
        started=time.perf_counter()
        first_http=self.http_idx+1
        common={'seed':self.seed,'repeat':self.rep,'state_marker':self.marker,
                'request_body_sha256':digest}
        try:
            content=self.inner(summary)
            self.last_usage=self.inner.last_usage
            self.last_request_id=self.inner.last_request_id
            self.last_attempt_log=self.inner.last_attempt_log
            old.save(target,{**common,'utc':old.utc(),'status':'success',
                'raw_content':content,'request_id':self.last_request_id,'usage':self.last_usage,
                'api_attempt_log':self.last_attempt_log,
                'http_attempts':list(range(first_http,self.http_idx+1)),
                'elapsed_seconds':time.perf_counter()-started})
            return content
        except Exception as exc:
            self.last_usage=self.inner.last_usage
            self.last_request_id=self.inner.last_request_id
            self.last_attempt_log=self.inner.last_attempt_log
            old.save(target,{**common,'utc':old.utc(),'status':'failure',
                'error_type':type(exc).__name__,'error':str(exc),
                'request_id':self.last_request_id,'usage':self.last_usage,
                'api_attempt_log':self.last_attempt_log,
                'http_attempts':list(range(first_http,self.http_idx+1)),
                'elapsed_seconds':time.perf_counter()-started})
            raise


def prior_format_failures(run_dir,client,marker):
    count=0
    path=run_dir/'failure_events.json'
    if path.exists():
        for e in json.loads(path.read_text()):
            if e.get('state_marker')==marker and e.get('error_type')=='ValueError' and \
                    e.get('message')=='Invalid D5 GLM policy JSON; no oracle query was made':
                count+=1
    # New invalid responses are durable even if the process exits before the
    # failure-event writer runs. The historical D6-format failure lacks a marker
    # in its decision receipt, so it is counted only from failure_events.json.
    for receipt in client.receipt_dir.glob('decision_*.json'):
        d=json.loads(receipt.read_text())
        if d.get('state_marker')!=marker or d.get('status')!='success':
            continue
        try:
            parsed=json.loads(d['raw_content'])
            invalid=(set(parsed)!={'policy','reason'} or not isinstance(parsed.get('reason'),str)
                     or not isinstance(parsed.get('policy'),str))
        except (ValueError,TypeError,AttributeError):
            invalid=True
        if invalid: count+=1
    return count


def run(seed,rep):
    verify_lock()
    assert 0<=seed<20 and 1<=rep<=5
    if rep==1 and seed<10:
        row=old.inspect_run(old.D6/f'glm_extended_seed{seed}'/'run.json',seed)
        return {'seed':seed,'repeat':rep,'status':'reused_d6','H50':row['H50'],
                'new_physical_requests_total':physical_count()}
    receipt_dir=PRIVATE/f'rep{rep}'/f'seed{seed}'
    abandoned=receipt_dir/'ABANDONED.json'
    if abandoned.exists():
        return {'seed':seed,'repeat':rep,'status':'abandoned_after_two_format_errors',
                'new_physical_requests_total':physical_count()}
    frozen.PRIVATE_OUT=PRIVATE/f'rep{rep}'
    client=BudgetClient(receipt_dir,seed,rep)
    OriginalController=frozen.Controller
    run_dir=frozen.PRIVATE_OUT/'runs/tnap/bit'/f'glm_extended_seed{seed}'

    class ControllerRetry(OriginalController):
        def choose(self,state):
            marker=state_marker(seed,state)
            client.marker=marker
            used=prior_format_failures(run_dir,client,marker)
            if used>=2:
                raise FormatRetryExhausted('Two format errors at the same decision state')
            while used<2:
                before=physical_count()
                try:
                    return super().choose(state)
                except ValueError as exc:
                    if str(exc)!='Invalid D5 GLM policy JSON; no oracle query was made':
                        raise
                    after=physical_count()
                    assert after>before,'Format failure without a physical provider response'
                    used+=1
                    old.save(client.receipt_dir/f'format_error_{client.decision_idx:03d}.json',
                        {'utc':old.utc(),'state_marker':marker,'format_attempt_number':used,
                         'request_body_sha256':request_digest(client_last_summary(client)),
                         'decision_receipt':f'decision_{client.decision_idx:03d}.json',
                         'physical_request_count':after})
                    if used>=2:
                        raise FormatRetryExhausted('Two format errors at the same decision state') from exc
            raise AssertionError('unreachable')

    frozen.Controller=ControllerRetry
    try:
        result=frozen.run_one('tnap','bit',seed,'glm_extended',client=client)
    except FormatRetryExhausted as exc:
        old.save(abandoned,{'utc':old.utc(),'seed':seed,'repeat':rep,
                            'reason':str(exc),'no_fallback_policy':True,
                            'physical_requests_total':physical_count()})
        return {'seed':seed,'repeat':rep,'status':'abandoned_after_two_format_errors',
                'new_physical_requests_total':physical_count()}
    finally:
        frozen.Controller=OriginalController
    row=old.inspect_run(old.run_path(frozen.PRIVATE_OUT,seed),seed)
    assert result['H50']==row['H50']
    return {'seed':seed,'repeat':rep,'status':'complete','H50':row['H50'],
            'new_physical_requests_total':physical_count()}


def client_last_summary(client):
    # Filled by BudgetClient.__call__ before the request; no label data added.
    return client.last_summary


def main():
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('lock')
    q=sub.add_parser('run');q.add_argument('--seed',type=int,required=True);q.add_argument('--rep',type=int,required=True)
    sub.add_parser('status')
    a=p.parse_args()
    if a.command=='lock': out=lock()
    elif a.command=='run': out=run(a.seed,a.rep)
    else:
        verify_lock()
        complete=10
        abandoned=0
        for rep in range(1,6):
            for seed in range(20):
                if rep==1 and seed<10: continue
                rp=old.run_path(PRIVATE/f'rep{rep}',seed)
                if rp.exists() and json.loads(rp.read_text()).get('complete'): complete+=1
                if (PRIVATE/f'rep{rep}'/f'seed{seed}'/'ABANDONED.json').exists(): abandoned+=1
        out={'complete_campaigns':complete,'abandoned_repeats':abandoned,
             'new_physical_requests_total':physical_count(),'remaining_to_380':380-physical_count()}
    print(json.dumps(out,ensure_ascii=False))


if __name__=='__main__': main()
