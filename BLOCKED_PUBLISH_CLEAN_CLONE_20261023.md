# Publication hard stop: clean-clone byte-hash check

Recorded: 2026-10-22 16:27 UTC (2026-10-23 Asia/Shanghai).

The private GitHub repository was confirmed at the exact canonical URL
`https://github.com/xinrongli-figskat/Agentic-AI-for-Adaptive-Virtual-Screening.git`.
The branch `codex/publish-20261022` was pushed without force at commit
`04345f5f0a20995cc098414b8ff1182b5a22d183`. All commits in the range
from `origin/restructure-20261018` to that commit have author and committer
`Xinrong Li <amyxinrong@gmail.com>`; no Codex co-author trailer was present.

A fresh clone was made at
`C:\Users\lixinrong\Documents\Codex\publish_clean_clone_20261023`.
Running the committed `outputs/publish_20261022/scan_publish.py` stopped at
the TNAP pool-card SHA-256 assertion, before the four-scan clean-clone report
could be produced. The bytes explain the discrepancy:

- Frozen manifest expected and Git committed blob: `7c12b7c2bec048b1fd88c67549c55855e04f5a7b555d391f60c52a9fa1a59984`.
- Fresh Windows worktree bytes: `8cd483daf090f18fe18c90ba12b4b874aa6e33f9708534bbf2a72146cc9a3398`.
- The worktree has 15 CRLF line endings. Replacing CRLF with LF in memory
  reproduces the frozen SHA-256 exactly.

This identifies a Git checkout newline conversion, not a change to the
committed TNAP pool card. Nevertheless, the required clean-clone verification
**did not pass**. The publication task card requires a hard stop in this case.
Read-only comparison also found the same CRLF-only difference in the two
controller source files, TNAP freeze receipt, TNAP pool manifest, and public
candidate list. The clean clone has `core.autocrlf=true`; each of these files
matches its committed blob after CRLF-to-LF normalization in memory.
No further push, history rewrite, force push, LFS operation, or change to a
frozen pool, label, threshold, or locked protocol has been made. The pushed
branch is retained as evidence; it has not been merged or made public.

A prospective repair is to add a narrowly scoped `.gitattributes` rule that
checks out hash-locked artifacts with LF bytes on Windows, then create a new
ordinary commit and repeat the entire clean-clone verification. The task card
requires user authorization before that repair and any additional push.

The user subsequently authorized that repair. The selected rule covers 25
exact public paths whose recorded SHA-256 matches the LF Git blob but differed
in the default Windows clone. Public files whose recorded hashes were made
from CRLF bytes were deliberately left out. The repair does not alter any
existing blob or rewrite history; the next clean clone must still pass before
publication can be marked complete.
