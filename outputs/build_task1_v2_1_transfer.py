"""Validate and package the independent reason-interface continuation fix."""
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
from curation_agent_v2_1.engine import read,save,sha,signature
from curation_agent_v2_1.run import source_hashes,environment
from install_task1_v2_1 import install,MANIFEST,digest


def main():
    out=ROOT/'outputs';package=out/'curation_agent_v2_1'
    validation=out/'task1_v2_1_validation';validation.mkdir(exist_ok=False)
    reference=read(package/'legacy_v2_reference.json')
    if any(sha(out/'curation_agent_v2'/k)!=v for k,v in reference['code_sha256'].items()):
        raise ValueError('Original v2 source was changed')
    v1=read(ROOT/'.sync_audit/task1_v2_development/v1_source_hashes_before.json')
    if any(sha(ROOT/k)!=v for k,v in v1.items()):raise ValueError('Original v1 source was changed')
    scientific=['engine.py','source_holds.json','vendor/audit.py','vendor/audit_policy.json',
        'vendor/discovery.py','vendor/discovery_criteria.json']
    if any(sha(package/k)!=sha(out/'curation_agent_v2'/k) for k in scientific):
        raise ValueError('Scientific tool/hold implementation changed')
    if read(package/'protocol.json')!={**reference['protocol'],'version':'task1_agent_v2.1','decision_interface':'single_top_level_reason_v1'}:
        raise ValueError('Scientific protocol or budgets changed')
    syntax=0
    for path in [*package.rglob('*.py'),out/'install_task1_v2_1.py']:
        ast.parse(path.read_text(encoding='utf-8'),feature_version=(3,10));syntax+=1
    env=dict(os.environ);env['PYTHONPATH']=str(out)+os.pathsep+env.get('PYTHONPATH','')
    env['TMP']=env['TEMP']=str(ROOT/'.cache/task1-v2-tests');env['PYTHONIOENCODING']='utf-8'
    tests=subprocess.run([sys.executable,'-B','-m','unittest','-v','curation_agent_v2_1.test_agent',
        'curation_agent_v2_1.test_continuation'],cwd=ROOT,env=env,capture_output=True,text=True,encoding='utf-8')
    (validation/'unittest.log').write_text(tests.stdout+tests.stderr,encoding='utf-8')
    if tests.returncode:raise RuntimeError(tests.stderr)
    receipt={'status':'V21_LOCAL_INTERFACE_AND_CONTINUATION_TESTS_PASSED','offline_tests':22,
        'python_310_syntax_files_including_installer':syntax,'environment':environment(),
        'v1_source_files_unchanged':len(v1),'v2_source_files_unchanged':len(reference['code_sha256']),
        'scientific_implementations_byte_identical':scientific,'scientific_protocol_and_budgets_unchanged':True,
        'source_hashes':source_hashes(),'test_log_sha256':sha(validation/'unittest.log'),
        'new_real_glm_requests':0,'remote_continuation_executed':False,'campaign_ready':False,
        'limitation':'Migration exercised on synthetic paused v2 runs with real version snapshots; real remote parent must pass offline verification after upload.'}
    save(validation/'validation_receipt.json',receipt)
    stage=out/'task1_v2_1_delivery';stage.mkdir(exist_ok=False)
    shutil.copyfile(out/'32_task1_v2_1_reason_interface_fix.md',stage/'32_task1_v2_1_reason_interface_fix.md')
    shutil.copyfile(out/'install_task1_v2_1.py',stage/'install_task1_v2_1.py')
    shutil.copytree(validation,stage/'validation')
    payload={p.relative_to(out).as_posix():p.read_bytes() for folder in (package,stage)
             for p in sorted(folder.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    manifest={'schema':'task1_v21_transfer_v1','files':{k:digest(v) for k,v in payload.items()},
        'software_version':'task1_agent_v2.1','purpose':'Interface-only versioned continuation; no scientific gate or budget changes'}
    archive=out/'task1_curation_agent_v2_1_transfer.zip'
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as bundle:
        for name,data in sorted(payload.items()):bundle.writestr(name,data)
        bundle.writestr(MANIFEST,json.dumps(manifest,ensure_ascii=False,indent=2).encode('utf-8'))
    with tempfile.TemporaryDirectory(dir=ROOT/'.cache/task1-v2-tests') as temporary:
        home=Path(temporary)
        for old in ('curation_agent_v1','curation_agent_v2'):
            (home/old).mkdir();(home/old/'sentinel.txt').write_text('Preserve old version',encoding='utf-8')
        first=install(archive,home);again=install(archive,home)
        if first['old_files_replaced'] or again['status']!='already_installed_expected_files_verified':
            raise ValueError('New-directory install verification failed')
        for old in ('curation_agent_v1','curation_agent_v2'):
            if (home/old/'sentinel.txt').read_text(encoding='utf-8')!='Preserve old version':raise ValueError('Old version overwritten')
        cli=subprocess.run([sys.executable,'-B','-m','curation_agent_v2_1.run','--help'],cwd=home,
            env=env,capture_output=True,text=True,encoding='utf-8')
        if cli.returncode or 'continue-v2' not in cli.stdout:raise ValueError('Installed CLI failed: '+cli.stderr)
        target=home/'curation_agent_v2_1/__init__.py';target.write_text('Keep this edit',encoding='utf-8')
        try:install(archive,home)
        except ValueError:pass
        else:raise ValueError('Modified installed files were overwritten')
        if target.read_text(encoding='utf-8')!='Keep this edit':raise ValueError('Modified file changed')
    result={'status':'V21_DELIVERY_PACKAGE_CHECKS_PASSED','archive':archive.name,'files':len(payload),
        'archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive),
        'installer_sha256':sha(out/'install_task1_v2_1.py'),'offline_tests':22,'old_files_replaced':0,
        'new_real_glm_requests':0,'remote_installation_confirmed':False}
    save(out/'task1_v2_1_package_validation.json',result)
    (out/'task1_curation_agent_v2_1_transfer.sha256').write_text(sha(archive)+'  '+archive.name+'\n'+
        sha(out/'install_task1_v2_1.py')+'  install_task1_v2_1.py\n',encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
