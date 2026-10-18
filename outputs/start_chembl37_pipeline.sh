#!/usr/bin/env bash
set -euo pipefail
dir=/driveA/xinrong/agentic-screening/data/source_dbs/chembl_37
if [[ -f "$dir/pipeline.pid" ]] && kill -0 "$(cat "$dir/pipeline.pid")" 2>/dev/null; then
  printf 'Pipeline already running PID %s\n' "$(cat "$dir/pipeline.pid")"
  exit 0
fi
nohup bash /driveA/xinrong/agentic-screening/run_chembl37_prescreen_after_download.sh \
  > "$dir/pipeline.log" 2>&1 < /dev/null &
printf '%s\n' "$!" > "$dir/pipeline.pid"
printf 'Started pipeline PID %s\n' "$(cat "$dir/pipeline.pid")"
