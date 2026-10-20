# Question: one network fault — what does an agent framework do twice?

## Already established (E0, raw data in evidence/)
- Tool re-execution: after a tool ran once, injecting 500 x2 or a mid-stream drop on the NEXT model request
  never re-ran the tool (OpenAI Agents SDK 0.24.0 chat/responses x stream/plain, LangGraph 1.2.16, smolagents 1.26.0): count = 1.
  Caveat learned: smolagents returns tool results without the standard `tool` role; the fake server must detect that.
- Model-request amplification, every request answered 429 with `Retry-After: 1`:
  Agents SDK 3 requests, LangGraph 3, smolagents OpenAIServerModel 9.
  smolagents: `ApiModel.retryer` (3 attempts; delay multiplied BEFORE each sleep: sleep1 = 60*2*(1+U) = 120-240 s,
  sleep2 = sleep1*2*(1+U) = 240-960 s, i.e. 6-20 min asleep before the error surfaces) wraps an openai client
  that keeps its default `max_retries=2`; outer gaps ignore Retry-After; `is_rate_limit_error` is substring matching,
  so a 500 whose body says "rate limit" is also retried 9 times (`harness/e0/sX.py`); a neutral 500 gives 3.
  Both directions of misclassification must be measured in E1: an unrelated error whose text contains "429"
  (e.g. a request id or "14290 tokens") gets the long backoff; a real 429 wrapped into text without those substrings gets none.
- Precedent: Agents SDK `run_internal/model_retry.py` reads retry_after and sets the inner client's retries to 0
  for LiteLLM / any-llm when its own retry is enabled.

## E1 — measurement matrix (deliverable: harness/ + results/ + results/SUMMARY.md)
Build ONE fault server (`harness/fault_server.py`, OpenAI Chat Completions + Responses compatible, streaming and not)
with modes: `429` (Retry-After: 1), `429-hard` (body code `insufficient_quota`, Retry-After: 3600),
`500-neutral`, `500-ratelimit-text`, `timeout` (accept, never answer), `drop` (close mid-stream),
`after-tool-500`, `after-tool-drop` (E0 scenarios: fault only on the request carrying the tool result).
Log per request: t, path, retry headers (x-stainless-retry-count etc.), has_tool_result, scenario.
Tool under test = a counter tool appending one line per execution to a file.

Frameworks (default configuration, latest stable, pin versions), max 6 + control:
1. OpenAI Agents SDK (chat + responses)  2. LangGraph (langchain-openai)  3. smolagents — OpenAIServerModel AND LiteLLMModel
4. CrewAI  5. Pydantic AI  6. Google ADK (via LiteLLM / OpenAI-compatible)  Control: Hermes Agent (NousResearch, latest main; record commit).
Record per cell: requests per logical model call, gaps between them, Retry-After honored (y/n per layer),
wall time until error (for 429-hard cap the run at 25 min and record "≥25 min"; smolagents defaults can sleep up to 20 min), tool execution count.
For long backoffs you MAY shrink a framework's wait constant ONLY to count requests; record that you did,
and measure wall time separately with defaults for at least one cell per framework.

Stop conditions: a framework will not install or talk to the fake server after 30 min of effort → record "not testable" + reason, move on.
Total compute for E1 must stay small; do not loop on retries of the whole matrix more than twice.

## E3-prep — smolagents fix on a local clone (do NOT open anything upstream)
- Clone huggingface/smolagents at latest main into `upstream/smolagents` (gitignored). Read CONTRIBUTING.md and the
  PR template; write their requirements into `upstream/SMOLAGENTS_RULES.md` (this file IS committed).
- Search its open and closed issues/PRs for: retry, rate limit, Retry-After, max_retries, RETRY_WAIT. List every hit
  with number, title, state in `upstream/PRIOR_ART.md`. If an existing issue/PR already covers the stacking, STOP E3-prep and report.
- Minimal fix: when the model's own retry is enabled and the user did not pass `max_retries` in client_kwargs,
  create the OpenAI/Azure client with `max_retries=0`; detect 429 by `status_code` when the exception has one,
  keep substring matching only as fallback. Add tests that fail before and pass after. Run the repo's own lint/tests.
- Save as `upstream/smolagents-fix.patch` + `upstream/TEST_LOG.txt` (commands and outputs).

## Final report (the last commit on e1): REPORT.md
Table of all cells, list of every claim with the evidence file that proves it, list of anything not done and why.
