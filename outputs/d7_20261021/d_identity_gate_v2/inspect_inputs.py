"""Read-only schema inspection, no gate application."""
import csv
import json
import sqlite3
from pathlib import Path

BASE = Path('/driveA/xinrong/agentic-screening')
ranked = list(csv.DictReader((BASE/'deliveries_20261018/outputs/r3_ranked_numeric_private_20261018_v2/ranked_numeric_qualified_62.csv').open()))
jobs = {j['assay_id']: j for j in json.loads((BASE/'data/curation_private/b2_candidate_metrics_20261017/job_inputs.json').read_text())}
job = jobs[ranked[0]['assay_id']]
records = json.loads(Path(job['compounds']).read_text())
print('ranked_count', len(ranked))
print('record_keys', sorted(records[0]))
print('record_nonstructure_fields', {k:v for k,v in records[0].items() if k not in ['standardized_smiles','canonical_smiles','compound_key']})
with sqlite3.connect('file:'+str(BASE/'data/source_dbs/chembl_37/extracted/chembl_37.db')+'?mode=ro', uri=True) as db:
    for table in ['compound_structures','compound_records','molecule_dictionary','source']:
        print('schema', table, [r[1] for r in db.execute('pragma table_info('+table+')')])
    print('source_reference', list(db.execute('select * from source where src_id in (1,7,21,37,38)')))
