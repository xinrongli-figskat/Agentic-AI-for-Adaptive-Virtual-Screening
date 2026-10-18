"""Check that batch curation preserves conflicts and private outcome provenance."""
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from assay_audit_v0 import audit_assay as audit
from curate_chembl37_batch import audit_one


class BatchCurationTest(unittest.TestCase):
    def test_conflicting_measurements_do_not_become_hit_or_nonhit(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            output = Path(directory) / "CHEMBL12"
            db = sqlite3.connect(":memory:")
            db.row_factory = sqlite3.Row
            db.executescript("""
                CREATE TABLE assays (assay_id INTEGER, chembl_id TEXT);
                CREATE TABLE activities (activity_id INTEGER, assay_id INTEGER, molregno INTEGER,
                    standard_type TEXT, standard_relation TEXT, standard_value REAL,
                    standard_units TEXT, potential_duplicate INTEGER,
                    data_validity_comment TEXT, activity_comment TEXT, doc_id INTEGER);
                CREATE TABLE molecule_dictionary (molregno INTEGER, chembl_id TEXT);
                CREATE TABLE compound_structures (molregno INTEGER, canonical_smiles TEXT);
                CREATE TABLE docs (doc_id INTEGER, chembl_id TEXT);
                INSERT INTO assays VALUES (1, 'CHEMBL12');
                INSERT INTO docs VALUES (1, 'CHEMBL99');
                INSERT INTO molecule_dictionary VALUES (1, 'CHEMBL1'), (2, 'CHEMBL2'), (3, 'CHEMBL3');
                INSERT INTO compound_structures VALUES (1, 'CCO'), (2, 'CCC'), (3, 'CCN');
                INSERT INTO activities VALUES
                    (1, 1, 1, 'IC50', '=', 500, 'nM', 0, NULL, NULL, 1),
                    (2, 1, 2, 'IC50', '=', 3000, 'nM', 0, NULL, NULL, 1),
                    (3, 1, 3, 'IC50', '=', 700, 'nM', 0, NULL, NULL, 1),
                    (4, 1, 3, 'IC50', '=', 2000, 'nM', 0, NULL, NULL, 1);
            """)
            base = Path(__file__).parent
            config = json.loads((base / "candidate_discovery_v0/criteria_v0.json").read_text())
            policy = json.loads((base / "assay_audit_v0/audit_policy_v0.json").read_text())
            protocol = json.loads((base / "curation_agent_v3/protocol.json").read_text())
            meta = {"assay_id": "CHEMBL12", "target_id": "CHEMBL5", "source_tier": "research_article",
                    "raw_ic50_records": 4, "confidence_score": 9}
            result = audit_one(db, meta, config, policy, protocol, audit.load_helper(), output, 1500)
            self.assertEqual(result["budget"]["provisional_pool_size"], 2)
            self.assertEqual(result["budget"]["hit_support_count"], 1)
            self.assertEqual(result["budget"]["nonhit_support_count"], 1)
            self.assertEqual(result["class_states_all_standardized_identities"]["threshold_disagreement"], 1)
            self.assertFalse(result["campaign_ready"])
            hashes = json.loads((output / "file_hashes.json").read_text())
            for name, expected in hashes.items():
                self.assertEqual(hashlib.sha256((output / name).read_bytes()).hexdigest(), expected)


if __name__ == "__main__":
    unittest.main()
