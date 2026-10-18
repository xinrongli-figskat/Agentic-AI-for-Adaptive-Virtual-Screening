"""Meaningful offline checks for immutable-input closeout and archive integrity."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from closeout_task1_v3 import closeout, digest, save
from curation_agent_v3.integrity import inventory, signature


class CloseoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "run"
        self.root.mkdir()
        for name in ("llm", "raw", "source_snapshot"):
            (self.root / name).mkdir()
        (self.root / ".writer.lock").write_bytes(b"0")
        (self.root / "source_snapshot/fixture.py").write_text("# fixture\n", encoding="utf-8")
        save(self.root / "catalog.json", [])
        save(self.root / "prior_exposure.json", {})
        save(self.root / "raw/one.json", {"fixture": True})
        old = {"prompt_tokens": 10, "completion_tokens": 2, "total_tokens": 12}
        new = {"prompt_tokens": 20, "completion_tokens": 3, "total_tokens": 23}
        for number, usage in enumerate((old, new), 1):
            save(self.root / "llm" / f"{number:04d}.json", {"status": "valid_decision", "usage": usage})
        save(self.root / "revision.json", {"parent_files_sha256": {}, "inherited_usage": old})
        p = {"maximum_llm_attempts": 2, "maximum_http_requests": 10}
        self.state = {
            "schema": "task1_agent_v3.0", "status": "paused_at_step_limit", "pending_action": None,
            "protocol": p, "protocol_sha256": signature(p),
            "catalog_sha256": digest(self.root / "catalog.json"),
            "prior_exposure_sha256": digest(self.root / "prior_exposure.json"),
            "code_sha256": {"fixture.py": digest(self.root / "source_snapshot/fixture.py")},
            "evidence": {}, "revision": {"ledger_sha256": digest(self.root / "revision.json"),
                "inherited_llm_attempts": 1, "inherited_http_attempts": 1},
            "llm_attempts": 2, "requests": [{"raw_file": "raw/one.json", "sha256": digest(self.root / "raw/one.json")} for _ in range(2)],
            "usage": {key: old[key] + new[key] for key in old},
            "events": [{"kind": "tool_action", "llm_attempt": 2,
                "decision": {"action": "decide_assay"}, "status": "tool_error"}],
            "assays": {}, "shortlist": [],
        }
        save(self.root / "state.json", self.state)

    def test_immutable_run_archive_and_separate_new_usage(self):
        (self.base / "outside_key_fixture.txt").write_text("must stay outside archive", encoding="utf-8")
        before = inventory(self.root)
        result = closeout(self.root, self.base / "reviews")
        self.assertEqual(inventory(self.root), before)
        self.assertEqual(result["summary"]["stored_status"], "paused_at_step_limit")
        self.assertEqual(result["summary"]["effective_closure_reason"], "llm_budget_exhausted")
        self.assertEqual(result["summary"]["revision_returned_usage"]["total_tokens"], 23)
        self.assertEqual(result["summary"]["revision_tool_statuses"], {"tool_error": 1})
        archive = Path(result["archive"])
        self.assertEqual(digest(archive), result["archive_sha256"])
        with zipfile.ZipFile(archive) as bundle:
            manifest = json.loads(bundle.read("EXPORT_MANIFEST.json"))
            self.assertNotIn("run/.writer.lock", bundle.namelist())
            self.assertFalse(any("outside_key_fixture" in name for name in bundle.namelist()))
            for name, wanted in manifest["files"].items():
                self.assertEqual(hashlib.sha256(bundle.read(name)).hexdigest(), wanted)

    def test_bad_receipt_usage_prevents_export(self):
        save(self.root / "llm/0002.json", {"usage": {"total_tokens": 999}})
        before = inventory(self.root)
        with self.assertRaisesRegex(ValueError, "usage totals"):
            closeout(self.root, self.base / "reviews")
        self.assertEqual(inventory(self.root), before)
        self.assertFalse((self.base / "reviews").exists())

    def test_active_run_and_nested_output_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "outside the input run"):
            closeout(self.root, self.root / "reports")
        self.state["llm_attempts"] = 1
        save(self.root / "state.json", self.state)
        with self.assertRaisesRegex(ValueError, "not finished"):
            closeout(self.root, self.base / "reviews")
        self.assertFalse((self.base / "reviews").exists())

    def test_tampered_evidence_prevents_export(self):
        (self.root / "raw/one.json").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Hash mismatch"):
            closeout(self.root, self.base / "reviews")
        self.assertFalse((self.base / "reviews").exists())


if __name__ == "__main__":
    unittest.main()
