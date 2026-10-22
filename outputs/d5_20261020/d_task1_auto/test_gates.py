import copy
import unittest

from gates import allowed_actions, apply_action, numeric_gate, validate_action


class GateTests(unittest.TestCase):
    def setUp(self):
        self.row = {"N": "462", "K": "53", "measured_nonhit_support": "409",
                    "largest_cluster_fraction": "0.0238", "scaffold_bucket_count_including_acyclic": "195",
                    "P_single_class10": "0.2919"}
        self.c = {"assay_id": "CHEMBL1738510", "stage": 0, "numeric": numeric_gate(self.row),
                  "source_assessment": None}

    def test_numeric_and_source_are_separate(self):
        self.assertTrue(self.c["numeric"]["pass"])
        self.assertIsNone(self.c["source_assessment"])

    def test_exact_stage_mask_and_no_skip(self):
        self.assertEqual(allowed_actions(self.c), ("inspect_metadata",))
        with self.assertRaisesRegex(ValueError, "Action masked"):
            validate_action(self.c, {"action": "decide_assay", "arguments": {"assay_id": self.c["assay_id"],
                                  "verdict": "review_shortlist"}, "reason": "Too early to decide"})
        for action in ("inspect_metadata", "read_evidence"):
            apply_action(self.c, {"action": action, "arguments": {"assay_id": self.c["assay_id"]},
                                  "reason": "Read the allowed evidence"})
        self.assertEqual(allowed_actions(self.c), ("assess_source",))

    def test_unknown_assay_masked(self):
        self.c["assay_id"] = "CHEMBL999"
        self.assertEqual(allowed_actions(self.c), ())

    def test_hold_cannot_shortlist(self):
        self.c["stage"] = 3
        self.c["source_assessment"] = {"status": "unresolved"}
        with self.assertRaisesRegex(ValueError, "Cannot shortlist"):
            validate_action(self.c, {"action": "decide_assay", "arguments": {"assay_id": self.c["assay_id"],
                                  "verdict": "review_shortlist"}, "reason": "This is an invalid promotion"})

    def test_draft_shortlist_never_campaign_ready(self):
        self.c["stage"] = 3
        self.c["source_assessment"] = {"status": "limited"}
        apply_action(self.c, {"action": "decide_assay", "arguments": {"assay_id": self.c["assay_id"],
                              "verdict": "review_shortlist"}, "reason": "Evidence supports limited review"})
        self.assertFalse(self.c["decision"]["campaign_ready"])
        self.assertEqual(allowed_actions(self.c), ())

    def test_numeric_failure_blocks_shortlist(self):
        self.c["stage"] = 3
        self.c["source_assessment"] = {"status": "limited"}
        self.c["numeric"] = copy.deepcopy(self.c["numeric"])
        self.c["numeric"]["pass"] = False
        with self.assertRaisesRegex(ValueError, "numeric gate"):
            validate_action(self.c, {"action": "decide_assay", "arguments": {"assay_id": self.c["assay_id"],
                                  "verdict": "review_shortlist"}, "reason": "Numerics fail the gate"})


if __name__ == "__main__":
    unittest.main()
