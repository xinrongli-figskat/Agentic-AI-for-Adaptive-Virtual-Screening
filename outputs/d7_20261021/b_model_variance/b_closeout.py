"""Read-only D7-B Tier B inventory plus new closeout files; no GLM or oracle use."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('/driveA/xinrong/agentic-screening')
sys.path.insert(0, str(ROOT))
PUBLIC = ROOT / 'outputs/d7_20261021/b_model_variance'
PRIVATE = ROOT / 'outputs/d7_20261021/b_model_variance_private'
D6 = ROOT / 'outputs/d6_20261020/b_menu_description_private/runs_v0_replay/runs/tnap/bit'


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path, data):
    assert not path.exists(), f'Will not overwrite existing file: {path}'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False)+'\n', encoding='utf-8')
    if 'private' in str(path):
        os.chmod(path, 0o600)


def main():
    from outputs.d7_20261021.b_model_variance.b_repeat import baseline, inspect_run, verify_lock
    verify_lock()
    baseline()
    assert sha(PUBLIC/'B_LOCK.json') == 'e7e27865e1c1d45ad03eabd7d94899bd0b2464d22d8f9aebc373d3259ffbf8d4'
    reused = sum((D6/f'glm_extended_seed{i}'/'run.json').exists() for i in range(10))
    complete_new = []
    for rep in range(1,6):
        for seed in range(20):
            if rep == 1 and seed < 10:
                continue
            p = PRIVATE/f'rep{rep}'/'runs/tnap/bit'/f'glm_extended_seed{seed}'/'run.json'
            if p.exists() and json.loads(p.read_text()).get('complete'):
                inspect_run(p, seed)
                complete_new.append([seed,rep])
    decisions = sorted(PRIVATE.glob('rep*/seed*/decision_*.json'))
    http = sorted(PRIVATE.glob('rep*/seed*/http_*.json'))
    statuses = Counter(json.loads(p.read_text())['status'] for p in decisions)
    http_statuses = Counter(str(json.loads(p.read_text()).get('http_status')) for p in http)
    partial = PRIVATE/'rep2/runs/tnap/bit/glm_extended_seed13/run.json'
    p = json.loads(partial.read_text())
    observations = [r for step in p['trajectory'] for r in step['observations']]
    assert len(observations) == len({r['compound_key'] for r in observations}) == 20
    assert not p['complete'] and len(p['trajectory']) == 2
    bad = PRIVATE/'rep2/seed13/decision_002.json'
    b = json.loads(bad.read_text())
    assert b['status'] == 'success' and set(json.loads(b['raw_content'])) == {'policy','reason',''}
    assert len(decisions)==len(http)==94 and statuses == {'success':94}
    assert http_statuses == {'200':94} and len(complete_new)==23 and reused==10
    total_usage = Counter()
    for f in decisions:
        u = json.loads(f.read_text()).get('usage') or {}
        for key in ('prompt_tokens','completion_tokens','total_tokens'):
            total_usage[key] += u.get(key,0)
    summary = {
        'generated_utc':utc(),'status':'blocked_tier_b_budget_after_invalid_format',
        'post_exposure':True,'lock_sha256':sha(PUBLIC/'B_LOCK.json'),
        'reused_d6_complete_campaigns':reused,'new_complete_campaigns':len(complete_new),
        'complete_campaigns_total':reused+len(complete_new),'target_campaigns':100,
        'new_decision_calls':len(decisions),'new_http_attempts':len(http),
        'valid_decisions':93,'invalid_decisions':1,'http_status_counts':dict(http_statuses),
        'http_retries':0,'returned_usage':dict(total_usage),
        'partial_campaign':{'seed':13,'repeat':2,'saved_batches':2,'saved_queries':20,
                            'distinct_compounds':20,'valid_feedback_decisions':1,
                            'failed_next_decision':2,'failed_next_decision_oracle_queries':0},
        'valid_decisions_still_needed_for_20x5':267,
        'unused_decision_budget':360-len(decisions),'shortfall':1,
        'no_additional_glm_after_block':True,
        'public_note':'No molecule-level labels, selections or trajectory are included.'
    }
    write_new(PUBLIC/'CLOSEOUT_TIER_B.json',summary)
    (PUBLIC/'STATUS_TIER_B').write_text('blocked_tier_b_budget_after_invalid_format\n',encoding='utf-8')
    (PUBLIC/'RUN_LOG_TIER_B.md').write_text(
        '# D7-B Tier B closeout\n\n'
        f'UTC: {summary["generated_utc"]}. Post-exposure. '
        'D5 and frozen pool files unchanged. Run lock and known-good regressions passed. '
        'Seed 0 repeat 2 pilot passed. Batch stopped automatically on the second GLM '
        'decision of seed 13 repeat 2: HTTP 200 with an extra empty JSON key. '
        'The unchanged D5 parser rejected it before an oracle query. '
        'The 360-call plan now lacks one decision; see BLOCKED_response_format_budget.md.\n',
        encoding='utf-8')
    files = sorted(p for p in PRIVATE.rglob('*') if p.is_file())
    private_manifest={'generated_utc':utc(),'status':'partial_frozen_at_tier_b',
                      'file_count':len(files),
                      'files':{str(p.relative_to(PRIVATE)).replace('\\','/'):sha(p) for p in files}}
    write_new(PRIVATE/'PRIVATE_MANIFEST_TIER_B.json',private_manifest)
    archive = PRIVATE/'partial_evidence_tier_b.zip'
    assert not archive.exists()
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for p in sorted(PRIVATE.rglob('*')):
            if p.is_file() and p != archive:
                z.write(p,arcname=str(p.relative_to(PRIVATE)).replace('\\','/'))
    os.chmod(archive,0o600)
    public_files = ['B_SPEC.md','b_repeat.py','B_LOCK.json','b_closeout.py',
                    'BLOCKED_response_format_budget.md','CLOSEOUT_TIER_B.json',
                    'STATUS_TIER_B','RUN_LOG_TIER_B.md']
    manifest={'generated_utc':utc(),'status':'blocked_tier_b',
              'files':{name:sha(PUBLIC/name) for name in public_files},
              'private_manifest_sha256':sha(PRIVATE/'PRIVATE_MANIFEST_TIER_B.json'),
              'private_archive_sha256':sha(archive),'private_archive_bytes':archive.stat().st_size,
              'private_file_count':len(files)}
    write_new(PUBLIC/'MANIFEST_TIER_B.json',manifest)
    print(json.dumps({'status':summary['status'],'new_decision_calls':len(decisions),
                      'new_http_attempts':len(http),'complete_campaigns':reused+len(complete_new),
                      'private_archive_sha256':manifest['private_archive_sha256'],
                      'manifest_sha256':sha(PUBLIC/'MANIFEST_TIER_B.json')},ensure_ascii=False))


if __name__ == '__main__':
    main()
