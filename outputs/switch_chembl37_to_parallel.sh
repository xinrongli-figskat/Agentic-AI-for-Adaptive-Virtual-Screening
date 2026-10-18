#!/usr/bin/env bash
set -euo pipefail
dest=/driveA/xinrong/agentic-screening/data/source_dbs/chembl_37
old_pid=$(cat "$dest/download.pid")
old_cmd=$(ps -p "$old_pid" -o args= || true)
if [[ "$old_cmd" != *download_chembl37_sqlite.sh* ]]; then
  echo "Unexpected prior downloader PID $old_pid: $old_cmd" >&2
  exit 1
fi
children=$(pgrep -P "$old_pid" || true)
for child in $children; do kill -TERM "$child"; done
kill -TERM "$old_pid" 2>/dev/null || true
sleep 2
if kill -0 "$old_pid" 2>/dev/null || pgrep -P "$old_pid" >/dev/null; then
  echo 'Prior downloader still active; parallel switch aborted' >&2
  exit 1
fi
nohup python3 -B /driveA/xinrong/agentic-screening/download_chembl37_parallel.py \
  --directory "$dest" --workers 8 > "$dest/parallel_download.log" 2>&1 < /dev/null &
printf '%s\n' "$!" > "$dest/parallel_download.pid"
printf 'Parallel downloader PID %s\n' "$(cat "$dest/parallel_download.pid")"
