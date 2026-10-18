"""Retrieve public primary sources into an isolated review directory; no LLM calls."""
import argparse
import hashlib
import json
import time
import urllib.error
import urllib.request
from datetime import datetime,timezone
from pathlib import Path

SOURCES={
 'p300_patent.html':'https://patents.google.com/patent/US11274090B2/en',
 'p2x_patent.html':'https://patents.google.com/patent/US10183937B2/en',
 'p300_compound_records.json':'https://www.ebi.ac.uk/chembl/api/data/compound_record.json?document_chembl_id=CHEMBL5729020&limit=1000',
 'p2x_compound_records.json':'https://www.ebi.ac.uk/chembl/api/data/compound_record.json?document_chembl_id=CHEMBL5726182&limit=1000',
 'chembl_status.json':'https://www.ebi.ac.uk/chembl/api/data/status.json',
}


def fetch(url,path):
    attempts=[]
    if path.exists():
        raise FileExistsError('Use a fresh output path or explicit cached inputs: '+str(path))
    for attempt in range(3):
        start=time.monotonic()
        try:
            request=urllib.request.Request(url,headers={'User-Agent':'Scientific-source-audit/1.0'})
            with urllib.request.urlopen(request,timeout=40) as response:
                data=response.read(32*1024**2+1)
                if len(data)>32*1024**2: raise ValueError('Source response too large')
                status=response.status
                final=response.url
            path.write_bytes(data)
            attempts.append({'attempt':attempt+1,'http_status':status,'elapsed_seconds':round(time.monotonic()-start,3)})
            return {'url':url,'final_url':final,'path':path.name,'bytes':len(data),
                    'sha256':hashlib.sha256(data).hexdigest(),'retrieved_at_utc':datetime.now(timezone.utc).isoformat(),
                    'attempts':attempts}
        except (urllib.error.URLError,TimeoutError) as error:
            attempts.append({'attempt':attempt+1,'error_type':type(error).__name__,
                             'elapsed_seconds':round(time.monotonic()-start,3)})
            if attempt==2:
                return {'url':url,'path':path.name,'failed':True,'attempts':attempts}
            time.sleep(attempt+1)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out-dir',type=Path,required=True)
    args=parser.parse_args()
    args.out_dir.mkdir(parents=True,exist_ok=True)
    log=args.out_dir/'retrieval_log.json'
    if log.exists(): raise FileExistsError('Retrieval log exists; do not overwrite sources')
    receipts=[]
    for name,url in SOURCES.items():
        receipt=fetch(url,args.out_dir/name)
        receipts.append(receipt)
        log.write_text(json.dumps(receipts,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(receipt,ensure_ascii=False),flush=True)
    if any(r.get('failed') for r in receipts): raise SystemExit(1)


if __name__=='__main__': main()
