"""Decision-point mapping and pure trigger tests for D2-1."""
import unittest

from run_d2_rule import AdaptiveV2Controller, policy_v2


def state(hits):
    revealed = []
    for h in hits:
        revealed += [{"outcome": 1}] * h + [{"outcome": 0}] * (10 - h)
    return {"next_round": len(hits), "revealed": revealed}


class DecisionMappingTests(unittest.TestCase):
    def test_four_decision_points(self):
        controller = AdaptiveV2Controller()
        allowed = ("knn_greedy", "knn_diverse", "uniform_random")
        cases = [
            ([2], "knn_greedy"),                 # batch 1: forced
            ([2, 1], "knn_diverse"),             # batch 2: h1 < h0
            ([2, 3, 2], "knn_diverse"),          # batch 3: h2 < mean(h0,h1)
            ([2, 3, 4, 2], "knn_diverse"),       # batch 4: h3 < mean(h0,h1,h2)
        ]
        for hits, expected in cases:
            self.assertEqual(controller.choose(state(hits), allowed)["policy"], expected)
        self.assertEqual([d["upcoming_batch"] for d in controller.decisions], [1, 2, 3, 4])

    def test_strict_inequality_and_fallback(self):
        self.assertEqual(policy_v2([2, 2], 2), "knn_greedy")
        self.assertEqual(policy_v2([1, 3, 2], 3), "knn_greedy")
        self.assertEqual(policy_v2([2, 3, 4, 3], 4), "knn_greedy")
        controller = AdaptiveV2Controller()
        self.assertEqual(controller.choose(state([0]), ("knn_greedy", "uniform_random"))["policy"],
                         "uniform_random")
        self.assertTrue(controller.decisions[0]["cold_start_fallback"])

    def test_reject_wrong_mapping_or_hidden_future(self):
        with self.assertRaises(ValueError):
            policy_v2([2], 3)
        with self.assertRaises(ValueError):
            AdaptiveV2Controller().choose({"next_round": 2, "revealed": [{"outcome": 1}] * 10},
                                          ("knn_greedy", "knn_diverse"))


if __name__ == "__main__":
    unittest.main()
