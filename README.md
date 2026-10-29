# agent-double-exec-bench

Simin Yuan · [github.com/simin-yuan](https://github.com/simin-yuan)

**One network fault: what does an agent framework do twice?**

We pointed seven agent frameworks at a local fake model server that fails on purpose
(429, 500, dropped connections, silence) and counted, from the server's own log,
how many requests each one sends and how many times a side-effecting tool runs.
Default settings everywhere. No real API, no cost; anyone can rerun it.

| framework (version) | requests for one 429 (Retry-After: 1) | requests for one 500 (message unrelated to rate limits) | tool runs after a failure |
|---|---|---|---|
| OpenAI Agents SDK 0.24.0 | 3 | 3 | 1 |
| LangGraph 1.2.16 | 3 | 3 | 1 |
| Pydantic AI 2.58.0 | 3 | 3 | 1 |
| Google ADK 2.12.0 | 3 | 3 | 1 |
| smolagents 1.26.0 | **9** | 3 | 1 |
| CrewAI 1.15.28 | **27** | 9 | **3** (known: crewAIInc/crewAI#5802) |
| Hermes Agent @ c5a3c0f | 3 | **23** | not measurable (see results/hermes) |

## What we found
1. **Tools are almost never run twice.** Only CrewAI re-runs a tool after a failed model request:
   its agent retry restarts the whole task. This is already reported upstream (#5802, fixes in #5822, #6048);
   we add a deterministic repro and the request counts.
2. **Retry layers multiply.** smolagents wraps an `openai` client that keeps its own 2 retries inside a
   3-attempt retry loop: 3 × 3 = 9 requests per rate limit. CrewAI stacks three layers: 27.
3. **Some frameworks decide whether to retry by reading the error text.** Same status code, only the message changes:

   | every request answers 500 with… | smolagents | CrewAI | Agents SDK, LangGraph, Pydantic AI, ADK |
   |---|---|---|---|
   | an unrelated message | 3 | 9 | 3 |
   | a message containing "rate limit" | **9** | **27** | 3 |
   | a message containing "429" | **9** | 9 | 3 |

   smolagents' outer retry loop also ignores `Retry-After` and sleeps 6–20 minutes before failing.

Full table, every cell next to its log: [results/SUMMARY.md](results/SUMMARY.md). Method and caveats: [REPORT.md](REPORT.md).

## Rerun
`harness/` contains the fault server and one runner per framework; `results/` holds the raw logs. The
`agent_pkg` field records a relative sandbox path: absolute build paths from the machine the runs were
taken on were replaced on 2026-10-29, with no change to any measurement, counter, log line or verdict.
Requests are counted from `server.jsonl`, never from client output, and only lines that record a model request
count: the Hermes start-up probe (`/api/show`) and the `client_closed_held_connection` events in timeout cells are
log lines, not requests. A plain `wc -l` will overcount.

## Upstream
- smolagents: issue huggingface/smolagents#3034, fix huggingface/smolagents#3036
- CrewAI: issue crewAIInc/crewAI#8332, fix crewAIInc/crewAI#8333; measurements added to crewAIInc/crewAI#7771
- Hermes Agent: measurements added to NousResearch/hermes-agent#140255

## Record

- Discovered: 2026-10-20
- First public: 2026-10-20
- Patch commit: `d4c81919c2d8` (on `huggingface/smolagents`, PR #3036; not merged upstream)

## License

License: MIT, except `upstream/smolagents-fix.patch`, which is a diff against Hugging Face `smolagents`
(Apache-2.0); the code it patches stays under that license.
