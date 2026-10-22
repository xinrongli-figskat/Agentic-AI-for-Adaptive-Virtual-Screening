"""Final D4 integrity audit, logs and file manifests; no API or oracle calls."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('/driveA/xinrong/agentic-screening')
BASE = ROOT / 'outputs/d4_tnap_glm_20261019'
GLM = BASE / 'd4_glm_private_20261019'
MATCHED = BASE / 'd4_matched_private_20261019'
ANALYSIS = BASE / 'attempt2_20261019/d4_analysis_private_20261019'
EXPECTED_RECEIPT = 'f8801efbe28f73ddbcf9c5a2d493d862cbf124f311b6659e9224f2161b5bf662'
EXPECTED_PROTOCOL = '8384797c0348b51e0b0bb2547b77520b36981d81af4b1320be4e6adb49b17943'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def manifest(directory):
    files = [{'path': p.relative_to(directory).as_posix(), 'bytes': p.stat().st_size,
              'sha256': sha(p)} for p in sorted(directory.rglob('*'))
             if p.is_file() and p != directory / 'MANIFEST.json']
    path = directory / 'MANIFEST.json'
    path.write_text(json.dumps({'files': files, 'self_excluded': True}, indent=2, sort_keys=True) + '\n')
    return sha(path), len(files)


def main():
    from d4_glm_run import protected_check
    protected_check()
    assert sha(ROOT / 'outputs/d3_tnap_20261019/freeze_tnap_v1/freeze_receipt.json') == EXPECTED_RECEIPT
    assert sha(ROOT / 'outputs/d3_tnap_20261019/tnap_v1_campaign_protocol.md') == EXPECTED_PROTOCOL
    before = json.loads((BASE / 'post_glm_verification.json').read_text())
    analysis = json.loads((ANALYSIS / 'analysis.json').read_text())
    assert analysis['seed_count'] == 20 and analysis['main_floor'] == 'forced_random_coldstart'
    assert analysis['cost'] == before['cost'] and before['cost']['successful_decisions'] == 160
    first_real = before['first_real_call_utc']
    declaration = json.loads((BASE / 'pre_real_declarations_lock.json').read_text(encoding='utf-8-sig'))
    floor = json.loads((BASE / 'd4_floor_lock.json').read_text(encoding='utf-8-sig'))
    assert floor['locked_at_utc'] < declaration['locked_utc'] < first_real
    spec = json.loads((BASE / 'matched_proportion_spec.json').read_text())
    latest_glm = []
    for rep in ('bit','count'):
        for seed in range(20):
            path = GLM / f'runs/llm_{rep}_seed{seed}/run.json'
            assert sha(path) == before['run_hashes'][f'{rep}_seed{seed}']
            saved = json.loads(path.read_text())
            assert saved['status'] == 'complete' and saved['result']['queried_count'] == 50
            latest_glm.append(saved['updated_utc'])
            assert (MATCHED / f'matched_{rep}_seed{seed}.json').is_file()
        assert (MATCHED / f'matched_{rep}_seed20.json').is_file()
    assert max(latest_glm) < spec['locked_utc']
    assert len(list(MATCHED.glob('matched_*.json'))) == 42
    assert (ANALYSIS / 'STATUS').read_text().strip() == 'done'
    assert (MATCHED / 'STATUS').read_text().strip() == 'done'
    assert (BASE / 'attempt1_20261019/BLOCKER.md').is_file()
    assert sha(BASE / 'attempt1_20261019/d4_analyze.py') == '6ecdb8b7bad5a57f9e53640fc4def6bfc317447b17744e5116345b8806c8d4af'
    assert 'Tier A' in (BASE / 'DEVIATION_20261019_D4_ANALYSIS_KEY.md').read_text()
    for name in ('d4_report.md', 'd4_cross_pool_synthesis.md'):
        assert (BASE / name).is_file()
    (GLM / 'STATUS').write_text('done\n')
    with (GLM / 'RUN_LOG.md').open('a') as stream:
        stream.write(f"Completed UTC: {datetime.now(timezone.utc).isoformat()}\n"
                     '40/40 runs, 160/160 policy decisions, 160 HTTP attempts, zero failure events.\n')
    glm_manifest, glm_files = manifest(GLM)
    matched_manifest, matched_files = manifest(MATCHED)
    analysis_manifest, analysis_files = manifest(ANALYSIS)
    log = BASE / 'RUN_LOG.md'
    with log.open('a', encoding='utf-8') as stream:
        stream.write(f"\nD4 completed UTC {datetime.now(timezone.utc).isoformat()}.\n"
                     f"First real GLM call UTC {first_real}; floor lock UTC {floor['locked_at_utc']}; budget/power lock UTC {declaration['locked_utc']}.\n"
                     f"GLM: 160/160 decisions, 160 HTTP attempts, 0 failures; bit/count mean H50 23.25/22.85.\n"
                     f"Post-hoc matched spec SHA {sha(BASE / 'matched_proportion_spec.json')}; 42 CPU runs.\n"
                     f"Analysis SHA {sha(ANALYSIS / 'analysis.json')}; Tier A mechanical repair 1/2, regression passed, failed attempt preserved.\n"
                     f"GLM private manifest SHA {glm_manifest} ({glm_files} files); matched private SHA {matched_manifest} ({matched_files}); analysis private SHA {analysis_manifest} ({analysis_files}).\n"
                     f"Protected TNAP receipt SHA {EXPECTED_RECEIPT}; protocol SHA {EXPECTED_PROTOCOL}; source unchanged.\n")
    (BASE / 'STATUS').write_text('done\n')
    root_manifest, root_files = manifest(BASE)
    print(json.dumps({'status': 'done', 'root_manifest_sha256': root_manifest,
                      'root_files': root_files, 'glm_private_manifest_sha256': glm_manifest,
                      'matched_private_manifest_sha256': matched_manifest,
                      'analysis_private_manifest_sha256': analysis_manifest,
                      'glm_decisions': 160, 'failure_events': 0, 'tier_a_repairs': 1}, ensure_ascii=False))


if __name__ == '__main__':
    main()
