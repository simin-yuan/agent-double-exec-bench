# Hermes layer-isolation runs (E5)

These runs isolate the retry layers behind the two Hermes numbers already reported in
[`../plain/500-neutral`](../plain/500-neutral) (23 requests) and
[`../stream/drop-chunked`](../stream/drop-chunked) (63 requests).

Everything here is a local run against a fake server on 127.0.0.1. No provider was contacted.

## Environment

| item | value |
|---|---|
| framework | `NousResearch/hermes-agent` @ `c5a3c0f8767a72203363d249add14142dbcf3cc7` |
| python | 3.11.16 |
| openai client | 2.24.0 (the user agent recorded in `server.jsonl` is `OpenAI/Python 2.24.0`) |
| fake server | `harness/fault_server.py`, modes `500-neutral` and `drop-chunked` |
| cells run | `plain/500-neutral` and `stream/drop-chunked` only, same two cells as before |
| machine | Windows 11 |

## How the layers were switched off

| layer | knob | where |
|---|---|---|
| mid-stream retry (3 attempts: 1 s, 2 s) | `HERMES_STREAM_RETRIES=0` | environment |
| application retry budget (default 3) | `agent.api_max_retries` | `config.yaml` under `HERMES_HOME` |
| recovery ladder (default 5 cycles: 15/30/60/60/60 s) | `agent.auto_recovery_cycles` | `config.yaml` under `HERMES_HOME` |

`api_max_retries: 0` is clamped to 1 by the code, so the "retries off" rows below are really
"one attempt per call". The configs used are in [`_cfg/`](_cfg).

## Results

Chat requests only. The startup `/api/show` probe and connection-close events are excluded.

| group | config | `500-neutral` | `drop-chunked` |
|---|---|---|---|
| `a-default` | defaults | **23** (18 streaming + 5 non-streaming), 291.6 s | **63** (63 streaming), 362.3 s |
| `b-no-ladder` | `auto_recovery_cycles: 0` | **4** (3 + 1), 6.9 s | **18**, 38.4 s |
| `c-no-retries` | `api_max_retries: 0` (clamped to 1) | **10** (6 + 4), 242.5 s | **21**, 265.8 s |
| `d-base` | both off | **2** (1 + 1), <1 s | **6**, 10.1 s |
| `e-no-stream-retry` | `HERMES_STREAM_RETRIES=0` | **23** (18 + 5), 294.6 s | **21**, 318.2 s |
| `b-rerun1` | same as `b` | **4** (3 + 1), 7.9 s | **18**, 39.3 s |
| `b-rerun2` | same as `b` | **4** (3 + 1), 6.9 s | **18**, 40.2 s |
| `b-rerun3` | same as `b` | **4** (3 + 1), 8.3 s | not kept (500 cell only) |

Spans are first-to-last request in `server.jsonl`. Five ladder waits were observed in every
defaulted group (16-18 s, 30-36 s, 60-72 s x3), matching the documented 15/30/60/60/60 s.

## What the numbers say

- `500-neutral`: streaming attempts are exactly `(1 + auto_recovery_cycles) x api_max_retries`
  - `a` 6 x 3 = 18, `b` 1 x 3 = 3, `c` 6 x 1 = 6, `d` 1 x 1 = 1.
  On top of that, the first attempt of a round is sometimes retried immediately without
  streaming (0.01-0.03 s later). That fallback fired in 4 of 4 first rounds (`b`, `b-rerun1/2/3`)
  but only in 5 of 6 rounds in `a`, and 4 of 6 in `c` - which is why `a` totals 23 rather than 24.
  **Why some ladder rounds skip that fallback is not explained here.**
- `drop-chunked`: calls = `2 x api_max_retries` for the first round plus `api_max_retries` per
  ladder round (`a` 6+15=21, `c` 2+5=7, `b` 6, `d` 2), and each call makes
  `1 + HERMES_STREAM_RETRIES` attempts (3 by default, 1 in `e`). 21x3=63, 6x3=18, 7x3=21,
  2x3=6, 21x1=21 - all exact.
- Time, not request count, is where the cost sits: 11 s with both layers off, 18 s with only
  the ladder off, 253 s with only the retry budget off, 303 s at defaults. The ladder accounts
  for nearly all of it.
- `HERMES_STREAM_RETRIES=0` changes nothing for `500-neutral` (23 stays 23) because that cell
  fails when headers arrive; it only bites on `drop-chunked` (63 to 21).

## Notes on this directory

- File layout per cell: `server.jsonl` (one line per HTTP request the fake server saw) and
  `client.txt` (framework stdout).
- Absolute local paths in `client.txt` were replaced with `<repo>` (this checkout) and
  `<local>` (the framework install), so the dumps point nowhere real. Nothing else was edited.
- The on-disk state directories Hermes created next to each run (`work/`, containing its own
  config, logs and session dumps) were not copied here.
- Shell logs of each batch were not copied either: they only contain a traceback from the fake
  server thread that hits a connection reset when the client aborts, unrelated to retry counts.
- `b-rerun1/2/3` exist to answer one question: is the immediate non-stream fallback
  deterministic in the first round. It was present in all four runs of `b`, so the
  missing-one-request case only appears in ladder rounds.

## Reproduce

The cells are driver-agnostic; three steps reproduce any row above.

1. Start the fake server: `python harness/fault_server.py <port> 500-neutral out.jsonl`
   (or `drop-chunked` for the stream cell).
2. Run the client: `python harness/e1_client.py hermes <port> <workdir>` with `PYTHONPATH`
   pointing at a `hermes-agent` checkout at `c5a3c0f`; pass the stream flag for the stream cell.
3. To switch a layer off, write `agent.api_max_retries` and/or `agent.auto_recovery_cycles`
   into the `config.yaml` of the framework home directory the client points at (the three
   files in [`_cfg/`](_cfg) are exactly what was used), and set `HERMES_STREAM_RETRIES=0` in
   the environment for the mid-stream layer.

The batch wrapper that looped over the five groups lives in the private working copy; it only
automates the three steps above and adds nothing to the measurement.
