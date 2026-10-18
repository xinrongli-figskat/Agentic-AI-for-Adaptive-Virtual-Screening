"""Read-only Task1 run audit. Standard library only; no network or model calls."""
import argparse
from collections import Counter
import csv
from datetime import datetime,timezone
import hashlib
import json
import math
from pathlib import Path
import uuid


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def signature(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def safe(root,relative):
    path=(root/relative).resolve();path.relative_to(root.resolve());return path


def inventory(root):
    result={}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():raise ValueError('Symlinks are unsupported: '+str(path))
        if path.is_file() and path.name!='.writer.lock':result[path.relative_to(root).as_posix()]=sha(path)
    return result


def verify_inputs(root,state):
    checked=[]
    def check(relative,wanted):
        if sha(safe(root,relative))!=wanted:raise ValueError('Hash mismatch: '+relative)
        checked.append(relative)
    if signature(state['protocol'])!=state['protocol_sha256']:raise ValueError('Protocol hash mismatch')
    check('catalog.json',state['catalog_sha256']);check('prior_exposure.json',state['prior_exposure_sha256'])
    for name,wanted in state['code_sha256'].items():check('source_snapshot/'+name,wanted)
    for evidence in state['evidence'].values():check(evidence['path'],evidence['sha256'])
    for request in state['requests']:
        if request.get('sha256'):check(request['raw_file'],request['sha256'])
    ledger=None
    if state.get('continuation'):
        check('continuation.json',state['continuation']['ledger_sha256']);ledger=read(root/'continuation.json')
        for name,wanted in ledger['parent_files_sha256'].items():
            if name=='.writer.lock':continue
            relative='history_v2/'+name if name in ('state.json','report.json') or name.startswith('source_snapshot/') else name
            check(relative,wanted)
    if state.get('revision'):
        check('revision.json',state['revision']['ledger_sha256'])
        revision=read(root/'revision.json')
        for name,wanted in revision['parent_files_sha256'].items():
            relative='history_v21/'+name if name in ('state.json','report.json') or name.startswith('source_snapshot/') else name
            check(relative,wanted)
    return checked,ledger


def model_context(receipt):
    messages=(receipt.get('request') or {}).get('messages') or []
    content=next((m.get('content') for m in reversed(messages) if m.get('role')=='user'),None)
    if not isinstance(content,str):return None
    try:
        value=json.loads(content)
        return value if isinstance(value,dict) else None
    except ValueError:return None


def visible_metadata(context,aid,eid):
    rows=[r for r in context.get('assay_preview',[]) if r.get('assay_id')==aid]
    confidence=any('confidence_score' in r or 'confidence_score' in (r.get('metadata') or {}) for r in rows)
    description=any(bool(r.get('description')) for r in rows)
    view=context.get('last_evidence_view') or {}
    if view.get('evidence_id')==eid:
        if view.get('view')=='assay_description':description=bool(view.get('text'))
        elif view.get('view')=='summary' and not view.get('truncated'):
            try:
                value=json.loads(view.get('text') or '{}')
                metadata=value.get('assay',value.get('summary',value)) if isinstance(value,dict) else {}
                confidence|='confidence_score' in metadata;description|=bool(metadata.get('description'))
            except (ValueError,AttributeError,TypeError):pass
    return bool(rows),confidence,description


def measured_seconds(values):
    valid=[v for v in values if type(v) in (int,float) and math.isfinite(v) and v>=0]
    return {'seconds':sum(valid) if valid else None,'measured_events':len(valid),'missing_or_invalid_events':len(values)-len(valid)}


def analyze(root,state,receipts,ledger):
    totals={'prompt_tokens':0,'completion_tokens':0,'total_tokens':0};unknown=0
    statuses=Counter();contexts={}
    for number,receipt in receipts.items():
        statuses[receipt.get('status','unknown')]+=1;usage=receipt.get('usage')
        if not usage:unknown+=1
        for key in totals:totals[key]+=int((usage or {}).get(key) or 0)
        context=model_context(receipt)
        if context is not None:contexts[number]=context
    if totals!=state['usage']:raise ValueError('Returned usage totals disagree with state')
    actions=[];visibility=[];seen=Counter();inspects=Counter();repeated=Counter()
    boundary=ledger.get('inherited_llm_attempts',0) if ledger else 0
    for event in state['events']:
        if event.get('kind')!='tool_action':continue
        decision=event['decision'];action=decision['action'];args=decision['arguments'];number=event['llm_attempt']
        key=signature({'action':action,'arguments':args});duplicate=seen[key]>0;seen[key]+=1
        if duplicate:repeated[action]+=1
        if action=='inspect_assay':inspects[args['assay_id']]+=1
        actions.append({'attempt':number,'phase':'v2.1' if ledger and number>boundary else 'v2_or_standalone',
            'action':action,'arguments':json.dumps(args,ensure_ascii=False,sort_keys=True),
            'status':event['status'],'same_tool_and_arguments_seen_before':duplicate,
            'reason':decision.get('reason'),'error':event.get('error'),
            'elapsed_seconds':event.get('elapsed_seconds')})
        context=contexts.get(number+1)
        if context is None:continue
        result=event.get('result') or {};eid=result.get('evidence_id');aid=args.get('assay_id')
        in_preview,confidence,description=visible_metadata(context,aid,eid)
        ids=[r.get('assay_chembl_id') or r.get('assay_id') for r in result.get('rows',[]) if isinstance(r,dict)]
        ids=[v for v in ids if v];serialized=json.dumps(context,ensure_ascii=False,sort_keys=True)
        visibility.append({'after_attempt':number,'next_request':number+1,'action':action,'assay_id':aid,
            'result_evidence_id':eid,'assay_in_next_preview':in_preview,
            'confidence_in_standard_metadata_locations':confidence if action=='inspect_assay' else None,
            'description_in_standard_metadata_locations':description if action=='inspect_assay' else None,
            'next_context_has_last_tool_result':'last_tool_result' in context,
            'recent_actions_include_arguments':any('arguments' in r for r in context.get('recent_actions',[])),
            'returned_assay_ids':len(ids),'returned_assay_ids_present_anywhere_in_next_context':sum(v in serialized for v in ids),
            'next_context_characters':len(serialized)})
    assays=[]
    for aid,item in sorted(state['assays'].items()):
        meta=item['summary'];c=item.get('curation') or {};b=c.get('budget') or {};source=item.get('source_assessment') or {}
        decision=item.get('decision') or {};description=meta.get('description') or ''
        assays.append({'assay_id':aid,'target_id':meta.get('target_id'),'confidence_score':meta.get('confidence_score'),
            'assay_type':meta.get('assay_type'),'document_chembl_id':meta.get('document_chembl_id'),
            'description_characters':len(description),'description_preview':description[:1200],
            'description_preview_truncated':len(description)>1200,'count_probe':state.get('assay_counts',{}).get(aid),
            'acquisition':item.get('acquisition'),'usable_compounds':b.get('provisional_pool_size'),
            'hits':b.get('hit_support_count'),'nonhits':b.get('nonhit_support_count'),
            'qualification':c.get('qualification'),'source_status':source.get('status'),'source_reason':source.get('reason'),
            'verdict':decision.get('verdict'),'decision_reason':decision.get('reason')})
    counts=state.get('target_counts',{})
    inspect_views=[v for v in visibility if v['action']=='inspect_assay']
    list_views=[v for v in visibility if v['action']=='list_assays' and v['returned_assay_ids']]
    summary={'run_status':state['status'],'finish_reason':state.get('finish_reason'),'release':state['release'],
        'catalog_size':len(read(root/'catalog.json')),
        'fresh_target_count_probes':sum(r['scope']=='IC50_type_B' for r in counts.values()),
        'imported_target_upper_bounds':sum(r['scope']=='prior_IC50_all_types_upper_bound' for r in counts.values()),
        'profiles_examined':len(state['profiles']),'assays_inspected':len(state['assays']),
        'assays_curated':sum('curation' in a for a in state['assays'].values()),
        'review_shortlist':state['shortlist'],'verdict_counts':dict(Counter(a['verdict'] or 'no_decision' for a in assays)),
        'llm_attempts':state['llm_attempts'],'http_attempts':len(state['requests']),
        'llm_usage_returned':totals,'attempts_without_returned_usage':unknown,'receipt_status_counts':dict(statuses),
        'successful_tool_actions':sum(a['status']=='success' for a in actions),
        'tool_errors':sum(a['status']=='tool_error' for a in actions),'tool_action_counts':dict(Counter(a['action'] for a in actions)),
        'repeated_same_tool_and_arguments':dict(repeated),'repeated_inspect_assays':{k:v for k,v in inspects.items() if v>1},
        'continuation_new_requests':len([n for n in receipts if n>boundary]) if ledger else None,
        'continuation_new_invalid_decisions':sum(r.get('status')=='invalid_decision' for n,r in receipts.items() if n>boundary) if ledger else None,
        'http_elapsed':measured_seconds([r.get('elapsed_seconds') for r in state['requests']]),
        'llm_elapsed':measured_seconds([r.get('elapsed_seconds') for r in receipts.values()]),
        'numerical_curation_compute':measured_seconds([a['curation'].get('computational_seconds') for a in state['assays'].values() if 'curation' in a]),
        'visibility_rows':len(visibility),'campaign_ready':False,'new_model_requests_by_audit':0,
        'tool_result_delivery_diagnostics':{
            'inspect_calls_with_a_next_saved_context':len(inspect_views),
            'inspected_assay_absent_from_next_preview':sum(not v['assay_in_next_preview'] for v in inspect_views),
            'confidence_not_in_standard_metadata_locations':sum(not v['confidence_in_standard_metadata_locations'] for v in inspect_views),
            'assay_list_calls_with_a_next_saved_context':len(list_views),
            'returned_assay_ids_missing_from_next_context':sum(v['returned_assay_ids']-v['returned_assay_ids_present_anywhere_in_next_context'] for v in list_views)},
        'interpretation_limits':['No shortlisted dataset in this bounded run does not establish absence in ChEMBL.',
            'Repeated actions can be cache reads; repetition is not by itself proof of unnecessary HTTP work.',
            'Metadata visibility flags check named structured locations, not all natural-language clues or model memory.',
            'Assay ID occurrence anywhere in the next context is not proof that its complete metadata was delivered.',
            'Descriptive comparison across versions is confounded by different evidence stages and an interface fix.']}
    return summary,assays,actions,visibility


def write_json(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def write_csv(path,rows):
    with path.open('w',encoding='utf-8-sig',newline='') as handle:
        if rows:
            writer=csv.DictWriter(handle,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def audit(run_dir,output_root):
    root=Path(run_dir).resolve();destination=Path(output_root).resolve()
    if destination.is_relative_to(root):raise ValueError('Reports must be outside the run directory')
    before=inventory(root);state=read(root/'state.json')
    if state['status'] not in ('finished','llm_budget_exhausted'):raise ValueError('Only a closed or budget-exhausted run can be audited')
    checked,ledger=verify_inputs(root,state);attempts=state['llm_attempts']
    expected={f'{n:04d}.json' for n in range(1,attempts+1)}
    if {p.name for p in (root/'llm').glob('*.json')}!=expected:raise ValueError('LLM receipt range mismatch')
    receipts={n:read(root/'llm'/f'{n:04d}.json') for n in range(1,attempts+1)}
    summary,assays,actions,visibility=analyze(root,state,receipts,ledger)
    if inventory(root)!=before:raise ValueError('Run changed during read-only audit')
    destination.mkdir(parents=True,exist_ok=True)
    out=destination/('review_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:8]);out.mkdir()
    write_json(out/'summary.json',summary);write_json(out/'assays.json',assays)
    write_csv(out/'actions.csv',actions);write_csv(out/'tool_result_visibility.csv',visibility)
    integrity={'status':'DECLARED_HASHES_AND_RETURNED_USAGE_VERIFIED','declared_file_checks':len(checked),
        'run_files_unchanged':len(before),'input_files_sha256':before,
        'note':'Original run was not written. Hashes check consistency with saved declarations, not independent source truth. OS lock is excluded.'}
    write_json(out/'integrity.json',integrity)
    lines=['# Task 1 闭环审计','',f'- 状态：{summary["run_status"]}；入选：{len(summary["review_shortlist"])}。',
        f'- 模型请求：{attempts}；ChEMBL 请求：{summary["http_attempts"]}；返回 tokens：{summary["llm_usage_returned"]["total_tokens"]}。',
        f'- 画像：{summary["profiles_examined"]}；检查 assay：{summary["assays_inspected"]}；已整理 assay：{summary["assays_curated"]}。',
        f'- 去留计数：{json.dumps(summary["verdict_counts"],ensure_ascii=False)}。',
        f'- 重复检查同一 assay：{json.dumps(summary["repeated_inspect_assays"],ensure_ascii=False)}。',
        '', '## 结束理由','',summary['finish_reason'] or '未记录模型结束理由。','',
        '## 含义与下一步','',
        '本轮没有入选项不等于数据库没有合适数据。inspect 成功不代表完整获取、完成整理或科学资格通过。',
        '核对 assays.json 的实际门槛与去留理由，再查看 actions.csv 的重复动作和错误。',
        'tool_result_visibility.csv 对照每个工具事件及其后一次模型输入，检查前六项候选以外的可见性和返回列表传递情况。',
        '这些是描述性诊断，不单独证明某个缺口导致整个搜索失败；改框架应另建版本并做针对性实验。',
        '',f'原运行 {len(before)} 个文件哈希未改变；报告未调用 API。']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return out,summary


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--run-dir',required=True,type=Path)
    parser.add_argument('--output-root',required=True,type=Path);args=parser.parse_args()
    out,summary=audit(args.run_dir,args.output_root)
    integrity=read(out/'integrity.json')
    print(json.dumps({'report_dir':str(out),'input_integrity':{k:integrity[k] for k in ['status','declared_file_checks','run_files_unchanged']},
        'summary':summary},ensure_ascii=False,indent=2))
    print('\nASSAY_DECISIONS')
    for a in read(out/'assays.json'):
        print(json.dumps({k:a[k] for k in ['assay_id','target_id','confidence_score','count_probe','usable_compounds',
            'hits','nonhits','qualification','source_status','verdict','decision_reason']},ensure_ascii=False))


if __name__=='__main__':main()
