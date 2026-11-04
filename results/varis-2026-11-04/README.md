# Independent verification: Varis long-running invocations

**Simin Yuan · [github.com/simin-yuan](https://github.com/simin-yuan) · Light Emerge Co., Ltd.**

On 4 November 2026 Varis released SDK 1.2.0, which changes what happens when a
service takes longer than the ~30 second request window: instead of a timeout the
call returns `202 in_progress` with an `invocation_id`, and the result can be
collected later by that id without re-running the service or charging twice.

We had reported the behaviour this replaces. We re-ran the same scenarios against
the release and this is what we measured.

**Verdict: the fix works.** Every scenario passed the criteria we wrote down and
committed before the first call was made.

---

## What we tested

Four scenarios, each run twice, against our own service (a 35-second delayed echo
that we publish on Varis for exactly this purpose). No third-party services, no
load testing, no changes to any parameter between runs.

| | scenario | what it asks |
|---|---|---|
| S1 | slow response | Does a 35 s call return `202 in_progress` instead of a 504, and can the result be collected by id? |
| S1b | same-key retry | After a completed call, does retrying with the same key return the result without re-running the service? |
| S2 | request identity | Do `X-Varis-Request-Id` and `invocation_id` stay stable across the retry? |
| S3 | MCP path | Do the same guarantees hold through `invoke_service` / `get_invocation`? |

## What we measured

| | result |
|---|---|
| S1 (n=2) | `202` + `status: in_progress`; result collected by id; service ran **once** per call; agent charged **once** |
| S1b (n=2) | `200` + `replayed: true` in 1.8–2.4 s; **same `execution_id` as the first call**; no new execution; no new charge |
| S2 (n=2) | `request_id` and `invocation_id` identical before and after the retry |
| S3 (n=2) | `get_invocation` exists as a tool; `invoke_service` reports `in_progress`; result returned; service ran **once** per call; charged **once** |

Six calls total, four billable. Reconciled three ways — client response, the
service's own request log, and the account ledger. The two same-key retries appear
in none of the three as an execution or a charge.

## What the implementation does that the docs do not say

These are properties of the shipped behaviour, worth knowing if you are building
against it. None of them is a defect.

1. **The `202` body carries more than `status` and `Retry-After`.** We observed
   nine fields, including `progress_percent`, `estimated_completion_at` and
   `instruction`.
2. **The agent's wall clock is longer than the provider's decision.** Our service
   reports "started" at ~20 s; the caller sees `202` at 24–27 s. It is inside the
   window, with less headroom than the number suggests.
3. **The lookup endpoint returns `202` while the invocation is still running** and
   `200` when it is done. A client that treats any `202` as a failure will
   misread a normal in-flight poll.
4. **The MCP path signals in-flight with `structuredContent.status`, not with a
   status code.** The outer response is `200`. Reading only the status code cannot
   distinguish an unfinished MCP call from a finished one. This is the protocol
   working as intended.
5. **`replayed: true` alone does not tell you the call succeeded.** We saw that
   flag on a `504` with an empty result before the fix, and on a `200` with the
   full result after it. Read the status and whether output is present.

## How to check our numbers

Nothing above requires trusting us:

- Every invocation id, request id, timestamp and status field is in
  [`data/fixverify-http.json`](data/fixverify-http.json) and
  [`data/fixverify-mcp.json`](data/fixverify-mcp.json), published here — the
  headers that describe the platform's own infrastructure have been stripped, the
  business identifiers have not, so the numbers can be recomputed from the file
  rather than taken on trust.
- The execution counts come from the service's own log — one line when a request
  arrives, one when it completes — not from the client's view.
- The charge counts come from the account ledger, before and after each batch.

If you publish a service on Varis and want to know how yours behaves under the
same conditions, the adapter in `harness/varis/` runs the same four scenarios
against any service and writes the same shape of log.

## What this does not cover

We tested one fault — a slow service — and one concurrency level. We did not test
concurrent invocations, invocation expiry, payloads above a few kilobytes, or what
happens when the provider never reports completion. The absence of a finding in
those areas is not a finding.

---

*The criteria above were written and committed before the first call was made, not
after the numbers were in. That order is the whole reason this counts as a
verification rather than an advertisement.*
