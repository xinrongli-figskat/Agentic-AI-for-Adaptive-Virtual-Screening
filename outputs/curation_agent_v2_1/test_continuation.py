"""Offline interface/continuation checks, including reported layouts; no real API."""
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout

from curation_agent_v2.run import prepare as prepare_old
from curation_agent_v2.efficient import Engine as OldEngine
from .test_agent import prior_fixture,FakeChEMBL
from .engine import read,save,signature
from .controller import parse_decision,DecisionFormatError
from .continuation import continue_v2,file_hashes
from .run import PACKAGE,prepare,load_engine,run_steps


def paused_parent(root,attempts=19):
    parent=prepare_old(prior_fixture(root),root/'v2_runs')
    state=read(parent/'state.json');engine=OldEngine(parent,state,FakeChEMBL)
    metadata=engine.inspect_assay('CHEMBL2')['evidence_id']
    engine.read_evidence(metadata,'assay_description',0,4000)
    assessment=engine.assess_source('CHEMBL2','Synthetic enzyme inhibition IC50','Exact synthetic construct unresolved',
        'primary_review_required',[metadata],'Synthetic metadata cannot establish all primary sample identities.')
    engine.fetch_assay('CHEMBL2');curation=engine.curate_assay('CHEMBL2')
    engine.decide_assay('CHEMBL2','reject',[metadata,assessment['evidence_id'],curation['evidence_id']],
        'assay_defined_inhibition','Synthetic pool is smaller than the reviewed numerical gates; reject this assay.')
    for n in range(1,attempts+1):
        save(parent/'llm'/f'{n:04d}.json',{'status':'invalid_decision' if n>attempts-3 else 'synthetic_history',
            'usage':{'prompt_tokens':7,'completion_tokens':3,'total_tokens':10},
            'returned_content':'{}','validation_error':'Synthetic format fixture'})
    state.update(status='paused_after_format_limit',llm_attempts=attempts,format_corrections_used=2,
        usage={'prompt_tokens':7*attempts,'completion_tokens':3*attempts,'total_tokens':10*attempts})
    engine.checkpoint();(parent/'.writer.lock').write_bytes(b'0')
    return parent


class SyntheticFinish:
    def call(self,context,receipt):
        save(receipt,{'status':'synthetic_decision','usage':{'prompt_tokens':7,'completion_tokens':3,'total_tokens':10}})
        return {'action':'finish','arguments':{},'reason':'Synthetic continuation completed without a scientific approval or a new campaign.'}


class ContinuationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.parent=paused_parent(self.root)

    def test_inherits_evidence_decisions_attempts_usage_without_parent_changes(self):
        before=file_hashes(self.parent);old=read(self.parent/'state.json')
        lock_before=(self.parent/'.writer.lock').read_bytes()
        child=continue_v2(self.parent,self.root/'new_runs');new=read(child/'state.json')
        self.assertEqual(file_hashes(self.parent),before)
        self.assertEqual((self.parent/'.writer.lock').read_bytes(),lock_before)
        self.assertEqual(new['llm_attempts'],19);self.assertEqual(new['usage']['total_tokens'],190)
        self.assertEqual(new['requests'],old['requests']);self.assertEqual(new['assays'],old['assays'])
        self.assertEqual(new['evidence'],old['evidence']);self.assertEqual(new['prior_exposure_sha256'],old['prior_exposure_sha256'])
        self.assertEqual(read(child/'history_v2/state.json'),old)
        self.assertEqual(new['protocol']['maximum_llm_attempts'],40)
        self.assertFalse(read(child/'continuation.json')['budgets_reset'])
        self.assertEqual(load_engine(child).report()['schema'],'task1_agent_v2.1')

    def test_repeated_continuation_returns_advanced_child_without_budget_reset(self):
        child=continue_v2(self.parent,self.root/'new_runs');engine=load_engine(child,FakeChEMBL)
        with redirect_stdout(io.StringIO()):run_steps(engine,SyntheticFinish(),1)
        self.assertEqual(engine.state['llm_attempts'],20)
        again=continue_v2(self.parent,self.root/'new_runs')
        self.assertEqual(child,again);self.assertEqual(read(child/'state.json')['llm_attempts'],20)
        self.assertEqual(read(child/'state.json')['usage']['total_tokens'],200)

    def test_changed_scientific_protocol_cannot_be_called_interface_continuation(self):
        state=read(self.parent/'state.json');state['protocol']['minimum_usable_compounds']=249
        state['protocol_sha256']=signature(state['protocol']);save(self.parent/'state.json',state)
        with self.assertRaisesRegex(ValueError,'Parent protocol'):continue_v2(self.parent,self.root/'new_runs')
        self.assertFalse((self.root/'new_runs').exists())

    def test_corrupt_evidence_is_rejected_before_copy(self):
        state=read(self.parent/'state.json');first=next(iter(state['evidence'].values()))
        (self.parent/first['path']).write_text('{}',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'evidence hash'):continue_v2(self.parent,self.root/'new_runs')
        self.assertFalse((self.root/'new_runs').exists())

    def test_inherited_exhausted_budget_does_not_call_model(self):
        for n in range(20,41):
            save(self.parent/'llm'/f'{n:04d}.json',{'usage':{'prompt_tokens':7,'completion_tokens':3,'total_tokens':10}})
        state=read(self.parent/'state.json');state['llm_attempts']=40
        state['usage']={'prompt_tokens':280,'completion_tokens':120,'total_tokens':400};save(self.parent/'state.json',state)
        child=continue_v2(self.parent,self.root/'new_runs');engine=load_engine(child,FakeChEMBL)
        class NeverCall:
            def call(self,*a):raise AssertionError('Inherited budget was reset')
        report=run_steps(engine,NeverCall(),1)
        self.assertEqual(report['status'],'llm_budget_exhausted');self.assertEqual(report['llm_attempts'],40)

    def test_reported_reply_layouts_have_one_unambiguous_canonical_reason(self):
        for fixture in read(PACKAGE/'failure_layout_fixtures.json'):
            original=json.loads(fixture['content'])
            if 'reason' not in original or 'reason' in original['arguments']:
                with self.assertRaises(DecisionFormatError):parse_decision(fixture['content'])
            else:
                # Layouts 12 and 18 already have exactly one top-level reason.
                parse_decision(fixture['content'])
            # Explicit unit-test construction only: the production parser never repairs old replies.
            canonical=json.loads(fixture['content']);args=canonical['arguments']
            reason=args.pop('reason',None) or canonical['reason'];canonical['reason']=reason
            parsed=parse_decision(json.dumps(canonical,ensure_ascii=False))
            self.assertNotIn('reason',parsed['arguments']);self.assertEqual(parsed['reason'],reason)

    def test_single_reason_is_preserved_in_the_scientific_assessment(self):
        fresh=self.root/'fresh';fresh.mkdir();folder=prepare(prior_fixture(fresh),fresh/'runs')
        engine=load_engine(folder,FakeChEMBL);eid=engine.inspect_assay('CHEMBL2')['evidence_id']
        engine.read_evidence(eid,'assay_description',0,4000)
        decision={'action':'assess_source','arguments':{'assay_id':'CHEMBL2','endpoint':'Synthetic enzyme IC50',
            'construct_or_receptor':'Exact construct unresolved','status':'primary_review_required','evidence_ids':[eid]},
            'reason':'Metadata is insufficient for full primary sample identity approval; further source review is required.'}
        parsed=parse_decision(json.dumps(decision));engine.execute(parsed['action'],parsed['arguments'],action_reason=parsed['reason'])
        self.assertEqual(engine.state['assays']['CHEMBL2']['source_assessment']['reason'],decision['reason'])
        self.assertFalse(engine.state['assays']['CHEMBL2']['source_assessment']['campaign_ready'])


if __name__=='__main__':unittest.main()
