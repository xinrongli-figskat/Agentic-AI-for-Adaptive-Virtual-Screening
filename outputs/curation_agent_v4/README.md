# Task 1 v4: data-first, stage-aware search

This is an independent continuation package. It reuses the reviewed v3 ChEMBL curation tools and numerical gates, adds a ranked context for already-counted but unprofiled targets and source-ID assay previews, and gives GLM a concise stage-specific prompt. Historical data and failed actions are inherited as seen evidence; nothing is rewritten. The model remains responsible for selecting the next target/assay/tool and for scientific interpretation.

No network or GLM call is made by `prepare`. Each new run declares exactly 12 additional GLM attempts and 100 additional ChEMBL HTTP requests. It preserves prior usage and uses ChEMBL release checks before online calls. The old v3 run must remain closed and unchanged.

## Install on remote Ubuntu

Upload both `task1_curation_agent_v4_transfer.zip` and `install_task1_v4.py` to `/driveA/xinrong/agentic-screening`. Verify the archive SHA256 provided with the package, then use the installer. It checks the archive manifest and every member hash before writing and refuses to replace existing package directories:

```bash
cd /driveA/xinrong/agentic-screening
sha256sum task1_curation_agent_v4_transfer.zip
python3 -B install_task1_v4.py --archive task1_curation_agent_v4_transfer.zip --root .
source .venv/bin/activate
python3 -B -m curation_agent_v4.run --help
```

The existing `curation_agent_v3` package must already be installed. The installer adds `curation_agent_v4/` and `task1_v4_delivery/` and does not replace v1/v2/v2.1/v3.

## Prepare a separate run

Use the closed v3 revision directory as the parent. Preparation validates its source snapshot and evidence, copies it to a separate directory, hashes the parent inventory, records inherited attempts/tokens, and writes no new ChEMBL or GLM receipts.

```bash
python -B -m curation_agent_v4.run prepare \
  --parent-run /driveA/xinrong/agentic-screening/data/curation_private/task1_agent_v3/revision_v3_d91bb3b1f7c5535c \
  --output-root /driveA/xinrong/agentic-screening/data/curation_private/task1_agent_v4 \
  --additional-llm-budget 12 \
  --additional-http-budget 100 \
  --check-only
```

Review `ready_to_prepare_no_files_written`, the inherited totals and the proposed new directory. If they match the closed v3 run, repeat without `--check-only`:

```bash
python -B -m curation_agent_v4.run prepare \
  --parent-run /driveA/xinrong/agentic-screening/data/curation_private/task1_agent_v3/revision_v3_d91bb3b1f7c5535c \
  --output-root /driveA/xinrong/agentic-screening/data/curation_private/task1_agent_v4 \
  --additional-llm-budget 12 \
  --additional-http-budget 100
```

Record the printed run directory in `TASK1_V4_RUN`. Check it with `status`; it should show the old 60 GLM attempts and 113 HTTP requests as inherited, with zero new calls. The new ceilings are 72 GLM attempts and 213 HTTP requests.

## Run the first decision batch

```bash
export ZAI_API_KEY="$(cat /driveA/xinrong/.config/agentic-screening/zhipu_api_key)"
python -B -m curation_agent_v4.run execute --run-dir "$TASK1_V4_RUN" --steps 8
unset ZAI_API_KEY
python -B -m curation_agent_v4.run status --run-dir "$TASK1_V4_RUN"
```

The context will rank unprofiled targets by existing IC50/type-B activity record counts and assay previews by the smaller class-support count. GLM can select one target to profile, inspect/list/count an assay, read its description, assess source meaning, or finish. A target count is not a compound count; assay previews are lower-bound molecule-ID signals before standardization. Full acquisition remains an LLM-selected action after evidence review.

Stop at the declared caps. Review the report and exact tool evidence before a full assay retrieval. A review shortlist is not a campaign benchmark. A passing candidate still needs primary sample/source review, a final protocol review, a new frozen pool/labels, and a controlled oracle before Task 2.
