"""Targeted feedback and disposition checks; synthetic data, no real APIs."""
import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from urllib.parse import urlencode

from .test_agent import prior_fixture,FakeChEMBL
from .engine import read,save,sha
from .run import PACKAGE,prepare,load_engine,run_steps
from .controller import parse_decision,DecisionFormatError
from .vendor.discovery import BASE_URL


class TwentyAssayClient(FakeChEMBL):
    def get(self,resource,params=None):
        if resource!='assay':return super().get(resource,params)
        rows=[{'assay_chembl_id':f'CHEMBL{200+i}','target_chembl_id':'CHEMBL1','confidence_score':9,
               'assay_type':'B','document_chembl_id':'CHEMBL3'} for i in range(20)]
        body={'assays':rows,'page_meta':{'total_count':20,'next':None}}
        filename=f'{len(self.log)+1:04d}_fake.json';save(self.folder/filename,body)
        self.log.append({'url':BASE_URL+'/assay.json?'+urlencode(params),'http_status':200,
            'raw_file':'raw/'+filename,'sha256':sha(self.folder/filename)})
        self.checkpoint();return body


class FeedbackTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.folder=prepare(prior_fixture(self.root),self.root/'runs');self.engine=load_engine(self.folder,FakeChEMBL)

    def test_metadata_value_and_cache_status_are_delivered(self):
        self.engine.client.confidence=8
        self.engine.execute('inspect_assay',{'assay_id':'CHEMBL2'},action_reason='Read the actual synthetic metadata.')
        c=self.engine.context()
        self.assertEqual(c['last_tool_result']['payload']['confidence_score'],8)
        self.assertEqual(c['active_assay_progress']['assay']['metadata']['confidence_score'],8)
        self.assertIn('metadata_gate',c['active_assay_progress']['suggested_tools'][0])
        self.engine.execute('inspect_assay',{'assay_id':'CHEMBL2'},action_reason='Explicit synthetic cache reread.')
        self.assertTrue(self.engine.context()['last_tool_result']['cache_replay'])

    def test_all_twenty_returned_assays_reach_next_context(self):
        self.engine=load_engine(self.folder,TwentyAssayClient)
        self.engine.execute('list_assays',{'target_id':'CHEMBL1','offset':0,'limit':20},action_reason='List a new assay page.')
        c=self.engine.context();rows=c['last_tool_result']['payload']['rows']
        self.assertEqual(len(rows),20)
        self.assertEqual({r['assay_chembl_id'] for r in rows},{f'CHEMBL{200+i}' for i in range(20)})
        self.assertLessEqual(len(json.dumps(c,ensure_ascii=False,sort_keys=True)),24000)

    def test_wrong_evidence_view_returns_kind_and_available_views(self):
        self.engine.execute('inspect_assay',{'assay_id':'CHEMBL2'},action_reason='Read synthetic metadata.')
        with self.assertRaisesRegex(ValueError,'View absent'):
            self.engine.execute('read_evidence',{'evidence_id':'E0001','view':'assay_description','offset':0,'limit':4000},action_reason='Synthetic wrong evidence view.')
        feedback=self.engine.context()['last_tool_result']
        self.assertEqual(feedback['status'],'tool_error');self.assertEqual(feedback['evidence']['kind'],'prior_target_profile')
        self.assertNotIn('assay_description',feedback['evidence']['available_views'])

    def test_read_text_identity_cannot_silently_become_another_assay(self):
        eid=self.engine.evidence('assay_metadata',{'assay':{'assay_chembl_id':'CHEMBL9','target_chembl_id':'CHEMBL4','description':'Other receptor experiment'}})
        self.engine.read_evidence(eid,'assay_description',0,4000)
        self.engine.execute('inspect_assay',{'assay_id':'CHEMBL2'},action_reason='Switch to another synthetic assay.')
        c=self.engine.context()
        self.assertEqual(c['last_evidence_view']['evidence_identity']['assay_id'],'CHEMBL9')
        self.assertFalse(c['last_evidence_view']['same_assay_as_active'])
        self.assertEqual(c['active_assay_progress']['assay']['assay_id'],'CHEMBL2')

    def test_active_assay_is_visible_even_outside_ranked_preview(self):
        for i in range(10):
            aid=f'CHEMBL{900+i}';self.engine.state['known_assays'][aid]='CHEMBL1'
        self.engine.state['active_assay_id']='CHEMBL909'
        c=self.engine.context()
        self.assertNotIn('CHEMBL909',[r['assay_id'] for r in c['assay_preview']])
        self.assertEqual(c['active_assay_progress']['assay']['assay_id'],'CHEMBL909')

    def test_partial_window_counts_cannot_establish_rejection_basis(self):
        self.engine.client.confidence=8
        eid=self.engine.inspect_assay('CHEMBL2')['evidence_id']
        with self.assertRaisesRegex(ValueError,'basis not established'):
            self.engine.decide_assay('CHEMBL2','reject',[eid],'assay_defined_inhibition',
                'A preview contains few source IDs, but this is not a complete assay count.',basis='count_upper_bound')
        decision=self.engine.decide_assay('CHEMBL2','reject',[eid],'assay_defined_inhibition',
            'The observed mapping confidence fails the fixed metadata gate.',basis='metadata_gate')
        self.assertEqual(decision['basis'],'metadata_gate')

    def test_full_new_description_page_survives_payload_size_control(self):
        self.engine.client.description='abcd'*6000
        meta=self.engine.execute('inspect_assay',{'assay_id':'CHEMBL2'},action_reason='Inspect a long synthetic description.')
        self.assertTrue(self.engine.context()['last_tool_result']['payload']['description_preview_truncated'])
        self.engine.execute('read_evidence',{'evidence_id':meta['evidence_id'],'view':'assay_description','offset':0,'limit':4000},action_reason='Read first full synthetic page.')
        c=self.engine.context();self.assertEqual(c['last_tool_result']['payload']['text'],'abcd'*1000)
        self.assertFalse(self.engine.description_read(meta['evidence_id']))
        self.assertLessEqual(len(json.dumps(c,ensure_ascii=False,sort_keys=True)),24000)

    def test_count_units_do_not_relabel_assay_ids_as_activity_records(self):
        c=self.engine.context();self.assertEqual(c['known_assay_ids'],1)
        self.assertNotIn('assay_count',c);self.assertIn('target_count_units',c)

    def test_disposition_parser_requires_explicit_basis(self):
        d={'action':'decide_assay','arguments':{'assay_id':'CHEMBL2','verdict':'reject','evidence_ids':['E0001'],
            'interpretation':'assay_defined_inhibition'},'reason':'A verified metadata failure supports this rejection.'}
        with self.assertRaisesRegex(DecisionFormatError,'basis'):parse_decision(json.dumps(d))
        d['arguments']['basis']='metadata_gate';self.assertEqual(parse_decision(json.dumps(d))['arguments']['basis'],'metadata_gate')


if __name__=='__main__':unittest.main()
