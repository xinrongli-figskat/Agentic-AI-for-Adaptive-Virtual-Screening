"""Add only S_morgan_logreg OOF metrics; reuse the five locked C2 values."""
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "outputs/d7_20261021/c_surrogate_factor/runtime_packages"))
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from outputs.d7_20261021.c_surrogate_factor_v2.run_c2v2 import load_inputs, read_jsonl
from outputs.d7_20261021.c_surrogate_factor_v2_orthogonal.orthogonal_proxy import OrthogonalProxy

PRIVATE = ROOT / "outputs/d7_20261021/c_surrogate_factor_v2_orthogonal_private"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def characterize(public, label_blob):
    candidates, label_rows = read_jsonl(public), read_jsonl(label_blob)
    keys = sorted(row["compound_key"] for row in candidates)
    labels = {row["compound_key"]: int(row["outcome"]) for row in label_rows}
    if len(keys) != len(set(keys)) or set(keys) != set(labels):
        raise ValueError("Public/private key mismatch")
    y = np.asarray([labels[key] for key in keys], dtype=int)
    proxy = OrthogonalProxy(candidates)
    features = proxy.morgan_sparse()
    oof = np.full(len(keys), np.nan)
    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
    for train, test in folds.split(np.zeros(len(keys)), y):
        model = LogisticRegression(C=1.0, solver="liblinear", random_state=0, max_iter=200)
        model.fit(features[train], y[train])
        positive = list(model.classes_).index(1)
        oof[test] = model.predict_proba(features[test])[:, positive]
    if np.isnan(oof).any():
        raise RuntimeError("Incomplete OOF")
    n_top = max(1, math.ceil(len(keys) * .01))
    top = sorted(range(len(keys)), key=lambda i: (-float(oof[i]), keys[i]))[:n_top]
    metric = {"roc_auc": float(roc_auc_score(y, oof)),
              "ef1_percent": float(y[top].mean() / y.mean())}
    private = [{"compound_key": key, "outcome": labels[key], "oof_score": float(oof[i])}
               for i, key in enumerate(keys)]
    return metric, private


def main():
    lock = json.loads((HERE / "C1_LOCK_v2.json").read_text())
    if lock["status"] != "C1_V2_LOCKED_PRE_NEW_PROXY_SCORES":
        raise RuntimeError("Missing pre-score lock")
    files = {
        "C1_v2_spec": HERE / "C1_SPEC_v2.md",
        "C1_v2_code": HERE / "orthogonal_proxy.py",
        "C2_v2_code": HERE / "run_c2_six.py",
        "D5_expanded_tools": ROOT / "outputs/d5_20261020/e_menu/expanded_tools.py",
    }
    for key, path in files.items():
        if sha(path) != lock["source_sha256"][key]:
            raise RuntimeError(f"Locked file changed: {key}")
    prior_path = ROOT / "outputs/d7_20261021/c_surrogate_factor_v2/C2V2_PUBLIC_SUMMARY.json"
    if sha(prior_path) != lock["source_sha256"]["C2_v2_public"]:
        raise RuntimeError("Previous C2 metrics changed")
    previous = json.loads(prior_path.read_text())
    private_results = {}
    public = {}
    for pool, (candidate_bytes, label_bytes) in load_inputs().items():
        metric, rows = characterize(candidate_bytes, label_bytes)
        private_results[pool] = rows
        metrics = dict(previous["pools"][pool]["metrics"])
        metrics["S_morgan_logreg"] = metric
        order = sorted(metrics, key=lambda name: (metrics[name]["roc_auc"], name))
        aucs = [item["roc_auc"] for item in metrics.values()]
        old_five = [item["roc_auc"] for item in previous["pools"][pool]["metrics"].values()]
        outlier = metric["roc_auc"] < min(old_five) - .15 or metric["roc_auc"] > max(old_five) + .15
        public[pool] = {"metrics": metrics, "observed_auc_rank_ascending": order,
                        "auc_span": max(aucs)-min(aucs), "new_logreg_outside_old_five_by_more_than_0_15": outlier}
        if pool == "TNAP":
            public[pool]["tier_b_pass"] = public[pool]["auc_span"] >= .05 and not outlier
    result = {"status": "C2_SIX_COMPLETE", "post_exposure": True,
              "utc": datetime.now(timezone.utc).isoformat(),
              "lock_sha256": sha(HERE / "C1_LOCK_v2.json"), "pools": public,
              "TNAP_tier_b_pass": public["TNAP"]["tier_b_pass"],
              "no_C3_started": True, "glm_calls": 0}
    PRIVATE.mkdir(parents=True, exist_ok=True)
    (PRIVATE / "C2_LOGREG_OOF_PRIVATE.json").write_text(json.dumps(private_results) + "\n", encoding="utf-8")
    out = HERE / "C2_SIX_PUBLIC.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"public": str(out), "sha256": sha(out), "TNAP": public["TNAP"],
                      "DYRK3": public["DYRK3"], "glm_calls": 0}, ensure_ascii=False))


if __name__ == "__main__":
    main()
