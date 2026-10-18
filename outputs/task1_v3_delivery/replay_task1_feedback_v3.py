"""Re-render actual historical states with repaired feedback; never call a model/tool."""
import copy
import argparse
import csv
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT if (ROOT/'curation_agent_v3').is_dir() else ROOT/'outputs'))

from curation_agent_v3.engine import read,save
from curation_agent_v3.feedback import Engine
from curation_agent_v3.integrity import inventory,model_context,visible_metadata
from curation_agent_v3.run import PACKAGE

RUN=ROOT/'outputs/results/task1_v21_closed_20261015/run'


def emitted_ids(value):
    result=[]
    if isinstance(value,dict):
        for key,v in value.items():
            if key in ('evidence_id','basis_evidence_id') and isinstance(v,str) and v.startswith('E'):result.append(int(v[1:]))
            elif isinstance(v,(dict,list)):result.extend(emitted_ids(v))
    elif isinstance(value,list):
        for v in value:result.extend(emitted_ids(v))
    return result


def apply_event(engine,event,final):
    action=event['decision']['action'];args=event['decision']['arguments'];result=event.get('result') or {};s=engine.state
    aid=args.get('assay_id');cache=aid in s['assays'] and action=='inspect_assay'
    if aid:s['active_assay_id']=aid;s['active_target_id']=s['known_assays'].get(aid)
    elif args.get('target_id'):s['active_target_id']=args['target_id'];s['active_assay_id']=None
    if event['status']=='success':
        if action=='screen_targets':
            for row in result['screened']:s['target_counts'][row['target_id']]=copy.deepcopy(row)
        elif action=='inspect_assay':
            if aid not in s['assays']:s['assays'][aid]={'summary':copy.deepcopy(result),'metadata':result['evidence_id']}
        elif action=='count_assay':s['assay_counts'][aid]=copy.deepcopy(result)
        elif action=='fetch_assay':s['assays'][aid]['acquisition']=copy.deepcopy(result)
        elif action=='curate_assay':s['assays'][aid]['curation']=copy.deepcopy(result)
        elif action=='assess_source':s['assays'][aid]['source_assessment']=copy.deepcopy(result)
        elif action=='decide_assay':s['assays'][aid]['decision']=copy.deepcopy(result)
        elif action=='list_assays':
            for row in result['rows']:s['known_assays'][row['assay_chembl_id']]=args['target_id']
        elif action=='read_evidence':
            s['last_evidence_view']=copy.deepcopy(result)
            s['evidence_views'].setdefault(args['evidence_id']+'|'+args['view'],[]).append([result['offset'],result['end']])
        ids=emitted_ids(result)
        if ids:
            limit=max(ids)
            for eid,e in final['evidence'].items():
                if int(eid[1:])<=limit:s['evidence'].setdefault(eid,copy.deepcopy(e))
        engine.record_feedback(action,args,result,cache_replay=cache)
    else:
        engine.record_feedback(action,args,error=ValueError(event.get('error','Recorded tool error')))


