"""Inventory saved project files and compare local/remote copies; standard library only.

Reads project bytes, including bounded ZIP members. Writes only requested inventory
and comparison reports. Never connects to SSH/API, copies project data, or deletes.
An editor's unsaved buffers are outside this tool's scope.
"""
import argparse
import csv
import hashlib
import json
import os
import re
import socket
import stat
import time
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

VERSION = 'project_sync_inventory_v1'
EXCLUDED_DIRS = {'.git', '.cache', '__pycache__', 'node_modules', '.ssh', '.config',
                 '.sync_audit', '.pytest_cache', '.mypy_cache', '.ruff_cache'}
SECRET_NAMES = {'zhipu_api_key', 'zai_api_key', 'openai_api_key', 'credentials.json',
                'auth.json', 'id_ed25519', 'id_rsa', 'id_ecdsa'}
SECRET_SUFFIXES = {'.pem', '.key', '.pfx', '.p12'}


def now():
    return datetime.now(timezone.utc).isoformat()


def excluded_dir(name):
    low = name.lower()
    return low in EXCLUDED_DIRS or low.startswith(('.venv', 'venv-', '.env-')) or low in {'venv', 'env'}


def secret(name):
    low = name.lower()
    return (low in SECRET_NAMES or low == '.env' or low.startswith(('.env.', 'id_ed25519', 'id_rsa', 'id_ecdsa'))
            or Path(low).suffix in SECRET_SUFFIXES)


def canonical(path, role):
    parts = list(PurePosixPath(path).parts)
    if role == 'local' and parts and parts[0] == 'outputs':
        parts.pop(0)
    value = '/'.join(parts)
    if len(parts) == 1 and re.match(r'^\d{2}_.+\.md$', parts[0]):
        return 'docs/' + parts[0]
    if value == 'assay_edge_inspection_v0/inspect_assay_edges.py':
        return 'assay_audit_v0/inspect_assay_edges.py'
    if parts and parts[0] == 'task1_v1_review_20261015':
        return 'data/curation_private/research_reviews/' + value
    return value


def importance(relative, role):
    parts = list(PurePosixPath(relative).parts)
    if role == 'local' and parts and parts[0] == 'outputs':
        parts.pop(0)
    path = '/'.join(parts)
    if relative.startswith('work/') or any(p.endswith('_transfer_20261014') for p in parts) or (parts and parts[0] in {
            'assay_review_transfer_20261014', 'next_stage_transfer', 'remote_sync_20261014'}):
        return 'working_or_duplicate_copy'
    if re.match(r'^\d{2}_.+\.md$', path) or path.startswith('docs/'):
        return 'research_note'
    if path.startswith('task1_v1_review_20261015/') or '/research_reviews/' in path:
        return 'review_artifact'
    if path.endswith('.zip') or path.endswith('.zip.sha256'):
        return 'transfer_archive'
    if path.endswith(('.py', '.md', '.toml', '.yaml', '.yml', '.sh', '.json')) and not path.startswith(('data/', 'results/')):
        return 'code_or_document'
    return 'data_or_other'


def hash_stream(handle, deadline):
    h = hashlib.sha256()
    while True:
        if time.monotonic() > deadline:
            raise TimeoutError('Inventory time limit reached')
        chunk = handle.read(1024 * 1024)
        if not chunk:
            return h.hexdigest()
        h.update(chunk)


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temporary, path)


