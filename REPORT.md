# REPORT — E1 done, E3-prep stopped on a problem in TASKS.md (owner decision needed)

## ⚠ STOP: the E3-prep "minimal fix" in TASKS.md would remove retries smolagents has today

TASKS.md asks: *"when the model's own retry is enabled and the user did not pass `max_retries` in client_kwargs,
create the OpenAI/Azure client with `max_retries=0`"*, citing the Agents SDK as precedent. Two problems, with evidence:

**1. The fix drops ALL retries for 5xx, dropped connections and timeouts on `OpenAIServerModel`.**
smolagents' outer retry (`ApiModel.retryer`) only retries when `is_rate_limit_error` matches. For every other
transient error the *only* retries today are the OpenAI SDK's own (`max_retries=2`; the SDK retries 408/409/429/5xx
and connection errors — `openai/_base_client.py` `_should_retry`, openai 2.54.0). Measured with the fix's client
state applied by configuration (`client_kwargs={"max_retries": 0}`, row `smol-openai-mr0`, not a code change):

| fault | smolagents today | with `max_retries=0` | evidence |
|---|---|---|---|
| 500, neutral text | 3 requests (2 SDK retries) | **1 request, run fails** | `results/e1/smol-openai/500-neutral`, `results/e1/smol-openai-mr0/500-neutral` |
| connection dropped mid-body | 3 | **1** | `smol-openai/drop`, `smol-openai-mr0/drop` |
| 500 on the request after a tool call | 1 + 3 | 1 + **1** | `smol-openai/after-tool-500`, `smol-openai-mr0/after-tool-500` |
| silent server | 3 × 600 s (≥ 25 min) | 1 × 600 s (error at 602 s) | `smol-openai/timeout`, `smol-openai-mr0/timeout` |
| 429 | 9 (680 s) | 3, outer only (error at 1095 s) | `smol-openai/429`, `smol-openai-mr0/429` |

So the fix trades 9→3 requests on 429 for 3→1 on the far more common transient 5xx/connection failures. I do not
think a maintainer would accept that, and it is not what the cited precedent does.

