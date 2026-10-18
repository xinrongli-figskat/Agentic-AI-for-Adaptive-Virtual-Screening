"""Create/verify content-addressed project ZIP backups. Standard library only.

No SSH, API, extraction, changes to research inputs, or credential contents.
Verification confirms saved bytes, not scientific validity or reproducibility.
"""
import argparse
import hashlib
import json
import os
import re
import socket
import stat
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

SCHEMA = 'agentic_screening_backup_v1'
MANIFEST = '_BACKUP_MANIFEST.json'
EXCLUDED_DIRS = {'.git', '.cache', '.sync_audit', '__pycache__', 'node_modules',
                 '.ssh', '.config', '.pytest_cache', '.mypy_cache', '.ruff_cache', 'venv', 'env'}
SECRET_NAMES = {'zhipu_api_key', 'zai_api_key', 'openai_api_key', 'credentials.json', 'auth.json'}


def utc():
    return datetime.now(timezone.utc).isoformat()


def skip_dir(name):
    value = name.lower()
    return value in EXCLUDED_DIRS or value.startswith(('.venv', 'venv-', '.env-'))


def secret(name):
    value = name.lower()
    return (value in SECRET_NAMES or value == '.env' or
            value.startswith(('.env.', 'id_ed25519', 'id_rsa', 'id_ecdsa')) or
            Path(value).suffix in {'.pem', '.key', '.pfx', '.p12'})


def safe_relative(value):
    if not isinstance(value, str) or '\\' in value or '\x00' in value or ':' in value:
        return False
    p = PurePosixPath(value)
    return bool(p.parts) and not p.is_absolute() and '..' not in p.parts and p.as_posix() == value


def digest_stream(handle):
    h = hashlib.sha256()
    while True:
        chunk = handle.read(1024 * 1024)
        if not chunk:
            return h.hexdigest()
        h.update(chunk)


def digest_file(path):
    with Path(path).open('rb') as handle:
        return digest_stream(handle)


def dump_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp.' + uuid.uuid4().hex)
    with temporary.open('x', encoding='utf-8') as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    temporary.replace(path)


def inventory(root):
    files, skipped = [], []

    def fail(error):
        raise error

    for folder, dirs, names in os.walk(root, followlinks=False, onerror=fail):
        parent = Path(folder)
        kept = []
        for name in sorted(dirs):
            p = parent / name
            rel = p.relative_to(root).as_posix()
            if p.is_symlink() or skip_dir(name) or rel == 'data/curation_private/backups':
                skipped.append({'path': rel, 'reason': 'excluded_directory_or_symlink'})
            else:
                kept.append(name)
        dirs[:] = kept
        for name in sorted(names):
            p = parent / name
            rel = p.relative_to(root).as_posix()
            if p.is_symlink() or secret(name):
                skipped.append({'path': rel, 'reason': 'credential_name_or_symlink'})
                continue
            mode = p.stat().st_mode
            if not stat.S_ISREG(mode):
                skipped.append({'path': rel, 'reason': 'not_regular'})
                continue
            if not safe_relative(rel) or rel == MANIFEST:
                raise ValueError('Unsupported/reserved project file path: ' + rel)
            files.append((rel, p))
    return files, skipped


