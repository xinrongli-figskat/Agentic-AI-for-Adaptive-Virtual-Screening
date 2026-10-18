import unittest

from curate_remaining_chembl37 import selected_queue


class QueueTest(unittest.TestCase):
    def test_excludes_prior_assays_and_orders_by_minority_class(self):
        rows = [
            {"assay_id": "A", "numeric_prescreen_pass": True, "hit_support_ids": 30,
             "nonhit_support_ids": 120, "supported_ids": 150},
            {"assay_id": "B", "numeric_prescreen_pass": True, "hit_support_ids": 80,
             "nonhit_support_ids": 100, "supported_ids": 180},
            {"assay_id": "C", "numeric_prescreen_pass": False, "hit_support_ids": 200,
             "nonhit_support_ids": 200, "supported_ids": 400},
            {"assay_id": "D", "numeric_prescreen_pass": True, "hit_support_ids": 60,
             "nonhit_support_ids": 130, "supported_ids": 190},
        ]
        actual = selected_queue({"assays": rows}, {"B"})
        self.assertEqual([row["assay_id"] for row in actual], ["D", "A"])


if __name__ == "__main__":
    unittest.main()
