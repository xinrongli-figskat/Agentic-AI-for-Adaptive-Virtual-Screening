#!/usr/bin/env bash
set -euo pipefail

root=/driveA/xinrong/agentic-screening
source_dir="$root/data/source_dbs/chembl_37"
candidate_dir="$root/data/candidate_discovery"
private_dir="$root/data/curation_private/chembl37_batch_curations"
mkdir -p "$private_dir" "$source_dir/scratch"
export TMPDIR="$source_dir/scratch"
export SQLITE_TMPDIR="$source_dir/scratch"

for _ in $(seq 1 1440); do
  mapfile -t results < <(find "$candidate_dir" -maxdepth 2 -type f -name result.json \
    -path '*/chembl37_assay_prescreen_*/result.json' -print)
  if (( ${#results[@]} == 1 )); then
    prescreen_dir=$(dirname "${results[0]}")
    if [[ -f "$prescreen_dir/manifest.json" ]]; then break; fi
  elif (( ${#results[@]} > 1 )); then
    echo 'Multiple prescreen outputs; refusing ambiguous batch curation' >&2
    exit 1
  fi
  pipeline_pid=$(cat "$source_dir/pipeline.pid")
  if ! kill -0 "$pipeline_pid" 2>/dev/null; then
    echo 'Prescreen pipeline exited before a complete result; inspect pipeline.log' >&2
    exit 1
  fi
  sleep 30
done
if [[ ! -f "${prescreen_dir:-}/manifest.json" ]]; then
  echo 'No prescreen result within the 12-hour wait window' >&2
  exit 1
fi

"$root/.venv/bin/python" -B "$root/curate_chembl37_batch.py" \
  --database "$source_dir/extracted/chembl_37.db" \
  --prescreen "$prescreen_dir" \
  --output-root "$private_dir" \
  --per-tier 3 \
  --max-pairwise 1500
