"""Read-only project inventory. No API calls, oracle queries, or file writes."""

import hashlib
import json
import socket
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
EXPECTED_SHA = "3866c7bfc99e92b8e0d6f92b98955d5e68a7ae202f609eac90d0e7a201f98235"
DEFAULT_ROOT = "/driveA/xinrong/agentic-screening"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(root, expected_sha=EXPECTED_SHA):
    root = Path(root).resolve()
    print("HOST:", socket.gethostname())
    print("PROJECT:", root)
    print("PYTHON:", sys.executable)
    print("VENV_ACTIVE:", sys.prefix != sys.base_prefix)

    files = ["inspect_chembl_sample.py",
             "candidate_discovery_v0/discover_chembl_candidates.py",
             "assay_audit_v0/audit_assay.py",
             "assay_audit_v0/inspect_assay_edges.py",
             "oracle_boundary_v0/oracle_boundary.py",
             "campaign_v0/real_campaign.py", "campaign_v0/evaluate_frozen.py",
             "freeze_v1/create_version.py"]
    print("MISSING_EXPECTED_TOOLS:", [p for p in files if not (root / p).is_file()])

    backup = root / "data/curation_private/research_notes_20261015"
    note_dirs = [root / "docs", backup / "docs"]
    stored = {i for i in range(1, 22)
              if any(list(d.glob(f"{i:02d}_*.md")) for d in note_dirs)}
    print("NOTES_FOUND:", len(stored), "/ 21")
    print("NOTES_MISSING_NUMBERS:", [f"{i:02d}" for i in range(1, 22) if i not in stored])
    receipt = backup / "docs/research_notes_sync_manifest_20261015.json"
    if receipt.is_file():
        try:
            bad = [item["path"] for item in read(receipt)["files"]
                   if not (backup / item["path"]).is_file()
                   or sha(backup / item["path"]) != item["sha256"]]
            print("NOTES_BACKUP_HASHES:", "PASS" if not bad else "FAIL", bad)
        except Exception as exc:
            print("NOTES_BACKUP_HASHES: ERROR", type(exc).__name__)
    else:
        print("NOTES_BACKUP_HASHES: NOT_CHECKED_NO_RECEIPT")

    frozen = root / "data/curation_private/frozen_dyrk3_v1"
    manifest_path = frozen / "manifest.json"
    if not manifest_path.is_file():
        print("FROZEN: MISSING")
        return 2
    actual_sha = sha(manifest_path)
    print("MANIFEST_SHA256:", actual_sha)
    if actual_sha != expected_sha:
        print("FROZEN: FAIL_MANIFEST_DIFFERS_FROM_RECORDED_VERSION")
        return 2
    sys.path.insert(0, str(root))
    try:
        from campaign_v0.real_campaign import load_frozen_manifest
        from campaign_v0.evaluation import summarize_run
        from oracle_boundary_v0.oracle_boundary import deterministic_order
        manifest = load_frozen_manifest(frozen)
        public = [json.loads(line) for line in
                  (Path(manifest["public_dir"]) / "candidates.jsonl").read_text(
                      encoding="utf-8").splitlines() if line.strip()]
    except Exception as exc:
        print("FROZEN: FAIL", type(exc).__name__, str(exc))
        return 2
    print("FROZEN: PASS_DATA_CODE_SNAPSHOTS_PROTOCOL")
    print("PUBLIC_CANDIDATES:", len(public))
    print("MODEL:", manifest["campaign_spec"]["model"])
    print("RUN_ROOT:", manifest["run_root"])
    print("controller rep seed status queries H50 API_calls")
    counts, policies = Counter(), Counter()
    prompt_tokens = completion_tokens = failure_events = 0
    pending, invalid = [], []
    names = {"fixed": "prescribed_knn_greedy", "random": "uniform_random_reference",
             "llm": "llm_policy_choice"}
    pool_ids = {row["compound_key"] for row in public}
    for rep in manifest["campaign_spec"]["representations"]:
        for controller, name in names.items():
            for seed in manifest["campaign_spec"]["seeds"]:
                slot = f"{controller}_{rep}_seed{seed}"
                folder = Path(manifest["run_root"]) / slot
                path = folder / "run.json"
                status, queries, hits, calls = "MISSING", "-", "-", "-"
                try:
                    if (folder / "failure_events.json").is_file():
                        failure_events += len(read(folder / "failure_events.json"))
                    if path.is_file():
                        saved = read(path)
                        expected = {"frozen_manifest_sha256": actual_sha,
                                    "controller_type": controller, "controller": name,
                                    "representation": rep, "seed": seed}
                        if any(saved.get(k) != v for k, v in expected.items()):
                            raise ValueError("run identity mismatch")
                        status = saved["status"].upper()
                        if status == "COMPLETE":
                            run = saved["result"]
                            if run["controller"] != name or run["seed"] != seed or run["representation"] != rep:
                                raise ValueError("result identity mismatch")
                            summary = summarize_run(run)
                            initial = deterministic_order(pool_ids, seed, "init")[:10]
                            ids = [key for step in run["trajectory"] for key in step["selection"]]
                            if run["trajectory"][0]["selection"] != initial or not set(ids) <= pool_ids:
                                raise ValueError("initialization or pool mismatch")
                            queries, hits, calls = run["queried_count"], summary["h_at_50"], summary["api_calls_with_usage"]
                            prompt_tokens += summary["prompt_tokens"]
                            completion_tokens += summary["completion_tokens"]
                            if controller == "llm":
                                policies.update(step["decision"]["policy"] for step in run["trajectory"][1:])
                        elif status == "IN_PROGRESS":
                            queries = sum(len(step["selection"]) for step in saved["trajectory"])
                        else:
                            raise ValueError("unknown saved status")
                except Exception as exc:
                    status = "INVALID"
                    invalid.append({"slot": slot, "error_type": type(exc).__name__})
                counts[status] += 1
                if status != "COMPLETE":
                    pending.append(slot)
                print(controller, rep, seed, status, queries, hits, calls)
    print("RUN_COUNTS:", dict(counts))
    print("PENDING_SLOTS:", pending)
    print("INVALID_RUNS:", invalid)
    print("LLM_POLICY_COUNTS_COMPLETED_RUNS:", dict(policies))
    print("RETURNED_TOKENS_COMPLETED_RUNS:", {"prompt": prompt_tokens, "completion": completion_tokens})
    print("SAVED_FAILURE_EVENTS:", failure_events)
    print("NOTE: token totals omit incomplete runs and provider usage not returned after failures.")
    return 1 if invalid else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ROOT))
