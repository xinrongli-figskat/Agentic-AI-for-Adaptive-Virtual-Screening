"""Synthetic-only pre-freeze export and integrity check."""

import json
import tempfile
import unittest
from pathlib import Path

from prepare_pool import export, json_bytes, sha256_bytes, verify_audit


class PreparePoolTest(unittest.TestCase):
    def test_public_private_split_and_tamper_detection(self):
        # The temporary fixture stays inside the verified project workspace.
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as temporary:
            base = Path(temporary)
            run = base / "audit"
            run.mkdir()
            compounds, records = [], []
            for index in range(232):
                smiles = "C" * (index + 1)
                key = "cmp_" + sha256_bytes(smiles.encode("utf-8"))
                unknown = index == 231
                state = "unknown" if unknown else "hit_support" if index < 116 else "nonhit_support"
                molecule_id = "CHEMBL1802358" if unknown else "CHEMBL" + str(1000000 + index)
                compounds.append({
                    "compound_key": key, "standardized_smiles": smiles, "activity_ids": [index + 1],
                    "molecule_chembl_ids": [molecule_id], "document_chembl_ids": ["CHEMBL5360622"],
                    "provisional_state": state, "review_flags": [],
                    "usable_for_prototype_review": not unknown,
                    "decision_reason": "no_eligible_threshold_support" if unknown else "unanimous_eligible_threshold_support",
                    "exact_min_nM": "230" if unknown else "100" if index < 116 else "2000",
                    "exact_max_nM": "230" if unknown else "100" if index < 116 else "2000",
                })
                records.append({"activity_id": index + 1, "assay_chembl_id": "CHEMBL5363961",
                                "record_signal": state, "potential_duplicate": 1 if unknown else 0})
            source = {
                "run_metadata.json": {"completed": True, "chembl_db_version": "ChEMBL_37", "rdkit_version": "test"},
                "summary.json": {"target_chembl_id": "CHEMBL4575", "assay_chembl_id": "CHEMBL5363961",
                                 "selected_assay_records": 232, "standardized_identity_count": 232,
                                 "usable_support_counts": {"hit_support": 116, "nonhit_support": 115}},
                "audit_policy.json": {"target_chembl_id": "CHEMBL4575", "assay_chembl_id": "CHEMBL5363961",
                                      "hit_threshold_nM": "1000"},
                "discovery_criteria_snapshot.json": {"hit_threshold_nM": "1000",
                                                     "exclude_flagged_potential_duplicates_from_signals": True},
                "compound_audit.json": compounds,
                "records_audit.json": records,
            }
            for name, obj in source.items():
                (run / name).write_bytes(json_bytes(obj))
            (run / "OUTPUT_SHA256_MANIFEST.json").write_bytes(json_bytes({
                name: sha256_bytes((run / name).read_bytes()) for name in source
            }))
            qualification, protocol = base / "qualification.md", base / "protocol.md"
            qualification.write_text("Feasibility decision before campaign\n", encoding="utf-8")
            protocol.write_text("Draft protocol\n", encoding="utf-8")
            result = export(run, qualification, protocol, base / "public", base / "private")
            self.assertEqual(result["compound_count"], 231)
            public = Path(result["public_dir"])
            private = Path(result["private_dir"])
            self.assertTrue((private / "oracle_labels.jsonl").exists())
            self.assertFalse((public / "oracle_labels.jsonl").exists())
            self.assertNotIn("outcome", (public / "candidates.jsonl").read_text(encoding="utf-8"))
            self.assertEqual(len((public / "candidates.jsonl").read_text(encoding="utf-8").splitlines()), 231)
            self.assertEqual(len((private / "oracle_labels.jsonl").read_text(encoding="utf-8").splitlines()), 231)
            self.assertEqual(json.loads((private / "excluded_unknown.json").read_text())[0]["state"], "unknown")
            (run / "summary.json").write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                verify_audit(run)


if __name__ == "__main__":
    unittest.main()
