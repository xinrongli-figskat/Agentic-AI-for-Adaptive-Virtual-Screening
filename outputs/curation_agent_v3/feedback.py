"""Typed tool feedback, active-candidate state and verifiable dispositions."""
import copy
import json

from .efficient import Engine as PreviousEngine


class Engine(PreviousEngine):
    def target_rows(self):
        rows=copy.deepcopy(super().target_rows())
        for row in rows:
            target=row['target_id']
            row['thin_profile_in_current_state']=target in self.state['profiles']
            row['prior_profile_available']=target in self.state['seed_profiles']
        return rows

    def evidence_reference(self,eid):
        if eid not in self.state['evidence']:return {'evidence_id':eid,'exists':False,'available_views':[]}
        data=self.cited(eid);meta=data.get('assay') or {};summary=data.get('summary') or {};profile=data.get('profile') or {}
        aid=meta.get('assay_chembl_id') or data.get('assay_id') or summary.get('assay_id')
        target=meta.get('target_chembl_id') or data.get('target_id') or data.get('target_chembl_id') or summary.get('target_id') or profile.get('target_chembl_id')
        if aid and not target:target=self.state['known_assays'].get(aid)
        views=['summary']
        if meta.get('description') is not None:views.append('assay_description')
        if data.get('document') is not None:views.append('document_metadata')
        views += [k for k in ['records','compounds','source_id_audit','aliases'] if k in data]
        return {'evidence_id':eid,'kind':self.state['evidence'][eid]['kind'],'assay_id':aid,'target_id':target,
            'document_id':meta.get('document_chembl_id') or summary.get('document_chembl_id'),
            'available_views':views,'sha256':self.state['evidence'][eid]['sha256']}

    def metadata_blockers(self,aid):
        item=self.state['assays'].get(aid,{});meta=item.get('summary') or {};blockers=[]
        if not meta:return blockers
        confidence=meta.get('confidence_score')
        if confidence is None or int(confidence)<self.p['minimum_confidence_score']:blockers.append('mapping_confidence')
        if meta.get('assay_type')!='B':blockers.append('assay_type_B')
        target=meta['target_id']
        if self.by_target[target]['target_type']!='SINGLE PROTEIN':blockers.append('single_protein_mapping')
        return blockers

    def assay_rows(self):
        rows=super().assay_rows()
        for row in rows:
            aid=row['assay_id'];item=self.state['assays'].get(aid,{});meta=item.get('summary') or {}
            if meta:
                row['metadata']={k:meta.get(k) for k in ['confidence_score','assay_type','document_chembl_id']}
                row['metadata']['evidence']=self.evidence_reference(item['metadata'])
                row['metadata']['description_characters']=len(meta.get('description') or '')
                row['metadata_blockers']=self.metadata_blockers(aid)
            profile=next((p for p in list(self.state['profiles'].values())+list(self.state['seed_profiles'].values())
                          if p['evidence_id']==row.get('evidence_id')),None)
            if profile and row.get('evidence_id'):
                row['preview_coverage']={'target_window_complete':profile['retrieval_complete'],
                    'records_retrieved':profile['records_received'],'matching_record_total':profile['source_total'],
                    'counts_unit':'observed source IDs before standardization; not final compound classes',
                    'partial_window_counts_are_not_assay_upper_bounds':not profile['retrieval_complete']}
        return rows

    def active_progress(self):
        aid=self.state.get('active_assay_id')
        if not aid:return None
        item=self.state['assays'].get(aid,{})
        row=next((r for r in self.assay_rows() if r['assay_id']==aid),{'assay_id':aid})
        progress={'assay':row,'suggested_tools':[],'suggestions_are_not_a_mandatory_policy':True}
        if item.get('decision'):
            progress['suggested_tools']=['choose another assay or expand target profiling'];return progress
        count=self.state['assay_counts'].get(aid)
        if count and count['below_raw_count_floor']:
            progress['count_upper_bound_blocker']=count;progress['suggested_tools']=['decide_assay: reject, basis=count_upper_bound'];return progress
        if self.metadata_blockers(aid):
            progress['suggested_tools']=['decide_assay: reject, basis=metadata_gate'];return progress
        if not item.get('metadata'):progress['suggested_tools']=['inspect_assay'];return progress
        if not count:progress['suggested_tools'].append('count_assay')
        if not self.description_read(item['metadata']):
            end=0
            for start,stop in sorted(self.state['evidence_views'].get(item['metadata']+'|assay_description',[])):
                if start>end:break
                end=max(end,stop)
            progress['next_description_read']={'evidence_id':item['metadata'],'view':'assay_description','offset':end,'limit':4000}
            progress['suggested_tools'].append('read_evidence using next_description_read');return progress
        source=item.get('source_assessment')
        if source and source['status']=='blocked' or aid in self.source_holds:
            progress['suggested_tools']=['decide_assay: hold, basis=source_problem'];return progress
        if not source:progress['suggested_tools'].append('assess_source');return progress
        acquired=item.get('acquisition')
        if not acquired:progress['suggested_tools'].append('fetch_assay');return progress
        if not acquired['complete']:progress['suggested_tools']=['decide_assay: hold, basis=resource_limit'];return progress
        if not item.get('curation'):progress['suggested_tools']=['curate_assay'];return progress
        progress['suggested_tools']=['decide_assay with basis=curation_gate according to qualification']
        return progress

    def describe_payload(self,action,result):
        payload=copy.deepcopy(result)
        if action=='inspect_assay':
            description=payload.pop('description',None) or ''
            payload['description_preview']=description[:600];payload['description_characters']=len(description)
            payload['description_preview_truncated']=len(description)>600
            # Sequence/ontology details remain available through the immutable metadata evidence.
            payload={k:v for k,v in payload.items() if k!='variant_sequence'}
        if action=='curate_assay':
            b=payload['budget'];d=payload['diversity']
            payload={k:payload[k] for k in ['assay_id','target_id','evidence_id','qualification','class_states_all_standardized_identities']}
            payload.update(usable_compounds=b['provisional_pool_size'],hits=b['hit_support_count'],nonhits=b['nonhit_support_count'],
                largest_cluster_fraction=d['largest_cluster_fraction'],scaffold_buckets=d['scaffold_count_including_acyclic_bucket'])
        serialized=json.dumps(payload,ensure_ascii=False,sort_keys=True)
        if action=='screen_targets' and len(serialized)>self.p['maximum_tool_result_characters']:
            payload={**payload,'screened':[{k:r[k] for k in ['target_id','raw_activity_count','scope','evidence_id','below_raw_count_floor']}
                      for r in payload['screened']],'names_omitted_for_size':True}
            serialized=json.dumps(payload,ensure_ascii=False,sort_keys=True)
        if len(serialized)>self.p['maximum_tool_result_characters']:
            # Never truncate an evidence page after marking it read or silently drop returned IDs.
            if action in ('read_evidence','list_assays'):raise ValueError('Required tool page exceeds reviewed payload cap')
            payload={'explicitly_truncated':True,'serialized_characters':len(serialized),'preview':serialized[:3500],
                'read_more_evidence_id':result.get('evidence_id'),'note':'Full result is in the tool event; use typed evidence to read more.'}
        return payload

    def record_feedback(self,action,args,result=None,error=None,cache_replay=False):
        eid=(result or {}).get('evidence_id') or args.get('evidence_id')
        feedback={'action':action,'arguments':copy.deepcopy(args),'status':'tool_error' if error else 'success',
            'cache_replay':cache_replay,'evidence':self.evidence_reference(eid) if eid else None}
        if error:feedback['error']={'type':type(error).__name__,'message':str(error)[:700]}
        else:feedback['payload']=self.describe_payload(action,result)
        self.state['last_tool_result']=feedback

    def read_evidence(self,evidence_id,view,offset,limit):
        result=super().read_evidence(evidence_id,view,offset,limit)
        result['evidence_identity']=self.evidence_reference(evidence_id)
        self.state['last_evidence_view']=result;self.checkpoint();return result

    def execute(self,action,args,action_reason=None):
        aid=args.get('assay_id')
        if aid:
            self.state['active_assay_id']=aid;self.state['active_target_id']=self.state['known_assays'].get(aid)
        elif args.get('target_id'):
            self.state['active_target_id']=args['target_id'];self.state['active_assay_id']=None
        item=self.state['assays'].get(aid,{})
        cache=(action=='inspect_assay' and bool(item.get('metadata')) or
               action=='count_assay' and aid in self.state['assay_counts'] or
               action=='fetch_assay' and bool(item.get('acquisition')) or action=='curate_assay' and bool(item.get('curation')))
        result=None
        try:
            result=super().execute(action,args,action_reason=action_reason)
            self.record_feedback(action,args,result=result,cache_replay=bool(cache))
        except Exception as error:
            self.record_feedback(action,args,result=result,error=error);self.checkpoint();raise
        self.checkpoint();return result

    def decide_assay(self,assay_id,verdict,evidence_ids,interpretation,reason,basis='curation_gate'):
        item=self.state['assays'][assay_id]
        count=self.state['assay_counts'].get(assay_id) or {}
        source=item.get('source_assessment') or {};curation=item.get('curation')
        remaining=self.p['maximum_llm_attempts']-self.state['llm_attempts']
        valid={
            'count_upper_bound':verdict=='reject' and count.get('below_raw_count_floor') is True,
            'metadata_gate':verdict=='reject' and bool(self.metadata_blockers(assay_id)),
            'curation_gate':bool(curation) and (verdict=='review_shortlist' and curation['qualification']['numerical_eligibility'] or
                verdict=='reject' and not curation['qualification']['numerical_eligibility']),
            'source_problem':verdict in ('reject','hold') and (assay_id in self.source_holds or source.get('status')=='blocked'),
            'resource_limit':verdict=='hold' and (remaining<=0 or len(self.state['requests'])>=self.p['maximum_http_requests'] or
                item.get('acquisition',{}).get('complete') is False)}
        if not valid.get(basis):raise ValueError('Disposition basis not established: '+str(basis)+'. A partial-window class count is not a complete assay upper bound.')
        if item.get('decision') and item['decision'].get('basis') not in (None,basis):raise ValueError('Existing decision basis is immutable')
        decision=super().decide_assay(assay_id,verdict,evidence_ids,interpretation,reason)
        if 'basis' not in decision:
            # Add a separate evidence record; never alter the original decision evidence file.
            eid=self.evidence('disposition_basis',{'assay_id':assay_id,'basis':basis,'decision_evidence_id':decision['evidence_id'],
                'metadata_blockers':self.metadata_blockers(assay_id),'count_probe':count})
            decision['basis']=basis;decision['basis_evidence_id']=eid;self.checkpoint()
        return decision

    def context(self):
        context=super().context()
        context.pop('context_characters_before_this_field',None)
        context.pop('assay_count',None);context.pop('screened_target_count',None)
        context['known_assay_ids']=len(self.state['known_assays'])
        context['target_count_units']={'IC50_B_counted_targets':sum(r['scope']=='IC50_type_B' for r in self.state['target_counts'].values()),
            'old_all_IC50_upper_bounds':sum(r['scope']=='prior_IC50_all_types_upper_bound' for r in self.state['target_counts'].values()),
            'not_complete_target_curations':True}
        context['last_tool_result']=self.state.get('last_tool_result')
        context['active_assay_progress']=self.active_progress()
        context['active_target_id']=self.state.get('active_target_id')
        revision=self.state.get('revision')
        context['experiment_state']={'status':self.state['status'],'software_version':self.p['version'],
            'post_exposure_revision':bool(revision),'prior_decisions_remain_historical':bool(revision),
            'revision':revision,
            'instruction':'For a prepared/running revision, the historical finish action is not completion of this new explicitly budgeted experiment.' if revision else
                'Current state is standalone or an offline historical rendering.'}
        context['unprofiled_data_rich_targets']=[r for r in self.target_rows() if r['scope']=='IC50_type_B' and
            not r['below_raw_count_floor'] and not r['thin_profile_in_current_state'] and not r['prior_profile_available']][:6]
        context['recent_actions']=[{'action':e.get('decision',{}).get('action'),'arguments':e.get('decision',{}).get('arguments'),
            'status':e.get('status'),'error':e.get('error'),'evidence_id':e.get('result',{}).get('evidence_id')}
            for e in self.state['events'][-3:]]
        view=context.get('last_evidence_view')
        if view:
            view=copy.deepcopy(view);view['evidence_identity']=self.evidence_reference(view['evidence_id'])
            view['same_assay_as_active']=bool(self.state.get('active_assay_id')) and view['evidence_identity'].get('assay_id')==self.state.get('active_assay_id')
            context['last_evidence_view']=view
        def size():return len(json.dumps(context,ensure_ascii=False,sort_keys=True))
        if size()>self.p['maximum_context_characters']:
            context['last_candidate_page']=None;context['target_preview']=context['target_preview'][:3]
            context['assay_preview']=context['assay_preview'][:2]
            # A complete new read_evidence page remains in last_tool_result; stale duplicate text is optional.
            if context.get('last_evidence_view'):
                context['last_evidence_view'].pop('text',None)
                context['last_evidence_view']['text_omitted_from_duplicate_view']=True
        if size()>self.p['maximum_context_characters']:raise ValueError('Typed feedback context exceeds cap; no model request made')
        return context

    def report(self):
        result=super().report();result['feedback_revision']=self.p.get('feedback_revision')
        result['known_assay_ids']=len(self.state['known_assays'])
        result['last_tool_result_action']=(self.state.get('last_tool_result') or {}).get('action')
        if self.state.get('revision'):
            result['revision']=self.state['revision'];result['new_llm_attempts']=self.state['llm_attempts']-self.state['revision']['inherited_llm_attempts']
            result['new_http_attempts']=len(self.state['requests'])-self.state['revision']['inherited_http_attempts']
            from .engine import read
            inherited=read(self.folder/'revision.json')['inherited_usage']
            result['new_returned_usage']={k:self.state['usage'][k]-inherited[k] for k in inherited}
        from .engine import save
        save(self.folder/'report.json',result);return result
