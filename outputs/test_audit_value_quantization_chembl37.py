import unittest

from audit_value_quantization_chembl37 import canonical_key, summarize_records


class ValueResolutionTests(unittest.TestCase):
    def test_equivalent_numeric_strings_share_bucket(self):
        self.assertEqual(canonical_key({"standard_relation": "=", "standard_value": 275.0,
                                        "standard_units": "nM"}),
                         canonical_key({"standard_relation": "=", "standard_value": "275.000",
                                        "standard_units": "nM"}))

    def test_low_resolution_is_review_flag_not_label(self):
        rows = [{"standard_relation": "=", "standard_value": 275,
                 "standard_units": "nM"}] * 150
        rows += [{"standard_relation": "=", "standard_value": 10250,
                  "standard_units": "nM"}] * 150
        result = summarize_records(rows)
        self.assertTrue(result["low_resolution_review_flag"])
        self.assertEqual(result["distinct_relation_value_unit"], 2)
        self.assertEqual(result["largest_value_fraction"], 0.5)


if __name__ == "__main__":
    unittest.main()
