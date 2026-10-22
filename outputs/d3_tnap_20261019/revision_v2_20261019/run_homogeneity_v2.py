"""D3-1 v2: verify selected endpoint provenance and auxiliary column families."""

import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

from scipy.stats import pointbiserialr
from sklearn.metrics import roc_auc_score

ROOT = Path("/driveA/xinrong/agentic-screening")
OUT = ROOT / "outputs/d3_tnap_20261019/revision_v2_20261019"
PRIVATE = OUT / "d3_1_v2_private_20261019"
SOURCE = ROOT / "data/curation_private/source_audits/source_sample_CHEMBL1738510_cccc2760ddd56b29/pubchem_aid1056"
CURATION = ROOT / "data/curation_private/chembl37_batch_curations/chembl37_batch_curation_d1d3b87ef2b3ea4e/CHEMBL1738510"
DB = ROOT / "data/source_dbs/chembl_37/extracted/chembl_37.db"
RULE_HASH = "64578594c0f3e25745a31110cb0d95799a98cd0cebbac7f37d83f1b85794d5c7"
DB_HASH = "4be13df3b68e25dcd0bff44bf094033b5aebe98f415acdc8c1cdf380e0c15142"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def output(name, obj, private=False):
    path = (PRIVATE if private else OUT) / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    return sha(path)


def family(name):
    if re.fullmatch(r"IC50_Qualifier_\d+_Range\d+", name):
        return "per_range_ic50_qualifier"
    if re.fullmatch(r"IC50_\d+_Range\d+", name):
        return "per_range_ic50_fit"
    if re.fullmatch(r"Std\.Err\(IC50\)_\d+_Range\d+", name):
        return "per_range_fit_standard_error"
    if re.fullmatch(r"nH_\d+_Range\d+", name):
        return "per_range_hill_slope"
    if re.fullmatch(r"Excluded_Points_(first|second|third)_point_Range\d+", name):
        return "excluded_dose_points"
    if re.fullmatch(r"% inhibition at [0-9.]+ uM_(first|second|third)_point_Range\d+\s*", name):
        return "dose_point_percent_inhibition"
    return None


