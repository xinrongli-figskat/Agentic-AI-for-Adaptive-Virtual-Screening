"""Offline assay/source alignment. Reads immutable inputs; writes new review artifacts.

Numeric agreement, source identifiers, chemical-name agreement and independently
verified stereochemical identity are separate evidence fields, never synonyms.
"""
import argparse
import csv
import hashlib
import json
import re
from collections import Counter,defaultdict
from decimal import Decimal,InvalidOperation
from pathlib import Path

from lxml import html
from rdkit import Chem
import rdkit


def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def text(e): return ' '.join(' '.join(e.itertext()).split())


def normal_name(value):
    # Layout/case normalization only; not an IUPAC equivalence algorithm.
    return re.sub(r'\s+','',value).casefold().replace('\u2212','-').replace('\u2010','-').replace('\u2011','-')


def potency(value):
    value=re.sub(r'\s+','',value).replace('\u2212','-').replace('\u2264','<=').replace('\u2265','>=')
    match=re.fullmatch(r'(<=|>=|<|>|=)?([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)',value)
    if not match:return None
    return match[1] or '=',Decimal(match[2])


def agrees(record,value,factor):
    source=potency(value)
    if source is None or record.get('standard_units')!='nM':return False
    try:
        return source[0]==record.get('standard_relation') and source[1]*Decimal(factor)==Decimal(record['standard_value'])
    except (InvalidOperation,TypeError):return False


def body_after_header(doc,needle):
    tables=doc.xpath('//table')
    indices=[i for i,t in enumerate(tables) if needle in text(t)]
    if len(indices)!=1:raise ValueError('Expected a unique assay header: '+needle)
    index=indices[0]
    # Google Patents splits these two specific header/body tables.
    if index+1>=len(tables):raise ValueError('Assay body table missing')
    return index+1,tables[index+1]


def parse_p300(doc):
    index,table=body_after_header(doc,'P300 HAT SPA')
    results=[]
    example=None
    for n,row in enumerate(table.xpath('.//tr'),1):
        cells=[text(c) for c in row.xpath('./td')]
        if not cells or not any(cells):continue
        if len(cells)>5:raise ValueError('Unexpected p300 row width')
        cells+=['']*(5-len(cells))
        if cells[0]:
            if not cells[0].isdigit():raise ValueError('Unexpected p300 example')
            example=int(cells[0])
        if example is None:raise ValueError('Example carry-forward lacks origin')
        if not re.fullmatch(r'Isomer \d+|racemic',cells[1],re.I):raise ValueError('Unknown p300 isomer')
        results.append({'example':example,'isomer':cells[1].lower(),'HAT_IC50_uM':cells[2],
                        'full_length_IC50_uM':cells[3],'cell_EC50_uM':cells[4],
                        'locator':f'Table 8; HTML table {index}, row {n}'})
    if len({(r['example'],r['isomer']) for r in results})!=len(results):raise ValueError('Duplicate p300 source key')
    return results


def parse_p2x(doc):
    index,table=body_after_header(doc,'hP2X2/3')
    results=[]
    for n,row in enumerate(table.xpath('.//tr'),1):
        cells=[text(c) for c in row.xpath('./td')]
        if not cells or not any(cells):continue
        if len(cells)==4 and not cells[0]:cells=cells[1:]
        if len(cells)!=3 or not cells[0].isdigit():raise ValueError('Unexpected P2X activity row')
        results.append({'example':int(cells[0]),'P2X3_IC50_nM':cells[1],'P2X2_3_IC50_nM':cells[2],
                        'locator':f'Biological Assays activity table; HTML table {index}, row {n}'})
    if len({r['example'] for r in results})!=len(results):raise ValueError('Duplicate P2X source key')
    return results


