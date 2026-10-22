"""Synthetic, label-independent D3-0 regression of the existing kNN code."""

import unittest

from rdkit import DataStructs

from campaign_v0.numerical_tools import NumericalTools


class ColdStartTest(unittest.TestCase):
    def test_all_nonhits_rank_by_inverse_similarity_weight(self):
        candidates = ([{"compound_key": f"observed_{i}", "standardized_smiles": "CCCCCC"}
                       for i in range(10)] + [
                           {"compound_key": "same", "standardized_smiles": "CCCCCC"},
                           {"compound_key": "near", "standardized_smiles": "CCCCCO"},
                           {"compound_key": "far", "standardized_smiles": "c1ccccc1"},
                       ])
        tools = NumericalTools(candidates)
        state = {"revealed": [{"compound_key": f"observed_{i}", "outcome": 0}
                              for i in range(10)],
                 "next_batch_size": 1, "remaining_budget": 40}
        scores = tools.score_knn(state)
        weights = {}
        for key in ("same", "near", "far"):
            weights[key] = sum(sorted((DataStructs.TanimotoSimilarity(
                tools.fingerprints[key], tools.fingerprints[f"observed_{i}"]) ** 2
                for i in range(10)), reverse=True)[:5])
            self.assertAlmostEqual(scores[key], (2 / 12) / (2 + weights[key]))
        self.assertEqual(len(set(weights.values())), 3)
        ordered = sorted(weights, key=weights.get)
        self.assertEqual(ordered, sorted(scores, key=scores.get, reverse=True))
        self.assertEqual(tools.select_batch(state, policy="knn_greedy", seed=0,
                                            round_number=1), [ordered[0]])


if __name__ == "__main__":
    unittest.main()
