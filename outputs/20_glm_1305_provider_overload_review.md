# GLM provider overload before DYRK3 v1 freeze

On 2026-10-15, two consecutive synthetic-only `glm-4.7-flash` probes returned
HTTP 429 with provider business code `1305` (`model_overloaded`). Both reported
`uses_real_labels: false` and `request_succeeded: false`; neither queried the
DYRK3 oracle. A prior synthetic probe had succeeded with this account and
endpoint. The two failures do not establish an invalid key, insufficient
credits, or an exhausted account quota. The provider's error-code reference
distinguishes `1305` (model traffic) from `1302` (account rate limit), `1308`
(usage limit), and `1113` (account payment required):
https://docs.bigmodel.cn/cn/api/api-code

Before any frozen DYRK3 campaign, the client was changed to retry **only**
`1305`, with three total attempts and waits of 5 and 15 seconds. Successful
decision records retain each HTTP attempt; exhausted decisions stop before the
next oracle query and append an event to a private failure history. A resumed
campaign replays completed batches and retains those failure events for cost
reporting. The fixed and random references do not require GLM availability.

The visible BigModel resource-package screen showed available gifted balances,
including packs labelled for `glm-5.3-flash`, but did not establish a matching
`glm-4.7-flash` allowance or a cause for `1305`. No purchase or model switch
was made. A future model change must be declared before freezing or treated as
a new campaign version; it cannot be inserted into the frozen comparison.

The revised retry package passed 19 tests locally and on the remote host. Its
subsequent synthetic probe raised a 60-second `TimeoutError` while waiting for
the HTTP response, after the request was sent. This is a transport timeout,
not a provider business-code response. The synthetic probe still used no
DYRK3 labels. The client was updated before freezing to report
`request_timeout` without an automatic timeout retry and to retain one
attempted request for cost tracking. The request may have been processed by
the provider, so its token use cannot be inferred from the local exception.
This correction has not yet been uploaded or tested on the remote host.
