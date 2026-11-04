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
| NVIDIA NeMo Agent Toolkit 1.9.0 (`tool_calling_agent`) | 3 | 3 | 1 |

NeMo Agent Toolkit row (added 2026-11-03): The model is the same local fake OpenAI-compatible server as every other row; no hosted model, no key. NAT 1.9.0 = tag `v1.9.0` (`baffefc68315b93e363cfd986c8f7e8dd45ce5e7`), `tool_calling_agent` workflow, `llms: {_type: openai}`, NAT defaults; NAT's agents always stream. n=3 per cell, run one after another; raw logs and the adapter are in [results/nat-1.9.0](results/nat-1.9.0/) and [harness/nat](harness/nat/). It also holds one request to a silent server for the whole 25-minute cap (no default request timeout; known upstream as NVIDIA/NeMo-Agent-Toolkit#1617), and returns the partial `Do` of a close-delimited stream as the answer, like most rows.

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

## Call-layer verification: Varis

Not a row in the table above, and not comparable to it. The table counts requests an
**agent framework** sends when the **model API** fails; this counts what a **calling
layer** does when the **service it calls** is slow. Same question, different unit — a
platform cannot be ranked against a framework, and putting it in the table would imply
a comparison that does not exist.

On 4 November 2026 Varis shipped SDK 1.2.0, replacing the request timeout with
`202 in_progress` plus an `invocation_id` you collect from afterwards. We had reported
the behaviour this replaces. Re-run against the release: **it works** — the service ran
once per call, the agent was charged once, the provider was paid once, and a same-key
retry returned the cached result without re-running anything. The MCP path behaves the
same way.

Criteria were written and committed before the first call, not after the numbers were
in. Results, timestamps and the scrubbed raw records:
[results/varis-2026-11-04](results/varis-2026-11-04/). Adapter, for any service you
publish there: [harness/varis](harness/varis/).

**The one mistake here that costs money:** a retry is a retry only if it carries the
same `Idempotency-Key`. A second request with a fresh key is a new invocation — the
service runs again and you are billed again. Our own first draft of the adapter did
exactly that. It would have reported a clean pass while charging the user twice.

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
- NeMo Agent Toolkit: nothing to report for this bench (no double execution); the default timeout is NVIDIA/NeMo-Agent-Toolkit#1617

## Record

- Discovered: 2026-10-20
- First public: 2026-10-20
- Patch commit: `d4c81919c2d8` (on `huggingface/smolagents`, PR #3036; not merged upstream)

## Citing the raw records

The per-run records behind this benchmark are archived as a citable dataset:

**Simin Yuan.** *Agent failure-mode benchmarks: raw measurement records.* Zenodo, 2026.
DOI [10.5281/zenodo.23808696](https://doi.org/10.5281/zenodo.23808696) — concept DOI for later versions: `10.5281/zenodo.23808695`.

- 721 files: the untouched result files from all four benchmarks, copied byte-for-byte at the commits named in this repository's record section.
- The records are CC-BY-4.0; the code in this repository keeps its own license (below).
- Cite this repository for the method, and the dataset for the runs behind the numbers.

## License

License: MIT, except `upstream/smolagents-fix.patch`, which is a diff against Hugging Face `smolagents`
(Apache-2.0); the code it patches stays under that license.
