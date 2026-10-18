"""Offline checks for v4 closeout's budget accounting and immutable archive."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from closeout_task1_v4 import closeout, digest, save
from curation_agent_v4.run import inventory
from verify_task1_v4_archive import verify


class CloseoutV4Tests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.root = self.base / "run"
        (self.root / "llm").mkdir(parents=True)
        (self.root / "raw").mkdir()
        save(self.root / "raw" / "source.json", {"activities": []})
        old = {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12}
        new = {"prompt_tokens": 20, "completion_tokens": 3, "total_tokens": 23}
        save(self.root / "llm" / "0001.json", {"status": "valid_decision", "usage": old})
        save(self.root / "llm" / "0002.json", {"status": "valid_decision", "usage": new})
        ledger = {"inherited_llm_attempts": 1, "inherited_http_requests": 1,
                  "inherited_usage": old}
        save(self.root / "v4_experiment.json", ledger)
        self.state = {
            "protocol": {"version": "task1_agent_v4.0", "maximum_llm_attempts": 2,
                         "maximum_http_requests": 10},
            "status": "paused_at_step_limit", "pending_action": None, "shortlist": [],
            "llm_attempts": 2, "requests": [{"http_status": 200}, {"http_status": 200}],
            "usage": {key: old[key] + new[key] for key in old},
            "v4_experiment": {"ledger_sha256": digest(self.root / "v4_experiment.json"),
                              "inherited_llm_attempts": 1, "inherited_http_requests": 1},
            "events": [{"kind": "tool_action", "llm_attempt": 2,
                        "decision": {"action": "inspect_assay"}, "status": "success"}],
            "assays": {"CHEMBL5734042": {"summary": {"target_id": "CHEMBL4333"},
                                           "metadata": "E001", "decision": None}},
            "profiles": {"CHEMBL4333": {"top_assays_in_window": [
                {"assay_chembl_id": "CHEMBL5734042", "hit_support_ids": 52,
                 "nonhit_support_ids": 242, "supported_ids": 294}]}},
        }
        save(self.root / "state.json", self.state)
        self.loader = patch("closeout_task1_v4.load_v4_engine", return_value=None)
        self.verifier = patch("closeout_task1_v4.verify_inputs", return_value=([], None))
        self.loader.start()
        self.verifier.start()
        self.addCleanup(self.loader.stop)
        self.addCleanup(self.verifier.stop)

    def test_archive_checks_hashes_and_preserves_run(self):
        before = inventory(self.root)
        result = closeout(self.root, self.base / "reviews")
        self.assertEqual(inventory(self.root), before)
        self.assertEqual(result["summary"]["effective_closure_reason"], "llm_budget_exhausted")
        self.assertEqual(result["summary"]["new_v4_llm_attempts"], 1)
        self.assertEqual(result["summary"]["new_v4_returned_usage"]["total_tokens"], 23)
        self.assertEqual(result["summary"]["pending_assays"][0]["assay_id"], "CHEMBL5734042")
        archive = Path(result["archive"])
        self.assertEqual(digest(archive), result["archive_sha256"])
        self.assertTrue(verify(archive, result["archive_sha256"])["verified"])
        with self.assertRaisesRegex(ValueError, "Whole-archive"):
            verify(archive, "0" * 64)
        with zipfile.ZipFile(archive) as bundle:
            manifest = json.loads(bundle.read("EXPORT_MANIFEST.json"))
            for name, expected in manifest["files"].items():
                self.assertEqual(hashlib.sha256(bundle.read(name)).hexdigest(), expected)

    def test_check_only_makes_no_output(self):
        before = inventory(self.root)
        receipt = closeout(self.root, self.base / "reviews", check_only=True)
        self.assertEqual(receipt["status"], "ready_to_archive_no_files_written")
        self.assertFalse((self.base / "reviews").exists())
        self.assertEqual(inventory(self.root), before)

    def test_usage_or_pending_decision_blocks_export(self):
        save(self.root / "llm" / "0002.json", {"usage": {"total_tokens": 999}})
        with self.assertRaisesRegex(ValueError, "usage totals"):
            closeout(self.root, self.base / "reviews")
        self.assertFalse((self.base / "reviews").exists())

    def test_nested_output_and_unfinished_budget_block_export(self):
        with self.assertRaisesRegex(ValueError, "separate sibling"):
            closeout(self.root, self.root / "reviews")
        self.state["protocol"]["maximum_llm_attempts"] = 3
        save(self.root / "state.json", self.state)
        with self.assertRaisesRegex(ValueError, "not finished"):
            closeout(self.root, self.base / "reviews")


if __name__ == "__main__":
    unittest.main()
