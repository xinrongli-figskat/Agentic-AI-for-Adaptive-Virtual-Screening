"""Inspect a small ChEMBL activity sample without assigning activity labels.

This is a data-inspection tool, not an LLM agent or a qualified benchmark.
The sample follows API order and must not be treated as representative.
"""

import argparse
import csv
import hashlib
import json
import platform
import re
import sys
import time
import uuid
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://www.ebi.ac.uk/chembl/api/data"
TOOL_VERSION = "0.1.0"
FIELDS = (
    "activity_id", "molecule_chembl_id", "canonical_smiles",
    "target_chembl_id", "target_pref_name", "target_organism",
    "assay_chembl_id", "assay_type", "document_chembl_id",
    "standard_type", "standard_relation", "standard_value", "standard_units",
    "pchembl_value", "activity_comment", "data_validity_comment",
    "potential_duplicate", "standard_flag",
)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def missing(value):
    return value is None or value == ""


def finite_number(value):
    if missing(value):
        return False
    try:
        return Decimal(str(value)).is_finite()
    except InvalidOperation:
        return False


def value_counts(records, field):
    counts = Counter("<missing>" if missing(r.get(field)) else str(r[field])
                     for r in records)
    return dict(sorted(counts.items()))


def validate_activities(payload):
    records = payload.get("activities")
    if not isinstance(records, list) or not all(isinstance(r, dict) for r in records):
        raise ValueError("Response did not contain a valid activities list.")
    return records


def summarize(records, payload):
    molecule_ids = [r["molecule_chembl_id"] for r in records
                    if not missing(r.get("molecule_chembl_id"))]
    return {
        "purpose": "exploratory_field_inspection_only",
        "sampling": "API order; not a random or representative sample",
        "labels_assigned": False,
        "records_received": len(records),
        "api_total_matching_records": payload.get("page_meta", {}).get("total_count"),
        "unique_molecules_with_ids": len(set(molecule_ids)),
        "repeated_molecule_records": len(molecule_ids) - len(set(molecule_ids)),
        "unique_targets_with_ids": len({r["target_chembl_id"] for r in records
                                        if not missing(r.get("target_chembl_id"))}),
        "unique_assays_with_ids": len({r["assay_chembl_id"] for r in records
                                       if not missing(r.get("assay_chembl_id"))}),
        "missing_field_counts": {
            field: sum(missing(r.get(field)) for r in records)
            for field in ("molecule_chembl_id", "canonical_smiles", "target_chembl_id",
                          "assay_chembl_id", "document_chembl_id", "standard_value",
                          "standard_relation", "standard_units")
        },
        "finite_numeric_value_count": sum(finite_number(r.get("standard_value"))
                                          for r in records),
        "censored_record_count": sum(r.get("standard_relation") in ("<", "<=", ">", ">=")
                                     for r in records),
        "standard_type_counts": value_counts(records, "standard_type"),
        "standard_units_counts": value_counts(records, "standard_units"),
        "standard_relation_counts": value_counts(records, "standard_relation"),
        "assay_type_counts": value_counts(records, "assay_type"),
        "data_validity_comment_counts": value_counts(records, "data_validity_comment"),
        "limitations": [
            "Counts describe this sample only; they do not qualify a target.",
            "No structures or measurements have been standardized or reconciled.",
            "Missing measurements have not been assigned inactive labels.",
            "Censored values remain bounds; they are not exact measurements.",
            "Assay compatibility and direct-binding evidence require further review.",
        ],
    }


def fetch_json(url, destination, request_log):
    entry = {"url": url, "started_at_utc": utc_now()}
    request_log.append(entry)
    started = time.monotonic()
    try:
        request = Request(url, headers={
            "Accept": "application/json",
            "User-Agent": "adaptive-screening-data-inspection/" + TOOL_VERSION,
        })
        with urlopen(request, timeout=60) as response:
            raw = response.read()
            entry["http_status"] = response.status
            entry["resolved_url"] = response.geturl()
            entry["etag"] = response.headers.get("ETag")
            entry["last_modified"] = response.headers.get("Last-Modified")
        destination.write_bytes(raw)
        entry["sha256"] = hashlib.sha256(raw).hexdigest()
        entry["raw_file"] = destination.name
        entry["received_at_utc"] = utc_now()
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("Expected a JSON object from " + url)
        return payload
    except Exception as error:
        entry["error"] = type(error).__name__ + ": " + str(error)
        raise
    finally:
        entry["elapsed_seconds"] = round(time.monotonic() - started, 3)


def write_json(path, payload):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def write_preview(path, records):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for record in records:
            writer.writerow({field: record.get(field) for field in FIELDS})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--target", help="Optional ChEMBL target ID, e.g. CHEMBL203")
    parser.add_argument("--output-dir", type=Path, default=Path("data/exploration"))
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= 200:
        parser.error("--limit must be between 1 and 200 for this inspection tool")
    if args.target and not re.fullmatch(r"CHEMBL\d+", args.target):
        parser.error("--target must be a ChEMBL ID such as CHEMBL203")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:8]
    run_dir = args.output_dir.resolve() / ("chembl_sample_" + run_id)
    run_dir.mkdir(parents=True, exist_ok=False)
    parameters = {"limit": args.limit, "offset": 0}
    if args.target:
        parameters["target_chembl_id"] = args.target
    metadata = {
        "tool_version": TOOL_VERSION,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "python_version": platform.python_version(),
        "started_at_utc": utc_now(),
        "request_parameters": parameters,
        "output_dir": str(run_dir),
        "completed": False,
        "requests": [],
    }
    try:
        status = fetch_json(BASE_URL + "/status.json", run_dir / "raw_status.json",
                            metadata["requests"])
        metadata["chembl_db_version"] = status.get("chembl_db_version")
        metadata["chembl_release_date"] = status.get("chembl_release_date")
        payload = fetch_json(BASE_URL + "/activity.json?" + urlencode(parameters),
                             run_dir / "raw_activities.json", metadata["requests"])
        records = validate_activities(payload)
        summary = summarize(records, payload)
        write_preview(run_dir / "activity_preview.csv", records)
        write_json(run_dir / "summary.json", summary)
        metadata["completed"] = True
        print("ChEMBL:", metadata["chembl_db_version"])
        print("Output directory:", run_dir)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    except Exception as error:
        metadata["error"] = type(error).__name__ + ": " + str(error)
        print("Inspection failed:", metadata["error"], file=sys.stderr)
        print("Partial files and request log:", run_dir, file=sys.stderr)
    finally:
        metadata["finished_at_utc"] = utc_now()
        write_json(run_dir / "run_metadata.json", metadata)
    return 0 if metadata["completed"] else 1


if __name__ == "__main__":
    sys.exit(main())
