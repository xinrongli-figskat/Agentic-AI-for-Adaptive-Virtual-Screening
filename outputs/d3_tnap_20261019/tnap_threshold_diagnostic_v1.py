"""D3 descriptive [800,1250] nM re-score of saved queries only."""
import hashlib
import json
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT / "outputs/d3_tnap_20261019"
CURATION=ROOT / "data/curation_private/chembl37_batch_curations/chembl37_batch_curation_d1d3b87ef2b3ea4e/CHEMBL1738510/compounds_private.json"
RUNS=BASE / "d3_6_runs_private_20261019"
OUT=BASE / "d3_6_threshold_diagnostic"
PRIVATE=BASE / "d3_6_threshold_diagnostic_private_20261019"
EXPECTED_CUR="db688a4a9814d9fb2dd7238a39075ee41f72d1da7c3ba4934ec8835bd2285c73"
EXPECTED_RUN_MANIFEST=""
ARMS=("random","structure_prior","label_shuffle","fixed","fixed_schedule","rule_adaptive_v2","forced_random_coldstart")


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+"\n",encoding="utf-8",newline="\n")


def main():
    assert sha(CURATION)==EXPECTED_CUR
    assert not OUT.exists() and not PRIVATE.exists()
    compounds=json.loads(CURATION.read_text())
    usable={c["compound_key"]:c for c in compounds if c["usable_for_prototype_review"]}
    assert len(usable)==462
    labels={json.loads(line)["compound_key"]:json.loads(line)["outcome"] for line in (BASE/"freeze_tnap_v1_private_labels/oracle_labels.jsonl").read_text().splitlines()}
    assert set(labels)==set(usable)
    near_pool={k for k,c in usable.items() if c["exact_min_nM"] is not None and c["exact_max_nM"] is not None
               and float(c["exact_min_nM"])==float(c["exact_max_nM"]) and 800<=float(c["exact_min_nM"])<=1250}
    # H6 counted any near-threshold exact source record (13 identities).
    # The DYRK3 diagnostic's stricter unique-exact compound rule gives 12;
    # one identity has nonidentical exact measurements and stays separate.
    h6=json.loads((BASE/"revision_v2_20261019/d3_1_v2_private_20261019/h6_near_threshold.json").read_text())
    assert len(h6)==13 and len(near_pool)==12
    rows=[]
    for path in (RUNS/f"{arm}_{rep}_seed{seed}.json" for rep in ("bit","count") for seed in range(20) for arm in ARMS):
        saved=json.loads(path.read_text())
        info=saved["summary"]
        selected=[k for step in saved["result"]["trajectory"] for k in step["selection"]]
        assert len(selected)==len(set(selected))==50
        groups=Counter()
        for key in selected:
            c=usable[key]; low,high=c["exact_min_nM"],c["exact_max_nM"]
            if low is None or high is None or float(low)!=float(high):kind="censored_or_not_unique_exact"
            elif 800<=float(low)<=1250:kind="near_exact"
            else:kind="far_exact"
            groups[kind+"_count"]+=1
            groups[kind+"_hits"]+=labels[key]
        assert sum(groups[k+"_count"] for k in ("near_exact","far_exact","censored_or_not_unique_exact"))==50
        assert sum(groups[k+"_hits"] for k in ("near_exact","far_exact","censored_or_not_unique_exact"))==info["H50"]
        rows.append({"representation":info["representation"],"seed":info["seed"],"arm":info["arm"],**groups})
    assert len(rows)==280
    OUT.mkdir();PRIVATE.mkdir()
    dump(PRIVATE/"per_run.json",rows)
    aggregate={"schema":"tnap_d3_threshold_diagnostic_v1","created_utc":datetime.now(timezone.utc).isoformat(),
      "post_exposure":True,"description":"Descriptive re-score of existing selections only; no threshold, outcome, or campaign changed.",
      "interval_nM":[800,1250],"source_record_near_compound_count":len(h6),
      "unique_exact_near_pool_count":len(near_pool),"runs":len(rows),"glm_calls":0,"arms":{}}
    for rep in ("bit","count"):
      aggregate["arms"][rep]={}
      for arm in ARMS:
        subset=[r for r in rows if r["representation"]==rep and r["arm"]==arm]
        aggregate["arms"][rep][arm]={key:statistics.mean(r.get(key,0) for r in subset)
          for key in ("near_exact_count","near_exact_hits","far_exact_count","far_exact_hits","censored_or_not_unique_exact_count","censored_or_not_unique_exact_hits")}
    dump(OUT/"aggregate.json",aggregate)
    (OUT/"STATUS").write_text("done\n",encoding="utf-8",newline="\n")
    (OUT/"README.md").write_text("# TNAP near-threshold diagnostic\n\nH6 found 13 usable identities with at least one exact source record in [800,1250] nM. Under the inherited DYRK3 diagnostic's stricter unique-exact compound rule, 12 qualify; one has nonidentical exact values and is categorized separately. This only re-scores existing queried compounds. Censored or discordant exact values are separate. No labels or queries were changed; compound-level run breakdown remains in the adjacent ignored `_private_` directory. This is descriptive, not a second campaign.\n",encoding="utf-8",newline="\n")
    dump(OUT/"MANIFEST.json",{"schema":"tnap_d3_threshold_diagnostic_manifest_v1","self_excluded":True,
      "source_curation_sha256":sha(CURATION),"run_manifest_sha256":sha(RUNS/"MANIFEST.json"),
      "private_per_run_sha256":sha(PRIVATE/"per_run.json"),
      "files":[{"path":p.name,"sha256":sha(p)} for p in OUT.iterdir() if p.is_file() and p.name!="MANIFEST.json"]})
    print(json.dumps({"status":"done","near_pool":len(near_pool),"manifest_sha256":sha(OUT/"MANIFEST.json")}))


if __name__=="__main__":main()
