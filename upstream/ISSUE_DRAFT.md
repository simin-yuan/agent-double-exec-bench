# DRAFT — not posted. Owner reviews, edits and posts it, then waits for `status:accepted` before any PR.

**Title:** OpenAIModel: client retries and ApiModel retries multiply (9 requests and up to ~20 min per rate limit)

### What happens
`OpenAIModel` (and `AzureOpenAIModel`) wraps `client.chat.completions.create` in `ApiModel.retryer`
(3 attempts, 120–240 s then 240–960 s waits). The `openai` client inside it keeps its default `max_retries=2`.
On a 429 every outer attempt therefore makes 3 requests: 9 requests in total, and the error reaches the agent
only after the outer waits.

### Minimal repro
Any endpoint that always answers `429` with `Retry-After: 1`:

```python
from smolagents import OpenAIModel
model = OpenAIModel(model_id="any", api_base="http://127.0.0.1:PORT/v1", api_key="dummy")
model.generate([{"role": "user", "content": [{"type": "text", "text": "hi"}]}])
```

Measured with a local fake server that answers every request with the fault (smolagents main @ 96f33fa, unpatched
vs. with the proposed change; openai 2.54.0; Python 3.13; a `ToolCallingAgent` run with default settings):

| fault (every request) | requests now | wall time to error now | with the proposed change (requests / wall time) |
|---|---|---|---|
| 429, Retry-After: 1 | 9 | 835.2 s | 5 / 600.5 s |
| 500 | 3 | 15.6 s | 3 / 16.6 s |
| connection dropped mid-body | 3 | 15.7 s | 3 / 16.7 s |
| no answer (timeout) | 3 | 1815.8 s | 3 / 1817.0 s |

Wall time = client start to the exception. About 15 s of every value is interpreter start-up: twelve runs started
at once, and the first request reached the server 14.7–15.8 s after it started. The 429 times vary run to run
because the retryer's waits are jittered. The 3 requests in the 500, drop and timeout rows are the client's own
retries (`x-stainless-retry-count` 0, 1, 2); the retryer does not retry those errors, so they are unchanged.

Evidence for each cell (paths in the measurement repository, not part of the issue):

| cell | before (unpatched) | after (patched) |
|---|---|---|
| 429 | `results/e3/before/429/` | `results/e3/after/429/` |
| 500 | `results/e3/before/500-neutral/` | `results/e3/after/500-neutral/` |
| drop | `results/e3/before/drop/` | `results/e3/after/drop/` |
| timeout | `results/e3/before/timeout/` | `results/e3/after/timeout/` |

Each directory has `server.jsonl` (requests: one line per request; the timeout logs also have one
`client_closed_held_connection` line per request, 6 lines for 3 requests) and `client.txt` (`elapsed_s` in the
`RESULT` line = wall time to the exception).

The plain `model.generate(...)` snippet above, against the same server answering 429 (unpatched main):
`raised RateLimitError` after 9 requests, `elapsed_s 1063.7`.

### Proposed change (small, `OpenAIModel` only)
Keep the client's own retries on the first attempt; on the retryer's replays use
`self.client.with_options(max_retries=0)`. 5xx, connection errors and timeouts keep exactly today's behaviour
(they are only retried by the client); a rate limit costs 3 + 1 + 1 requests instead of 3 × 3.
This is the pattern the OpenAI Agents SDK uses (`agents/run_internal/model_retry.py`,
`_should_disable_provider_managed_retries`: provider retries stay on the initial attempt and are turned off on
replay attempts the runner manages itself).

Not in scope: how a rate limit is detected (`is_rate_limit_error`). #2186 and #2382 already propose
status-code-based classification; this change is independent of both and does not touch the predicate.

I have a patch with tests (fail before, pass after; `make quality` and `pytest ./tests/` run) and can open a PR
once this is accepted.

<!-- OWNER: AI-assistant disclosure required by CONTRIBUTING.md goes here. -->
[AI-ASSISTANCE DISCLOSURE — to be written by the owner]
