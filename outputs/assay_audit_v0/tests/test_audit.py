"""Offline scientific edge cases and end-to-end synthetic source verification."""
import contextlib
import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from rdkit import rdBase

ROOT = Path(__file__).resolve().parents[1]
TEST_CACHE = ROOT.parent / ".cache" / "assay-audit-tests"
TEST_CACHE.mkdir(parents=True, exist_ok=True)
spec = importlib.util.spec_from_file_location("assay_audit", ROOT / "audit_assay.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
helper = audit.load_helper()
POLICY = json.loads((ROOT / "audit_policy_v0.json").read_text(encoding="utf-8"))
CONFIG = {"standard_type": "IC50", "assay_type_for_record_signals": "B", "hit_threshold_nM": "1000",
          "validity_comments_allowed": [None, "", "Manually validated"], "exclude_flagged_potential_duplicates_from_signals": True,
          "review_priority_gates": {"molecule_ids_with_class_support": 500, "hit_support_molecule_ids": 30, "nonhit_support_molecule_ids": 100}}


def record(number=1, molecule="M1", smiles="CCO", value="500", relation="=", units="nM", **extra):
    return {"activity_id": number, "molecule_chembl_id": molecule, "canonical_smiles": smiles,
            "target_chembl_id": "CHEMBL4575", "assay_chembl_id": "CHEMBL5363961", "document_chembl_id": "SYNTHETIC_DOC",
            "standard_type": "IC50", "assay_type": "B", "standard_value": value,
            "standard_relation": relation, "standard_units": units, **extra}


def source_fixture(path):
    path.mkdir()
    (path / "raw").mkdir()
    (path / "profiles").mkdir()
    rows = [record(1, "M1", value="100"), record(2, "M2", value="200"), record(3, "M2", "OCC", "300"),
            record(4, "M3", "Oc1ccccc1", "2000"), record(5, "M4", "c1ccccc1"),
            record(6, "M4", "c1ccccc1", "1000", ">"), record(7, "M5", "invalid_smiles"),
            record(8, "M6", "CC.O=C(O)C"), record(9, "M7", "CCN", "300", ">"),
            record(10, "M8", "CC(C)C", activity_comment="inactive"),
            record(11, "M9", "CC(C)O", "2000"), record(12, "M9", "CC(C)O", "3000", ">"),
            record(13, "M10", "[13CH3]CO")]
    raw = json.dumps({"activities": rows, "page_meta": {"total_count": len(rows)}}).encode()
    (path / "raw" / "page.json").write_bytes(raw)
    source = (ROOT / "discovery_helper.py").read_bytes()
    (path / "tool_source.py").write_bytes(source)
    audit.save_json(path / "criteria_snapshot.json", CONFIG)
    audit.save_json(path / "profiles" / "CHEMBL4575.json", helper.profile({"target_chembl_id": "CHEMBL4575"}, rows, len(rows), True, CONFIG))
    audit.save_json(path / "run_metadata.json", {"completed": True, "chembl_db_version": "SYNTHETIC_RELEASE",
        "script_sha256": hashlib.sha256(source).hexdigest(), "requests": [{
            "url": "https://www.ebi.ac.uk/chembl/api/data/activity.json?target_chembl_id=CHEMBL4575&standard_type=IC50&offset=0",
            "raw_file": "raw/page.json", "http_status": 200, "sha256": hashlib.sha256(raw).hexdigest()}]})
    review = path.parent / "source_review.json"
    audit.save_json(review, {"source_release": "SYNTHETIC_RELEASE", "assays": [{"assay_chembl_id": "CHEMBL5363961",
        "target_chembl_id": "CHEMBL4575", "description": "SYNTHETIC TEST DATA ONLY", "confidence_score": 9}]})
    return rows, review, raw


class AuditTests(unittest.TestCase):
    def test_censored_threshold_and_contradictions(self):
        r = lambda rows: audit.reconcile(rows, CONFIG, "1000", helper.record_signal)
        self.assertEqual(r([record(value="1000", relation="=")])["provisional_state"], "hit_support")
        self.assertEqual(r([record(value="1000", relation=">=")])["provisional_state"], "unknown")
        self.assertEqual(r([record(value="1000", relation=">")])["provisional_state"], "nonhit_support")
        self.assertFalse(r([record(value="500"), record(2, value="1000", relation=">")])["usable_for_prototype_review"])
        self.assertIn("censored_bounds_or_exact_values_disagree_needs_review",
                      r([record(value="400", relation=">"), record(2, value="400", relation="<=")])["review_flags"])
        self.assertFalse(r([record(value="2000"), record(2, value="3000", relation=">")])["usable_for_prototype_review"])

    def test_unknown_and_annotation_are_not_negative(self):
        for extra in ({"standard_value": None}, {"potential_duplicate": 1}, {"data_validity_comment": "Potential author error"}):
            row = {**record(), **extra}
            self.assertEqual(audit.reconcile([row], CONFIG, "1000", helper.record_signal)["provisional_state"], "unknown")
        result = audit.reconcile([record(activity_comment="inactive")], CONFIG, "1000", helper.record_signal)
        self.assertEqual(result["provisional_state"], "hit_support")
        self.assertFalse(result["usable_for_prototype_review"])

    def test_units_and_exact_spread_without_averaging(self):
        result = audit.reconcile([record(value="0.5", units="uM"), record(2, value="900")], CONFIG, "1000", helper.record_signal)
        self.assertTrue(result["usable_for_prototype_review"])
        self.assertEqual(result["exact_min_nM"], "500.0")
        self.assertEqual(float(result["exact_fold_range"]), 1.8)
        self.assertNotIn("mean_nM", result)

    def test_salt_stereochemistry_isotopes_and_mixtures(self):
        f = audit.standardize_structure
        self.assertEqual(f("CC[NH3+].[Cl-]")["standardized_smiles"], f("CC[NH3+]")["standardized_smiles"])
        self.assertNotEqual(f("CC[NH3+]")["standardized_smiles"], f("CCN")["standardized_smiles"])
        self.assertNotEqual(f("F[C@H](Cl)Br")["standardized_smiles"], f("F[C@@H](Cl)Br")["standardized_smiles"])
        self.assertNotEqual(f("[13CH3]CO")["standardized_smiles"], f("CCO")["standardized_smiles"])
        self.assertEqual(f("CC.O=C(O)C")["structure_status"], "quarantined")
        self.assertEqual(f("[CH3]")["structure_status"], "quarantined")

    def test_collision_and_source_identity_ambiguity(self):
        rows = [record(1, "M1", "CC[NH3+].[Cl-]", "100"), record(2, "M2", "CC[NH3+]", "2000")]
        _, ids, compounds, _ = audit.audit_records(rows, CONFIG, POLICY, helper)
        self.assertEqual(len(compounds), 1)
        self.assertEqual(compounds[0]["molecule_chembl_ids"], ["M1", "M2"])
        self.assertEqual(compounds[0]["provisional_state"], "threshold_disagreement")
        self.assertFalse(compounds[0]["usable_for_prototype_review"])
        _, ids, compounds, _ = audit.audit_records([record(1), record(2, smiles="CCN")], CONFIG, POLICY, helper)
        self.assertEqual(len(compounds), 0)
        self.assertEqual(ids[0]["structure_reason"], "multiple_structures_for_one_source_id")

    def test_diversity_small_pools_and_scaffolds(self):
        _, _, compounds, _ = audit.audit_records([record(1, "M1", "c1ccccc1"), record(2, "M2", "Oc1ccccc1"),
                                                   record(3, "M3", "CCO", "2000")], CONFIG, POLICY, helper)
        d = audit.diversity(compounds, POLICY)
        self.assertEqual(d["pair_count"], 3)
        self.assertEqual(d["scaffold_count_including_acyclic_bucket"], 2)
        self.assertEqual(d["acyclic_compounds"], 1)
        self.assertAlmostEqual(d["largest_scaffold_fraction"], 2/3)
        self.assertEqual(sum(c["size"] for c in d["clusters"]), 3)
        self.assertEqual(audit.diversity([], POLICY)["compound_count"], 0)
        self.assertIsNone(audit.diversity(compounds[:1], POLICY)["nearest_neighbor_tanimoto_median"])

    def test_budget_includes_initialization_and_checks_pool(self):
        compounds = [{"provisional_state": "hit_support" if i < 116 else "nonhit_support",
                      "usable_for_prototype_review": True} for i in range(231)]
        b = audit.budget_analysis(compounds, POLICY["budget_proposals"])
        p = b["proposals"][0]
        self.assertAlmostEqual(p["random_expected_hits"], 25.1082251082)
        self.assertEqual(p["queries_after_initialization"], 40)
        self.assertEqual(p["feedback_batches_after_initialization"], 4)
        self.assertLess(p["initialization_probability_single_class"], .002)
        self.assertFalse(audit.budget_analysis(compounds[:49], POLICY["budget_proposals"])["proposals"][0]["pool_large_enough"])

    def test_complete_pipeline_preserves_raw_and_outputs_manifest(self):
        with tempfile.TemporaryDirectory(dir=TEST_CACHE) as temp:
            base = Path(temp)
            assert base.resolve().is_relative_to(TEST_CACHE.resolve())
            rows, review, raw = source_fixture(base / "source")
            with rdBase.BlockLogs(), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                code = audit.main(["--discovery-run", str(base / "source"), "--source-review", str(review), "--output-dir", str(base / "results")])
            self.assertEqual(code, 0)
            run = next((base / "results").iterdir())
            summary = json.loads((run / "summary.json").read_text())
            self.assertEqual(summary["quarantined_molecule_ids"], 2)
            self.assertEqual(summary["standardized_identity_count"], 7)
            self.assertEqual(summary["usable_support_counts"], {"hit_support": 2, "nonhit_support": 1})
            self.assertEqual((base / "source" / "raw" / "page.json").read_bytes(), raw)
            self.assertEqual(len(json.loads((run / "records_audit.json").read_text())), len(rows))
            for name, expected in json.loads((run / "OUTPUT_SHA256_MANIFEST.json").read_text()).items():
                self.assertEqual(audit.digest(run / name), expected)

    def test_changed_raw_or_partial_source_fails_closed(self):
        with tempfile.TemporaryDirectory(dir=TEST_CACHE) as temp:
            base = Path(temp)
            assert base.resolve().is_relative_to(TEST_CACHE.resolve())
            source = base / "source"
            source_fixture(source)
            profile_path = source / "profiles" / "CHEMBL4575.json"
            original = profile_path.read_bytes()
            profile = json.loads(original)
            profile["retrieval_complete"] = False
            audit.save_json(profile_path, profile)
            with self.assertRaisesRegex(ValueError, "incomplete"):
                audit.load_evidence(source, "CHEMBL4575", "IC50")
            profile_path.write_bytes(original)
            (source / "raw" / "page.json").write_bytes(b"{}")
            with self.assertRaisesRegex(ValueError, "hash-verified"):
                audit.load_evidence(source, "CHEMBL4575", "IC50")


if __name__ == "__main__":
    unittest.main()
