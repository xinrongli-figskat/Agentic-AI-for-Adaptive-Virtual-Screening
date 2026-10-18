"""Synthetic safety and adaptation checks. No internet, API key or real outcomes."""
import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode

from .controller import GLM,DecisionFormatError,APIError,parse_decision
from .engine import read,save,sha,signature,qualification
from .efficient import Engine
from .run import PACKAGE,prepare,load_engine,prescreen,run_steps,refresh_usage
from .vendor.discovery import BASE_URL


def rows_for(target='CHEMBL1'):
    rows=[]
    for i,smiles in enumerate(['CCO','CCN','c1ccccc1','Oc1ccccc1','CCCl','CCBr','CCF','CCCC'],1):
        rows.append({'activity_id':i,'record_id':1000+i,'molecule_chembl_id':'CHEMBL'+str(100+i),
            'canonical_smiles':smiles,'target_chembl_id':target,'assay_chembl_id':'CHEMBL2',
            'document_chembl_id':'CHEMBL3','standard_type':'IC50','assay_type':'B','standard_units':'nM',
            'standard_relation':'=','standard_value':'500' if i<=3 else '2000','potential_duplicate':0})
    rows[-2]['standard_value']=None
    rows[-1]['potential_duplicate']=1
    return rows if target=='CHEMBL1' else rows[:1] if target=='CHEMBL4' else []


def prior_fixture(root):
    folder=root/'prior';folder.mkdir()
    catalog=[{'target_chembl_id':k,'pref_name':'SYNTHETIC '+k,'target_type':'SINGLE PROTEIN','organism':'Homo sapiens'}
             for k in ['CHEMBL1','CHEMBL4','CHEMBL5']]
    save(folder/'catalog.json',catalog)
    (folder/'source_snapshot').mkdir();(folder/'source_snapshot/stub.py').write_text('# synthetic provenance\n',encoding='utf-8')
    profile={'assay_chembl_id':'CHEMBL2','hit_support_ids':3,'nonhit_support_ids':3,'supported_ids':6,
             'threshold_disagreement_ids':0,'unknown_evidence_ids':2}
    save(folder/'evidence/E0001_target_profile.json',{'assay_profiles':[profile],
        'target_chembl_id':'CHEMBL1','api_matching_IC50_records':8,'records_retrieved':8})
    p={'version':'synthetic_v1'}
    s={'schema':'task1_agent_v1.0','status':'finished','release':'SYNTHETIC_ONLY','protocol':p,'protocol_sha256':signature(p),
       'catalog_sha256':sha(folder/'catalog.json'),'code_sha256':{'stub.py':sha(folder/'source_snapshot/stub.py')},
       'requests':[],'evidence':{'E0001':{'kind':'target_profile','path':'evidence/E0001_target_profile.json','sha256':sha(folder/'evidence/E0001_target_profile.json')}},
       'profiles':{'CHEMBL1':{'target_id':'CHEMBL1','name':'SYNTHETIC','source_total':8,'records_received':8,
          'retrieval_complete':True,'top_assays_in_window':[profile],'evidence_id':'E0001'}},'assays':{}}
    save(folder/'state.json',s);return folder


