# GLM-5.3-Flash parameter check before campaign freeze

A synthetic-only call using `glm-5.3-flash` returned HTTP 400 with business
code `1210` (invalid request parameters). It did not use DYRK3 labels. The
client had reused `thinking: {type: disabled}` from `glm-4.7-flash`. Zhipu's
GLM-5.3-Flash model page explicitly says its `thinking.type` supports only
`enabled`, and its Chat Completion documentation lists `low`, `high`, and
`max` as supported reasoning-effort values. The latter also recommends at
least 1024 output tokens for these model families. Sources:

- https://docs.bigmodel.cn/cn/guide/models/vlm/glm-5.3-flash
- https://docs.bigmodel.cn/api-reference/%E6%A8%A1%E5%9E%8B-api/%E5%AF%B9%E8%AF%9D%E8%A1%A5%E5%85%A8
- https://docs.bigmodel.cn/cn/api/api-code

Before freeze, the client was updated with two reviewed request profiles:
`glm-4.7-flash` retains disabled thinking and 256 maximum tokens, while
`glm-5.3-flash` uses enabled thinking, low reasoning effort, 1024 maximum
tokens and a 120-second timeout. JSON-object output remains requested in both
profiles. The 1210 error is consistent with disabled thinking, but the
provider did not identify a specific field in the safe diagnostic; a new
synthetic probe is required to verify the complete 5.3-Flash request.

The revised client passed 23 offline tests locally and on the remote host. A
live synthetic probe then succeeded once with `glm-5.3-flash` (HTTP 200, 486
prompt tokens, 45 completion tokens, 531 total tokens; request ID
`202610150031271da33dde78ed4fef`). It chose the allowed `uniform_random`
policy after seeing one synthetic nonhit and did not use DYRK3 labels. This
verifies request compatibility, not scientific effectiveness or sustained
service availability.

Before any real-label campaign, the final protocol and manifest were revised
to select `glm-5.3-flash`, enabled thinking, low reasoning effort, 1024 output
tokens and a 120-second timeout. Sampling was disabled for improved
repeatability, a documented request setting that remains to be checked with
one final synthetic call. The two models must not be mixed within a paired
campaign comparison.

The final pre-freeze package passed 24 local offline tests. A full 50-query
synthetic dry run on 60 synthetic compounds completed all five batches with
50 distinct IDs for each of the bit and count representations. The actual
231 public structures still require the same remote synthetic smoke check;
the final GLM request with sampling disabled remains to be probed.
