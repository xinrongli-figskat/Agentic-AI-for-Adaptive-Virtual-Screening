"""Add S_morgan_gbdt and publish aggregate-only measured AUC ranks."""
from __future__ import annotations

import hashlib
import json
import math
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "outputs/d7_20261021/c_surrogate_factor/runtime_packages"))
import numpy as np
from rdkit import DataStructs
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from outputs.d7_20261021.c_surrogate_factor.c1_surrogates import SurrogateBank

TNAP = ROOT / "data/benchmarks/tnap_chembl1738510_v1"
BACKUP = ROOT / ".sync_audit/backup_20261015_bbea8ee9/remote_snapshot.zip"
DYRK3_PUBLIC = "data/campaign_public/prefreeze_20261014T145140Z_6402306a507c6fd5/candidates.jsonl"
DYRK3_LABELS = "data/curation_private/prefreeze_20261014T145140Z_6402306a507c6fd5/oracle_labels.jsonl"
DYRK3_MANIFEST = "data/curation_private/frozen_dyrk3_v1/manifest.json"
OLD_SUMMARY = ROOT / "outputs/d7_20261021/c_surrogate_factor/C2_PUBLIC_SUMMARY.json"
PRIVATE_DIR = ROOT / "outputs/d7_20261021/c_surrogate_factor_v2_private"


