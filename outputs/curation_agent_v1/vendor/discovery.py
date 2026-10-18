"""Build an inspectable preliminary candidate table; never qualify benchmarks.

Standard-library only. Candidate selection uses a declared hash ordering of the
complete SINGLE PROTEIN catalog, independent of activity outcomes. Records are
profiled within a bounded API-order window; truncated windows are explicit.
"""

import argparse
import csv
import hashlib
import json
import platform
import sys
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://www.ebi.ac.uk/chembl/api/data"
VERSION = "0.1.1"


def now():
    return datetime.now(timezone.utc).isoformat()


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class Client:
    def __init__(self, directory, config, log, checkpoint=None):
        self.directory, self.config, self.log = directory, config, log
        self.checkpoint = checkpoint or (lambda: None)

    def get(self, resource, parameters=None):
        if len(self.log) >= self.config["max_requests"]:
            raise RuntimeError("Declared HTTP request limit reached; run is incomplete")
        url = BASE_URL + "/" + resource + ".json"
        if parameters:
            url += "?" + urlencode(parameters)
        filename = f"{len(self.log)+1:04d}_{resource.replace('/', '_')}.json"
        entry = {"url": url, "raw_file": "raw/" + filename, "started_at_utc": now()}
        self.log.append(entry)
        self.checkpoint()
        start = time.monotonic()
        chunks = []
        try:
            request = Request(url, headers={"Accept": "application/json", "User-Agent": "candidate-discovery/" + VERSION})
            with urlopen(request, timeout=self.config["request_timeout_seconds"]) as response:
                entry["http_status"] = response.status
                entry["resolved_url"] = response.geturl()
                while True:
                    if time.monotonic() - start > self.config["request_wall_deadline_seconds"]:
                        raise TimeoutError("HTTP response exceeded the declared wall deadline")
                    chunk = response.read(65536)
                    if not chunk:
                        break
                    chunks.append(chunk)
                if time.monotonic() - start > self.config["request_wall_deadline_seconds"]:
                    raise TimeoutError("HTTP response exceeded the declared wall deadline")
            raw = b"".join(chunks)
            (self.directory / filename).write_bytes(raw)
            entry["sha256"] = hashlib.sha256(raw).hexdigest()
            entry["bytes"] = len(raw)
            value = json.loads(raw)
            if not isinstance(value, dict):
                raise ValueError("Expected JSON object")
            return value
        except Exception as error:
            entry["error"] = type(error).__name__ + ": " + str(error)
            if chunks and not (self.directory / filename).exists():
                partial = filename + ".incomplete"
                (self.directory / partial).write_bytes(b"".join(chunks))
                entry["partial_file"] = "raw/" + partial
            raise
        finally:
            entry["elapsed_seconds"] = round(time.monotonic() - start, 3)
            entry["finished_at_utc"] = now()
            self.checkpoint()


def read_pages(client, resource, key, parameters, page_size, cap=None):
    """Stable offset paging; reject duplicates, changing totals and early empty pages."""
    records, identifiers, total = [], set(), None
    id_field = "target_chembl_id" if resource == "target" else "activity_id"
    while total is None or len(records) < total:
        if cap is not None and len(records) >= cap:
            break
        limit = min(page_size, cap - len(records)) if cap is not None else page_size
        payload = client.get(resource, {**parameters, "limit": limit, "offset": len(records), "order_by": id_field})
        page = payload.get(key)
        count = payload.get("page_meta", {}).get("total_count")
        if not isinstance(page, list) or not all(isinstance(row, dict) for row in page):
            raise ValueError("Malformed page: " + resource)
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise ValueError("Missing or invalid total_count")
        if total is not None and count != total:
            raise ValueError("total_count changed between pages; coverage is uncertain")
        total = count
        if len(page) > limit or (not page and len(records) < total):
            raise ValueError("Unexpected page length; coverage is uncertain")
        for row in page:
            identifier = row.get(id_field)
            if identifier is None or identifier in identifiers:
                raise ValueError("Missing or repeated pagination ID: " + str(identifier))
            identifiers.add(identifier)
            records.append(row)
        if len(records) > total:
            raise ValueError("Retrieved more rows than total_count")
    return records, total, len(records) == total


