# D11 run log

- Instruction differences were decomposed and hashed before provider calls; B-class differences existed, so the ablation proceeded.
- D11 protocol and runner were locked before real calls. Synthetic preflight passed with zero GLM calls.
- Seeds 0–9 passed the required checkpoint: 10/10 campaigns, 40/40 valid model decisions, all initializations matched C4 and D9, and all four runtime assertions passed.
- Seeds 10–19 completed; total campaign set is 20/20. One campaign used C4’s automatic zero-hit commitment for its final batch, yielding 79 valid model decisions from 80 nominal feedback points.
- Physical attempts: 82. This includes one DNS/transport failure and two invalid-format responses; each invalid response received one exact-body retry. No fallback policy was used.
- Independent receipt audit reconstructed and verified the exact request payload and all four information-boundary assertions for all 82 physical attempts.
- Returned model usage: 54,755 tokens. Project cumulative physical estimate: 846/1,000 from baseline 764.
- Paired bootstrap: 10,000 resamples, seed 20261018. Model-noise sensitivity uses SD 2.1943108257491692 and the preregistered SE multiplier.
- Final registered interpretation: intermediate. See `D11_ANALYSIS.json` and `D11_DECOMPOSITION.json`.
- No Git operations, no pool freeze, no edits to historical D3–D10 outputs.
- Private prompts, raw responses, HTTP receipts, and trajectories are under ignored `d11_private/`.
