#!/usr/bin/env bash
set -euo pipefail
root=/driveA/xinrong/agentic-screening
source_dir="$root/data/source_dbs/chembl_37"
if [[ -f "$source_dir/batch.pid" ]] && kill -0 "$(cat "$source_dir/batch.pid")" 2>/dev/null; then
  echo 'Batch watcher is already running' >&2
  exit 1
fi
nohup bash "$root/run_chembl37_batch_after_prescreen.sh" > "$source_dir/batch.log" 2>&1 < /dev/null &
printf '%s\n' "$!" > "$source_dir/batch.pid"
printf 'Batch watcher PID %s\n' "$(cat "$source_dir/batch.pid")"
