# Checklist to run before changing this repository's visibility

**Changing this repository from private to public exposes the entire commit history at once.
Passing a push check is not the same as passing this checklist. Re-run every item below and
pass it before any visibility change.**

## 1. History scan

```
git log --all --name-only --pretty=format: | sort -u > /tmp/ever_tracked.txt
grep -niE 'private|curation_private|sync_audit|oracle_label|frozen_dyrk3|d5_backups|\.env|ssh_config|\.sqlite|\.db$|api_key|secret|token' /tmp/ever_tracked.txt
```

Path matches are not by themselves disclosures: tooling that *manages* privacy has such names.
Adjudicate each match on content against the scope rule in section 5, and record the verdict.
A match whose content pairs an evaluation-set member's identity with a result, or which carries
a credential value, blocks the change.

## 2. Index scan

```
git ls-files > /tmp/tracked_now.txt
```
Apply the same regex and the same adjudication.

## 3. Ignore-rule verification

Every path below must return a matching rule from `git check-ignore -v`. Any `NOT IGNORED`
blocks the change.

```
data/curation_private/
.sync_audit/
outputs/**/*private*/
**/*_private/
**/oracle_labels*
**/llm_receipts/
```

## 4. Content scans over tracked files

- **Results:** no artifact pairs an evaluation-set member's identity with a result or activity
  value. Assert field-by-field on every published pool or manifest file: the candidate
  interface is exactly `compound_key` and `standardized_smiles` plus metadata.
- **Credentials:** `api_key`, `API_KEY`, `Authorization`, `Bearer `, `sk-`, `ZHIPU`, `GLM_`,
  and any hexadecimal or base64 run of 32 characters or more. A scan reported as complete in an
  earlier round must be re-run, not inherited.
- **Size:** anything above 5 MB justified in writing; anything above 50 MB blocks the change.

## 5. Scope rule for adjudicating a match

**Prohibited:** per-compound results or activity values belonging to an evaluation set, and any
artifact from which those could be reconstructed — that is, anything pairing an evaluation-set
member's identity with a result.

**Permitted:** source-review evidence for candidates that were never admitted, where the values
are already public at their source and the artifact carries no molecular identity that resolves
to an evaluation-set member. See `PATENT_EXCERPTS_PROVENANCE.md`.

## 6. Licence

A public repository with no `LICENSE` file grants no reuse permission. Decide the licence,
reconciling ChEMBL's share-alike terms with the code licence, before the change.

## 7. Record

Write the result of every item above, with the commands run and their output, to a dated
receipt committed alongside this file.
