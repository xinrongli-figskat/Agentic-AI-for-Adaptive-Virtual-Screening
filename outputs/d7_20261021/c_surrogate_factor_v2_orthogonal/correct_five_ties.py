"""Additive C3 five-menu aggregate correction for 0.05-hit floating ties."""
import copy
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / "outputs/d7_20261021/c_surrogate_factor/runtime_packages"))
from scipy.stats import spearmanr, rankdata

original_path = HERE / "C3_FIVE_PUBLIC_SUMMARY.json"
original_bytes = original_path.read_bytes()
original = json.loads(original_bytes)
corrected = copy.deepcopy(original)
point = corrected["TNAP_six_point_auc_vs_adaptive_gap"]
values = [round(float(value), 2) for value in point["adaptive_gap_H50"]]
rho = float(spearmanr(range(1, 7), values).statistic)
assert values == [2.15, 4.70, 3.50, 2.15, 1.95, 2.20]
assert abs(rho - (-0.2898855178262242)) < 1e-12
point["adaptive_gap_H50_rounded_to_0_01"] = values
point["gap_average_tie_ranks"] = [float(v) for v in rankdata(values)]
point["spearman_rho_original_raw_float"] = point["spearman_rho"]
point["spearman_rho"] = rho
point["tie_handling"] = "round H50 mean differences to 0.01, then average tied ranks"
corrected["status"] = "C3_FIVE_MENU_CPU_COMPLETE_TIE_CORRECTED"
corrected["correction_utc"] = datetime.now(timezone.utc).isoformat()
corrected["supersedes_aggregate_sha256"] = hashlib.sha256(original_bytes).hexdigest()
out = HERE / "C3_FIVE_PUBLIC_SUMMARY_v1_1.json"
if out.exists():
    raise FileExistsError(out)
out.write_text(json.dumps(corrected, indent=2, ensure_ascii=False,
                          sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
print(json.dumps({"output": str(out), "spearman_rho": rho,
                  "sha256": hashlib.sha256(out.read_bytes()).hexdigest()}))
