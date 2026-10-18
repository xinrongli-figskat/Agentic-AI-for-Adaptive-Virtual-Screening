"""Independent Task1 v2: offline prepare, numeric prescreen, bounded GLM actions."""
import argparse
import json
import platform
import shutil
import time
import uuid
from contextlib import contextmanager
from datetime import datetime,timezone
from pathlib import Path
from .controller import GLM,DecisionFormatError,APIError
from .engine import read,save,sha,signature
from .feedback import Engine

PACKAGE=Path(__file__).parent

def source_hashes():
    return {p.relative_to(PACKAGE).as_posix():sha(p) for p in sorted(PACKAGE.rglob('*'))
            if p.is_file() and p.suffix in ('.py','.json','.md') and '__pycache__' not in p.parts}

def environment():
    import rdkit,numpy
    return {'python':platform.python_version(),'rdkit':rdkit.__version__,'numpy':numpy.__version__}

def validate_protocol(p):
    integers=['minimum_usable_compounds','preferred_usable_compounds','minimum_hits','minimum_nonhits',
        'minimum_confidence_score','minimum_scaffold_buckets','query_budget','initialization_queries',
        'feedback_batch_size','maximum_target_window','maximum_assay_records','maximum_pairwise_compounds',
        'maximum_http_requests','maximum_llm_attempts','page_size','maximum_output_tokens','request_timeout_seconds',
        'maximum_context_characters','maximum_evidence_page_characters','context_target_limit','context_assay_limit']
    for key in integers:
        if type(p[key]) is not int or p[key]<=0:raise ValueError('Invalid positive integer: '+key)
    if type(p['maximum_format_corrections']) is not int or not 0<=p['maximum_format_corrections']<=2:
        raise ValueError('At most two automatic format corrections')
    for key in ['maximum_largest_cluster_fraction','maximum_initial_single_class_probability','maximum_query_fraction']:
        if type(p[key]) not in (int,float) or not 0<p[key]<=1:raise ValueError('Invalid bounded fraction: '+key)
    if (not 0<p['initialization_queries']<p['query_budget']<=p['minimum_usable_compounds'] or
        p['query_budget']/p['minimum_usable_compounds']>p['maximum_query_fraction'] or
        p['preferred_usable_compounds']<p['minimum_usable_compounds'] or
        p['minimum_hits']+p['minimum_nonhits']>p['minimum_usable_compounds']):
        raise ValueError('Qualification tier/class/query budget inconsistency')
    if p['maximum_evidence_page_characters']>4000 or p['maximum_context_characters']>24000:
        raise ValueError('Context exceeds reviewed implementation bounds')
    if p['model']!='glm-5.3-flash' or p['hit_threshold_nM']!='1000':raise ValueError('Unreviewed model or endpoint settings')
    if p.get('decision_interface')!='single_top_level_reason_v1':raise ValueError('Unreviewed decision interface')
    if type(p.get('maximum_tool_result_characters')) is not int or not 1000<=p['maximum_tool_result_characters']<=6500:
        raise ValueError('Invalid latest tool result cap')

def safe(root,relative):
    path=(root/relative).resolve();path.relative_to(root.resolve());return path

def verify_prior(prior):
    prior=Path(prior).resolve();state=read(prior/'state.json')
    if state.get('schema')!='task1_agent_v1.0' or state.get('status')!='finished':
        raise ValueError('Expected the completed original Task1 v1 run')
    if signature(state['protocol'])!=state['protocol_sha256']:raise ValueError('Prior protocol hash mismatch')
    if sha(prior/'catalog.json')!=state['catalog_sha256']:raise ValueError('Prior catalog hash mismatch')
    for item in state['evidence'].values():
        if sha(safe(prior,item['path']))!=item['sha256']:raise ValueError('Prior evidence hash mismatch')
    for item in state['requests']:
        if item.get('sha256') and sha(safe(prior,item['raw_file']))!=item['sha256']:raise ValueError('Prior HTTP-response hash mismatch')
    for relative,wanted in state['code_sha256'].items():
        if sha(safe(prior/'source_snapshot',relative))!=wanted:raise ValueError('Prior source snapshot hash mismatch')
    catalog=read(prior/'catalog.json')
    if len({r['target_chembl_id'] for r in catalog})!=len(catalog) or any(r['target_type']!='SINGLE PROTEIN' for r in catalog):
        raise ValueError('Incompatible catalog')
    for target,p in state['profiles'].items():
        full=read(safe(prior,state['evidence'][p['evidence_id']]['path']))
        if (full.get('target_chembl_id')!=target or full.get('api_matching_IC50_records')!=p['source_total'] or
                full.get('records_retrieved')!=p['records_received']):
            raise ValueError('Prior profile summary disagrees with its saved source evidence')
    return state,catalog

