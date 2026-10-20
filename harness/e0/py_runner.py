"""Run one framework against cut_server.py and report what happened to the tool call.

usage: python py_runner.py FRAMEWORK MODE PORT WORKDIR
FRAMEWORK: agents-chat | agents-responses | langgraph | langgraph-responses | smolagents
MODE: stream | plain

The only tool is write_file(path, content). It writes into WORKDIR and records every call it
receives in WORKDIR/calls.jsonl, so execution is read from the side effect, not from the framework."""
import json, os, sys, traceback

FW, MODE, PORT, WORK = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
BASE = f"http://127.0.0.1:{PORT}/v1"
os.makedirs(WORK, exist_ok=True)
PROMPT = "Write the 40-line file notes.txt."


def write_file(path: str, content: str) -> str:
    """Write content to a file.

    Args:
        path: file name
        content: full file content
    """
    target = os.path.join(WORK, os.path.basename(path))
    with open(target, "w") as f:
        f.write(content)
    with open(os.path.join(WORK, "calls.jsonl"), "a") as f:
        f.write(json.dumps({"path": path, "content_chars": len(content),
                            "lines": content.count("\n"), "last_line": content.splitlines()[-1] if content else ""}) + "\n")
    return f"wrote {len(content)} chars to {path}"


out = {"framework": FW, "mode": MODE, "exception": None, "final_output": None}
try:
    if FW.startswith("agents"):
        import asyncio
        from openai import AsyncOpenAI
        from agents import Agent, Runner, OpenAIChatCompletionsModel, OpenAIResponsesModel, set_tracing_disabled, function_tool
        set_tracing_disabled(True)
        client = AsyncOpenAI(base_url=BASE, api_key="dummy", max_retries=int(os.environ.get("RETRIES", "0")))
        model = (OpenAIChatCompletionsModel("cut-model", client) if FW == "agents-chat"
                 else OpenAIResponsesModel("cut-model", client))
        agent = Agent(name="a", instructions="Use the tool.", model=model, tools=[function_tool(write_file)])

        async def go():
            if MODE == "stream":
                r = Runner.run_streamed(agent, PROMPT, max_turns=3)
                async for _ in r.stream_events():
                    pass
                return r.final_output
            r = await Runner.run(agent, PROMPT, max_turns=3)
            return r.final_output
        out["final_output"] = asyncio.run(go())
    elif FW in ("langgraph", "langgraph-responses"):
        from langchain_openai import ChatOpenAI
        from langchain_core.tools import tool
        from langgraph.prebuilt import create_react_agent
        llm = ChatOpenAI(model="cut-model", base_url=BASE, api_key="dummy", streaming=(MODE == "stream"), max_retries=int(os.environ.get("RETRIES", "0")),
                         use_responses_api=(FW == "langgraph-responses"))
        g = create_react_agent(llm, tools=[tool(write_file)])
        res = g.invoke({"messages": [("user", PROMPT)]}, {"recursion_limit": 6})
        msgs = res["messages"]
        out["final_output"] = msgs[-1].content if msgs else None
        ai = [m for m in msgs if getattr(m, "tool_calls", None) or getattr(m, "invalid_tool_calls", None)]
        if ai:
            out["first_ai_tool_calls"] = [{"name": t["name"], "args_keys": list(t["args"].keys())} for t in ai[0].tool_calls]
            out["first_ai_invalid_tool_calls"] = len(ai[0].invalid_tool_calls)
            out["first_ai_finish_reason"] = ai[0].response_metadata.get("finish_reason")
    elif FW == "smolagents":
        from smolagents import ToolCallingAgent, OpenAIServerModel, tool
        m = OpenAIServerModel(model_id="cut-model", api_base=BASE, api_key="dummy", client_kwargs={"max_retries": int(os.environ.get("RETRIES", "0"))})
        a = ToolCallingAgent(tools=[tool(write_file)], model=m, stream_outputs=(MODE == "stream"), max_steps=2, verbosity_level=0)
        out["final_output"] = str(a.run(PROMPT))[:200]
    else:
        raise SystemExit("unknown framework " + FW)
except Exception as e:
    out["exception"] = f"{type(e).__name__}: {str(e)[:300]}"
    out["trace_tail"] = traceback.format_exc().splitlines()[-4:]

calls = []
p = os.path.join(WORK, "calls.jsonl")
if os.path.exists(p):
    calls = [json.loads(l) for l in open(p)]
out["tool_executions"] = calls
if isinstance(out["final_output"], str):
    out["final_output"] = out["final_output"][:200]
print("\nRESULT " + json.dumps(out))
