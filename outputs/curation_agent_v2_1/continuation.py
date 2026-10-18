"""Continue a paused v2 run in a separate v2.1 directory; retain spent budgets."""
from contextlib import contextmanager
from datetime import datetime,timezone
import json
from pathlib import Path
import platform
import shutil

from .engine import read,save,sha,signature
from .run import PACKAGE,environment,source_hashes,validate_protocol,load_engine,refresh_usage,safe


def file_hashes(root):
    result={}
    for path in sorted(root.rglob('*')):
        if path.name=='.writer.lock':continue  # Windows denies reads while its byte-range lock is held.
        if path.is_symlink():raise ValueError('Symlinks are not supported in a continuation source')
        if path.is_file():result[path.relative_to(root).as_posix()]=sha(path)
    return result


@contextmanager
def parent_lock(parent):
    # Use the existing lock without writing to it or creating any parent file.
    if (parent/'.writer.lock').is_symlink():raise ValueError('Parent lock must not be a symlink')
    with (parent/'.writer.lock').open('r+b') as handle:
        if platform.system()=='Windows':
            import msvcrt
            msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:yield
        finally:
            handle.seek(0)
            if platform.system()=='Windows':msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(handle,fcntl.LOCK_UN)


def verify_parent(parent):
    state=read(parent/'state.json');reference=read(PACKAGE/'legacy_v2_reference.json')
    if state.get('schema')!='task1_agent_v2.0' or state.get('status')!='paused_after_format_limit':
        raise ValueError('Expected a v2.0 run paused_after_format_limit')
    if state.get('pending_action') is not None or state.get('shortlist'):
        raise ValueError('Only a paused run with no pending action and no exported shortlist is supported')
    if state['protocol']!=reference['protocol'] or signature(state['protocol'])!=state['protocol_sha256']:
        raise ValueError('Parent protocol differs from the reviewed v2.0 protocol')
    if state['code_sha256']!=reference['code_sha256']:raise ValueError('Parent v2 source version mismatch')
    if state['environment']!=environment():raise ValueError('Scientific runtime changed; continuation refused')
    for relative,wanted in state['code_sha256'].items():
        if sha(safe(parent/'source_snapshot',relative))!=wanted:raise ValueError('Parent source snapshot hash mismatch')
    if sha(parent/'catalog.json')!=state['catalog_sha256']:raise ValueError('Parent catalog hash mismatch')
    if sha(parent/'prior_exposure.json')!=state['prior_exposure_sha256']:raise ValueError('Parent exposure ledger hash mismatch')
    for evidence in state['evidence'].values():
        if sha(safe(parent,evidence['path']))!=evidence['sha256']:raise ValueError('Parent scientific evidence hash mismatch')
    for request in state['requests']:
        if request.get('sha256') and sha(safe(parent,request['raw_file']))!=request['sha256']:
            raise ValueError('Parent HTTP response hash mismatch')
    attempts=state['llm_attempts']
    if type(attempts) is not int or not 1<=attempts<=state['protocol']['maximum_llm_attempts']:
        raise ValueError('Invalid inherited LLM budget')
    receipts=sorted((parent/'llm').glob('*.json'))
    if {p.name for p in receipts}!={f'{n:04d}.json' for n in range(1,attempts+1)}:
        raise ValueError('Parent LLM receipts are missing or outside the reserved attempt range')
    totals={'prompt_tokens':0,'completion_tokens':0,'total_tokens':0};unknown=0
    for path in receipts:
        usage=read(path).get('usage')
        if not usage:unknown+=1
        for key in totals:totals[key]+=int((usage or {}).get(key) or 0)
    if totals!=state['usage']:raise ValueError('Parent returned usage totals disagree with saved receipts')
    if len(state['requests'])>state['protocol']['maximum_http_requests']:raise ValueError('Parent exceeded HTTP cap')
    return state,totals,unknown


