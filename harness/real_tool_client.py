"""Drive one turn the way the upstream report does: real `terminal` toolset, yolo approvals.

    python harness/real_tool_client.py <port> <workdir> <marker>
"""
import json, os, sys, time, traceback

PORT, WORK, MARKER = sys.argv[1], sys.argv[2], sys.argv[3]
os.makedirs(WORK, exist_ok=True)
BASE = "http://127.0.0.1:%s/v1" % PORT
KEY = "fake-key-1234567890"
os.environ["HERMES_HOME"] = os.path.join(WORK, ".hermes")
os.environ.update({"OPENAI_API_KEY": KEY, "OPENAI_BASE_URL": BASE, "OPENAI_API_BASE": BASE,
                   "OTEL_SDK_DISABLED": "true", "HERMES_YOLO_MODE": "1"})
T0 = time.time()

import httpx
CONSUMED = []
for _name in ("iter_lines", "iter_bytes", "aiter_lines", "aiter_bytes"):
    _orig = getattr(httpx.Response, _name, None)
    if _orig is None:
        continue
    def _mk(orig):
        if getattr(orig, "__code__", None) and orig.__code__.co_flags & 0x80:
            async def awrapper(self, *a, **kw):
                n = 0
                async for chunk in orig(self, *a, **kw):
                    n += len(chunk)
                    yield chunk
                CONSUMED.append(n)
            return awrapper

        def wrapper(self, *a, **kw):
            n = 0
            for chunk in orig(self, *a, **kw):
                n += len(chunk)
                yield chunk
            CONSUMED.append(n)
        return wrapper
    setattr(httpx.Response, _name, _mk(_orig))

out = {"exception": None, "final": None}
try:
    from run_agent import AIAgent
    import agent

    out["agent_pkg"] = agent.__file__
    CALLS = os.path.join(WORK, "executor_calls.jsonl")

    if os.environ.get("PROBE_FEED"):
        import probe_feed
        probe_feed.install(WORK)

    import agent.conversation_loop as _cl
    _orig_round = _cl.run_tool_round
    import functools

    @functools.wraps(_orig_round)
    def _spy(agent, **kw):
        am = kw.get("assistant_message")
        tcs = getattr(am, "tool_calls", None)
        if tcs is None and isinstance(am, dict):
            tcs = am.get("tool_calls")
        for tc in (tcs or []):
            fn = tc.get("function") if isinstance(tc, dict) else getattr(tc, "function", None)
            name = fn.get("name") if isinstance(fn, dict) else getattr(fn, "name", None)
            args = fn.get("arguments") if isinstance(fn, dict) else getattr(fn, "arguments", None)
            with open(CALLS, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"name": name, "args": str(args)[:80]}) + "\n")
        return _orig_round(agent, **kw)

    _cl.run_tool_round = _spy

    agent_obj = AIAgent(base_url=BASE, model="fake-model", api_key=KEY, enabled_toolsets=["terminal"],
                        quiet_mode=True, save_trajectories=False, skip_context_files=True,
                        skip_memory=True, skip_background_review=True)
    r = agent_obj.run_conversation("run echo hi")
    out["final"] = {k: (str(v)[:400] if not isinstance(v, (int, float, bool, type(None))) else v)
                    for k, v in (r or {}).items() if k in ("completed", "api_calls", "final_response", "error")}
    text = (r or {}).get("final_response") or ""
    with open(os.path.join(WORK, "user_visible.txt"), "w", encoding="utf-8") as fh:
        fh.write(text)
except BaseException as e:
    out["exception"] = "%s.%s: %s" % (type(e).__module__, type(e).__name__, str(e)[:300])
    out["trace_tail"] = traceback.format_exc().splitlines()[-6:]
    try:
        with open(os.path.join(WORK, "user_visible.txt"), "w", encoding="utf-8") as fh:
            fh.write("EXCEPTION: " + out["exception"])
    except Exception:
        pass

out["elapsed_s"] = round(time.time() - T0, 2)
out["consumed_bytes_per_request"] = CONSUMED
out["consumed_total"] = sum(CONSUMED)
probe = 0
if os.path.exists(os.path.join(WORK, "executor_calls.jsonl")):
    probe = sum(1 for _ in open(os.path.join(WORK, "executor_calls.jsonl"), encoding="utf-8"))
out["probe_records"] = probe
out["marker_lines"] = sum(1 for _ in open(MARKER, encoding="utf-8")) if os.path.exists(MARKER) else 0
print("RESULT " + json.dumps(out, ensure_ascii=False), flush=True)
