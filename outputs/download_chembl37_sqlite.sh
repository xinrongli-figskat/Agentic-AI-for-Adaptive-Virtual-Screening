#!/usr/bin/env bash
set -euo pipefail

dest=/driveA/xinrong/agentic-screening/data/source_dbs/chembl_37
base=https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/releases/chembl_37
mkdir -p "$dest"
cd "$dest"

curl --fail --location --retry 4 --retry-delay 5 --output checksums.txt "$base/checksums.txt"
curl --fail --location --retry 4 --retry-delay 5 --continue-at - \
  --output chembl_37_sqlite.tar.gz "$base/chembl_37_sqlite.tar.gz"

expected=$(awk '$2 == "chembl_37_sqlite.tar.gz" {print $1}' checksums.txt)
if [[ "$expected" != 33c203740555f96067710cdfc1c3c55d890660e5908ec5cbf5817492c290d281 ]]; then
  echo 'Unexpected ChEMBL 37 release checksum; stopping' >&2
  exit 1
fi
printf '%s  %s\n' "$expected" chembl_37_sqlite.tar.gz | sha256sum --check --status
printf '{"status":"verified","archive_sha256":"%s","archive_bytes":%s}\n' \
  "$expected" "$(stat -c %s chembl_37_sqlite.tar.gz)" > download_verified.json
cat download_verified.json