def scan(root, role, *, max_file_bytes=64*1024**2, max_archive_bytes=256*1024**2,
         max_files=30000, time_limit=180):
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError('Project directory not found: ' + str(root))
    started = now()
    deadline = time.monotonic() + time_limit
    files, members, issues = [], [], []
    skipped = Counter()
    archive_count = 0
    truncated = False

    def walk_error(error):
        issues.append({'kind': 'directory_read_error', 'error': type(error).__name__,
                       'path': str(Path(error.filename).relative_to(root)) if error.filename else None})

    for directory, subdirs, names in os.walk(root, followlinks=False, onerror=walk_error):
        parent = Path(directory)
        kept = []
        for name in sorted(subdirs):
            p = parent / name
            if p.is_symlink():
                skipped['symlink_directories'] += 1
            elif excluded_dir(name):
                skipped['excluded_directories'] += 1
            else:
                kept.append(name)
        subdirs[:] = kept
        if truncated:
            break
        for name in sorted(names):
            path = parent / name
            relative = path.relative_to(root).as_posix()
            if secret(name):
                skipped['credential_files'] += 1
                continue
            if path.is_symlink():
                skipped['symlink_files'] += 1
                continue
            if len(files) >= max_files or time.monotonic() > deadline:
                issues.append({'kind': 'scan_limit', 'at': relative})
                truncated = True
                break
            item = {'path': relative, 'canonical': canonical(relative, role),
                    'category': importance(relative, role), 'size': None,
                    'sha256': None, 'status': 'unread'}
            files.append(item)
            try:
                before = path.stat()
                item['size'] = before.st_size
                item['modified_ns'] = before.st_mtime_ns
                if not stat.S_ISREG(before.st_mode):
                    item['status'] = 'not_regular'
                    continue
                if before.st_size > max_file_bytes:
                    item['status'] = 'too_large_not_hashed'
                    continue
                with path.open('rb') as handle:
                    item['sha256'] = hash_stream(handle, deadline)
                after = path.stat()
                if (before.st_mtime_ns, before.st_size) != (after.st_mtime_ns, after.st_size):
                    item.update(status='changed_during_scan', sha256=None)
                    continue
                item['status'] = 'hashed'
                if path.suffix.lower() != '.zip':
                    continue
                archive_count += 1
                with zipfile.ZipFile(path) as z:
                    entries = z.infolist()
                    if len(entries) > 10000 or sum(e.file_size for e in entries) > max_archive_bytes:
                        issues.append({'kind': 'archive_limit', 'path': relative})
                        continue
                    for entry in entries:
                        if time.monotonic() > deadline:
                            issues.append({'kind': 'scan_limit', 'at': relative})
                            truncated = True
                            break
                        if entry.is_dir():
                            continue
                        member = PurePosixPath(entry.filename.replace('\\', '/'))
                        if member.is_absolute() or '..' in member.parts or not member.parts or ':' in member.parts[0]:
                            issues.append({'kind': 'unsafe_archive_member', 'archive': relative})
                            continue
                        if any(excluded_dir(p) for p in member.parts[:-1]) or secret(member.name):
                            skipped['excluded_archive_entries'] += 1
                            continue
                        if stat.S_ISLNK(entry.external_attr >> 16):
                            skipped['archive_symlinks'] += 1
                            continue
                        record = {'archive': relative, 'member': member.as_posix(), 'size': entry.file_size,
                                  'sha256': None, 'status': 'too_large_not_hashed'}
                        members.append(record)
                        if entry.file_size <= max_file_bytes:
                            try:
                                with z.open(entry) as handle:
                                    record['sha256'] = hash_stream(handle, deadline)
                                record['status'] = 'hashed'
                            except Exception as error:
                                record.update(status='error', error_type=type(error).__name__)
                                issues.append({'kind': 'archive_entry_error', 'archive': relative,
                                               'member': member.as_posix(), 'error_type': type(error).__name__})
                    after_archive = path.stat()
                    if (after_archive.st_mtime_ns, after_archive.st_size) != (after.st_mtime_ns, after.st_size):
                        item.update(status='changed_during_scan', sha256=None)
                        for record in members:
                            if record['archive'] == relative:
                                record.update(status='archive_changed_during_scan', sha256=None)
                        issues.append({'kind': 'archive_changed_during_scan', 'path': relative})
            except Exception as error:
                if item['status'] == 'hashed':
                    issues.append({'kind': 'archive_read_error', 'path': relative, 'error_type': type(error).__name__})
                else:
                    item.update(status='error', sha256=None, error_type=type(error).__name__)
                    issues.append({'kind': 'file_read_error', 'path': relative, 'error_type': type(error).__name__})
    return {'schema': VERSION, 'role': role, 'host': socket.gethostname(), 'root': str(root),
            'started_at_utc': started, 'finished_at_utc': now(), 'files': files,
            'archive_members': members, 'issues': issues, 'skipped': dict(skipped),
            'limits': {'max_file_bytes': max_file_bytes, 'max_archive_uncompressed_bytes': max_archive_bytes,
                       'max_files': max_files, 'time_limit_seconds': time_limit},
            'summary': {'regular_files_seen': len(files), 'regular_files_hashed': sum(bool(f['sha256']) for f in files),
                        'zip_files_inspected': archive_count, 'archive_members_seen': len(members),
                        'archive_members_hashed': sum(bool(f['sha256']) for f in members),
                        'scan_truncated': truncated},
            'scope': 'Saved project files only; excludes environments, caches, Git internals, credentials and symlinks. Unhashed/omitted files are not verified. ZIP copies are backup evidence, not deployed code.'}