class FakeChEMBL:
    def __init__(self,folder,config,log,checkpoint):
        self.folder,self.config,self.log,self.checkpoint=folder,config,log,checkpoint
        self.calls=[];self.confidence=9;self.description='SYNTHETIC biochemical enzyme inhibition IC50; not a binding constant.'
    def get(self,resource,params=None):
        params=params or {};self.calls.append((resource,copy.deepcopy(params)))
        if len(self.log)>=self.config['max_requests']:raise RuntimeError('HTTP budget exhausted')
        if resource=='status':body={'chembl_db_version':'SYNTHETIC_ONLY'}
        elif resource=='activity':
            rows=rows_for(params.get('target_chembl_id','CHEMBL1'))
            if 'only' in params:rows=[{k:r.get(k) for k in params['only'].split(',')} for r in rows]
            body={'activities':rows[params.get('offset',0):params.get('offset',0)+params.get('limit',500)],
                  'page_meta':{'total_count':len(rows),'next':None}}
        elif resource=='assay':
            rows=[{'assay_chembl_id':'CHEMBL2','target_chembl_id':'CHEMBL1','assay_type':'B',
                   'confidence_score':self.confidence,'document_chembl_id':'CHEMBL3'}]
            body={'assays':rows[params['offset']:params['offset']+params['limit']],'page_meta':{'total_count':1,'next':None}}
        elif resource=='assay/CHEMBL2':
            body={'assay_chembl_id':'CHEMBL2','target_chembl_id':'CHEMBL1','document_chembl_id':'CHEMBL3',
                  'assay_type':'B','confidence_score':self.confidence,'description':self.description}
        elif resource=='document/CHEMBL3':body={'document_chembl_id':'CHEMBL3','doc_type':'SYNTHETIC','title':'Synthetic only'}
        elif resource=='compound_record':
            body={'compound_records':[{'record_id':r['record_id'],'molecule_chembl_id':r['molecule_chembl_id'],
                    'compound_name':'SYNTHETIC '+str(r['record_id'])} for r in rows_for()],
                  'page_meta':{'total_count':8,'next':None}}
        else:raise AssertionError(resource)
        filename=f'{len(self.log)+1:04d}_fake.json';save(self.folder/filename,body)
        self.log.append({'url':BASE_URL+'/'+resource+'.json'+('?' + urlencode(params) if params else ''),
                         'http_status':200,'raw_file':'raw/'+filename,'sha256':sha(self.folder/filename)})
        self.checkpoint();return body


class AdaptiveController:
    def call(self,c,receipt):
        assay=next(r for r in c['assay_preview'] if r['assay_id']=='CHEMBL2')
        if not c['assay_preview'][0].get('metadata_evidence_id'):
            action,args='inspect_assay',{'assay_id':'CHEMBL2'}
        elif not assay['description_read']:
            last=c.get('last_evidence_view') or {}
            action,args='read_evidence',{'evidence_id':assay['metadata_evidence_id'],'view':'assay_description',
                'offset':last.get('next_offset') or 0,'limit':4000}
        elif not assay.get('source_assessment'):
            action,args='assess_source',{'assay_id':'CHEMBL2','endpoint':'Synthetic enzyme inhibition IC50',
                'construct_or_receptor':'Synthetic purified enzyme; exact construct needs primary review',
                'status':'primary_review_required','evidence_ids':[assay['metadata_evidence_id']],
                'reason':'Observed metadata supports enzyme inhibition, but primary identity and construct need review.'}
        elif not assay.get('acquisition'):
            action,args='fetch_assay',{'assay_id':'CHEMBL2'}
        elif not assay.get('curation'):
            action,args='curate_assay',{'assay_id':'CHEMBL2'}
        elif not assay.get('decision'):
            action,args='decide_assay',{'assay_id':'CHEMBL2',
                'verdict':'review_shortlist' if assay['curation']['qualification']['numerical_eligibility'] else 'reject',
                'evidence_ids':[assay['metadata_evidence_id'],assay['curation']['evidence_id'],assay['source_assessment']['evidence_id']],
                'interpretation':'assay_defined_inhibition','reason':'Decision follows synthetic numerical gates and documented pending primary review.'}
        else:action,args='finish',{'reason':'Synthetic review path complete; no scientific approval or campaign.'}
        save(receipt,{'status':'synthetic_decision','usage':{'prompt_tokens':7,'completion_tokens':3,'total_tokens':10}})
        return {'action':action,'arguments':args,'reason':'Choose the next tool from current synthetic evidence.'}


