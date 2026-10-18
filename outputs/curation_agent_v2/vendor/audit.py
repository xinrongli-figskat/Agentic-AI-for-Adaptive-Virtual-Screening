"""Offline, provenance-checked single-assay structure and measurement audit.

The output contains provisional evidence classes, not frozen campaign labels.
No network, LLM or oracle tool is exposed here. Requires the remote RDKit install.
"""
import argparse
import csv
import hashlib
import importlib.util
import json
import math
import platform
import re
import sys
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import parse_qs, urlparse

VERSION = "0.1.1"


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path, rows, columns):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v
                             for k, v in row.items() if k in columns})


def load_helper():
    source = Path(__file__).with_name("discovery_helper.py")
    spec = importlib.util.spec_from_file_location("assay_discovery_helper", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_evidence(run, target, endpoint):
    """Require a complete declared target/endpoint acquisition and verify raw hashes."""
    run = run.resolve()
    metadata = json.loads((run / "run_metadata.json").read_text(encoding="utf-8"))
    profile = json.loads((run / "profiles" / (target + ".json")).read_text(encoding="utf-8"))
    config = json.loads((run / "criteria_snapshot.json").read_text(encoding="utf-8"))
    if digest(run / "tool_source.py") != metadata.get("script_sha256"):
        raise ValueError("Discovery source snapshot does not match its recorded hash")
    if not metadata.get("completed") or not profile.get("retrieval_complete"):
        raise ValueError("Target acquisition is incomplete; do not curate a truncated window as complete")
    if profile.get("target_chembl_id") != target or config.get("standard_type") != endpoint:
        raise ValueError("Saved profile or endpoint does not match audit scope")
    receipts, records, total, expected_offset, ids = [], [], None, 0, set()
    for receipt in metadata["requests"]:
        query = parse_qs(urlparse(receipt["url"]).query)
        if query.get("target_chembl_id") != [target] or query.get("standard_type") != [endpoint]:
            continue
        if urlparse(receipt["url"]).path.rstrip("/").split("/")[-1] != "activity.json":
            continue
        path = (run / receipt["raw_file"]).resolve()
        if not path.is_relative_to(run):
            raise ValueError("Raw source path escapes the declared run directory")
        if receipt.get("error") or receipt.get("http_status") != 200 or digest(path) != receipt.get("sha256"):
            raise ValueError("Raw response is failed, changed, or not hash-verified")
        if int(query.get("offset", ["0"])[0]) != expected_offset:
            raise ValueError("Missing or reordered source page")
        page = json.loads(path.read_bytes())
        count = page["page_meta"]["total_count"]
        if total is not None and count != total:
            raise ValueError("Source totals differ between pages")
        total = count
        for row in page["activities"]:
            identifier = row.get("activity_id")
            if identifier is None or identifier in ids:
                raise ValueError("Missing or duplicated source activity ID")
            if row.get("target_chembl_id") != target or row.get("standard_type") != endpoint:
                raise ValueError("Activity outside declared target/endpoint scope")
            ids.add(identifier)
            records.append(row)
        expected_offset = len(records)
        receipts.append({"raw_file": receipt["raw_file"], "sha256": receipt["sha256"], "url": receipt["url"]})
    if total is None or len(records) != total or len(records) != profile["records_retrieved"]:
        raise ValueError("Verified source rows do not cover the complete saved target profile")
    return records, config, profile, metadata, receipts


def standardize_structure(smiles):
    from rdkit import Chem
    from rdkit.Chem.MolStandardize import rdMolStandardize
    result = {"source_smiles": smiles or "", "structure_status": "quarantined", "structure_reason": ""}
    try:
        mol = Chem.MolFromSmiles(smiles) if isinstance(smiles, str) and smiles.strip() else None
        if mol is None or not mol.GetNumAtoms():
            raise ValueError("missing_or_invalid_structure")
        result["parsed_source_smiles"] = Chem.MolToSmiles(mol, isomericSmiles=True)
        fragments = Chem.GetMolFrags(mol, asMols=True, sanitizeFrags=True)
        organic = [f for f in fragments if any(a.GetAtomicNum() == 6 for a in f.GetAtoms())]
        if len(organic) != 1:
            raise ValueError("zero_or_multiple_carbon_containing_fragments")
        parent = rdMolStandardize.Cleanup(organic[0])
        Chem.SanitizeMol(parent)
        if len(Chem.GetMolFrags(parent)) != 1:
            raise ValueError("cleanup_produced_multiple_fragments")
        allowed = {1, 5, 6, 7, 8, 9, 14, 15, 16, 17, 35, 53}
        if any(a.GetAtomicNum() not in allowed or a.GetNumRadicalElectrons() for a in parent.GetAtoms()):
            raise ValueError("dummy_radical_or_unsupported_element")
        canonical = Chem.MolToSmiles(parent, canonical=True, isomericSmiles=True)
        uncharged = rdMolStandardize.Uncharger().uncharge(Chem.Mol(parent))
        scaffold = Chem.MolFromSmiles(Chem.MolToSmiles(parent, isomericSmiles=False))
        from rdkit.Chem.Scaffolds import MurckoScaffold
        scaffold = MurckoScaffold.GetScaffoldForMol(scaffold)
        result.update({
            "structure_status": "ok", "standardized_smiles": canonical,
            "removed_fragment_count": len(fragments)-1,
            "normalization_changed_retained_fragment": Chem.MolToSmiles(organic[0], isomericSmiles=True) != canonical,
            "formal_charge": Chem.GetFormalCharge(parent),
            "unspecified_atom_stereocenters": sum(tag == "?" for _, tag in Chem.FindMolChiralCenters(parent, includeUnassigned=True)),
            "stereo_and_isotope_agnostic_smiles": Chem.MolToSmiles(parent, isomericSmiles=False),
            "uncharged_smiles_sensitivity_only": Chem.MolToSmiles(uncharged, isomericSmiles=True),
            "scaffold_smiles": Chem.MolToSmiles(scaffold, isomericSmiles=False) or "<acyclic>",
            "generic_scaffold_smiles": Chem.MolToSmiles(MurckoScaffold.MakeScaffoldGeneric(scaffold), isomericSmiles=False) or "<acyclic>",
        })
    except Exception as error:
        result["structure_reason"] = str(error)
    return result


def potency_nM(row):
    factor = {"nM": Decimal(1), "uM": Decimal(1000), "µM": Decimal(1000), "μM": Decimal(1000)}.get(row.get("standard_units"))
    if factor is None:
        return None
    try:
        value = Decimal(str(row.get("standard_value"))) * factor
        return value if value.is_finite() and value > 0 else None
    except (InvalidOperation, ValueError):
        return None


def reconcile(rows, config, threshold, record_signal):
    """Combine only unanimous eligible threshold evidence; preserve exact values and bounds."""
    local_config = {**config, "hit_threshold_nM": str(threshold)}
    signals, eligible, reasons = [], [], Counter()
    for row in rows:
        signal, reason = record_signal(row, local_config)
        signals.append(signal)
        reasons[reason] += 1
        # Valid censor bounds can be threshold-unknown but still need reconciliation.
        if reason in {"exact_report", "upper_bound_below_threshold", "lower_bound_above_threshold",
                      "bound_crosses_threshold_or_relation_missing"} and potency_nM(row) is not None:
            eligible.append(row)
    support = set(signals) - {"unknown"}
    state = "threshold_disagreement" if len(support) == 2 else next(iter(support), "unknown")
    bounds = [(r["standard_relation"], potency_nM(r)) for r in eligible if r.get("standard_relation") in ("<", "<=", ">", ">=")]
    exact = [potency_nM(r) for r in eligible if r.get("standard_relation") == "="]
    flags = []
    if state == "threshold_disagreement":
        flags.append("eligible_measurements_cross_hit_threshold")
    lowers = [(v, rel == ">") for rel, v in bounds if rel in (">", ">=")]
    uppers = [(v, rel == "<") for rel, v in bounds if rel in ("<", "<=")]
    incompatible = any(lo > hi or (lo == hi and (ls or hs)) for lo, ls in lowers for hi, hs in uppers)
    incompatible |= any((rel == "<" and v >= b) or (rel == "<=" and v > b)
                        or (rel == ">" and v <= b) or (rel == ">=" and v < b)
                        for v in exact for rel, b in bounds)
    if incompatible:
        flags.append("censored_bounds_or_exact_values_disagree_needs_review")
    if state == "hit_support" and any(re.search(r"\b(inactive|inconclusive|not active)\b", str(r.get("activity_comment") or ""), re.I) for r in rows):
        flags.append("source_activity_annotation_disagrees_with_hit_support")
    return {
        "provisional_state": state, "review_flags": flags,
        "usable_for_prototype_review": state in ("hit_support", "nonhit_support") and not flags,
        "decision_reason": ", ".join(flags) if flags else "unanimous_eligible_threshold_support" if support else "no_eligible_threshold_support",
        "record_reason_counts": dict(reasons), "eligible_exact_count": len(exact),
        "eligible_censored_count": len(bounds),
        "exact_min_nM": str(min(exact)) if exact else None,
        "exact_max_nM": str(max(exact)) if exact else None,
        "exact_fold_range": str(max(exact)/min(exact)) if exact else None,
    }


def percentile(values, p):
    ordered = sorted(values)
    if not ordered:
        return None
    position = (len(ordered)-1)*p
    left, right = math.floor(position), math.ceil(position)
    return ordered[left] + (ordered[right]-ordered[left])*(position-left)


def diversity(compounds, policy):
    from rdkit import Chem, DataStructs
    from rdkit.Chem import rdFingerprintGenerator
    from rdkit.ML.Cluster import Butina
    active = sorted((c for c in compounds if c["usable_for_prototype_review"]), key=lambda c: c["compound_key"])
    n = len(active)
    settings = policy["diversity_policy"]
    if n > settings["maximum_compounds_for_exact_pairwise_analysis"]:
        raise ValueError("Pairwise diversity exceeds declared compound limit; revise analysis explicitly")
    generator = rdFingerprintGenerator.GetMorganGenerator(radius=settings["radius"], fpSize=settings["bits"], includeChirality=settings["include_chirality"])
    fps = [generator.GetFingerprint(Chem.MolFromSmiles(c["standardized_smiles"])) for c in active]
    distances, nearest, pairs, high_pairs = [], [0.0]*n, 0, 0
    near_cutoff = settings["near_duplicate_similarity_threshold"]
    for i in range(1, n):
        similarities = DataStructs.BulkTanimotoSimilarity(fps[i], fps[:i])
        distances.extend(1-s for s in similarities)
        for j, similarity in enumerate(similarities):
            nearest[i], nearest[j] = max(nearest[i], similarity), max(nearest[j], similarity)
            pairs += 1
            high_pairs += similarity >= near_cutoff
    cutoff = settings["butina_tanimoto_similarity_threshold"]
    clusters = Butina.ClusterData(distances, n, 1-cutoff, isDistData=True, reordering=True) if n else []
    cluster_rows = []
    for i, cluster in enumerate(clusters):
        identifier = "cluster_" + str(i+1).zfill(4)
        counts = Counter(active[j]["provisional_state"] for j in cluster)
        for j in cluster:
            active[j]["cluster_id"] = identifier
            active[j]["nearest_neighbor_tanimoto"] = nearest[j] if n > 1 else None
        cluster_rows.append({"cluster_id": identifier, "size": len(cluster),
                             "centroid_compound_key": active[cluster[0]]["compound_key"],
                             "hit_support": counts["hit_support"], "nonhit_support": counts["nonhit_support"]})
    scaffolds = Counter(c["scaffold_smiles"] for c in active)
    generic = Counter(c["generic_scaffold_smiles"] for c in active)
    return {
        "compound_count": n, "pair_count": pairs, "scaffold_count_including_acyclic_bucket": len(scaffolds),
        "generic_scaffold_count_including_acyclic_bucket": len(generic),
        "acyclic_compounds": scaffolds.get("<acyclic>", 0),
        "largest_scaffold_fraction": max(scaffolds.values(), default=0)/n if n else None,
        "top_scaffolds": [{"scaffold": s, "count": count} for s, count in scaffolds.most_common(10)],
        "butina_cluster_count": len(clusters), "largest_cluster_fraction": max(map(len, clusters), default=0)/n if n else None,
        "clusters": cluster_rows,
        "nearest_neighbor_tanimoto_p10": percentile(nearest, .1) if n > 1 else None,
        "nearest_neighbor_tanimoto_median": percentile(nearest, .5) if n > 1 else None,
        "nearest_neighbor_tanimoto_p90": percentile(nearest, .9) if n > 1 else None,
        "near_neighbor_similarity_cutoff": near_cutoff,
        "fraction_with_neighbor_at_or_above_cutoff": sum(s >= near_cutoff for s in nearest)/n if n > 1 else None,
        "pair_fraction_at_or_above_cutoff": high_pairs/pairs if pairs else None,
        "interpretation": "Similarity is representation-dependent; Butina clusters are greedy centroid groups, not all-pairs equivalence classes. Scaffold counts alone do not prove diversity.",
    }


def audit_records(records, config, policy, helper):
    cache, by_id, audits = {}, defaultdict(list), []
    for row in records:
        smiles = row.get("canonical_smiles")
        cache_key = smiles if isinstance(smiles, str) else None
        if cache_key not in cache:
            cache[cache_key] = standardize_structure(smiles)
        structure = cache[cache_key]
        signal, reason = helper.record_signal(row, {**config, "hit_threshold_nM": policy["hit_threshold_nM"]})
        value = potency_nM(row)
        audits.append({**row, **structure, "record_signal": signal, "record_reason": reason,
                       "normalized_value_nM": str(value) if value is not None else None})
        if row.get("molecule_chembl_id"):
            by_id[row["molecule_chembl_id"]].append((row, structure))
    grouped, id_audit = defaultdict(list), []
    for molecule_id, entries in sorted(by_id.items()):
        keys = {s.get("standardized_smiles") for _, s in entries if s["structure_status"] == "ok"}
        reason = "structure_failure" if any(s["structure_status"] != "ok" for _, s in entries) else "multiple_structures_for_one_source_id" if len(keys) != 1 else ""
        id_audit.append({"molecule_chembl_id": molecule_id, "structure_status": "quarantined" if reason else "ok",
                         "structure_reason": reason, "standardized_smiles_variants": sorted(keys),
                         "activity_ids": [r["activity_id"] for r, _ in entries]})
        if not reason:
            grouped[next(iter(keys))].extend((molecule_id, r, s) for r, s in entries)
    compounds, sensitivity = [], {t: Counter() for t in policy["sensitivity_thresholds_nM"]}
    for smiles, entries in sorted(grouped.items()):
        rows = [r for _, r, _ in entries]
        structure = entries[0][2]
        outcome = reconcile(rows, config, policy["hit_threshold_nM"], helper.record_signal)
        compound = {**structure, **outcome, "compound_key": "cmp_"+hashlib.sha256(smiles.encode()).hexdigest(),
                    "molecule_chembl_ids": sorted({m for m, _, _ in entries}),
                    "activity_ids": sorted(r["activity_id"] for r in rows),
                    "document_chembl_ids": sorted({r["document_chembl_id"] for r in rows if r.get("document_chembl_id")}),
                    "record_count": len(rows), "cluster_id": None, "nearest_neighbor_tanimoto": None}
        compounds.append(compound)
        for threshold in sensitivity:
            result = reconcile(rows, config, threshold, helper.record_signal)
            sensitivity[threshold][result["provisional_state"]] += 1
            sensitivity[threshold]["usable_hit_support" if result["usable_for_prototype_review"] and result["provisional_state"] == "hit_support"
                                   else "usable_nonhit_support" if result["usable_for_prototype_review"] else "requires_review_or_unknown"] += 1
    return audits, id_audit, compounds, {k: dict(v) for k, v in sensitivity.items()}


def budget_analysis(compounds, proposals):
    counts = Counter(c["provisional_state"] for c in compounds if c["usable_for_prototype_review"])
    hits, nonhits = counts["hit_support"], counts["nonhit_support"]
    n = hits + nonhits
    result = {"provisional_pool_size": n, "hit_support_count": hits, "nonhit_support_count": nonhits,
              "assumption": "Uniform sampling of distinct compounds without replacement; provisional support classes must survive review before campaign use.",
              "initialization_is_included_in_total_budget": True, "campaign_evaluation_performed": False, "proposals": []}
    for proposal in proposals:
        q, initial, batch = proposal["query_budget"], proposal["initialization_queries"], proposal["feedback_batch_size"]
        row = {**proposal, "pool_large_enough": n >= q, "both_classes_present": bool(hits and nonhits)}
        if n >= q:
            p = hits / n
            denominator = math.comb(n, initial)
            no_hits = math.comb(nonhits, initial)/denominator if initial <= nonhits else 0.0
            no_nonhits = math.comb(hits, initial)/denominator if initial <= hits else 0.0
            row.update({"pool_fraction_queried": q/n, "random_expected_hits": q*p,
                        "random_hit_count_sd": math.sqrt(q*p*(1-p)*(n-q)/(n-1)) if n > 1 else 0.0,
                        "maximum_possible_hits_with_budget": min(q, hits),
                        "initialization_expected_hits": initial*p,
                        "initialization_probability_no_hits": no_hits,
                        "initialization_probability_no_nonhits": no_nonhits,
                        "initialization_probability_single_class": no_hits + no_nonhits,
                        "queries_after_initialization": q-initial,
                        "feedback_batches_after_initialization": math.ceil((q-initial)/batch)})
        else:
            row["reason"] = "Budget exceeds the number of distinct provisional usable compounds"
        result["proposals"].append(row)
    return result


def validate_policy(policy):
    for value in [policy["hit_threshold_nM"], *policy["sensitivity_thresholds_nM"]]:
        number = Decimal(str(value))
        if not number.is_finite() or number <= 0:
            raise ValueError("Thresholds must be finite and positive")
    for proposal in policy["budget_proposals"]:
        values = [proposal[k] for k in ("query_budget", "initialization_queries", "feedback_batch_size")]
        if any(not isinstance(v, int) or isinstance(v, bool) or v <= 0 for v in values) or values[1] > values[0]:
            raise ValueError("Budget, initialization and batch sizes must be positive integers; initialization is included")
    settings = policy["diversity_policy"]
    if not 0 < settings["butina_tanimoto_similarity_threshold"] < 1 or not 0 < settings["near_duplicate_similarity_threshold"] <= 1:
        raise ValueError("Invalid declared similarity thresholds")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--discovery-run", type=Path, required=True)
    parser.add_argument("--source-review", type=Path, required=True, help="Verified source_review_combined.json")
    parser.add_argument("--policy", type=Path, default=Path(__file__).with_name("audit_policy_v0.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/curation_review"))
    args = parser.parse_args(argv)
    run = args.output_dir.resolve() / ("assay_audit_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:8])
    run.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    metadata = {"tool_version": VERSION, "started_at_utc": now(), "completed": False,
                "python_version": platform.python_version(), "network_calls": 0, "LLM_calls": 0,
                "oracle_queries": 0, "campaign_labels_frozen": False, "benchmark_qualified": False,
                "discovery_run": str(args.discovery_run.resolve()), "source_review": str(args.source_review.resolve())}
    try:
        import rdkit
        metadata["rdkit_version"] = rdkit.__version__
        helper = load_helper()
        policy = json.loads(args.policy.read_text(encoding="utf-8"))
        validate_policy(policy)
        for name, source in (("audit_tool_source.py", Path(__file__)), ("discovery_helper.py", Path(__file__).with_name("discovery_helper.py")),
                             ("audit_policy.json", args.policy), ("source_review.json", args.source_review)):
            (run / name).write_bytes(source.read_bytes())
        target, assay = policy["target_chembl_id"], policy["assay_chembl_id"]
        records, config, profile, source_metadata, receipts = load_evidence(args.discovery_run, target, policy["endpoint"])
        source_review = json.loads(args.source_review.read_text(encoding="utf-8"))
        if source_review.get("source_release") != source_metadata.get("chembl_db_version"):
            raise ValueError("Source description and activity release differ; review version change explicitly")
        description = next(a for a in source_review["assays"] if a["assay_chembl_id"] == assay)
        if description["target_chembl_id"] != target:
            raise ValueError("Assay source description maps to another target")
        selected = [r for r in records if r.get("assay_chembl_id") == assay]
        if not selected:
            raise ValueError("Selected assay has no activity records in complete target acquisition")
        baseline = helper.profile({"target_chembl_id": target}, records, len(records), True, config)
        baseline_assay = next(a for a in baseline["assay_profiles"] if a["assay_chembl_id"] == assay)
        saved_assay = next(a for a in profile["assay_profiles"] if a["assay_chembl_id"] == assay)
        if baseline_assay != saved_assay:
            raise ValueError("Recomputed initial assay evidence differs from saved discovery profile")
        save_json(run / "source_receipts.json", receipts)
        save_json(run / "original_target_profile.json", profile)
        save_json(run / "discovery_criteria_snapshot.json", config)
        save_json(run / "raw_selected_activities.json", {"activities": selected})
        audits, id_audit, compounds, sensitivity = audit_records(selected, config, policy, helper)
        statistics = diversity(compounds, policy)
        budget = budget_analysis(compounds, policy["budget_proposals"])
        save_json(run / "records_audit.json", audits)
        save_json(run / "molecule_id_audit.json", id_audit)
        save_json(run / "compound_audit.json", compounds)
        save_json(run / "budget_feasibility.json", budget)
        write_csv(run / "records_audit.csv", audits, ["activity_id", "molecule_chembl_id", "assay_chembl_id", "document_chembl_id",
                  "type", "relation", "value", "units", "standard_type", "standard_relation", "standard_value", "standard_units",
                  "normalized_value_nM", "activity_comment", "data_validity_comment", "potential_duplicate", "record_signal", "record_reason",
                  "source_smiles", "structure_status", "structure_reason", "standardized_smiles", "removed_fragment_count"])
        write_csv(run / "compound_audit.csv", compounds, ["compound_key", "standardized_smiles", "molecule_chembl_ids", "activity_ids",
                  "document_chembl_ids", "record_count", "provisional_state", "review_flags", "decision_reason", "usable_for_prototype_review",
                  "exact_min_nM", "exact_max_nM", "exact_fold_range", "formal_charge", "unspecified_atom_stereocenters",
                  "scaffold_smiles", "generic_scaffold_smiles", "cluster_id", "nearest_neighbor_tanimoto"])
        states = Counter(c["provisional_state"] for c in compounds)
        usable = Counter(c["provisional_state"] for c in compounds if c["usable_for_prototype_review"])
        identity_sensitivity = {}
        for field in ("stereo_and_isotope_agnostic_smiles", "uncharged_smiles_sensitivity_only"):
            groups = defaultdict(list)
            for c in compounds:
                groups[c[field]].append(c["compound_key"])
            identity_sensitivity[field] = {"group_count": len(groups), "groups_with_multiple_primary_identities": sum(len(g)>1 for g in groups.values())}
        summary = {"purpose": "single_assay_curation_review", "target_chembl_id": target, "assay_chembl_id": assay,
                   "endpoint_interpretation": description["description"], "assay_mapping_confidence": description["confidence_score"],
                   "target_endpoint_records_verified": len(records), "selected_assay_records": len(selected),
                   "source_molecule_ids": len(id_audit), "quarantined_molecule_ids": sum(r["structure_status"] != "ok" for r in id_audit),
                   "standardized_identity_count": len(compounds),
                   "primary_identity_groups_merging_multiple_source_ids": sum(len(c["molecule_chembl_ids"])>1 for c in compounds),
                   "initial_assay_evidence_before_structure_processing": baseline_assay,
                   "provisional_state_counts": dict(states), "usable_support_counts": dict(usable),
                   "compounds_requiring_review_or_unknown": sum(not c["usable_for_prototype_review"] for c in compounds),
                   "threshold_sensitivity": sensitivity, "identity_sensitivity": identity_sensitivity,
                   "diversity": statistics, "budget_feasibility": budget, "benchmark_qualified": False, "campaign_labels_frozen": False,
                   "limitations": ["Only the declared target, assay and IC50 scope was curated.",
                     "Numerical IC50 inhibition evidence does not establish direct binding.",
                     "Charge and tautomer choices can change identity; alternatives are not silently pooled.",
                     "A literature-series pool can have source and analogue-selection bias.",
                     "Manual source/conflict review, criteria review, final qualification and campaign isolation remain required."]}
        save_json(run / "summary.json", summary)
        report = ["# Single-assay audit: review pending", "", f"Target: {target}; assay: {assay}",
                  f"Selected records: {len(selected)}; source molecule IDs: {len(id_audit)}.",
                  f"Structure-quarantined IDs: {summary['quarantined_molecule_ids']}; standardized identities: {len(compounds)}.",
                  f"Provisional usable support classes: {dict(usable)}.", "",
                  "## Consequential choices", "",
                  "Only this assay and IC50 scope are combined. Original records and source URLs remain available.",
                  "The single carbon-containing fragment is retained; ambiguous mixtures and invalid structures are quarantined.",
                  "Canonical isomeric identity preserves specified stereochemistry and isotopes. Uncharging is a sensitivity analysis only.",
                  "Conflicting threshold evidence or incompatible censored bounds require review; no average potency is invented.",
                  "Unknown evidence is retained. No decoy labels are assigned.", "",
                  "## Diversity and budget review", "",
                  f"Scaffold groups (including acyclic bucket): {statistics['scaffold_count_including_acyclic_bucket']}.",
                  f"Largest scaffold fraction: {statistics['largest_scaffold_fraction']}.",
                  f"Butina clusters: {statistics['butina_cluster_count']}; largest cluster fraction: {statistics['largest_cluster_fraction']}.",
                  "Read budget_feasibility.json for both budget proposals, random expectations and single-class initialization probabilities.",
                  "These calculations use the provisional pool and are not campaign results.", "",
                  "## Required next decisions", "",
                  "Inspect quarantined structures, measurement flags and merged source IDs.",
                  "Judge whether analogue/source concentration is acceptable for the intended prototype.",
                  "Review quantity, class coverage and budget criteria before freezing any benchmark or running campaigns.",
                  "Changing thresholds must be justified scientifically before evaluation, rather than selected for agent performance.",
                  "Curation outputs contain outcomes and must be inaccessible to the future campaign agent."]
        (run / "review_notes.md").write_text("\n".join(report)+"\n", encoding="utf-8")
        metadata.update({"completed": True, "chembl_db_version": source_metadata["chembl_db_version"], "provisional_compound_evidence_constructed": True})
        print(json.dumps({k: summary[k] for k in ("target_chembl_id", "assay_chembl_id", "selected_assay_records", "source_molecule_ids",
                         "quarantined_molecule_ids", "standardized_identity_count", "provisional_state_counts", "usable_support_counts",
                         "compounds_requiring_review_or_unknown", "threshold_sensitivity")}, ensure_ascii=True, indent=2))
        print(json.dumps({"diversity": {k: v for k, v in statistics.items() if k != "clusters"}}, ensure_ascii=True, indent=2))
        print(json.dumps({"budget_feasibility": budget}, ensure_ascii=True, indent=2))
    except (Exception, KeyboardInterrupt) as error:
        metadata["error"] = type(error).__name__ + ": " + str(error)
        print("Audit incomplete:", metadata["error"], file=sys.stderr)
    finally:
        metadata["finished_at_utc"] = now()
        metadata["elapsed_seconds"] = round(time.monotonic()-started, 3)
        save_json(run / "run_metadata.json", metadata)
        save_json(run / "OUTPUT_SHA256_MANIFEST.json", {p.name: digest(p) for p in run.iterdir() if p.is_file()})
        print("Output directory:", run)
        print("Completed:", metadata["completed"], "| Qualification: review pending")
    return 0 if metadata["completed"] else 1


if __name__ == "__main__":
    sys.exit(main())
