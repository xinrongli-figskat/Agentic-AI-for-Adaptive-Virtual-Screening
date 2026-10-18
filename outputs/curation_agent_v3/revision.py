"""Explicit new software experiment after a closed v2.1 run; no hidden budget reset."""
from datetime import datetime,timezone
from pathlib import Path
import shutil

from .engine import read,save,sha,signature
from .integrity import inventory,verify_inputs
from .run import PACKAGE,source_hashes,environment,load_engine,refresh_usage,validate_protocol


def prepare_revision(parent,output_root,additional_llm_budget,additional_http_budget):
    if type(additional_llm_budget) is not int or not 1<=additional_llm_budget<=40:
        raise ValueError('Explicit additional LLM budget must be 1..40')
    if type(additional_http_budget) is not int or not 1<=additional_http_budget<=200:
        raise ValueError('Explicit additional HTTP budget must be 1..200')
    parent=Path(parent).resolve();output_root=Path(output_root).resolve()
    if output_root.is_relative_to(parent):raise ValueError('New experiment must be outside the closed parent run')
    state=read(parent/'state.json');reference=read(PACKAGE/'parent_v21_reference.json')
    if state.get('schema')!='task1_agent_v2.1' or state.get('status') not in ('finished','llm_budget_exhausted'):
        raise ValueError('Expected a closed v2.1 run')
    if state.get('pending_action') is not None or state.get('shortlist'):raise ValueError('Pending actions/exports require separate reviewed migration')
    if state['environment']!=environment():raise ValueError('Scientific runtime changed; do not silently migrate')
    if state['protocol']!=reference['protocol'] or state['code_sha256']!=reference['code_sha256']:
        raise ValueError('Parent does not match the reviewed v2.1 protocol/source version')
    verify_inputs(parent,state);before=inventory(parent)
    receipts=[read(parent/'llm'/f'{n:04d}.json') for n in range(1,state['llm_attempts']+1)]
    totals={k:sum(int((r.get('usage') or {}).get(k) or 0) for r in receipts) for k in ['prompt_tokens','completion_tokens','total_tokens']}
    if totals!=state['usage']:raise ValueError('Parent usage totals do not reconcile')
    protocol=read(PACKAGE/'protocol.json')
    expected={**reference['protocol'],'version':'task1_agent_v3.0','maximum_tool_result_characters':6500,
              'feedback_revision':'typed_result_active_candidate_and_verifiable_disposition_v1'}
    if protocol!=expected:raise ValueError('Unreviewed scientific/default protocol change')
    protocol['maximum_llm_attempts']=state['llm_attempts']+additional_llm_budget
    protocol['maximum_http_requests']=len(state['requests'])+additional_http_budget
    validate_protocol(protocol);code=source_hashes()
    key=signature({'parent_files':before,'code':code,'protocol':protocol})[:16]
    folder=output_root/('revision_v3_'+key)
    if folder.exists():
        load_engine(folder)
        save(output_root/'latest_revision.json',{'run_dir':str(folder)})
        return folder
    output_root.mkdir(parents=True,exist_ok=True)
    shutil.copytree(parent,folder,ignore=shutil.ignore_patterns('.writer.lock'))
    history=folder/'history_v21';history.mkdir()
    for name in ('state.json','report.json','source_snapshot'):
        path=folder/name
        if path.exists():path.rename(history/name)
    for name,wanted in before.items():
        target=history/name if name in ('state.json','report.json') or name.startswith('source_snapshot/') else folder/name
        if sha(target)!=wanted:raise ValueError('Parent copy hash mismatch')
    for relative in code:
        target=folder/'source_snapshot'/relative;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(PACKAGE/relative,target)
    ledger={'schema':'task1_post_exposure_software_revision_v1','created_at_utc':datetime.now(timezone.utc).isoformat(),
        'parent_run':str(parent),'parent_tree_sha256':signature(before),'parent_files_sha256':before,
        'inherited_llm_attempts':state['llm_attempts'],'inherited_http_attempts':len(state['requests']),
        'inherited_usage':totals,'additional_llm_budget':additional_llm_budget,'additional_http_budget':additional_http_budget,
        'exposure':'All earlier decisions/results have been seen. New software experiment, not an independent blind test.',
        'scientific_thresholds_changed':False,'changed':'Typed direct results, pinned active assay, explicit units, machine-verifiable disposition basis.',
        'old_invalid_responses_reexecuted':False}
    save(folder/'revision.json',ledger)
    state.update(schema='task1_agent_v3.0',protocol=protocol,protocol_sha256=signature(protocol),code_sha256=code,
        status='prepared_new_revision_no_network_no_glm',format_feedback=None,format_corrections_used=0,
        active_assay_id=None,active_target_id=None,last_tool_result=None,last_evidence_view=None,last_candidate_page=None,
        revision={'ledger_sha256':sha(folder/'revision.json'),'parent_run':str(parent),
            'inherited_llm_attempts':state['llm_attempts'],'inherited_http_attempts':len(state['requests']),
            'additional_llm_budget':additional_llm_budget,'additional_http_budget':additional_http_budget})
    state.pop('finish_reason',None)
    state['events'].append({'kind':'new_post_exposure_software_revision','ledger':'revision.json','budgets_reset':False})
    save(folder/'state.json',state)
    if inventory(parent)!=before:raise ValueError('Closed parent changed while preparing new experiment')
    engine=load_engine(folder);refresh_usage(engine);engine.report()
    save(output_root/'latest_revision.json',{'run_dir':str(folder)})
    return folder
