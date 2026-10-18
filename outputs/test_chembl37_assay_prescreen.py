"""Behavioral checks for the assay-level numeric prescreen."""
from __future__ import annotations

import sqlite3
from pathlib import Path
import tempfile
import unittest

from enumerate_chembl37_assays import record_signal, run, summarize_assay


class SignalTest(unittest.TestCase):
    def row(self, relation="=", value=1000, **changes):
        row = {"molregno": 1, "molecule_chembl_id": "CHEMBL1", "canonical_smiles": "CCO",
               "data_validity_comment": None, "potential_duplicate": 0,
               "standard_units": "nM", "standard_value": value,
               "standard_relation": relation, "activity_comment": None}
        row.update(changes)
        return row

    def test_threshold_and_censor_direction(self):
        expected = [("=", 1000, "hit_support"), ("=", 1000.1, "nonhit_support"),
                    ("<", 1000, "hit_support"), ("<=", 1000, "hit_support"),
                    (">", 1000, "nonhit_support"), (">=", 1000, "unknown"),
                    (">", 900, "unknown"), ("<", 1100, "unknown")]
        for relation, value, outcome in expected:
            with self.subTest(relation=relation, value=value):
                self.assertEqual(record_signal(self.row(relation, value))[0], outcome)

    def test_unknown_is_not_negative(self):
        for changes in ({"standard_value": None}, {"potential_duplicate": 1},
                        {"canonical_smiles": None}, {"data_validity_comment": "Potential author error"}):
            self.assertEqual(record_signal(self.row(**changes))[0], "unknown")

    def test_conflicting_measurements_remove_compound_from_both_classes(self):
        db = sqlite3.connect(":memory:")
        db.row_factory = sqlite3.Row
        db.executescript("""
            CREATE TABLE activities(activity_id INTEGER, assay_id INTEGER, molregno INTEGER,
                standard_type TEXT, standard_relation TEXT, standard_value REAL,
                standard_units TEXT, potential_duplicate INTEGER, data_validity_comment TEXT,
                activity_comment TEXT);
            CREATE TABLE molecule_dictionary(molregno INTEGER, chembl_id TEXT);
            CREATE TABLE compound_structures(molregno INTEGER, canonical_smiles TEXT);
            INSERT INTO molecule_dictionary VALUES(1, 'CHEMBL1'),(2, 'CHEMBL2'),(3, 'CHEMBL3');
            INSERT INTO compound_structures VALUES(1, 'CCO'),(2, 'CCN'),(3, 'CCC');
            INSERT INTO activities VALUES
                (1, 10, 1, 'IC50', '=', 500, 'nM', 0, NULL, NULL),
                (2, 10, 1, 'IC50', '=', 2000, 'nM', 0, NULL, NULL),
                (3, 10, 2, 'IC50', '<', 1000, 'nM', 0, NULL, NULL),
                (4, 10, 3, 'IC50', '>', 1000, 'nM', 0, NULL, NULL);
        """)
        meta = {"assay_id": 10, "assay_chembl_id": "CHEMBL10", "target_chembl_id": "CHEMBL20",
                "target_name": "Synthetic", "target_organism": "Homo sapiens", "description": "Synthetic",
                "relationship_type": "D", "confidence_score": 9, "assay_src_id": 1,
                "doc_type": "PUBLICATION", "document_chembl_id": "CHEMBL30", "document_title": "Synthetic",
                "doi": "10.synthetic/test", "pubmed_id": None, "patent_id": None, "raw_ic50_records": 4}
        report = summarize_assay(db, meta)
        self.assertEqual((report["hit_support_ids"], report["nonhit_support_ids"],
                          report["conflict_ids"], report["supported_ids"]), (1, 1, 1, 2))
        self.assertEqual(report["source_tier"], "research_article")
        self.assertFalse(report["campaign_ready"])
        db.close()

    def test_full_sql_prescreen_keeps_only_metadata_and_numeric_pass(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as temporary:
            database = Path(temporary) / "synthetic.sqlite"
            db = sqlite3.connect(database)
            db.executescript("""
                CREATE TABLE activities(activity_id INTEGER, assay_id INTEGER, molregno INTEGER,
                    standard_type TEXT, standard_relation TEXT, standard_value REAL,
                    standard_units TEXT, potential_duplicate INTEGER, data_validity_comment TEXT,
                    activity_comment TEXT);
                CREATE TABLE assays(assay_id INTEGER, chembl_id TEXT, description TEXT,
                    assay_type TEXT, confidence_score INTEGER, relationship_type TEXT,
                    src_id INTEGER, tid INTEGER, doc_id INTEGER);
                CREATE TABLE target_dictionary(tid INTEGER, chembl_id TEXT, pref_name TEXT,
                    organism TEXT, target_type TEXT);
                CREATE TABLE docs(doc_id INTEGER, chembl_id TEXT, doc_type TEXT, doi TEXT,
                    pubmed_id INTEGER, patent_id TEXT, title TEXT, src_id INTEGER);
                CREATE TABLE molecule_dictionary(molregno INTEGER, chembl_id TEXT);
                CREATE TABLE compound_structures(molregno INTEGER, canonical_smiles TEXT);
                INSERT INTO assays VALUES
                    (1,'CHEMBL_A','Measured inhibition','B',9,'D',1,11,21),
                    (2,'CHEMBL_B','Low confidence','B',8,'D',1,11,21);
                INSERT INTO target_dictionary VALUES(11,'CHEMBL_T','Synthetic target','Homo sapiens','SINGLE PROTEIN');
                INSERT INTO docs VALUES(21,'CHEMBL_D','PUBLICATION','10.synthetic/test',NULL,NULL,'Synthetic',1);
            """)
            molecules = [(number, f"CHEMBL{number}") for number in range(1, 261)]
            db.executemany("INSERT INTO molecule_dictionary VALUES(?,?)", molecules)
            db.executemany("INSERT INTO compound_structures VALUES(?,?)", [(n, "CCO") for n, _ in molecules])
            for assay_id in (1, 2):
                rows = []
                for mol in range(1, 261):
                    value = 500 if mol <= 40 else 2500
                    rows.append((assay_id * 1000 + mol, assay_id, mol, "IC50", "=", value, "nM", 0, None, None))
                db.executemany("INSERT INTO activities VALUES(?,?,?,?,?,?,?,?,?,?)", rows)
            db.commit()
            db.close()
            sql = Path(__file__).with_name("chembl37_assay_prescreen.sql")
            report = run(database, sql)
            self.assertEqual(report["funnel"]["raw_assays_ge_250"], 2)
            self.assertEqual(report["funnel"]["single_protein"], 1)
            self.assertEqual(report["funnel"]["numeric_prescreen_pass"], 1)
            self.assertEqual(report["assays"][0]["assay_id"], "CHEMBL_A")
            self.assertEqual((report["assays"][0]["hit_support_ids"],
                              report["assays"][0]["nonhit_support_ids"]), (40, 220))


if __name__ == "__main__":
    unittest.main()
