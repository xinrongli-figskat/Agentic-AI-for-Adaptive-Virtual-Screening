"""Apply authorized S-1 source groups to hash-locked raw provenance facts."""
import csv
import hashlib
import json
import subprocess
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
PARENT=ROOT.parent
REFERENCES={'TNAP':'CHEMBL1738510','ACC2':'CHEMBL3705476','TACE':'CHEMBL5733557','CPT2':'CHEMBL3431931','ACLY':'CHEMBL5738952','S1PR1':'CHEMBL5734042'}
TIER_IDS={7:'T1',21:'T1',37:'T2',38:'T2',1:'T3'}

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()

def group(src):
    if src in (37,38):return 'G_patent_agg'
    if src in (7,21):return 'G_deposited'
    if src==1:return 'G_lit'
    return 'G_src_'+str(src)

def classify(complete_keys,own,alternate):
    if not complete_keys or not own:return 'unresolvable'
    if len(own)>=2:return 'full_match'
    if alternate-own:return 'skeleton_only'
    return 'single_source'

def write_json(name,data):
    p=ROOT/name
    assert not p.exists(),p
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def write_csv(name,rows):
    p=ROOT/name
    assert not p.exists(),p
    with p.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    started=datetime.now(timezone.utc).isoformat()
    lock=json.loads((ROOT/'rule_v3_lock.json').read_text())
    assert digest(PARENT/'MANIFEST.json')==lock['parent_manifest_sha256']
    for item in lock['files']:assert digest(ROOT/item['path'])==item['sha256']
    old_manifest=json.loads((PARENT/'MANIFEST.json').read_text())
    for item in old_manifest['files']:assert digest(PARENT/item['path'])==item['sha256'],item['path']
    facts=json.loads((PARENT/'identity_private/per_identity_measurement_v2.json').read_text())
    previous=list(csv.DictReader((PARENT/'credential_62_measurement_final_partial.csv').open()))
    assert len(previous)==62 and len(facts)==25813
    assert len({group(x) for x in (37,38)})==1
    assert len({group(x) for x in (7,21)})==1
    assert len({group(x) for x in (1,37)})==2
    assert classify(True,{'G_patent_agg'},{'G_patent_agg'})=='single_source'
    assert classify(True,{'G_patent_agg'},{'G_lit'})=='skeleton_only'
    assert classify(False,{'G_patent_agg'},set())=='unresolvable'
    assert classify(True,set(),set())=='unresolvable'
    assert classify(True,{'G_lit','G_patent_agg'},set())=='full_match'
    by_assay=defaultdict(list)
    categories=Counter()
    for rec in facts:
        complete_keys=bool(rec['full_keys']) and all(len(k)==27 for k in rec['full_keys'])
        # All five merged identities have distinct complete constituent keys;
        # no absent-key aggregation choice is required in these locked inputs.
        if len(rec['molregnos'])>1:assert len(rec['full_keys'])==len(rec['molregnos'])
        own={group(x) for x in rec['global_src_ids']}
        alt={group(x) for x in rec['alternate_key_src_ids']}
        rec={**rec,'source_groups':sorted(own),'alternate_source_groups':sorted(alt),'n_src_groups':len(own),
             'measurement_category_v3':classify(complete_keys,own,alt)}
        categories[rec['measurement_category_v3']]+=1
        by_assay[rec['assay_id']].append(rec)
    credentials=[]
    decisions=[]
    raw_to_group_changes=Counter()
    for old in previous:
        aid=old['assay_id']; rs=by_assay[aid];n=len(rs)
        assert n==int(old['support_identity_count'])
        counts=Counter(r['measurement_category_v3'] for r in rs)
        tier_counts=Counter()
        src_counts=Counter()
        for r in rs:
            tiers={TIER_IDS[x] for x in r['assay_support_src_ids']}
            assert tiers,aid
            tier_counts.update(tiers)
            src_counts.update(r['assay_support_src_ids'])
            raw_to_group_changes[(r['measurement_category'],r['measurement_category_v3'])]+=1
        tiers=sorted(tier_counts)
        row={'rank':int(old['rank']),'assay_id':aid,'support_identity_count':n,
            'molregno_count':int(old['molregno_count']),'multi_molregno_count':int(old['multi_molregno_count']),
            'multi_molregno_fraction':float(old['multi_molregno_fraction']),
            'multi_molregno_de_minimis':float(old['multi_molregno_fraction'])<=.01,
            **{k+'_frac':counts[k]/n for k in ['full_match','skeleton_only','single_source','unresolvable']},
            'structure_resolvable_frac':float(old['structure_resolvable_frac']),
            'source_tier':tiers[0] if len(tiers)==1 else 'T4',
            'involved_source_tiers':json.dumps(tiers),
            'source_tier_identity_fractions':json.dumps({t:tier_counts[t]/n for t in tiers},sort_keys=True),
            'assay_source_identity_counts':json.dumps(dict(src_counts),sort_keys=True),
            'source_scope':'assay_supporting_activity_provenance',
            'credential_scope':'global_compound_records_source_groups',
            'post_exposure':True,'campaign_ready':False}
        assert abs(sum(row[k+'_frac'] for k in ['full_match','skeleton_only','single_source','unresolvable'])-1)<1e-9
        assert row['multi_molregno_de_minimis']
        credentials.append(row)
        checks={}
        for t in tiers:
            if t=='T1':checks[t]=row['structure_resolvable_frac']>=.95
            elif t=='T2':checks[t]=row['full_match_frac']>=.50
            elif t=='T3':checks[t]=row['full_match_frac']>=.33
        g1=row['skeleton_only_frac']>=.25
        g2=all(checks.values())
        credential=('pass_'+tiers[0].lower() if len(tiers)==1 else 'pass_t4_all_components') if g2 else ('fail' if tiers==['T1'] else 'fail_patent_identity' if tiers==['T2'] else 'fail_literature_identity' if tiers==['T3'] else 'fail_t4_component')
        decisions.append({'rank':row['rank'],'assay_id':aid,'source_tier':row['source_tier'],
            'full_match_frac':row['full_match_frac'],'skeleton_only_frac':row['skeleton_only_frac'],
            'single_source_frac':row['single_source_frac'],'unresolvable_frac':row['unresolvable_frac'],
            'structure_resolvable_frac':row['structure_resolvable_frac'],'G2_component_checks':json.dumps(checks,sort_keys=True),
            'failed_G2_components':json.dumps([t for t,p in checks.items() if not p]),
            'stereochemistry_unresolved':g1,'G2_pass':g2,'identity_credential':credential,
            'shortlist_permitted':g2 and not g1,'r3_numeric_status':'previously_passed_unchanged',
            'source_review_complete':False,'campaign_ready':False,'post_exposure':True})
    assert sum(r['multi_molregno_count'] for r in credentials)==5
    indexed={r['assay_id']:r for r in decisions}
    validation={'recorded_utc':datetime.now(timezone.utc).isoformat(),'post_exposure':True,
        'TACE_expected_false':not indexed['CHEMBL5733557']['shortlist_permitted'],
        'TNAP_expected_true':indexed['CHEMBL1738510']['shortlist_permitted'],
        'reference_rows':{name:indexed[aid] for name,aid in REFERENCES.items()},
        'row_count':len(credentials),'four_ratio_sum_all_pass':True,'multi_total':5,
        'all_de_minimis':True,'glm_calls':0,
        'reference_exposure_note':'These six reference candidates were exposed before calibration; they are not an independent validation set. No precision/recall is computed.'}
    validation['passed']=validation['TACE_expected_false'] and validation['TNAP_expected_true']
    write_json('verification.json',validation)
    write_csv('credential_62.csv',credentials)
    write_csv('gate_decisions_62.csv',decisions)
    write_json('identity_private/per_identity_measurement_v3.json',[r for aid in by_assay for r in by_assay[aid]])
    summary={'post_exposure':True,'rule_locked_utc':lock['locked_utc'],'measurement_started_utc':started,
        'measurement_completed_utc':datetime.now(timezone.utc).isoformat(),'candidate_rows':62,'support_identity_count':25813,
        'source_tier_counts':dict(Counter(r['source_tier'] for r in credentials)),
        'category_counts':dict(categories),'credential_counts':dict(Counter(r['identity_credential'] for r in decisions)),
        'shortlist_permitted_count':sum(r['shortlist_permitted'] for r in decisions),
        'G1_block_count':sum(r['stereochemistry_unresolved'] for r in decisions),
        'assays_with_src37':sum(37 in {x for rr in by_assay[r['assay_id']] for x in rr['assay_support_src_ids']} for r in credentials),
        'multi_molregno_count':5,'four_ratio_sum_all_pass':True,
        'unresolvable_fraction_min':min(r['unresolvable_frac'] for r in credentials),'unresolvable_fraction_max':max(r['unresolvable_frac'] for r in credentials),
        'classification_changes':[{'old':a,'new':b,'count':n} for (a,b),n in sorted(raw_to_group_changes.items())],
        'gate_validation_passed':validation['passed'],'glm_calls':0,'campaign_ready_count':0}
    assert summary['assays_with_src37']==43
    write_json('credential_summary.json',summary)
    if validation['passed']:
        unseen=[r['assay_id'] for r in credentials if r['assay_id'] not in REFERENCES.values()][:8]
        assert len(unseen)==8
        write_json('unseen_set_lock.json',{'locked_utc':datetime.now(timezone.utc).isoformat(),'post_exposure':True,
            'selection_rule':'first 8 in unchanged R3 ranking after excluding six exposed reference candidates; not filtered by credential',
            'excluded_reference_assays':list(REFERENCES.values()),'assay_ids':unseen,
            'calls_authorized_now':0,'planned_stage_order':['inspect_metadata','read_evidence','assess_source','decide_assay'],
            'maximum_calls_after_root_release':40,'maximum_calls_per_candidate':4,'campaign_ready':False})
        status='S1_VERIFIED_NO_GLM_AWAITING_ROOT_RELEASE'
    else:
        status='BLOCKED_TIER_B_CREDENTIAL_VALIDATION'
        (ROOT/'BLOCKED_credential_validation.md').write_text('# S-1 Tier B validation failure\n\nPost-exposure. At least one predeclared TACE/TNAP condition failed. See verification.json for exact ratios and branches. No rule was changed and no GLM was called.\n',encoding='utf-8')
    (ROOT/'STATUS').write_text(status+'\n',encoding='utf-8')
    assert subprocess.run(['git','check-ignore','--quiet',str(ROOT/'identity_private/per_identity_measurement_v3.json')]).returncode==0
    write_json('input_verification.json',{'checked_utc':datetime.now(timezone.utc).isoformat(),'old_manifest_all_members_unchanged':True,
        'old_manifest_sha256':digest(PARENT/'MANIFEST.json'),'old_manifest_member_count':len(old_manifest['files']),
        'source_facts_sha256':digest(PARENT/'identity_private/per_identity_measurement_v2.json'),
        'private_gitignored':True,'rule_lock_precedes_measurement':lock['locked_utc']<started})
    print(json.dumps({'status':status,'summary':summary,'reference_rows':validation['reference_rows']},indent=2))

if __name__=='__main__':main()
