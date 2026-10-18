"""Three bounded public GETs verify count and projection support; no GLM/campaign."""
import argparse
import json
from pathlib import Path
from .engine import save
from .efficient import THIN_FIELDS
from .vendor.discovery import Client


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out-dir',type=Path,required=True);args=parser.parse_args()
    args.out_dir.mkdir(parents=True,exist_ok=False);(args.out_dir/'raw').mkdir()
    requests=[]
    client=Client(args.out_dir/'raw',{'max_requests':3,'request_timeout_seconds':30,'request_wall_deadline_seconds':60},
                  requests,lambda:save(args.out_dir/'requests.json',requests))
    scope={'target_chembl_id':'CHEMBL3784','assay_chembl_id':'CHEMBL5737918','standard_type':'IC50','assay_type':'B','order_by':'activity_id','offset':0}
    count=client.get('activity',{**scope,'limit':1,'only':'activity_id,assay_chembl_id,target_chembl_id,standard_type,assay_type'})
    thin=client.get('activity',{**scope,'limit':3,'only':','.join(THIN_FIELDS)})
    full=client.get('activity',{**scope,'limit':3})
    totals=[p['page_meta']['total_count'] for p in [count,thin,full]]
    if len(set(totals))!=1:raise ValueError('Counts changed across probe requests')
    if [r['activity_id'] for r in thin['activities']]!=[r['activity_id'] for r in full['activities']]:raise ValueError('Projected IDs differ')
    if any('assay_description' in r for r in thin['activities']):raise ValueError('Projection not honored')
    if any(r.get('target_chembl_id')!='CHEMBL3784' or r.get('assay_type')!='B' or r.get('standard_type')!='IC50' for r in thin['activities']):
        raise ValueError('Filter scope mismatch')
    result={'status':'PUBLIC_API_COUNT_PROJECTION_CHECK_PASSED','http_requests':len(requests),
            'known_prior_assay':'CHEMBL5737918','total_records':totals[0],
            'count_response_bytes':requests[0]['bytes'],'thin_three_records_bytes':requests[1]['bytes'],
            'full_three_records_bytes':requests[2]['bytes'],'thin_to_full_byte_ratio':requests[1]['bytes']/requests[2]['bytes'],
            'glm_requests':0,'campaign_queries':0,
            'limitation':'Interface/payload smoke check on an already seen assay; not evidence of improved discovery yield or LLM control.'}
    save(args.out_dir/'result.json',result);print(json.dumps(result,indent=2))


if __name__=='__main__':main()
