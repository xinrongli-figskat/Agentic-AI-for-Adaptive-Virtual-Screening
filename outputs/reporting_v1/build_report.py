"""Verify 30 frozen DYRK3 runs and create a private, versioned results report.

No LLM requests or oracle queries. The private evaluator reads source labels
for consistency and the prespecified threshold diagnostic. Frozen files are
never modified. All output is new and remains in the curation workspace.
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
from statistics import mean, stdev
import uuid

from campaign_v0.evaluation import check_run
from campaign_v0.evaluate_frozen import evaluate
from campaign_v0.real_campaign import load_frozen_manifest
from oracle_boundary_v0.oracle_boundary import deterministic_order, read_json, read_jsonl


EXPECTED_MANIFEST_SHA = "3866c7bfc99e92b8e0d6f92b98955d5e68a7ae202f609eac90d0e7a201f98235"
NAMES = {"llm": "llm_policy_choice", "fixed": "prescribed_knn_greedy",
         "random": "uniform_random_reference"}
LABELS = {"llm_policy_choice": "LLM", "prescribed_knn_greedy": "Fixed greedy",
          "uniform_random_reference": "Random"}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def describe(values):
    return {"mean": mean(values), "sample_sd": stdev(values) if len(values) > 1 else None}


def failure_telemetry(events):
    """Missing metadata is unknown, rather than zero cost or zero attempts."""
    attempts = [item for event in events for item in
                ((event.get("public_api_diagnostic") or {}).get("attempt_log") or [])]
    missing_attempts = sum(not ((event.get("public_api_diagnostic") or {}).get("attempt_log"))
                           for event in events)
    missing_seconds = sum(event.get("decision_seconds") is None for event in events)
    known_seconds = sum(event["decision_seconds"] for event in events
                        if event.get("decision_seconds") is not None)
    return {"saved_failure_events": len(events), "recorded_failed_http_attempts": len(attempts),
            "events_without_attempt_metadata": missing_attempts,
            "events_without_elapsed_time": missing_seconds,
            "known_failed_decision_seconds": known_seconds,
            "total_failed_decision_seconds": None if missing_seconds else known_seconds,
            "failed_request_tokens": None if events else 0,
            "cost_complete": not events,
            "note": "Failure-event files do not preserve token usage; missing values are unknown. "
                    "A generic ValueError alone does not identify its exact cause or response content."}


def collect(frozen_dir):
    frozen_dir = Path(frozen_dir).resolve()
    manifest_path = frozen_dir / "manifest.json"
    manifest_sha = digest(manifest_path)
    if manifest_sha != EXPECTED_MANIFEST_SHA:
        raise ValueError("Manifest differs from the recorded frozen v1 version")
    manifest = load_frozen_manifest(frozen_dir)
    spec = manifest["campaign_spec"]
    public = read_jsonl(Path(manifest["public_dir"]) / "candidates.jsonl")
    pool = {row["compound_key"] for row in public}
    private = {row["compound_key"]: row["outcome"] for row in
               read_jsonl(Path(manifest["private_dir"]) / "oracle_labels.jsonl")}
    snapshots, traces, failures = {}, [], []
    policy_counts = {rep: Counter() for rep in spec["representations"]}
    slots = 0
    for rep in spec["representations"]:
        for seed in spec["seeds"]:
            initial = deterministic_order(pool, seed, "init")[:spec["initialization_queries"]]
            for controller, expected_name in NAMES.items():
                slot = f"{controller}_{rep}_seed{seed}"
                folder = Path(manifest["run_root"]) / slot
                path = folder / "run.json"
                if not path.is_file():
                    raise ValueError("Missing run: " + slot)
                saved = read_json(path)
                expected = {"status": "complete", "frozen_manifest_sha256": manifest_sha,
                            "controller_type": controller, "controller": expected_name,
                            "seed": seed, "representation": rep}
                if any(saved.get(k) != v for k, v in expected.items()):
                    raise ValueError("Run identity/status mismatch: " + slot)
                run = saved["result"]
                if any(run.get(k) != expected[k] for k in ("controller", "seed", "representation")):
                    raise ValueError("Result identity mismatch: " + slot)
                queried = check_run(run)
                if not set(queried) <= pool or run["trajectory"][0]["selection"] != initial:
                    raise ValueError("Pool/initialization mismatch: " + slot)
                observed = []
                for step in run["trajectory"]:
                    if controller == "llm" and observed:
                        call = step.get("llm_call") or {}
                        summary = call.get("public_summary") or {}
                        decision = step.get("decision") or {}
                        if call.get("model") != spec["model"] or call.get("decision") != decision or \
                           summary.get("revealed_observations") != observed or \
                           summary.get("queried_count") != len(observed) or \
                           decision.get("policy") not in spec["policies"]:
                            raise ValueError("LLM feedback/decision log mismatch: " + slot)
                        policy_counts[rep][decision["policy"]] += 1
                        traces.append({"slot": slot, "stage": step["stage"],
                                       "queries_before_decision": len(observed),
                                       "decision": decision, "api_request_id": call.get("api_request_id"),
                                       "api_usage": call.get("api_usage"),
                                       "api_attempt_log": call.get("api_attempt_log"),
                                       "decision_seconds": call.get("decision_seconds")})
                    for row in step["observations"]:
                        if row["outcome"] != private[row["compound_key"]]:
                            raise ValueError("Observed outcome differs from fixed source: " + slot)
                    observed.extend(step["observations"])
                snapshots[str(path)] = digest(path)
                failure_path = folder / "failure_events.json"
                if failure_path.is_file():
                    failures.extend({**event, "slot": slot} for event in read_json(failure_path))
                    snapshots[str(failure_path)] = digest(failure_path)
                slots += 1
    evaluation = evaluate(frozen_dir)
    if evaluation["status"] != "complete" or len(evaluation["run_summaries"]) != slots:
        raise ValueError("Evaluation is incomplete")
    # Detect a source log changing while the report is collected.
    if any(digest(path) != expected for path, expected in snapshots.items()):
        raise ValueError("A campaign log changed during report collection")
    groups = {}
    for rep in spec["representations"]:
        groups[rep] = {name: describe([row["h_at_50"] for row in evaluation["run_summaries"]
                                      if row["representation"] == rep and row["controller"] == name])
                       for name in NAMES.values()}
    return {"status": "complete", "generated_utc": datetime.now(timezone.utc).isoformat(),
            "frozen_manifest_sha256": manifest_sha, "verified_runs": slots,
            "candidate_count": len(pool), "campaign_spec": spec,
            "group_h_at_50": groups, "evaluation": evaluation,
            "llm_policy_counts": {k: dict(v) for k, v in policy_counts.items()},
            "llm_decision_trace": traces, "failure_events": failures,
            "failure_telemetry": failure_telemetry(failures),
            "known_successful_call_costs": {
                "validated_decision_records": len(traces),
                "decisions_without_usage": sum(not isinstance(row["api_usage"], dict) for row in traces),
                "prompt_tokens": sum(row["prompt_tokens"] for row in evaluation["run_summaries"]),
                "completion_tokens": sum(row["completion_tokens"] for row in evaluation["run_summaries"]),
                "api_calls_with_usage": sum(row["api_calls_with_usage"] for row in evaluation["run_summaries"]),
                "http_attempts_logged_for_successful_decisions": sum(row["api_attempts_total"] for row in evaluation["run_summaries"]),
                "decision_seconds": sum(row["decision_seconds_total"] for row in evaluation["run_summaries"])},
            "source_log_sha256": snapshots,
            "cost_limitations": ["Failed format-validation replies were not saved by the frozen client.",
                                 "Failure token usage and missing durations must not be counted as zero.",
                                 "Analysis time from aborted decisions is not completely preserved.",
                                 "Probe calls and monetary billing are not included; verify billing separately."],
            "software_versions": {"python": platform.python_version(), **{
                name: importlib.metadata.version(name) for name in ("numpy", "rdkit", "matplotlib")}},
            "private_report_parent": str(Path(manifest["private_dir"]).parent / "reports_dyrk3_v1"),
            "project_root": manifest["project_root"]}


def make_figures(report, output):
    os.environ.setdefault("MPLCONFIGDIR", str(Path(report["project_root"]) / ".cache/matplotlib"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    colors = {"llm_policy_choice": "#b35a00", "prescribed_knn_greedy": "#126c9b",
              "uniform_random_reference": "#69747b"}
    rows = report["evaluation"]["run_summaries"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
    for ax, rep in zip(axes, ("bit", "count")):
        for name in NAMES.values():
            curves = [row["h_checkpoints"] for row in rows
                      if row["representation"] == rep and row["controller"] == name]
            means = [mean(col) for col in zip(*curves)]
            deviations = [stdev(col) for col in zip(*curves)]
            ax.plot((10, 20, 30, 40, 50), means, marker="o", color=colors[name], label=LABELS[name])
            ax.fill_between((10, 20, 30, 40, 50), [m-s for m, s in zip(means, deviations)],
                            [m+s for m, s in zip(means, deviations)], color=colors[name], alpha=.12)
        ax.set(title=f"{rep}: {'primary' if rep == 'bit' else 'sensitivity'}", xlabel="Distinct compounds queried",
               xticks=(10, 20, 30, 40, 50), xlim=(10, 50), ylim=(0, 50))
        ax.grid(alpha=.2)
    axes[0].set_ylabel("Cumulative assay-defined hits")
    axes[1].legend(fontsize=9)
    fig.suptitle("DYRK3 v1 | Five seeds; shading = sample SD")
    fig.tight_layout()
    for extension in ("png", "pdf"):
        fig.savefig(output / f"hit_recovery.{extension}", dpi=180, bbox_inches="tight")
    plt.close(fig)

    pairs = report["evaluation"]["paired_comparison"]["paired_runs"]
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.7), sharey=True)
    for ax, rep in zip(axes, ("bit", "count")):
        selected = [row for row in pairs if row["representation"] == rep]
        differences = [row["llm_minus_fixed"] for row in selected]
        ax.axhline(0, color="#69747b", linewidth=1)
        ax.plot([row["seed"] for row in selected], differences, "o", color="#b35a00")
        ax.axhline(mean(differences), color="#b35a00", linestyle="--",
                   label=f"Mean: {mean(differences):+.1f}")
        ax.set(title=f"{rep}: {'primary' if rep == 'bit' else 'sensitivity'}", xlabel="Prespecified seed", xticks=(0, 1, 2, 3, 4))
        ax.legend()
        ax.grid(alpha=.2)
    axes[0].set_ylabel("H@50 difference: LLM minus fixed")
    fig.tight_layout()
    for extension in ("png", "pdf"):
        fig.savefig(output / f"paired_difference.{extension}", dpi=180, bbox_inches="tight")
    plt.close(fig)


def write_report(report):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = Path(report["private_report_parent"]) / f"report_{stamp}_{uuid.uuid4().hex[:8]}"
    output.mkdir(parents=True, mode=0o700)
    os.chmod(output, 0o700)
    (output / "evaluation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# DYRK3 v1 feasibility results", "", "Single-assay, same-series retrospective prototype.",
             "", f"Verified runs: {report['verified_runs']}; manifest SHA256: {report['frozen_manifest_sha256']}",
             "", "## H@50", "", "Mean ± sample SD across five seeds. Bit is the primary analysis; count is separate sensitivity.",
             "", "| Representation | LLM | Fixed greedy | Random | Paired LLM−fixed mean ± SD | Paired LLM−random mean ± SD |", "|---|---:|---:|---:|---:|---:|"]
    for rep in ("bit", "count"):
        values = report["group_h_at_50"][rep]
        cells = [f"{values[name]['mean']:.1f} ± {values[name]['sample_sd']:.2f}" for name in NAMES.values()]
        paired = report["evaluation"]["paired_comparison"]["by_representation"][rep]
        random_delta = describe([row["llm_minus_random"] for row in
                                 report["evaluation"]["paired_comparison"]["paired_runs"] if row["representation"] == rep])
        lines.append(f"| {rep} | " + " | ".join(cells) + f" | {paired['mean_llm_minus_fixed']:+.1f} ± {paired['sample_sd_llm_minus_fixed']:.2f} | {random_delta['mean']:+.1f} ± {random_delta['sample_sd']:.2f} |")
    lines.extend(["", "![Hit recovery](hit_recovery.png)", "", "![Paired differences](paired_difference.png)",
                  "", "## Decisions and failures", "", "Policy counts: " + json.dumps(report["llm_policy_counts"], ensure_ascii=False),
                  "", "Failure accounting: " + json.dumps(report["failure_telemetry"], ensure_ascii=False),
                  "", "Returned usage from completed decision logs: " + json.dumps(report["known_successful_call_costs"]),
                  "", *["- " + item for item in report["cost_limitations"]],
                  "", "## Interpretation", "", "Report paired differences within this pool, rather than treating raw hit counts as evidence of broad superiority. "
                  "Five fixed seeds, a high-hit-rate pool and concentrated analogues limit inference. "
                  "Curation involved prior access to labels; this is not blind external validation. "
                  "Assay-defined inhibition does not establish direct binding. Count results must not replace the prespecified bit primary result. "
                  "The [800,1250] nM threshold diagnostic in evaluation.json re-scores existing queries only.",
                  "", "## Remaining scope", "", "These results evaluate one feasibility prototype. "
                  "They do not complete the evidence-driven LLM curation workflow or a reviewed, qualifying target shortlist."])
    (output / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (output / "report_generator_source.py").write_bytes(Path(__file__).read_bytes())
    make_figures(report, output)
    checksums = {path.name: digest(path) for path in output.iterdir() if path.is_file()}
    (output / "REPORT_SHA256.json").write_text(json.dumps(checksums, indent=2) + "\n", encoding="utf-8")
    for path in output.iterdir():
        if path.is_file():
            os.chmod(path, 0o600)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frozen-dir", type=Path, required=True)
    args = parser.parse_args()
    report = collect(args.frozen_dir)
    output = write_report(report)
    print(json.dumps({"status": "report_created", "verified_runs": report["verified_runs"],
                      "report_dir": str(output), "group_h_at_50": report["group_h_at_50"],
                      "paired_comparison": report["evaluation"]["paired_comparison"],
                      "llm_policy_counts": report["llm_policy_counts"],
                      "failure_telemetry": report["failure_telemetry"],
                      "known_successful_call_costs": report["known_successful_call_costs"]}, indent=2))


if __name__ == "__main__":
    main()
