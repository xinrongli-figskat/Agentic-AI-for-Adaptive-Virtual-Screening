"""Offline evaluator for the fixed six-assay Task 1 reference exercise."""
from __future__ import annotations

import csv
import hashlib
import json
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    lock = json.loads((HERE / "agent_lock.json").read_text(encoding="utf-8"))
    for rel, digest in lock["file_sha256"].items():
        assert sha(HERE / rel) == digest, rel
    progress = json.loads((HERE / "progress.json").read_text(encoding="utf-8"))
    refs = json.loads((HERE / "human_reference_postrun.json").read_text(encoding="utf-8"))
    assert progress["status"] == "complete_six_reference_assays"
    assert progress["api_attempts"] <= 30
    assert len(progress["candidates"]) == len(refs["rows"]) == 6
    assert len(progress["events"]) == progress["api_attempts"]
    for ref in refs["rows"]:
        assert sha(PROJECT / ref["source_path"]) == ref["source_sha256"]
    receipts = [json.loads(path.read_text(encoding="utf-8")) for path in sorted((HERE / "llm_receipts").glob("*.json"))]
    assert len(receipts) == progress["api_attempts"]
    assert all(r["candidate_assay_id"] in {x["assay_id"] for x in refs["rows"]} for r in receipts)
    for receipt in receipts:
        sent = json.dumps(receipt["request"], ensure_ascii=False)
        assert "human_reference_postrun" not in sent
        assert "human_reference_verdict" not in sent
        assert "existing_human_hold" not in sent
    reference_map = {r["assay_id"]: r for r in refs["rows"]}
    rows = []
    for candidate in progress["candidates"]:
        aid = candidate["assay_id"]
        ref = reference_map[aid]
        events = [e for e in progress["events"] if e["assay_id"] == aid]
        verdict = candidate["decision"]["verdict"]
        rows.append({"name": candidate["name"], "assay_id": aid,
                     "r3_rank": next(p["rank"] for p in json.loads((HERE / "inputs_locked.json").read_text())["packets"] if p["assay_id"] == aid),
                     "human_reference_verdict": ref["human_reference_verdict"],
                     "reference_strength": ref["reference_strength"],
                     "agent_source_status": candidate["source_assessment"]["status"],
                     "agent_verdict": verdict,
                     "agent_campaign_ready": candidate["decision"]["campaign_ready"],
                     "exact_agreement": verdict == ref["human_reference_verdict"],
                     "glm_attempts": len(events),
                     "returned_total_tokens": sum((e.get("usage") or {}).get("total_tokens", 0) for e in events),
                     "executed_actions": sum(e["status"] == "action_executed" for e in events),
                     "failed_or_masked_actions": sum(e["status"] != "action_executed" for e in events),
                     "reference_source_path": ref["source_path"],
                     "reference_source_sha256": ref["source_sha256"]})
    with (HERE / "agreement.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    formal = [r for r in rows if r["reference_strength"] != "provisional_source_endpoint_unresolved_not_final"]
    tp = sum(r["agent_verdict"] == "review_shortlist" and r["human_reference_verdict"] == "review_shortlist" for r in formal)
    fp = sum(r["agent_verdict"] == "review_shortlist" and r["human_reference_verdict"] != "review_shortlist" for r in formal)
    tn = sum(r["agent_verdict"] != "review_shortlist" and r["human_reference_verdict"] != "review_shortlist" for r in formal)
    fn = sum(r["agent_verdict"] != "review_shortlist" and r["human_reference_verdict"] == "review_shortlist" for r in formal)
    tokens = {key: sum((r.get("usage") or {}).get(key, 0) for r in receipts)
              for key in ("prompt_tokens", "completion_tokens", "total_tokens")}
    metric = {"formal_reference_n": len(formal), "provisional_reference_n": len(rows)-len(formal),
              "confusion_binary_shortlist_vs_hold_or_reject": {"TP": tp, "FP": fp, "TN": tn, "FN": fn},
              "precision": tp/(tp+fp) if tp+fp else None,
              "recall": tp/(tp+fn) if tp+fn else None,
              "exact_disposition_agreement": sum(r["exact_agreement"] for r in formal),
              "reference_positive_n": tp+fn,
              "api_attempts": progress["api_attempts"], "allowed_max_api_attempts": 30,
              "unused_api_budget": 30-progress["api_attempts"],
              "completed_candidate_n": len(rows),
              "mean_calls_per_completed_disposition": progress["api_attempts"]/len(rows),
              "all_actions_executed": all(e["status"] == "action_executed" for e in progress["events"]),
              "returned_usage": tokens,
              "mean_http_elapsed_seconds": statistics.mean(r["elapsed_seconds"] for r in receipts),
              "candidate_assays_outside_scope_called": sorted({r["candidate_assay_id"] for r in receipts} - {x["assay_id"] for x in rows}),
              "campaign_ready_promotions": sum(bool(r["agent_campaign_ready"]) for r in rows)}
    (HERE / "metrics.json").write_text(json.dumps(metric, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metric, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
