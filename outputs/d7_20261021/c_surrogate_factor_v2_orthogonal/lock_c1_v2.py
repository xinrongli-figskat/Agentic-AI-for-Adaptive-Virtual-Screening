"""Write the additive C1 lock without reading private outcomes."""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "outputs/d7_20261021/c_surrogate_factor/runtime_packages"))
import numpy
import rdkit
import scipy
import sklearn


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    target = HERE / "C1_LOCK_v2.json"
    if target.exists():
        raise FileExistsError(target)
    previous = json.loads((ROOT / "outputs/d7_20261021/c_surrogate_factor_v2/C2V2_ENV_LOCK.json").read_text())
    versions = {"python": sys.version.split()[0], "rdkit": rdkit.__version__,
                "scikit-learn": sklearn.__version__, "scipy": scipy.__version__,
                "numpy": numpy.__version__}
    if versions != previous["runtime"]:
        raise RuntimeError(f"Runtime changed since C2-v2: {versions}")
    sources = {
        "C1_v1_spec": ROOT / "outputs/d7_20261021/c_surrogate_factor/C1_SPEC.md",
        "C1_v1_code": ROOT / "outputs/d7_20261021/c_surrogate_factor/c1_surrogates.py",
        "C2_v2_lock": ROOT / "outputs/d7_20261021/c_surrogate_factor_v2/C2V2_ENV_LOCK.json",
        "C2_v2_public": ROOT / "outputs/d7_20261021/c_surrogate_factor_v2/C2V2_PUBLIC_SUMMARY.json",
        "D5_expanded_tools": ROOT / "outputs/d5_20261020/e_menu/expanded_tools.py",
        "numerical_tools": ROOT / "outputs/campaign_v0/numerical_tools.py",
        "C1_v2_spec": HERE / "C1_SPEC_v2.md",
        "C1_v2_code": HERE / "orthogonal_proxy.py",
        "C2_v2_code": HERE / "run_c2_six.py",
    }
    data = {"status": "C1_V2_LOCKED_PRE_NEW_PROXY_SCORES", "post_exposure": True,
            "utc": datetime.now(timezone.utc).isoformat(), "labels_read_by_this_lock": False,
            "runtime": versions,
            "source_sha256": {key: sha(path) for key, path in sources.items()},
            "D5_actual_logreg_max_iter": 200,
            "task_card_parenthetical_claim_of_default_100": "conflicts with D5 source; preserve D5 exact behavior",
            "existing_four_C2_metrics_reused": True,
            "existing_morgan_gbdt_C2_metrics_reused": True,
            "new_metric_to_compute": "S_morgan_logreg"}
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"lock": str(target), "sha256": sha(target), "utc": data["utc"],
                      "labels_read": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
