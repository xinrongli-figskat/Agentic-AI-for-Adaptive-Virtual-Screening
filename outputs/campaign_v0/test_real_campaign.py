"""Offline persistence checks; no private data and no API calls."""

import tempfile
import unittest
import json
from pathlib import Path
from unittest.mock import patch

from oracle_boundary_v0.oracle_boundary import read_json

from .real_campaign import atomic_json, controller_for, run_one
from .glm_api import GLMAPIError


class RealCampaignOfflineTest(unittest.TestCase):
    def test_atomic_checkpoint_round_trip(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            path = Path(tmp) / "run.json"
            atomic_json(path, {"status": "in_progress", "trajectory": [{"round": 0}]})
            self.assertEqual(read_json(path)["trajectory"], [{"round": 0}])
            atomic_json(path, {"status": "complete", "trajectory": []})
            self.assertEqual(read_json(path)["status"], "complete")
            self.assertFalse(path.with_suffix(".tmp").exists())

    def test_reference_controllers_need_no_api_key(self):
        self.assertEqual(controller_for("fixed", "glm-4.7-flash").name,
                         "prescribed_knn_greedy")
        self.assertEqual(controller_for("random", "glm-4.7-flash").name,
                         "uniform_random_reference")

    def test_fixed_launcher_writes_private_checkpoint_and_is_idempotent(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            root = Path(tmp)
            public, private, frozen = (root / name for name in ("public", "private", "frozen"))
            for path in (public, private, frozen):
                path.mkdir()
            (frozen / "manifest.json").write_text("{}", encoding="utf-8")
            candidates = [{"compound_key": f"synthetic_{i:03d}",
                           "standardized_smiles": "C" * (i + 1)} for i in range(60)]
            labels = [{"compound_key": row["compound_key"], "outcome": int(i % 3 == 0)}
                      for i, row in enumerate(candidates)]
            (public / "candidates.jsonl").write_text("".join(json.dumps(x) + "\n" for x in candidates),
                                                      encoding="utf-8")
            (private / "oracle_labels.jsonl").write_text("".join(json.dumps(x) + "\n" for x in labels),
                                                         encoding="utf-8")
            manifest = {"public_dir": str(public), "private_dir": str(private),
                        "run_root": str(root / "private_runs"),
                        "campaign_spec": {"seeds": [0], "representations": ["bit"],
                                          "model": "glm-4.7-flash", "total_budget": 50,
                                          "initialization_queries": 10, "batch_size": 10}}
            with patch("campaign_v0.real_campaign.load_frozen_manifest", return_value=manifest):
                result = run_one(frozen, controller_name="fixed", seed=0, representation="bit")
                repeated = run_one(frozen, controller_name="fixed", seed=0, representation="bit")
            self.assertEqual(result["queried_count"], 50)
            self.assertEqual(repeated["hits_at_budget"], result["hits_at_budget"])
            run_file = root / "private_runs" / "fixed_bit_seed0" / "run.json"
            self.assertEqual(read_json(run_file)["status"], "complete")
            self.assertFalse((public / "run.json").exists())

    def test_overloaded_llm_stops_before_feedback_and_keeps_failure_history(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
            root = Path(tmp)
            public, private, frozen = (root / name for name in ("public", "private", "frozen"))
            for path in (public, private, frozen):
                path.mkdir()
            (frozen / "manifest.json").write_text("{}", encoding="utf-8")
            candidates = [{"compound_key": f"synthetic_{i:03d}",
                           "standardized_smiles": "C" * (i + 1)} for i in range(60)]
            labels = [{"compound_key": row["compound_key"], "outcome": int(i % 3 == 0)}
                      for i, row in enumerate(candidates)]
            (public / "candidates.jsonl").write_text(
                "".join(json.dumps(x) + "\n" for x in candidates), encoding="utf-8")
            (private / "oracle_labels.jsonl").write_text(
                "".join(json.dumps(x) + "\n" for x in labels), encoding="utf-8")
            manifest = {"public_dir": str(public), "private_dir": str(private),
                        "run_root": str(root / "private_runs"),
                        "campaign_spec": {"seeds": [0], "representations": ["bit"],
                                          "model": "glm-4.7-flash", "total_budget": 50,
                                          "initialization_queries": 10, "batch_size": 10}}

            class OverloadedController:
                def choose(self, *_):
                    error = GLMAPIError(429, "1305")
                    error.attempt_log = [{"http_status": 429, "business_code": "1305"}] * 3
                    error.decision_seconds = 20.0
                    raise error

            with patch("campaign_v0.real_campaign.load_frozen_manifest", return_value=manifest), \
                 patch("campaign_v0.real_campaign.controller_for", return_value=OverloadedController()):
                with self.assertRaises(GLMAPIError):
                    run_one(frozen, controller_name="llm", seed=0, representation="bit")
            run_dir = root / "private_runs" / "llm_bit_seed0"
            checkpoint = read_json(run_dir / "run.json")
            self.assertEqual(checkpoint["status"], "in_progress")
            self.assertEqual(len(checkpoint["trajectory"]), 1)
            self.assertEqual(len(checkpoint["trajectory"][0]["observations"]), 10)
            failures = read_json(run_dir / "failure_events.json")
            self.assertEqual(len(failures), 1)
            self.assertEqual(len(failures[0]["public_api_diagnostic"]["attempt_log"]), 3)


if __name__ == "__main__":
    unittest.main()
