"""Prepare and execute a bounded, post-exposure Task 1 data-first revision."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from curation_agent_v3.engine import read, save, sha, signature
from curation_agent_v3.run import (
    environment, load_engine as load_v3_engine, refresh_usage, run_steps,
    single_writer, validate_protocol,
)

from .controller import GLM
from .engine import Engine

PACKAGE = Path(__file__).parent


def source_hashes():
    return {
        path.relative_to(PACKAGE).as_posix(): sha(path)
        for path in sorted(PACKAGE.rglob("*"))
        if path.is_file() and path.suffix in (".py", ".json", ".md") and "__pycache__" not in path.parts
    }


def inventory(root):
    result = {}
    for path in sorted(Path(root).rglob("*")):
        if path.is_file() and ".writer.lock" not in path.parts:
            result[path.relative_to(root).as_posix()] = sha(path)
    return result


def prepare(parent_run, output_root, additional_llm_budget, additional_http_budget, check_only=False):
    if type(additional_llm_budget) is not int or additional_llm_budget != 12:
        raise ValueError("This reviewed stage uses exactly 12 additional LLM attempts")
    if type(additional_http_budget) is not int or additional_http_budget != 100:
        raise ValueError("This reviewed stage uses exactly 100 additional ChEMBL HTTP requests")
    parent = Path(parent_run).resolve()
    output_root = Path(output_root).resolve()
    if not (parent / "raw").is_dir():
        raise ValueError("Expected the existing parent raw-cache directory; refusing to create anything in the historical run")
    if output_root.is_relative_to(parent) or parent.is_relative_to(output_root):
        raise ValueError("Parent run and new output root must be separate directories")
    parent_engine = load_v3_engine(parent)
    state = parent_engine.state
    if state.get("status") not in ("paused_at_step_limit", "llm_budget_exhausted"):
        raise ValueError("Expected the closed v3 run; no historical run was changed")
    if state.get("pending_action") is not None or state.get("shortlist"):
        raise ValueError("A pending action or draft shortlist needs separate review")
    if state["llm_attempts"] != state["protocol"]["maximum_llm_attempts"]:
        raise ValueError("Parent does not have the expected fully consumed v3 LLM budget")
    if environment() != state["environment"]:
        raise ValueError("Scientific runtime differs from the parent run")
    if not any(row.get("scope") == "IC50_type_B" for row in state.get("target_counts", {}).values()):
        raise ValueError("No reusable IC50/type-B count evidence is present")

    parent_files = inventory(parent)
    v4_sources = source_hashes()
    protocol = dict(state["protocol"])
    inherited_http = len(state["requests"])
    inherited_llm = state["llm_attempts"]
    inherited_usage = dict(state["usage"])
    protocol.update({
        "version": "task1_agent_v4.0",
        "maximum_llm_attempts": inherited_llm + additional_llm_budget,
        "maximum_http_requests": inherited_http + additional_http_budget,
        "feedback_revision": "ranked_data_first_context_v1",
    })
    validate_protocol(protocol)
    run_key = signature({
        "parent_files": parent_files,
        "v4_sources": v4_sources,
        "protocol": protocol,
        "additional_llm_budget": additional_llm_budget,
        "additional_http_budget": additional_http_budget,
    })[:16]
    folder = output_root / ("task1_v4_" + run_key)
    if check_only:
        return {"status": "ready_to_prepare_no_files_written", "would_create": str(folder),
                "parent_file_count": len(parent_files), "inherited_llm_attempts": inherited_llm,
                "inherited_http_requests": inherited_http, "additional_llm_budget": additional_llm_budget,
                "additional_http_budget": additional_http_budget, "qualification_rules_changed": False}
    if folder.exists():
        load_v4_engine(folder)
        return {"status": "existing_v4_run_reused_without_reset", "run_dir": str(folder),
                "inherited_llm_attempts": inherited_llm, "additional_llm_budget": additional_llm_budget,
                "additional_http_budget": additional_http_budget}

    output_root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(parent, folder, ignore=shutil.ignore_patterns(".writer.lock"))
    if inventory(folder) != parent_files:
        raise ValueError("Copied historical run differs from its pre-copy inventory")
    history = folder / "history_v3_parent"
    history.mkdir()
    for name in ("state.json", "report.json"):
        source = folder / name
        if source.exists():
            source.rename(history / name)
    snapshot = folder / "v4_source_snapshot"
    for relative in v4_sources:
        target = snapshot / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(PACKAGE / relative, target)
    if {rel: sha(snapshot / rel) for rel in v4_sources} != v4_sources:
        raise ValueError("Task1 v4 source snapshot failed its hash check")

    # The parent's state was moved above so it can remain byte-for-byte intact.
    # Read that historical copy, then write the v4-updated state at the run root.
    state = read(history / "state.json")
    state["protocol"] = protocol
    state["protocol_sha256"] = signature(protocol)
    state["status"] = "prepared_task1_v4_post_exposure"
    ledger = {
        "schema": "task1_v4_post_exposure_revision_v1",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "parent_run": str(parent),
        "parent_file_sha256": parent_files,
        "parent_state_sha256": sha(parent / "state.json"),
        "v4_source_sha256": v4_sources,
        "additional_llm_budget": additional_llm_budget,
        "additional_http_budget": additional_http_budget,
        "inherited_llm_attempts": inherited_llm,
        "inherited_http_requests": inherited_http,
        "inherited_usage": inherited_usage,
        "criteria_changed": False,
        "prior_exposure": "Earlier DYRK3, Task1 v1-v3 data and results were seen; not blind validation.",
        "source_scope": "ChEMBL_37 catalog and hash-verified v3 evidence; fresh calls must confirm release before continuing.",
    }
    save(folder / "v4_experiment.json", ledger)
    state["v4_experiment"] = {
        "ledger_sha256": sha(folder / "v4_experiment.json"),
        "inherited_llm_attempts": inherited_llm,
        "inherited_http_requests": inherited_http,
        "inherited_usage": inherited_usage,
        "additional_llm_budget": additional_llm_budget,
        "additional_http_budget": additional_http_budget,
    }
    state["events"].append({
        "kind": "task1_v4_search_efficiency_revision_prepared",
        "criteria_changed": False,
        "prior_results_rewritten": False,
        "new_budget": {"llm_attempts": additional_llm_budget, "http_requests": additional_http_budget},
    })
    save(folder / "state.json", state)
    if inventory(parent) != parent_files:
        raise ValueError("Parent run changed during preparation")
    prepared = load_v4_engine(folder)
    refresh_usage(prepared)
    prepared.report()
    return {"status": "prepared_no_network_no_glm", "run_dir": str(folder),
            "inherited_llm_attempts": inherited_llm, "inherited_http_requests": inherited_http,
            "additional_llm_budget": additional_llm_budget, "additional_http_budget": additional_http_budget,
            "qualification_rules_changed": False, "candidate_count": len(state.get("target_counts", {}))}


def load_v4_engine(folder):
    folder = Path(folder).resolve()
    state = read(folder / "state.json")
    exp = state.get("v4_experiment")
    if not exp or sha(folder / "v4_experiment.json") != exp.get("ledger_sha256"):
        raise ValueError("Missing or changed Task1 v4 experiment ledger")
    ledger = read(folder / "v4_experiment.json")
    for relative, wanted in ledger["v4_source_sha256"].items():
        if sha(folder / "v4_source_snapshot" / relative) != wanted:
            raise ValueError("Task1 v4 source snapshot mismatch")
        if source_hashes().get(relative) != wanted:
            raise ValueError("Task1 v4 source changed; create a new run/version")
    for relative, wanted in ledger["parent_file_sha256"].items():
        historical = Path("history_v3_parent") / relative if relative in ("state.json", "report.json") else Path(relative)
        if sha(folder / historical) != wanted:
            raise ValueError("Inherited v3 parent file changed: " + relative)
    # The unchanged v3 loader verifies all inherited evidence, API receipts and code snapshot.
    load_v3_engine(folder)
    engine = Engine(folder, state)
    return engine


def summary(report):
    return {key: report.get(key) for key in (
        "status", "software_version", "release", "profiles_examined", "assays_inspected",
        "review_shortlist", "campaign_ready", "llm_attempts", "new_llm_attempts",
        "http_attempts", "new_http_requests", "llm_usage_returned", "new_returned_tokens")}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("--parent-run", type=Path, required=True)
    prep.add_argument("--output-root", type=Path, required=True)
    prep.add_argument("--additional-llm-budget", type=int, required=True)
    prep.add_argument("--additional-http-budget", type=int, required=True)
    prep.add_argument("--check-only", action="store_true")
    for name in ("execute", "status"):
        cmd = commands.add_parser(name)
        cmd.add_argument("--run-dir", type=Path, required=True)
        if name == "execute":
            cmd.add_argument("--steps", type=int, default=8)
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(args.parent_run, args.output_root, args.additional_llm_budget,
                         args.additional_http_budget, args.check_only)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    if args.command == "execute" and not 1 <= args.steps <= 12:
        parser.error("--steps must be 1..12")
    with single_writer(args.run_dir):
        engine = load_v4_engine(args.run_dir)
        refresh_usage(engine)
        if args.command == "status":
            report = engine.report()
        else:
            from curation_agent_v3.run import check_release
            check_release(engine)
            report = run_steps(engine, GLM(engine.p), args.steps)
        print(json.dumps(summary(report), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
