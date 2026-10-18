# DYRK3 assay edge inspection v0

This is a read-only **curation** follow-up for the completed audit run. It verifies the audit output hashes, shows the source evidence for compounds that are unknown or require review, and lists groups of compounds with identical **2048-bit Morgan fingerprints** under the exact audit settings. Fingerprint equality is a statement about the numerical representation, not proof that two structures are the same molecule. This tool does not change any compound, outcome, threshold, or benchmark version and makes no API/GLM calls.

The result contains provisional outcome labels. Keep it in the curation workspace; do not make it available to a campaign agent.

From Windows PowerShell, copy the script to the Ubuntu project. If the SSH key is elsewhere, adjust only the local key path:

```powershell
scp -i "$env:USERPROFILE\.ssh\id_ed25519_lab" "C:\Users\lixinrong\Documents\Codex\2026-10-09\agentic-ai-for-adaptive-virtual-screening\outputs\assay_edge_inspection_v0\inspect_assay_edges.py" xinrong@100.92.205.88:/driveA/xinrong/agentic-screening/assay_audit_v0/inspect_assay_edges.py
```

Then log in and run:

```bash
cd /driveA/xinrong/agentic-screening
source .venv/bin/activate
python assay_audit_v0/inspect_assay_edges.py \
  --audit-run /driveA/xinrong/agentic-screening/data/curation_review/assay_audit_20261014T140422Z_e4a0108b \
  --output-dir /driveA/xinrong/agentic-screening/data/curation_review
```

The console reports the unknown/review records, how many fingerprint-equal groups exist, how many mix hit/nonhit support, and up to three group examples. The full list is written to a new `edge_inspection_.../edge_inspection.json` directory. Review the source record for the unknown compound; do not assign it an inactive label from absence of a usable measurement. Mixed-label fingerprint groups indicate a limit of using that fingerprint alone to separate compounds, not necessarily bad assay data. The audit remains `review pending` until the evidence and qualification criteria are reviewed.

Local synthetic check of unknown retention and output integrity: `python test_inspect_assay_edges.py` (requires RDKit). The script must still be run on the real remote audit to learn the actual unknown reason and fingerprint groups.
