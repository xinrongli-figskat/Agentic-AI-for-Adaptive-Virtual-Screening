"""Synthetic label-isolation, budget, and checksum tests."""

import json
import tempfile
import unittest
from pathlib import Path

from oracle_boundary import BatchOracle, QueryRejected, sha256_file, verify_prepared


class OracleBoundaryTest(unittest.TestCase):
    def test_query_interface_hides_unqueried_labels_and_enforces_budget(self):
        candidates = [{"compound_key": "cmp_" + str(i), "standardized_smiles": "C" * (i + 1)} for i in range(231)]
        labels = {row["compound_key"]: i % 2 for i, row in enumerate(candidates)}
        oracle = BatchOracle(candidates, labels, seed=0, total_budget=50, initialization_queries=10, batch_size=10)
        initial = oracle.proposed_initial_ids()
        self.assertNotIn("outcome", json.dumps(oracle.public_state()))
        with self.assertRaises(QueryRejected):
            oracle.query_batch_tool({"compound_keys": initial[:9] + ["not_in_pool"]})
        self.assertEqual(oracle.public_state()["remaining_budget"], 50)
        first = oracle.query_batch_tool({"compound_keys": initial})
        self.assertEqual(first["round"], 0)
        self.assertEqual(first["queried_count"], 10)
        self.assertEqual(len(oracle.public_state()["revealed"]), 10)
        with self.assertRaises(QueryRejected):
            oracle.query_batch_tool({"compound_keys": [initial[0]] * 10})
        self.assertEqual(oracle.public_state()["remaining_budget"], 40)
        remaining = [row["compound_key"] for row in candidates if row["compound_key"] not in initial]
        for round_index in range(4):
            oracle.query_batch_tool({"compound_keys": remaining[round_index * 10:(round_index + 1) * 10]})
        self.assertEqual(oracle.public_state()["remaining_budget"], 0)
        self.assertEqual(len(oracle.public_state()["revealed"]), 50)
        with self.assertRaises(QueryRejected):
            oracle.query_batch_tool({"compound_keys": remaining[40:50]})

    def test_prepared_receipts_are_checked_without_returning_labels(self):
        # Temporary fixture is confined to this project folder.
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as temporary:
            base = Path(temporary)
            public, private = base / "public", base / "private"
            public.mkdir()
            private.mkdir()
            candidates = [{"compound_key": "cmp_" + str(i), "standardized_smiles": "C" * (i + 1)} for i in range(231)]
            labels = [{"compound_key": "cmp_" + str(i), "outcome": i % 2} for i in range(231)]
            (public / "candidates.jsonl").write_text("".join(json.dumps(r) + "\n" for r in candidates), encoding="utf-8")
            (private / "oracle_labels.jsonl").write_text("".join(json.dumps(r) + "\n" for r in labels), encoding="utf-8")
            status = "pre_freeze_export_not_campaign_ready"
            public_sha = sha256_file(public / "candidates.jsonl")
            (public / "public_receipt.json").write_text(json.dumps({
                "status": status, "pool_id": "synthetic", "candidates_sha256": public_sha,
            }), encoding="utf-8")
            (private / "private_receipt.json").write_text(json.dumps({
                "status": status, "pool_id": "synthetic", "public_candidates_sha256": public_sha,
                "private_labels_sha256": sha256_file(private / "oracle_labels.jsonl"),
            }), encoding="utf-8")
            safe = verify_prepared(public, private)
            self.assertEqual(safe["candidate_count"], 231)
            self.assertNotIn("outcome", json.dumps(safe))
            (private / "oracle_labels.jsonl").write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Private label checksum mismatch"):
                verify_prepared(public, private)


if __name__ == "__main__":
    unittest.main()
