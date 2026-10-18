import copy
import json
from pathlib import Path
import unittest

from reconcile_tace_patent_sample import reconcile


ROOT = Path(__file__).parent


class TacePatentTests(unittest.TestCase):
    def setUp(self):
        self.selection = json.loads((ROOT.parent / ".sync_audit" / "chembl37_benchmark_20261017" /
                                     "tace_selection.json").read_text(encoding="utf-8"))
        self.table = json.loads((ROOT / "tace_patent_us9926281_sample_values.json").read_text(encoding="utf-8"))

    def test_frozen_sample_matches_patent_transcription(self):
        result = reconcile(self.selection, self.table)
        self.assertEqual((result["sample_count"], result["name_matches"], result["value_matches"]),
                         (12, 12, 12))
        self.assertFalse(result["source_endpoint_resolved"])

    def test_a_wrong_source_value_is_detected(self):
        table = copy.deepcopy(self.table)
        table["source_values"][0]["value_nM"] = "278"
        result = reconcile(self.selection, table)
        self.assertEqual(result["value_matches"], 11)


if __name__ == "__main__":
    unittest.main()