def continue_v2(parent,output_root):
    parent=Path(parent).resolve();output_root=Path(output_root).resolve()
    if output_root.is_relative_to(parent):raise ValueError('Continuation must be outside the parent directory')
    protocol=read(PACKAGE/'protocol.json');validate_protocol(protocol)
    with parent_lock(parent):
        state,usage,unknown=verify_parent(parent)
        expected={**state['protocol'],'version':'task1_agent_v2.1','decision_interface':'single_top_level_reason_v1'}
        if protocol!=expected:raise ValueError('Scientific criteria or budgets changed; not an interface-only continuation')
        before=file_hashes(parent);parent_tree_hash=signature(before);code=source_hashes()
        version=signature({'parent':parent_tree_hash,'new_code':code})[:16]
        folder=output_root/('continuation_v2_1_'+version)
        if folder.exists():
            engine=load_engine(folder)
            if read(folder/'continuation.json')['parent_tree_sha256']!=parent_tree_hash:
                raise ValueError('Existing continuation has a different parent')
            save(output_root/'latest_continuation.json',{'run_dir':str(folder),'parent_tree_sha256':parent_tree_hash})
            return folder  # Repeated setup never resets a child's later requests or decisions.
        output_root.mkdir(parents=True,exist_ok=True)
        shutil.copytree(parent,folder,ignore=shutil.ignore_patterns('.writer.lock'))
        history=folder/'history_v2';history.mkdir()
        for name in ('state.json','report.json','source_snapshot'):
            path=folder/name
            if path.exists():path.rename(history/name)
        for name,wanted in before.items():
            if name=='.writer.lock':continue
            inherited=history/name if name in ('state.json','report.json') or name.startswith('source_snapshot/') else folder/name
            if sha(inherited)!=wanted:raise ValueError('Copied parent file hash mismatch')
        for relative in code:
            target=folder/'source_snapshot'/relative;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(PACKAGE/relative,target)
        ledger={'schema':'task1_v2_1_interface_continuation','created_at_utc':datetime.now(timezone.utc).isoformat(),
            'parent_run':str(parent),'parent_state_sha256':before['state.json'],'parent_tree_sha256':parent_tree_hash,
            'parent_files_sha256':before,'parent_code_sha256':state['code_sha256'],
            'inventory_exclusion':'Operating-system .writer.lock only; scientific data and all LLM receipts included.',
            'parent_protocol_sha256':state['protocol_sha256'],'new_protocol_sha256':signature(protocol),
            'inherited_llm_attempts':state['llm_attempts'],'inherited_http_attempts':len(state['requests']),
            'inherited_usage':usage,'inherited_attempts_without_returned_usage':unknown,
            'change':'One rationale at $.reason; program passes it to rationale-taking tools. No automatic acceptance of old invalid responses.',
            'scientific_criteria_changed':False,'model_changed':False,'budgets_reset':False,
            'exposure':'Same evidence and previously observed results; this is a versioned continuation, not an independent or blind run.'}
        save(folder/'continuation.json',ledger)
        state.update(schema='task1_agent_v2.1',protocol=protocol,protocol_sha256=signature(protocol),code_sha256=code,
            status='continued_no_network_no_glm',format_corrections_used=0,
            continuation={'ledger_sha256':sha(folder/'continuation.json'),'parent_run':str(parent),
                'inherited_llm_attempts':state['llm_attempts'],'inherited_http_attempts':len(state['requests'])})
        state['format_feedback']={'interface_update':'There is now only ONE reason, at $.reason. NEVER include reason in $.arguments. Old invalid replies were not executed.'}
        state['events'].append({'kind':'versioned_interface_continuation','ledger':'continuation.json','budgets_reset':False})
        save(folder/'state.json',state)
        if file_hashes(parent)!=before:raise ValueError('Parent changed while copying; do not execute this continuation')
        engine=load_engine(folder);refresh_usage(engine);engine.report()
        save(output_root/'latest_continuation.json',{'run_dir':str(folder),'parent_tree_sha256':parent_tree_hash})
        return folder
