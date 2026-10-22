import json
import sqlite3

DB = "/driveA/xinrong/agentic-screening/data/source_dbs/chembl_37/extracted/chembl_37.db"
with sqlite3.connect(DB) as conn:
    for table in ("compound_structures", "compound_records", "molecule_dictionary"):
        print(table, [row[1] for row in conn.execute(f"PRAGMA table_info({table})")])

job_path = "/driveA/xinrong/agentic-screening/data/curation_private/b2_candidate_metrics_20261017/job_inputs.json"
jobs = json.load(open(job_path, encoding="utf-8"))
print("job_count", len(jobs), "first", jobs[0]["assay_id"], jobs[0]["compounds"])
records = json.load(open(jobs[0]["compounds"], encoding="utf-8"))
print("record_count", len(records))
print("record_keys", sorted(records[0]))
print("record", records[0])

from collections import Counter
summary = Counter()
examples = []
for job in jobs[:-1]:
    for record in json.load(open(job["compounds"], encoding="utf-8")):
        if record["usable_for_prototype_review"] and record["provisional_state"] in {"hit_support", "nonhit_support"}:
            count = len(record["molecule_chembl_ids"])
            summary[count] += 1
            if count > 1:
                examples.append((job["assay_id"], record["molecule_chembl_ids"], record["standardized_smiles"]))
print("molecule_id_counts", summary)
print("multi_examples", examples)

with sqlite3.connect(DB) as conn:
    for assay_id, chembl_ids, _ in examples:
        print("multi_detail", assay_id)
        for chembl_id in chembl_ids:
            row = conn.execute(
                "SELECT md.molregno, cs.standard_inchi_key, cs.canonical_smiles, "
                "GROUP_CONCAT(DISTINCT cr.src_id) "
                "FROM molecule_dictionary md "
                "LEFT JOIN compound_structures cs ON cs.molregno=md.molregno "
                "LEFT JOIN compound_records cr ON cr.molregno=md.molregno "
                "WHERE md.chembl_id=? GROUP BY md.molregno, cs.standard_inchi_key, cs.canonical_smiles",
                (chembl_id,),
            ).fetchone()
            print(chembl_id, row)
