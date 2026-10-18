#!/usr/bin/env bash
set -euo pipefail
root=/driveA/xinrong/agentic-screening
source_dir="$root/data/source_dbs/chembl_37"
for _ in $(seq 1 960); do
  if [[ -f "$source_dir/download_verified.json" ]]; then break; fi
  transfer_pid=$(cat "$source_dir/parallel_download.pid")
  if ! kill -0 "$transfer_pid" 2>/dev/null; then
    echo 'Parallel download exited before verification; inspect parallel_download.log' >&2
    exit 1
  fi
  sleep 30
done
if [[ ! -f "$source_dir/download_verified.json" ]]; then
  echo 'Download did not finish within the 8-hour wait window' >&2
  exit 1
fi
python3 -B "$root/prepare_chembl37_sqlite.py" --source-dir "$source_dir"
python3 -B "$root/enumerate_chembl37_assays.py" \
  --database "$source_dir/extracted/chembl_37.db" \
  --sql "$root/chembl37_assay_prescreen.sql" \
  --verified-download "$source_dir/download_verified.json" \
  --output-root "$root/data/candidate_discovery"