def classify(source, destination):
    paths, content, archives = defaultdict(list), defaultdict(list), defaultdict(list)
    for row in destination['files']:
        paths[row['canonical']].append(row)
        if row.get('sha256'):
            content[(row['size'], row['sha256'])].append(row['path'])
    for row in destination['archive_members']:
        if row.get('sha256'):
            archives[(row['size'], row['sha256'])].append(row['archive'] + '!' + row['member'])
    result = []
    for row in source['files']:
        same_path = paths.get(row['canonical'], [])
        key = (row['size'], row.get('sha256'))
        copies = content.get(key, []) if row.get('sha256') else []
        zipped = archives.get(key, []) if row.get('sha256') else []
        if not row.get('sha256'):
            status = 'UNVERIFIED_PRESENT' if same_path else 'UNVERIFIED_NOT_LOCATED'
        elif any(r.get('sha256') == row['sha256'] and r['size'] == row['size'] for r in same_path):
            status = 'SAME_AT_EXPECTED_PATH'
        elif same_path:
            status = 'DIFFERENT_AT_EXPECTED_PATH' if any(r.get('sha256') for r in same_path) else 'UNVERIFIED_PRESENT'
        elif copies:
            status = 'SAME_CONTENT_ELSEWHERE'
        elif zipped:
            status = 'ARCHIVED_COPY_ONLY'
        else:
            status = 'NO_MATCH_IN_SCANNED_SCOPE'
        result.append({'path': row['path'], 'canonical': row['canonical'], 'category': row['category'],
                       'size': row['size'], 'sha256': row.get('sha256'), 'status': status,
                       'expected_path_candidates': [r['path'] for r in same_path],
                       'same_content_files': copies, 'same_content_archive_members': zipped})
    return result


LABELS = {
    'SAME_AT_EXPECTED_PATH': '预期路径内容一致',
    'DIFFERENT_AT_EXPECTED_PATH': '预期路径内容不同，需检查版本',
    'SAME_CONTENT_ELSEWHERE': '其他位置有相同副本，部署位置未确认',
    'ARCHIVED_COPY_ONLY': '仅在压缩包中有相同备份',
    'NO_MATCH_IN_SCANNED_SCOPE': '本次扫描范围未找到相同副本',
    'UNVERIFIED_PRESENT': '对应路径存在，但尚未验证内容',
    'UNVERIFIED_NOT_LOCATED': '未完成内容验证，也未定位对应路径',
}


