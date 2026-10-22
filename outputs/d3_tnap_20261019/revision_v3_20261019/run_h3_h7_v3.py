"""Locked-rule D3-1 v3 audit. Writes private compound diagnostics separately."""

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path("/driveA/xinrong/agentic-screening")
OUT = ROOT / "outputs/d3_tnap_20261019/revision_v3_20261019"
PRIVATE = OUT / "d3_1_v3_private_20261019"
SOURCE = ROOT / "data/curation_private/source_audits/source_sample_CHEMBL1738510_cccc2760ddd56b29/pubchem_aid1056"
CURATION = ROOT / "data/curation_private/chembl37_batch_curations/chembl37_batch_curation_d1d3b87ef2b3ea4e/CHEMBL1738510"
RULE_SHA = "680b48265d8d64f372df665f86592795a7e4e88b4e38ec0937a77ac0169384ec"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return sha(path)


def family(name):
    if re.fullmatch(r"IC50_Qualifier_\d+_Range\d+", name):
        return "per_range_ic50_qualifier"
    if re.fullmatch(r"IC50_\d+_Range\d+", name):
        return "per_range_ic50_fit"
    if re.fullmatch(r"Std\.Err\(IC50\)_\d+_Range\d+", name):
        return "fit_standard_error"
    if re.fullmatch(r"nH_\d+_Range\d+", name):
        return "hill_slope"
    if re.fullmatch(r"Excluded_Points_[A-Za-z]+_point_Range\d+", name):
        return "excluded_dose_points"
    if re.fullmatch(r"% inhibition at [0-9.]+ uM_[A-Za-z]+_point_Range\d+\s*", name):
        return "dose_point_percent_inhibition"
    return None


