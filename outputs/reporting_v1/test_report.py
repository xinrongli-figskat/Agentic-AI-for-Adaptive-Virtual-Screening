"""Synthetic-only integration checks; no API requests or real DYRK3 labels."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from oracle_boundary_v0.oracle_boundary import deterministic_order
from . import build_report as reporting


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def fixture(root):
    public, private, frozen = (root / name for name in ("public", "private", "frozen"))
    for path in (public, private, frozen):
        path.mkdir()
    candidates = [{"compound_key": f"synthetic_{i:03d}", "standardized_smiles": "CCO"} for i in range(231)]
    outcomes = {row["compound_key"]: i % 2 for i, row in enumerate(candidates)}
    labels = [{"compound_key": key, "outcome": outcome,
               "exact_min_nM": 100 if outcome else 10000,
               "exact_max_nM": 100 if outcome else 10000} for key, outcome in outcomes.items()]
    for folder, name, rows in ((public, "candidates.jsonl", candidates), (private, "oracle_labels.jsonl", labels)):
        (folder / name).write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    public_sha, private_sha = reporting.digest(public / "candidates.jsonl"), reporting.digest(private / "oracle_labels.jsonl")
    receipt = {"status": "pre_freeze_export_not_campaign_ready", "pool_id": "synthetic"}
    put(public / "public_receipt.json", {**receipt, "candidates_sha256": public_sha})
    put(private / "private_receipt.json", {**receipt, "public_candidates_sha256": public_sha,
                                          "private_labels_sha256": private_sha})
    (frozen / "protocol_decisions.md").write_text("Synthetic-only fixture", encoding="utf-8")
    manifest = {"status": "frozen_dyrk3_v1", "pool_id": "synthetic", "project_root": str(root),
                "public_dir": str(public), "private_dir": str(private), "run_root": str(root / "runs"),
                "data_sha256": {"public_candidates": public_sha, "private_labels": private_sha},
                "source_sha256": {}, "protocol_decisions_sha256": reporting.digest(frozen / "protocol_decisions.md"),
                "campaign_spec": {"model": "glm-5.3-flash", "seeds": [0, 1, 2, 3, 4],
                                  "representations": ["bit", "count"], "initialization_queries": 10,
                                  "total_budget": 50, "batch_size": 10,
                                  "policies": ["knn_greedy", "knn_diverse", "uniform_random"]}}
    put(frozen / "manifest.json", manifest)
    frozen_sha = reporting.digest(frozen / "manifest.json")
    for rep in ("bit", "count"):
        for seed in range(5):
            initial = deterministic_order(outcomes, seed, "init")[:10]
            selected = initial + sorted(set(outcomes) - set(initial))[:40]
            for controller, name in reporting.NAMES.items():
                observed, steps = [], []
                for start in range(0, 50, 10):
                    ids = selected[start:start+10]
                    rows = [{"compound_key": key, "outcome": outcomes[key]} for key in ids]
                    step = {"stage": "initialization" if not start else f"feedback_round_{start//10}",
                            "selection": ids, "observations": rows, "selection_seconds": 0,
                            "cumulative_hits": sum(row["outcome"] for row in observed + rows)}
                    if start:
                        decision = {"policy": "knn_diverse", "reason": "Synthetic feedback only"}
                        step["decision"] = decision
                        if controller == "llm":
                            step["llm_call"] = {"model": "glm-5.3-flash", "decision": decision,
                                                "public_summary": {"revealed_observations": list(observed), "queried_count": len(observed)},
                                                "api_usage": {"prompt_tokens": 100, "completion_tokens": 10},
                                                "api_request_id": f"synthetic_{rep}_{seed}_{start}",
                                                "api_attempt_log": [{"http_status": 200, "business_code": None}],
                                                "decision_seconds": .01}
                    steps.append(step)
                    observed.extend(rows)
                run = {"controller": name, "seed": seed, "representation": rep,
                       "queried_count": 50, "hits_at_budget": steps[-1]["cumulative_hits"],
                       "hit_recovery_checkpoints": [step["cumulative_hits"] for step in steps],
                       "feature_build_seconds": 0, "selection_seconds_total": 0,
                       "decision_seconds_total": .04 if controller == "llm" else 0,
                       "trajectory": steps}
                folder = root / "runs" / f"{controller}_{rep}_seed{seed}"
                put(folder / "run.json", {"status": "complete", "frozen_manifest_sha256": frozen_sha,
                                          "controller_type": controller, "controller": name,
                                          "seed": seed, "representation": rep, "result": run})
                if controller == "llm" and rep == "count" and seed in (0, 4):
                    put(folder / "failure_events.json", [{"error_type": "ValueError", "completed_batches": 1 if seed == 0 else 3,
                                                           "public_api_diagnostic": None, "decision_seconds": None}])
    return frozen, frozen_sha


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.frozen, self.sha = fixture(self.root)
        self.patcher = patch.object(reporting, "EXPECTED_MANIFEST_SHA", self.sha)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        # Versions are tested on the real plotting integration separately.
        self.versions = patch.object(reporting.importlib.metadata, "version", return_value="synthetic")
        self.versions.start()
        self.addCleanup(self.versions.stop)

    def test_complete_collection_preserves_inputs_and_unknown_costs(self):
        before = {str(p): reporting.digest(p) for p in self.root.rglob("*") if p.is_file()}
        result = reporting.collect(self.frozen)
        self.assertEqual(result["verified_runs"], 30)
        self.assertEqual(len(result["llm_decision_trace"]), 40)
        self.assertEqual(result["known_successful_call_costs"]["prompt_tokens"], 4000)
        self.assertEqual(result["failure_telemetry"]["saved_failure_events"], 2)
        self.assertIsNone(result["failure_telemetry"]["total_failed_decision_seconds"])
        self.assertIsNone(result["failure_telemetry"]["failed_request_tokens"])
        self.assertEqual(before, {str(p): reporting.digest(p) for p in self.root.rglob("*") if p.is_file()})

    def test_missing_run_rejected(self):
        (self.root / "runs/llm_count_seed4/run.json").unlink()
        with self.assertRaisesRegex(ValueError, "Missing run"):
            reporting.collect(self.frozen)

    def test_changed_run_identity_rejected(self):
        path = self.root / "runs/llm_bit_seed0/run.json"
        saved = json.loads(path.read_text())
        saved["frozen_manifest_sha256"] = "different"
        put(path, saved)
        with self.assertRaisesRegex(ValueError, "identity/status"):
            reporting.collect(self.frozen)

    def test_unrevealed_feedback_rejected(self):
        path = self.root / "runs/llm_bit_seed0/run.json"
        saved = json.loads(path.read_text())
        saved["result"]["trajectory"][1]["llm_call"]["public_summary"]["revealed_observations"].append(
            {"compound_key": "unqueried", "outcome": 1})
        put(path, saved)
        with self.assertRaisesRegex(ValueError, "feedback/decision"):
            reporting.collect(self.frozen)


if __name__ == "__main__":
    unittest.main()
