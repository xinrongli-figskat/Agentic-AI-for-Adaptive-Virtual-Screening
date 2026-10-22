"""Document order-dependent Butina count and seal the pre-freeze D3-2 record."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STAGE = ROOT / "outputs/d3_tnap_20261019/d3_2_pool"
POOL = ROOT / "data/benchmarks/tnap_chembl1738510_v1"
PRIOR_MANIFEST = "b5ebaac3d30dad085b15230fbea2596c4a40fb54eec8988fe1e461f773f00cf0"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    manifest_path = POOL / "manifest.json"
    assert sha(manifest_path) == PRIOR_MANIFEST, "Only the initial, unfrozen pool can be amended"
    qualification = json.loads((STAGE / "qualification.json").read_text())
    assert qualification["all_checks_pass"]
    assert qualification["butina_cluster_count"] == 310
    card = STAGE / "pool_card.md"
    with card.open("a", encoding="utf-8", newline="\n") as out:
        out.write("\nIndependent Butina re-clustering yielded 310 clusters, versus 308 in the prior curation file. Butina cluster partitions can change with input ordering and tied centroid choices. The predeclared gate is the largest-cluster fraction, which exactly agrees in both computations (11/462); the count difference is recorded and is not used to tune the pool.\n")
    manifest = json.loads(manifest_path.read_text())
    manifest["pool_card_sha256"] = sha(card)
    manifest["pre_freeze_amendment"] = {"prior_manifest_sha256": PRIOR_MANIFEST,
        "reason": "Disclose the 310 versus 308 order-sensitive Butina cluster count before freezing; no candidate or label changed."}
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    now = datetime.now(timezone.utc).isoformat()
    with (STAGE / "RUN_LOG.md").open("a", encoding="utf-8", newline="\n") as out:
        out.write(f"{now}: Pre-freeze amendment documented Butina count 310 versus 308; same maximum cluster 11/462. Prior pool manifest SHA256 {PRIOR_MANIFEST}; amended SHA256 {sha(manifest_path)}. No public/label rows changed.\n")
    files = []
    for p in [ROOT / "outputs/d3_tnap_20261019/build_tnap_pool_v1.py", Path(__file__),
              STAGE / "qualification.json", STAGE / "pool_card.md", STAGE / "RUN_LOG.md", STAGE / "STATUS",
              POOL / "public/candidates.jsonl", POOL / "curation_private_labels/oracle_labels.jsonl", manifest_path]:
        files.append({"path": str(p.relative_to(ROOT)).replace("\\", "/"), "bytes": p.stat().st_size,
                      "sha256": sha(p), "private": "_private_" in str(p)})
    stage_manifest = {"schema": "tnap_d3_2_stage_manifest_v1", "created_utc": now,
                      "status": "done", "self_excluded": True, "glm_calls": 0, "files": files}
    p = STAGE / "MANIFEST.json"
    assert not p.exists()
    p.write_text(json.dumps(stage_manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": "done", "pool_manifest_sha256": sha(manifest_path),
                      "stage_manifest_sha256": sha(p), "utc": now}))


if __name__ == "__main__":
    main()
