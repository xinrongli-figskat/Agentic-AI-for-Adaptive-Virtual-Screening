import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from review_task1_v3_archive import extract_new, verified_payloads


class ArchiveBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def archive(self, files, corrupt_manifest=False):
        path = self.root / "fixture.zip"
        manifest = {"format": "task1_v3_closeout_v1", "files": {
            name: ("0" * 64 if corrupt_manifest else hashlib.sha256(data).hexdigest())
            for name, data in files.items()}}
        with zipfile.ZipFile(path, "w") as bundle:
            for name, data in files.items():
                bundle.writestr(name, data)
            bundle.writestr("EXPORT_MANIFEST.json", json.dumps(manifest))
        return path, hashlib.sha256(path.read_bytes()).hexdigest()

    def test_verified_extraction_and_existing_destination_preserved(self):
        archive, wanted = self.archive({"run/state.json": b"{}"})
        payloads, result = verified_payloads(archive, wanted)
        self.assertEqual(result["verified_manifest_files"], 1)
        dest = extract_new(payloads, self.root / "extracted")
        self.assertEqual((dest / "run/state.json").read_bytes(), b"{}")
        with self.assertRaisesRegex(ValueError, "already exists"):
            extract_new(payloads, dest)
        self.assertEqual((dest / "run/state.json").read_bytes(), b"{}")

    def test_traversal_rejected_before_extraction(self):
        archive, wanted = self.archive({"run/../outside.txt": b"escape"})
        with self.assertRaisesRegex(ValueError, "Unsafe archive path"):
            verified_payloads(archive, wanted)
        self.assertFalse((self.root / "outside.txt").exists())

    def test_case_collision_rejected_on_windows(self):
        archive, wanted = self.archive({"run/State.json": b"1", "run/state.json": b"2"})
        with self.assertRaisesRegex(ValueError, "case-colliding"):
            verified_payloads(archive, wanted)

    def test_outer_and_member_hashes_independently_checked(self):
        archive, wanted = self.archive({"run/state.json": b"{}"}, corrupt_manifest=True)
        with self.assertRaisesRegex(ValueError, "Archive SHA256 mismatch"):
            verified_payloads(archive, "0" * 64)
        with self.assertRaisesRegex(ValueError, "Member hash mismatch"):
            verified_payloads(archive, wanted)


if __name__ == "__main__":
    unittest.main()
