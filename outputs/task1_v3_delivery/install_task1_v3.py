"""Verify a Task1 v2 transfer and install new directories without replacing old files."""
import argparse
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import shutil
import stat
import tempfile
import zipfile

MANIFEST='TASK1_V3_TRANSFER_MANIFEST.json'
ROOTS={'curation_agent_v3','task1_v3_delivery'}


def digest(data):return hashlib.sha256(data).hexdigest()


def install(archive,root):
    root=Path(root).resolve()
    if not root.is_dir():raise ValueError('Project directory must already exist')
    with zipfile.ZipFile(archive) as bundle:
        names=bundle.namelist()
        if len(names)!=len(set(names)):raise ValueError('Duplicate archive entries')
        manifest=json.loads(bundle.read(MANIFEST))
        if manifest.get('schema')!='task1_v3_transfer_v1':raise ValueError('Wrong manifest schema')
        expected=manifest['files']
        if set(names)!={MANIFEST,*expected}:raise ValueError('Archive/manifest file list mismatch')
        payload={}
        for name,wanted in expected.items():
            path=PurePosixPath(name);mode=bundle.getinfo(name).external_attr>>16
            if (path.is_absolute() or path.as_posix()!=name or '\\' in name or ':' in name or
                any(part in ('..','.') for part in path.parts) or len(path.parts)<2 or path.parts[0] not in ROOTS or
                stat.S_ISLNK(mode) or bundle.getinfo(name).is_dir()):
                raise ValueError('Unsafe or unexpected archive path: '+name)
            data=bundle.read(name)
            if digest(data)!=wanted:raise ValueError('File hash mismatch: '+name)
            payload[name]=data
        installed=[(root/name).exists() or (root/name).is_symlink() for name in ROOTS]
        if any(installed):
            if (all(installed) and not any((root/name).is_symlink() for name in ROOTS) and
                all((root/name).is_file() and not (root/name).is_symlink() and
                digest((root/name).read_bytes())==wanted for name,wanted in expected.items())):
                return {'status':'already_installed_expected_files_verified','files':len(expected),'old_files_replaced':0}
            raise ValueError('A destination already exists or differs; no files replaced. Keep it and use a new reviewed version.')
        staging=Path(tempfile.mkdtemp(prefix='.task1-v3-install-',dir=root)).resolve()
        staging.relative_to(root)
        try:
            for name,data in payload.items():
                target=staging/name;target.resolve().relative_to(staging)
                target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            for name in sorted(ROOTS):
                os.rename(staging/name,root/name)
        finally:
            if staging.is_dir():
                staging.relative_to(root)
                shutil.rmtree(staging)
    return {'status':'installed_verified_new_directories','files':len(expected),
        'directories':sorted(ROOTS),'old_files_replaced':0}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--archive',required=True,type=Path)
    parser.add_argument('--root',required=True,type=Path);args=parser.parse_args()
    print(json.dumps(install(args.archive,args.root),indent=2))


if __name__=='__main__':main()