def replay(output_dir):
    before=inventory(RUN);final=read(RUN/'state.json')
    events=final['events'];tools=[e for e in events if e.get('kind')=='tool_action']
    if any(e['decision']['action']=='profile_target' for e in tools):raise ValueError('This replay expects the observed run with only pre-LLM target profiles')
    initial_limit=min(emitted_ids(tools[0]['result']))-1
    state=copy.deepcopy(final);state['protocol']=read(PACKAGE/'protocol.json')
    state.update(assays={},assay_counts={},events=[],shortlist=[],evidence_views={},last_evidence_view=None,last_tool_result=None,
                 active_assay_id=None,active_target_id=None)
    state['evidence']={k:copy.deepcopy(v) for k,v in final['evidence'].items() if int(k[1:])<=initial_limit}
    state['target_counts']={k:copy.deepcopy(v) for k,v in final['target_counts'].items() if int(v['evidence_id'][1:])<=initial_limit}
    state['known_assays']={}
    for p in list(state['seed_profiles'].values())+list(state['profiles'].values()):
        data=read(RUN/state['evidence'][p['evidence_id']]['path']);profile=data.get('profile',data)
        for row in profile['assay_profiles']:state['known_assays'][row['assay_chembl_id']]=p['target_id']
    initial_known=len(state['known_assays']);engine=Engine(RUN,state)
    out=Path(output_dir).resolve();out.mkdir(parents=True,exist_ok=False)
    rendered=out/'rendered_contexts';rendered.mkdir()
    metrics=[];done=set()
    for number in range(1,final['llm_attempts']+1):
        old=model_context(read(RUN/'llm'/f'{number:04d}.json'))
        for index,event in enumerate(events):
            n=event.get('llm_attempt',event.get('attempt'))
            if n is None or n>=number or index in done:continue
            done.add(index)
            if event.get('kind')=='tool_action':apply_event(engine,event,final)
            state['events'].append(copy.deepcopy(event))
        state['llm_attempts']=number-1;state['requests']=final['requests'][:final['protocol']['maximum_http_requests']-old['remaining_http_requests']]
        state['format_feedback']=copy.deepcopy(old.get('format_feedback'))
        state['last_evidence_view']=copy.deepcopy(old.get('last_evidence_view'))
        assert len(state['known_assays'])==old['assay_count'], ('assay state reconstruction mismatch',number)
        assert len(state['target_counts'])==old['screened_target_count'], ('target state reconstruction mismatch',number)
        for row in old['assay_preview']:
            current=state['assays'].get(row['assay_id'],{})
            assert current.get('metadata')==row.get('metadata_evidence_id'), ('metadata timing mismatch',number,row['assay_id'])
        new=engine.context();save(rendered/f'{number:04d}_repaired.json',new)
        preceding=next((e for e in reversed(tools) if e['llm_attempt']<number),None)
        action=preceding['decision']['action'] if preceding else None
        aid=preceding['decision']['arguments'].get('assay_id') if preceding else None
        eid=(preceding.get('result') or {}).get('evidence_id') if preceding else None
        old_visible=visible_metadata(old,aid,eid)[1] if action=='inspect_assay' else None
        payload=(new.get('last_tool_result') or {}).get('payload') or {}
        new_visible=payload.get('confidence_score') is not None if action=='inspect_assay' else None
        returned=(preceding.get('result') or {}).get('rows',[]) if action=='list_assays' else []
        ids=[r['assay_chembl_id'] for r in returned]
        old_text=json.dumps(old,ensure_ascii=False);new_text=json.dumps(new,ensure_ascii=False,sort_keys=True)
        metrics.append({'request':number,'preceding_tool_attempt':preceding['llm_attempt'] if preceding else None,
            'preceding_tool':action,'old_structured_confidence_visible':old_visible,'new_direct_confidence_visible':new_visible,
            'returned_assay_ids':len(ids),'old_returned_ids_in_input':sum(i in old_text for i in ids),
            'new_returned_ids_in_input':sum(i in new_text for i in ids),'old_context_characters':len(old_text),'new_context_characters':len(new_text)})
    with (out/'comparison.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(metrics[0]));writer.writeheader();writer.writerows(metrics)
    inspect=[r for r in metrics if r['preceding_tool']=='inspect_assay' and r['preceding_tool_attempt']==r['request']-1]
    lists=[r for r in metrics if r['preceding_tool']=='list_assays' and r['preceding_tool_attempt']==r['request']-1]
    assert inventory(RUN)==before
    assert len(inspect)==11 and sum(r['new_direct_confidence_visible'] for r in inspect)==11
    assert len(lists)==1 and lists[0]['old_returned_ids_in_input']==0 and lists[0]['new_returned_ids_in_input']==20
    assert all(r['new_context_characters']<=24000 for r in metrics)
    summary={'status':'ACTUAL_HISTORICAL_CONTEXT_REPLAY_PASSED','saved_requests_replayed':len(metrics),
        'reconstruction_checks':'Known assay/target counts and visible metadata acquisition timing match every original request.',
        'input_files_unchanged':len(before),'initial_known_assays_reconstructed':initial_known,
        'inspect_pairs':len(inspect),'old_direct_structured_confidence_visible':sum(r['old_structured_confidence_visible'] for r in inspect),
        'new_direct_confidence_visible':sum(r['new_direct_confidence_visible'] for r in inspect),
        'assay_list_pairs':len(lists),'old_list_ids_visible':lists[0]['old_returned_ids_in_input'],
        'new_list_ids_visible':lists[0]['new_returned_ids_in_input'],
        'maximum_new_context_characters':max(r['new_context_characters'] for r in metrics),
        'known_assays_in_final_state':len(final['known_assays']),
        'E0096_window':{k:read(RUN/final['evidence']['E0096']['path']).get(k) for k in ['target_chembl_id','records_retrieved','api_matching_IC50_records','retrieval_complete']},
        'E0145_description_delivery_intervals':final['evidence_views'].get('E0145|assay_description',[]),
        'real_llm_requests':0,'new_scientific_tool_calls':0,
        'limitations':['Re-rendered historical states; no counterfactual LLM decisions or improved discovery yield measured.',
            'New structured decision basis changes validation; information-availability comparison does not evaluate this policy effect.']}
    save(out/'summary.json',summary);print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--run-dir',type=Path,default=RUN)
    parser.add_argument('--output-dir',type=Path,required=True);args=parser.parse_args()
    RUN=args.run_dir.resolve();replay(args.output_dir)
