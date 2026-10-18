"""Small synthetic integrity and unknown-label check; no ChEMBL data."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from inspect_assay_edges import inspect, write_json


class EdgeInspectionTest(unittest.TestCase):
    def test_unknown_retained_and_manifest_checked(self):
        # Sandbox-safe temporary fixture: Python cleans up only a child of this folder.
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as temporary:
            run = Path(temporary)
            write_json(run / "run_metadata.json", {"completed": True})
            write_json(run / "summary.json", {
                "target_chembl_id": "CHEMBL4575", "assay_chembl_id": "CHEMBL5363961",
                "standardized_identity_count": 2, "selected_assay_records": 2,
            })
            write_json(run / "audit_policy.json", {
                "target_chembl_id": "CHEMBL4575", "assay_chembl_id": "CHEMBL5363961",
                "diversity_policy": {"fingerprint": "Morgan bit fingerprint", "radius": 2,
                                     "bits": 2048, "include_chirality": True},
            })
            write_json(run / "compound_audit.json", [
                {"compound_key": "a", "standardized_smiles": "CCO", "activity_ids": [1],
                 "molecule_chembl_ids": ["CHEMBL1"], "provisional_state": "hit_support",
                 "usable_for_prototype_review": True},
                {"compound_key": "b", "standardized_smiles": "CCN", "activity_ids": [2],
                 "molecule_chembl_ids": ["CHEMBL2"], "provisional_state": "unknown",
                 "decision_reason": "no_eligible_threshold_support", "record_reason_counts": {"missing_value": 1},
                 "review_flags": [], "usable_for_prototype_review": False},
            ])
            write_json(run / "records_audit.json", [
                {"activity_id": 1},
                {"activity_id": 2, "molecule_chembl_id": "CHEMBL2", "standard_relation": ">",
                 "standard_value": None, "standard_units": "nM", "record_signal": "unknown",
                 "record_reason": "missing_value"},
            ])
            write_json(run / "OUTPUT_SHA256_MANIFEST.json", {
                p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in run.iterdir()
            })
            result = inspect(run)
            self.assertEqual(result["usable_compounds"], 1)
            self.assertEqual(result["unresolved_compounds"][0]["source_records"][0]["record_reason"], "missing_value")
            self.assertEqual(result["identical_bit_fingerprint_group_count"], 0)
            (run / "records_audit.json").write_text("{}", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "hash differs"):
                inspect(run)


if __name__ == "__main__":
    unittest.main()
