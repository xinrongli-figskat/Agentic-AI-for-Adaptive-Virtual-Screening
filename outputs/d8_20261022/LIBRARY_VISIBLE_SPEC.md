# D8 library-visible LLM variant

Status: post-exposure design, locked before its synthetic checks and any provider request. This is a controller information-boundary variant, not a new benchmark.

## Information made available

At each decision, the language model receives the complete preset public library: every `compound_key`, its `standardized_smiles`, and the current S_strong predicted probability for that candidate. The score model is refit using only outcomes already revealed for selected compounds. Before two measured classes are available, scores are `null`, matching the existing random cold-start behavior. Already measured active and inactive keys are listed separately. The same five actions and descriptions as the locked C3 five-action menu are used.

## Information withheld

The controller receives no result for an unselected compound, no concentration value, no hidden-label prevalence, no near-threshold count, and no measurement-effort variable. The private label file is not opened by this module. The prediction helper accepts only the public candidate interface and selected/revealed `(compound_key, outcome)` pairs. This is application-level information control; it is not an operating-system sandbox.

## Prompt construction and size

Candidates are serialized in ascending key order to make the prompt reproducible. All candidates are included; there is no silent truncation. Before a provider call, record the UTF-8 byte count and a conservative token estimate of one token per four characters. If the estimate exceeds 80,000 tokens, stop and revise the protocol before calling the model. This preserves the full-library assertion and avoids an undocumented partial library.

The existing D5 strict response schema remains: exactly `policy` and `reason`, with one allowed action and a nonempty reason. The existing D5 API module and controller are not modified.

## Synthetic checks

Before any real call, assert that (1) the candidate key and structure set in the serialized payload equals the entire public library, (2) changing synthetic outcomes for unselected candidates leaves the payload unchanged, and (3) no per-candidate result field is serialized. A synthetic API probe, if performed, must use a synthetic public state and record model, `do_sample=false`, request ID, token usage, prompt size, and status. It does not query the campaign oracle.

## Scope and limits

The optional evaluation is limited to TNAP × S_strong × bit, seeds 0–9, one repeat, four decisions per run. It is a post-exposure checkpoint and cannot replace or be pooled with the completed 20-seed C4 result. Any observed difference is a small exploratory comparison of library visibility under this particular model, proxy, and menu.
