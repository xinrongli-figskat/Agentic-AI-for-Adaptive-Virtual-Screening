# DYRK3 v1 freeze preparation

`create_version.py` verifies the existing public/private pre-freeze export,
checks the declared ChEMBL 37 DYRK3 pool and hashes, archives source snapshots,
and writes a private manifest at
`/driveA/xinrong/agentic-screening/data/curation_private/frozen_dyrk3_v1`.
It fails if that folder already exists and never overwrites a frozen version.
No campaign outcome is revealed by this command.

From the remote project root, **after** the updated offline tests and final
synthetic GLM probe have been reviewed, first run the command below with
`--check-only`. It verifies the receipts, pool, code and protocol and prints
the planned campaign spec without creating a frozen version. Review the
`candidate_count`, model and request settings; then run the same command
without `--check-only` to write the frozen version.

```bash
python -m freeze_v1.create_version \
  --project-root /driveA/xinrong/agentic-screening \
  --public-dir /driveA/xinrong/agentic-screening/data/campaign_public/prefreeze_20261014T145140Z_6402306a507c6fd5 \
  --private-dir /driveA/xinrong/agentic-screening/data/curation_private/prefreeze_20261014T145140Z_6402306a507c6fd5 \
  --check-only
```

The manifest fixes 231 compound identities, the 1000 nM assay threshold,
five seeds, 10+40 query schedule, policy menu, bit/count representations,
GLM-5.3-Flash with thinking enabled, low reasoning effort and sampling disabled,
code hashes, source audit hashes, metrics and
threshold diagnostic. The original data export retains its pre-freeze status;
the separate manifest is the version declaration. Changing any pool member,
label, protocol or source file requires a new version.

`campaign_v0.real_campaign` is the private-side launcher. Do not run it until
the freeze output has been checked. It never passes private paths or unrevealed
outcomes to the LLM client.
