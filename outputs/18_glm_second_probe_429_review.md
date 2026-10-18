# Second GLM probe: HTTP 429 before model response

Date: 2026-10-14. The corrected synthetic-state probe was run against `glm-4.7-flash` on the remote Ubuntu desktop. The HTTP request returned 429 before the program received a model decision. No DYRK3 label was queried; the probe contains only synthetic feedback.

The previous adapter discarded the provider's JSON business error code and Retry-After header. The observed output therefore does **not** distinguish account rate limiting, model overload, usage cap, billing state or model permission. Do not describe it as a confirmed rate-limit cause and do not automatically retry.

The adapter now extracts only HTTP status, numeric business error code and numeric Retry-After, and maps official 429 codes to diagnostic categories. It does not echo raw provider error text or the API key. An offline test simulates business code 1302 and verifies that the key and provider text are absent from the exception. A future single synthetic probe may be used to diagnose the cause; if the account dashboard already explains the limit, use that information instead of another request.

The first successful request remains valid evidence of endpoint/model/authentication connectivity. Neither probe is evidence of active-search performance. The DYRK3 pool remains pre-freeze.
