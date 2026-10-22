"""Deterministic D5 Task 1 action and admission preconditions.

The model may interpret source evidence, but this module alone controls which
action can execute. It never promotes a draft shortlist to campaign-ready.
"""
from __future__ import annotations

import math

STAGES = ("inspect_metadata", "read_evidence", "assess_source", "decide_assay")
REFERENCE_IDS = (
    "CHEMBL1738510", "CHEMBL3705476", "CHEMBL5733557",
    "CHEMBL3431931", "CHEMBL5738952", "CHEMBL5734042",
)


def numeric_gate(row: dict) -> dict:
    """Re-evaluate the fixed R3 numeric checks; never treat them as source approval."""
    n, hits, nonhits = (int(row[key]) for key in ("N", "K", "measured_nonhit_support"))
    checks = {
        "pool_ge_250": n >= 250,
        "hits_ge_30": hits >= 30,
        "measured_nonhits_ge_100": nonhits >= 100,
        "largest_cluster_le_025": float(row["largest_cluster_fraction"]) <= .25,
        "scaffolds_ge_10": int(row["scaffold_bucket_count_including_acyclic"]) >= 10,
        "query_fraction_le_020": 50 / n <= .20,
        "p_single_class10_le_05": float(row["P_single_class10"]) <= .5,
    }
    assert hits + nonhits == n, "R3 supported-class reconciliation failed"
    assert all(math.isfinite(float(row[key])) for key in ("largest_cluster_fraction", "P_single_class10"))
    return {"checks": checks, "pass": all(checks.values())}


def allowed_actions(candidate: dict) -> tuple[str, ...]:
    """One legal stage at a time prevents premature curate/decide calls."""
    if candidate["assay_id"] not in REFERENCE_IDS:
        return ()
    stage = int(candidate.get("stage", 0))
    if not 0 <= stage <= len(STAGES):
        return ()
    if stage == len(STAGES):
        return ()
    if stage == 3 and not candidate.get("source_assessment"):
        return ()
    return (STAGES[stage],)


def validate_action(candidate: dict, decision: dict) -> None:
    allowed = allowed_actions(candidate)
    if not allowed or decision.get("action") not in allowed:
        raise ValueError(f"Action masked; allowed={allowed}")
    args = decision.get("arguments")
    if not isinstance(args, dict) or args.get("assay_id") != candidate["assay_id"]:
        raise ValueError("Wrong assay or missing arguments")
    if not isinstance(decision.get("reason"), str) or len(decision["reason"].strip()) < 8:
        raise ValueError("A substantive reason is required")
    action = allowed[0]
    keys = {
        "inspect_metadata": {"assay_id"},
        "read_evidence": {"assay_id"},
        "assess_source": {"assay_id", "status", "endpoint", "construct_or_receptor"},
        "decide_assay": {"assay_id", "verdict"},
    }[action]
    if set(args) != keys:
        raise ValueError(f"Wrong action schema for {action}: {sorted(set(args) ^ keys)}")
    if action == "assess_source":
        if args["status"] not in ("limited", "unresolved", "reject"):
            raise ValueError("Unknown source status")
        if not all(isinstance(args[k], str) and args[k].strip() for k in ("endpoint", "construct_or_receptor")):
            raise ValueError("Endpoint and construct assessment required")
    if action == "decide_assay":
        if args["verdict"] not in ("review_shortlist", "hold", "reject"):
            raise ValueError("Unknown disposition")
        if args["verdict"] == "review_shortlist" and not candidate["numeric"]["pass"]:
            raise ValueError("Cannot shortlist without numeric gate")
        if args["verdict"] == "review_shortlist" and candidate["source_assessment"]["status"] != "limited":
            raise ValueError("Cannot shortlist with unresolved/rejected source status")


def apply_action(candidate: dict, decision: dict) -> dict:
    validate_action(candidate, decision)
    action, args = decision["action"], decision["arguments"]
    if action == "assess_source":
        candidate["source_assessment"] = {**args, "reason": decision["reason"]}
    elif action == "decide_assay":
        candidate["decision"] = {"verdict": args["verdict"], "reason": decision["reason"],
                                 "campaign_ready": False,
                                 "scope": "draft source judgment; separate human scientific review required"}
    candidate["stage"] += 1
    return candidate