def distribution(values):
    if not values:
        return {"n": 0}
    seq = sorted(values)
    return {"n": len(seq), "min": seq[0], "p25": seq[len(seq)//4],
            "median": seq[len(seq)//2], "p75": seq[3*len(seq)//4],
            "max": seq[-1], "counts": dict(sorted(Counter(seq).items()))}


def main():
    if sha(OUT / "homogeneity_measurement_rule_v3.md") != RULE_SHA:
        raise ValueError("V3 rule differs from pre-result lock")
    for path, expected in [
        (ROOT / "outputs/d3_tnap_20261019/BLOCKER.md", "f77718741153450bf8b01bc954f305f3fc49a5beb31cd531f90a611994c56451"),
        (ROOT / "outputs/d3_tnap_20261019/tnap_homogeneity_assertion.json", "b4bb2d52646dc682362cadc28540716b8199855d955051fffd9d23056afa9ad8"),
        (ROOT / "outputs/d3_tnap_20261019/reconciliation_summary.json", "b22d9ca229c8b264c19e3dba8a4b38af5b1246438e7382fc989df7d284c12e5f"),
        (ROOT / "outputs/d3_tnap_20261019/revision_v2_20261019/tnap_homogeneity_v2.json", "ca2437c427357e29ba3ddce102ce36e8322a044399f5a6852cb070093d7501a6"),
    ]:
        if sha(path) != expected:
            raise ValueError("Protected prior artifact changed: " + str(path))
    receipt = json.loads((SOURCE / "full_receipt.json").read_text())
    if sha(SOURCE / "full.json") != receipt["sha256"]:
        raise ValueError("Source file differs from receipt")
    deposited = json.loads((SOURCE / "full.json").read_text())["PC_AssaySubmit"]
    description = deposited["assay"]["descr"]
    names = {int(item["tid"]): item["name"] for item in description["results"]}
    rows = deposited["data"]
    if len(rows) != 485 or len({int(row["sid"]) for row in rows}) != 485:
        raise ValueError("Source row count/SID uniqueness differs")
    target = description.get("target") or []
    same_target = len(target) == 1 and target[0].get("mol_id", {}).get("protein_accession") == "NP_000469.3"
    protocol = " ".join(description.get("protocol") or []).lower()
    same_protocol = "tnap dose-response protocol" in protocol and "cdp-star" in protocol and "luminescence" in protocol
    coverage = Counter(int(item["tid"]) for row in rows for item in row["data"])
    grouped = defaultdict(list)
    unmatched = []
    for tid in sorted(set(coverage) - {1, 2}):
        fam = family(names.get(tid, ""))
        if fam is None:
            unmatched.append(tid)
        else:
            grouped[fam].append(tid)
    families = {fam: {"tid_count": len(tids), "row_coverage_min": min(coverage[t] for t in tids),
                      "row_coverage_max": max(coverage[t] for t in tids)}
                for fam, tids in sorted(grouped.items())}
    H3 = {"passed": not unmatched and same_target and same_protocol,
          "present_auxiliary_tid_count": len(set(coverage) - {1, 2}),
          "classified_tid_count": sum(len(x) for x in grouped.values()),
          "unclassified_tid_count": len(unmatched), "same_target": same_target,
          "same_protocol": same_protocol, "families": families}
    save(OUT / "h3_family_report.json", H3)
    if not H3["passed"]:
        raise SystemExit(2)

    comment = " ".join(description.get("comment") or [])
    desc = " ".join(description.get("description") or [])
    evidence = comment + " " + desc
    protocol_says_ten = "10 concentrations" in protocol
    mean_says_curves = "IC50 results for all curves were averaged to produce an IC50_Mean" in evidence
    ranges = sorted(set(int(re.search(r"_Range(\d+)$", name).group(1)) for name in names.values()
                        if re.fullmatch(r"IC50_\d+_Range\d+", name)))
    proxy_known = protocol_says_ten and mean_says_curves and bool(ranges)
    row_by_sid = {int(row["sid"]): row for row in rows}
    align = json.loads((ROOT / "data/curation_private/source_audits/source_sample_CHEMBL1738510_cccc2760ddd56b29/full_alignment_v1/record_alignment.json").read_text())
    sid_by_activity = {int(row["activity_id"]): int(row["sid"]) for row in align}
    if len(sid_by_activity) != 485:
        raise ValueError("Alignment coverage differs")
    depth_by_sid = {}
    row_details = {}
    for sid, row in row_by_sid.items():
        data = {names[int(item["tid"])]: item["value"] for item in row["data"]}
        fits = [(name, value.get("fval")) for name, value in data.items() if family(name) == "per_range_ic50_fit"]
        dose = [(name, value.get("fval")) for name, value in data.items() if family(name) == "dose_point_percent_inhibition"]
        depth_by_sid[sid] = len(fits)
        row_details[sid] = {"source_sid": sid, "depth": len(fits), "mean_qualifier": data["IC50_Mean_Qualifier"].get("sval"),
                            "mean_uM": data["IC50_Mean"].get("fval"), "fits": fits,
                            "dose_points": dose}
    H7a = {"proxy_meaning": "count of per-range fitted IC50 curve columns per source substance row",
           "not": "count of concentrations or independently verified run count",
           "source_says_ten_concentrations_per_curve": protocol_says_ten,
           "source_says_curve_ic50_results_averaged": mean_says_curves,
           "range_indices": ranges, "meaning_determined": proxy_known,
           "source_row_fit_depth": distribution(list(depth_by_sid.values())),
           "independent_run_count_verified": False}
    save(OUT / "h7a_depth_meaning.json", H7a)
    if not proxy_known:
        raise SystemExit(3)

    compounds = json.loads((CURATION / "compounds_private.json").read_text())
    usable = [c for c in compounds if c["usable_for_prototype_review"]]
    if len(usable) != 462:
        raise ValueError("Usable pool size differs")
    compound_rows = []
    for compound in usable:
        sids = [sid_by_activity[int(a)] for a in compound["activity_ids"]]
        depths = [depth_by_sid[sid] for sid in sids]
        if not depths or min(depths) < 1:
            raise ValueError("Missing fitted IC50 for usable compound")
        compound_rows.append({"compound_key": compound["compound_key"],
                              "label": int(compound["provisional_state"] == "hit_support"),
                              "source_sids": sids, "source_row_count": len(sids),
                              "depth_min": min(depths), "depth_max": max(depths)})
    def stratum(depth):
        return "1" if depth == 1 else "2-5" if depth <= 5 else "6-10" if depth <= 10 else ">10"
    strata = {}
    for name in ("1", "2-5", "6-10", ">10"):
        subset = [r for r in compound_rows if stratum(r["depth_min"]) == name]
        hits = sum(r["label"] for r in subset)
        strata[name] = {"compounds": len(subset), "hits": hits,
                        "measured_nonhits": len(subset) - hits,
                        "hit_fraction": hits / len(subset) if subset else None}
    H7b = {"depth_definition": "minimum fitted-curve count across a standardized compound's source rows",
           "strata": strata, "hit_depth_distribution": distribution([r["depth_min"] for r in compound_rows if r["label"]]),
           "nonhit_depth_distribution": distribution([r["depth_min"] for r in compound_rows if not r["label"]]),
           "source_row_multiplicity": distribution([r["source_row_count"] for r in compound_rows]),
           "both_classes_substantial_10_each": [name for name, x in strata.items() if x["hits"] >= 10 and x["measured_nonhits"] >= 10]}
    H7b["private_compound_table_sha256"] = save(PRIVATE / "h7b_compound_depth_labels.json", compound_rows)
    save(OUT / "h7b_strata.json", H7b)

    depth_one = [r for r in compound_rows if r["depth_min"] == 1]
    thin_sids = sorted({sid for r in depth_one for sid in r["source_sids"] if depth_by_sid[sid] == 1})
    details = []
    for sid in thin_sids:
        row = row_details[sid]
        concentrations = sorted({float(re.search(r"% inhibition at ([0-9.]+) uM", name).group(1))
                                 for name, value in row["dose_points"] if value is not None})
        exact = row["mean_qualifier"] == "="
        mean = row["mean_uM"]
        fit = row["fits"][0][1]
        fit_matches = mean is not None and fit is not None and abs(mean - fit) <= 0.001
        bracketed = mean is not None and bool(concentrations) and concentrations[0] <= mean <= concentrations[-1]
        supported = (not exact) or (len(concentrations) >= 4 and fit_matches and bracketed)
        details.append({"source_sid": sid, "qualifier": row["mean_qualifier"],
                        "mean_nM": mean * 1000 if mean is not None else None,
                        "fit_nM": fit * 1000 if fit is not None else None,
                        "dose_point_count": len(row["dose_points"]),
                        "unique_concentrations": len(concentrations),
                        "concentration_min_uM": concentrations[0] if concentrations else None,
                        "concentration_max_uM": concentrations[-1] if concentrations else None,
                        "fit_matches_mean": fit_matches, "ic50_within_tested_range": bracketed,
                        "supported": supported})
    exact_rows = [r for r in details if r["qualifier"] == "="]
    censored_rows = [r for r in details if r["qualifier"] != "="]
    exact_vals = sorted(r["mean_nM"] for r in exact_rows)
    qualifiers_by_compound = []
    for r in depth_one:
        quals = {row_details[sid]["mean_qualifier"] for sid in r["source_sids"] if depth_by_sid[sid] == 1}
        qualifiers_by_compound.append("exact_only" if quals == {"="} else "censored_only" if "=" not in quals else "mixed")
    H7c = {"depth_one_compounds": len(depth_one), "depth_one_source_rows": len(details),
           "source_row_exact": len(exact_rows), "source_row_censored": len(censored_rows),
           "compound_qualifier_states": dict(Counter(qualifiers_by_compound)),
           "exact_ic50_nM": {"min": exact_vals[0] if exact_vals else None,
                             "median": exact_vals[len(exact_vals)//2] if exact_vals else None,
                             "max": exact_vals[-1] if exact_vals else None,
                             "log10_span": math.log10(exact_vals[-1]/exact_vals[0]) if len(exact_vals)>1 else 0},
           "exact_unique_concentration_distribution": distribution([r["unique_concentrations"] for r in exact_rows]),
           "exact_supported_count": sum(r["supported"] for r in exact_rows),
           "exact_unsupported_count": sum(not r["supported"] for r in exact_rows),
           "support_rule": "one deposited fit matches IC50_Mean within 0.001 uM, >=4 numeric distinct dose concentrations, and IC50 lies within measured dose range",
           "private_source_row_sha256": save(PRIVATE / "h7c_thin_source_rows.json", details)}
    save(OUT / "h7c_thin_ic50_support.json", H7c)

    previous_h6 = json.loads((ROOT / "outputs/d3_tnap_20261019/revision_v2_20261019/d3_1_v2_private_20261019/h6_near_threshold.json").read_text())
    by_key = {r["compound_key"]: r for r in compound_rows}
    near = [{"compound_key": r["compound_key"], "depth_min": by_key[r["compound_key"]]["depth_min"],
             "depth_max": by_key[r["compound_key"]]["depth_max"]} for r in previous_h6]
    H7d = {"near_threshold_compounds": len(near),
           "depth_min_distribution": distribution([r["depth_min"] for r in near]),
           "depth_one_count": sum(r["depth_min"] == 1 for r in near),
           "majority_depth_one": sum(r["depth_min"] == 1 for r in near) > len(near)/2,
           "private_file_sha256": save(PRIVATE / "h7d_near_threshold_depth.json", near)}
    save(OUT / "h7d_near_threshold_depth.json", H7d)
    classification = "limited" if H7c["exact_unsupported_count"] == 0 else "blocker"
    result = {"h3_passed": H3["passed"], "h7a_meaning_determined": proxy_known,
              "h7c_exact_unsupported_count": H7c["exact_unsupported_count"],
              "source_gap_class": classification, "campaign_ready": False,
              "next_step": "D3-2 qualification only" if classification == "limited" else "hard stop"}
    save(OUT / "d3_1_v3_decision.json", result)
    print(json.dumps({"H3": H3, "H7a": {"meaning": H7a["proxy_meaning"], "fit_depth": H7a["source_row_fit_depth"]},
                      "H7b": {"strata": strata, "both_classes_substantial_10_each": H7b["both_classes_substantial_10_each"]},
                      "H7c": {k: v for k, v in H7c.items() if k != "private_source_row_sha256"},
                      "H7d": {"near_threshold_compounds": H7d["near_threshold_compounds"],
                              "depth_min_distribution": H7d["depth_min_distribution"]},
                      "decision": result}, ensure_ascii=False))
    if classification != "limited":
        raise SystemExit(4)


if __name__ == "__main__":
    main()
