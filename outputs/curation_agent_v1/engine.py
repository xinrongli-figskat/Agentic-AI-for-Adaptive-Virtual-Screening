"""Task 1 tools. All paths are program-selected; the LLM gets no shell or file tool.

Labels in this workspace belong to curation. Never mount this directory in a
campaign agent. Exported candidates have no source IDs or assay outcome fields.
"""
import hashlib
import json
import os
import re
import time
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .vendor import audit, discovery


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    os.replace(temporary, path)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def signature(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'CHEMBL[0-9]+', value):
        raise ValueError('Expected a ChEMBL identifier')
    return value


def import_catalog(source):
    """Reconstruct the catalog from hash-verified source pages, not an unchecked index."""
    source = Path(source).resolve()
    metadata = read(source / 'run_metadata.json')
    if not metadata.get('completed'):
        raise ValueError('Seed discovery did not complete')
    if sha(source / 'tool_source.py') != metadata.get('script_sha256'):
        raise ValueError('Seed discovery source hash mismatch')
    rows, seen, total, release = [], set(), None, None
    for receipt in metadata['requests']:
        url = urlparse(receipt['url'])
        if url.hostname != 'www.ebi.ac.uk':
            continue
        resource = url.path.rsplit('/', 1)[-1]
        if resource not in ('target.json', 'status.json'):
            continue
        path = (source / receipt['raw_file']).resolve()
        if not path.is_relative_to(source) or receipt.get('error') or receipt.get('http_status') != 200:
            raise ValueError('Unusable seed source receipt')
        if sha(path) != receipt.get('sha256'):
            raise ValueError('Seed raw source hash mismatch')
        payload = read(path)
        if resource == 'status.json':
            release = payload['chembl_db_version']
            continue
        query = parse_qs(url.query)
        if query.get('target_type') != ['SINGLE PROTEIN']:
            raise ValueError('Seed catalog has a different target scope')
        if int(query.get('offset', ['0'])[0]) != len(rows):
            raise ValueError('Seed catalog page missing or out of order')
        page_total = payload['page_meta']['total_count']
        if total is not None and page_total != total:
            raise ValueError('Seed catalog totals changed')
        total = page_total
        for row in payload['targets']:
            key = identifier(row['target_chembl_id'])
            if key in seen or row['target_type'] != 'SINGLE PROTEIN':
                raise ValueError('Seed catalog duplicate or incompatible target')
            seen.add(key)
            rows.append(row)
    if release is None or total is None or len(rows) != total:
        raise ValueError('Seed catalog coverage or release is incomplete')
    return rows, release


def qualification(summary, protocol):
    """Prospectively fixed operational gates; model cannot override failed gates."""
    b = summary['budget']
    d = summary['diversity']
    proposal = b['proposals'][0]
    checks = {
        'complete_assay_endpoint_scope': summary['complete'],
        'single_protein_mapping': summary['target_type'] == 'SINGLE PROTEIN',
        'assay_type_B': summary['assay_type'] == 'B',
        'mapping_confidence': summary['confidence_score'] >= protocol['minimum_confidence_score'],
        'usable_compounds': b['provisional_pool_size'] >= protocol['minimum_usable_compounds'],
        'hits': b['hit_support_count'] >= protocol['minimum_hits'],
        'nonhits': b['nonhit_support_count'] >= protocol['minimum_nonhits'],
        'largest_cluster': d['largest_cluster_fraction'] is not None and
            d['largest_cluster_fraction'] <= protocol['maximum_largest_cluster_fraction'],
        'scaffold_buckets': d['scaffold_count_including_acyclic_bucket'] >= protocol['minimum_scaffold_buckets'],
        'campaign_pool_size': proposal['pool_large_enough'],
        'initialization_class_risk': proposal.get('initialization_probability_single_class', 1.0) <=
            protocol['maximum_initial_single_class_probability'],
    }
    return {'checks': checks, 'failed_checks': [key for key, ok in checks.items() if not ok],
            'numerical_eligibility': all(checks.values()),
            'scientific_review_complete': False, 'campaign_ready': False}