def prepare(prior,output_root,protocol_path=PACKAGE/'protocol.json'):
    prior=Path(prior).resolve();p=read(protocol_path);validate_protocol(p)
    old,catalog=verify_prior(prior)
    folder=Path(output_root)/('curation_v2_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:8])
    folder.mkdir(parents=True,exist_ok=False);save(folder/'catalog.json',catalog)
    exposure={'status':'post_exploration_not_blind','prior_run':str(prior),'prior_state_sha256':sha(prior/'state.json'),
        'prior_protocol_sha256':old['protocol_sha256'],
        'previously_examined_targets':[{k:v for k,v in row.items() if k in ('target_id','name','source_total','retrieval_complete')}
                                       for row in old['profiles'].values()],
        'previously_curated_assays':[{'assay_id':key,'budget':v.get('curation',{}).get('budget'),
            'prior_decision':v.get('decision')} for key,v in old['assays'].items() if 'curation' in v],
        'already_seen_results':['DYRK3 v1 231-compound feasibility pool and controller results',
            'Task1 v1 search of 60 profiles, p300 and P2X class/curation evidence',
            'Source alignment review: p300 HAT domain/isomer merges; P2X2/3 receptor/citation issues'],
        'new_criteria_rationale':p['budget_rationale'],'source_holds_sha256':sha(PACKAGE/'source_holds.json'),
        'warning':'Earlier rejects remain in their original run. Changed tiers are not independent preregistration for already seen candidates.'}
    save(folder/'prior_exposure.json',exposure);hashes=source_hashes()
    for relative in hashes:
        target=folder/'source_snapshot'/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(PACKAGE/relative,target)
    state={'schema':'task1_agent_v3.0','status':'prepared','release':old['release'],
        'protocol':p,'protocol_sha256':signature(p),'code_sha256':hashes,'catalog_sha256':sha(folder/'catalog.json'),
        'prior_exposure_sha256':sha(folder/'prior_exposure.json'),'environment':environment(),
        'created_at_utc':datetime.now(timezone.utc).isoformat(),'requests':[],'profiles':{},'seed_profiles':{},
        'target_counts':{},'assay_counts':{},'known_assays':{},'assays':{},'evidence':{},'shortlist':[],
        'events':[],'llm_attempts':0,'pending_action':None,'usage':{'prompt_tokens':0,'completion_tokens':0,'total_tokens':0},
        'evidence_views':{},'last_evidence_view':None,'last_candidate_page':None,'format_feedback':None,'format_corrections_used':0}
    save(folder/'state.json',state);engine=Engine(folder,state)
    for target,profile in old['profiles'].items():
        original=old['evidence'][profile['evidence_id']];value=read(safe(prior,original['path']))
        eid=engine.evidence('prior_target_profile',{'source_hash':original['sha256'],'prior_evidence_id':profile['evidence_id'],
            'profile':value,'prior_run':str(prior),'limitation':'Previously seen preview, not a new validation dataset'})
        state['seed_profiles'][target]={**profile,'evidence_id':eid}
        for row in value['assay_profiles']:state['known_assays'][row['assay_chembl_id']]=target
        state['target_counts'][target]={'target_id':target,'name':profile['name'],
            'raw_activity_count':profile['source_total'],'scope':'prior_IC50_all_types_upper_bound',
            'evidence_id':eid,'below_raw_count_floor':profile['source_total']<p['minimum_usable_compounds']}
    engine.checkpoint();engine.report();save(Path(output_root)/'latest_prepared.json',{'run_dir':str(folder.resolve())})
    return folder

def load_engine(folder,client_factory=None):
    folder=Path(folder);state=read(folder/'state.json')
    if state.get('schema')!='task1_agent_v3.0':raise ValueError('Wrong run schema; v1 cannot be resumed as v2')
    validate_protocol(state['protocol'])
    if signature(state['protocol'])!=state['protocol_sha256'] or source_hashes()!=state['code_sha256']:
        raise ValueError('Protocol/code changed; create a new run/version')
    if environment()!=state['environment']:raise ValueError('Scientific runtime changed; create new run/version')
    if sha(folder/'catalog.json')!=state['catalog_sha256']:raise ValueError('Catalog hash mismatch')
    if sha(folder/'prior_exposure.json')!=state['prior_exposure_sha256']:raise ValueError('Prior exposure ledger hash mismatch')
    if state.get('continuation'):
        if sha(folder/'continuation.json')!=state['continuation']['ledger_sha256']:
            raise ValueError('Continuation ledger hash mismatch')
    if state.get('revision'):
        if sha(folder/'revision.json')!=state['revision']['ledger_sha256']:raise ValueError('Revision ledger hash mismatch')
        for relative,wanted in read(folder/'revision.json')['parent_files_sha256'].items():
            historical='history_v21/'+relative if relative in ('state.json','report.json') or relative.startswith('source_snapshot/') else relative
            if sha(safe(folder,historical))!=wanted:raise ValueError('Inherited closed-parent file hash mismatch')
    for relative,wanted in state['code_sha256'].items():
        if sha(safe(folder/'source_snapshot',relative))!=wanted:raise ValueError('Source snapshot hash mismatch')
    engine=Engine(folder,state,client_factory) if client_factory else Engine(folder,state)
    for eid in state['evidence']:engine.cited(eid)
    for r in state['requests']:
        if r.get('sha256') and sha(safe(folder,r['raw_file']))!=r['sha256']:raise ValueError('Source response hash mismatch')
    return engine

@contextmanager
def single_writer(folder):
    with (Path(folder)/'.writer.lock').open('a+b') as handle:
        handle.seek(0);handle.write(b'0');handle.flush();handle.seek(0)
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

def refresh_usage(engine):
    totals={'prompt_tokens':0,'completion_tokens':0,'total_tokens':0};returned=0
    for path in (engine.folder/'llm').glob('*.json'):
        usage=read(path).get('usage')
        if usage:returned+=1
        for key in totals:totals[key]+=int((usage or {}).get(key) or 0)
    engine.state['usage']=totals
    engine.state['llm_attempts_without_returned_usage']=max(0,engine.state['llm_attempts']-returned)
    engine.checkpoint()

def check_release(engine):
    if engine.client.get('status').get('chembl_db_version')!=engine.state['release']:
        raise ValueError('ChEMBL release changed; new compatible catalog/run required')

def prescreen(engine,targets,profiles):
    if engine.state['status']=='finished' or engine.state['llm_attempts']:
        raise ValueError('Program prescreen is only for a run before its first GLM attempt; use agent tools thereafter')
    check_release(engine)
    for _ in range(targets):
        result=engine.screen_targets(1)
        if not result['screened']:break
        row=result['screened'][0]
        print(json.dumps({'numeric_count_probe':row['target_id'],'records':row['raw_activity_count'],
                          'below_count_floor':row['below_raw_count_floor']}),flush=True)
    rich=[r for r in engine.target_rows() if r['scope']=='IC50_type_B' and not r['below_raw_count_floor'] and r['target_id'] not in engine.state['profiles']]
    for row in rich[:profiles]:
        value=engine.profile_target(row['target_id'])
        print(json.dumps({'thin_profile':row['target_id'],'received':value['records_received'],
                          'complete':value['retrieval_complete']}),flush=True)
    engine.state['status']='prescreened_no_llm_used';engine.checkpoint();return engine.report()

def run_steps(engine,controller,steps):
    state=engine.state
    if state['status']=='finished':return engine.report()
    check_release(engine)
    if state['status']=='paused_after_format_limit':
        state['events'].append({'kind':'manual_resume_after_format_limit','previous_feedback':state['format_feedback']})
        state['format_corrections_used']=0
    state['status']='running';engine.checkpoint();actions=0
    while actions<steps:
        if state['pending_action'] is None:
            if state['llm_attempts']>=engine.p['maximum_llm_attempts']:
                state['status']='llm_budget_exhausted';break
            context=engine.context()
            number=state['llm_attempts']+1;state['llm_attempts']=number
            receipt=engine.folder/'llm'/f'{number:04d}.json';engine.checkpoint()
            try:
                decision=controller.call(context,receipt)
                state['pending_action']={'decision':decision,'attempt':number,'receipt':str(receipt.relative_to(engine.folder))}
                state['format_feedback']=None;state['format_corrections_used']=0;engine.checkpoint()
            except DecisionFormatError as error:
                saved=read(receipt) if receipt.exists() else {}
                state['format_feedback']={'invalid_attempt':number,'validation_error':saved.get('validation_error',str(error)),
                    'previous_reply':(saved.get('returned_content') or '')[:1200],
                    'instruction':'Correct the exact tool schema on the same evidence. No tool executed. All attempts count.'}
                state['events'].append({'kind':'llm_format_failure','attempt':number,'receipt':str(receipt.relative_to(engine.folder)),
                                        'validation_error':state['format_feedback']['validation_error']})
                refresh_usage(engine)
                if state['format_corrections_used']>=engine.p['maximum_format_corrections']:
                    state['status']='paused_after_format_limit';break
                state['format_corrections_used']+=1;engine.checkpoint()
                print(json.dumps({'attempt':number,'format_invalid':True,'next_correction':state['format_corrections_used'],
                                  'no_tool_executed':True}),flush=True);continue
            except APIError:
                state['events'].append({'kind':'llm_api_failure','attempt':number,'receipt':str(receipt.relative_to(engine.folder))})
                state['status']='paused_after_api_failure';refresh_usage(engine);engine.report();raise
            refresh_usage(engine)
        pending=state['pending_action'];decision=pending['decision'];start=time.monotonic()
        event={'kind':'tool_action','decision':decision,'llm_attempt':pending['attempt'],'receipt':pending['receipt']}
        try:
            result=engine.execute(decision['action'],decision['arguments'],action_reason=decision['reason']);event.update(status='success',result=result)
        except Exception as error:event.update(status='tool_error',error_type=type(error).__name__,error=str(error)[:500])
        event['elapsed_seconds']=time.monotonic()-start
        state['events'].append(event);state['pending_action']=None;actions+=1;engine.checkpoint()
        print(json.dumps({'attempt':pending['attempt'],'action':decision['action'],'arguments':decision['arguments'],
                          'status':event['status'],'review_shortlist':state['shortlist']},ensure_ascii=False),flush=True)
        engine.report()
        if state['status']=='finished':break
        if len(state['requests'])>=engine.p['maximum_http_requests']:
            state['status']='http_budget_exhausted';break
    if state['status']=='running':state['status']='paused_at_step_limit'
    engine.checkpoint();return engine.report()

def main():
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    prep=commands.add_parser('prepare');prep.add_argument('--prior-run',type=Path,required=True);prep.add_argument('--output-root',type=Path,required=True)
    revision=commands.add_parser('prepare-revision');revision.add_argument('--parent-run',type=Path,required=True)
    revision.add_argument('--output-root',type=Path,required=True)
    revision.add_argument('--additional-llm-budget',type=int,required=True)
    revision.add_argument('--additional-http-budget',type=int,required=True)
    for name in ['prescreen','execute','status']:
        cmd=commands.add_parser(name);cmd.add_argument('--run-dir',type=Path,required=True)
        if name=='prescreen':cmd.add_argument('--targets',type=int,default=32);cmd.add_argument('--profiles',type=int,default=3)
        if name=='execute':cmd.add_argument('--steps',type=int,default=8)
    args=parser.parse_args()
    if args.command=='prepare-revision':
        from .revision import prepare_revision
        folder=prepare_revision(args.parent_run,args.output_root,args.additional_llm_budget,args.additional_http_budget)
        report=load_engine(folder).report()
        print(json.dumps({'run_dir':str(folder.resolve()),'status':report['status'],
            'inherited_llm_attempts':report['llm_attempts'],'inherited_http_attempts':report['http_attempts'],
            'inherited_returned_tokens':report['llm_usage_returned']['total_tokens'],
            'additional_llm_budget':args.additional_llm_budget,'additional_http_budget':args.additional_http_budget,
            'campaign_ready':False},indent=2));return
    if args.command=='prepare':
        folder=prepare(args.prior_run,args.output_root)
        print(json.dumps({'run_dir':str(folder.resolve()),'status':'prepared_no_network_no_glm','campaign_ready':False},indent=2));return
    if args.command=='execute' and not 1<=args.steps<=40:parser.error('--steps must be 1..40')
    if args.command=='prescreen' and not (0<=args.targets<=128 and 0<=args.profiles<=12):parser.error('prescreen targets 0..128, profiles 0..12')
    with single_writer(args.run_dir):
        engine=load_engine(args.run_dir)
        if args.command=='prescreen' and (engine.state['status']=='finished' or engine.state['llm_attempts']):
            parser.error('prescreen is only available before the first GLM attempt; existing run was not changed')
        refresh_usage(engine)
        try:
            if args.command=='prescreen':report=prescreen(engine,args.targets,args.profiles)
            elif args.command=='execute':report=run_steps(engine,GLM(engine.p),args.steps)
            else:report=engine.report()
        except (ValueError,RuntimeError,OSError) as error:
            if engine.state['status'] not in ('paused_after_api_failure','paused_after_format_limit'):
                engine.state['status']='paused_after_runtime_failure';engine.checkpoint()
            engine.report()
            print(json.dumps({'paused':True,'error_type':type(error).__name__,'message':str(error),'run_dir':str(args.run_dir)},ensure_ascii=False));raise SystemExit(1)
        print(json.dumps({k:report[k] for k in ['status','fresh_target_count_probes','imported_target_upper_bounds',
            'profiles_examined','assays_inspected','review_shortlist','llm_attempts','http_attempts',
            'llm_usage_returned','llm_attempts_without_returned_usage','campaign_ready']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
