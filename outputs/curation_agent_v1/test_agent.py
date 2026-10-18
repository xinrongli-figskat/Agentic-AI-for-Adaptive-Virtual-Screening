"""Synthetic end-to-end tests: decisions, evidence guards, exports and crash recovery.

No API key, internet or actual campaign outcomes are used.
"""
import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode

from .controller import GLM, parse_decision
from .engine import Engine, import_catalog, read, save, sha
from .run import PACKAGE, load_engine, prepare, run_steps
from .vendor import audit, discovery


def seed_fixture(root):
    folder = root / 'seed'
    folder.mkdir()
    (folder / 'raw').mkdir()
    (folder / 'tool_source.py').write_text('# synthetic seed source\n', encoding='utf-8')
    receipts = []
    for name, body, params in [('status', {'chembl_db_version': 'SYNTHETIC_ONLY'}, {}),
        ('target', {'targets': [{'target_chembl_id': 'CHEMBL1', 'pref_name': 'SYNTHETIC_TARGET',
             'target_type': 'SINGLE PROTEIN', 'organism': 'Homo sapiens'}], 'page_meta': {'total_count': 1}},
         {'target_type': 'SINGLE PROTEIN', 'offset': 0})]:
        filename = f'raw/{name}.json'
        save(folder / filename, body)
        receipts.append({'url': discovery.BASE_URL + '/' + name + '.json' + ('?' + urlencode(params) if params else ''),
                         'raw_file': filename, 'http_status': 200, 'sha256': sha(folder / filename)})
    save(folder / 'run_metadata.json', {'completed': True, 'script_sha256': sha(folder / 'tool_source.py'),
                                      'requests': receipts})
    return folder


def synthetic_rows():
    rows = []
    for i, smiles in enumerate(['CCO', 'CCN', 'c1ccccc1', 'Oc1ccccc1', 'CCCl', 'CCBr', 'CCF', 'CCCC'], 1):
        rows.append({'activity_id': i, 'molecule_chembl_id': 'CHEMBL' + str(100+i),
            'canonical_smiles': smiles, 'target_chembl_id': 'CHEMBL1', 'assay_chembl_id': 'CHEMBL2',
            'document_chembl_id': 'CHEMBL3', 'standard_type': 'IC50', 'assay_type': 'B',
            'standard_relation': '=', 'standard_units': 'nM', 'standard_value': '500' if i <= 3 else '2000'})
    rows[-2]['standard_value'] = None  # Must NOT become a measured nonhit.
    rows[-1]['potential_duplicate'] = 1  # Must NOT enter the query pool.
    return rows


class FakeChEMBL:
    confidence = 9

    def __init__(self, folder, config, log, checkpoint):
        self.folder, self.config, self.log, self.checkpoint = folder, config, log, checkpoint

    def get(self, resource, params=None):
        if len(self.log) >= self.config['max_requests']:
            raise RuntimeError('Request budget exceeded')
        if resource == 'status':
            body = {'chembl_db_version': 'SYNTHETIC_ONLY'}
        elif resource == 'activity':
            rows = synthetic_rows()
            body = {'activities': rows[params['offset']:params['offset'] + params['limit']],
                    'page_meta': {'total_count': len(rows)}}
        elif resource == 'assay/CHEMBL2':
            body = {'assay_chembl_id': 'CHEMBL2', 'target_chembl_id': 'CHEMBL1',
                    'document_chembl_id': 'CHEMBL3', 'confidence_score': self.confidence,
                    'description': 'SYNTHETIC biochemical inhibition assay, not binding evidence', 'assay_type': 'B'}
        elif resource == 'document/CHEMBL3':
            body = {'document_chembl_id': 'CHEMBL3', 'title': 'SYNTHETIC ONLY'}
        else:
            raise AssertionError(resource)
        filename = f'{len(self.log)+1:04d}_fake.json'
        save(self.folder / filename, body)
        self.log.append({'url': discovery.BASE_URL + '/' + resource + '.json' + ('?' + urlencode(params) if params else ''),
                         'raw_file': 'raw/' + filename, 'sha256': sha(self.folder / filename), 'http_status': 200})
        self.checkpoint()
        return body


class AdaptiveSyntheticLLM:
    """Branch from TOOL evidence, never consult hidden fixture outcomes."""
    def call(self, context, receipt):
        if not context['profiles']:
            action, args = 'discover_batch', {'offset': 0, 'count': 1}
        elif not context['assays']:
            action, args = 'inspect_assay', {'assay_id': context['profiles'][0]['top_assays_in_window'][0]['assay_chembl_id']}
        else:
            item = context['assays']['CHEMBL2']
            if 'acquisition' not in item:
                action, args = 'fetch_assay', {'assay_id': 'CHEMBL2'}
            elif 'curation' not in item:
                action, args = 'curate_assay', {'assay_id': 'CHEMBL2'}
            elif 'decision' not in item:
                action, args = 'decide_assay', {'assay_id': 'CHEMBL2',
                    'verdict': 'shortlist' if item['curation']['qualification']['numerical_eligibility'] else 'reject',
                    'evidence_ids': [item['metadata'], item['curation']['evidence_id']],
                    'interpretation': 'assay_defined_inhibition',
                    'reason': 'Synthetic evidence supports this decision under fixed criteria; inhibition is not direct binding.'}
            else:
                action, args = 'finish', {'reason': 'Synthetic path completed with evidence-specific decision.'}
        save(receipt, {'status': 'synthetic_decision', 'usage': {'prompt_tokens': 7, 'completion_tokens': 3, 'total_tokens': 10}})
        return {'action': action, 'arguments': args, 'reason': 'Decision based on currently available synthetic tool evidence.'}


