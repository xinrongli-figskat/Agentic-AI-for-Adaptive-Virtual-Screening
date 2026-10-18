"""Private-side launcher for one frozen DYRK3 retrospective campaign.

Never pass this launcher, its filesystem access, or its private paths to the
LLM. The model receives only the summary built by ToolChoiceLLMController.
"""

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from oracle_boundary_v0.oracle_boundary import BatchOracle, read_json, read_jsonl, sha256_file, verify_prepared

from .campaign_core import FixedController, RandomController, run_campaign
from .glm_api import GLMAPIError, OfficialGLMDecisionClient
from .llm_controller import ToolChoiceLLMController


CONTROLLERS = ("llm", "fixed", "random")


def atomic_json(path, value):
    temp = path.with_suffix(".tmp")
    with temp.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    temp.replace(path)


def load_frozen_manifest(frozen_dir):
    manifest = read_json(Path(frozen_dir) / "manifest.json")
    if manifest.get("status") != "frozen_dyrk3_v1":
        raise ValueError("Manifest is not a frozen DYRK3 v1 version")
    public_dir = Path(manifest["public_dir"])
    private_dir = Path(manifest["private_dir"])
    verification = verify_prepared(public_dir, private_dir)
    if verification["pool_id"] != manifest["pool_id"] or \
       verification["public_sha256"] != manifest["data_sha256"]["public_candidates"] or \
       sha256_file(private_dir / "oracle_labels.jsonl") != manifest["data_sha256"]["private_labels"]:
        raise ValueError("Frozen pool or label hash mismatch")
    for path_str, expected in manifest["source_sha256"].items():
        if sha256_file(path_str) != expected:
            raise ValueError("Frozen code changed: " + Path(path_str).name)
        relative = Path(path_str).relative_to(Path(manifest["project_root"]))
        if sha256_file(Path(frozen_dir) / "source_snapshot" / relative) != expected:
            raise ValueError("Frozen source snapshot changed: " + relative.name)
    if sha256_file(Path(frozen_dir) / "protocol_decisions.md") != \
       manifest["protocol_decisions_sha256"]:
        raise ValueError("Frozen protocol changed")
    return manifest


def controller_for(name, model_name):
    if name == "llm":
        return ToolChoiceLLMController(OfficialGLMDecisionClient(model_name=model_name),
                                       model_name=model_name)
    if name == "fixed":
        return FixedController()
    if name == "random":
        return RandomController()
    raise ValueError("Unknown controller")


def run_one(frozen_dir, *, controller_name, seed, representation):
    manifest = load_frozen_manifest(frozen_dir)
    spec = manifest["campaign_spec"]
    if controller_name not in CONTROLLERS or seed not in spec["seeds"] or \
       representation not in spec["representations"]:
        raise ValueError("Run settings differ from the frozen protocol")
    public = read_jsonl(Path(manifest["public_dir"]) / "candidates.jsonl")
    private_rows = read_jsonl(Path(manifest["private_dir"]) / "oracle_labels.jsonl")
    labels = {row["compound_key"]: row["outcome"] for row in private_rows}
    oracle = BatchOracle(public, labels, seed=seed, total_budget=spec["total_budget"],
                         initialization_queries=spec["initialization_queries"],
                         batch_size=spec["batch_size"])
    run_dir = Path(manifest["run_root"]) / f"{controller_name}_{representation}_seed{seed}"
    run_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(run_dir, 0o700)
    run_path = run_dir / "run.json"
    frozen_manifest_hash = sha256_file(Path(frozen_dir) / "manifest.json")
    expected_name = {"llm": "llm_policy_choice", "fixed": "prescribed_knn_greedy",
                     "random": "uniform_random_reference"}[controller_name]
    identity = {"frozen_manifest_sha256": frozen_manifest_hash,
                "controller_type": controller_name, "controller": expected_name,
                "representation": representation, "seed": seed}
    if run_path.exists():
        saved = read_json(run_path)
        if any(saved.get(key) != value for key, value in identity.items()):
            raise ValueError("Existing run identity differs from frozen settings")
        if saved["status"] == "complete":
            return saved["result"]
        trajectory = saved["trajectory"]
        prior_feature_seconds = saved["feature_build_seconds"]
    else:
        trajectory, prior_feature_seconds = [], 0.0

    controller = controller_for(controller_name, spec["model"])

    def checkpoint(rows, feature_seconds):
        atomic_json(run_path, {**identity, "status": "in_progress",
                               "trajectory": rows, "feature_build_seconds": feature_seconds,
                               "updated_utc": datetime.now(timezone.utc).isoformat()})
        os.chmod(run_path, 0o600)

    try:
        result = run_campaign(public, oracle, controller, seed=seed,
                              representation=representation, existing_trajectory=trajectory,
                              on_checkpoint=checkpoint,
                              prior_feature_seconds=prior_feature_seconds)
    except Exception as exc:
        completed_batches = (len(read_json(run_path)["trajectory"]) if run_path.exists() else 0)
        event = {"at_utc": datetime.now(timezone.utc).isoformat(),
                 "error_type": type(exc).__name__,
                 "public_api_diagnostic": exc.public_diagnostic() if isinstance(exc, GLMAPIError) else None,
                 "decision_seconds": exc.decision_seconds if isinstance(exc, GLMAPIError) else None,
                 "completed_batches": completed_batches}
        atomic_json(run_dir / "last_error.json", event)
        history_path = run_dir / "failure_events.json"
        history = read_json(history_path) if history_path.exists() else []
        history.append(event)
        atomic_json(history_path, history)
        os.chmod(history_path, 0o600)
        raise
    atomic_json(run_path, {**identity, "status": "complete", "result": result,
                           "updated_utc": datetime.now(timezone.utc).isoformat()})
    os.chmod(run_path, 0o600)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frozen-dir", type=Path, required=True)
    parser.add_argument("--controller", choices=CONTROLLERS, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--representation", choices=("bit", "count"), default="bit")
    parser.add_argument("--execute-frozen", action="store_true", required=True,
                        help="Explicitly allow revealing stored outcomes through the oracle")
    args = parser.parse_args()
    result = run_one(args.frozen_dir, controller_name=args.controller,
                     seed=args.seed, representation=args.representation)
    print(json.dumps({"complete": True, "controller": result["controller"],
                      "seed": result["seed"], "representation": result["representation"],
                      "queried_count": result["queried_count"],
                      "hits_at_budget": result["hits_at_budget"]}, indent=2))


if __name__ == "__main__":
    main()