**2. The precedent is narrower than TASKS.md states.** In openai-agents 0.24.0 the runner's own retry is opt-in
(`retry_settings` defaults to `None`), and even when enabled it **keeps the provider/SDK retries on the first
attempt** and zeroes them only on the runner's own replay attempts (plus explicit `max_retries=0` and stateful
requests). Source: `agents/run_internal/model_retry.py`, `_should_disable_provider_managed_retries`
("Keep provider-managed retries on the initial attempt for backward compatibility") and
`agents/extensions/models/litellm_model.py` ("Preserve provider-managed retries on the first attempt, but make runner
retries the sole retry layer by forcing LiteLLM's retry knobs off on replay attempts"). It applies to the OpenAI
chat/responses models too, not only LiteLLM / any-llm. Hermes Agent (source reading only, commit c5a3c0f) does set
the SDK's `max_retries=0`, but its outer loop also retries 5xx (`agent/agent_runtime_helpers.py`: "Delegate all
rate-limit / 5xx retry to hermes's outer conversation loop").

**Options for the owner (nothing implemented, nothing upstream):**
- **A (recommended, Agents-SDK style):** keep SDK retries on the first outer attempt; use
  `client.with_options(max_retries=0)` only for smolagents' outer *re*-attempts. 429: 3+1+1 = 5 requests instead of 9;
  5xx/drop/timeout behaviour unchanged. Smallest behaviour change, has a precedent.
- **B (TASKS.md as written + widen the outer predicate to 5xx/connection/timeout, Hermes style):** larger, and overlaps
  two open upstream PRs (#2186, #2382) that already propose status-code classification of transient errors.
- **C:** keep inner retries; make the outer predicate skip `openai.APIStatusError` 429s when the client already retried.
The status-code-first 429 detection (second half of the fix) is unaffected by this problem but overlaps #2186/#2382
(see `upstream/PRIOR_ART.md`).

Also for the owner: smolagents' CONTRIBUTING.md requires an accepted issue before a PR, and a disclosure of any
AI-assistant use in the PR (`upstream/SMOLAGENTS_RULES.md`, rule 3). Only the owner can write that PR text.

**Waiting for a decision before writing the patch, tests, `upstream/smolagents-fix.patch` and `upstream/TEST_LOG.txt`.**

---

## E1 — done
Deliverables: `harness/fault_server.py`, `harness/e1_client.py`, `harness/e1_run.sh`, `harness/e1_matrix.sh`,
`harness/e1_summarize.py`, `harness/scrub_paths.sh`; `results/e1/` (raw cells), `results/e1/TABLE.md` (every cell),
`results/e1/VERSIONS.txt` (pins), `results/SUMMARY.md` (tables + findings).
Rows: OpenAI Agents SDK 0.24.0 chat + responses, LangGraph 1.2.16 / langchain-openai 1.7.2, smolagents 1.26.0
OpenAIServerModel + LiteLLMModel (litellm 1.106.0), CrewAI 1.15.28, Pydantic AI 2.58.0, Google ADK 2.12.0 (LiteLlm).
13 modes: the 8 from TASKS.md, the `ok` control, `429-neutral-body` and `500-text-429` for the two misclassification
directions TASKS.md asks for, and `drop-chunked` / `after-tool-drop-chunked` (see finding 16). Non-streaming for all
rows, streaming for `ok` and the drop modes: 133 cells including the 5 `smol-openai-mr0` cells.
Defaults everywhere, no wait constant shrunk; 25-min cap per cell; whole matrix run once (plus the separate
`drop-chunked` and `mr0` cells).

## Claims and the evidence that proves each
(paths relative to `results/e1/`; counts from `server.jsonl`, tool runs from `counter.txt`)

| # | claim | evidence |
|---|---|---|
| 1 | All 8 rows + streaming talk to the fake server and run the tool exactly once with no fault (2 requests). | `*/ok/` |
| 2 | CrewAI runs the tool 3 times when every request carrying the tool result fails (500 or drop); cause: `Agent.max_retry_limit=2` re-runs the task from the prompt. | `crewai/after-tool-500/counter.txt`, `crewai/after-tool-drop/`, `crewai-stream/after-tool-drop-chunked/`; crewai `agent/core.py` |
| 3 | No other row re-executed a tool in any cell. | `*/after-tool-*/counter.txt` |
| 4 | CrewAI: 27 requests per 429 (3 SDK × 3 `llms/retry.py` × 3 agent), 9 for 429-hard and neutral 500, 27 for a 500 saying "Rate limit". | `crewai/429`, `crewai/429-hard`, `crewai/500-neutral`, `crewai/500-ratelimit-text` |
| 5 | CrewAI's middle retry layer does not honor Retry-After on OpenAI SDK errors (gaps 1.0–1.3 s, 1.7–2.4 s; RA 3600 retried). | `outer_gaps` of `crewai/*` in `cells.json`; `crewai/llms/retry.py` `_retry_after_seconds` (dict headers only) |
| 6 | Agents SDK, LangGraph, Pydantic AI, ADK: 3 requests for 429/500/drop, 1 for 429 with Retry-After 3600. | `agents-*/`, `langgraph/`, `pydantic-ai/`, `adk/` |
| 7 | The OpenAI SDK layer honors Retry-After (1.00–1.06 s gaps for RA 1; no retry for RA 3600, above `MAX_RETRY_AFTER_DELAY` = 120 s; Round 1 wrote 60 s — corrected). | `inner_gaps` in `cells.json`; `openai/_base_client.py` `_should_retry` |
| 8 | smolagents: 9 requests for 429 (680 s OpenAI / 872 s LiteLLM to error) — E0's count of 9 reproduced with full default waits. | `smol-openai/429`, `smol-litellm/429` |
| 9 | smolagents retries a quota 429 (RA 3600) for 591 s although the SDK declined to. | `smol-openai/429-hard` |
| 10 | smolagents retries an unrelated 500 whose text contains "429": 9 requests, 500–621 s. | `smol-*/500-text-429` |
| 11 | smolagents LiteLLMModel does not retry a real 429 whose text lacks the trigger strings; OpenAIServerModel does (1066 s). | `smol-litellm/429-neutral-body`, `smol-openai/429-neutral-body` (exception text in `client.txt`) |
| 12 | smolagents outer gaps 142–232 s then 349–831 s, Retry-After ignored; matches 60·2·(1+U) and ·2·(1+U) again. | `outer_gaps` in `cells.json`; smolagents `utils.py` `Retrying.__call__` |
| 13 | LangGraph/langchain-openai has no request timeout by default (held 25 min, no retry). | `langgraph/timeout/server.jsonl`; langchain-openai `request_timeout` default `None` |
| 14 | All other rows: 600 s timeout, retried twice (≥ 25 min, error not reached within the cap). | `*/timeout/server.jsonl` (close events 600 s apart) |
| 15 | No SDK retries a stream that drops after the 200; with chunked framing every row raises. | `*-stream/drop-chunked` |
| 16 | A close-delimited truncated stream is returned as a successful final answer `'Do'` by 5 of 6 frameworks (qualified: HTTP-legal end of body). | `*-stream/drop`, `*-stream/after-tool-drop` |
| 17 | smolagents streaming with close-delimited truncation loops 20 steps (23 requests) without re-running the tool. | `smol-*-stream/drop`, `smol-*-stream/after-tool-drop` |
| 18 | The TASKS.md fix's client state removes all 5xx/drop retries in smolagents (3 → 1). | `smol-openai-mr0/*` vs `smol-openai/*` |
| 19 | No upstream issue/PR covers the retry stacking; #2186/#2382 overlap the status-code half. | `upstream/PRIOR_ART.md` |
| 20 | smolagents contribution rules (issue first, one PR at a time, AI disclosure, ruff + pytest). | `upstream/SMOLAGENTS_RULES.md` |

## Not done, and why
- **E3-prep patch, tests, `upstream/smolagents-fix.patch`, `upstream/TEST_LOG.txt`**: stopped on the problem above.
  The clone is at `upstream/smolagents` (main 96f33fa, gitignored); prior art and rules are done.
- **Hermes Agent control (NousResearch main, commit c5a3c0f8767a72203363d249add14142dbcf3cc7)**: cloned and installed,
  and an `e1_client.py` branch was written, but executing the checkout was refused by the working environment's
  permission policy (code from an external repository). Not run. To run it:
  `PYTHONPATH=<checkout> sh harness/e1_run.sh <venv> hermes <mode>`. Only its source was read (SDK `max_retries=0`,
  own outer loop that honors Retry-After and retries 5xx).
- **Prior-art search method**: the GitHub API was not reachable from the working environment; the issue search
  pages were read as rendered text, so some states read "not shown". Details in `upstream/PRIOR_ART.md`.

## Method notes and deviations
- litellm 1.106.0 fails on its first call with `No module named 'mcp'`; `mcp` 2.3.0 was added to the smolagents and
  ADK venvs (`results/e1/VERSIONS.txt`). The smolagents venv therefore resolved openai 2.54.0 (litellm's pin).
- The fake model re-issues the tool call to any request that lacks the tool result. This is what makes a restart
  visible as a second tool run (finding 2). It assumes a real model would call the tool again on the same prompt.
- E0's tool re-execution runs (`harness/e0/py_runner.py`) used `RETRIES` default `0`, i.e. the SDK's retries were
  off. E1 re-measured with defaults; the count stayed 1 for every framework E0 covered.
- Machine paths in `client.txt` are replaced by `$VENVS` / `$REPO` (`harness/scrub_paths.sh`).
