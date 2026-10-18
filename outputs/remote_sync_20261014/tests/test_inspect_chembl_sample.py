import csv
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "inspect_chembl_sample.py"
if not SOURCE.is_file():
    SOURCE = ROOT / "outputs" / "inspect_chembl_sample.py"
TEMP_ROOT = ROOT / ".cache" / "inspection-tests"
TEMP_ROOT.mkdir(parents=True, exist_ok=True)
SPEC = importlib.util.spec_from_file_location("sample_tool", SOURCE)
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)

RECORDS = [
    {"activity_id": 1, "molecule_chembl_id": "CHEMBL1", "canonical_smiles": "CCO",
     "target_chembl_id": "CHEMBL10", "assay_chembl_id": "CHEMBL100",
     "standard_type": "IC50", "standard_relation": ">", "standard_value": "10000",
     "standard_units": "nM", "potential_duplicate": False},
    {"activity_id": 2, "molecule_chembl_id": "CHEMBL1", "canonical_smiles": "CCO",
     "target_chembl_id": "CHEMBL10", "assay_chembl_id": "CHEMBL101",
     "standard_type": "Ki", "standard_relation": "=", "standard_value": "Not determined",
     "standard_units": "uM"},
    {"activity_id": 3, "molecule_chembl_id": "CHEMBL2", "canonical_smiles": None,
     "target_chembl_id": "CHEMBL20", "assay_chembl_id": "CHEMBL102",
     "standard_type": "IC50", "standard_relation": None, "standard_value": None,
     "standard_units": None},
]
PAYLOAD = {"activities": RECORDS, "page_meta": {"total_count": 12345}}


class InspectionChecks(unittest.TestCase):
    def test_fetch_keeps_exact_response_bytes_and_hash(self):
        raw = b'{ "activities": [], "page_meta": {"total_count": 0} }\n'
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as directory:
            path = Path(directory) / "raw.json"
            log = []
            with patch.object(TOOL, "urlopen") as mocked:
                response = mocked.return_value.__enter__.return_value
                response.read.return_value = raw
                response.status = 200
                response.geturl.return_value = TOOL.BASE_URL + "/activity.json"
                response.headers.get.return_value = None
                result = TOOL.fetch_json(TOOL.BASE_URL + "/activity.json", path, log)
            self.assertEqual(path.read_bytes(), raw)
            self.assertEqual(result["activities"], [])
            self.assertEqual(log[0]["sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(log[0]["http_status"], 200)

    def test_scientific_edge_cases_are_reported_without_labeling(self):
        summary = TOOL.summarize(RECORDS, PAYLOAD)
        self.assertEqual(summary["records_received"], 3)
        self.assertEqual(summary["unique_molecules_with_ids"], 2)
        self.assertEqual(summary["repeated_molecule_records"], 1)
        self.assertEqual(summary["unique_assays_with_ids"], 3)
        self.assertEqual(summary["censored_record_count"], 1)
        self.assertEqual(summary["finite_numeric_value_count"], 1)
        self.assertEqual(summary["missing_field_counts"]["standard_value"], 1)
        self.assertEqual(summary["standard_units_counts"], {"<missing>": 1, "nM": 1, "uM": 1})
        self.assertFalse(summary["labels_assigned"])

    def test_csv_preserves_bounds_units_duplicates_and_missing_data(self):
        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as directory:
            path = Path(directory) / "preview.csv"
            TOOL.write_preview(path, RECORDS)
            with path.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 3)
            self.assertEqual(rows[0]["standard_relation"], ">")
            self.assertEqual(rows[0]["standard_value"], "10000")
            self.assertEqual(rows[1]["standard_units"], "uM")
            self.assertEqual(rows[2]["standard_value"], "")
            self.assertNotIn("hit", rows[0])

    def test_malformed_response_is_not_silently_treated_as_empty_data(self):
        for payload in ({}, {"activities": {}}, {"activities": [None]}):
            with self.assertRaises(ValueError):
                TOOL.validate_activities(payload)

    def test_main_records_version_and_creates_separate_run_directories(self):
        def fake_fetch(url, destination, log):
            payload = ({"chembl_db_version": "ChEMBL_fixture", "chembl_release_date": "fixture"}
                       if url.endswith("status.json") else PAYLOAD)
            destination.write_text(json.dumps(payload), encoding="utf-8")
            log.append({"url": url, "fixture": True})
            return payload

        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as directory:
            with patch.object(TOOL, "fetch_json", side_effect=fake_fetch), patch("builtins.print"):
                args = ["--limit", "20", "--target", "CHEMBL10", "--output-dir", directory]
                self.assertEqual(TOOL.main(args), 0)
                self.assertEqual(TOOL.main(args), 0)
            runs = list(Path(directory).iterdir())
            self.assertEqual(len(runs), 2)
            metadata = json.loads((runs[0] / "run_metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["chembl_db_version"], "ChEMBL_fixture")
            self.assertTrue(metadata["completed"])
            self.assertEqual(metadata["request_parameters"]["target_chembl_id"], "CHEMBL10")
            self.assertEqual(len(metadata["requests"]), 2)

    def test_failed_activity_request_retains_status_and_failed_manifest(self):
        def fake_fetch(url, destination, log):
            log.append({"url": url, "fixture": True})
            if url.endswith("status.json"):
                payload = {"chembl_db_version": "ChEMBL_fixture"}
                destination.write_text(json.dumps(payload), encoding="utf-8")
                return payload
            raise RuntimeError("simulated activity request failure")

        with tempfile.TemporaryDirectory(dir=TEMP_ROOT) as directory:
            with patch.object(TOOL, "fetch_json", side_effect=fake_fetch), patch("builtins.print"):
                self.assertEqual(TOOL.main(["--output-dir", directory]), 1)
            run = next(Path(directory).iterdir())
            metadata = json.loads((run / "run_metadata.json").read_text(encoding="utf-8"))
            self.assertFalse(metadata["completed"])
            self.assertIn("simulated activity request failure", metadata["error"])
            self.assertTrue((run / "raw_status.json").exists())
            self.assertFalse((run / "summary.json").exists())


if __name__ == "__main__":
    unittest.main()
