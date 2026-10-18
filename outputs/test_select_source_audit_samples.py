"""Check fixed source sample selection, including conflict exclusion."""
import unittest

from select_source_audit_samples import select


class SourceSelectionTest(unittest.TestCase):
    def test_distinct_balanced_sample_excludes_conflicted_molecule(self):
        rows = []
        for number in range(1, 8):
            rows.append(self.row(number, number, 500))
        for number in range(8, 15):
            rows.append(self.row(number, number, 5000))
        rows.append(self.row(15, 1, 600))  # Repeat of a hit molecule.
        rows.append(self.row(16, 15, 400))
        rows.append(self.row(17, 15, 4000))  # Conflicting source molecule.
        result = select(rows)
        self.assertTrue(result["main_sample_complete"])
        self.assertEqual(len(result["main_sample"]["hit_support"]), 6)
        self.assertEqual(len(result["main_sample"]["nonhit_support"]), 6)
        self.assertEqual(len({r["molecule_chembl_id"] for r in result["main_sample"]["hit_support"]}), 6)
        self.assertNotIn("CHEMBL15", {r["molecule_chembl_id"] for group in result["main_sample"].values() for r in group})
        self.assertEqual(result["conflicting_source_ids"][0]["activity_ids"], [16, 17])

    @staticmethod
    def row(activity, molecule, value):
        return {"activity_id": activity, "molregno": molecule,
                "molecule_chembl_id": f"CHEMBL{molecule}", "canonical_smiles": "CCO",
                "standard_relation": "=", "standard_value": value, "standard_units": "nM",
                "potential_duplicate": 0, "data_validity_comment": None,
                "activity_comment": None}


if __name__ == "__main__":
    unittest.main()
