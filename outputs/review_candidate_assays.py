"""Fetch source descriptions for five assays chosen from the user's saved profiles.

Run beside candidate_discovery_v0, or supply --discovery-dir explicitly.
This adds source evidence only; it assigns no benchmark labels or qualifications.
"""

import argparse
import hashlib
import importlib.util
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


SELECTED = [
    ("CHEMBL4575", "CHEMBL5363961"),
    ("CHEMBL3769299", "CHEMBL5737708"),
    ("CHEMBL204", "CHEMBL816079"),
    ("CHEMBL4822", "CHEMBL871431"),
    ("CHEMBL4372", "CHEMBL861854"),
]

ASSAY_FIELDS = [
    "assay_chembl_id", "description", "assay_type", "target_chembl_id",
    "confidence_score", "relationship_type", "assay_organism", "assay_tax_id",
    "assay_cell_type", "assay_tissue", "assay_subcellular_fraction",
    "bao_format", "bao_label", "variant_sequence", "document_chembl_id",
    "src_id", "src_assay_id", "aidx", "assay_parameters",
]
DOCUMENT_FIELDS = [
    "document_chembl_id", "title", "authors", "journal", "year", "doi",
    "pubmed_id", "patent_id", "doc_type", "abstract",
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--discovery-dir", type=Path,
                        default=Path(__file__).resolve().parent / "candidate_discovery_v0")
    parser.add_argument("--output-dir", type=Path, default=Path("data/exploration"))
    parser.add_argument("--assay-id", choices=[a for _, a in SELECTED], action="append",
                        help="Fetch only these selected assays, for example after a failed request")
    args = parser.parse_args()
    selected = [(t, a) for t, a in SELECTED if args.assay_id is None or a in args.assay_id]
    source = args.discovery_dir / "discover_chembl_candidates.py"
    spec = importlib.util.spec_from_file_location("discovery_metadata_helper", source)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    config = json.loads((args.discovery_dir / "criteria_v0.json").read_text(encoding="utf-8"))
    config["max_requests"] = 12
    run = args.output_dir.resolve() / (
        "assay_review_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "_" + uuid.uuid4().hex[:8]
    )
    (run / "raw").mkdir(parents=True, exist_ok=False)
    (run / "review_tool_source.py").write_bytes(Path(__file__).read_bytes())
    (run / "discovery_helper_source.py").write_bytes(source.read_bytes())
    log = []
    metadata = {
        "tool_version": "candidate_assay_review_0.1.1",
        "started_at_utc": helper.now(), "completed": False,
        "purpose": "Review source descriptions before selecting a benchmark scope",
        "selection_basis": "Five best-assay IDs printed by the user's remote discovery run",
        "source_discovery_run": "discovery_20261014T122202Z_5a03ac52",
        "selected_target_assay_pairs": selected,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "helper_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "max_requests": config["max_requests"],
        "request_timeout_seconds": config["request_timeout_seconds"],
        "request_wall_deadline_seconds": config["request_wall_deadline_seconds"],
        "requests": log, "errors": [], "LLM_calls": 0, "oracle_queries": 0,
        "benchmark_labels_assigned": False, "benchmark_qualified": False,
    }
    summary = {"assays": [], "documents": []}
    def checkpoint():
        helper.save_json(run / "run_metadata.json", metadata)
    checkpoint()
    client = helper.Client(run / "raw", config, log, checkpoint)
    try:
        status = client.get("status")
        metadata["chembl_db_version"] = status.get("chembl_db_version")
        metadata["chembl_release_date"] = status.get("chembl_release_date")
        for target_id, assay_id in selected:
            try:
                assay = client.get("assay/" + assay_id)
                if assay.get("assay_chembl_id") != assay_id or assay.get("target_chembl_id") != target_id:
                    raise ValueError("Returned assay or target did not match requested pair")
                summary["assays"].append({k: assay.get(k) for k in ASSAY_FIELDS})
                helper.save_json(run / "summary.json", summary)
                print("Read assay:", assay_id, flush=True)
            except Exception as error:
                metadata["errors"].append({"assay_id": assay_id, "error": str(error)})
        document_ids = sorted({a["document_chembl_id"] for a in summary["assays"] if a["document_chembl_id"]})
        for document_id in document_ids:
            try:
                document = client.get("document/" + document_id)
                if document.get("document_chembl_id") != document_id:
                    raise ValueError("Returned document ID did not match request")
                summary["documents"].append({k: document.get(k) for k in DOCUMENT_FIELDS})
                helper.save_json(run / "summary.json", summary)
                print("Read document:", document_id, flush=True)
            except Exception as error:
                metadata["errors"].append({"document_id": document_id, "error": str(error)})
        metadata["completed"] = not metadata["errors"] and len(summary["assays"]) == len(selected)
    except (Exception, KeyboardInterrupt) as error:
        metadata["errors"].append({"error": type(error).__name__ + ": " + str(error)})
    finally:
        metadata["finished_at_utc"] = helper.now()
        metadata["request_count"] = len(log)
        metadata["HTTP_elapsed_seconds"] = round(sum(r.get("elapsed_seconds", 0) for r in log), 3)
        helper.save_json(run / "summary.json", summary)
        checkpoint()
        print("Output directory:", run)
        print("Completed:", metadata["completed"])
        print(json.dumps(summary, ensure_ascii=True, indent=2))
        if metadata["errors"]:
            print(json.dumps(metadata["errors"], ensure_ascii=True, indent=2))
    return 0 if metadata["completed"] else 1


if __name__ == "__main__":
    sys.exit(main())