def create(root, output):
    root, output = Path(root).resolve(), Path(output).resolve()
    if not root.is_dir():
        raise ValueError('Source project directory missing')
    if output.exists():
        raise FileExistsError('Existing backup retained; verify it or use a new output path')
    output.parent.mkdir(parents=True, exist_ok=True)
    files, skipped = inventory(root)
    if any(p.resolve() == output for _, p in files):
        raise ValueError('Output is included in source files')
    temporary = output.with_name(output.name + '.partial.' + uuid.uuid4().hex)
    records, stamps = [], {}
    try:
        with temporary.open('xb') as raw:
            if os.name == 'posix':
                os.chmod(temporary, 0o600)
            with zipfile.ZipFile(raw, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
                for relative, path in files:
                    before = path.stat()
                    stamp = (before.st_size, before.st_mtime_ns)
                    h = hashlib.sha256()
                    size = 0
                    with path.open('rb') as source, archive.open(relative, 'w', force_zip64=True) as target:
                        while True:
                            chunk = source.read(1024 * 1024)
                            if not chunk:
                                break
                            target.write(chunk)
                            h.update(chunk)
                            size += len(chunk)
                    after = path.stat()
                    if stamp != (after.st_size, after.st_mtime_ns) or size != before.st_size:
                        raise RuntimeError('Source changed while backing up: ' + relative)
                    stamps[relative] = stamp
                    records.append({'path': relative, 'size': size, 'sha256': h.hexdigest(),
                                    'modified_ns': before.st_mtime_ns, 'source_mode': stat.S_IMODE(before.st_mode)})
                current, _ = inventory(root)
                if {name for name, _ in current} != set(stamps):
                    raise RuntimeError('Source file list changed while backing up')
                for relative, path in current:
                    s = path.stat()
                    if (s.st_size, s.st_mtime_ns) != stamps[relative]:
                        raise RuntimeError('Source changed before backup completed: ' + relative)
                manifest = {'schema': SCHEMA, 'created_at_utc': utc(), 'source_host': socket.gethostname(),
                            'source_root': str(root), 'file_count': len(records),
                            'total_source_bytes': sum(row['size'] for row in records),
                            'files': records, 'excluded': skipped,
                            'scope': 'Saved project files. Environments, caches, Git internals, known credential names, '
                                     'symlinks and backup directories excluded. No filesystem-wide atomic snapshot. '
                                     'Project ZIP files are preserved as opaque historical artifacts.'}
                archive.writestr(MANIFEST, json.dumps(manifest, ensure_ascii=False, indent=2).encode('utf-8'))
        temporary.replace(output)
    except BaseException:
        if temporary.exists():
            temporary.unlink()
        raise
    return verify(output)


def verify(path, expected_sha256=None):
    path = Path(path).resolve()
    before = path.stat()
    file_hash = digest_file(path)
    if expected_sha256 is not None and file_hash != expected_sha256:
        raise ValueError('Transport archive SHA256 mismatch')
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [i.filename for i in infos]
        if len(names) > 100000 or len(names) != len(set(names)):
            raise ValueError('Duplicate paths or excessive archive entries')
        if any(not safe_relative(i.filename) or i.is_dir() or
               stat.S_ISLNK(i.external_attr >> 16) for i in infos):
            raise ValueError('Unsafe/non-file archive entry')
        if sum(i.file_size for i in infos) > 10 * 1024**3 or archive.getinfo(MANIFEST).file_size > 32 * 1024**2:
            raise ValueError('Archive exceeds verification size bounds')
        manifest = json.loads(archive.read(MANIFEST))
        if manifest.get('schema') != SCHEMA:
            raise ValueError('Unexpected backup schema')
        rows = manifest['files']
        if (not isinstance(rows, list) or len(rows) != manifest['file_count'] or
                any(not safe_relative(r['path']) or r['path'] == MANIFEST or
                    not re.fullmatch('[0-9a-f]{64}', r['sha256']) for r in rows)):
            raise ValueError('Invalid manifest file list')
        expected_names = [r['path'] for r in rows]
        if len(expected_names) != len(set(expected_names)) or set(names) != set(expected_names) | {MANIFEST}:
            raise ValueError('Archive contents differ from manifest')
        for row in rows:
            if archive.getinfo(row['path']).file_size != row['size']:
                raise ValueError('File size mismatch: ' + row['path'])
            with archive.open(row['path']) as handle:
                if digest_stream(handle) != row['sha256']:
                    raise ValueError('File content mismatch: ' + row['path'])
        if sum(r['size'] for r in rows) != manifest['total_source_bytes']:
            raise ValueError('Total byte count mismatch')
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise RuntimeError('Backup changed during verification')
    return {'status': 'VERIFIED_BACKUP_CONTENT', 'verified_at_utc': utc(), 'archive': str(path),
            'archive_sha256': file_hash, 'archive_bytes': after.st_size,
            'source_root': manifest['source_root'], 'source_host': manifest['source_host'],
            'file_count': len(rows), 'total_source_bytes': manifest['total_source_bytes'],
            'excluded_count': len(manifest['excluded']),
            'meaning': 'Every archived project file matches its saved manifest. Not a scientific validation.'}


def check_frozen(root, expected_manifest):
    root = Path(root).resolve()
    frozen = root / 'data/curation_private/frozen_dyrk3_v1'
    manifest_path = frozen / 'manifest.json'
    if digest_file(manifest_path) != expected_manifest:
        raise ValueError('Frozen DYRK3 manifest differs from the previously recorded hash')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest.get('status') != 'frozen_dyrk3_v1':
        raise ValueError('Unexpected frozen version status')

    def confined(value):
        path = Path(value).resolve()
        path.relative_to(root)
        return path

    expected = {
        confined(manifest['public_dir'])/'candidates.jsonl': manifest['data_sha256']['public_candidates'],
        confined(manifest['private_dir'])/'oracle_labels.jsonl': manifest['data_sha256']['private_labels'],
        frozen/'protocol_decisions.md': manifest['protocol_decisions_sha256']}
    for value, wanted in manifest['source_sha256'].items():
        source = confined(value)
        expected[source] = wanted
        expected[frozen/'source_snapshot'/source.relative_to(root)] = wanted
    for path, wanted in expected.items():
        if digest_file(path) != wanted:
            raise ValueError('Frozen source/data/protocol differs: ' + path.relative_to(root).as_posix())
    run_hashes = {}
    run_root = confined(manifest['run_root'])
    for controller in ['fixed','random','llm']:
        for representation in manifest['campaign_spec']['representations']:
            for seed in manifest['campaign_spec']['seeds']:
                path = run_root/f'{controller}_{representation}_seed{seed}'/'run.json'
                run = json.loads(path.read_text(encoding='utf-8'))
                result = run.get('result',{})
                ids = [key for step in result.get('trajectory',[]) for key in step['selection']]
                if (run.get('status') != 'complete' or result.get('queried_count') != 50 or
                        len(ids) != 50 or len(set(ids)) != 50 or
                        run.get('frozen_manifest_sha256') != expected_manifest):
                    raise ValueError('Missing/inconsistent completed campaign: ' + str(path))
                run_hashes[path.relative_to(root).as_posix()] = digest_file(path)
    return {'status': 'PRESERVED_FROZEN_VERSION_AND_COMPLETED_RUNS',
            'frozen_manifest_sha256': expected_manifest, 'frozen_data_code_protocol_checks': len(expected),
            'completed_campaigns': len(run_hashes), 'campaign_file_sha256': run_hashes,
            'scope': 'Frozen hashes and saved completion/query counts only; no campaigns or API calls rerun.'}


def remote_step(root, backup_id, local_sha256, incoming, expected_frozen_manifest=None):
    if not re.fullmatch(r'backup_[0-9]{8}_[0-9a-f]{8}', backup_id):
        raise ValueError('Unexpected backup ID')
    root = Path(root).resolve()
    anchors = check_frozen(root, expected_frozen_manifest) if expected_frozen_manifest else None
    folder = root / 'data/curation_private/backups' / backup_id
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    if os.name == 'posix':
        os.chmod(folder, 0o700)
    target = folder / 'local_snapshot.zip'
    if not target.exists():
        verify(incoming, local_sha256)
        temporary = target.with_name(target.name + '.partial.' + uuid.uuid4().hex)
        try:
            with Path(incoming).open('rb') as source, temporary.open('xb') as destination:
                if os.name == 'posix':
                    os.chmod(temporary, 0o600)
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    destination.write(chunk)
            verify(temporary, local_sha256)
            temporary.replace(target)
        except BaseException:
            if temporary.exists():
                temporary.unlink()
            raise
    received = verify(target, local_sha256)
    dump_json(folder / 'local_received_receipt.json', received)
    remote_zip = folder / 'remote_snapshot.zip'
    exported = verify(remote_zip) if remote_zip.exists() else create(root, remote_zip)
    if exported['source_root'] != str(root):
        raise ValueError('Existing remote backup source root does not match')
    if anchors is not None:
        if check_frozen(root, expected_frozen_manifest) != anchors:
            raise ValueError('Frozen version or campaign files changed during the backup')
        with zipfile.ZipFile(remote_zip) as archive:
            saved = {row['path']:row['sha256'] for row in json.loads(archive.read(MANIFEST))['files']}
        for relative, expected_hash in anchors['campaign_file_sha256'].items():
            if saved.get(relative) != expected_hash:
                raise ValueError('Archived campaign differs from preserved campaign: ' + relative)
        if saved.get('data/curation_private/frozen_dyrk3_v1/manifest.json') != expected_frozen_manifest:
            raise ValueError('Archived frozen manifest hash mismatch')
        exported['preservation_checks'] = anchors
    dump_json(folder / 'remote_created_receipt.json', exported)
    return {'remote_directory': str(folder), 'local_received': received, 'remote_created': exported}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    c = subs.add_parser('create')
    c.add_argument('--root', type=Path, required=True)
    c.add_argument('--out', type=Path, required=True)
    c.add_argument('--receipt', type=Path)
    v = subs.add_parser('verify')
    v.add_argument('--archive', type=Path, required=True)
    v.add_argument('--expected-sha256')
    v.add_argument('--receipt', type=Path)
    r = subs.add_parser('remote-step')
    r.add_argument('--root', type=Path, required=True)
    r.add_argument('--backup-id', required=True)
    r.add_argument('--local-sha256', required=True)
    r.add_argument('--incoming', type=Path, required=True)
    r.add_argument('--expected-frozen-manifest')
    args = parser.parse_args()
    if args.command == 'create':
        result = create(args.root, args.out)
    elif args.command == 'verify':
        result = verify(args.archive, args.expected_sha256)
    else:
        result = remote_step(args.root, args.backup_id, args.local_sha256, args.incoming, args.expected_frozen_manifest)
    if getattr(args, 'receipt', None):
        dump_json(args.receipt, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