def select_candidates(catalog, count, seed):
    def order(row):
        identifier = row["target_chembl_id"]
        return hashlib.sha256((seed + "|" + identifier).encode()).hexdigest(), identifier
    return sorted(catalog, key=order)[:count]


def record_signal(record, config):
    """Return provisional record evidence, never an assigned compound label."""
    if record.get("standard_type") != config["standard_type"]:
        return "unknown", "different_endpoint"
    if record.get("assay_type") != config["assay_type_for_record_signals"]:
        return "unknown", "outside_initial_assay_scope"
    if not record.get("molecule_chembl_id") or not record.get("canonical_smiles") or not record.get("assay_chembl_id"):
        return "unknown", "missing_id_or_structure_string"
    if record.get("data_validity_comment") not in config["validity_comments_allowed"]:
        return "unknown", "validity_flag_needs_review"
    if config["exclude_flagged_potential_duplicates_from_signals"] and record.get("potential_duplicate") in (True, 1, "1"):
        return "unknown", "source_potential_duplicate"
    factor = {"nM": Decimal(1), "uM": Decimal(1000), "µM": Decimal(1000), "μM": Decimal(1000)}.get(record.get("standard_units"))
    if factor is None:
        return "unknown", "unsupported_unit"
    try:
        value = Decimal(str(record.get("standard_value"))) * factor
        if not value.is_finite() or value <= 0:
            return "unknown", "nonpositive_or_nonfinite_potency"
    except InvalidOperation:
        return "unknown", "missing_or_nonnumeric_value"
    threshold = Decimal(config["hit_threshold_nM"])
    relation = record.get("standard_relation")
    if relation == "=":
        return ("hit_support" if value <= threshold else "nonhit_support"), "exact_report"
    if relation in ("<", "<=") and value <= threshold:
        return "hit_support", "upper_bound_below_threshold"
    if (relation == ">" and value >= threshold) or (relation == ">=" and value > threshold):
        return "nonhit_support", "lower_bound_above_threshold"
    return "unknown", "bound_crosses_threshold_or_relation_missing"


