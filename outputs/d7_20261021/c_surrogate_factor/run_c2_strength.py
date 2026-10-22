"""Private, retrospective D7-C2 characterization; writes per-key scores privately."""
from __future__ import annotations

import hashlib
import json
import math
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

# Load the pinned, project-local runtime before importing scientific packages.
ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE / "runtime_packages"))

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.ensemble import GradientBoostingClassifier

PRIVATE = ROOT / "outputs/d7_20261021/c_surrogate_factor_private"
TNAP = ROOT / "data/benchmarks/tnap_chembl1738510_v1"
BACKUP = ROOT / ".sync_audit/backup_20261015_bbea8ee9/remote_snapshot.zip"
DYRK3_PUBLIC = "data/campaign_public/prefreeze_20261014T145140Z_6402306a507c6fd5/candidates.jsonl"
DYRK3_LABELS = "data/curation_private/prefreeze_20261014T145140Z_6402306a507c6fd5/oracle_labels.jsonl"
DYRK3_MANIFEST = "data/curation_private/frozen_dyrk3_v1/manifest.json"
SURROGATES = ("S_weak", "S_maccs", "S_incumbent", "S_strong")

from c1_surrogates import SurrogateBank, _fill_from_training


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_jsonl(blob: bytes):
    return [json.loads(line) for line in blob.splitlines() if line.strip()]


def load_inputs():
    tnap_manifest = json.loads((TNAP / "manifest.json").read_text(encoding="utf-8"))
    t_public = (TNAP / "public/candidates.jsonl").read_bytes()
    t_labels = (TNAP / "curation_private_labels/oracle_labels.jsonl").read_bytes()
    if sha(t_public) != tnap_manifest["public"]["sha256"] or sha(t_labels) != tnap_manifest["private"]["sha256"]:
        raise ValueError("TNAP frozen input hash mismatch")
    with zipfile.ZipFile(BACKUP) as archive:
        d_public = archive.read(DYRK3_PUBLIC)
        d_labels = archive.read(DYRK3_LABELS)
        d_manifest_bytes = archive.read(DYRK3_MANIFEST)
    d_manifest = json.loads(d_manifest_bytes)
    if sha(d_public) != d_manifest["data_sha256"]["public_candidates"]:
        raise ValueError("DYRK3 backup public input hash mismatch")
    if sha(d_labels) != d_manifest["data_sha256"]["private_labels"]:
        raise ValueError("DYRK3 backup private input hash mismatch")
    return {
        "TNAP": (t_public, t_labels, tnap_manifest, "local frozen pool"),
        "DYRK3": (d_public, d_labels, d_manifest, "hash-verified backup copy"),
    }


def fit_predict(bank: SurrogateBank, surrogate: str, train_keys: list[str], train_y: np.ndarray,
                test_keys: list[str]) -> np.ndarray:
    if surrogate == "S_incumbent":
        revealed = [{"compound_key": key, "outcome": int(value)}
                    for key, value in zip(train_keys, train_y)]
        scores = bank.incumbent.score_knn({"revealed": revealed})
        return np.asarray([scores[key] for key in test_keys], dtype=float)

    feature_name = surrogate
    matrix = bank.features[feature_name]
    tr_i = np.asarray([bank.index[key] for key in train_keys], dtype=int)
    te_i = np.asarray([bank.index[key] for key in test_keys], dtype=int)
    x_train, x_test, _ = _fill_from_training(matrix[tr_i], matrix[te_i])
    if surrogate == "S_weak":
        mean = x_train.mean(axis=0)
        scale = x_train.std(axis=0)
        scale[scale == 0] = 1.0
        x_train = (x_train - mean) / scale
        x_test = (x_test - mean) / scale
        model = LogisticRegression(C=1, solver="liblinear", random_state=0, max_iter=200)
    elif surrogate == "S_maccs":
        model = LogisticRegression(C=1, solver="liblinear", random_state=0, max_iter=200)
    elif surrogate == "S_strong":
        model = GradientBoostingClassifier(n_estimators=200, max_depth=3,
                                           learning_rate=0.1, random_state=0)
    else:
        raise ValueError(f"Unknown surrogate {surrogate}")
    model.fit(x_train, train_y)
    positive_index = list(model.classes_).index(1)
    return model.predict_proba(x_test)[:, positive_index]


def ef1(y: np.ndarray, scores: np.ndarray, keys: list[str]) -> float:
    n_top = max(1, math.ceil(0.01 * len(y)))
    selected = sorted(range(len(y)), key=lambda i: (-float(scores[i]), keys[i]))[:n_top]
    return (float(y[selected].mean()) / float(y.mean()))


