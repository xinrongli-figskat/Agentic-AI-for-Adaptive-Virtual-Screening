"""Synthetic audit checks; no scientific APIs or LLM calls."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from audit_task1_finished_v1 import audit,inventory,sha,signature,read,write_json,visible_metadata


def fixture(root):
    folder=root/'run';folder.mkdir();p={'version':'SYNTHETIC_ONLY'}
    write_json(folder/'catalog.json',[{'target_chembl_id':'CHEMBL1'}]);write_json(folder/'prior_exposure.json',{'synthetic':True})
    (folder/'source_snapshot').mkdir();(folder/'source_snapshot/stub.py').write_text('# Synthetic only\n',encoding='utf-8')
    (folder/'evidence').mkdir();write_json(folder/'evidence/E0001.json',{'assay':{'confidence_score':8,'description':'UNIQUE_SYNTHETIC_DESCRIPTION'}})
    (folder/'raw').mkdir();write_json(folder/'raw/0001.json',{'synthetic':True})
    (folder/'llm').mkdir()
    for n in range(1,4):
        context={'assay_preview':[],'recent_actions':[{'action':'inspect_assay','evidence_id':'E0001'}]}
        if n==3:context['assay_preview']=[{'assay_id':'CHEMBL2','confidence_score':8,'description':'UNIQUE_SYNTHETIC_DESCRIPTION'}]
        write_json(folder/'llm'/f'{n:04d}.json',{'status':'valid_decision','usage':{'prompt_tokens':7,'completion_tokens':3,'total_tokens':10},
            'request':{'messages':[{'role':'user','content':json.dumps(context)}]},'elapsed_seconds':1.2})
    summary={'assay_id':'CHEMBL2','target_id':'CHEMBL1','evidence_id':'E0001','confidence_score':8,
             'description':'UNIQUE_SYNTHETIC_DESCRIPTION','assay_type':'B','document_chembl_id':'CHEMBL3'}
    event={'kind':'tool_action','decision':{'action':'inspect_assay','arguments':{'assay_id':'CHEMBL2'},'reason':'Synthetic evidence inspection'},
           'status':'success','result':summary,'llm_attempt':1}
    second=copy.deepcopy(event);second['llm_attempt']=2
    finish={'kind':'tool_action','decision':{'action':'finish','arguments':{},'reason':'Synthetic bounded finish'},
            'status':'success','result':{},'llm_attempt':3}
    state={'status':'finished','finish_reason':'Synthetic bounded finish','release':'SYNTHETIC_ONLY','protocol':p,'protocol_sha256':signature(p),
        'catalog_sha256':sha(folder/'catalog.json'),'prior_exposure_sha256':sha(folder/'prior_exposure.json'),
        'code_sha256':{'stub.py':sha(folder/'source_snapshot/stub.py')},
        'evidence':{'E0001':{'path':'evidence/E0001.json','sha256':sha(folder/'evidence/E0001.json')}},
        'requests':[{'raw_file':'raw/0001.json','sha256':sha(folder/'raw/0001.json'),'elapsed_seconds':0.5}],
        'llm_attempts':3,'usage':{'prompt_tokens':21,'completion_tokens':9,'total_tokens':30},
        'events':[event,second,finish],'profiles':{},'assays':{'CHEMBL2':{'metadata':'E0001','summary':summary}},
        'shortlist':[],'target_counts':{}}
    write_json(folder/'state.json',state);return folder


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        self.run=fixture(self.root)

    def test_reports_repeats_visibility_usage_without_changing_input(self):
        before=inventory(self.run);out,summary=audit(self.run,self.root/'reviews')
        self.assertEqual(inventory(self.run),before);self.assertEqual(summary['llm_usage_returned']['total_tokens'],30)
        self.assertEqual(summary['repeated_inspect_assays'],{'CHEMBL2':2})
        self.assertEqual(summary['tool_result_delivery_diagnostics']['inspected_assay_absent_from_next_preview'],1)
        self.assertEqual(summary['tool_result_delivery_diagnostics']['confidence_not_in_standard_metadata_locations'],1)
        self.assertEqual(summary['numerical_curation_compute']['seconds'],None)
        self.assertTrue((out/'tool_result_visibility.csv').is_file())
        self.assertEqual(read(out/'integrity.json')['run_files_unchanged'],len(before))

    def test_changed_evidence_rejected_before_report_creation(self):
        write_json(self.run/'evidence/E0001.json',{'changed':True})
        with self.assertRaisesRegex(ValueError,'Hash mismatch'):audit(self.run,self.root/'reviews')
        self.assertFalse((self.root/'reviews').exists())

    def test_usage_disagreement_rejected(self):
        state=read(self.run/'state.json');state['usage']['total_tokens']=999;write_json(self.run/'state.json',state)
        with self.assertRaisesRegex(ValueError,'usage totals'):audit(self.run,self.root/'reviews')

    def test_active_runs_and_inside_run_outputs_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'outside'):audit(self.run,self.run/'review')
        state=read(self.run/'state.json');state['status']='running';write_json(self.run/'state.json',state)
        with self.assertRaisesRegex(ValueError,'closed'):audit(self.run,self.root/'reviews')

    def test_visibility_distinguishes_metadata_and_unrelated_views(self):
        c={'assay_preview':[{'assay_id':'CHEMBL2','metadata_evidence_id':'E0001'}],
            'last_evidence_view':{'evidence_id':'E9999','view':'summary','text':'{"confidence_score":8,"description":"other"}'}}
        self.assertEqual(visible_metadata(c,'CHEMBL2','E0001'),(True,False,False))
        c['last_evidence_view']['evidence_id']='E0001'
        self.assertEqual(visible_metadata(c,'CHEMBL2','E0001'),(True,True,True))

    def test_continuation_inherited_receipts_are_verified_and_counted_once(self):
        history=self.run/'history_v2';history.mkdir();write_json(history/'state.json',{'synthetic_old_state':True})
        ledger={'inherited_llm_attempts':1,'parent_files_sha256':{'state.json':sha(history/'state.json'),
            'llm/0001.json':sha(self.run/'llm/0001.json')}}
        write_json(self.run/'continuation.json',ledger);state=read(self.run/'state.json')
        state['continuation']={'ledger_sha256':sha(self.run/'continuation.json')};write_json(self.run/'state.json',state)
        _,summary=audit(self.run,self.root/'reviews')
        self.assertEqual(summary['llm_attempts'],3);self.assertEqual(summary['continuation_new_requests'],2)
        write_json(history/'state.json',{'changed':True})
        with self.assertRaisesRegex(ValueError,'Hash mismatch'):audit(self.run,self.root/'other_review')


if __name__=='__main__':unittest.main()