def compare(local, remote, output):
    for value, role in ((local, 'local'), (remote, 'remote')):
        if value.get('schema') != VERSION or value.get('role') != role:
            raise ValueError('Manifest schema or local/remote role does not match')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    directions = {'local_to_remote': classify(local, remote), 'remote_to_local': classify(remote, local)}
    report = {'schema': VERSION, 'compared_at_utc': now(),
              'inventories': {role: {key: m[key] for key in ['host','root','started_at_utc','finished_at_utc','summary','issues','limits']}
                              for role, m in [('local',local),('remote',remote)]},
              'summary': {direction: dict(Counter(r['status'] for r in rows)) for direction, rows in directions.items()},
              'directions': directions, 'labels': LABELS,
              'warning': 'No automatic copying or deletion. Different deployment paths and deliberate data separation may be valid. No-match means only the scanned scope, not proof of lost data. Editor buffers are not inspected.'}
    write_json(output / 'comparison.json', report)
    lines = ['# 本机与远端文件盘点', '', '只比较已经保存到磁盘的内容。不会检查编辑器未保存缓冲区，也不检查是否提交 Git。',
             '不会自动复制、覆盖或删除项目文件。只有 ZIP 副本不代表已经解压安装。', '']
    for role, m in [('本机',local),('远端',remote)]:
        lines.extend([f'- {role}：`{m["root"]}`；清单完成于 {m["finished_at_utc"]}；扫描问题 {len(m["issues"])} 项。'])
    for direction, rows in directions.items():
        title = '本机文件在远端的保存情况' if direction == 'local_to_remote' else '远端文件在本机的保存情况'
        lines.extend(['', '## ' + title, '', '| 状态 | 文件数 |', '|---|---:|'])
        counts = Counter(r['status'] for r in rows)
        lines.extend(f'| {label} | {counts[key]} |' for key, label in LABELS.items())
        focus = [r for r in rows if r['category'] in {'research_note','review_artifact','code_or_document'}
                 and r['status'] in {'NO_MATCH_IN_SCANNED_SCOPE','DIFFERENT_AT_EXPECTED_PATH','ARCHIVED_COPY_ONLY','UNVERIFIED_PRESENT','UNVERIFIED_NOT_LOCATED'}]
        lines.extend(['', '### 优先查看的代码、文档和审查文件', ''])
        if not focus:
            lines.append('此筛选范围内没有待核对项；仍请查看完整 CSV 中的不同路径副本与数据文件。')
        for row in focus[:80]:
            lines.append(f'- `{row["path"]}`：{LABELS[row["status"]]}。')
        if len(focus)>80:
            lines.append(f'其余 {len(focus)-80} 项见 CSV。')
        with (output / (direction + '.csv')).open('w', encoding='utf-8-sig', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ['path','status'])
            writer.writeheader()
            for row in rows:
                writer.writerow({k: json.dumps(v,ensure_ascii=False) if isinstance(v,list) else v for k,v in row.items()})
    lines.extend(['', '## 范围限制', '',
        '- 虚拟环境、缓存、Git 内部文件、凭据和符号链接跳过；超出大小、时间或归档上限的内容不作哈希验证。',
        '- 不同路径但内容相同，表示有字节一致副本，不证明程序正从该位置运行。',
        '- 两端有意保持不同的数据集、临时工作文件与历史版本不一定需要同步；不要据此直接覆盖。',
        '- 清单生成之后的变化不在本次结果中；优先查看 comparison.json 中两端的问题与时间。'])
    (output / 'comparison.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    s = commands.add_parser('scan')
    s.add_argument('--root', type=Path, required=True)
    s.add_argument('--role', choices=['local','remote'], required=True)
    s.add_argument('--out', type=Path, required=True)
    s.add_argument('--max-file-mib', type=int, default=64)
    s.add_argument('--time-limit', type=int, default=180)
    c = commands.add_parser('compare')
    c.add_argument('--local', type=Path, required=True)
    c.add_argument('--remote', type=Path, required=True)
    c.add_argument('--out-dir', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'scan':
        if args.max_file_mib < 1 or args.time_limit < 1:
            parser.error('Limits must be positive')
        if args.out.resolve() == args.root.resolve() or (args.out.exists() and args.out.is_dir()):
            parser.error('--out must be an inventory file, not the project directory')
        manifest = scan(args.root,args.role,max_file_bytes=args.max_file_mib*1024**2,time_limit=args.time_limit)
        write_json(args.out,manifest)
        print(json.dumps({'inventory':str(args.out.resolve()), **manifest['summary'],
                          'issues':len(manifest['issues']), 'skipped':manifest['skipped']},ensure_ascii=False,indent=2))
    else:
        local = json.loads(args.local.read_text(encoding='utf-8-sig'))
        remote = json.loads(args.remote.read_text(encoding='utf-8-sig'))
        report = compare(local,remote,args.out_dir)
        print(json.dumps({'output':str(args.out_dir.resolve()),'summary':report['summary']},ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
