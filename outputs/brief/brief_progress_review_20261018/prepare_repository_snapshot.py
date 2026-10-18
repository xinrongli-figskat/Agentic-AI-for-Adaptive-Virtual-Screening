"""Create a code-only, reviewable Git candidate without touching historical files."""
import hashlib
import json
import re
import shutil
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
DEST = ROOT / 'github_snapshot_20261018'
BRIEF = Path(r'D:\Wechat Files\xwechat_files\wxid_pozxbg6467gz22_417d\msg\file\2026-10\Agentic AI for adaptive virtual screening brief.docx')

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    if DEST.exists():
        raise FileExistsError('Snapshot already exists; preserve it and choose a new version.')
    DEST.mkdir()
    (OUT / 'source').mkdir(exist_ok=True)
    shutil.copy2(BRIEF, OUT / 'source' / 'original_brief.docx')
    with ZipFile(BRIEF) as z:
        root = ET.fromstring(z.read('word/document.xml'))
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    paragraphs = []
    for number, paragraph in enumerate(root.findall('.//w:p', ns), 1):
        text = ''.join(node.text or '' for node in paragraph.findall('.//w:t', ns))
        if text:
            paragraphs.append(f'{number}. {text}')
    (OUT / 'source' / 'brief_extracted.md').write_text(
        '# 原始 brief 正文抽取\n\n附件 SHA-256: ' + sha(BRIEF) + '\n\n' + '\n\n'.join(paragraphs) + '\n', encoding='utf-8')
    local = json.loads((OUT / 'local_code_inventory.json').read_text(encoding='utf-8-sig'))['files']
    remote = json.loads((OUT / 'remote_code_inventory.json').read_text(encoding='utf-8-sig'))['files']
    selected = {row['path'] for row in local if not row['path'].startswith(
        ('outputs/results/', 'outputs/remote_sync_20261014/'))}
    packages = ('candidate_discovery_v0', 'assay_audit_v0', 'assay_edge_inspection_v0',
                'curation_agent_v1', 'curation_agent_v2', 'curation_agent_v2_1',
                'curation_agent_v3', 'curation_agent_v4', 'campaign_v0',
                'oracle_boundary_v0', 'freeze_v1', 'dyrk3_prefreeze_v0', 'reporting_v1')
    for name in packages:
        for path in (ROOT / 'outputs' / name).rglob('*'):
            if path.is_file() and path.suffix in ('.json', '.md', '.txt') and '__pycache__' not in path.parts:
                selected.add(path.relative_to(ROOT).as_posix())
    extras = (
        'config/task_params_20261018.json',
        'outputs/low_hit_fallback_design_private_20261017/protocol_proposal.md',
        'outputs/p5_init_gate_private_20261018/init_gate_definition.md',
        'outputs/p5_init_gate_private_20261018/init_gate_provenance.md',
        'outputs/task1_v5_source_adjudication_rules_20261016.md',
        'outputs/task1_v5_execution_plan_20261016.md',
        'outputs/task1_v5_protocol_lock_20261016.json',
        'outputs/r1_criteria_reconstruction_20261018/qualification_criteria_table_reconstructed.csv',
        'outputs/r1_criteria_reconstruction_20261018/monthly_prototype_guidance_v0_3_20261018.md',
        'outputs/r7_oracle_service_private_20261018/BLOCKER.md',
    )
    selected.update(extras)
    rows = []
    for rel in sorted(selected):
        source = ROOT / rel
        assert source.is_file() and not source.is_symlink(), rel
        destination = DEST / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        assert sha(source) == sha(destination)
        rows.append({'path': rel, 'bytes': source.stat().st_size, 'sha256': sha(source),
                     'source_relative_path': rel})
    hashes = {row['sha256'] for row in rows}
    missing = [r['path'] for r in remote if r['sha256'] not in hashes]
    assert not missing, missing
    requirements = OUT / 'requirements.remote-observed.txt'
    (DEST / 'requirements.remote-observed.txt').write_text(
        requirements.read_text(encoding='utf-8-sig'), encoding='utf-8')
    (DEST / '.gitignore').write_text(
        '# Runtime data and secrets are not versioned with the code snapshot.\n'
        '.venv*/\nvenv/\n__pycache__/\n*.py[cod]\n.cache/\n.sync_audit/\n.git/\n'
        '.env\n.env.*\n!.env.example\n.ssh/\n*.pem\n*.key\nid_ed25519*\nid_rsa*\n'
        'zhipu_api_key*\n*credentials*\n'
        'data/\nresults/\noutputs/results/\n**/runs/\n**/raw/\n**/source_snapshot/\n'
        '*oracle_labels*\n*compounds_private*\n*.sqlite\n*.sqlite3\n*.db\n'
        '*.zip\n*.tar\n*.tar.gz\n*.tgz\n*.7z\n*.pdf\n*.docx\n*.png\n'
        'github_snapshot_*/\n', encoding='utf-8')
    (DEST / '.gitattributes').write_text('# Preserve byte-level source hashes in this historical snapshot.\n* -text\n', encoding='utf-8')
    # Pattern scan reports only paths/line numbers, never matched values.
    patterns = {
        'private_key_block': re.compile(r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----'),
        'github_token': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})'),
        'api_token_literal': re.compile(r'\bsk-[A-Za-z0-9_-]{28,}'),
    }
    findings = []
    for path in DEST.rglob('*'):
        if path.is_file():
            text = path.read_text(encoding='utf-8', errors='replace')
            for line_no, line in enumerate(text.splitlines(), 1):
                for name, pattern in patterns.items():
                    if pattern.search(line):
                        findings.append({'path': path.relative_to(DEST).as_posix(), 'line': line_no, 'pattern': name})
    assert not findings, findings
    report = {
        'utc': datetime.now(timezone.utc).isoformat(),
        'original_brief_sha256': sha(BRIEF),
        'local_code_file_instances': len(local), 'remote_code_file_instances': len(remote),
        'remote_unique_code_contents': len({r['sha256'] for r in remote}),
        'copied_files': len(rows), 'copied_bytes': sum(r['bytes'] for r in rows),
        'remote_code_hashes_covered': len(remote), 'remote_unmatched': missing,
        'secret_pattern_findings': findings,
        'secret_scan_scope': 'common private-key/GitHub/sk token patterns; no claim of exhaustive secret detection',
        'git_initialized': False, 'github_uploaded': False,
        'limitations': ['No real datasets, private labels, credentials or original evidence archives copied.',
                       'Historical package names retained for import compatibility.',
                       'Several scripts contain workstation-specific absolute paths; this is not a portable release.',
                       'Code coverage is hash-based; duplicate remote copies count separately.'],
    }
    (OUT / 'repository_readiness.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (DEST / 'SOURCE_COPY_MANIFEST.json').write_text(json.dumps({'files': rows}, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))

if __name__ == '__main__':
    main()