def profile(target, records, total, complete, config):
    signals, reasons = Counter(), Counter()
    assay_sets = defaultdict(lambda: {"hit_support": set(), "nonhit_support": set(), "unknown": set()})
    molecule_sets = {"hit_support": set(), "nonhit_support": set(), "unknown": set()}
    endpoints, assay_types = Counter(), Counter()
    for row in records:
        if row.get("target_chembl_id") != target["target_chembl_id"]:
            raise ValueError("Activity target did not match requested target")
        signal, reason = record_signal(row, config)
        signals[signal] += 1
        reasons[reason] += 1
        endpoints[row.get("standard_type") or "<missing>"] += 1
        assay_types[row.get("assay_type") or "<missing>"] += 1
        molecule = row.get("molecule_chembl_id")
        if molecule:
            molecule_sets[signal].add(molecule)
            if row.get("assay_chembl_id"):
                assay_sets[row["assay_chembl_id"]][signal].add(molecule)
    assay_profiles = []
    for identifier, sets in sorted(assay_sets.items()):
        conflict = sets["hit_support"] & sets["nonhit_support"]
        hits, nonhits = sets["hit_support"] - conflict, sets["nonhit_support"] - conflict
        assay_profiles.append({"assay_chembl_id": identifier, "hit_support_ids": len(hits),
                               "nonhit_support_ids": len(nonhits), "supported_ids": len(hits | nonhits),
                               "threshold_disagreement_ids": len(conflict), "unknown_evidence_ids": len(sets["unknown"])})
    gates = config["review_priority_gates"]
    priority = [row for row in assay_profiles if row["supported_ids"] >= gates["molecule_ids_with_class_support"]
                and row["hit_support_ids"] >= gates["hit_support_molecule_ids"]
                and row["nonhit_support_ids"] >= gates["nonhit_support_molecule_ids"]]
    best = max(assay_profiles, key=lambda row: (min(row["hit_support_ids"], row["nonhit_support_ids"]), row["supported_ids"]), default={})
    union = molecule_sets["hit_support"] | molecule_sets["nonhit_support"]
    if priority:
        status = "priority_for_assay_and_structure_review"
    elif not complete:
        status = "partial_window_needs_complete_or_assay_specific_fetch"
    elif not records:
        status = "no_IC50_records_in_declared_scope"
    elif not molecule_sets["nonhit_support"]:
        status = "needs_experimental_nonhit_evidence_or_scope_review"
    elif len(union) < gates["molecule_ids_with_class_support"]:
        status = "small_pool_in_initial_scope"
    else:
        status = "needs_assay_compatibility_and_class_coverage_review"
    return {
        "target_chembl_id": target["target_chembl_id"], "pref_name": target.get("pref_name"),
        "organism": target.get("organism"), "target_type": target.get("target_type"),
        "api_matching_IC50_records": total, "records_retrieved": len(records),
        "retrieval_complete": complete, "window_selection": "API order_by activity_id; not random",
        "molecule_ids_in_window": len({row["molecule_chembl_id"] for row in records if row.get("molecule_chembl_id")}),
        "molecule_ids_with_hit_support": len(molecule_sets["hit_support"]),
        "molecule_ids_with_nonhit_support": len(molecule_sets["nonhit_support"]),
        "molecule_ids_with_unknown_evidence": len(molecule_sets["unknown"]),
        "molecule_ids_with_both_supports_across_assays": len(molecule_sets["hit_support"] & molecule_sets["nonhit_support"]),
        "best_assay_id_for_next_review": best.get("assay_chembl_id"),
        "best_assay_supported_ids": best.get("supported_ids", 0),
        "best_assay_hit_support_ids": best.get("hit_support_ids", 0),
        "best_assay_nonhit_support_ids": best.get("nonhit_support_ids", 0),
        "assays_meeting_preliminary_priority_gates": len(priority),
        "record_signal_counts": dict(signals), "record_reason_counts": dict(reasons),
        "assay_type_counts": dict(assay_types), "endpoint_counts": dict(endpoints),
        "assay_profiles": assay_profiles, "next_review_status": status,
        "benchmark_qualified": False, "benchmark_labels_assigned": False,
        "structure_standardization_completed": False, "assay_compatibility_review_completed": False,
        "limitations": ["Structure strings and molecule IDs are not validated standardized compounds.",
                        "Evidence sets can overlap and do not constitute pooled compound labels.",
                        "Assay descriptions, mapping confidence, conditions, diversity and conflicts remain to review."]
    }


