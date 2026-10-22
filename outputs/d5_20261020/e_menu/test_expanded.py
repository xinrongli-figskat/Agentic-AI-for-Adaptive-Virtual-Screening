"""Synthetic-only D5 menu tests; no real oracle labels are opened."""

import unittest

from outputs.d5_20261020.e_menu.expanded_tools import MENU, ExpandedTools
from outputs.d5_20261020.e_menu.run_extended import Controller


CANDIDATES = [
    {"compound_key": str(i), "standardized_smiles": smiles}
    for i, smiles in enumerate((
        "CCO", "CCN", "CCC", "CCCO", "CCCN", "c1ccccc1", "c1ccncc1",
        "O=C(O)CC", "CCCl", "CCBr", "CC(=O)O", "CC(C)O", "CNC", "COC",
        "CC(C)N", "c1ccc(O)cc1", "c1ccc(N)cc1", "CCCC", "CCOC", "CCS",
    ))
]


def state(outcomes):
    revealed = [{"compound_key": str(i), "outcome": outcome}
                for i, outcome in enumerate(outcomes)]
    return {"candidate_pool": CANDIDATES, "revealed": revealed,
            "queried_count": len(revealed), "remaining_budget": 50 - len(revealed),
            "next_batch_size": 10, "next_round": 1}


class MenuTests(unittest.TestCase):
    def test_old_menu_exactly_delegates(self):
        for rep in ("bit", "count"):
            tools = ExpandedTools(CANDIDATES, rep)
            for policy in MENU[:3]:
                current = state([0, 1, 0, 0, 1])
                self.assertEqual(tools.select(current, policy, 3, 1),
                                 tools.legacy.select_batch(current, policy=policy,
                                                           seed=3, round_number=1))

    def test_every_new_item_selects_distinct_unqueried(self):
        for rep in ("bit", "count"):
            tools = ExpandedTools(CANDIDATES, rep)
            for outcomes in ([0, 0, 0, 0, 0], [0, 1, 0, 0, 1]):
                current = state(outcomes)
                for policy in MENU[3:]:
                    with self.subTest(rep=rep, outcomes=outcomes, policy=policy):
                        chosen = tools.select(current, policy, 0, 1)
                        self.assertEqual(len(chosen), 10)
                        self.assertEqual(len(set(chosen)), 10)
                        self.assertTrue(set(chosen).isdisjoint(
                            {row["compound_key"] for row in current["revealed"]}))

    def test_persistent_commitment_spends_slots_without_extra_model_call(self):
        class Stub:
            last_usage = {"total_tokens": 1}
            last_request_id = "synthetic"
            last_attempt_log = [{"http_status": 200}]

            def __init__(self):
                self.calls = 0

            def __call__(self, summary):
                self.calls += 1
                return '{"policy":"persistent_random_until_first_hit","reason":"synthetic test"}'

        stub = Stub()
        controller = Controller("glm_extended", 0, client=stub)
        first, first_call = controller.choose(state([0, 0, 0, 0, 0]))
        self.assertEqual(first["policy"], "persistent_random_until_first_hit")
        self.assertIsNotNone(first_call)
        second, second_call = controller.choose(state([0, 0, 0, 0, 0]))
        self.assertTrue(second["automatic_commitment"])
        self.assertIsNone(second_call)
        self.assertEqual(stub.calls, 1)
        controller.choose(state([0, 1, 0, 0, 0]))
        self.assertEqual(stub.calls, 2)


if __name__ == "__main__":
    unittest.main()
