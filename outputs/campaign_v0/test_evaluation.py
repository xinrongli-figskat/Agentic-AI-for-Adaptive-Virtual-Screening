"""Synthetic outcome trajectory evaluation checks."""

import unittest

from .campaign_core import FixedController, RandomController, SyntheticAdaptiveStub, run_synthetic_campaign
from .evaluation import check_run, compare_paired, summarize_run


class EvaluationTest(unittest.TestCase):
    def test_metrics_on_complete_synthetic_run(self):
        candidates = [{"compound_key": f"synthetic_{i:03d}",
                       "standardized_smiles": "C" * (i + 1)} for i in range(60)]
        labels = {row["compound_key"]: int(i % 2 == 0) for i, row in enumerate(candidates)}
        run = run_synthetic_campaign(candidates, labels, FixedController(), seed=0)
        self.assertEqual(len(check_run(run)), 50)
        summary = summarize_run(run)
        self.assertEqual(summary["h_at_50"], run["hits_at_budget"])
        self.assertEqual(sum(summary["round_hits"]), summary["h_at_50"])
        self.assertGreaterEqual(summary["auc_10_50_average_cumulative_hits"], 0)
        self.assertEqual(summary["api_calls_with_usage"], 0)

    def test_api_attempts_and_overload_rejections_are_counted(self):
        candidates = [{"compound_key": f"synthetic_{i:03d}",
                       "standardized_smiles": "C" * (i + 1)} for i in range(60)]
        labels = {row["compound_key"]: int(i % 2 == 0) for i, row in enumerate(candidates)}
        run = run_synthetic_campaign(candidates, labels, FixedController(), seed=0)
        run["trajectory"][1]["llm_call"] = {
            "api_usage": {"prompt_tokens": 20, "completion_tokens": 5},
            "api_attempt_log": [{"http_status": 429, "business_code": "1305"},
                                {"http_status": 200, "business_code": None}],
        }
        summary = summarize_run(run)
        self.assertEqual(summary["api_attempts_total"], 2)
        self.assertEqual(summary["api_overload_rejections"], 1)
        self.assertEqual(summary["prompt_tokens"], 20)

    def test_incorrect_cumulative_count_rejected(self):
        candidates = [{"compound_key": f"synthetic_{i:03d}",
                       "standardized_smiles": "C" * (i + 1)} for i in range(60)]
        labels = {row["compound_key"]: 0 for row in candidates}
        run = run_synthetic_campaign(candidates, labels, RandomController(), seed=0)
        run["trajectory"][2]["cumulative_hits"] = 1
        with self.assertRaisesRegex(ValueError, "cumulative"):
            check_run(run)

    def test_matched_seed_comparison_rejects_different_initialization(self):
        candidates = [{"compound_key": f"synthetic_{i:03d}",
                       "standardized_smiles": "C" * (i + 1)} for i in range(60)]
        labels = {row["compound_key"]: int(i % 2 == 0) for i, row in enumerate(candidates)}
        runs = [run_synthetic_campaign(candidates, labels, controller, seed=0)
                for controller in (SyntheticAdaptiveStub(), FixedController(), RandomController())]
        result = compare_paired(runs, agent_name="synthetic_adaptive_stub_not_llm")
        self.assertEqual(len(result["paired_runs"]), 1)
        self.assertIsNone(result["by_representation"]["bit"]["sample_sd_llm_minus_fixed"])
        runs[0]["trajectory"][0]["selection"][0] = "tampered"
        with self.assertRaises(ValueError):
            compare_paired(runs, agent_name="synthetic_adaptive_stub_not_llm")


if __name__ == "__main__":
    unittest.main()
