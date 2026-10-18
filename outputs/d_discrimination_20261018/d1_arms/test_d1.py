"""Tests for the D1 label-blind structural reference."""
import unittest

from run_d1 import select_structure_batch, structure_run


class StructurePriorTests(unittest.TestCase):
    def test_oracle_outcomes_cannot_change_selection(self):
        candidates = [{"compound_key": f"c{i:03d}", "standardized_smiles": "CCO"}
                      for i in range(60)]
        descriptor_rows = [{"compound_key": row["compound_key"],
                            "mean_tanimoto_k5": (i % 7) / 7}
                           for i, row in enumerate(candidates)]
        labels = {row["compound_key"]: int(i % 3 == 0)
                  for i, row in enumerate(candidates)}
        for seed in (0, 1, 19):
            original = structure_run(candidates, labels, descriptor_rows, seed)
            inverted = structure_run(candidates, {k: 1 - v for k, v in labels.items()},
                                     descriptor_rows, seed)
            self.assertEqual(original, inverted)
            self.assertEqual([len(batch) for batch in original], [10] * 5)
            self.assertEqual(len({key for batch in original for key in batch}), 50)

    def test_tie_rule_is_deterministic_without_outcomes(self):
        scores = {f"c{i:03d}": 0.5 for i in range(30)}
        chosen = select_structure_batch(scores, set(), 7, 2, 10)
        self.assertEqual(chosen, select_structure_batch(scores, set(), 7, 2, 10))
        self.assertEqual(len(set(chosen)), 10)


if __name__ == "__main__":
    unittest.main()
