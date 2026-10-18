#!/usr/bin/env bash
set -euo pipefail
dest=/driveA/xinrong/agentic-screening/data/source_dbs/chembl_37
mkdir -p "$dest"
if [[ -f "$dest/download_verified.json" ]]; then
  echo 'Already verified'; exit 0
fi
if [[ -f "$dest/download.pid" ]] && kill -0 "$(cat "$dest/download.pid")" 2>/dev/null; then
  printf 'Already running PID %s\n' "$(cat "$dest/download.pid")"; exit 0
fi
nohup bash /driveA/xinrong/agentic-screening/download_chembl37_sqlite.sh \
  > "$dest/download.log" 2>&1 < /dev/null &
printf '%s\n' "$!" > "$dest/download.pid"
printf 'Started PID %s\n' "$(cat "$dest/download.pid")"