def write_table(path, profiles):
    columns = ["target_chembl_id", "pref_name", "organism", "api_matching_IC50_records", "records_retrieved",
               "retrieval_complete", "molecule_ids_in_window", "molecule_ids_with_hit_support",
               "molecule_ids_with_nonhit_support", "molecule_ids_with_both_supports_across_assays",
               "best_assay_id_for_next_review", "best_assay_supported_ids", "best_assay_hit_support_ids",
               "best_assay_nonhit_support_ids", "next_review_status", "benchmark_qualified"]
    ordered = sorted(profiles, key=lambda row: (-row["assays_meeting_preliminary_priority_gates"],
                     -min(row["best_assay_hit_support_ids"], row["best_assay_nonhit_support_ids"]),
                     -row["best_assay_supported_ids"], row["target_chembl_id"]))
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(ordered)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("criteria_v0.json"))
    parser.add_argument("--candidate-count", type=int, help="Override planned batch size for a pilot")
    parser.add_argument("--max-records-per-target", type=int, help="Explicit API-order window cap")
    parser.add_argument("--output-dir", type=Path, default=Path("data/candidate_discovery"))
    args = parser.parse_args(argv)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if args.candidate_count is not None:
        config["candidate_count"] = args.candidate_count
    if args.max_records_per_target is not None:
        config["max_activity_records_per_target"] = args.max_records_per_target
    if not 1 <= config["candidate_count"] <= 50 or not 1 <= config["max_activity_records_per_target"] <= 10000:
        parser.error("candidate count must be 1–50; per-target record cap must be 1–10000")
    threshold = Decimal(config["hit_threshold_nM"])
    if not threshold.is_finite() or threshold <= 0:
        parser.error("hit threshold must be finite and positive")
    run = args.output_dir.resolve() / ("discovery_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:8])
    (run / "raw").mkdir(parents=True, exist_ok=False)
    (run / "profiles").mkdir()
    save_json(run / "criteria_snapshot.json", config)
    (run / "tool_source.py").write_bytes(Path(__file__).read_bytes())
    log, profiles = [], []
    metadata = {"tool_version": VERSION, "started_at_utc": now(), "completed": False,
                "python_version": platform.python_version(), "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "criteria_file_sha256": hashlib.sha256(args.config.read_bytes()).hexdigest(),
                "requests": log, "LLM_calls": 0, "oracle_queries": 0,
                "benchmark_labels_assigned": False, "catalog_complete": False}
    checkpoint = lambda: save_json(run / "run_metadata.json", metadata)
    checkpoint()
    client = Client(run / "raw", config, log, checkpoint)
    try:
        status = client.get("status")
        metadata["chembl_db_version"] = status.get("chembl_db_version")
        metadata["chembl_release_date"] = status.get("chembl_release_date")
        filters = {"target_type": config["target_type"], "only": "target_chembl_id,pref_name,target_type,organism"}
        if config.get("organism"):
            filters["organism"] = config["organism"]
        catalog, total, complete = read_pages(client, "target", "targets", filters, config["catalog_page_size"])
        if not complete or any(row.get("target_type") != config["target_type"] for row in catalog):
            raise ValueError("Catalog incomplete or target filter was not respected")
        metadata["catalog_complete"] = True
        metadata["catalog_targets"] = total
        save_json(run / "target_catalog.json", catalog)
        selected = select_candidates(catalog, config["candidate_count"], config["sampling_seed"])
        save_json(run / "selected_candidates.json", {"method": "SHA256(seed|target_id) order over full catalog",
                  "seed": config["sampling_seed"], "targets": selected})
        print(f"Catalog: {total} targets; selected: {len(selected)}", flush=True)
        for target in selected:
            records, total, complete = read_pages(client, "activity", "activities",
                {"target_chembl_id": target["target_chembl_id"], "standard_type": config["standard_type"]},
                config["activity_page_size"], config["max_activity_records_per_target"])
            if any(row.get("standard_type") != config["standard_type"] for row in records):
                raise ValueError("Endpoint filter was not respected")
            result = profile(target, records, total, complete, config)
            profiles.append(result)
            save_json(run / "profiles" / (target["target_chembl_id"] + ".json"), result)
            write_table(run / "candidate_profiles.csv", profiles)
            print(f"{target['target_chembl_id']}: {len(records)}/{total} records; "
                  f"{result['molecule_ids_in_window']} molecule IDs; {result['next_review_status']}", flush=True)
        metadata["completed"] = True
    except (Exception, KeyboardInterrupt) as error:
        metadata["error"] = type(error).__name__ + ": " + str(error)
        print("Discovery incomplete:", metadata["error"], file=sys.stderr, flush=True)
    finally:
        write_table(run / "candidate_profiles.csv", profiles)
        metadata["profiled_targets"] = len(profiles)
        metadata["request_count"] = len(log)
        metadata["HTTP_elapsed_seconds"] = round(sum(entry["elapsed_seconds"] for entry in log), 3)
        metadata["response_bytes"] = sum(entry.get("bytes", 0) for entry in log)
        metadata["finished_at_utc"] = now()
        save_json(run / "run_metadata.json", metadata)
        print("Output directory:", run, flush=True)
        print("Completed:", metadata["completed"], "| Qualified benchmarks: 0 (review pending)", flush=True)
    return 0 if metadata["completed"] else 1


if __name__ == "__main__":
    sys.exit(main())
