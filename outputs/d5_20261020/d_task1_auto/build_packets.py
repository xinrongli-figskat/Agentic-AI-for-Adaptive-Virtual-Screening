"""Seal six factual evidence packets from the R3 ranked queue, without reference verdicts."""
from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from gates import REFERENCE_IDS, numeric_gate

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
R3_SHA = "dfb3569217454cd73a6c60b69128988aa1f57dc9866b7949728954933add47b9"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def put(path, object):
    Path(path).write_text(json.dumps(object, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build():
    spec = json.loads((HERE / "evidence_inputs.json").read_text(encoding="utf-8"))
    ranked = PROJECT / spec["ranked_source"]
    if sha(ranked) != R3_SHA:
        raise ValueError("R3 ranked input changed; stop without sealing packets")
    rows = {r["assay_id"]: r for r in csv.DictReader(ranked.open(encoding="utf-8", newline=""))}
    ids = tuple(c["assay_id"] for c in spec["candidates"])
    if ids != REFERENCE_IDS or len(rows) != 62:
        raise ValueError("Reference IDs/order or R3 62-row queue changed")
    packets = []
    source_hashes = {}
    for entry in spec["candidates"]:
        aid = entry["assay_id"]
        source_refs = []
        for rel in entry["sources"]:
            path = PROJECT / rel
            digest = sha(path)
            source_hashes[rel] = digest
            source_refs.append({"project_path": rel, "sha256": digest})
        row = rows[aid]
        numeric = numeric_gate(row)
        if not numeric["pass"]:
            raise ValueError(f"Expected R3 numerical pass for {aid}")
        packets.append({
            "name": entry["name"], "assay_id": aid,
            "rank": int(row["rank"]), "target_id": row["target_id"],
            "target_name": row["target_name"], "source_tier": row["verified_source_tier"],
            "numeric": numeric,
            "counts": {"usable": int(row["N"]), "hit_support": int(row["K"]),
                       "measured_nonhit_support": int(row["measured_nonhit_support"])},
            "facts": entry["facts"], "sources": source_refs,
        })
    out = {"schema": "d5_task1_sealed_facts_v1", "post_exposure": True,
           "human_reference_verdicts_included": False, "all_r3_queue_count": len(rows),
           "evaluation_scope": "exactly six reference assays", "packets": packets}
    put(HERE / "inputs_locked.json", out)
    lock = {"locked_at_utc": datetime.now(timezone.utc).isoformat(),
            "evidence_inputs_sha256": sha(HERE / "evidence_inputs.json"),
            "ranked_r3_sha256": R3_SHA,
            "source_files_sha256": source_hashes,
            "inputs_locked_sha256": sha(HERE / "inputs_locked.json"),
            "note": "Factual packets exclude human verdicts. No GLM call made by this step."}
    put(HERE / "input_lock.json", lock)
    return lock


if __name__ == "__main__":
    print(json.dumps(build(), ensure_ascii=False, indent=2))
