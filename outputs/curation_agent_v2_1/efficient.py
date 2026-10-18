"""Data-first retrieval, bounded evidence views, source holds and compact state."""
import json
import re
from collections import Counter
from urllib.parse import urlencode

from .engine import Engine as LegacyEngine, identifier, read, sha, save, signature
from .vendor import discovery

TOOLS={
 'screen_targets': {'count':'integer 1..16; count-only queries, program ranks results'},
 'profile_target': {'target_id':'CHEMBL ID; only targets with sufficient IC50/B count are profiled'},
 'list_assays': {'target_id':'CHEMBL ID','offset':'integer >=0','limit':'integer 1..20'},
 'count_assay': {'assay_id':'discovered CHEMBL ID; metadata count is not a compound count'},
 'inspect_assay': {'assay_id':'discovered CHEMBL ID; inspect full metadata before a source assessment'},
 'fetch_assay': {'assay_id':'inspected CHEMBL ID; complete acquisition needed for curation'},
 'curate_assay': {'assay_id':'completely fetched CHEMBL ID'},
 'inspect_source_aliases': {'assay_id':'completely fetched CHEMBL ID; database aliases, not full-text review'},
 'read_evidence': {'evidence_id':'supplied E#### ID','view':'summary, assay_description, document_metadata, records, compounds, source_id_audit, aliases',
                   'offset':'character offset >=0','limit':'integer 1..4000'},
 'list_candidates': {'kind':'targets, assays, evidence','offset':'integer >=0','limit':'integer 1..12'},
 'assess_source': {'assay_id':'inspected assay whose full description was read',
                  'endpoint':'scientifically interpreted endpoint','construct_or_receptor':'specific construct/receptor or unresolved',
                  'status':'primary_review_required or blocked','evidence_ids':'list of evidence IDs'},
 'decide_assay': {'assay_id':'inspected assay','verdict':'reject, hold, or review_shortlist',
                  'evidence_ids':'list of metadata/curation/source-assessment evidence IDs',
                  'interpretation':'assay_defined_inhibition'},
 'finish': {}
}

RATIONALE_TOOLS={'assess_source','decide_assay','finish'}

THIN_FIELDS=['activity_id','assay_chembl_id','target_chembl_id','document_chembl_id','molecule_chembl_id',
             'canonical_smiles','standard_type','standard_units','standard_value','standard_relation',
             'assay_type','data_validity_comment','potential_duplicate']