TOOLS = {
    'discover_batch': {'offset': 'integer >=0', 'count': 'integer 1..3'},
    'profile_target': {'target_id': 'CHEMBL ID from the catalog'},
    'inspect_assay': {'assay_id': 'CHEMBL ID from a profile'},
    'fetch_assay': {'assay_id': 'inspected CHEMBL ID'},
    'curate_assay': {'assay_id': 'completely fetched CHEMBL ID'},
    'decide_assay': {'assay_id': 'inspected CHEMBL ID', 'verdict': 'reject or shortlist',
                     'evidence_ids': 'nonempty list of supplied evidence IDs',
                     'interpretation': 'assay_defined_inhibition',
                     'reason': 'evidence-specific reason, including compatibility and limitations'},
    'finish': {'reason': 'why sufficient progress was made or resources are insufficient'},
}


class Engine:
    def __init__(self, folder, state, client_factory=discovery.Client):
        self.folder, self.state = Path(folder), state
        self.p = state['protocol']
        self.catalog = read(self.folder / 'catalog.json')
        self.by_target = {r['target_chembl_id']: r for r in self.catalog}
        self.ordered = discovery.select_candidates(self.catalog, len(self.catalog), self.p['catalog_seed'])
        self.config = read(Path(__file__).parent / 'vendor/discovery_criteria.json')
        self.config.update(hit_threshold_nM=self.p['hit_threshold_nM'],
                           max_requests=self.p['maximum_http_requests'],
                           request_timeout_seconds=30, request_wall_deadline_seconds=60)
        self.config['review_priority_gates'] = {
            'molecule_ids_with_class_support': self.p['minimum_usable_compounds'],
            'hit_support_molecule_ids': self.p['minimum_hits'],
            'nonhit_support_molecule_ids': self.p['minimum_nonhits']}
        (self.folder / 'raw').mkdir(exist_ok=True)
        self.client = client_factory(self.folder / 'raw', self.config, state['requests'], self.checkpoint)

    def checkpoint(self):
        save(self.folder / 'state.json', self.state)

    def evidence(self, kind, value):
        index = len(self.state['evidence']) + 1
        key = f'E{index:04d}'
        relative = f'evidence/{key}_{kind}.json'
        save(self.folder / relative, value)
        self.state['evidence'][key] = {'path': relative, 'sha256': sha(self.folder / relative), 'kind': kind}
        self.checkpoint()
        return key

    def cited(self, key):
        item = self.state['evidence'][key]
        path = self.folder / item['path']
        if sha(path) != item['sha256']:
            raise ValueError('Evidence hash mismatch')
        return read(path)

    def checked_get(self, resource, params=None):
        if not re.fullmatch(r'(status|activity|target|assay/CHEMBL[0-9]+|document/CHEMBL[0-9]+)', resource):
            raise ValueError('Resource is outside the allowlisted ChEMBL tools')
        # Reuse successful identical responses across retries and process restarts.
        from urllib.parse import urlencode
        url = discovery.BASE_URL + '/' + resource + '.json'
        if params:
            url += '?' + urlencode(params)
        for entry in self.state['requests']:
            if entry.get('url') == url and entry.get('http_status') == 200 and not entry.get('error'):
                path = self.folder / entry['raw_file']
                if sha(path) != entry['sha256']:
                    raise ValueError('Cached API response hash mismatch')
                return read(path)
        return self.client.get(resource, params)

    def get(self, resource, params=None):
        """Adapter for the previously tested paginator."""
        return self.checked_get(resource, params)

    def execute(self, action, args):
        if action not in TOOLS or not isinstance(args, dict) or set(args) != set(TOOLS[action]):
            raise ValueError('Unknown tool or incorrect argument keys')
        if 'assay_id' in args:
            identifier(args['assay_id'])
        if action == 'discover_batch':
            offset, count = args['offset'], args['count']
            if type(offset) is not int or type(count) is not int or not 0 <= offset < len(self.ordered) or not 1 <= count <= 3:
                raise ValueError('Invalid catalog window')
            results = [self.profile_target(r['target_chembl_id']) for r in self.ordered[offset:offset+count]]
            return {'catalog_offset': offset, 'next_offset': offset + len(results), 'profiles': results}
        if action == 'profile_target':
            return self.profile_target(identifier(args['target_id']))
        if action == 'inspect_assay':
            return self.inspect_assay(args['assay_id'])
        if action == 'fetch_assay':
            return self.fetch_assay(args['assay_id'])
        if action == 'curate_assay':
            return self.curate_assay(args['assay_id'])
        if action == 'decide_assay':
            return self.decide_assay(**args)
        if not isinstance(args['reason'], str) or not args['reason'].strip():
            raise ValueError('Finish needs a reason')
        self.state['status'] = 'finished'
        self.state['finish_reason'] = args['reason']
        self.checkpoint()
        return {'status': 'finished', 'shortlist': self.state['shortlist']}

    def profile_target(self, target_id):
        if target_id not in self.by_target:
            raise ValueError('Target absent from the verified single-protein catalog')
        if target_id in self.state['profiles']:
            return self.state['profiles'][target_id]
        records, total, complete = discovery.read_pages(self, 'activity', 'activities',
            {'target_chembl_id': target_id, 'standard_type': 'IC50'},
            self.p['page_size'], self.p['maximum_target_window'])
        if any(r.get('target_chembl_id') != target_id or r.get('standard_type') != 'IC50' for r in records):
            raise ValueError('Activity page does not match requested scope')
        value = discovery.profile(self.by_target[target_id], records, total, complete, self.config)
        return self.store_profile(target_id, value)

    def store_profile(self, target_id, value):
        evidence_id = self.evidence('target_profile', value)
        assays = value['assay_profiles']
        ranked = sorted(assays, key=lambda a: (min(a['hit_support_ids'], a['nonhit_support_ids']), a['supported_ids']), reverse=True)
        result = {'target_id': target_id, 'name': self.by_target[target_id]['pref_name'],
                  'evidence_id': evidence_id, 'records_received': value['records_retrieved'],
                  'source_total': value['api_matching_IC50_records'], 'retrieval_complete': value['retrieval_complete'],
                  'top_assays_in_window': ranked[:6],
                  'limitation': 'API-order window; counts are source-ID support, not curated identities. Absent assays may exist outside this window.'}
        self.state['profiles'][target_id] = result
        # Keep every discovered assay addressable, even when not in the top-six summary.
        for item in assays:
            self.state['known_assays'][item['assay_chembl_id']] = target_id
        self.checkpoint()
        return result

    def import_seed_profiles(self, source):
        """Recompute prior windows from verified raw records under the NEW fixed rules."""
        source = Path(source).resolve()
        meta = read(source / 'run_metadata.json')
        groups = {}
        for entry in meta['requests']:
            url = urlparse(entry['url'])
            query = parse_qs(url.query)
            if url.hostname != 'www.ebi.ac.uk' or not url.path.endswith('/activity.json'):
                continue
            if query.get('standard_type') != ['IC50'] or len(query.get('target_chembl_id', [])) != 1:
                continue
            target = identifier(query['target_chembl_id'][0])
            path = (source / entry['raw_file']).resolve()
            if not path.is_relative_to(source) or entry.get('error') or entry.get('http_status') != 200 or sha(path) != entry.get('sha256'):
                raise ValueError('Seed activity source is not hash-verified')
            groups.setdefault(target, []).append((int(query.get('offset', ['0'])[0]), read(path), entry))
        for target, pages in groups.items():
            if target not in self.by_target:
                raise ValueError('Seed activity target absent from catalog')
            rows, total, receipts, ids = [], None, [], set()
            for offset, payload, receipt in sorted(pages, key=lambda x: x[0]):
                if offset != len(rows):
                    raise ValueError('Seed activity page missing, repeated or out of order')
                count = payload['page_meta']['total_count']
                if total is not None and count != total:
                    raise ValueError('Seed activity total changed')
                total = count
                for row in payload['activities']:
                    if row.get('target_chembl_id') != target or row.get('standard_type') != 'IC50' or row.get('activity_id') is None or row['activity_id'] in ids:
                        raise ValueError('Seed activity scope or pagination mismatch')
                    ids.add(row['activity_id'])
                    rows.append(row)
                receipts.append(receipt)
            if total is None or len(rows) > total:
                raise ValueError('Invalid seed activity total')
            raw_id = self.evidence('imported_target_window', {'target_id': target, 'records': rows,
                'source_receipts': receipts, 'source_release': self.state['release'],
                'complete': len(rows) == total, 'source_total': total})
            result = self.store_profile(target, discovery.profile(self.by_target[target], rows, total, len(rows) == total, self.config))
            result['imported_raw_evidence_id'] = raw_id
        self.checkpoint()

    def inspect_assay(self, assay_id):
        if assay_id not in self.state['known_assays']:
            raise ValueError('Assay was not discovered by a tool')
        if assay_id in self.state['assays']:
            return self.state['assays'][assay_id]['summary']
        value = self.checked_get('assay/' + assay_id)
        target = self.state['known_assays'][assay_id]
        if value.get('assay_chembl_id') != assay_id or value.get('target_chembl_id') != target:
            raise ValueError('Assay metadata does not match discovered mapping')
        document = value.get('document_chembl_id')
        doc = self.checked_get('document/' + identifier(document)) if document else None
        if doc is not None and doc.get('document_chembl_id') != document:
            raise ValueError('Document metadata ID mismatch')
        eid = self.evidence('assay_metadata', {'assay': value, 'document': doc,
            'limitation': 'ChEMBL descriptions and bibliographic metadata only; source full text has not been reviewed.'})
        fields = ['description', 'assay_type', 'confidence_score', 'relationship_type', 'assay_organism',
                  'assay_cell_type', 'bao_format', 'bao_label', 'variant_sequence', 'document_chembl_id']
        summary = {'assay_id': assay_id, 'target_id': target, 'evidence_id': eid,
                   **{k: value.get(k) for k in fields},
                   'document': {k: doc.get(k) for k in ('title', 'doi', 'pubmed_id', 'year')} if doc else None,
                   'source_full_text_reviewed': False, 'direct_binding_established': False}
        self.state['assays'][assay_id] = {'summary': summary, 'metadata': eid}
        self.checkpoint()
        return summary

    def fetch_assay(self, assay_id):
        item = self.state['assays'][assay_id]
        if 'acquisition' in item:
            return item['acquisition']
        rows, total, complete = discovery.read_pages(self, 'activity', 'activities',
            {'assay_chembl_id': assay_id, 'standard_type': 'IC50'},
            self.p['page_size'], self.p['maximum_assay_records'])
        target = self.state['known_assays'][assay_id]
        if any(r.get('assay_chembl_id') != assay_id or r.get('target_chembl_id') != target or
               r.get('standard_type') != 'IC50' for r in rows):
            raise ValueError('Assay activity scope mismatch')
        # Detect release transitions during multi-page acquisition as well as at invocation start.
        if self.client.get('status').get('chembl_db_version') != self.state['release']:
            raise ValueError('ChEMBL release changed during assay acquisition; new run/version required')
        eid = self.evidence('assay_records', {'records': rows, 'total': total, 'complete': complete,
            'scope': {'assay_id': assay_id, 'target_id': target, 'endpoint': 'IC50'}})
        result = {'evidence_id': eid, 'records_received': len(rows), 'source_total': total,
                  'complete': complete, 'eligible_for_curation': complete,
                  'reason': 'Complete within the declared single-assay IC50 scope' if complete else
                      'Record cap reached; do not curate the truncated pool as complete'}
        item['acquisition'] = result
        self.checkpoint()
        return result

    def curate_assay(self, assay_id):
        item = self.state['assays'][assay_id]
        if 'curation' in item:
            return item['curation']
        acquired = item['acquisition']
        if not acquired['complete']:
            raise ValueError('Incomplete assay acquisition cannot enter curation')
        rows = self.cited(acquired['evidence_id'])['records']
        policy = read(Path(__file__).parent / 'vendor/audit_policy.json')
        policy.update(target_chembl_id=self.state['known_assays'][assay_id], assay_chembl_id=assay_id,
                      hit_threshold_nM=self.p['hit_threshold_nM'],
                      budget_proposals=[{'name': 'prospective_draft', 'query_budget': self.p['query_budget'],
                          'initialization_queries': self.p['initialization_queries'],
                          'feedback_batch_size': self.p['feedback_batch_size']}])
        policy['diversity_policy']['maximum_compounds_for_exact_pairwise_analysis'] = self.p['maximum_pairwise_compounds']
        started = time.monotonic()
        ra, ia, compounds, sensitivity = audit.audit_records(rows, self.config, policy, discovery)
        # This is an explicit computational limit; do not replace a large pool by an unreported subset.
        d = audit.diversity(compounds, policy)
        b = audit.budget_analysis(compounds, policy['budget_proposals'])
        meta = item['summary']
        summary = {'assay_id': assay_id, 'target_id': meta['target_id'], 'complete': True,
                   'assay_type': meta['assay_type'], 'confidence_score': int(meta['confidence_score'] or 0),
                   'target_type': self.by_target[meta['target_id']]['target_type'],
                   'budget': b, 'diversity': {k: v for k, v in d.items() if k != 'clusters'},
                   'class_states_all_standardized_identities': dict(Counter(c['provisional_state'] for c in compounds)),
                   'source_ids_quarantined': sum(r['structure_status'] != 'ok' for r in ia),
                   'threshold_sensitivity': sensitivity, 'computational_seconds': time.monotonic() - started,
                   'interpretation': self.p['interpretation']}
        summary['qualification'] = qualification(summary, self.p)
        eid = self.evidence('curation', {'summary': summary, 'policy': policy, 'records': ra,
            'source_id_audit': ia, 'compounds': compounds, 'diversity': d,
            'provenance_evidence_ids': [item['metadata'], acquired['evidence_id']]})
        item['curation'] = {'evidence_id': eid, **summary}
        self.checkpoint()
        return item['curation']

    def decide_assay(self, assay_id, verdict, evidence_ids, interpretation, reason):
        item = self.state['assays'][assay_id]
        if item.get('decision'):
            existing = item['decision']
            if all(existing.get(k) == v for k, v in {'verdict': verdict, 'reason': reason,
                    'evidence_ids': evidence_ids, 'interpretation': interpretation}.items()):
                return existing  # Safe replay after a checkpoint but before runner event commit.
            raise ValueError('An assay decision is already recorded; revise only in a new run/version')
        if verdict not in ('reject', 'shortlist') or interpretation != 'assay_defined_inhibition':
            raise ValueError('Unsupported verdict or biological interpretation')
        if not isinstance(reason, str) or len(reason.strip()) < 20:
            raise ValueError('A substantive evidence-specific rationale is required')
        required = {item['metadata']}
        if 'curation' in item:
            required.add(item['curation']['evidence_id'])
        if not isinstance(evidence_ids, list) or not all(isinstance(k, str) for k in evidence_ids) or not required.issubset(evidence_ids):
            raise ValueError('Decision must cite the assay metadata and available curation evidence')
        for key in evidence_ids:
            self.cited(key)
        if verdict == 'shortlist':
            c = item.get('curation')
            if c is None or not c['qualification']['numerical_eligibility']:
                raise ValueError('Shortlist blocked by missing curation or failed fixed criteria')
            self.export_draft(assay_id)
            if assay_id not in self.state['shortlist']:
                self.state['shortlist'].append(assay_id)
        decision = {'verdict': verdict, 'reason': reason, 'evidence_ids': evidence_ids,
                    'interpretation': interpretation, 'campaign_ready': False}
        eid = self.evidence('assay_decision', decision)
        item['decision'] = {**decision, 'evidence_id': eid}
        self.checkpoint()
        return item['decision']

    def export_draft(self, assay_id):
        item = self.state['assays'][assay_id]
        curated = self.cited(item['curation']['evidence_id'])
        usable = sorted((c for c in curated['compounds'] if c['usable_for_prototype_review']), key=lambda c: c['compound_key'])
        version = signature({'protocol': self.p, 'curation_sha256': self.state['evidence'][item['curation']['evidence_id']]['sha256']})[:16]
        folder = self.folder / 'drafts' / (assay_id + '_' + version)
        public = [{'compound_id': 'cmp_' + str(i).zfill(5), 'smiles': c['standardized_smiles']} for i, c in enumerate(usable)]
        labels = [{'compound_id': pub['compound_id'], 'outcome': int(c['provisional_state'] == 'hit_support'),
                   'label_kind': 'measured_assay_outcome', 'activity_ids': c['activity_ids'],
                   'molecule_chembl_ids': c['molecule_chembl_ids'], 'document_chembl_ids': c['document_chembl_ids']}
                  for pub, c in zip(public, usable)]
        save(folder / 'public/candidates.json', public)
        save(folder / 'private/labels.json', labels)
        save(folder / 'manifest.json', {'status': 'draft_for_protocol_review_not_campaign_ready',
            'assay_id': assay_id, 'target_id': item['summary']['target_id'], 'release': self.state['release'],
            'protocol_sha256': signature(self.p), 'curation_evidence_id': item['curation']['evidence_id'],
            'candidate_count': len(public), 'candidates_sha256': sha(folder / 'public/candidates.json'),
            'private_labels_sha256': sha(folder / 'private/labels.json'),
            'unknown_and_quarantined_compounds': 'Excluded from query pool; retained in curation evidence.',
            'warning': 'Logical file split only. No OS/process isolation or oracle is provisioned. Never give campaign agent access to this run. Requires independent protocol review and new freeze.'})

    def context(self):
        return {'objective': 'Find and justify technically eligible measured single-assay screening datasets; expand discovery if evidence is inadequate. Zero shortlisted assays is allowed.',
                'protocol': self.p, 'release': self.state['release'], 'tools': TOOLS,
                'catalog_size': len(self.catalog),
                'next_unprofiled_catalog_offset': next((i for i, r in enumerate(self.ordered)
                    if r['target_chembl_id'] not in self.state['profiles']), None),
                'profiles': list(self.state['profiles'].values()), 'assays': self.state['assays'],
                'shortlist': self.state['shortlist'],
                'remaining_http_requests': self.p['maximum_http_requests'] - len(self.state['requests']),
                'remaining_llm_attempts': self.p['maximum_llm_attempts'] - self.state['llm_attempts'],
                'recent_actions': self.state['events'][-4:]}

    def report(self):
        curated = [(key, val) for key, val in self.state['assays'].items() if 'curation' in val]
        # Transparent ranking: eligibility, then smaller largest cluster, then more minority support.
        ranked = sorted(curated, key=lambda kv: (
            not kv[1]['curation']['qualification']['numerical_eligibility'],
            kv[1]['curation']['diversity']['largest_cluster_fraction'] if kv[1]['curation']['diversity']['largest_cluster_fraction'] is not None else 1,
            -min(kv[1]['curation']['budget']['hit_support_count'], kv[1]['curation']['budget']['nonhit_support_count']), kv[0]))
        report = {'status': self.state['status'], 'release': self.state['release'],
                  'profiles_examined': len(self.state['profiles']), 'assays_inspected': len(self.state['assays']),
                  'shortlist': self.state['shortlist'], 'campaign_ready': False,
                  'ranking_rule': 'Numerical eligibility, ascending largest cluster fraction, descending minority class count, assay ID. Ranking is a review aid, not a performance claim.',
                  'ranked_curated_assays': [{'assay_id': key, 'curation': val['curation'], 'decision': val.get('decision')} for key, val in ranked],
                  'llm_attempts': self.state['llm_attempts'], 'http_attempts': len(self.state['requests']),
                  'llm_usage_returned': self.state['usage'],
                  'cost_limitations': 'Token totals include invalid responses if provider returned usage. Timeouts may have unreturned usage. No monetary price is assumed. Curation costs are separate from campaign query budgets.',
                  'limitations': ['ChEMBL only; IC50/type-B scope; no assay pooling or decoys.',
                    'Partial target windows can miss better assays; all partial windows are explicit.',
                    'Assay metadata and bibliographic metadata are not full-text scientific review.',
                    'No direct binding conclusion from assay type or IC50 alone.',
                    'No campaign evaluation and no generalization claim from this curation run.']}
        save(self.folder / 'report.json', report)
        return report