def stats(values):
    sorted_values = sorted(values)
    n = len(values)
    return {"n": n, "min": sorted_values[0], "p25": sorted_values[n // 4],
            "median": sorted_values[n // 2], "p75": sorted_values[3 * n // 4],
            "max": sorted_values[-1], "distinct_counts": dict(sorted(Counter(values).items()))}


def main():
    if sha(OUT / "homogeneity_rule_v2.md") != RULE_HASH:
        raise ValueError("v2 rule hash differs from pre-result lock")
    if sha(DB) != DB_HASH:
        raise ValueError("ChEMBL 37 SQLite hash differs")
    prior = ROOT / "outputs/d3_tnap_20261019"
    for filename, expected in {
        "BLOCKER.md": "f77718741153450bf8b01bc954f305f3fc49a5beb31cd531f90a611994c56451",
        "tnap_homogeneity_assertion.json": "b4bb2d52646dc682362cadc28540716b8199855d955051fffd9d23056afa9ad8",
        "reconciliation_summary.json": "b22d9ca229c8b264c19e3dba8a4b38af5b1246438e7382fc989df7d284c12e5f",
    }.items():
        if sha(prior / filename) != expected:
            raise ValueError("Prior D3 artifact changed: " + filename)
    receipt = json.loads((SOURCE / "full_receipt.json").read_text())
    if receipt["aid"] != 1056 or sha(SOURCE / "full.json") != receipt["sha256"]:
        raise ValueError("PubChem source hash mismatch")
    source = json.loads((SOURCE / "full.json").read_text())["PC_AssaySubmit"]
    descr = source["assay"]["descr"]
    names = {int(x["tid"]): x["name"] for x in descr["results"]}
    rows = source["data"]
    by_sid = {str(row["sid"]): row for row in rows}
    if len(rows) != len(by_sid) or len(rows) != 485:
        raise ValueError("PubChem SID rows are not exactly 485 unique entries")
    conn = sqlite3.connect("file:" + str(DB) + "?mode=ro", uri=True)
    conn.execute("pragma query_only=on")
    records = conn.execute("""select act.activity_id, cr.src_compound_id, act.standard_relation,
                    act.standard_value, act.standard_units, act.standard_type, a.assay_type,
                    a.confidence_score, a.tid from activities act
                    join assays a on a.assay_id=act.assay_id
                    join compound_records cr on cr.record_id=act.record_id
                    where a.chembl_id='CHEMBL1738510' order by act.activity_id""").fetchall()
    accession = conn.execute("""select cs.accession from assays a
                    join target_components tc on tc.tid=a.tid
                    join component_sequences cs on cs.component_id=tc.component_id
                    where a.chembl_id='CHEMBL1738510'""").fetchall()
    conn.close()
    alignment = json.loads((ROOT / "data/curation_private/source_audits/source_sample_CHEMBL1738510_cccc2760ddd56b29/full_alignment_v1/record_alignment.json").read_text())
    aligned = {int(row["activity_id"]): row for row in alignment}
    if len(records) != len(aligned) or len(records) != 485:
        raise ValueError("Record alignment coverage is incomplete")
    H1 = (names.get(1) == "IC50_Mean_Qualifier" and names.get(2) == "IC50_Mean"
          and all({1, 2}.issubset({int(item["tid"]) for item in row["data"]}) for row in rows))
    bad_h2 = []
    row_by_activity = {}
    for aid, sid, relation, value, units, endpoint, assay_type, confidence, tid in records:
        source_row = by_sid.get(str(sid))
        pair = {int(item["tid"]): item["value"] for item in source_row["data"]} if source_row else {}
        if (source_row is None or pair.get(1, {}).get("sval") != relation
            or "fval" not in pair.get(2, {}) or value is None
            or abs(Decimal(str(value)) - Decimal(str(pair[2]["fval"])) * 1000) > Decimal("0.001")
            or units != "nM" or endpoint != "IC50" or assay_type != "B" or confidence != 9
            or tid != 101624 or aligned.get(aid, {}).get("alignment_status") != "matched"):
            bad_h2.append(aid)
        row_by_activity[aid] = source_row
    H2 = not bad_h2 and accession == [("P05186",)]
    tid_coverage = Counter(int(item["tid"]) for row in rows for item in row["data"])
    auxiliary = {tid: name for tid, name in names.items() if tid not in (1, 2) and tid_coverage[tid]}
    grouped = defaultdict(list)
    unknown = []
    for tid, name in auxiliary.items():
        group = family(name)
        if group is None:
            unknown.append({"tid": tid, "name": name})
        else:
            grouped[group].append(tid)
    target = descr.get("target") or []
    one_target = (len(target) == 1 and target[0].get("mol_id", {}).get("protein_accession") == "NP_000469.3")
    protocol = " ".join(descr.get("protocol") or []).lower()
    protocol_same = "tnap dose-response protocol" in protocol and "cdp-star" in protocol and "luminescence" in protocol
    H3 = not unknown and one_target and protocol_same and set(auxiliary) == set(tid_coverage) - {1, 2}
    families = {key: {"tid_count": len(tids), "row_coverage_min": min(tid_coverage[t] for t in tids),
                      "row_coverage_max": max(tid_coverage[t] for t in tids)} for key, tids in sorted(grouped.items())}

    aux_counts = {int(row["sid"]): sum(int(item["tid"]) not in (1, 2) for item in row["data"]) for row in rows}
    fits = {int(row["sid"]): sum(family(names[int(item["tid"])]) == "per_range_ic50_fit"
                                 for item in row["data"] if int(item["tid"]) in names)
            for row in rows}
    records_by_activity = {int(rec[0]): int(rec[1]) for rec in records}
    compounds = json.loads((CURATION / "compounds_private.json").read_text())
    usable = [c for c in compounds if c["usable_for_prototype_review"]]
    private_rows = []
    for compound in usable:
        sids = [records_by_activity[int(a)] for a in compound["activity_ids"]]
        private_rows.append({"compound_key": compound["compound_key"],
                             "label": int(compound["provisional_state"] == "hit_support"),
                             "source_sids": sids,
                             "auxiliary_tid_count_mean": sum(aux_counts[s] for s in sids) / len(sids),
                             "underlying_fit_counts": [fits[s] for s in sids]})
    labels = [r["label"] for r in private_rows]
    depths = [r["auxiliary_tid_count_mean"] for r in private_rows]
    auc = float(roc_auc_score(labels, depths))
    r_value = float(pointbiserialr(labels, depths).statistic)
    audit_rows = json.loads((CURATION / "record_audit.json").read_text())
    exact_near = {int(r["activity_id"]) for r in audit_rows if r["standard_relation"] == "="
                  and r["standard_value"] is not None and 800 <= float(r["standard_value"]) <= 1250}
    near_rows = []
    for compound in usable:
        near_ids = sorted(set(int(a) for a in compound["activity_ids"]) & exact_near)
        if near_ids:
            near_rows.append({"compound_key": compound["compound_key"],
                              "activity_ids": near_ids,
                              "underlying_fit_counts": [fits[records_by_activity[a]] for a in near_ids]})
    H4 = {"per_source_row_auxiliary_tid_count": stats(list(aux_counts.values())),
          "per_source_row_fit_count_proxy": stats(list(fits.values())),
          "fit_depth_varies": len(set(fits.values())) > 1,
          "precision_caveat": "Per-range IC50 columns proxy underlying fit count; source does not independently certify repeat number per compound."}
    H5 = {"usable_compounds": len(private_rows), "auc_auxiliary_tid_count_predicting_hit": auc,
          "pointbiserial_r": r_value, "private_file_sha256": output("h5_compound_depth_labels.json", private_rows, True)}
    H6 = {"near_threshold_compounds": len(near_rows),
          "underlying_fit_count_distribution": dict(sorted(Counter(n for row in near_rows for n in row["underlying_fit_counts"]).items())),
          "private_file_sha256": output("h6_near_threshold.json", near_rows, True)}
    result = {"schema": "tnap_homogeneity_v2", "rule_sha256": RULE_HASH, "database_sha256": DB_HASH,
              "source_sha256": receipt["sha256"], "rows": len(rows),
              "H1": {"passed": H1, "rows_with_chosen_pair": sum({1, 2}.issubset({int(x["tid"]) for x in row["data"]}) for row in rows)},
              "H2": {"passed": H2, "aligned_from_tid_2": len(records) - len(bad_h2), "bad_activity_ids": bad_h2},
              "H3": {"passed": H3, "auxiliary_tid_count": len(auxiliary), "families": families,
                     "unknown_names": unknown, "single_target": one_target, "same_protocol": protocol_same},
              "H4": H4, "H5": H5, "H6": H6,
              "gate_passed": H1 and H2 and H3}
    output("tnap_homogeneity_v2.json", result)
    print(json.dumps({"H1": result["H1"], "H2": result["H2"], "H3": result["H3"],
                      "H4": {"fit_depth_varies": H4["fit_depth_varies"], "fit_depth": H4["per_source_row_fit_count_proxy"]},
                      "H5": {k: v for k, v in H5.items() if k != "private_file_sha256"},
                      "H6": {k: v for k, v in H6.items() if k != "private_file_sha256"}}, ensure_ascii=False))
    if not result["gate_passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
