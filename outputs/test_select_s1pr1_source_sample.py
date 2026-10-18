"""Focused checks for the frozen source-ID selection and bound logic."""
import unittest

from select_s1pr1_source_sample import sample_records, signal


CONFIG = {
    "standard_type": "IC50", "assay_type_for_record_signals": "B",
    "validity_comments_allowed": [None, "", "Manually validated"],
    "exclude_flagged_potential_duplicates_from_signals": True,
    "hit_threshold_nM": "1000",
}


def row(number, molecule, value, relation="="):
    return {"activity_id": number, "assay_chembl_id": "CHEMBL5734042",
            "target_chembl_id": "CHEMBL4333", "molecule_chembl_id": molecule,
            "canonical_smiles": "CCO", "standard_type": "IC50", "assay_type": "B",
            "standard_value": str(value), "standard_units": "nM", "standard_relation": relation,
            "data_validity_comment": None, "potential_duplicate": 0}


class SampleTests(unittest.TestCase):
    def test_censoring_and_boundary(self):
        self.assertEqual(signal(row(1, "A", 1000, "<"), CONFIG)[0], "hit_support")
        self.assertEqual(signal(row(2, "B", 1000, ">"), CONFIG)[0], "nonhit_support")
        self.assertEqual(signal(row(3, "C", 1000, ">="), CONFIG)[0], "unknown")
        self.assertEqual(signal(row(4, "D", 1000, "="), CONFIG)[0], "hit_support")

    def test_conflict_excluded_and_molecules_are_unique(self):
        rows = [row(1, "A", 500), row(2, "A", 1500), row(3, "B", 600),
                row(4, "B", 650), row(5, "C", 1700)]
        expected = {"hit_support_ids": 1, "nonhit_support_ids": 1,
                    "supported_ids": 2, "threshold_disagreement_ids": 1,
                    "unknown_evidence_ids": 0}
        result = sample_records(rows, CONFIG, expected)
        self.assertEqual(result["conflict_molecule_ids"], ["A"])
        self.assertEqual({x["molecule_chembl_id"] for x in result["selected"]}, {"B", "C"})
        self.assertEqual(len(result["selected"][0]["same_molecule_records"]), 2)
        self.assertEqual(len(result["boundary_records"]), 2)

    def test_profile_mismatch_stops_selection(self):
        with self.assertRaisesRegex(ValueError, "Recomputed"):
            sample_records([row(1, "A", 500)], CONFIG,
                           {"hit_support_ids": 0, "nonhit_support_ids": 0,
                            "supported_ids": 0, "threshold_disagreement_ids": 0,
                            "unknown_evidence_ids": 0})


if __name__ == "__main__":
    unittest.main()
