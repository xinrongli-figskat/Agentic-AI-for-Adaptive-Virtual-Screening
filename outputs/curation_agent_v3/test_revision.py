"""Budget and immutability tests for a separately declared new experiment."""
from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
import io

from curation_agent_v2_1.test_continuation import paused_parent,SyntheticFinish
from curation_agent_v2_1.continuation import continue_v2
from curation_agent_v2_1.run import load_engine as load_old,run_steps as run_old
from .test_agent import FakeChEMBL
from .revision import prepare_revision
from .run import load_engine,run_steps
from .engine import read,save
from .integrity import inventory


class RevisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        original=paused_parent(self.root)
        self.parent=continue_v2(original,self.root/'v21')
        with redirect_stdout(io.StringIO()):run_old(load_old(self.parent,FakeChEMBL),SyntheticFinish(),1)

    def test_new_explicit_allowance_retains_old_usage_and_parent(self):
        before=inventory(self.parent)
        child=prepare_revision(self.parent,self.root/'v3',3,10);state=read(child/'state.json')
        self.assertEqual(inventory(self.parent),before)
        self.assertEqual(state['llm_attempts'],20);self.assertEqual(state['protocol']['maximum_llm_attempts'],23)
        self.assertEqual(state['usage']['total_tokens'],200)
        self.assertEqual(state['protocol']['maximum_http_requests'],len(state['requests'])+10)
        self.assertEqual(state['assays'],read(self.parent/'state.json')['assays'])
        self.assertEqual(read(child/'revision.json')['additional_llm_budget'],3)
        context=load_engine(child).context()
        self.assertTrue(context['experiment_state']['post_exposure_revision'])
        self.assertEqual(context['experiment_state']['revision']['inherited_llm_attempts'],20)

    def test_repeated_setup_does_not_rewind_advanced_new_experiment(self):
        child=prepare_revision(self.parent,self.root/'v3',3,10)
        with redirect_stdout(io.StringIO()):run_steps(load_engine(child,FakeChEMBL),SyntheticFinish(),1)
        again=prepare_revision(self.parent,self.root/'v3',3,10)
        self.assertEqual(again,child);self.assertEqual(read(child/'state.json')['llm_attempts'],21)

    def test_new_budget_must_be_explicit_and_runtime_cannot_silently_change(self):
        with self.assertRaises(ValueError):prepare_revision(self.parent,self.root/'v3',0,10)
        state=read(self.parent/'state.json');state['environment']['python']='DIFFERENT';save(self.parent/'state.json',state)
        with self.assertRaisesRegex(ValueError,'runtime changed'):prepare_revision(self.parent,self.root/'v3',3,10)


if __name__=='__main__':unittest.main()
