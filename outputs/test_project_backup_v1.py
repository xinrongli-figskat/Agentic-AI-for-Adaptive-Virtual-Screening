import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from project_backup_v1 import MANIFEST, create, verify, remote_step, check_frozen, digest_file


class BackupTests(unittest.TestCase):
    def test_round_trip_private_data_and_exclusions(self):
        with tempfile.TemporaryDirectory() as temp:
            parent = Path(temp)
            root = parent/'project'
            (root/'data/curation_private/frozen').mkdir(parents=True)
            (root/'data/curation_private/frozen/labels.json').write_text('{"private":true}')
            (root/'script.py').write_text('print("sample")')
            for directory in ['.venv','.cache','.sync_audit','data/curation_private/backups']:
                (root/directory).mkdir(parents=True,exist_ok=True)
                (root/directory/'skip.txt').write_text('skip')
            (root/'id_ed25519_lab').write_text('fake-key')
            (root/'.env').write_text('fake-secret')
            original = {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}
            backup = parent/'saved.zip'
            receipt = create(root,backup)
            self.assertEqual(receipt['file_count'],2)
            self.assertEqual(verify(backup,receipt['archive_sha256'])['file_count'],2)
            with zipfile.ZipFile(backup) as z:
                self.assertEqual(set(z.namelist()),{'script.py','data/curation_private/frozen/labels.json',MANIFEST})
            self.assertEqual(original,{p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()})
            with self.assertRaises(FileExistsError):
                create(root,backup)
            with self.assertRaisesRegex(ValueError,'Transport'):
                verify(backup,'0'*64)

    def test_manifest_detects_changed_archive_member(self):
        with tempfile.TemporaryDirectory() as temp:
            parent=Path(temp)
            root=parent/'project'
            root.mkdir()
            (root/'result.json').write_text('original')
            create(root,parent/'original.zip')
            with zipfile.ZipFile(parent/'original.zip') as source, zipfile.ZipFile(parent/'changed.zip','w') as target:
                for name in source.namelist():
                    target.writestr(name,b'modified' if name=='result.json' else source.read(name))
            with self.assertRaisesRegex(ValueError,'content mismatch'):
                verify(parent/'changed.zip')

    def test_remote_backup_does_not_nest_backups_and_can_resume(self):
        with tempfile.TemporaryDirectory() as temp:
            parent=Path(temp)
            local=parent/'local'
            remote=parent/'remote'
            local.mkdir()
            remote.mkdir()
            (local/'review.md').write_text('saved review')
            (remote/'frozen.json').write_text('frozen evidence')
            received=parent/'upload.zip'
            receipt=create(local,received)
            result=remote_step(remote,'backup_20261015_1234abcd',receipt['archive_sha256'],received)
            self.assertEqual(result['remote_created']['file_count'],1)
            folder=Path(result['remote_directory'])
            self.assertEqual((remote/'frozen.json').read_text(),'frozen evidence')
            first_hash=result['remote_created']['archive_sha256']
            repeated=remote_step(remote,'backup_20261015_1234abcd',receipt['archive_sha256'],received)
            self.assertEqual(repeated['remote_created']['archive_sha256'],first_hash)
            self.assertTrue((folder/'local_received_receipt.json').exists())

    def test_preservation_checks_anchor_data_code_and_thirty_runs(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp).resolve()
            frozen=root/'data/curation_private/frozen_dyrk3_v1'
            public=root/'data/campaign_public/pool'
            private=root/'data/curation_private/pool'
            run_root=root/'data/curation_private/runs_dyrk3_v1'
            for folder in [frozen/'source_snapshot',public,private,run_root]:
                folder.mkdir(parents=True,exist_ok=True)
            (public/'candidates.jsonl').write_text('public')
            (private/'oracle_labels.jsonl').write_text('synthetic')
            (root/'example.py').write_text('original code')
            (frozen/'source_snapshot/example.py').write_text('original code')
            (frozen/'protocol_decisions.md').write_text('fixed protocol')
            manifest={'status':'frozen_dyrk3_v1','public_dir':str(public),'private_dir':str(private),
                      'run_root':str(run_root),'data_sha256':{
                          'public_candidates':digest_file(public/'candidates.jsonl'),
                          'private_labels':digest_file(private/'oracle_labels.jsonl')},
                      'source_sha256':{str(root/'example.py'):digest_file(root/'example.py')},
                      'protocol_decisions_sha256':digest_file(frozen/'protocol_decisions.md'),
                      'campaign_spec':{'representations':['bit','count'],'seeds':list(range(5))}}
            (frozen/'manifest.json').write_text(json.dumps(manifest))
            expected=digest_file(frozen/'manifest.json')
            for controller in ['llm','fixed','random']:
                for rep in ['bit','count']:
                    for seed in range(5):
                        folder=run_root/f'{controller}_{rep}_seed{seed}'
                        folder.mkdir()
                        (folder/'run.json').write_text(json.dumps({'status':'complete',
                            'frozen_manifest_sha256':expected,'result':{'queried_count':50,
                            'trajectory':[{'selection':list(range(50))}]}}))
            self.assertEqual(check_frozen(root,expected)['completed_campaigns'],30)
            (root/'example.py').write_text('changed code')
            with self.assertRaisesRegex(ValueError,'Frozen source/data/protocol differs'):
                check_frozen(root,expected)


if __name__=='__main__':
    unittest.main()
