"""Record the user-authorized S-1 rule v3 before producing new measurements."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
ADDENDUM=ROOT.parents[1]/'task_card_D7_addendum_20261021.md'
expected='fb5b81850f20aa7353ca564a6615f78f85f8694a05dad71af1189e5e7f36ced8'
raw=ADDENDUM.read_bytes()
assert hashlib.sha256(raw).hexdigest()==expected
start=raw.index('# S-1：'.encode())
end=raw.index('# S-2：'.encode(),start)
rule=raw[start:end]
assert not (ROOT/'rule_v3_lock.json').exists()
(ROOT/'rule_v3_authorized.md').write_bytes(rule)
spec={
 'version':'D7-D identity credential v3', 'post_exposure':True,
 'unit':'saved_standardized_support_identity',
 'denominator':'full_R3_support_identity_count',
 'source_groups':{'G_patent_agg':[37,38],'G_deposited':[7,21],'G_lit':[1]},
 'other_global_sources':'one independent group per src_id',
 'source_tier_scope':'assay_supporting_activity_provenance',
 'credential_scope':'global_compound_records_union_across_constituent_molregnos',
 'source_tiers':{'T1':[7,21],'T2':[37,38],'T3':[1]},
 'classification_priority':['unresolvable','full_match','skeleton_only','single_source'],
 'unresolvable':'missing complete key or no source groups',
 'full_match':'n_src_groups >= 2',
 'skeleton_only':'one own source group and alternative-key groups outside own group set',
 'single_source':'one own source group and all alternative-key groups contained in own group set',
 'G1_skeleton_only_block_gte':0.25,
 'G2':{'T1_structure_resolvable_gte':0.95,'T2_full_match_gte':0.50,'T3_full_match_gte':0.33,'T4':'all involved component tier gates must pass'},
 'multi_molregno_de_minimis_lte':0.01,
 'required_multi_molregno_occurrences':5,
 'validation':{'CHEMBL5733557':False,'CHEMBL1738510':True},
 'glm_calls_authorized_now':0,
 'on_validation_failure':'Tier B stop; preserve results and do not change rule'
}
(ROOT/'rule_v3_operational.json').write_text(json.dumps(spec,indent=2)+'\n',encoding='utf-8')
lock={'locked_utc':datetime.now(timezone.utc).isoformat(),'post_exposure':True,'addendum_sha256':expected,
 'files':[{'path':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in [ROOT/'rule_v3_authorized.md',ROOT/'rule_v3_operational.json']],
 'parent_manifest_sha256':hashlib.sha256((ROOT.parent/'MANIFEST.json').read_bytes()).hexdigest()}
(ROOT/'rule_v3_lock.json').write_text(json.dumps(lock,indent=2)+'\n',encoding='utf-8')
print(json.dumps(lock,indent=2))
