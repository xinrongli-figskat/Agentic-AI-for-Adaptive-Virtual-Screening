# Task 1 next-stage delivery

This directory contains a reproducible offline queue builder and the reviewed prospective search plan. It does not call ChEMBL or GLM and does not change any historical run.

The prebuilt queue is included for remote use. `实施说明.md` explains the qualification rules and maps this stage to the original brief. The remote v4 installation instructions are in `curation_agent_v4/README.md`.

## Build the queue from the verified local v3 archive

From the project root in PowerShell:

```powershell
& .\.venv-curation-check\Scripts\python.exe -B outputs\task1_v4_delivery\build_candidate_queue.py
```

Outputs go to `outputs/task1_v4_delivery/queue/`: `target_queue.csv`, `assay_preview_queue.csv`, and a JSON receipt with source hashes and limitations.

## Remote execution boundary

The queue is a preparation artifact. Do not copy private evidence into a campaign workspace. For online source review, use a new curation run directory on the remote desktop, keep the current ChEMBL release fixed, and use a newly declared budget. The program presents four unprofiled data-rich target choices and eight existing assay previews. GLM chooses one target or assay action at a time; new profile results update the next decision. Full assay retrieval and curation are allowed only after the LLM has inspected the exact assay metadata and source meaning.

Do not resume the exhausted v3 run or alter its stored status. Do not expose any curation label file to Task 2. If a new dataset passes review, create a new benchmark version and freeze its public pool and private labels before any campaign.
