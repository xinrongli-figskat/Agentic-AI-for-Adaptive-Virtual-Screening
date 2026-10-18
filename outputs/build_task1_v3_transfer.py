"""Package the tested v3 feedback repair and actual-state replay evidence."""
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
from curation_agent_v3.engine import read,save,sha
from curation_agent_v3.run import source_hashes,environment
from curation_agent_v3.integrity import inventory,verify_inputs
from install_task1_v3 import install,MANIFEST,digest


def main():
    out=ROOT/'outputs';package=out/'curation_agent_v3'
    reference=read(package/'parent_v21_reference.json')
    if any(sha(out/'curation_agent_v2_1'/k)!=v for k,v in reference['code_sha256'].items()):raise ValueError('Old v2.1 code changed')
    ref2=read(out/'curation_agent_v2_1/legacy_v2_reference.json')
    if any(sha(out/'curation_agent_v2'/k)!=v for k,v in ref2['code_sha256'].items()):raise ValueError('Old v2 code changed')
    closed=out/'results/task1_v21_closed_20261015/run';state=read(closed/'state.json');verify_inputs(closed,state)
    manifest=read(out/'results/task1_v21_closed_20261015/EXPORT_MANIFEST.json')['files']
    expected={k.removeprefix('run/'):v for k,v in manifest.items() if k.startswith('run/')}
    if inventory(closed)!=expected:raise ValueError('Closed input tree changed')
    for name in ['engine.py','source_holds.json','vendor/audit.py','vendor/audit_policy.json','vendor/discovery.py','vendor/discovery_criteria.json']:
        if sha(package/name)!=sha(out/'curation_agent_v2_1'/name):raise ValueError('Numerical tool/source hold changed')
    syntax=0
    for path in [*package.rglob('*.py'),out/'install_task1_v3.py',out/'replay_task1_feedback_v3.py']:
        ast.parse(path.read_text(encoding='utf-8'),feature_version=(3,10));syntax+=1
    replay=read(out/'task1_v3_replay_release_validation/summary.json')
    if replay['saved_requests_replayed']!=40 or replay['new_direct_confidence_visible']!=11 or replay['new_list_ids_visible']!=20:
        raise ValueError('Replay checks missing')
    validation=out/'task1_v3_validation';validation.mkdir(exist_ok=False)
    test_receipt=read(out/'task1_v3_final_checks/tests.json')
    if test_receipt['source_hashes']!=source_hashes() or test_receipt['exit_code']!=0:raise ValueError('Code changed after tests')
    receipt={'status':'V3_TESTED_CODE_AND_ACTUAL_CONTEXT_REPLAY_VALIDATED',
        'unit_tests':{'passed':27,'elapsed_seconds':12.561,'log_sha256':sha(out/'task1_v3_final_checks/unittest.log')},
        'python_310_syntax_files_including_delivery_helpers':syntax,'environment':environment(),
        'old_v2_and_v21_code_unchanged':True,'closed_input_files_unchanged':len(expected),
        'source_hashes':source_hashes(),'actual_replay':replay,'new_real_glm_requests':0,
        'remote_installation_confirmed':False,'new_discovery_success_measured':False}
    save(validation/'validation_receipt.json',receipt)
    shutil.copyfile(out/'task1_v3_replay_release_validation/comparison.csv',validation/'comparison.csv')
    shutil.copyfile(out/'task1_v3_final_checks/unittest.log',validation/'unittest.log')
    stage=out/'task1_v3_delivery';stage.mkdir(exist_ok=False)
    for name in ['35_task1_v3_real_replay_and_feedback_fix.md','install_task1_v3.py','replay_task1_feedback_v3.py']:
        shutil.copyfile(out/name,stage/name)
    shutil.copytree(validation,stage/'validation')
    payload={p.relative_to(out).as_posix():p.read_bytes() for folder in (package,stage) for p in sorted(folder.rglob('*'))
             if p.is_file() and '__pycache__' not in p.parts}
    archive=out/'task1_curation_agent_v3_transfer.zip'
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as bundle:
        for name,data in sorted(payload.items()):bundle.writestr(name,data)
        bundle.writestr(MANIFEST,json.dumps({'schema':'task1_v3_transfer_v1','files':{k:digest(v) for k,v in payload.items()},
            'status':'offline-tested-software-no-live-v3-search','scientific_thresholds_changed':False},ensure_ascii=False,indent=2).encode('utf-8'))
    with tempfile.TemporaryDirectory(dir=ROOT/'.cache/task1-v2-tests') as temporary:
        home=Path(temporary);(home/'curation_agent_v2_1').mkdir()
        (home/'curation_agent_v2_1/sentinel.txt').write_text('Preserve old version',encoding='utf-8')
        installed=install(archive,home);again=install(archive,home)
        if installed['old_files_replaced'] or again['status']!='already_installed_expected_files_verified':raise ValueError('Installer failed')
        if (home/'curation_agent_v2_1/sentinel.txt').read_text(encoding='utf-8')!='Preserve old version':raise ValueError('Old directory overwritten')
        env=dict(os.environ);env['PYTHONPATH']=str(ROOT/'.cache/audit-deps');env['PYTHONIOENCODING']='utf-8'
        cli=subprocess.run([sys.executable,'-B','-m','curation_agent_v3.run','--help'],cwd=home,env=env,
            capture_output=True,text=True,encoding='utf-8')
        if cli.returncode or 'prepare-revision' not in cli.stdout:raise ValueError('Installed CLI failed: '+cli.stderr)
    result={'status':'V3_PACKAGE_INSTALLATION_CHECKS_PASSED','archive':archive.name,'files':len(payload),
        'bytes':archive.stat().st_size,'archive_sha256':sha(archive),'installer_sha256':sha(out/'install_task1_v3.py'),
        'tests_passed':27,'actual_historical_contexts_replayed':40,'old_files_replaced':0,'new_real_glm_requests':0}
    save(out/'task1_v3_package_validation.json',result)
    (out/'task1_curation_agent_v3_transfer.sha256').write_text(sha(archive)+'  '+archive.name+'\n'+sha(out/'install_task1_v3.py')+'  install_task1_v3.py\n',encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