def characterize(pool: str, public_bytes: bytes, label_bytes: bytes, manifest: dict, origin: str):
    candidates = read_jsonl(public_bytes)
    labels = read_jsonl(label_bytes)
    if any(set(row) != {"compound_key", "standardized_smiles"} for row in candidates):
        raise ValueError(f"{pool}: unexpected public schema")
    if any("compound_key" not in row or "outcome" not in row for row in labels):
        raise ValueError(f"{pool}: missing required private key/outcome fields")
    public_keys = [row["compound_key"] for row in candidates]
    label_keys = [row["compound_key"] for row in labels]
    if len(public_keys) != len(set(public_keys)) or len(label_keys) != len(set(label_keys)):
        raise ValueError(f"{pool}: duplicate compound key")
    if set(public_keys) != set(label_keys):
        raise ValueError(f"{pool}: public/private key sets differ")
    by_key = {row["compound_key"]: row for row in labels}
    keys = sorted(public_keys)
    y = np.asarray([int(by_key[key]["outcome"]) for key in keys], dtype=int)
    if not set(np.unique(y)).issubset({0, 1}) or len(np.unique(y)) != 2:
        raise ValueError(f"{pool}: outcomes must contain both binary classes")

    bank = SurrogateBank(candidates)
    key_to_y = dict(zip(keys, y.tolist()))
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=0)
    oof = {name: np.full(len(keys), np.nan, dtype=float) for name in SURROGATES}
    splits = list(cv.split(np.zeros(len(keys)), y))
    for train_idx, test_idx in splits:
        train_keys = [keys[int(i)] for i in train_idx]
        test_keys = [keys[int(i)] for i in test_idx]
        train_y = np.asarray([key_to_y[key] for key in train_keys], dtype=int)
        for name in SURROGATES:
            oof[name][test_idx] = fit_predict(bank, name, train_keys, train_y, test_keys)
    if any(np.isnan(scores).any() for scores in oof.values()):
        raise RuntimeError(f"{pool}: incomplete out-of-fold scores")

    aggregates = {}
    score_rows = []
    for name in SURROGATES:
        scores = oof[name]
        aggregates[name] = {
            "roc_auc": float(roc_auc_score(y, scores)),
            "ef1_percent": ef1(y, scores, keys),
        }
        for key, outcome, score in zip(keys, y.tolist(), scores.tolist()):
            score_rows.append({"pool": pool, "surrogate": name, "compound_key": key,
                               "outcome": outcome, "oof_score": score})
    ranked = sorted(SURROGATES, key=lambda name: (aggregates[name]["roc_auc"], name))
    strict_expected_order = list(SURROGATES)
    return {
        "pool": pool,
        "origin": origin,
        "candidate_count": len(candidates),
        "hit_count": int(y.sum()),
        "nonhit_count": int(len(y) - y.sum()),
        "public_sha256": sha(public_bytes),
        "private_sha256": sha(label_bytes),
        "manifest_source": manifest.get("schema"),
        "private_label_schema_fields": sorted(set().union(*(row.keys() for row in labels))),
        "private_labels_projected_to": ["compound_key", "outcome"],
        "metrics": aggregates,
        "observed_roc_auc_order": ranked,
        "expected_strict_order": strict_expected_order,
        "strict_order_pass": ranked == strict_expected_order,
        "private_oof_rows": score_rows,
    }


def main():
    env_lock_path = HERE / "C2_ENV_LOCK.json"
    env_lock_bytes = env_lock_path.read_bytes()
    env_lock = json.loads(env_lock_bytes)
    if env_lock.get("status") != "PRE_LABEL_ENVIRONMENT_LOCKED" or env_lock.get("labels_read") is not False:
        raise ValueError("Pre-label environment lock absent or invalid")
    if hashlib.sha256((HERE / "c1_surrogates.py").read_bytes()).hexdigest() != env_lock["C1_code_sha256"]:
        raise ValueError("C1 code changed after environment lock")
    inputs = load_inputs()
    results = {}
    for pool, (public, labels, manifest, origin) in inputs.items():
        results[pool] = characterize(pool, public, labels, manifest, origin)
    private_metrics = {
        "status": "C2_COMPLETE",
        "post_exposure": True,
        "utc": datetime.now(timezone.utc).isoformat(),
        "environment_lock_sha256": sha(env_lock_bytes),
        "runner_sha256": sha(Path(__file__).read_bytes()),
        "pools": results,
        "tier_b_stop": any(not results[pool]["strict_order_pass"] for pool in results),
        "interpretation": "Retrospective private characterization only; not a campaign and no model was selected from outcomes.",
    }
    PRIVATE.mkdir(parents=True, exist_ok=True)
    private_path = PRIVATE / "surrogate_strength.json"
    private_path.write_text(json.dumps(private_metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    public_metrics = {
        "status": "C2_COMPLETE",
        "post_exposure": True,
        "utc": private_metrics["utc"],
        "environment_lock_sha256": private_metrics["environment_lock_sha256"],
        "pools": {
            pool: {
                "candidate_count": results[pool]["candidate_count"],
                "hit_count": results[pool]["hit_count"],
                "nonhit_count": results[pool]["nonhit_count"],
                "metrics": results[pool]["metrics"],
                "observed_roc_auc_order": results[pool]["observed_roc_auc_order"],
                "expected_strict_order": results[pool]["expected_strict_order"],
                "strict_order_pass": results[pool]["strict_order_pass"],
            }
            for pool in results
        },
        "tier_b_stop": private_metrics["tier_b_stop"],
        "disclosure": "Aggregate AUC/EF1 only. Per-compound predictions and outcomes remain private.",
    }
    public_path = HERE / "C2_PUBLIC_SUMMARY.json"
    public_path.write_text(json.dumps(public_metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(public_metrics, ensure_ascii=False, indent=2))
    print("private_sha256:", sha(private_path.read_bytes()))
    print("public_sha256:", sha(public_path.read_bytes()))


if __name__ == "__main__":
    main()
