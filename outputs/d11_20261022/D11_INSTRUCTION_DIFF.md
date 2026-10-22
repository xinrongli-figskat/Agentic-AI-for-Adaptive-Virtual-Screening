# D11 system-instruction comparison

Date: 2026-10-22. Read-only source comparison, completed before any D11 provider call. The C4 instruction is the exact `SYSTEM_PROMPT` constant imported by `outputs/d7_20261021/c4_five/run_c4.py` from `outputs/campaign_v0/glm_api.py`. The D9 instruction is the exact `SYSTEM_PROMPT` constant in `outputs/d8_20261022/library_visible_api.py`, imported by `outputs/d9_20261022/run_library_visible.py`.

## C4 system instruction (verbatim)

> You control one batch of a retrospective compound-search prototype. The user message contains only public candidate counts and already revealed binary outcomes. Choose exactly one of the allowed numerical selection policies for the next batch. Reason only from the supplied feedback. Do not claim to know candidate scores, unknown labels, or chemical details; numerical tools will choose actual compounds. State the observed hit counts relevant to your choice in one short sentence. Return only JSON: {"policy":"allowed_policy_name","reason":"brief evidence-based reason"}.

## D9 system instruction (verbatim)

> You choose one allowed policy for a retrospective active-search run. The complete preset candidate library, public molecular structures, and current model scores are visible. Results are available only for the listed already measured active and inactive compounds. Do not infer or claim the result of any unselected compound. Select exactly one allowed policy and explain briefly using the supplied information. Return only JSON with exactly these keys: {"policy":"...","reason":"..."}.

## Paragraph-level comparison and classification

| Difference | C4 text | D9 text | Class | Reason |
|---|---|---|---|---|
| Task framing | “control one batch” of a prototype | “choose one allowed policy” for an active-search run | B | Both describe the same policy-selection role; neither phrase depends on visible structures or scores. D11 uses the D9 role framing. |
| Information availability | User message has public counts and revealed binary outcomes | Complete candidate library, structures and current scores are visible | A | D9 explicitly refers to fields absent from C4. This sentence is excluded from the D11 instruction. |
| Which results are available | Already revealed binary outcomes | Results only for listed measured active/inactive compounds | A | The D9 formulation refers to identity lists in its payload; C4 exposes aggregate counts, not those lists. Excluded from D11. |
| Unselected-result restraint | Do not claim unknown labels | Do not infer or claim any unselected compound’s result | B | Both apply with either information surface. The D9 wording can be used without implying access to compound identities. Included in D11. |
| Explanation | Reason only from supplied feedback | Explain briefly using supplied information | B | This is general reasoning guidance. D11 retains C4’s feedback-only restriction and the D9 brevity/evidence wording. |
| Relevant hit counts | State relevant observed hit counts in one short sentence | No corresponding sentence | B | Hit counts exist in both information surfaces. D11 retains the C4 instruction. |
| Candidate scores and chemical details | Do not claim to know candidate scores, unknown labels, or chemical details; numerical tools select actual compounds | Candidate scores and chemical details are expressly made visible | A for the score/structure clause; B for the division-of-labour clause | The prohibition on discussing scores and structures cannot be copied into an arm where those fields are visible, so the D9 score/structure disclosure is excluded. “Numerical tools choose actual compounds” is a framework statement, but is already implicit in the fixed policy-choice task; D11 retains the C4 wording that is compatible with its information surface. |
| Output format | Return only JSON with policy/reason placeholders and a brief evidence-based reason | Return only JSON with exactly the two keys policy/reason | B | Exact key enforcement is independent of information surface. D11 uses the stricter D9 wording and the C4 brief-reason requirement. |

## B-class differences

1. D9 frames the instruction around choosing a policy, rather than controlling a batch.
2. D9 explicitly says not to infer or claim an unselected result; this is compatible with C4’s aggregate-only input and clarifies the same unknown-label boundary.
3. D9 asks for a brief explanation grounded in supplied information. C4 separately requires reasoning only from feedback and one short sentence about relevant observed hit counts; D11 keeps both compatible requirements.
4. D9 makes the exact `{policy, reason}` key set explicit. D11 combines that strict schema with C4’s brief evidence-based reason requirement.
5. D9 omits C4’s instruction to state relevant observed hit counts in one short sentence. Since counts remain present in C4’s summary, D11 keeps the C4 requirement; the omission itself is recorded as a B-class difference.

## D11 instruction composition

D11 keeps the C4 information-surface description and its limits on claims about scores, unknown labels and chemical details. It adopts the D9 policy-choice framing, explicit unselected-result restraint, concise evidence-based explanation, and exact two-key JSON schema. It preserves the C4 short hit-count sentence. It does **not** include either A-class statement about a full library, structures, individual current scores, or named measured compounds. This is the instruction text locked for the D11 arm:

> You choose one allowed policy for one batch in a retrospective compound-search prototype. The user message contains only public candidate counts and already revealed binary outcomes. Choose exactly one of the allowed numerical selection policies for the next batch. Reason only from the supplied feedback. Do not claim to know candidate scores, unknown labels, or chemical details; numerical tools will choose actual compounds. Do not infer or claim the result of any unselected compound. State the observed hit counts relevant to your choice in one short sentence. Explain briefly using the supplied information. Return only JSON with exactly these keys: {"policy":"allowed_policy_name","reason":"brief evidence-based reason"}.

Classification is based on text meaning and the stored prompts, not on observed model responses. There are B-class differences, so D11 is separable under the task card's criterion and proceeds to the locked ablation.