def parse_p2x_names(doc):
    names=defaultdict(list)
    for e in doc.xpath('//heading|//div[@class="description-paragraph"]'):
        value=text(e)
        match=re.fullmatch(r'Example (\d+):\s*(.+)',value)
        if match:
            names[int(match[1])].append({'name':match[2],'locator':e.get('id'),'basis':'primary_example_heading'})
    tables=doc.xpath('//table')
    body_index,_=body_after_header(doc,'hP2X2/3')
    enabled=False
    for index,table in enumerate(tables[:body_index-1]):
        value=text(table)
        if value.startswith('Ex. Structure Name Analytical Data'): enabled=True
        if not enabled:continue
        for n,row in enumerate(table.xpath('.//tr'),1):
            cells=[text(c) for c in row.xpath('./td')]
            if len(cells)==4 and cells[0].isdigit() and cells[2]:
                names[int(cells[0])].append({'name':cells[2],'locator':f'HTML table {index}, row {n}',
                                           'basis':'primary_example_structure_table_name'})
    return names


def parse_p300_structure_rows(doc):
    rows={}
    for table_index,table in enumerate(doc.xpath('//table')):
        value=text(table)
        if not re.match(r'TABLE [1-7]\b',value) or 'IUPAC Name' not in value:continue
        for row_index,row in enumerate(table.xpath('.//tr'),1):
            cells=row.xpath('./td')
            if len(cells)!=5:continue
            match=re.match(r'^(\d+)\b',text(cells[0]))
            if not match:continue
            example=int(match[1])
            rows[example]={'example':example,'isomers_text':text(cells[0]),'iupac_name_as_printed':text(cells[2]),
                           'exact_mass_text':text(cells[3]),'chiral_column_text':text(cells[4]),
                           'structure_images':cells[1].xpath('.//img/@src'),
                           'locator':f'HTML table {table_index}, row {row_index}'}
    for heading in doc.xpath('//heading'):
        match=re.fullmatch(r'Example (\d+)',text(heading))
        if not match or int(match[1]) in rows:continue
        example=int(match[1]);images=[];name=None
        for sibling in list(heading.itersiblings())[:4]:
            images.extend(sibling.xpath('.//img/@src'))
            if sibling.tag=='heading':
                name=text(sibling)
                break
        if name and not name.startswith(('Scheme ','Example ')):
            rows[example]={'example':example,'isomers_text':'see example synthesis and Table 8',
                           'iupac_name_as_printed':name,'exact_mass_text':'see synthesis paragraph',
                           'chiral_column_text':'see synthesis paragraph','structure_images':images,
                           'locator':heading.get('id')+'; next chemical-name heading'}
    return rows


def aliases(name):
    return [{'patent':'US'+p,'example':int(e),'isomer':('isomer '+i) if i else None}
            for p,e,i in re.findall(r'US(\d+),\s*Example\s+(\d+)(?:\s+Isomer\s+(\d+))?',name)]


def structure_info(smiles):
    mol=Chem.MolFromSmiles(smiles)
    if mol is None:return {'valid':False}
    chiral=Chem.FindMolChiralCenters(mol,includeUnassigned=True,useLegacyImplementation=False)
    return {'valid':True,'isomeric_smiles':Chem.MolToSmiles(mol,isomericSmiles=True),
            'connectivity_smiles':Chem.MolToSmiles(mol,isomericSmiles=False),
            'assigned_chiral_centres':sum(c!='?' for _,c in chiral),
            'unassigned_chiral_centres':sum(c=='?' for _,c in chiral)}


def write_csv(path,rows):
    if not rows:return
    fields=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',encoding='utf-8-sig',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in row.items()})


