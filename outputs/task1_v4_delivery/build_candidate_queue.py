"""Build a transparent, offline Task 1 follow-up queue from the closed v3 run.

This script assigns no labels and makes no API or GLM calls. Counts are screening
signals only; assay-level counts are preliminary molecule-ID support counts.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE = ROOT / "outputs/results/task1_v3_closed_20261016/run/state.json"
DEFAULT_HOLDS = ROOT / "outputs/curation_agent_v3/source_holds.json"


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def flatten_assays(state, holds):
    profiles = {}
    for origin, collection in (("historical_preview", state.get("seed_profiles", {})),
                               ("v3_profile", state.get("profiles", {}))):
        for target_id, profile in collection.items():
            for row in profile.get("top_assays_in_window", profile.get("assay_profiles", [])):
                assay_id = row.get("assay_chembl_id")
                if not assay_id:
                    continue
                previous = profiles.get(assay_id, {})
                # Keep the clearest available scope; these counts are still previews.
                profiles[assay_id] = {
                    "assay_id": assay_id,
                    "target_id": target_id,
                    "target_name": profile.get("name") or profile.get("pref_name") or profile.get("target_name"),
                    "target_record_count": profile.get("source_total"),
                    "target_window_records": profile.get("records_received"),
                    "target_window_complete": profile.get("retrieval_complete"),
                    "window_origin": origin,
                    "profile_evidence_id": profile.get("evidence_id"),
                    "hit_support_ids": int(row.get("hit_support_ids", 0)),
                    "nonhit_support_ids": int(row.get("nonhit_support_ids", 0)),
                    "supported_ids": int(row.get("supported_ids", 0)),
                    "threshold_disagreement_ids": int(row.get("threshold_disagreement_ids", 0)),
                    "unknown_evidence_ids": int(row.get("unknown_evidence_ids", 0)),
                }
                # Do not let a lower-information duplicate overwrite richer evidence.
                if previous and previous.get("target_window_complete") and not profiles[assay_id].get("target_window_complete"):
                    profiles[assay_id] = previous

    for row in profiles.values():
        row["source_hold"] = holds.get(row["assay_id"])
        row["class_balance_proxy"] = min(row["hit_support_ids"], row["nonhit_support_ids"])
        row["interpretation"] = (
            "preview_only; IDs with support before structure standardization; "
            "not an assay compound count or a benchmark label set"
        )
    return sorted(profiles.values(), key=lambda r: (
        bool(r["source_hold"]), -r["class_balance_proxy"], -r["supported_ids"],
        r["unknown_evidence_ids"], r["target_id"], r["assay_id"]))


def build(state_path: Path, holds_path: Path, output_dir: Path):
    state = read(state_path)
    if state.get("schema") != "task1_agent_v3.0":
        raise ValueError("Expected the archived Task 1 v3 state")
    if state.get("status") not in ("paused_at_step_limit", "llm_budget_exhausted", "finished"):
        raise ValueError("Input state is not a closed historical run")
    holds_doc = read(holds_path)
    holds = holds_doc.get("holds", {})
    protocol = state["protocol"]
    minimum = int(protocol["minimum_usable_compounds"])
    targets = []
    for target_id, row in state.get("target_counts", {}).items():
        if row.get("scope") != "IC50_type_B":
            continue
        profiled = target_id in state.get("profiles", {}) or target_id in state.get("seed_profiles", {})
        profile = state.get("profiles", {}).get(target_id) or state.get("seed_profiles", {}).get(target_id) or {}
        targets.append({
            "target_id": target_id,
            "target_name": row.get("name"),
            "organism": (state.get("catalog_by_target", {}).get(target_id) or {}).get("organism"),
            "raw_ic50_type_b_record_count": int(row.get("raw_activity_count", 0)),
            "count_evidence_id": row.get("evidence_id"),
            "profiled_in_closed_run": profiled,
            "profile_records_received": profile.get("records_received"),
            "profile_source_total": profile.get("source_total"),
            "profile_complete": profile.get("retrieval_complete"),
            "profile_evidence_id": profile.get("evidence_id"),
            "status": "target_count_only_not_assay_qualified",
            "recommendation": "profile_target" if not profiled and int(row.get("raw_activity_count", 0)) >= minimum else
                "list_assays_and_count_assay" if profiled else "below_current_raw_count_screen",
        })
    targets.sort(key=lambda r: (-r["raw_ic50_type_b_record_count"], r["target_id"]))
    assays = flatten_assays(state, holds)

    out = output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    def portable(path):
        try:
            return path.resolve().relative_to(ROOT).as_posix()
        except ValueError:
            return path.name

    source_hashes = {portable(state_path): sha(state_path), portable(holds_path): sha(holds_path)}
    result = {
        "schema": "task1_v4_offline_candidate_queue_v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_release": state.get("release"),
        "source_run_status": state.get("status"),
        "source_run": "Task 1 v3 closed evidence; post-exposure exploratory extension",
        "source_sha256": source_hashes,
        "no_network_calls": True,
        "no_llm_calls": True,
        "labels_assigned": False,
        "qualification_rule_version": protocol.get("version"),
        "operational_gates_retained": {
            "limited_feasibility_usable_compounds": minimum,
            "preferred_usable_compounds": protocol["preferred_usable_compounds"],
            "minimum_hit_support": protocol["minimum_hits"],
            "minimum_nonhit_support": protocol["minimum_nonhits"],
            "budget": protocol["query_budget"],
            "initialization_in_budget": protocol["initialization_queries"],
            "maximum_query_fraction": protocol["maximum_query_fraction"],
            "interpretation": "retained for prospective candidate review; exploratory choices, not brief-mandated thresholds",
        },
        "target_queue": targets,
        "assay_preview_queue": assays,
        "limitations": [
            "Target record counts are not distinct compound counts and do not show class balance.",
            "A complete target window can still contain incomplete assay windows.",
            "Assay preview counts are source molecule-ID supports before structure standardization.",
            "Partial target windows provide observed lower bounds, never complete upper bounds.",
            "Source holds apply to listed assays only; they do not reject whole targets.",
            "This queue ranks where to inspect next; it does not qualify a benchmark.",
        ],
    }
    (out / "candidate_queue.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_csv(out / "target_queue.csv", targets)
    write_csv(out / "assay_preview_queue.csv", assays)
    return result


def write_csv(path: Path, rows):
    if not rows:
        path.write_text("\n", encoding="utf-8")
        return
    columns = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--holds", type=Path, default=DEFAULT_HOLDS)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "outputs/task1_v4_delivery/queue")
    args = parser.parse_args()
    result = build(args.state, args.holds, args.output_dir)
    print(json.dumps({
        "status": "offline_queue_built",
        "targets_ranked": len(result["target_queue"]),
        "unprofiled_targets_at_or_above_current_raw_count_gate": sum(
            r["recommendation"] == "profile_target" for r in result["target_queue"]),
        "assay_previews_ranked": len(result["assay_preview_queue"]),
        "source_release": result["source_release"],
        "no_network_calls": result["no_network_calls"],
        "no_llm_calls": result["no_llm_calls"],
        "output_dir": str(args.output_dir.resolve()),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
