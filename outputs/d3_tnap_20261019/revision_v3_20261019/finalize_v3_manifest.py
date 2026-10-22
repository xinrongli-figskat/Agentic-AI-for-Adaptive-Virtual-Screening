"""Close the v3 audit without modifying either earlier failed audit."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EXPECTED = {
    ROOT / "BLOCKER.md": "f77718741153450bf8b01bc954f305f3fc49a5beb31cd531f90a611994c56451",
    ROOT / "tnap_homogeneity_assertion.json": "b4bb2d52646dc682362cadc28540716b8199855d955051fffd9d23056afa9ad8",
    ROOT / "reconciliation_summary.json": "b22d9ca229c8b264c19e3dba8a4b38af5b1246438e7382fc989df7d284c12e5f",
    ROOT / "revision_v2_20261019" / "tnap_homogeneity_v2.json": "ca2437c427357e29ba3ddce102ce36e8322a044399f5a6852cb070093d7501a6",
    HERE / "homogeneity_measurement_rule_v3.md": "680b48265d8d64f372df665f86592795a7e4e88b4e38ec0937a77ac0169384ec",
    HERE / "h3_family_report.json": "a24711e40e8c9fc5ed5f4a16790b869e3f07391e514b828b930f64c3019c74ae",
    HERE / "h7a_depth_meaning.json": "bd907d324395574310f96318b3fe24fd7dee4c6627c19a20668d7a6df741fa2b",
    HERE / "h7b_strata.json": "886c56c243883750dcc660f0ffda3baa4876eacc831106b71882b6f8b43a1f6d",
    HERE / "h7c_thin_ic50_support.json": "a8e3dc7a78d9e4ee19e2f5eed470ec483a2d6e2ce58c87063bc3aa4fc92c96fc",
    HERE / "h7d_near_threshold_depth.json": "042c0afebe206d171b40abf1abe6aba3f80704c7cf069d4cc437e2fe21dccb74",
    HERE / "d3_1_v3_decision.json": "56becc7420aed716c9624b0070871af506c10ba3116dddcf801c4c4d2e6c6eb1",
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    for path, expected in EXPECTED.items():
        assert sha(path) == expected, f"Immutable evidence changed: {path}"
    assert not (HERE / "MANIFEST.json").exists(), "v3 manifest already exists"
    decision = json.loads((HERE / "d3_1_v3_decision.json").read_text())
    assert decision["source_gap_class"] == "limited" and decision["h3_passed"]
    now = datetime.now(timezone.utc).isoformat()
    with (HERE / "RUN_LOG.md").open("a", encoding="utf-8", newline="\n") as out:
        out.write(f"- {now}: H3 reclassified 494/494 auxiliary tids into six same-protocol families, zero unmatched; H7 single-fit source support 73/73 exact rows; 485→462 reconciliation and earlier blocked assertions unchanged. Scientific classification `limited`, no campaign yet, GLM calls 0.\n")
    (HERE / "STATUS").write_text("done\n", encoding="utf-8", newline="\n")
    files = []
    for path in sorted(HERE.rglob("*")):
        if not path.is_file() or path.name == "MANIFEST.json":
            continue
        files.append({"path": path.relative_to(HERE).as_posix(), "bytes": path.stat().st_size,
                      "sha256": sha(path), "private": "_private_" in path.as_posix()})
    manifest = {"schema": "d3_tnap_h3_h7_v3_manifest_v1", "created_utc": now,
                "status": "done", "source_gap_class": "limited", "campaign_ready": False,
                "glm_calls": 0, "rule_sha256": EXPECTED[HERE / "homogeneity_measurement_rule_v3.md"],
                "prior_evidence_verified": {p.relative_to(ROOT).as_posix(): h for p, h in EXPECTED.items() if p != HERE / "homogeneity_measurement_rule_v3.md"},
                "self_excluded": True, "files": files}
    (HERE / "MANIFEST.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": "done", "manifest_sha256": sha(HERE / "MANIFEST.json"), "files": len(files), "utc": now}))


if __name__ == "__main__":
    main()
