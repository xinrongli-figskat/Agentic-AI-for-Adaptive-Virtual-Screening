"""Copy only small report/manifest files from the verified P1/P5 archives."""
from pathlib import Path
import tarfile


BASE = Path(__file__).resolve().parents[1]
ARCHIVES = BASE / ".sync_audit/p1_p5_20261018"
SELECTED = {
    "p1_negcoverage_private_20261018": (
        "MANIFEST.json", "RUN_LOG.md", "STATUS", "p1_input_check.md",
        "p1_input_check.json", "rank_rule_p1.md", "regression_5.json",
        "gate_matrix.csv", "hypothetical_negatives_needed.csv",
        "ranked_distance_to_qualification.csv", "failure_patterns.md",
        "q2_negative_coverage_answer_draft.md", "comparison_with_62_numeric_pass.csv",
        "b1_vs_curated_nonhit_counts.csv", "p1_aggregate_totals.json",
        "DEVIATION_20261018_P1.md"),
    "p5_init_gate_private_20261018": (
        "MANIFEST.json", "RUN_LOG.md", "STATUS", "init_gate_definition.md",
        "init_gate_validation.md", "init_gate_min_hits_table.csv",
        "init_gate_min_hits_table.md", "init_gate_status_all_candidates.csv",
        "init_gate_status_p1_226.csv", "init_gate_sensitivity_descriptive.csv",
        "init_gate_provenance.md", "init_gate_rationale_draft.md",
        "qualification_addendum_init_gate_20261018.md"),
    "p5_standard_table_private_20261018": (
        "MANIFEST.json", "RUN_LOG.md", "STATUS", "BLOCKER.md"),
}


for directory, files in SELECTED.items():
    archive = ARCHIVES / (directory + ".tar.gz")
    target = BASE / "outputs" / directory
    target.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as tar:
        for name in files:
            member = tar.getmember(directory + "/" + name)
            data = tar.extractfile(member).read()
            (target / name).write_bytes(data)
    print(directory, "selected_files", len(files))
