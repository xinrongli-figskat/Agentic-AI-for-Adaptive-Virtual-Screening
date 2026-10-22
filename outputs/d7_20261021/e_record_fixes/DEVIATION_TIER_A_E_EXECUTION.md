# D7-E execution-only repairs

Recorded UTC: 2026-10-21T09:54:05.647038+00:00. This is the write time of this record; exact event
timestamps for the earlier failed inspection commands were not recorded.

During read-only schema discovery, a remote inline Python command failed
because Windows/SSH quoting changed escaped quote characters. Replaced the
inline invocation with a transferred Python file. The first transfer failed
because the assigned remote E directory did not yet exist; created that
directory and repeated the transfer. A schema-inspection script then found
that the D6-A manifest was present locally but absent at the assumed remote
path; the historical public-manifest check was run against the preserved
local artifacts, while private archive/replay checks ran on the workstation.

Invocation/path deltas only:
1. `ssh ... python -c <quoted code>` -> `scp inspect_schema.py; ssh ... python inspect_schema.py`.
2. Missing remote E destination -> create that same assigned destination,
   then repeat the same transfer.
3. Historical manifests assumed remote -> local preserved public artifacts;
   authoritative private D5/D6 run paths remain remote.

No experiment specification, frozen input, selection rule or threshold was
changed. No campaign or API call occurred. The final verifier passed all
seven known-good fixed-arm means and the exact 20-seed GLM H@50 regression,
and independently matched all 17 historical manifest members.
