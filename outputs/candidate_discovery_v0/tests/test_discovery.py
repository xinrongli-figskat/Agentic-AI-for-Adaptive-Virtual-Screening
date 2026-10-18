import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("discovery", ROOT / "discover_chembl_candidates.py")
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)
CONFIG = json.loads((ROOT / "criteria_v0.json").read_text(encoding="utf-8"))
TEMP = ROOT / ".cache" / "tests"
TEMP.mkdir(parents=True, exist_ok=True)


def record(molecule="CHEMBL1", assay="CHEMBL10", value="500", relation="=", **changes):
    return {"molecule_chembl_id": molecule, "target_chembl_id": "CHEMBL100", "assay_chembl_id": assay,
            "canonical_smiles": "CCO", "standard_type": "IC50", "assay_type": "B",
            "standard_value": value, "standard_relation": relation, "standard_units": "nM",
            "data_validity_comment": None, "potential_duplicate": False, **changes}


class DiscoveryChecks(unittest.TestCase):
    def test_boundaries_units_and_unknowns(self):
        cases = [
            (record(value="1000"), "hit_support"),
            (record(value="1001"), "nonhit_support"),
            (record(value="1", standard_units="uM"), "hit_support"),
            (record(value="1000", relation=">"), "nonhit_support"),
            (record(value="1000", relation=">="), "unknown"),
            (record(value="1000", relation="<="), "hit_support"),
            (record(value="100", relation=">"), "unknown"),
            (record(value="2000", relation="<"), "unknown"),
            (record(value=None), "unknown"),
            (record(relation=None), "unknown"),
            (record(value="0"), "unknown"),
            (record(value="NaN"), "unknown"),
            (record(standard_units="%"), "unknown"),
            (record(assay_type="F"), "unknown"),
            (record(potential_duplicate=True), "unknown"),
            (record(data_validity_comment="Potential author error"), "unknown"),
        ]
        for source, expected in cases:
            with self.subTest(source=source):
                self.assertEqual(TOOL.record_signal(source, CONFIG)[0], expected)

    def test_within_assay_disagreement_is_not_counted_as_two_classes(self):
        rows = [record(value="500"), record(value="5000")]
        result = TOOL.profile({"target_chembl_id": "CHEMBL100"}, rows, 2, True, CONFIG)
        assay = result["assay_profiles"][0]
        self.assertEqual(assay["threshold_disagreement_ids"], 1)
        self.assertEqual(assay["supported_ids"], 0)
        self.assertFalse(result["benchmark_qualified"])
        self.assertFalse(result["benchmark_labels_assigned"])

    def test_classes_across_different_assays_are_not_pooled_for_priority(self):
        config = {**CONFIG, "review_priority_gates": {"molecule_ids_with_class_support": 2,
                                                     "hit_support_molecule_ids": 1, "nonhit_support_molecule_ids": 1}}
        rows = [record(), record(molecule="CHEMBL2", assay="CHEMBL20", value="5000")]
        result = TOOL.profile({"target_chembl_id": "CHEMBL100"}, rows, 2, True, config)
        self.assertEqual(result["assays_meeting_preliminary_priority_gates"], 0)
        self.assertFalse(result["benchmark_qualified"])

    def test_pagination_cap_and_full_catalog_coverage(self):
        class Fake:
            def get(self, resource, parameters):
                data = [{"activity_id": i} for i in range(5)]
                start, count = parameters["offset"], parameters["limit"]
                return {"activities": data[start:start+count], "page_meta": {"total_count": 5}}
        rows, total, complete = TOOL.read_pages(Fake(), "activity", "activities", {}, 2, 3)
        self.assertEqual((len(rows), total, complete), (3, 5, False))
        rows, total, complete = TOOL.read_pages(Fake(), "activity", "activities", {}, 2)
        self.assertEqual((len(rows), total, complete), (5, 5, True))

    def test_inconsistent_or_repeated_pages_fail(self):
        class Fake:
            def get(self, resource, parameters):
                return {"activities": [{"activity_id": 1}], "page_meta": {"total_count": 2}}
        with self.assertRaisesRegex(ValueError, "pagination ID"):
            TOOL.read_pages(Fake(), "activity", "activities", {}, 1)
        class Changing:
            def get(self, resource, parameters):
                offset = parameters["offset"]
                return {"activities": [{"activity_id": offset}], "page_meta": {"total_count": 2+offset}}
        with self.assertRaisesRegex(ValueError, "changed"):
            TOOL.read_pages(Changing(), "activity", "activities", {}, 1)

    def test_selection_is_order_independent_and_has_no_activity_inputs(self):
        catalog = [{"target_chembl_id": f"CHEMBL{i}"} for i in range(10)]
        selected = TOOL.select_candidates(catalog, 3, CONFIG["sampling_seed"])
        self.assertEqual(selected, TOOL.select_candidates(list(reversed(catalog)), 3, CONFIG["sampling_seed"]))
        self.assertEqual(len(selected), 3)

    def test_original_bytes_hash_and_failed_json_are_retained(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as directory:
            log = []
            client = TOOL.Client(Path(directory), CONFIG, log)
            raw = b'{ "status": "UP" }\n'
            with patch.object(TOOL, "urlopen") as mocked:
                response = mocked.return_value.__enter__.return_value
                response.read.side_effect = [raw, b""]
                response.status = 200
                response.geturl.return_value = TOOL.BASE_URL + "/status.json"
                client.get("status")
            self.assertEqual((Path(directory)/"0001_status.json").read_bytes(), raw)
            self.assertEqual(log[0]["sha256"], hashlib.sha256(raw).hexdigest())
            with patch.object(TOOL, "urlopen") as mocked:
                response = mocked.return_value.__enter__.return_value
                response.read.side_effect = [b'not json', b""]
                response.status = 200
                response.geturl.return_value = TOOL.BASE_URL + "/activity.json"
                with self.assertRaises(json.JSONDecodeError):
                    client.get("activity")
            self.assertTrue((Path(directory)/"0002_activity.json").exists())
            self.assertIn("error", log[1])

    def test_deadline_retains_partial_bytes_and_checkpoints_error(self):
        with tempfile.TemporaryDirectory(dir=TEMP) as directory:
            log, checkpoints = [], []
            client = TOOL.Client(Path(directory), CONFIG, log, lambda: checkpoints.append(len(log)))
            with patch.object(TOOL, "urlopen") as mocked, patch.object(TOOL.time, "monotonic", side_effect=[0, 0, 61, 61]):
                response = mocked.return_value.__enter__.return_value
                response.read.return_value = b'partial'
                response.status = 200
                response.geturl.return_value = TOOL.BASE_URL + "/target.json"
                with self.assertRaises(TimeoutError):
                    client.get("target")
            self.assertEqual((Path(directory)/"0001_target.json.incomplete").read_bytes(), b'partial')
            self.assertFalse((Path(directory)/"0001_target.json").exists())
            self.assertEqual(checkpoints, [1, 1])
            self.assertIn("wall deadline", log[0]["error"])

    def test_failed_main_has_manifest_and_no_completed_claim(self):
        class FakeClient:
            def __init__(self, *args):
                pass
            def get(self, resource, parameters=None):
                if resource == "status":
                    return {"chembl_db_version": "fixture"}
                raise RuntimeError("fixture catalog failure")
        with tempfile.TemporaryDirectory(dir=TEMP) as directory:
            with patch.object(TOOL, "Client", FakeClient), patch("builtins.print"):
                self.assertEqual(TOOL.main(["--output-dir", directory, "--candidate-count", "1"]), 1)
            run = next(Path(directory).iterdir())
            metadata = json.loads((run/"run_metadata.json").read_text(encoding="utf-8"))
            self.assertFalse(metadata["completed"])
            self.assertFalse(metadata["catalog_complete"])
            self.assertEqual(metadata["LLM_calls"], 0)
            self.assertIn("fixture catalog failure", metadata["error"])


if __name__ == "__main__":
    unittest.main()
