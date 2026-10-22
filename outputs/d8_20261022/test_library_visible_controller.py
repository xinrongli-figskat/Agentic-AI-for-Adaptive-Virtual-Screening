import unittest

from library_visible_controller import (
    LibraryVisibleController, make_library_visible_payload, payload_text,
)


MENU = ["greedy", "diverse", "random", "persistent_random_until_first_hit",
        "diverse_random_coldstart"]


class LibraryVisiblePayloadTests(unittest.TestCase):
    def setUp(self):
        self.candidates = [
            {"compound_key": "cmp_a", "standardized_smiles": "CCO"},
            {"compound_key": "cmp_b", "standardized_smiles": "CCN"},
            {"compound_key": "cmp_c", "standardized_smiles": "CCC"},
        ]
        self.revealed = [{"compound_key": "cmp_a", "outcome": 1}]
        self.scores = {"cmp_a": 0.8, "cmp_b": 0.4, "cmp_c": 0.2}

    def test_all_candidate_keys_structures_and_scores_are_visible(self):
        payload = make_library_visible_payload(self.candidates, self.revealed,
                                               self.scores, MENU)
        rows = payload["candidate_library"]
        self.assertEqual({r["compound_key"] for r in rows},
                         {r["compound_key"] for r in self.candidates})
        self.assertEqual({r["standardized_smiles"] for r in rows},
                         {r["standardized_smiles"] for r in self.candidates})
        self.assertTrue(all("predicted_active_probability" in r for r in rows))

    def test_unqueried_synthetic_results_do_not_change_payload(self):
        hidden_a = {"cmp_b": 0, "cmp_c": 1}
        hidden_b = {"cmp_b": 1, "cmp_c": 0}
        payload_a = make_library_visible_payload(self.candidates, self.revealed,
                                                 self.scores, MENU)
        payload_b = make_library_visible_payload(self.candidates, self.revealed,
                                                 self.scores, MENU)
        self.assertNotEqual(hidden_a, hidden_b)
        self.assertEqual(payload_text(payload_a), payload_text(payload_b))
        client_a = lambda payload: {"policy": "greedy", "reason": "Use current scores."}
        client_b = lambda payload: {"policy": "greedy", "reason": "Use current scores."}
        scores = lambda _candidates, _revealed: self.scores
        state = {"revealed": self.revealed}
        controller_a = LibraryVisibleController(client_a, "synthetic", self.candidates, scores)
        controller_b = LibraryVisibleController(client_b, "synthetic", self.candidates, scores)
        self.assertEqual(controller_a.choose(state, MENU), controller_b.choose(state, MENU))

    def test_serialized_payload_has_no_per_candidate_outcome_field(self):
        payload = make_library_visible_payload(self.candidates, self.revealed,
                                               self.scores, MENU)
        text = payload_text(payload)
        self.assertNotIn('"outcome"', text)
        self.assertEqual(payload["already_measured_active_keys"], ["cmp_a"])
        self.assertEqual(payload["already_measured_inactive_keys"], [])
        library_keys = {"compound_key", "standardized_smiles",
                         "predicted_active_probability"}
        self.assertTrue(all(set(row) == library_keys
                            for row in payload["candidate_library"]))


if __name__ == "__main__":
    unittest.main()