def sha(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def read_jsonl(blob: bytes):
    return [json.loads(line) for line in blob.splitlines() if line.strip()]


def load_inputs():
    t_manifest = json.loads((TNAP / "manifest.json").read_text(encoding="utf-8"))
    t_pub = (TNAP / "public/candidates.jsonl").read_bytes()
    t_lab = (TNAP / "curation_private_labels/oracle_labels.jsonl").read_bytes()
    if sha(t_pub) != t_manifest["public"]["sha256"] or sha(t_lab) != t_manifest["private"]["sha256"]:
        raise ValueError("TNAP frozen input hash mismatch")
    with zipfile.ZipFile(BACKUP) as z:
        d_pub, d_lab, dm = z.read(DYRK3_PUBLIC), z.read(DYRK3_LABELS), z.read(DYRK3_MANIFEST)
    d_manifest = json.loads(dm)
    if sha(d_pub) != d_manifest["data_sha256"]["public_candidates"] or sha(d_lab) != d_manifest["data_sha256"]["private_labels"]:
        raise ValueError("DYRK3 backup input hash mismatch")
    return {"TNAP": (t_pub, t_lab), "DYRK3": (d_pub, d_lab)}


def ef1(y, scores, keys):
    n = max(1, math.ceil(0.01 * len(y)))
    chosen = sorted(range(len(y)), key=lambda i: (-float(scores[i]), keys[i]))[:n]
    return float(np.mean(y[chosen]) / np.mean(y))


def run_pool(pool, public_bytes, labels_bytes):
    candidates, labels = read_jsonl(public_bytes), read_jsonl(labels_bytes)
    keys = sorted(row["compound_key"] for row in candidates)
    by_label = {row["compound_key"]: row for row in labels}
    if len(keys) != len(set(keys)) or set(keys) != set(by_label):
        raise ValueError(f"{pool}: public/private key mismatch")
    if any(set(row) != {"compound_key", "standardized_smiles"} for row in candidates):
        raise ValueError(f"{pool}: public schema mismatch")
    y = np.asarray([int(by_label[key]["outcome"]) for key in keys], dtype=int)
    if set(np.unique(y)) != {0, 1}:
        raise ValueError(f"{pool}: both classes required")
    bank = SurrogateBank(candidates)
    fp_matrix = np.zeros((len(keys), 2048), dtype=np.uint8)
    for i, key in enumerate(keys):
        fp = bank.incumbent.fingerprints[key]
        for bit in fp.GetOnBits():
            fp_matrix[i, bit] = 1
    index = {key: i for i, key in enumerate(keys)}
    oof = np.full(len(keys), np.nan, dtype=float)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
    for train_i, test_i in cv.split(np.zeros(len(keys)), y):
        model = GradientBoostingClassifier(n_estimators=200, max_depth=3,
                                           learning_rate=0.1, random_state=0)
        model.fit(fp_matrix[train_i], y[train_i])
        pos = list(model.classes_).index(1)
        oof[test_i] = model.predict_proba(fp_matrix[test_i])[:, pos]
    if np.isnan(oof).any():
        raise RuntimeError("Incomplete OOF predictions")
    result = {"candidate_count": len(keys), "hit_count": int(y.sum()),
              "nonhit_count": int(len(y)-y.sum()), "roc_auc": float(roc_auc_score(y, oof)),
              "ef1_percent": ef1(y, oof, keys)}
    return result, [{"pool": pool, "compound_key": key, "outcome": int(out),
                     "oof_score": float(score)} for key, out, score in zip(keys, y, oof)]


def main():
    lock_path = HERE / "C2V2_ENV_LOCK.json"
    lock_bytes = lock_path.read_bytes()
    lock = json.loads(lock_bytes)
    if lock.get("status") != "C2V2_PRE_SCORE_LOCKED" or lock.get("labels_read") is not False:
        raise ValueError("C2 v2 pre-score lock missing")
    for path_key, filepath in (("C1_code_sha256", ROOT / "outputs/d7_20261021/c_surrogate_factor/c1_surrogates.py"),
                               ("NumericalTools_sha256", ROOT / "outputs/campaign_v0/numerical_tools.py"),
                               ("C2v1_public_summary_sha256", OLD_SUMMARY)):
        if sha(filepath.read_bytes()) != lock[path_key]:
            raise ValueError(f"Locked input changed: {path_key}")
    old = json.loads(OLD_SUMMARY.read_text(encoding="utf-8"))
    results = {}
    private_rows = []
    for pool, (pub, lab) in load_inputs().items():
        new_metric, rows = run_pool(pool, pub, lab)
        private_rows.extend(rows)
        old_pool = old["pools"][pool]
        proxies = {name: {"roc_auc": float(old_pool["metrics"][name]["roc_auc"]),
                          "ef1_percent": float(old_pool["metrics"][name]["ef1_percent"])}
                   for name in ("S_weak", "S_maccs", "S_incumbent", "S_strong")}
        proxies["S_morgan_gbdt"] = {"roc_auc": new_metric["roc_auc"], "ef1_percent": new_metric["ef1_percent"]}
        ranks = sorted(proxies, key=lambda name: (proxies[name]["roc_auc"], name))
        result = {"candidate_count": new_metric["candidate_count"], "hit_count": new_metric["hit_count"],
                  "nonhit_count": new_metric["nonhit_count"], "metrics": proxies,
                  "observed_auc_rank_ascending": ranks,
                  "auc_span": max(v["roc_auc"] for v in proxies.values()) - min(v["roc_auc"] for v in proxies.values())}
        if pool == "TNAP":
            ref_auc = [proxies[n]["roc_auc"] for n in ("S_weak", "S_maccs", "S_incumbent", "S_strong")]
            new_auc = proxies["S_morgan_gbdt"]["roc_auc"]
            result["tier_b"] = {"auc_span_ge_0_05": result["auc_span"] >= 0.05,
                                "morgan_auc_outside_reference_range_by_more_than_0_15":
                                    new_auc < min(ref_auc)-0.15 or new_auc > max(ref_auc)+0.15,
                                "pass": result["auc_span"] >= 0.05 and not (new_auc < min(ref_auc)-0.15 or new_auc > max(ref_auc)+0.15)}
        results[pool] = result
    public_pools = {pool: {"metrics": result["metrics"],
                           "observed_auc_rank_ascending": result["observed_auc_rank_ascending"],
                           "auc_span": result["auc_span"],
                           **({"tier_b": result["tier_b"]} if pool == "TNAP" else {})}
                    for pool, result in results.items()}
    public = {"status": "C2V2_COMPLETE", "post_exposure": True,
              "utc": datetime.now(timezone.utc).isoformat(), "C2v2_lock_sha256": sha(lock_bytes),
              "ranking_rule": "measured ROC-AUC ascending; independent of campaign outcomes and fixed before any C3 campaign",
              "pools": public_pools, "TNAP_tier_b_pass": results["TNAP"]["tier_b"]["pass"],
              "DYRK3_role": "signal-poor CPU negative control; excluded from TNAP factor conclusions",
              "public_scope": "Five proxy AUC/EF1 values and observed rank only; no per-compound scores."}
    private = {"status": "C2V2_PRIVATE_COMPLETE", "post_exposure": True,
               "utc": public["utc"], "C2v2_lock_sha256": public["C2v2_lock_sha256"],
               "per_compound_oof_scores": private_rows, "pools": results}
    PRIVATE_DIR.mkdir(parents=True, exist_ok=True)
    prv = PRIVATE_DIR / "C2V2_OOF_PRIVATE.json"
    prv.write_text(json.dumps(private, indent=2) + "\n", encoding="utf-8")
    out = HERE / "C2V2_PUBLIC_SUMMARY.json"
    out.write_text(json.dumps(public, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(public, indent=2))
    print("private_sha256:", sha(prv.read_bytes()))
    print("public_sha256:", sha(out.read_bytes()))


if __name__ == "__main__":
    main()
