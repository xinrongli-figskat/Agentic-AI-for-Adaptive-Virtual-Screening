"""Synthetic-only complete-budget comparison; no real DYRK3 labels."""

import unittest

from .campaign_core import FixedController, RandomController, SyntheticAdaptiveStub, run_campaign, run_synthetic_campaign
from .llm_controller import ToolChoiceLLMController
from .numerical_tools import NumericalTools
from oracle_boundary_v0.oracle_boundary import BatchOracle
import copy
from rdkit import DataStructs


class CampaignTest(unittest.TestCase):
    def test_same_initialization_full_budget_and_feedback_trace(self):
        candidates = [{"compound_key": "synthetic_" + str(i).zfill(3),
                       "standardized_smiles": "C" * (i + 1)} for i in range(80)]
        labels = {row["compound_key"]: int(i % 10 == 0) for i, row in enumerate(candidates)}
        runs = [run_synthetic_campaign(candidates, labels, controller, seed=3)
                for controller in (FixedController(), RandomController(), SyntheticAdaptiveStub())]
        initial = runs[0]["trajectory"][0]["selection"]
        for run in runs:
            self.assertEqual(run["queried_count"], 50)
            self.assertEqual(len(run["trajectory"]), 5)
            self.assertEqual(run["trajectory"][0]["selection"], initial)
            self.assertEqual([len(step["selection"]) for step in run["trajectory"]], [10] * 5)
            queried = [key for step in run["trajectory"] for key in step["selection"]]
            self.assertEqual(len(queried), len(set(queried)))
            self.assertEqual(run["hits_at_budget"], sum(labels[key] for key in queried))
            self.assertEqual(run["hit_recovery_checkpoints"][-1], run["hits_at_budget"])
            for step in run["trajectory"]:
                self.assertEqual({r["compound_key"] for r in step["observations"]}, set(step["selection"]))
        self.assertEqual(runs[0]["controller"], "prescribed_knn_greedy")
        self.assertEqual(runs[1]["controller"], "uniform_random_reference")
        self.assertEqual(runs[2]["controller"], "synthetic_adaptive_stub_not_llm")

    def test_constrained_llm_client_sees_only_public_feedback_and_can_change_policy(self):
        candidates = [{"compound_key": "synthetic_" + str(i).zfill(3),
                       "standardized_smiles": "C" * (i + 1)} for i in range(80)]
        labels = {row["compound_key"]: int(i % 3 == 0) for i, row in enumerate(candidates)}
        seen = []

        def fake_client(summary):
            self.assertNotIn("private_labels", summary)
            self.assertNotIn("candidate_pool", summary)
            self.assertEqual(summary["queried_count"], 10 * len(seen) + 10)
            self.assertEqual(summary["remaining_budget"], 40 - 10 * len(seen))
            seen.append(summary)
            policy = "knn_diverse" if summary["next_round"] % 2 else "knn_greedy"
            return {"policy": policy, "reason": "Synthetic client decision from public round number"}

        controller = ToolChoiceLLMController(fake_client, model_name="fake_client_no_api")
        run = run_synthetic_campaign(candidates, labels, controller, seed=1)
        self.assertEqual(len(seen), 4)
        self.assertEqual(len(controller.decision_log), 4)
        self.assertEqual(seen[0]["numerical_summary"]["unqueried_count"], 70)
        self.assertEqual(len(seen[0]["revealed_observations"]), 10)
        self.assertEqual([step["decision"]["policy"] for step in run["trajectory"][1:]],
                         ["knn_diverse", "knn_greedy", "knn_diverse", "knn_greedy"])
        self.assertEqual(run["queried_count"], 50)
        self.assertEqual(run["hits_at_budget"], sum(labels[key] for step in run["trajectory"]
                                                      for key in step["selection"]))

    def test_invalid_llm_decision_is_rejected_before_query(self):
        controller = ToolChoiceLLMController(lambda _: '{"policy":"read_private","reason":"bad"}',
                                             model_name="fake_client_no_api")
        public_state = {"candidate_pool": [{"compound_key": "x", "standardized_smiles": "CC"},
                                           {"compound_key": "y", "standardized_smiles": "CCC"}],
                        "revealed": [{"compound_key": "x", "outcome": 1}],
                        "queried_count": 1, "remaining_budget": 1, "next_round": 1,
                        "next_batch_size": 1}
        with self.assertRaises(ValueError):
            controller.choose(public_state, ("knn_greedy",))

    def test_inconsistent_state_rejected_before_llm_call(self):
        calls = []
        controller = ToolChoiceLLMController(lambda summary: calls.append(summary),
                                             model_name="fake_client_no_api")
        inconsistent = {"candidate_pool": [{"compound_key": "x", "standardized_smiles": "CC"}],
                        "revealed": [{"compound_key": "x", "outcome": 0}],
                        "queried_count": 1, "remaining_budget": 1,
                        "next_round": 1, "next_batch_size": 1}
        with self.assertRaisesRegex(ValueError, "Inconsistent public campaign state"):
            controller.choose(inconsistent, ("knn_greedy",))
        self.assertEqual(calls, [])

    def test_count_fingerprint_sensitivity_representation(self):
        candidates = [
            {"compound_key": "six", "standardized_smiles": "Cn1ncc2cc(/C=C3\\N=C(NC4CCCCC4)NC3=O)ccc21"},
            {"compound_key": "seven", "standardized_smiles": "Cn1ncc2cc(/C=C3\\N=C(NC4CCCCCC4)NC3=O)ccc21"},
        ]
        bit = NumericalTools(candidates, representation="bit")
        count = NumericalTools(candidates, representation="count")
        self.assertEqual(DataStructs.TanimotoSimilarity(bit.fingerprints["six"],
                                                        bit.fingerprints["seven"]), 1.0)
        self.assertLess(DataStructs.TanimotoSimilarity(count.fingerprints["six"],
                                                       count.fingerprints["seven"]), 1.0)

    def test_checkpoint_replay_resumes_without_new_decisions_for_old_batches(self):
        candidates = [{"compound_key": f"synthetic_{i:03d}",
                       "standardized_smiles": "C" * (i + 1)} for i in range(80)]
        labels = {row["compound_key"]: int(i % 4 == 0) for i, row in enumerate(candidates)}
        saved = []

        def stop_after_first_feedback(trajectory, feature_seconds):
            saved[:] = copy.deepcopy(trajectory)
            if len(trajectory) == 2:
                raise RuntimeError("synthetic interruption")

        original_oracle = BatchOracle(candidates, labels, seed=2, total_budget=50,
                                      initialization_queries=10, batch_size=10)
        with self.assertRaisesRegex(RuntimeError, "synthetic interruption"):
            run_campaign(candidates, original_oracle, FixedController(), seed=2,
                         on_checkpoint=stop_after_first_feedback)
        self.assertEqual(len(saved), 2)
        resumed_oracle = BatchOracle(candidates, labels, seed=2, total_budget=50,
                                     initialization_queries=10, batch_size=10)
        resumed = run_campaign(candidates, resumed_oracle, FixedController(), seed=2,
                               existing_trajectory=saved)
        uninterrupted = run_synthetic_campaign(candidates, labels, FixedController(), seed=2)
        self.assertEqual([step["selection"] for step in resumed["trajectory"]],
                         [step["selection"] for step in uninterrupted["trajectory"]])
        self.assertEqual(resumed["hits_at_budget"], uninterrupted["hits_at_budget"])
        tampered = copy.deepcopy(saved)
        tampered[1]["observations"][0]["outcome"] ^= 1
        with self.assertRaisesRegex(ValueError, "Stored checkpoint differs"):
            run_campaign(candidates, BatchOracle(candidates, labels, seed=2, total_budget=50,
                                                  initialization_queries=10, batch_size=10),
                         FixedController(), seed=2, existing_trajectory=tampered)


if __name__ == "__main__":
    unittest.main()
