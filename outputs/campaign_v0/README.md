# Campaign v0: controlled feedback prototype

This package exercises the 10-initialization + four 10-query feedback schedule
with synthetic labels. It includes a random reference, a prescribed kNN-greedy
controller, a deterministic adaptive stub, and a narrow LLM policy-choice
interface. The stub and fake decision client in tests are **not GLM**. No actual
DYRK3 outcome is queried by these programs.

Run from the remote project root after extracting `campaign_v0` beside
`oracle_boundary_v0`:

```bash
source .venv/bin/activate
python -m unittest campaign_v0.test_campaign
python -m campaign_v0.smoke_public \
  --public-dir /driveA/xinrong/agentic-screening/data/campaign_public/prefreeze_20261014T145140Z_6402306a507c6fd5
```

The first command runs synthetic-label checks, including a fake LLM client
that selects different policies across rounds and verifies its input contains
only public feedback. The second reads only the public SMILES to check that
RDKit can make the declared Morgan radius-2, 2048-bit, chirality-aware bit
fingerprints for the actual 231-candidate pool. It does not load labels.
Add `--full-synthetic` to also run complete 50-query fixed-controller dry runs
with both bit and count fingerprints on the 231 public structures. Labels for
that check are generated from compound IDs and have no relationship to real
DYRK3 outcomes.

`ToolChoiceLLMController` accepts a callable receiving a public feedback
summary and returning JSON with exactly `policy` and `reason`. The optional
`OfficialGLMDecisionClient` sends that summary to the official Zhipu chat API,
using `ZAI_API_KEY` from the environment; its offline tests do **not** make an
API call. To test the connection with one synthetic-feedback request only:

```bash
read -rsp 'Zhipu API key: ' ZAI_API_KEY; echo
export ZAI_API_KEY
python -m campaign_v0.probe_glm --model glm-4.7-flash
unset ZAI_API_KEY
```

The key is never printed or written by this package. The GLM adapter offers
no file, shell, retrieval, numerical, or oracle tool to the model. The
numerical selection and label query remain in the controlled Python runner.
The public state is checked for internal consistency before an API call. For
the default `glm-4.7-flash`, the adapter requests JSON output with thinking
disabled and a 256-token output limit; this is a pre-campaign cost and
validity check, not a claim of optimal model settings.
The `glm-5.3-flash` probe uses the model's documented thinking-enabled mode
with `reasoning_effort: low`, a 1024-token output limit, `do_sample: false`,
and a 120-second request timeout. The DYRK3 v1 frozen protocol explicitly
selects this model and request profile; the probe alone never changes a
campaign's model.
If the API rejects a request, the probe prints only the HTTP status, numeric
business error code, an allowlisted category and any numeric Retry-After value.
An HTTP 429 alone does not show whether the cause is a rate limit, quota,
account balance or model access. Do not retry repeatedly without checking
the business code.
For business code `1305` only (provider model overload), the adapter makes at
most three attempts for one decision, waiting 5 and 15 seconds between them.
The probe prints the HTTP attempt history, and real campaigns save both
successful and failed attempts for cost accounting. If all three attempts
fail, wait until the provider recovers; do not repeatedly launch the probe.
A 60-second network read timeout is reported as `request_timeout` and is not
retried automatically. The provider may have processed the timed-out request,
so its token use is unknown without provider-side records. No next oracle batch
is queried when a model decision times out.
The private-side `real_campaign.py` launcher can run only against a verified
`freeze_v1` manifest and requires the explicit `--execute-frozen` flag. It
stores each completed batch in a private checkpoint; on restart it replays
saved batches through the fixed oracle and refuses changed outcomes. On an API
error it saves the completed batch count and stops before the next label query.
The LLM receives all previously revealed outcomes and a compact numerical
summary, never the private source file or hidden labels.

Do **not** launch real-label campaigns from a pre-freeze export. The model,
code and protocol must first be tested and frozen on the remote host. The
private evaluator then checks full 50-query runs and paired comparisons; its
near-threshold result is descriptive re-scoring, not a new campaign.
