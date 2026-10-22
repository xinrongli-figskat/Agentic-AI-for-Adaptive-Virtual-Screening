"""D7-D definition-preserving measurement; unresolved cases stay unresolved."""
import csv
import hashlib
import json
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

BASE = Path('/driveA/xinrong/agentic-screening')
OUT = Path(__file__).resolve().parent
PRIVATE = OUT/'identity_private'
RANKED = BASE/'deliveries_20261018/outputs/r3_ranked_numeric_private_20261018_v2/ranked_numeric_qualified_62.csv'
DB = BASE/'data/source_dbs/chembl_37/extracted/chembl_37.db'
TIERS = {7:'T1', 21:'T1', 38:'T2', 1:'T3'}

def utc():
    return datetime.now(timezone.utc).isoformat()

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024), b''):
            h.update(b)
    return h.hexdigest()

def save(path, data):
    if path.exists():
        raise RuntimeError(f'Refuse overwrite: {path}')
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def tier(ids):
    missing = sorted(set(ids)-TIERS.keys())
    if missing:
        return 'unresolved_unmapped_src_id', missing
    ts = {TIERS[x] for x in ids}
    return (next(iter(ts)) if len(ts)==1 else 'T4' if ts else 'unresolved_empty'), []

def main():
    start = utc()
    lock = json.loads((OUT/'gate_rule_lock.json').read_text())
    for item in lock['files']:
        assert digest(OUT/item['path']) == item['sha256']
    assert digest(RANKED) == 'dfb3569217454cd73a6c60b69128988aa1f57dc9866b7949728954933add47b9'
    ranked = list(csv.DictReader(RANKED.open()))
    assert len(ranked)==62
    jobs = {j['assay_id']:j for j in json.loads((BASE/'data/curation_private/b2_candidate_metrics_20261017/job_inputs.json').read_text())}
    support = {}
    input_files = []
    for row in ranked:
        path = Path(jobs[row['assay_id']]['compounds'])
        records = json.loads(path.read_text())
        chosen = [r for r in records if r['usable_for_prototype_review'] and r['provisional_state'] in ('hit_support','nonhit_support')]
        assert len(chosen)==int(row['N']), (row['assay_id'],len(chosen),row['N'])
        assert sum(r['provisional_state']=='hit_support' for r in chosen)==int(row['K'])
        support[row['assay_id']] = chosen
        input_files.append({'path':str(path), 'sha256':digest(path)})
    PRIVATE.mkdir(exist_ok=True)
    conn = sqlite3.connect('file:'+str(DB)+'?mode=ro',uri=True)
    conn.execute('CREATE TEMP TABLE wanted(chembl_id TEXT PRIMARY KEY)')
    ids = sorted({x for records in support.values() for r in records for x in r['molecule_chembl_ids']})
    conn.executemany('INSERT INTO wanted VALUES(?)', [(x,) for x in ids])
    molecules = {}
    for cid,mol,key,smiles in conn.execute('SELECT md.chembl_id,md.molregno,cs.standard_inchi_key,cs.canonical_smiles FROM wanted w JOIN molecule_dictionary md ON md.chembl_id=w.chembl_id LEFT JOIN compound_structures cs ON cs.molregno=md.molregno'):
        molecules[cid] = {'molregno':mol,'key':key,'resolvable':bool(key and smiles),'src':set()}
    assert len(molecules)==len(ids)
    bymol = {v['molregno']:v for v in molecules.values()}
    for mol,src in conn.execute('SELECT DISTINCT cr.molregno,cr.src_id FROM wanted w JOIN molecule_dictionary md ON md.chembl_id=w.chembl_id JOIN compound_records cr ON cr.molregno=md.molregno'):
        bymol[mol]['src'].add(src)
    conn.execute('CREATE TEMP TABLE skeletons(skeleton TEXT PRIMARY KEY)')
    skels = {v['key'][:14] for v in molecules.values() if v['key']}
    conn.executemany('INSERT INTO skeletons VALUES(?)',[(x,) for x in skels])
    print('support_loaded',sum(map(len,support.values())), 'skeletons',len(skels),flush=True)
    skel_sources = defaultdict(lambda:defaultdict(set))
    for key,src in conn.execute('SELECT cs.standard_inchi_key,cr.src_id FROM compound_structures cs JOIN skeletons s ON substr(cs.standard_inchi_key,1,14)=s.skeleton JOIN compound_records cr ON cr.molregno=cs.molregno GROUP BY cs.standard_inchi_key,cr.src_id'):
        skel_sources[key[:14]][key].add(src)
    output=[]
    details=[]
    for row in ranked:
        aid=row['assay_id']
        counter=Counter()
        src_counts=Counter()
        assay_src_counts=Counter()
        multi=0
        resolvable_all=resolvable_any=0
        n=len(support[aid])
        for rec in support[aid]:
            ms=[molecules[x] for x in rec['molecule_chembl_ids']]
            src=set().union(*(x['src'] for x in ms))
            multi += len(ms)>1
            src_counts.update(src)
            resolvable_all += all(x['resolvable'] for x in ms)
            resolvable_any += any(x['resolvable'] for x in ms)
            keys={x['key'] for x in ms}
            alt=set()
            for key in keys:
                if key:
                    for other,sources in skel_sources[key[:14]].items():
                        if other != key:
                            alt.update(sources)
            if len(src)>=2:
                kind='full_match'
            elif len(ms)>1:
                kind='undefined_multi_key_single_source'
            elif len(src)==1 and alt-src:
                kind='skeleton_only'
            elif len(src)==1 and not alt:
                kind='single_source'
            elif len(src)==1:
                kind='undefined_same_source_alternate_key'
            else:
                kind='undefined_no_source'
            counter[kind]+=1
            provenance=set()
            for act in rec['activity_ids']:
                provenance.update(r[0] for r in conn.execute('SELECT DISTINCT cr.src_id FROM activities a JOIN compound_records cr ON cr.record_id=a.record_id WHERE a.activity_id=?',(int(act),)))
            assay_src_counts.update(provenance)
            details.append({'assay_id':aid,'compound_key':rec['compound_key'], 'molecule_chembl_ids':rec['molecule_chembl_ids'],'molregnos':[m['molregno'] for m in ms], 'full_keys':sorted(k for k in keys if k), 'global_src_ids':sorted(src),'assay_support_src_ids':sorted(provenance),'alternate_key_src_ids':sorted(alt),'measurement_category':kind})
        global_tier, global_missing=tier(src_counts)
        provenance_tier, provenance_missing=tier(assay_src_counts)
        ratio_sum=sum(counter[x] for x in ('full_match','skeleton_only','single_source'))/n
        source_tier=global_tier if global_tier==provenance_tier and not global_missing else 'unresolved_scope_or_source_mapping'
        output.append({'rank':row['rank'],'assay_id':aid,'support_identity_count':n,
            'molregno_count':sum(len(r['molecule_chembl_ids']) for r in support[aid]),
            'multi_molregno_count':multi,'multi_molregno_fraction':multi/n,'multi_molregno_de_minimis':multi/n<=0.01,
            'full_match_frac':counter['full_match']/n,'skeleton_only_frac':counter['skeleton_only']/n,'single_source_frac':counter['single_source']/n,
            'defined_ratio_sum':ratio_sum,'unclassified_identity_count':n-int(round(ratio_sum*n)),
            'unclassified_categories':json.dumps({k:v for k,v in counter.items() if k.startswith('undefined')},sort_keys=True),
            'structure_resolvable_frac':resolvable_all/n,'structure_resolvable_any_frac':resolvable_any/n,
            'source_tier':source_tier,'global_source_tier':global_tier,'assay_provenance_source_tier':provenance_tier,
            'global_src_identity_counts':json.dumps(dict(src_counts),sort_keys=True),'assay_src_identity_counts':json.dumps(dict(assay_src_counts),sort_keys=True),
            'unmapped_global_src_ids':json.dumps(global_missing),'unmapped_assay_src_ids':json.dumps(provenance_missing)})
    conn.close()
    path=OUT/'credential_62_measurement_partial.csv'
    if path.exists(): raise RuntimeError('Do not overwrite measurements')
    with path.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(output[0]));writer.writeheader();writer.writerows(output)
    save(PRIVATE/'per_identity_measurement.json',details)
    save(PRIVATE/'input_files.json',input_files)
    summary={'post_exposure':True,'measurement_started_utc':start,'measurement_completed_utc':utc(),'rule_locked_utc':lock['locked_utc'],
        'candidate_rows':len(output),'support_identity_count':sum(r['support_identity_count'] for r in output),
        'multi_molregno_total':sum(r['multi_molregno_count'] for r in output),
        'multi_molregno_details':[{k:r[k] for k in ['assay_id','support_identity_count','multi_molregno_count','multi_molregno_fraction','multi_molregno_de_minimis']} for r in output if r['multi_molregno_count']],
        'all_multi_fractions_de_minimis':all(r['multi_molregno_de_minimis'] for r in output),
        'ratio_sum_pass_rows':sum(abs(r['defined_ratio_sum']-1)<1e-9 for r in output),
        'unclassified_identity_total':sum(r['unclassified_identity_count'] for r in output),
        'unmapped_global_src_ids':sorted({x for r in output for x in json.loads(r['unmapped_global_src_ids'])}),
        'unmapped_assay_src_ids':sorted({x for r in output for x in json.loads(r['unmapped_assay_src_ids'])}),
        'unmapped_assay_src_rows':sum(bool(json.loads(r['unmapped_assay_src_ids'])) for r in output),
        'unresolved_source_tier_rows':sum(r['source_tier'].startswith('unresolved') for r in output),
        'structure_resolvable_all_any_differences':sum(r['structure_resolvable_frac']!=r['structure_resolvable_any_frac'] for r in output),
        'glm_calls':0,'gate_application_performed':False,'campaign_ready':False}
    assert summary['multi_molregno_total']==5
    save(OUT/'credential_summary_partial.json',summary)
    print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':main()
