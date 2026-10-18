-- ChEMBL_37 numeric assay prescreen, not final chemical curation.
-- Count all IC50 activity rows first. A raw count below 250 is a safe upper
-- bound for a 250-compound single-assay pool. Relationship/structure gates
-- are applied subsequently by the Python enumerator.
WITH assay_raw AS (
    SELECT assay_id, COUNT(*) AS raw_ic50_records
    FROM activities
    WHERE standard_type = 'IC50'
    GROUP BY assay_id
    HAVING COUNT(*) >= 250
)
SELECT a.assay_id, a.chembl_id AS assay_chembl_id,
       a.description, a.assay_type, a.confidence_score,
       a.relationship_type, a.src_id AS assay_src_id,
       td.chembl_id AS target_chembl_id, td.pref_name AS target_name,
       td.organism AS target_organism, td.target_type,
       d.chembl_id AS document_chembl_id, d.doc_type,
       d.doi, d.pubmed_id, d.patent_id, d.title AS document_title,
       assay_raw.raw_ic50_records
FROM assay_raw
JOIN assays a ON a.assay_id = assay_raw.assay_id
JOIN target_dictionary td ON td.tid = a.tid
JOIN docs d ON d.doc_id = a.doc_id
ORDER BY assay_raw.raw_ic50_records DESC, a.chembl_id;
