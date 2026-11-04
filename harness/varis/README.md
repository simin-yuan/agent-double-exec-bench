# harness/varis

Answers one question against any service you publish on Varis:

> When a call runs longer than the request window, does the platform hand back
> something you can collect from — and if an agent retries, does the service run
> and bill a second time?

This is not a ninth row in the framework table. The table compares **agent
frameworks** under a model-API fault; this compares a **calling layer** under a
slow-service fault. Same spirit, different unit of measurement — the numbers are
not comparable to the `requests per 429` columns and are not presented as if they
were.

## Run it

```bash
export VARIS_AGENT_KEY=var_ak_...      # your agent key; never commit it
export VARIS_SERVICE_ID=var_srvc_...   # a service you control
export DELAY_SECONDS=35                # must exceed the ~30s request window
python run_varis.py --out ./varis-run
```

Two calls to the service, two same-key retries. With a 35 s delay that is roughly
four billable invocations — **run it against your own service, and know what it
costs before you start.** There is no rate-limit testing here and no concurrency.

## The one thing that is easy to get wrong

A retry is only a retry if it carries **the same `Idempotency-Key`**. Sending a
second request with a fresh key is a new invocation: the service runs again and you
are charged again. If you build a "does it re-run my service?" test with a new key
each time, the answer is always yes and you have measured nothing except that
invocations cost money.

The runner sends the key on the first call specifically so the retry can reuse it.
Older versions of this file did not, and that version would have charged you twice
while reporting a clean result. If you copy this pattern elsewhere, keep that line.

## What to compare

The client's view is one of three, and the weakest of them.

| source | what only it can tell you |
|---|---|
| client response | what the caller was handed: status code, `invocation_id`, `replayed` |
| **your service's own request log** | **whether the body actually executed, and how many times** |
| **your account ledger** | **how many charges actually landed** |

A `200` with `replayed: true` is the platform telling you it replayed. It is not
the service telling you it did not run. Count from the service's log.

## Reading the output

`varis-run/http.json` has three sections:

- `s1` — the slow call. `status` should be `in_progress` with an `invocation_id`,
  and `final` shows what the lookup returned once the invocation finished.
- `s1b` — the same-key retry. `replayed` and `has_output` are the interesting
  fields; `invocation_id` should match the `s1` entry of the same index.
- `s2` — a placeholder. Identity stability is a comparison you make across `s1`
  and `s1b` for the same index: `request_id` and `invocation_id` should be
  unchanged.

One field is a trap: in our own published JSON, the `s1b` records carry a
top-level `idempotency_key` of `null`, because the value lives under `retry`. It
is a redundancy in the record layout, not a missing key. If you read that field
and conclude the retry used no key, you will draw the opposite conclusion from the
data.

## What is not covered

Concurrent invocations, invocation expiry, payloads above a few kilobytes, and the
case where a provider never reports completion. A test that does not cover these
says nothing about them either way.
