# Retry-After control (2026-10-20)
Fake server answers every request 429 with `Retry-After: 3` (s3.py). Default configs (r2.py).
- OpenAI Agents SDK 0.24.0: requests at t=3.0, 6.0, 9.01; x-stainless-retry-count 0,1,2 -> gaps 3.0 s.
- LangGraph 1.2.16 / langchain-openai: t=3.04, 6.05, 9.05; count 0,1,2 -> gaps 3.0 s.
With `Retry-After: 1` the same clients spaced retries 1.0 s (evidence/e0-retry). Gaps track the header,
so the inner openai client honors Retry-After; this is not its default backoff.
smolagents uses the same openai client inside, so its inner layer inherits this; its outer layer
(smolagents-429.jsonl, Retry-After: 1) slept 7.44 s and 26.19 s, measured from the last request of
one group to the first request of the next, with RETRY_WAIT shrunk to 2: it ignores Retry-After.

## smolagents, measured (added same day)
smolagents 1.26.0 OpenAIServerModel against s3.py (`Retry-After: 3`), r429.py (RETRY_WAIT shrunk to 2 only to finish fast):
9 requests, x-stainless-retry-count 0,1,2 in three groups. Inner gaps all 3.00 s -> inner layer honors Retry-After (measured, not inferred).
Outer sleeps (last request of a group -> first of the next): 5.16 s and 14.82 s, unrelated to the header -> outer layer ignores it.