class Response:
    status = 200

    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        pass

    def read(self):
        return json.dumps(self.body).encode()


class AgentTests(unittest.TestCase):
    def setUp(self):
        # Use workspace TEMP rather than the system TEMP for sandbox portability.
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        p = read(PACKAGE / 'protocol.json')
        p.update(minimum_usable_compounds=6, minimum_hits=2, minimum_nonhits=2,
                 query_budget=4, initialization_queries=2, feedback_batch_size=1,
                 minimum_scaffold_buckets=1, maximum_largest_cluster_fraction=1,
                 maximum_initial_single_class_probability=1)
        self.protocol = self.root / 'test_protocol.json'
        save(self.protocol, p)
        self.seed = seed_fixture(self.root)
        self.folder = prepare(self.seed, self.root / 'runs', self.protocol)
        self.engine = Engine(self.folder, read(self.folder / 'state.json'), FakeChEMBL)

    def execute(self, steps=10):
        with redirect_stdout(io.StringIO()):
            return run_steps(self.engine, AdaptiveSyntheticLLM(), steps)

    def test_end_to_end_shortlist_export_excludes_unknown_and_duplicate(self):
        report = self.execute()
        self.assertEqual(report['status'], 'finished')
        self.assertEqual(report['shortlist'], ['CHEMBL2'])
        folder = next((self.folder / 'drafts').iterdir())
        public = read(folder / 'public/candidates.json')
        private = read(folder / 'private/labels.json')
        self.assertEqual(len(public), 6)
        self.assertEqual(sum(r['outcome'] for r in private), 3)
        self.assertTrue(all(set(r) == {'compound_id', 'smiles'} for r in public))
        self.assertFalse(read(folder / 'manifest.json')['status'] == 'campaign_ready')
        self.assertEqual(report['llm_usage_returned']['total_tokens'], 60)

    def test_decision_changes_when_mapping_evidence_changes(self):
        self.engine.client.confidence = 8
        self.assertEqual(self.execute()['shortlist'], [])
        item = self.engine.state['assays']['CHEMBL2']
        self.assertEqual(item['decision']['verdict'], 'reject')
        self.assertIn('mapping_confidence', item['curation']['qualification']['failed_checks'])

    def test_resume_preserves_completed_steps_and_cached_source(self):
        self.execute(3)
        self.assertEqual(self.engine.state['llm_attempts'], 3)
        state = read(self.folder / 'state.json')
        self.engine = Engine(self.folder, state, FakeChEMBL)
        self.assertEqual(self.execute()['shortlist'], ['CHEMBL2'])
        self.assertEqual(self.engine.state['llm_attempts'], 6)
        actions = [e['decision']['action'] for e in state['events']]
        self.assertEqual(actions.count('fetch_assay'), 1)
        self.assertEqual(len(list((self.folder / 'drafts').iterdir())), 1)

    def test_model_cannot_override_gates_or_invent_citations(self):
        self.engine.client.confidence = 8
        self.execute(4)
        item = self.engine.state['assays']['CHEMBL2']
        args = dict(assay_id='CHEMBL2', verdict='shortlist', interpretation='assay_defined_inhibition',
                    reason='A substantive but unsupported model claim of eligibility.',
                    evidence_ids=[item['metadata'], item['curation']['evidence_id']])
        with self.assertRaisesRegex(ValueError, 'blocked'):
            self.engine.decide_assay(**args)
        args['verdict'] = 'reject'
        args['evidence_ids'] = ['E9999']
        with self.assertRaises(ValueError):
            self.engine.decide_assay(**args)

    def test_incomplete_acquisition_cannot_be_curated(self):
        self.engine.p['maximum_assay_records'] = 2
        self.execute(3)
        self.assertFalse(self.engine.state['assays']['CHEMBL2']['acquisition']['complete'])
        with self.assertRaisesRegex(ValueError, 'Incomplete'):
            self.engine.curate_assay('CHEMBL2')

    def test_hash_tampering_and_tool_escape_are_rejected(self):
        with self.assertRaises(ValueError):
            self.engine.checked_get('assay/../../private/labels')
        with self.assertRaises(ValueError):
            self.engine.execute('shell', {'command': 'anything'})
        (self.folder / 'catalog.json').write_text('[]', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Catalog hash'):
            load_engine(self.folder)
        (self.seed / 'raw/target.json').write_text('{}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'hash'):
            import_catalog(self.seed)

    def test_invalid_llm_keeps_raw_response_and_usage_before_validation(self):
        body = {'id': 'synthetic-request', 'usage': {'total_tokens': 11},
                'choices': [{'message': {'content': '{"invalid":"TOP_SECRET_TEST_KEY"}'}}]}
        receipt = self.root / 'invalid.json'
        client = GLM(self.engine.p, 'TOP_SECRET_TEST_KEY', opener=lambda *a, **k: Response(body))
        with self.assertRaises(ValueError):
            client.call(self.engine.context(), receipt)
        saved = read(receipt)
        self.assertEqual(saved['usage']['total_tokens'], 11)
        self.assertEqual(saved['request_id'], 'synthetic-request')
        self.assertEqual(saved['status'], 'invalid_response')
        self.assertNotIn('TOP_SECRET_TEST_KEY', receipt.read_text())
        self.assertIn('REDACTED', saved['raw_response_text'])

    def test_failure_then_resume_consumes_no_extra_tool_action(self):
        body = {'usage': {'total_tokens': 11}, 'choices': [{'message': {'content': '{}'}}]}
        client = GLM(self.engine.p, 'fake-key', opener=lambda *a, **k: Response(body))
        with self.assertRaises(ValueError):
            run_steps(self.engine, client, 1)
        self.assertEqual(self.engine.state['llm_attempts'], 1)
        self.assertFalse(self.engine.state['profiles'])
        self.assertEqual(self.execute()['status'], 'finished')
        self.assertEqual(self.engine.state['llm_attempts'], 7)
        self.assertEqual(self.engine.state['usage']['total_tokens'], 71)

    def test_strict_json_rejects_duplicate_keys_and_extra_actions(self):
        for text in ['{"action":"finish","action":"shell","arguments":{},"reason":"x"}',
                     '{"action":"finish","arguments":{"reason":"x"},"reason":"x","extra":1}']:
            with self.assertRaises(ValueError):
                parse_decision(text)

    def test_protocol_cannot_change_in_place(self):
        state = read(self.folder / 'state.json')
        state['protocol']['minimum_hits'] = 1
        save(self.folder / 'state.json', state)
        with self.assertRaisesRegex(ValueError, 'Protocol or code changed'):
            load_engine(self.folder)

    def test_valid_api_decision_and_failure_receipt(self):
        content = json.dumps({'action': 'finish', 'arguments': {'reason': 'Insufficient evidence'}, 'reason': 'Stop without fabricated outcomes'})
        good = GLM(self.engine.p, 'test-key', opener=lambda *a, **k: Response({
            'id': 'synthetic-good', 'usage': {'total_tokens': 5}, 'choices': [{'message': {'content': content}}]}))
        self.assertEqual(good.call({}, self.root / 'good.json')['action'], 'finish')
        def bad(*args, **kwargs):
            raise HTTPError('https://example.invalid', 429, 'test', {}, io.BytesIO(b'{"error":{"code":"1305"}}'))
        client = GLM(self.engine.p, 'test-key', opener=bad)
        with self.assertRaisesRegex(RuntimeError, '429'):
            client.call({}, self.root / '429.json')
        self.assertEqual(read(self.root / '429.json')['status'], 'http_error')

    def test_censoring_conflicts_and_structure_duplicate_merge(self):
        config = self.engine.config
        record = synthetic_rows()[0]
        def state(rows):
            return audit.reconcile(rows, config, '1000', discovery.record_signal)
        self.assertEqual(state([{**record, 'standard_relation': '>=', 'standard_value': '1000'}])['provisional_state'], 'unknown')
        self.assertEqual(state([{**record, 'standard_relation': '>', 'standard_value': '1000'}])['provisional_state'], 'nonhit_support')
        self.assertFalse(state([record, {**record, 'activity_id': 20, 'standard_value': '2000'}])['usable_for_prototype_review'])
        policy = read(PACKAGE / 'vendor/audit_policy.json')
        _, _, compounds, _ = audit.audit_records([record,
            {**record, 'activity_id': 20, 'canonical_smiles': 'OCC', 'molecule_chembl_id': 'CHEMBL999'}], config, policy, discovery)
        self.assertEqual(len(compounds), 1)
        self.assertEqual(len(compounds[0]['activity_ids']), 2)

    def test_decision_replay_is_idempotent(self):
        self.execute(5)
        decision = self.engine.state['assays']['CHEMBL2']['decision']
        self.engine.decide_assay('CHEMBL2', **{k: decision[k] for k in ('verdict', 'evidence_ids', 'interpretation', 'reason')})
        self.assertEqual(self.engine.state['shortlist'], ['CHEMBL2'])
        self.assertEqual(len(list((self.folder / 'drafts').iterdir())), 1)

    def test_global_attempt_budget_is_enforced(self):
        self.engine.state['llm_attempts'] = self.engine.p['maximum_llm_attempts']
        report = self.execute(2)
        self.assertEqual(report['status'], 'llm_budget_exhausted')
        self.assertFalse(self.engine.state['profiles'])


if __name__ == '__main__':
    unittest.main()
