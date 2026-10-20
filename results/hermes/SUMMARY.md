# Hermes Agent row — raw counts, three ways of counting a log line

`server.jsonl` is a log of everything the fault server saw, not a list of API requests. Three kinds
of line appear in it, and only the first should be called a request:

| line kind | how it is identified | counted as |
|---|---|---|
| chat request | `action` set, path `/v1/chat/completions` | **requests** (comparable to the other rows) |
| start-up probe | `action` set, path `/api/show` | reported separately, never as a retry |
| disconnect event | `action` is `null` (written when the client gives up on a held request) | **events** |

Counting `wc -l` therefore overcounts. It overcounted the `timeout` cells by 3 here and by 3 in
`results/e1/*/timeout`, and it overcounted every cell in this row by 1 (the `/api/show` probe).
`tools` is the tool's own side effect (`counter.txt`), never a framework claim.

| delivery | fault | requests | probe | disconnect events | tool executions | span (s) | wall (s) | exit | first gaps (s) |
|---|---|---|---|---|---|---|---|---|---|
| plain | `429` | 3 | 1 | 0 | N/A | 2.1 | 11.79 | 0 | 1.03, 1.03 |
| plain | `429-hard` | 1 | 1 | 0 | N/A | 0.0 | 9.77 | 0 |  |
| plain | `429-neutral-body` | 3 | 1 | 0 | N/A | 2.1 | 11.79 | 0 | 1.04, 1.03 |
| plain | `500-neutral` | 23 | 1 | 0 | N/A | 305.1 | 315.75 | 0 | 0.03, 2.43, 5.63, 15.85, 2.63 |
| plain | `500-ratelimit-text` | 23 | 1 | 0 | N/A | 301.3 | 311.89 | 0 | 0.03, 2.43, 4.23, 16.06, 2.24 |
| plain | `500-text-429` | 23 | 1 | 0 | N/A | 300.7 | 311.31 | 0 | 0.03, 2.43, 5.83, 17.05, 2.83 |
| plain | `after-tool-500` | 1 | 1 | 0 | N/A | 0.0 | 10.55 | 0 |  |
| plain | `after-tool-drop` | 1 | 1 | 0 | N/A | 0.0 | 8.28 | 0 |  |
| plain | `drop` | 4 | 1 | 0 | N/A | 0.1 | 11.16 | 0 | 0.04, 0.03, 0.03 |
| plain | `timeout` | 2 | 1 | 3 | N/A | 902.5 | 1500.12 | 137 | 902.53 |
| stream | `after-tool-drop` | 1 | 1 | 0 | N/A | 0.0 | 8.92 | 0 |  |
| stream | `after-tool-drop-chunked` | 1 | 1 | 0 | N/A | 0.0 | 7.91 | 0 |  |
| stream | `drop` | 4 | 1 | 0 | N/A | 0.1 | 9.04 | 0 | 0.04, 0.03, 0.03 |
| stream | `drop-chunked` | 63 | 1 | 0 | N/A | 366.6 | 375.44 | 0 | 1.01, 2.01, 2.64, 1.01, 2.01 |
## Notes on individual cells

- **`429` = 3 chat requests, not 4.** The fourth line was the `/api/show` start-up probe. Three
  attempts, ~1 s apart, i.e. Hermes honours `Retry-After` and then stops — the same request count
  as the OpenAI Agents SDK and LangGraph rows, not one more.
- `429-hard` = 1 request (hard quota: one attempt, no retry). `429-neutral-body` = 3, identical in
  shape to `429`, so the body's wording changes nothing.
- **`500-neutral`, `500-ratelimit-text`, `500-text-429` = 23 requests each over ~310 s**, with a
  repeating gap motif (~1 s, ~2.4 s, ~5.3 s, then ~70 s). The three cells differ only in the error
  body's wording and the count did not move: Hermes decides on the status code, not the text.
- `drop-chunked` = **63 requests over 368 s**, the largest amplification anywhere in the matrix
  (CrewAI's worst is 27).
- `after-tool-*` = 1 request: with no tool executed, no request ever carried a tool result, so the
  condition those cells exist to test never occurred.
- `timeout` was killed at the harness cap (1500 s, `exit=137`) and is **not** a completed
  measurement: one chat request was held ~900 s, the next ~584 s, and the cap fired mid-wait. It
  still shows Hermes has no default per-request timeout that would end this earlier.

## Tool executions are not measurable here

`counter.txt` does not exist in any cell. That is not Hermes refusing to duplicate a tool — the tool
never reached the model:

```
"tools_offered": ["tool_search", "tool_describe", "tool_call"]
```

`harness/e1_client.py` registers `counter`, and Hermes's progressive disclosure defers it behind
`tool_search`/`describe`/`call` (log: `Tool Search (tier 1): 1 MCP/plugin tools deferred ... behind
tool_search/describe/call`). `fault_server.py` then takes its documented fallback branch — *"client
offered no native tools: answer in ReAct text"* — and Hermes, which does not parse ReAct text into
tool calls, treats that string as the final answer (`api_calls=1`).

So this column is **N/A**, not 0. A 0 would claim Hermes is immune to duplicate tool execution,
which this run does not establish. Measuring it needs a non-default setup (`tools.tool_search.enabled:
off` in the cell's `HERMES_HOME/config.yaml`, or an eager-tool list); that is left as a proposal
rather than silently applied, because "default configuration" is the premise of the matrix.
