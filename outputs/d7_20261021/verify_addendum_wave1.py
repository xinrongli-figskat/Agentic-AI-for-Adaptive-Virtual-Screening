"""Independent D7 addendum wave-one acceptance; never modifies prior receipts."""

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[1]
ADDENDUM_SHA = "fb5b81850f20aa7353ca564a6615f78f85f8694a05dad71af1189e5e7f36ced8"


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest_check(folder, name="MANIFEST.json"):
    manifest = folder / name
    body = json.loads(manifest.read_text(encoding="utf-8"))
    members = body.get("files", body.get("members"))
    assert members is not None
    for member in members:
        path = (folder / member["path"]).resolve()
        assert path.is_relative_to(folder.resolve()), member["path"]
        assert path.is_file(), path
        assert sha(path) == member["sha256"], path
        if "bytes" in member:
            assert path.stat().st_size == member["bytes"], path
    return {"members": len(members), "sha256": sha(manifest)}


def main():
    assert sha(BASE / "task_card_D7_addendum_20261021.md") == ADDENDUM_SHA
    lock = json.loads((BASE / "task_card_D7_addendum_lock.json").read_text(encoding="utf-8"))
    assert lock["sha256"] == ADDENDUM_SHA
    preflight = json.loads((BASE / "preflight_20261021T112208Z.json").read_text(encoding="utf-8"))
    assert preflight["passed"] and all(x["match"] for x in preflight["inputs"])
    assert len(preflight["inputs"]) == 11

    a_root = BASE / "a_headroom_bandit"
    a_new = a_root / "s2_s3_addendum"
    d_root = BASE / "d_identity_gate_v2"
    d_new = d_root / "revision_v3"
    e_root = BASE / "e_record_fixes"
    checked = {
        "a_previous": manifest_check(a_root / "revision_11field"),
        "a_addendum": manifest_check(a_root, "MANIFEST_S2_S3.json"),
        "d_previous": manifest_check(d_root),
        "d_addendum": manifest_check(d_new),
        "e_previous": manifest_check(e_root),
    }
    assert checked["d_previous"]["sha256"] == "befdbd58888e50cf7e0793f101db94997634eb82ab2c118f917a6b2637a6c367"
    assert checked["d_addendum"]["sha256"] == "83153b955623689771028f8794696bdd2db096f5f7deba2fefb013693dc9544c"
    assert checked["a_addendum"]["sha256"] == "b3a06493f4776beaf643c295f1f3d0605e86be98aecfc668f10f3ea687f3b7e1"

    d_lock = json.loads((d_new / "rule_v3_lock.json").read_text(encoding="utf-8"))
    d_summary = json.loads((d_new / "credential_summary.json").read_text(encoding="utf-8"))
    d_verify = json.loads((d_new / "independent_verification.json").read_text(encoding="utf-8"))
    assert d_lock["addendum_sha256"] == ADDENDUM_SHA
    assert d_lock["locked_utc"] < d_summary["measurement_started_utc"]
    assert d_summary["candidate_rows"] == 62 and d_summary["support_identity_count"] == 25813
    assert d_summary["assays_with_src37"] == 43
    assert d_summary["multi_molregno_count"] == 5
    assert d_summary["category_counts"] == {"single_source": 25036, "full_match": 701, "skeleton_only": 76}
    assert d_summary["campaign_ready_count"] == 0 and d_summary["glm_calls"] == 0
    assert d_verify["TACE_false"] and d_verify["TNAP_true"]
    assert d_verify["old_manifest_24_members_unchanged"] and d_verify["gate_boundary_cases"] >= 8
    credentials = list(csv.DictReader((d_new / "credential_62.csv").open(encoding="utf-8", newline="")))
    decisions = list(csv.DictReader((d_new / "gate_decisions_62.csv").open(encoding="utf-8", newline="")))
    assert len(credentials) == len(decisions) == 62
    assert sum(int(r["multi_molregno_count"]) for r in credentials) == 5
    for credential, decision in zip(credentials, decisions):
        assert credential["assay_id"] == decision["assay_id"]
        assert abs(sum(float(credential[f"{name}_frac"]) for name in
                       ("full_match", "skeleton_only", "single_source", "unresolvable")) - 1) < 1e-9
        tiers = json.loads(credential["involved_source_tiers"])
        checks = {"T1": float(credential["structure_resolvable_frac"]) >= .95,
                  "T2": float(credential["full_match_frac"]) >= .50,
                  "T3": float(credential["full_match_frac"]) >= .33}
        expected = float(credential["skeleton_only_frac"]) < .25 and all(checks[t] for t in tiers)
        assert decision["shortlist_permitted"].lower() == str(expected).lower()
        assert decision["campaign_ready"].lower() == "false"
    by_id = {row["assay_id"]: row for row in decisions}
    assert by_id["CHEMBL5733557"]["shortlist_permitted"].lower() == "false"
    assert by_id["CHEMBL1738510"]["shortlist_permitted"].lower() == "true"
    unseen = json.loads((d_new / "unseen_set_lock.json").read_text(encoding="utf-8"))
    assert len(unseen["assay_ids"]) == 8
    assert unseen["assay_ids"] == [row["assay_id"] for row in credentials
                                    if row["assay_id"] not in unseen["excluded_reference_assays"]][:8]

    a_lock = json.loads((a_new / "execution_lock_v2.json").read_text(encoding="utf-8"))
    a_gate = json.loads((a_new / "s2_gate_reanalysis.json").read_text(encoding="utf-8"))
    variance = json.loads((a_new / "variance_estimate_audit.json").read_text(encoding="utf-8"))
    assert a_lock["inputs"]["addendum"]["sha256"] == ADDENDUM_SHA
    assert a_lock["utc"] < a_gate["utc"]
    assert a_gate["resamples"] == 10000 and a_gate["threshold"] == 2.0
    assert a_gate["glm_calls"] == variance["glm_calls"] == 0
    assert {(r["pool"], r["representation"]) for r in a_gate["rows"] if r["new_gate_pass"]} == {
        ("tnap", "bit"), ("tnap", "count")}
    assert all(r["benefit_claim_status"] == "BLOCKED_variance_definition_not_established"
               for r in variance["rows"])
    assert variance["paired_difference_sample_sd"] > 4.20
    assert (a_root / "PREREGISTRATION_OUTCOMES.md").is_file()

    receipt = {
        "utc": datetime.now(timezone.utc).isoformat(), "post_exposure": True,
        "status": "ADDENDUM_WAVE1_VERIFIED", "preflight_inputs": 11,
        "manifest_checks": checked, "credential_rows": 62, "support_identities": 25813,
        "source_37_assays": 43, "TACE_false": True, "TNAP_true": True,
        "s2_eligible_existing_D5_cells": ["tnap_bit", "tnap_count"],
        "S3_benefit_claim_blocked_pending_D7_B": True,
        "glm_calls_so_far_in_D7_addendum": 0,
        "next_stage": "B_model_variance_and_C_surrogate_CPU",
        "campaign_ready": False,
    }
    path = BASE / "d7_addendum_wave1_verification.json"
    assert not path.exists(), path
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == "__main__":
    main()
