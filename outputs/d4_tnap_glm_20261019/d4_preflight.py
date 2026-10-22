"""D4 preflight: verify frozen artifacts, then make one synthetic GLM probe."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('/driveA/xinrong/agentic-screening')
OUT = ROOT / 'outputs/d4_tnap_glm_20261019'
D3 = ROOT / 'outputs/d3_tnap_20261019'
FROZEN_V1 = ROOT / 'data/curation_private/frozen_dyrk3_v1'
EXPECTED_RECEIPT = 'f8801efbe28f73ddbcf9c5a2d493d862cbf124f311b6659e9224f2161b5bf662'
EXPECTED_PROTOCOL = '8384797c0348b51e0b0bb2547b77520b36981d81af4b1320be4e6adb49b17943'
EXPECTED_V1_MANIFEST = '3866c7bfc99e92b8e0d6f92b98955d5e68a7ae202f609eac90d0e7a201f98235'


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def write(path: Path, value: dict) -> None:
    if path.exists():
        raise FileExistsError(f'Protected preflight artifact exists: {path}')
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + '\n', encoding='utf-8')


def verify() -> tuple[dict, dict]:
    lock = json.loads((OUT / 'pre_real_declarations_lock.json').read_text(encoding='utf-8-sig'))
    assert lock['before_first_real_glm_call'] is True
    for row in lock['files']:
        assert sha(OUT / row['path']) == row['sha256'], row['path']
    manifest = json.loads((FROZEN_V1 / 'manifest.json').read_text())
    assert sha(FROZEN_V1 / 'manifest.json') == EXPECTED_V1_MANIFEST
    spec = manifest['campaign_spec']
    expected = {'model': 'glm-5.3-flash', 'thinking': 'enabled',
                'reasoning_effort': 'low', 'max_output_tokens': 1024,
                'api_timeout_seconds': 120, 'do_sample': False}
    assert {key: spec[key] for key in expected} == expected
    assert spec['policies'] == ['knn_greedy', 'knn_diverse', 'uniform_random']
    modules = {}
    for name in ('campaign_core.py', 'glm_api.py', 'llm_controller.py', 'numerical_tools.py'):
        current = ROOT / 'campaign_v0' / name
        snapshot = FROZEN_V1 / 'source_snapshot/campaign_v0' / name
        actual, frozen = sha(current), sha(snapshot)
        registered = manifest['source_sha256'][str(current)]
        modules[name] = {'current_sha256': actual, 'v1_snapshot_sha256': frozen,
                         'v1_manifest_sha256': registered, 'identical': actual == frozen == registered}
    parity = {'checked_utc': utc(), 'frozen_v1_manifest_sha256': EXPECTED_V1_MANIFEST,
              'modules': modules, 'request_spec': spec,
              'prompt_config_identical': all(row['identical'] for row in modules.values())}
    write(OUT / 'prompt_config_parity.json', parity)
    assert parity['prompt_config_identical'], 'Tier C: prompt/config parity failure'
    receipt_path = D3 / 'freeze_tnap_v1/freeze_receipt.json'
    protocol_path = D3 / 'tnap_v1_campaign_protocol.md'
    assert sha(receipt_path) == EXPECTED_RECEIPT
    assert sha(protocol_path) == EXPECTED_PROTOCOL
    receipt = json.loads(receipt_path.read_text())
    protected = {}
    for row in receipt['files']:
        snap, source = Path(row['snapshot']), Path(row['source'])
        assert sha(snap) == sha(source) == row['sha256'], snap
        protected[str(snap)] = row['sha256']
    candidates = D3 / 'freeze_tnap_v1/public/candidates.jsonl'
    labels = D3 / 'freeze_tnap_v1_private_labels/oracle_labels.jsonl'
    public_rows = [json.loads(s) for s in candidates.read_text().splitlines() if s]
    private_rows = [json.loads(s) for s in labels.read_text().splitlines() if s]
    assert len(public_rows) == len(private_rows) == 462
    assert all(set(row) == {'compound_key', 'standardized_smiles'} for row in public_rows)
    assert sum(int(row['outcome']) for row in private_rows) == 53
    check = {'checked_utc': utc(), 'receipt_sha256': EXPECTED_RECEIPT,
             'protocol_sha256': EXPECTED_PROTOCOL, 'public_sha256': sha(candidates),
             'private_sha256': sha(labels), 'frozen_files_verified': len(protected),
             'candidate_count': 462, 'measured_hits': 53, 'public_has_no_label_fields': True,
             'protected_file_hashes': protected, 'status': 'pass'}
    write(OUT / 'frozen_integrity_preflight.json', check)
    return spec, check


def probe(spec: dict) -> None:
    if not os.environ.get('ZAI_API_KEY'):
        raise ValueError('ZAI_API_KEY missing; no synthetic API call made')
    sys.path.insert(0, str(ROOT))
    from campaign_v0.glm_api import OfficialGLMDecisionClient
    from campaign_v0.llm_controller import ToolChoiceLLMController
    from campaign_v0.numerical_tools import NumericalTools
    client = OfficialGLMDecisionClient(model_name='glm-5.3-flash')
    controller = ToolChoiceLLMController(client, model_name='glm-5.3-flash')
    state = {'candidate_pool': [{'compound_key': f'synthetic_{i:03d}',
                                 'standardized_smiles': 'C' * (i + 1)} for i in range(1, 7)],
             'revealed': [{'compound_key': 'synthetic_001', 'outcome': 0}],
             'queried_count': 1, 'remaining_budget': 4, 'next_round': 1, 'next_batch_size': 1}
    state['numerical_summary'] = NumericalTools(state['candidate_pool']).describe_state(state)
    start = time.perf_counter()
    decision = controller.choose(state, tuple(spec['policies']))
    elapsed = time.perf_counter() - start
    assert decision['policy'] in spec['policies'] and client.last_request_id
    write(OUT / 'synthetic_probe.json', {
        'checked_utc': utc(), 'probe_only': True, 'uses_real_labels': False,
        'request_succeeded': True, 'request_id': client.last_request_id,
        'policy': decision['policy'], 'usage': client.last_usage,
        'latency_seconds_including_retries': elapsed, 'api_attempt_log': client.last_attempt_log,
        'model': client.model_name})


def main() -> None:
    if any((OUT / name).exists() for name in ('prompt_config_parity.json',
                                               'frozen_integrity_preflight.json',
                                               'synthetic_probe.json')):
        raise FileExistsError('Preflight already attempted; preserve artifacts and use a new attempt directory')
    spec, check = verify()
    probe(spec)
    print(json.dumps({'status': 'pass', 'parity': True,
                      'freeze_receipt_sha256': check['receipt_sha256'],
                      'probe': json.loads((OUT / 'synthetic_probe.json').read_text())}, ensure_ascii=False))


if __name__ == '__main__':
    main()
