"""Build and verify a new-directory-only delivery. Run from the local project."""
import ast
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'outputs'))
from curation_agent_v2.engine import read,save,sha
from curation_agent_v2.run import source_hashes
from install_task1_v2 import install,MANIFEST,digest


def write_zip(path,payload,manifest):
    with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED) as bundle:
        for name,data in sorted(payload.items()):bundle.writestr(name,data)
        bundle.writestr(MANIFEST,json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf-8'))


def main():
    out=ROOT/'outputs';validation=read(out/'task1_v2_validation/validation_receipt.json')
    if validation['source_hashes']!=source_hashes():raise ValueError('Source changed after validation')
    stage=out/'task1_v2_delivery';stage.mkdir(exist_ok=False)
    for name in ['31_task1_v2_implementation_and_criteria.md','30_p300_p2x_source_alignment_decisions.md','install_task1_v2.py']:
        shutil.copyfile(out/name,stage/name)
    shutil.copytree(out/'task1_v2_validation',stage/'validation')
    payload={}
    for folder in [out/'curation_agent_v2',stage]:
        for path in sorted(folder.rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts:
                payload[path.relative_to(out).as_posix()]=path.read_bytes()
    manifest={'schema':'task1_v2_transfer_v1','files':{name:digest(data) for name,data in payload.items()},
        'status':'tested_software_not_new_benchmark','real_glm_search_started':False,'campaign_ready':False,
        'old_versions_modified':False,'qualification':'post-exploration review tiers, not blind preregistration'}
    archive=out/'task1_curation_agent_v2_transfer.zip';write_zip(archive,payload,manifest)
    ast.parse((out/'install_task1_v2.py').read_text(encoding='utf-8'),feature_version=(3,10))
    temp_root=ROOT/'.cache/task1-v2-installer-tests';temp_root.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=temp_root) as temporary:
        home=Path(temporary);installed=home/'project';installed.mkdir()
        old=installed/'curation_agent_v1';old.mkdir();(old/'sentinel.txt').write_text('Old result must remain',encoding='utf-8')
        before=sha(old/'sentinel.txt')
        first=install(archive,installed);second=install(archive,installed)
        if first['old_files_replaced'] or second['status']!='already_installed_expected_files_verified':
            raise ValueError('Install replay check failed')
        if sha(old/'sentinel.txt')!=before:raise ValueError('Old result overwritten')
        env=dict(os.environ);env['PYTHONPATH']=str(ROOT/'.cache/audit-deps');env['PYTHONIOENCODING']='utf-8'
        cli=subprocess.run([sys.executable,'-B','-m','curation_agent_v2.run','--help'],cwd=installed,env=env,
                           capture_output=True,text=True,encoding='utf-8')
        if cli.returncode or 'prescreen' not in cli.stdout:raise ValueError('Installed CLI failed: '+cli.stderr)
        changed=installed/'curation_agent_v2/__init__.py';changed.write_text('Keep edited file',encoding='utf-8')
        try:install(archive,installed)
        except ValueError:pass
        else:raise ValueError('Installer overwrote a modified existing version')
        if changed.read_text(encoding='utf-8')!='Keep edited file':raise ValueError('Edited file was changed')
        broken=dict(payload);one=next(iter(broken));broken[one]+=b'\ncorrupt'
        corrupt=home/'corrupt.zip';write_zip(corrupt,broken,manifest);empty=home/'empty';empty.mkdir()
        try:install(corrupt,empty)
        except ValueError:pass
        else:raise ValueError('Corrupt file was installed')
        if list(empty.iterdir()):raise ValueError('Corrupt package left installed files')
        hostile={'../escape.txt':b'x'};traversal=home/'traversal.zip'
        write_zip(traversal,hostile,{'schema':'task1_v2_transfer_v1','files':{'../escape.txt':digest(b'x')}})
        try:install(traversal,empty)
        except ValueError:pass
        else:raise ValueError('Traversal archive was accepted')
    receipt={'status':'PACKAGE_AND_INSTALLER_CHECKS_PASSED','archive':archive.name,'file_count':len(payload),
        'archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive),'installer_sha256':sha(out/'install_task1_v2.py'),
        'checks':['per-file verification','repeat install verifies without replacement','edited destination refuses overwrite',
                  'old result sentinel unchanged','corrupt payload rejected before writes','path traversal rejected','installed CLI imports'],
        'remote_installation_confirmed':False,'new_real_glm_search_started':False}
    save(out/'task1_v2_package_validation.json',receipt)
    (out/'task1_curation_agent_v2_transfer.sha256').write_text(
        sha(archive)+'  '+archive.name+'\n'+sha(out/'install_task1_v2.py')+'  install_task1_v2.py\n',encoding='utf-8')
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':main()
