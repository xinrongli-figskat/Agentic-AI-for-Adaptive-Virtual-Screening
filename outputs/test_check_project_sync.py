"""Synthetic checks: no real credentials, scientific outcomes or remote access."""
import tempfile
import unittest
import zipfile
from pathlib import Path

from check_project_sync import scan, classify, compare


class SyncInventoryTests(unittest.TestCase):
    def test_mappings_backups_conflicts_and_missing(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            local, remote = root / 'local', root / 'remote'
            (local / 'outputs').mkdir(parents=True)
            (remote / 'docs').mkdir(parents=True)
            for name, content in [('01_note.md','same'), ('different.py','new'),
                                  ('backup.py','backup'), ('elsewhere.py','elsewhere'),
                                  ('missing.py','missing')]:
                (local / 'outputs' / name).write_text(content)
            (remote / 'docs/01_note.md').write_text('same')
            (remote / 'different.py').write_text('old')
            (remote / 'moved.py').write_text('elsewhere')
            with zipfile.ZipFile(remote / 'transfer.zip', 'w') as archive:
                archive.writestr('backup.py', 'backup')
                archive.writestr('different.py', 'new')
            before = {str(p): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            left, right = scan(local,'local'), scan(remote,'remote')
            statuses = {r['path']:r['status'] for r in classify(left,right)}
            self.assertEqual(statuses, {
                'outputs/01_note.md':'SAME_AT_EXPECTED_PATH',
                'outputs/different.py':'DIFFERENT_AT_EXPECTED_PATH',
                'outputs/backup.py':'ARCHIVED_COPY_ONLY',
                'outputs/elsewhere.py':'SAME_CONTENT_ELSEWHERE',
                'outputs/missing.py':'NO_MATCH_IN_SCANNED_SCOPE'})
            compare(left,right,root / 'report')
            self.assertTrue((root/'report/comparison.md').is_file())
            self.assertEqual(before, {p:p2.read_bytes() for p in before for p2 in [Path(p)]})

    def test_scope_secrets_archive_paths_and_size_limit(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ['.venv','.cache','.sync_audit']:
                (root/name).mkdir()
                (root/name/'skip.txt').write_text('excluded')
            (root/'.env').write_text('fake credential')
            (root/'id_ed25519_lab').write_text('fake credential')
            (root/'large.dat').write_bytes(b'x'*1025)
            with zipfile.ZipFile(root/'test.zip','w') as archive:
                archive.writestr('../escape.txt','unsafe')
                archive.writestr('.env','fake')
                archive.writestr('readme.md','safe')
            manifest = scan(root,'local',max_file_bytes=1024)
            self.assertEqual({p['path'] for p in manifest['files']},{'large.dat','test.zip'})
            self.assertEqual(manifest['files'][0]['status'],'too_large_not_hashed')
            self.assertEqual([p['member'] for p in manifest['archive_members']],['readme.md'])
            self.assertTrue(any(p['kind']=='unsafe_archive_member' for p in manifest['issues']))
            self.assertFalse((root.parent/'escape.txt').exists())
            self.assertEqual(manifest['skipped']['credential_files'],2)


if __name__ == '__main__':
    unittest.main()