def audit(run,source,output):
    if output.exists():raise FileExistsError('Use a new review output directory')
    output.mkdir(parents=True)
    original_files={p.relative_to(run).as_posix():sha(p) for p in run.rglob('*') if p.is_file()}
    source_files={p.name:sha(p) for p in source.iterdir() if p.is_file()}
    state=read(run/'state.json')

    def evidence(key):
        item=state['evidence'][key]
        path=run/item['path']
        if sha(path)!=item['sha256']:raise ValueError('Original evidence hash mismatch: '+key)
        return read(path)

    summary={'review_type':'source_alignment_not_benchmark_construction','rdkit_version':rdkit.__version__,
             'source_chembl_status':read(source/'chembl_status.json'),'assays':{}}
    all_rows={}
    for tag,aid,primary_patent in [('p300','CHEMBL5737918','US11274090'),('p2x','CHEMBL5732233','US10183937')]:
        a=state['assays'][aid]
        records=evidence(a['acquisition']['evidence_id'])['records']
        curated=evidence(a['curation']['evidence_id'])
        compound_export=read(source/f'{tag}_compound_records.json')
        if compound_export['page_meta']['next'] or len(compound_export['compound_records'])!=compound_export['page_meta']['total_count']:
            raise ValueError('Incomplete source compound-record retrieval')
        by_record={r['record_id']:r for r in compound_export['compound_records']}
        doc=html.fromstring((source/f'{tag}_patent.html').read_bytes())
        primary=parse_p300(doc) if tag=='p300' else parse_p2x(doc)
        write_csv(output/f'{tag}_primary_activity_table.csv',primary)
        if tag=='p300':
            primary_map={(r['example'],r['isomer']):r for r in primary}
            structural=parse_p300_structure_rows(doc)
            write_csv(output/'p300_primary_structure_names.csv',list(structural.values()))
            name_index=None
        else:
            primary_map={r['example']:r for r in primary}
            structural=parse_p2x_names(doc)
            write_csv(output/'p2x_primary_structure_names.csv',[{'example':e,**n} for e,ns in structural.items() for n in ns])
            name_index=defaultdict(set)
            for e,ns in structural.items():
                for n in ns:name_index[normal_name(n['name'])].add(e)
        rows=[]
        groups=defaultdict(lambda:{'molecules':set(),'connectivities':set(),'source_aliases':set()})
        for record in records:
            src=by_record.get(record['record_id'])
            if src is None or src['molecule_chembl_id']!=record['molecule_chembl_id']:
                raise ValueError('Missing/different record-to-molecule mapping')
            names=aliases(src['compound_name'])
            si=structure_info(record['canonical_smiles'])
            row={'activity_id':record['activity_id'],'record_id':record['record_id'],
                 'molecule_chembl_id':record['molecule_chembl_id'],'bindingdb_compound_key':src['compound_key'],
                 'bindingdb_activity_comment_as_recorded':record.get('activity_comment'),
                 'compound_name_as_recorded':src['compound_name'],'source_aliases':names,
                 'standard_relation':record['standard_relation'],'standard_value_nM':record['standard_value'],
                 'potential_duplicate':record['potential_duplicate'],'structure':si,
                 'independent_full_structure_verification':'not_completed',
                 'source_endpoint_approved_for_campaign':False}
            if tag=='p300':
                keys=sorted({(n['example'],n['isomer'] or 'racemic') for n in names if n['patent']==primary_patent})
                candidates=[primary_map[k] for k in keys if k in primary_map]
                row['identity_mapping_basis']='current_patent_record_alias'
                row['source_alias_count']=len(keys)
                row['primary_candidates']=candidates
                columns={'HAT_IC50_uM':1000,'full_length_IC50_uM':1000,'cell_EC50_uM':1000}
                # EC50 column comparison is an audit of extraction, not endpoint pooling.
                matched={col:[(r['example'],r['isomer']) for r in candidates if agrees(record,r[col],factor)]
                         for col,factor in columns.items()}
                row['column_matches']=matched
                row['expected_column_match_count']=len(matched['HAT_IC50_uM'])
                row['source_isomer_absolute_configuration']='not_established_by_elution_order'
                for ex,iso in keys:
                    g=groups[ex];g['molecules'].add(record['molecule_chembl_id'])
                    if si['valid']:g['connectivities'].add(si['connectivity_smiles'])
                    g['source_aliases'].add(iso)
            else:
                direct={n['example'] for n in names if n['patent']==primary_patent}
                chemical=src['compound_name'].split('::')[0]
                name_matches=name_index.get(normal_name(chemical),set())
                foreign={n['example'] for n in names}
                if direct:
                    keys=sorted(direct);basis='current_patent_alias'
                elif name_matches:
                    keys=sorted(name_matches);basis='exact_primary_name_after_whitespace_case_normalization'
                else:
                    keys=sorted(foreign);basis='cross_patent_alias_candidate_only'
                candidates=[primary_map[k] for k in keys if k in primary_map]
                row.update(identity_mapping_basis=basis,primary_name_matching_examples=sorted(name_matches),
                           primary_candidates=candidates,source_alias_count=len(keys))
                matched={col:[r['example'] for r in candidates if agrees(record,r[col],1)]
                         for col in ['P2X3_IC50_nM','P2X2_3_IC50_nM']}
                row['column_matches']=matched
                row['expected_column_match_count']=len(matched['P2X2_3_IC50_nM'])
                row['source_receptor_interpretation']='human_P2X2_3_functional_antagonism_candidate'
            rows.append(row)
        all_rows[tag]=rows
        write_csv(output/f'{tag}_record_alignment.csv',rows)
        summary['assays'][tag]={'assay_id':aid,'records':len(records),'source_compound_records':len(by_record),
            'primary_table_rows':len(primary),'valid_record_to_molecule_joins':len(rows),
            'identity_mapping_basis_counts':dict(Counter(r['identity_mapping_basis'] for r in rows)),
            'expected_column_exact_matches':sum(bool(r['expected_column_match_count']) for r in rows),
            'expected_column_unmatched_activity_ids':[r['activity_id'] for r in rows if not r['expected_column_match_count']],
            'multi_alias_records':sum(r['source_alias_count']>1 for r in rows),
            'flagged_potential_duplicate_records':sum(bool(r['potential_duplicate']) for r in rows),
            'no_campaign_or_new_labels_created':True}
        if tag=='p300':
            group_rows=[{'example':e,'molecule_chembl_ids':sorted(g['molecules']),
                         'distinct_connectivity_count':len(g['connectivities']),
                         'source_isomer_labels':sorted(g['source_aliases'])} for e,g in sorted(groups.items())]
            write_csv(output/'p300_example_structure_groups.csv',group_rows)
            summary['assays'][tag].update(
                primary_structure_examples_captured=len(structural),
                examples_with_multiple_db_connectivities=[r['example'] for r in group_rows if r['distinct_connectivity_count']>1],
                records_with_assigned_chiral_centres=sum(r['structure'].get('assigned_chiral_centres',0)>0 for r in rows),
                records_with_unassigned_chiral_centres=sum(r['structure'].get('unassigned_chiral_centres',0)>0 for r in rows),
                multi_alias_source_records=[r for r in compound_export['compound_records'] if len([n for n in aliases(r['compound_name']) if n['patent']==primary_patent])>1])
        else:
            # Saved table/API ordering is corroboration of extraction, NOT identity evidence.
            diagnostics=[]
            for record,row in zip(records,primary):
                diagnostics.append({'activity_id':record['activity_id'],'example_at_same_row_position':row['example'],
                    'P2X2_3_column_value_match':agrees(record,row['P2X2_3_IC50_nM'],1),
                    'P2X3_column_value_match':agrees(record,row['P2X3_IC50_nM'],1),
                    'identity_status':'row_order_only_not_identity_confirmation'})
            write_csv(output/'p2x_order_only_diagnostic.csv',diagnostics)
            summary['assays'][tag]['order_only_diagnostic']={
                'paired_rows':len(diagnostics),'P2X2_3_column_matches':sum(r['P2X2_3_column_value_match'] for r in diagnostics),
                'P2X3_column_matches':sum(r['P2X3_column_value_match'] for r in diagnostics),
                'not_used_to_assign_or_repair_compound_identity':True}
            summary['assays'][tag]['heteromer_target_metadata']=read(source/'p2x_heteromer_target.json')

    # Trace same-target, unflagged possible antecedents. Never restore labels here.
    traces=[];trace_completeness=[]
    for path in sorted(source.glob('p2x_duplicate_trace_*.json')):
        data=read(path)
        trace_completeness.append({'file':path.name,'received':len(data['activities']),
                                   'total':data['page_meta']['total_count'],'next':data['page_meta']['next']})
        if data['page_meta']['next']:raise ValueError('Duplicate trace truncated')
        traces.extend(data['activities'])
    extra=read(source/'p2x_unresolved_molecule_all_targets.json')
    if extra['page_meta']['next']:raise ValueError('Single-molecule follow-up truncated')
    # Supplement the sole unmatched row with its same-target earlier record,
    # retaining the fact that this earlier record is ALSO duplicate-flagged.
    trace_by_id={r['activity_id']:r for r in traces}
    for r in extra['activities']:
        if r['target_chembl_id']=='CHEMBL2531':trace_by_id[r['activity_id']]=r
    traces=list(trace_by_id.values())
    earlier_compounds=read(source/'p2x_earlier_compound_records.json')
    if earlier_compounds['page_meta']['next']:raise ValueError('Earlier source record list truncated')
    earlier_by_id={r['record_id']:r for r in earlier_compounds['compound_records']}
    earlier_table=parse_p2x(html.fromstring((source/'p2x_earlier_patent.html').read_bytes()))
    earlier_by_example={r['example']:r for r in earlier_table}
    write_csv(output/'p2x_earlier_primary_activity_table.csv',earlier_table)
    original=evidence(state['assays']['CHEMBL5732233']['acquisition']['evidence_id'])['records']
    duplicate_rows=[]
    for r in original:
        if not r.get('potential_duplicate'):continue
        same=[x for x in traces if x['molecule_chembl_id']==r['molecule_chembl_id'] and
              x['standard_relation']==r['standard_relation'] and x['standard_value']==r['standard_value'] and
              x['document_chembl_id']!=r['document_chembl_id']]
        matched=[]
        for x in same:
            c=earlier_by_id.get(x['record_id'])
            ex=[] if c is None else [a['example'] for a in aliases(c['compound_name']) if a['patent']=='US10174016']
            checked=[e for e in ex if e in earlier_by_example and agrees(x,earlier_by_example[e]['P2X2_3_IC50_nM'],1)]
            matched.append({'activity_id':x['activity_id'],'assay_id':x['assay_chembl_id'],
                            'document_id':x['document_chembl_id'],'record_id':x['record_id'],
                            'potential_duplicate':x.get('potential_duplicate'),
                            'same_isomeric_structure':structure_info(x['canonical_smiles'])['isomeric_smiles']==structure_info(r['canonical_smiles'])['isomeric_smiles'],
                            'earlier_source_compound_name':c['compound_name'] if c else None,
                            'earlier_patent_matching_examples':checked})
        duplicate_rows.append({'activity_id':r['activity_id'],'molecule_chembl_id':r['molecule_chembl_id'],
                               'record_id':r['record_id'],'standard_relation':r['standard_relation'],
                               'standard_value_nM':r['standard_value'],'earlier_numeric_matches':matched,
                               'earlier_patent_corrob_match':any(m['earlier_patent_matching_examples'] and m['same_isomeric_structure'] for m in matched),
                               'decision':'retain_original_exclusion_no_label_restoration',
                               'interpretation':'possible_repeated_citation_not_independent_replication'})
    write_csv(output/'p2x_duplicate_source_trace.csv',duplicate_rows)
    summary['duplicate_trace']={'scope':'CHEMBL2531 IC50/nM unflagged records for flagged molecule IDs, plus an all-target/flag follow-up for CHEMBL5951677; not an exhaustive publication search',
        'retrievals':trace_completeness,'flagged_rows_examined':len(duplicate_rows),
        'same_molecule_relation_value_other_document_matches':sum(bool(r['earlier_numeric_matches']) for r in duplicate_rows),
        'with_unflagged_earlier_counterpart':sum(any(not m['potential_duplicate'] for m in r['earlier_numeric_matches']) for r in duplicate_rows),
        'earlier_patent_and_isomeric_structure_corrob':sum(r['earlier_patent_corrob_match'] for r in duplicate_rows),
        'unresolved_activity_ids':[r['activity_id'] for r in duplicate_rows if not r['earlier_patent_corrob_match']],
        'earlier_document':read(source/'p2x_earlier_document.json'),
        'earlier_assay':read(source/'p2x_earlier_assay.json'),
        'no_claim_of_experiment_independence_or_label_restoration':True}
    spotchecks=[]
    for item in read(source/'structure_spotcheck_inputs.json'):
        parsed=read(source/(item['name']+'_opsin.json'))
        tag=item['name'].split('_')[0]
        candidates=[r for r in all_rows[tag] if any(a['example']==1 for a in r['source_aliases'])]
        if tag=='p2x':
            # Explicitly selected example-1 candidate; matching graph is the test.
            candidates=[r for r in candidates if r['record_id']==4248885]
        source_structure=structure_info(parsed.get('smiles','')) if parsed.get('status')=='SUCCESS' else {'valid':False}
        for row in candidates:
            graph=row['structure']
            spotchecks.append({**item,'activity_id':row['activity_id'],'molecule_id':row['molecule_chembl_id'],
                'opsin_status':parsed.get('status'),'opsin_warnings':parsed.get('warnings'),
                'connectivity_matches':source_structure.get('connectivity_smiles')==graph.get('connectivity_smiles'),
                'full_stereochemical_graph_matches':source_structure.get('isomeric_smiles')==graph.get('isomeric_smiles'),
                'scope':'targeted name-to-structure check; does not verify all examples or elution-order-to-absolute-configuration mapping'})
    write_csv(output/'structure_spotchecks.csv',spotchecks)
    summary['structure_spotchecks']=spotchecks
    summary['review_dispositions']={
        'p300':{'status':'HOLD_NOT_CAMPAIGN_READY','measurement_interpretation':'p300 HAT domain biochemical inhibition IC50; residues 1287-1666',
                'blocking_items':['absolute-isomer-to-structure identity not fully confirmed',
                                  'four merged source IDs link distinct source isomers',
                                  'qualification criteria require a separately justified new version'],
                'retain_as_source_review_candidate':True},
        'p2x':{'status':'UNSUITABLE_AS_CURRENT_SINGLE_P2X2_POOL',
               'measurement_interpretation':'human P2X2/P2X3 heteromer functional antagonism IC50',
               'blocking_items':['current catalog target is single P2X2, inconsistent with source receptor column',
                                 'cross-patent numbering and merged stereoisomer/sample identities unresolved',
                                 'repeated citations must not count as independent measurement evidence'],
               'retain_as_receptor_complex_source_review_candidate_only':True},
        'new_campaigns':0,'new_benchmark_versions':0,'existing_pool_labels_or_protocols_changed':False}
    # Ensure review did not change or add anything to the historical run.
    after={p.relative_to(run).as_posix():sha(p) for p in run.rglob('*') if p.is_file()}
    if original_files!=after:raise RuntimeError('Historical evidence changed during review')
    if source_files!={p.name:sha(p) for p in source.iterdir() if p.is_file()}:raise RuntimeError('Source inputs changed during review')
    summary['original_inputs_preserved']={'historical_run_files':len(original_files),'source_files':len(source_files),'hash_comparison':'PASS'}
    (output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (output/'input_sha256.json').write_text(json.dumps({'historical_run':original_files,'new_sources':source_files},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return summary


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run-dir',type=Path,required=True)
    parser.add_argument('--source-dir',type=Path,required=True)
    parser.add_argument('--out-dir',type=Path,required=True)
    a=parser.parse_args()
    audit(a.run_dir.resolve(),a.source_dir.resolve(),a.out_dir.resolve())


if __name__=='__main__':main()
