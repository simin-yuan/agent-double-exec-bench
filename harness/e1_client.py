"""Run one agent framework, in its default configuration, against fault_server.py (E1).

usage: python e1_client.py FRAMEWORK PORT WORKDIR [stream]
FRAMEWORK: agents-chat | agents-responses | langgraph | smol-openai | smol-openai-mr0 | smol-litellm | crewai | pydantic-ai | adk | hermes
(hermes: needs the Hermes Agent checkout on PYTHONPATH; the counter tool is registered in its tool registry.
 This branch was written but NOT run in E1 — see REPORT.md.)

Only what is needed to reach the fake server is set: base URL, a dummy key, the model name, and switching off
anything that would phone home (tracing / telemetry / cost-map download). Retry, timeout and step settings are
the framework's defaults. The single tool is `counter`: every execution appends one line to WORKDIR/counter.txt,
so the tool execution count is read from that side effect, not from the framework."""
import json, os, sys, time, traceback

FW, PORT, WORK = sys.argv[1], sys.argv[2], sys.argv[3]
STREAM = len(sys.argv) > 4 and sys.argv[4] == "stream"
BASE = f"http://127.0.0.1:{PORT}/v1"
KEY = "sk-fake-local-only"
PROMPT = "Call the counter tool exactly once, then answer Done."
os.makedirs(WORK, exist_ok=True)
CFILE = os.path.join(WORK, "counter.txt")
os.environ.update({"OPENAI_API_KEY": KEY, "OPENAI_BASE_URL": BASE, "OPENAI_API_BASE": BASE,
                   "LITELLM_LOCAL_MODEL_COST_MAP": "True", "CREWAI_DISABLE_TELEMETRY": "true",
                   "OTEL_SDK_DISABLED": "true", "CREWAI_TRACING_ENABLED": "false"})
T0 = time.time()


def counter() -> str:
    """Increment the counter. Call this once.
    """
    with open(CFILE, "a") as f:
        f.write(f"{time.time() - T0:.3f}\n")
    n = sum(1 for _ in open(CFILE))
    return f"COUNTER_OK n={n}"


def run():
    if FW.startswith("agents"):
        import asyncio
        from agents import Agent, Runner, function_tool, set_default_openai_api, set_tracing_disabled
        set_tracing_disabled(True)
        set_default_openai_api("chat_completions" if FW == "agents-chat" else "responses")
        agent = Agent(name="a", instructions="Use the tool.", model="fake-model", tools=[function_tool(counter)])

        async def go():
            if STREAM:
                r = Runner.run_streamed(agent, PROMPT)
                async for _ in r.stream_events():
                    pass
                return r.final_output
            return (await Runner.run(agent, PROMPT)).final_output
        return asyncio.run(go())
    if FW == "langgraph":
        from langchain_openai import ChatOpenAI
        from langchain_core.tools import tool
        from langgraph.prebuilt import create_react_agent
        llm = ChatOpenAI(model="fake-model", base_url=BASE, api_key=KEY, streaming=STREAM)
        res = create_react_agent(llm, tools=[tool(counter)]).invoke({"messages": [("user", PROMPT)]})
        return res["messages"][-1].content
    if FW.startswith("smol"):
        from smolagents import ToolCallingAgent, OpenAIServerModel, LiteLLMModel, tool
        if FW == "smol-openai":
            m = OpenAIServerModel(model_id="fake-model", api_base=BASE, api_key=KEY)
        elif FW == "smol-openai-mr0":
            # NOT default: the client state the TASKS.md E3 fix would create (inner SDK retries off, outer retry on)
            m = OpenAIServerModel(model_id="fake-model", api_base=BASE, api_key=KEY, client_kwargs={"max_retries": 0})
        else:
            m = LiteLLMModel(model_id="openai/fake-model", api_base=BASE, api_key=KEY)
        return ToolCallingAgent(tools=[tool(counter)], model=m, stream_outputs=STREAM).run(PROMPT)
    if FW == "crewai":
        from crewai import Agent, Crew, LLM, Task
        from crewai.tools import tool
        t = tool("counter")(counter)
        llm = LLM(model="openai/fake-model", base_url=BASE, api_key=KEY, stream=STREAM)
        a = Agent(role="counter user", goal="call the counter tool once", backstory="tester", tools=[t], llm=llm)
        task = Task(description=PROMPT, expected_output="Done.", agent=a)
        return str(Crew(agents=[a], tasks=[task]).kickoff())
    if FW == "pydantic-ai":
        from pydantic_ai import Agent
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider
        agent = Agent(OpenAIChatModel("fake-model", provider=OpenAIProvider(base_url=BASE, api_key=KEY)))
        agent.tool_plain(counter)
        if STREAM:
            import asyncio

            async def go():
                async with agent.run_stream(PROMPT) as r:
                    return await r.get_output()
            return asyncio.run(go())
        return agent.run_sync(PROMPT).output
    if FW == "adk":
        import asyncio
        from google.adk.agents import LlmAgent
        from google.adk.models.lite_llm import LiteLlm
        from google.adk.runners import Runner
        from google.adk.sessions import InMemorySessionService
        from google.adk.agents.run_config import RunConfig, StreamingMode
        from google.genai import types
        agent = LlmAgent(name="a", model=LiteLlm(model="openai/fake-model", api_base=BASE, api_key=KEY),
                         instruction="Use the tool.", tools=[counter])
        ss = InMemorySessionService()

        async def go():
            s = await ss.create_session(app_name="e1", user_id="u")
            r = Runner(agent=agent, app_name="e1", session_service=ss)
            last = None
            rc = RunConfig(streaming_mode=StreamingMode.SSE) if STREAM else RunConfig()
            async for ev in r.run_async(user_id="u", session_id=s.id, run_config=rc,
                                        new_message=types.Content(role="user", parts=[types.Part(text=PROMPT)])):
                if ev.content and ev.content.parts and ev.content.parts[0].text:
                    last = ev.content.parts[0].text
                if getattr(ev, "error_code", None):
                    last = f"error_event {ev.error_code}: {ev.error_message}"
            return last
        return asyncio.run(go())
    if FW == "hermes":
        os.environ["HERMES_HOME"] = os.path.join(WORK, ".hermes")  # keep config/state inside the cell
        from tools.registry import registry
        from run_agent import AIAgent
        registry.register(name="counter", toolset="counter", handler=lambda args, **kw: counter(),
                          schema={"name": "counter", "description": "Increment the counter. Call this once.",
                                  "parameters": {"type": "object", "properties": {}}})
        agent = AIAgent(base_url=BASE, model="fake-model", api_key=KEY, enabled_toolsets=["counter"])
        r = agent.run_conversation(PROMPT)
        return f"completed={r.get('completed')} api_calls={r.get('api_calls')} final={r.get('final_response')!r}"
    raise SystemExit("unknown framework " + FW)


out = {"framework": FW, "stream": STREAM, "exception": None, "final_output": None}
try:
    out["final_output"] = str(run())[:300]
except BaseException as e:  # noqa: BLE001 — record whatever ends the run
    out["exception"] = f"{type(e).__module__}.{type(e).__name__}: {str(e)[:400]}"
    out["trace_tail"] = traceback.format_exc().splitlines()[-6:]
out["elapsed_s"] = round(time.time() - T0, 2)
out["tool_executions"] = sum(1 for _ in open(CFILE)) if os.path.exists(CFILE) else 0
print("\nRESULT " + json.dumps(out), flush=True)
