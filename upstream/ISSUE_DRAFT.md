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

Measured with a local fake server (smolagents main @ 96f33fa, openai 2.54.0, Python 3.13, default settings):

| fault (every request) | requests now | wall time to error now | with the proposed change |
|---|---|---|---|
| 429, Retry-After: 1 | TBD | TBD | TBD |
| 500 | TBD | TBD | TBD |
| connection dropped mid-body | TBD | TBD | TBD |
| no answer (timeout) | TBD | TBD | TBD |

Wall time includes ~1 s of start-up; 429 wall times vary run to run because the outer waits are jittered.

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