class Engine(LegacyEngine):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.source_holds=read(__import__('pathlib').Path(__file__).parent/'source_holds.json')['holds']
        prior=self.state.get('seed_profiles',{})
        priority=sorted((key for key,p in prior.items() if p['source_total']>=self.p['minimum_usable_compounds']),
                        key=lambda k:(-max((r['supported_ids'] for r in prior[k]['top_assays_in_window']),default=0),k))
        self.screening_order=priority+[r['target_chembl_id'] for r in self.ordered if r['target_chembl_id'] not in priority]

    def checked_get(self,resource,params=None):
        if not re.fullmatch(r'(status|activity|target|assay|compound_record|assay/CHEMBL[0-9]+|document/CHEMBL[0-9]+)',resource):
            raise ValueError('Resource outside allowlisted scientific tools')
        url=discovery.BASE_URL+'/'+resource+'.json'+('?' + urlencode(params) if params else '')
        for entry in self.state['requests']:
            if entry.get('url')==url and entry.get('http_status')==200 and not entry.get('error'):
                path=self.folder/entry['raw_file']
                if sha(path)!=entry['sha256']:raise ValueError('Cached API response hash mismatch')
                return read(path)
        return self.client.get(resource,params)

    @staticmethod
    def page(payload,key,limit):
        rows=payload.get(key);total=payload.get('page_meta',{}).get('total_count')
        if not isinstance(rows,list) or type(total) is not int or total<0 or len(rows)>limit:
            raise ValueError('Malformed API page/count')
        return rows,total

    def count_target(self,target_id):
        identifier(target_id)
        if target_id not in self.by_target:raise ValueError('Unknown catalog target')
        old=self.state['target_counts'].get(target_id)
        if old and old['scope']=='IC50_type_B':return old
        payload=self.checked_get('activity',{'target_chembl_id':target_id,'standard_type':'IC50',
            'assay_type':'B','only':'activity_id,target_chembl_id,standard_type,assay_type','limit':1,'offset':0})
        rows,total=self.page(payload,'activities',1)
        if (total>0 and not rows) or any(r.get('target_chembl_id')!=target_id or r.get('standard_type')!='IC50' or r.get('assay_type')!='B' for r in rows):
            raise ValueError('Count probe scope mismatch')
        eid=self.evidence('target_count',{'target_id':target_id,'raw_activity_count':total,
            'scope':'IC50_type_B','meaning':'record count is an upper bound on usable identities, not class coverage'})
        result={'target_id':target_id,'name':self.by_target[target_id]['pref_name'],'raw_activity_count':total,
                'scope':'IC50_type_B','evidence_id':eid,
                'below_raw_count_floor':total<self.p['minimum_usable_compounds']}
        self.state['target_counts'][target_id]=result;self.checkpoint()
        return result

    def screen_targets(self,count):
        if type(count) is not int or not 1<=count<=16:raise ValueError('count must be 1..16')
        pending=[k for k in self.screening_order if k not in self.state['target_counts'] or
                 (self.state['target_counts'][k]['scope']!='IC50_type_B' and not self.state['target_counts'][k]['below_raw_count_floor'])]
        results=[]
        for target in pending[:count]:results.append(self.count_target(target))
        return {'screened':results,'remaining_unprobed_targets':max(0,len(pending)-len(results)),
                'meaning':'cheap numerical prefilter only; no structural qualification or whole-database claim'}

    def profile_target(self,target_id):
        identifier(target_id)
        if target_id in self.state['profiles']:return self.state['profiles'][target_id]
        count=self.count_target(target_id)
        if count['below_raw_count_floor']:
            return {**count,'not_profiled':'raw record upper bound below minimum; no full activity window fetched'}
        params={'target_chembl_id':target_id,'standard_type':'IC50','assay_type':'B','only':','.join(THIN_FIELDS)}
        rows,total,complete=discovery.read_pages(self,'activity','activities',params,self.p['page_size'],self.p['maximum_target_window'])
        if total!=count['raw_activity_count']:raise ValueError('Count changed since screening')
        if any(r.get('target_chembl_id')!=target_id or r.get('standard_type')!='IC50' or r.get('assay_type')!='B' for r in rows):
            raise ValueError('Thin activity scope mismatch')
        value=discovery.profile(self.by_target[target_id],rows,total,complete,self.config)
        value['projection_fields']=THIN_FIELDS
        value['raw_count_scope']='IC50_type_B'
        raw=self.evidence('thin_target_window',{'target_id':target_id,'records':rows,'total':total,'complete':complete})
        result=self.store_profile(target_id,value)
        result['raw_evidence_id']=raw;self.checkpoint()
        return result

    def list_assays(self,target_id,offset,limit):
        identifier(target_id)
        if target_id not in self.by_target or type(offset) is not int or offset<0 or type(limit) is not int or not 1<=limit<=20:
            raise ValueError('Invalid assay catalog window')
        data=self.checked_get('assay',{'target_chembl_id':target_id,'assay_type':'B',
            'confidence_score__gte':self.p['minimum_confidence_score'],
            'only':'assay_chembl_id,target_chembl_id,assay_type,confidence_score,document_chembl_id',
            'offset':offset,'limit':limit,'order_by':'assay_chembl_id'})
        rows,total=self.page(data,'assays',limit)
        for r in rows:
            identifier(r.get('assay_chembl_id'))
            if (r.get('target_chembl_id')!=target_id or r.get('assay_type')!='B' or
                    type(r.get('confidence_score')) is not int or r['confidence_score']<self.p['minimum_confidence_score']):
                raise ValueError('Assay catalog scope mismatch')
            self.state['known_assays'][r['assay_chembl_id']]=target_id
        eid=self.evidence('assay_catalog_page',{'target_id':target_id,'rows':rows,'offset':offset,'total':total})
        self.checkpoint()
        return {'evidence_id':eid,'rows':rows,'total':total,'next_offset':offset+len(rows) if offset+len(rows)<total else None}

    def count_assay(self,assay_id):
        if assay_id not in self.state['known_assays']:raise ValueError('Assay not discovered')
        if assay_id in self.state['assay_counts']:return self.state['assay_counts'][assay_id]
        data=self.checked_get('activity',{'assay_chembl_id':assay_id,'standard_type':'IC50',
            'only':'activity_id,assay_chembl_id,standard_type','limit':1,'offset':0})
        rows,total=self.page(data,'activities',1)
        if (total>0 and not rows) or any(r.get('assay_chembl_id')!=assay_id or r.get('standard_type')!='IC50' for r in rows):
            raise ValueError('Assay count scope mismatch')
        eid=self.evidence('assay_count',{'assay_id':assay_id,'raw_activity_count':total,'is_compound_count':False})
        result={'evidence_id':eid,'raw_activity_count':total,'below_raw_count_floor':total<self.p['minimum_usable_compounds']}
        self.state['assay_counts'][assay_id]=result;self.checkpoint()
        return result

    def inspect_source_aliases(self,assay_id):
        item=self.state['assays'][assay_id]
        if not item.get('acquisition',{}).get('complete'):raise ValueError('Complete assay required')
        if 'source_aliases' in item:return item['source_aliases']
        doc=item['summary']['document_chembl_id']
        data=self.checked_get('compound_record',{'document_chembl_id':doc,'limit':1000,'offset':0})
        records,total=self.page(data,'compound_records',1000)
        complete=not data['page_meta'].get('next') and len(records)==total
        ids={r['record_id'] for r in self.cited(item['acquisition']['evidence_id'])['records']}
        selected=[r for r in records if r.get('record_id') in ids]
        aliases=[]
        for r in selected:
            names=re.findall(r'US\d+,\s*Example\s+\d+(?:\s+Isomer\s+\d+)?',r.get('compound_name') or '')
            if len(set(names))>1:aliases.append({'record_id':r['record_id'],'molecule_id':r['molecule_chembl_id'],'aliases':names})
        summary={'assay_id':assay_id,'complete_document_records':complete,'matched_assay_record_ids':len(selected),
                 'assay_record_ids':len(ids),'multi_alias_source_ids':len(aliases),'source_full_text_reviewed':False,
                 'limitation':'Aliases may be different patents or stereoisomers; neither numeric match nor shared molecule ID verifies primary sample identity.'}
        eid=self.evidence('source_aliases',{'summary':summary,'aliases':aliases,'records':selected})
        item['source_aliases']={**summary,'evidence_id':eid};self.checkpoint()
        return item['source_aliases']

    def read_evidence(self,evidence_id,view,offset,limit):
        if evidence_id not in self.state['evidence']:raise ValueError('Unknown evidence ID')
        if type(offset) is not int or offset<0 or type(limit) is not int or not 1<=limit<=self.p['maximum_evidence_page_characters']:
            raise ValueError('Invalid evidence character window')
        data=self.cited(evidence_id)
        if view=='assay_description':value=data.get('assay',{}).get('description')
        elif view=='document_metadata':value=data.get('document')
        elif view=='summary':value=data.get('summary',data)
        elif view in ('records','compounds','source_id_audit','aliases'):value=data.get(view)
        else:raise ValueError('Unknown evidence view')
        if value is None:raise ValueError('View absent from this evidence')
        serialized=value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,sort_keys=True)
        if offset>len(serialized):raise ValueError('Evidence offset exceeds content')
        end=min(offset+limit,len(serialized))
        result={'evidence_id':evidence_id,'view':view,'offset':offset,'end':end,'total_characters':len(serialized),
                'text':serialized[offset:end],'truncated':end<len(serialized),'next_offset':end if end<len(serialized) else None}
        self.state['last_evidence_view']=result
        key=evidence_id+'|'+view
        self.state['evidence_views'].setdefault(key,[]).append([offset,end])
        self.checkpoint();return result

    def description_read(self,eid):
        description=self.cited(eid)['assay'].get('description') or ''
        end=0
        for start,stop in sorted(self.state['evidence_views'].get(eid+'|assay_description',[])):
            if start>end:break
            end=max(end,stop)
        return bool(description) and end>=len(description)

    def assess_source(self,assay_id,endpoint,construct_or_receptor,status,evidence_ids,reason):
        item=self.state['assays'][assay_id]
        if item.get('decision'):raise ValueError('Source assessment cannot change after an assay disposition')
        if not self.description_read(item['metadata']):raise ValueError('Read complete assay_description before source assessment')
        if status not in ('primary_review_required','blocked'):raise ValueError('No automatic source approval tool exists')
        if not all(isinstance(v,str) and 5<=len(v)<=1200 for v in [endpoint,construct_or_receptor,reason]):
            raise ValueError('Specific source assessment text required')
        if not isinstance(evidence_ids,list) or item['metadata'] not in evidence_ids:raise ValueError('Cite assay metadata')
        for eid in evidence_ids:self.cited(eid)
        if assay_id in self.source_holds and status!='blocked':raise ValueError('Reviewed source hold cannot be removed by model')
        value={'assay_id':assay_id,'endpoint':endpoint,'construct_or_receptor':construct_or_receptor,
               'status':status,'evidence_ids':evidence_ids,'reason':reason,'source_full_text_reviewed':False,
               'scientific_review_complete':False,'campaign_ready':False}
        eid=self.evidence('source_assessment',value)
        item['source_assessment']={**value,'evidence_id':eid};self.checkpoint()
        return item['source_assessment']

    def export_draft(self,assay_id):
        super().export_draft(assay_id)
        item=self.state['assays'][assay_id]
        version=signature({'protocol':self.p,'curation_sha256':self.state['evidence'][item['curation']['evidence_id']]['sha256']})[:16]
        path=self.folder/'drafts'/(assay_id+'_'+version)/'manifest.json'
        manifest=read(path)
        manifest.update(status='review_shortlist_draft_not_scientifically_approved_not_campaign_ready',
            tier=item['curation']['qualification']['tier'],source_assessment=item['source_assessment'],
            source_assessment_sha256=self.state['evidence'][item['source_assessment']['evidence_id']]['sha256'],
            prior_exposure_sha256=self.state['prior_exposure_sha256'])
        save(path,manifest)

    def decide_assay(self,assay_id,verdict,evidence_ids,interpretation,reason):
        item=self.state['assays'][assay_id]
        if verdict not in ('reject','hold','review_shortlist') or interpretation!='assay_defined_inhibition':
            raise ValueError('Invalid reviewed disposition')
        if not isinstance(reason,str) or not 20<=len(reason)<=2000:raise ValueError('Substantive bounded rationale required')
        if item.get('decision'):
            old=item['decision']
            if all(old.get(k)==v for k,v in {'verdict':verdict,'reason':reason,'evidence_ids':evidence_ids,'interpretation':interpretation}.items()):return old
            raise ValueError('Existing decisions are immutable within a run')
        required={item['metadata']}
        if 'curation' in item:required.add(item['curation']['evidence_id'])
        if 'source_assessment' in item:required.add(item['source_assessment']['evidence_id'])
        if not isinstance(evidence_ids,list) or not required.issubset(evidence_ids):raise ValueError('Missing required evidence citations')
        for eid in evidence_ids:self.cited(eid)
        if verdict=='review_shortlist':
            if assay_id in self.source_holds:raise ValueError('Known primary source hold blocks shortlist')
            source=item.get('source_assessment',{})
            if source.get('status')!='primary_review_required':raise ValueError('Source assessment required; blocked evidence cannot shortlist')
            if not item.get('curation',{}).get('qualification',{}).get('numerical_eligibility'):
                raise ValueError('Missing curation or numerical gate failure')
            self.export_draft(assay_id)
            if assay_id not in self.state['shortlist']:self.state['shortlist'].append(assay_id)
        value={'verdict':verdict,'reason':reason,'evidence_ids':evidence_ids,'interpretation':interpretation,
               'scientific_review_complete':False,'campaign_ready':False}
        eid=self.evidence('assay_decision',value)
        item['decision']={**value,'evidence_id':eid};self.checkpoint();return item['decision']

    def target_rows(self):
        rows=list(self.state['target_counts'].values())
        return sorted(rows,key=lambda r:(r['below_raw_count_floor'],-r['raw_activity_count'],r['target_id']))

    def assay_rows(self):
        rows={}
        for profile in list(self.state['seed_profiles'].values())+list(self.state['profiles'].values()):
            for a in profile['top_assays_in_window']:
                aid=a['assay_chembl_id']
                rows[aid]={'assay_id':aid,'target_id':profile['target_id'],
                    'prior_or_preview_source_id_counts':{k:a[k] for k in ['supported_ids','hit_support_ids','nonhit_support_ids']},
                    'evidence_id':profile['evidence_id']}
        for aid,target in self.state['known_assays'].items():rows.setdefault(aid,{'assay_id':aid,'target_id':target})
        for aid,row in rows.items():
            if aid in self.source_holds:row['source_hold']=self.source_holds[aid]
            if aid in self.state['assay_counts']:row['raw_count_probe']=self.state['assay_counts'][aid]
            item=self.state['assays'].get(aid,{})
            row['metadata_evidence_id']=item.get('metadata')
            row['description_read']=self.description_read(item['metadata']) if item.get('metadata') else False
            if item.get('acquisition'):row['acquisition']={k:item['acquisition'][k] for k in ['evidence_id','records_received','complete']}
            if item.get('curation'):
                c=item['curation'];b=c['budget']
                row['curation']={'evidence_id':c['evidence_id'],'pool':b['provisional_pool_size'],
                    'hits':b['hit_support_count'],'nonhits':b['nonhit_support_count'],'qualification':c['qualification']}
            if item.get('source_assessment'):
                source=item['source_assessment']
                row['source_assessment']={k:source[k] for k in ['evidence_id','status']}
                row['source_assessment'].update({k:source[k][:200] for k in ['endpoint','construct_or_receptor']})
            if item.get('decision'):row['decision']={k:item['decision'][k] for k in ['evidence_id','verdict']}
        def rank(r):
            counts=r.get('prior_or_preview_source_id_counts',{})
            raw=r.get('raw_count_probe',{})
            return (bool(r.get('decision')),bool(r.get('source_hold')),raw.get('below_raw_count_floor',False),
                    -min(counts.get('hit_support_ids',0),counts.get('nonhit_support_ids',0)),
                    -counts.get('supported_ids',raw.get('raw_activity_count',0)),r['assay_id'])
        return sorted(rows.values(),key=rank)

    def list_candidates(self,kind,offset,limit):
        if kind not in ('targets','assays','evidence') or type(offset) is not int or offset<0 or type(limit) is not int or not 1<=limit<=12:
            raise ValueError('Invalid candidate page')
        rows=self.target_rows() if kind=='targets' else self.assay_rows() if kind=='assays' else [
            {'evidence_id':key,'kind':value['kind']} for key,value in self.state['evidence'].items()]
        selected=rows[offset:offset+limit]
        while len(selected)>1 and len(json.dumps(selected,ensure_ascii=False))>self.p['maximum_evidence_page_characters']:
            selected.pop()
        result={'kind':kind,'offset':offset,'rows':selected,'total':len(rows),
                'next_offset':offset+len(selected) if offset+len(selected)<len(rows) else None,
                'requested_limit':limit,'returned_rows':len(selected),'bounded_page':True}
        self.state['last_candidate_page']=result;self.checkpoint();return result

    def execute(self,action,args,action_reason=None):
        if action not in TOOLS or not isinstance(args,dict) or set(args)!=set(TOOLS[action]):raise ValueError('Unknown tool or incorrect argument keys')
        if 'assay_id' in args:identifier(args['assay_id'])
        if action in RATIONALE_TOOLS:
            if not isinstance(action_reason,str) or not 20<=len(action_reason.strip())<=1200:
                raise ValueError('A single substantive top-level reason is required')
            args={**args,'reason':action_reason}
        if action=='finish':
            if not isinstance(args['reason'],str) or not args['reason'].strip():raise ValueError('Finish needs rationale')
            self.state['status']='finished';self.state['finish_reason']=args['reason'];self.checkpoint()
            return {'status':'finished','review_shortlist':self.state['shortlist'],'campaign_ready':False}
        return getattr(self,action)(**args)

    def context(self):
        targets=self.target_rows();assays=self.assay_rows()
        compact_protocol={k:self.p[k] for k in ['version','hit_threshold_nM','minimum_usable_compounds',
            'preferred_usable_compounds','minimum_hits','minimum_nonhits','minimum_confidence_score',
            'maximum_largest_cluster_fraction','minimum_scaffold_buckets','maximum_initial_single_class_probability',
            'query_budget','initialization_queries','feedback_batch_size','maximum_query_fraction']}
        context={'objective':'Numerically screen and scientifically triage measured single-assay candidates; all shortlisted drafts still require primary source/sample identity and campaign review.',
            'protocol':compact_protocol,'release':self.state['release'],'tools':TOOLS,
            'catalog_size':len(self.catalog),'screened_target_count':len(targets),'target_preview':targets[:self.p['context_target_limit']],
            'assay_count':len(assays),'assay_preview':assays[:self.p['context_assay_limit']],
            'source_holds':self.source_holds,'shortlist':self.state['shortlist'],
            'remaining_http_requests':self.p['maximum_http_requests']-len(self.state['requests']),
            'remaining_llm_attempts':self.p['maximum_llm_attempts']-self.state['llm_attempts'],
            'recent_actions':[{'action':e.get('decision',{}).get('action'),'status':e.get('status'),
                              'error':e.get('error'),'evidence_id':e.get('result',{}).get('evidence_id')}
                             for e in self.state['events'][-3:]],
            'last_evidence_view':self.state.get('last_evidence_view'),
            'last_candidate_page':self.state.get('last_candidate_page'),
            'format_feedback':self.state.get('format_feedback'),
            'decision_interface':'Exactly action, arguments, reason. Reason exists ONLY at $.reason, NEVER in $.arguments. Program passes it to rationale-taking tools.',
            'full_history_and_evidence':'Not included by default; use read_evidence/list_candidates. No source full-text tool or source approval tool exists.'}
        # Drop optional duplicate previews first, never silently trim returned evidence.
        serialized=json.dumps(context,ensure_ascii=False,sort_keys=True)
        if len(serialized)>self.p['maximum_context_characters']:
            context['last_candidate_page']=None;context['target_preview']=context['target_preview'][:3];context['assay_preview']=context['assay_preview'][:3]
            serialized=json.dumps(context,ensure_ascii=False,sort_keys=True)
        if len(serialized)>self.p['maximum_context_characters']:raise ValueError('Compact context limit exceeded; no model request made')
        context['context_characters_before_this_field']=len(serialized)
        if len(json.dumps(context,ensure_ascii=False,sort_keys=True))>self.p['maximum_context_characters']:
            raise ValueError('Final compact context exceeds cap; no model request made')
        return context

    def report(self):
        result=super().report()
        result.update(schema='task1_agent_v2.1',target_count_probes=len(self.state.get('target_counts',{})),
            fresh_target_count_probes=sum(r['scope']=='IC50_type_B' for r in self.state.get('target_counts',{}).values()),
            imported_target_upper_bounds=sum(r['scope']=='prior_IC50_all_types_upper_bound' for r in self.state.get('target_counts',{}).values()),
            review_shortlist=result['shortlist'],source_holds=self.source_holds,
            qualification_tiers={'preferred':self.p['preferred_usable_compounds'],'limited_feasibility':self.p['minimum_usable_compounds']},
            prior_exposure_sha256=self.state.get('prior_exposure_sha256'),format_correction_limit=self.p['maximum_format_corrections'],
            llm_attempts_without_returned_usage=self.state.get('llm_attempts_without_returned_usage',0),
            scientific_review_complete=False)
        if self.state.get('continuation'):
            result['continuation']=self.state['continuation']
            result['inherited_budget_is_not_reset']=True
        result['limitations']+=['Pre-counts are records, not standardized compound counts. Target/assay windows and catalog coverage are bounded.',
            'Smaller review tier was chosen after previous data/results were seen; not an independent blind protocol.',
            'Source alias retrieval is database provenance only; neither full-text review nor confirmation of all stereochemical identities.',
            'Current scope still SINGLE PROTEIN; P2X2/3 complex requires a separately reviewed scope/version.']
        save(self.folder/'report.json',result);return result
