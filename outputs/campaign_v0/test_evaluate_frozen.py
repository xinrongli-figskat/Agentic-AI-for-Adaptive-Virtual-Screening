"""Private evaluator's threshold diagnostic on synthetic records."""

import unittest

from .evaluate_frozen import threshold_diagnostic


class ThresholdDiagnosticTest(unittest.TestCase):
    def test_exact_near_and_censored_separated_without_relabeling(self):
        values = [800, 1000, 1250, 799, 1251] + [2000] * 44
        private = {f"synthetic_{i:03d}": {"exact_min_nM": value,
                                           "exact_max_nM": value}
                   for i, value in enumerate(values)}
        private["synthetic_049"] = {"exact_min_nM": None, "exact_max_nM": None}
        observations = [{"compound_key": f"synthetic_{i:03d}",
                         "outcome": int(i in (0, 2, 4))} for i in range(50)]
        run = {"trajectory": [{"observations": observations}]}
        result = threshold_diagnostic(run, private)
        self.assertEqual(result["near_exact_count"], 3)
        self.assertEqual(result["near_exact_hits"], 2)
        self.assertEqual(result["far_exact_count"], 46)
        self.assertEqual(result["censored_or_not_exact_count"], 1)


if __name__ == "__main__":
    unittest.main()