class Response:
    status=200
    def __init__(self,content):self.content=content
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self):return json.dumps({'id':'synthetic','usage':{'prompt_tokens':7,'completion_tokens':3,'total_tokens':10},
        'choices':[{'message':{'content':self.content}}]}).encode()


class V2Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.prior=prior_fixture(self.root)
        p=read(PACKAGE/'protocol.json');p.update(minimum_usable_compounds=6,preferred_usable_compounds=8,
            minimum_hits=2,minimum_nonhits=2,query_budget=4,initialization_queries=2,feedback_batch_size=1,
            maximum_query_fraction=1,minimum_scaffold_buckets=1,maximum_largest_cluster_fraction=1,
            maximum_initial_single_class_probability=1)
        save(self.root/'synthetic_protocol.json',p)
        self.folder=prepare(self.prior,self.root/'runs',self.root/'synthetic_protocol.json')
        self.engine=load_engine(self.folder,FakeChEMBL)

    def run_synthetic(self,steps=12):
        with redirect_stdout(io.StringIO()):return run_steps(self.engine,AdaptiveController(),steps)

    def test_prescreen_counts_sparse_targets_without_fetching_windows(self):
        with redirect_stdout(io.StringIO()):report=prescreen(self.engine,3,3)
        counts=self.engine.state['target_counts']
        self.assertEqual(counts['CHEMBL4']['raw_activity_count'],1)
        self.assertEqual(counts['CHEMBL5']['raw_activity_count'],0)
        windows=[p for r,p in self.engine.client.calls if r=='activity' and p.get('limit')!=1]
        self.assertEqual(len(windows),1)
        self.assertEqual(windows[0]['target_chembl_id'],'CHEMBL1')
        self.assertIn('only',windows[0]);self.assertNotIn('assay_description',windows[0]['only'])
        self.assertEqual(report['llm_attempts'],0)

    def test_adaptive_end_to_end_exports_only_review_draft(self):
        result=self.run_synthetic()
        self.assertEqual(result['status'],'finished');self.assertEqual(result['review_shortlist'],['CHEMBL2'])
        folder=next((self.folder/'drafts').iterdir());public=read(folder/'public/candidates.json');labels=read(folder/'private/labels.json')
        self.assertEqual(len(public),6);self.assertEqual(sum(r['outcome'] for r in labels),3)
        self.assertTrue(all(set(r)=={'compound_id','smiles'} for r in public))
        manifest=read(folder/'manifest.json')
        self.assertEqual(manifest['tier'],'limited_feasibility_review_candidate')
        self.assertFalse(manifest['source_assessment']['scientific_review_complete'])
        self.assertFalse(result['campaign_ready'])

    def test_source_hold_blocks_model_shortlist(self):
        self.run_synthetic(5)
        item=self.engine.state['assays']['CHEMBL2']
        self.engine.source_holds['CHEMBL2']={'reason':'SYNTHETIC known unresolved source'}
        with self.assertRaisesRegex(ValueError,'Known primary source hold'):
            self.engine.decide_assay('CHEMBL2','review_shortlist',
                [item['metadata'],item['curation']['evidence_id'],item['source_assessment']['evidence_id']],
                'assay_defined_inhibition','A long but unsupported claim that this source should be admitted.')
        self.assertEqual(self.engine.state['shortlist'],[])

    def test_partial_description_cannot_be_assessed_as_read(self):
        self.engine.client.description='SYNTHETIC '+('description '*500)
        item=self.engine.inspect_assay('CHEMBL2');eid=item['evidence_id']
        page=self.engine.read_evidence(eid,'assay_description',0,100)
        self.assertTrue(page['truncated']);self.assertFalse(self.engine.description_read(eid))
        with self.assertRaisesRegex(ValueError,'Read complete'):
            self.engine.assess_source('CHEMBL2','Enzyme IC50','Unresolved construct','primary_review_required',[eid],'Needs primary source review')
        while page['next_offset'] is not None:page=self.engine.read_evidence(eid,'assay_description',page['next_offset'],4000)
        self.assertTrue(self.engine.description_read(eid))

    def test_invalid_format_is_corrected_with_receipts_and_usage(self):
        invalid=json.dumps({'action':'finish','arguments':{},'reason':'Missing argument'})
        valid=json.dumps({'action':'finish','arguments':{'reason':'Synthetic bounded finish'},'reason':'Stop on available evidence'})
        replies=iter([invalid,valid]);contexts=[]
        def opener(request,**kw):
            contexts.append(json.loads(request.data)['messages'][1]['content']);return Response(next(replies))
        controller=GLM(self.engine.p,'FAKE_SECRET',opener)
        with redirect_stdout(io.StringIO()):report=run_steps(self.engine,controller,1)
        self.assertEqual(report['status'],'finished');self.assertEqual(report['llm_attempts'],2)
        self.assertIn('missing=',contexts[1]);self.assertEqual(report['llm_usage_returned']['total_tokens'],20)
        self.assertEqual(len([e for e in self.engine.state['events'] if e['kind']=='tool_action']),1)
        self.assertEqual(read(self.folder/'llm/0001.json')['status'],'invalid_decision')
        self.assertNotIn('FAKE_SECRET',(self.folder/'llm/0001.json').read_text(encoding='utf-8'))

    def test_format_correction_limit_stops_without_tools(self):
        controller=GLM(self.engine.p,'FAKE',lambda *a,**k:Response('{}'))
        with redirect_stdout(io.StringIO()):report=run_steps(self.engine,controller,1)
        self.assertEqual(report['status'],'paused_after_format_limit');self.assertEqual(report['llm_attempts'],3)
        self.assertEqual(report['llm_usage_returned']['total_tokens'],30)
        self.assertFalse(any(e['kind']=='tool_action' for e in self.engine.state['events']))

    def test_http_error_does_not_trigger_format_retry(self):
        calls=[]
        def opener(*args,**kwargs):
            calls.append(1);raise HTTPError('synthetic',429,'busy',{},io.BytesIO(b'{"error":{"code":"1305"}}'))
        with self.assertRaises(APIError):run_steps(self.engine,GLM(self.engine.p,'FAKE',opener),1)
        self.assertEqual(len(calls),1);self.assertEqual(self.engine.state['llm_attempts'],1)
        self.assertEqual(self.engine.state['status'],'paused_after_api_failure')
        self.assertEqual(self.engine.state['llm_attempts_without_returned_usage'],1)
        # An interruption after reserving an attempt but before its receipt is not zero usage.
        self.engine.state['llm_attempts']+=1;refresh_usage(self.engine)
        self.assertEqual(self.engine.state['llm_attempts_without_returned_usage'],2)

    def test_resume_keeps_completed_tool_steps(self):
        self.run_synthetic(3);self.engine=load_engine(self.folder,FakeChEMBL)
        report=self.run_synthetic()
        self.assertEqual(report['status'],'finished')
        actions=[e['decision']['action'] for e in self.engine.state['events'] if e['kind']=='tool_action']
        self.assertEqual(actions.count('inspect_assay'),1)
        self.assertEqual(actions.count('read_evidence'),1)

    def test_compact_context_excludes_full_history_and_limits_views(self):
        self.engine.inspect_assay('CHEMBL2')
        self.engine.state['events']=[{'kind':'test','result':{'huge':'x'*100000}}]*20
        c=self.engine.context();serialized=json.dumps(c,ensure_ascii=False)
        self.assertLess(len(serialized),24000);self.assertNotIn('x'*100,serialized)
        self.assertNotIn('assays',c);self.assertIsNone(c['last_evidence_view'])
        with self.assertRaises(ValueError):self.engine.read_evidence('E9999','summary',0,4001)
        with self.assertRaises(ValueError):self.engine.checked_get('../../secret')

    def test_prior_and_protocol_changes_are_rejected(self):
        (self.folder/'prior_exposure.json').write_text('{}',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'exposure'):load_engine(self.folder,FakeChEMBL)
        state=read(self.prior/'state.json');state['status']='running';save(self.prior/'state.json',state)
        with self.assertRaisesRegex(ValueError,'completed original'):prepare(self.prior,self.root/'new',self.root/'synthetic_protocol.json')

    def test_parser_requires_verdict_and_rejects_duplicate_json_keys(self):
        value={'action':'decide_assay','arguments':{'assay_id':'CHEMBL2','evidence_ids':['E0001'],
               'interpretation':'assay_defined_inhibition','reason':'Scientific evidence rationale'},'reason':'Top rationale'}
        with self.assertRaisesRegex(DecisionFormatError,'verdict'):parse_decision(json.dumps(value))
        with self.assertRaises(DecisionFormatError):parse_decision('{"action":"finish","action":"shell","arguments":{},"reason":"x"}')

    def test_numerical_tiers_preserve_class_and_budget_gates(self):
        protocol=read(PACKAGE/'protocol.json')
        summary={'complete':True,'target_type':'SINGLE PROTEIN','assay_type':'B','confidence_score':9,
            'budget':{'provisional_pool_size':250,'hit_support_count':100,'nonhit_support_count':150,
                'proposals':[{'pool_large_enough':True,'initialization_probability_single_class':0.02}]},
            'diversity':{'largest_cluster_fraction':0.1,'scaffold_count_including_acyclic_bucket':20}}
        self.assertEqual(qualification(summary,protocol)['tier'],'limited_feasibility_review_candidate')
        summary['budget']['provisional_pool_size']=500
        summary['budget']['nonhit_support_count']=400
        self.assertEqual(qualification(summary,protocol)['tier'],'preferred_review_candidate')
        summary['budget']['nonhit_support_count']=99
        self.assertIn('nonhits',qualification(summary,protocol)['failed_checks'])
        summary['budget']['provisional_pool_size']=249
        self.assertIn('campaign_query_fraction',qualification(summary,protocol)['failed_checks'])
        summary['confidence_score']=8
        self.assertIn('mapping_confidence',qualification(summary,protocol)['failed_checks'])

    def test_truncated_assay_is_not_curated_or_shortlisted(self):
        self.engine.p['maximum_assay_records']=3
        self.engine.inspect_assay('CHEMBL2')
        acquired=self.engine.fetch_assay('CHEMBL2')
        self.assertFalse(acquired['complete']);self.assertEqual(acquired['records_received'],3)
        with self.assertRaisesRegex(ValueError,'Incomplete'):self.engine.curate_assay('CHEMBL2')
        self.assertEqual(self.engine.state['shortlist'],[])

    def test_closed_assay_and_run_cannot_be_changed_by_prescreen(self):
        self.run_synthetic()
        before=copy.deepcopy(self.engine.state);calls=len(self.engine.client.calls)
        with self.assertRaisesRegex(ValueError,'before its first GLM'):prescreen(self.engine,3,3)
        self.assertEqual(self.engine.state,before);self.assertEqual(len(self.engine.client.calls),calls)
        item=self.engine.state['assays']['CHEMBL2']
        with self.assertRaisesRegex(ValueError,'after an assay disposition'):
            self.engine.assess_source('CHEMBL2','Synthetic enzyme IC50','Exact construct unresolved',
                'blocked',[item['metadata']],'Attempted change after an immutable decision')

    def test_argument_bounds_are_correctable_format_errors(self):
        for action,args in [('screen_targets',{'count':0}),
            ('read_evidence',{'evidence_id':'E0001','view':'summary','offset':0,'limit':4001}),
            ('inspect_assay',{'assay_id':'../../private'})]:
            with self.assertRaises(DecisionFormatError):
                parse_decision(json.dumps({'action':action,'arguments':args,'reason':'Invalid synthetic argument'}))


if __name__=='__main__':unittest.main()
