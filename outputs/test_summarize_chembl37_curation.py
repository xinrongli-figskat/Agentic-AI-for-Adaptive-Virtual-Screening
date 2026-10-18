import unittest

from summarize_chembl37_curation import build


class FunnelTest(unittest.TestCase):
    def test_rejects_missing_or_duplicate_assays(self):
        prescreen = {"assays": [
            {"assay_id": "A", "numeric_prescreen_pass": True},
            {"assay_id": "B", "numeric_prescreen_pass": True},
        ]}
        row = {"assay_id": "A", "campaign_ready": False,
               "qualification": {"numerical_eligibility": True},
               "source_tier": "other_or_unknown"}
        with self.assertRaises(ValueError):
            build(prescreen, [[row]])
        with self.assertRaises(ValueError):
            build(prescreen, [[row, row]])


if __name__ == "__main__":
    unittest.main()
