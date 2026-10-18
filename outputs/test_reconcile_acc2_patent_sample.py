import copy
import json
import unittest
from decimal import Decimal
from pathlib import Path

from reconcile_acc2_patent_sample import reconcile


TABLE = json.loads((Path(__file__).parent / "acc2_patent_us8835472_sample_values.json").read_text())


class ReconcileTest(unittest.TestCase):
    def test_exact_unit_conversion(self):
        rows = []
        for signal in ("hit_support", "nonhit_support"):
            for item in TABLE["values"][len(rows):len(rows) + 6]:
                rows.append({"compound_name": f"US8835472, {item['example']}",
                             "standard_value": float(Decimal(item["ic50_uM"]) * 1000),
                             "standard_relation": "=", "activity_id": len(rows),
                             "molecule_chembl_id": str(len(rows)), "src_compound_id": str(len(rows))})
        selection = {"assay_id": "CHEMBL3705476", "main_sample": {
            "hit_support": rows[:6], "nonhit_support": rows[6:]}}
        self.assertEqual(reconcile(selection, TABLE)["value_matches"], 12)
        altered = copy.deepcopy(selection)
        altered["main_sample"]["hit_support"][0]["standard_value"] += 1
        self.assertEqual(reconcile(altered, TABLE)["value_mismatches"], 1)


if __name__ == "__main__":
    unittest.main()
