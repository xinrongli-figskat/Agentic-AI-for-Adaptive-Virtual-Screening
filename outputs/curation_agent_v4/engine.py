"""Stage-aware view over the unchanged, hash-pinned v3 curation tools."""
from __future__ import annotations

import copy

from curation_agent_v3.feedback import Engine as V3Engine


class Engine(V3Engine):
    def target_queue(self, limit=8):
        rows = []
        excluded = set(self.state.get("profiles", {})) | set(self.state.get("seed_profiles", {}))
        for target_id, row in self.state.get("target_counts", {}).items():
            if row.get("scope") != "IC50_type_B" or target_id in excluded:
                continue
            count = int(row.get("raw_activity_count", 0))
            if count < self.p["minimum_usable_compounds"]:
                continue
            rows.append({
                "target_id": target_id,
                "name": row.get("name"),
                "raw_ic50_type_b_activity_records": count,
                "count_evidence_id": row.get("evidence_id"),
                "status": "unprofiled_count_only",
                "action_hint": "profile_target; count is not a compound count",
            })
        rows.sort(key=lambda r: (-r["raw_ic50_type_b_activity_records"], r["target_id"]))
        return rows[:limit]

    def assay_queue(self, limit=10):
        rows = copy.deepcopy(self.assay_rows())
        ranked = []
        for row in rows:
            counts = row.get("prior_or_preview_source_id_counts") or {}
            if not counts:
                continue
            hits = int(counts.get("hit_support_ids", 0))
            nonhits = int(counts.get("nonhit_support_ids", 0))
            row["preview_minority_class_support"] = min(hits, nonhits)
            row["preview_interpretation"] = "source-ID support only; pre-standardization and not a label set"
            item = self.state.get("assays", {}).get(row["assay_id"], {})
            decision = (item.get("decision") or {}).get("verdict")
            source_status = (item.get("source_assessment") or {}).get("status")
            curated = bool(item.get("curation"))
            held = bool(row.get("source_hold")) or source_status == "blocked"
            ranked.append({
                "assay_id": row["assay_id"],
                "target_id": row["target_id"],
                "target_name": row.get("target_name"),
                "hit_support_ids": hits,
                "nonhit_support_ids": nonhits,
                "supported_ids": int(counts.get("supported_ids", 0)),
                "preview_minority_class_support": min(hits, nonhits),
                "target_window_complete": row.get("preview_coverage", {}).get("target_window_complete"),
                "prior_decision": decision,
                "source_assessment_status": source_status,
                "source_hold": held,
                "curation_completed": curated,
                "already_reviewed": bool(decision or held or curated),
                "preview_interpretation": "source-ID supports before structure standardization; not labels",
            })
        ranked.sort(key=lambda r: (
            r["already_reviewed"],
            bool(r.get("source_hold")),
            -r["preview_minority_class_support"],
            -r["supported_ids"],
            r["assay_id"],
        ))
        return ranked[:limit]

    def context(self):
        context = super().context()
        context["next_stage"] = {
            "purpose": "Use prior count evidence to choose a few data-rich, not-yet-profiled targets, then use assay evidence to select source-review actions.",
            "target_queue_is_ranked_by": "IC50/type-B activity record count, descending; this is a search priority, not qualification.",
            "target_queue": self.target_queue(limit=4),
            "assay_preview_queue": self.assay_queue(limit=8),
            "additional_llm_attempts_remaining": max(0, self.p["maximum_llm_attempts"] - self.state["llm_attempts"]),
            "additional_http_requests_remaining": max(0, self.p["maximum_http_requests"] - len(self.state["requests"])),
            "criteria_changed": False,
            "historical_results_are_already_seen": True,
        }
        return context

    def report(self):
        report = super().report()
        experiment = self.state.get("v4_experiment", {})
        report.update({
            "software_version": "task1_agent_v4.0",
            "new_llm_attempts": self.state["llm_attempts"] - experiment.get("inherited_llm_attempts", self.state["llm_attempts"]),
            "new_http_requests": len(self.state["requests"]) - experiment.get("inherited_http_requests", len(self.state["requests"])),
            "new_returned_tokens": {
                key: self.state["usage"].get(key, 0) - experiment.get("inherited_usage", {}).get(key, 0)
                for key in ("prompt_tokens", "completion_tokens", "total_tokens")
            },
            "prior_exposure": "All inherited scientific data and results were previously seen; this run is a post-exposure search/software extension.",
        })
        from curation_agent_v3.engine import save
        save(self.folder / "report.json", report)
        return report
