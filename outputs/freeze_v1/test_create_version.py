"""Read-only pre-freeze verification on a synthetic receipt, without labels."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from .create_version import (POOL_ID, PRIVATE_SHA, PUBLIC_SHA, SOURCE_FILES,
                             create_version)


class FreezeCheckOnlyTest(unittest.TestCase):
    def test_check_only_reports_final_model_and_does_not_create_freeze(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            root = Path(tmp)
            public_dir, private_dir = root / "public", root / "private"
            public_dir.mkdir()
            private_dir.mkdir()
            for name in SOURCE_FILES:
                source = root / name
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_text("synthetic source\n", encoding="utf-8")
            (root / "freeze_v1" / "protocol_decisions.md").write_text(
                "synthetic protocol\n", encoding="utf-8")
            (private_dir / "private_receipt.json").write_text(json.dumps({
                "private_labels_sha256": PRIVATE_SHA,
                "class_counts": {"hit_support": 116, "nonhit_support": 115},
                "excluded_unknown_count": 1,
                "chembl_release": "ChEMBL_37",
            }), encoding="utf-8")
            verification = {"pool_id": POOL_ID, "public_sha256": PUBLIC_SHA,
                            "candidate_count": 231}
            with patch("freeze_v1.create_version.verify_prepared", return_value=verification):
                result = create_version(root, public_dir, private_dir, check_only=True)
            self.assertEqual(result["status"], "ready_to_freeze_no_files_written")
            self.assertEqual(result["candidate_count"], 231)
            self.assertEqual(result["campaign_spec"]["model"], "glm-5.3-flash")
            self.assertEqual(result["campaign_spec"]["thinking"], "enabled")
            self.assertEqual(result["campaign_spec"]["reasoning_effort"], "low")
            self.assertEqual(result["campaign_spec"]["max_output_tokens"], 1024)
            self.assertFalse(result["campaign_spec"]["do_sample"])
            self.assertFalse((root / "frozen_dyrk3_v1").exists())


if __name__ == "__main__":
    unittest.main()
