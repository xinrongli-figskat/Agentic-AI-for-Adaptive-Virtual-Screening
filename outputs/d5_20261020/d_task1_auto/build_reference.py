"""Seal existing human reference dispositions only AFTER six model judgments finish."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]

ROWS = [
    ("TNAP", "CHEMBL1738510", "review_shortlist", "final_limited_frozen",
     "outputs/d3_tnap_20261019/freeze_tnap_v1/pool_card.md"),
    ("ACC2", "CHEMBL3705476", "hold", "existing_human_hold",
     "outputs/brief/benchmark_build_progress_20261017.md"),
    ("TACE", "CHEMBL5733557", "hold", "existing_human_hold",
     "outputs/tace_source_value_review_20261017.md"),
    ("CPT2", "CHEMBL3431931", "hold", "existing_human_hold",
     "outputs/brief/benchmark_build_progress_20261017.md"),
    ("ACLY", "CHEMBL5738952", "hold", "existing_human_hold",
     "outputs/acly_source_value_review_20261017.md"),
    ("S1PR1", "CHEMBL5734042", "hold", "provisional_source_endpoint_unresolved_not_final",
     "outputs/r3_ranked_numeric_private_20261018_v2/provisional_shortlist.csv"),
]


def main():
    progress = json.loads((HERE / "progress.json").read_text(encoding="utf-8"))
    if progress["status"] != "complete_six_reference_assays" or not all(c["decision"] for c in progress["candidates"]):
        raise ValueError("Human reference cannot be loaded before six completed model judgments")
    if (HERE / "human_reference_postrun.json").exists():
        raise ValueError("Reference file already exists; no overwrite")
    refs = []
    for name, aid, verdict, strength, rel in ROWS:
        path = PROJECT / rel
        refs.append({"name": name, "assay_id": aid, "human_reference_verdict": verdict,
                     "reference_strength": strength, "source_path": rel,
                     "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    out = {"schema": "d5_existing_human_reference_v1",
           "built_after_all_model_judgments_at_utc": datetime.now(timezone.utc).isoformat(),
           "formal_metric_excludes_provisional_s1pr1": True,
           "model_packet_included_human_verdict": False, "rows": refs}
    (HERE / "human_reference_postrun.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"reference_rows": len(refs), "final_rows": 5,
                      "model_calls_before_reference": progress["api_attempts"]}))


if __name__ == "__main__":
    main()
