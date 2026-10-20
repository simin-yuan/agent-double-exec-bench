"""Minimal repro: one CrewAI agent, one counter tool, a fake model server whose replies after the tool call fail.

usage: python repro/crewai_tool_reexec.py [MODE] [MAX_RETRY_LIMIT]
  MODE             fault_server.py mode (default after-tool-500: every request carrying the tool result gets HTTP 500)
  MAX_RETRY_LIMIT  passed to crewai.Agent(max_retry_limit=...); omitted = CrewAI's default

Needs: crewai (tested 1.15.28) in the running interpreter; harness/fault_server.py from this repository.
Nothing leaves the machine: the model is the local fake server, the key is a dummy.

Prints the counter (tool executions), the number of model requests the server received, and for every tool
execution the CrewAI functions on the call stack, so the code path that re-runs the tool is visible."""
import json, os, socket, subprocess, sys, tempfile, time, traceback

MODE = sys.argv[1] if len(sys.argv) > 1 else "after-tool-500"
LIMIT = int(sys.argv[2]) if len(sys.argv) > 2 else None
HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.join(HERE, "..", "harness", "fault_server.py")

s = socket.socket(); s.bind(("127.0.0.1", 0)); PORT = s.getsockname()[1]; s.close()
tmp = tempfile.mkdtemp()
LOG = os.path.join(tmp, "server.jsonl")
srv = subprocess.Popen([sys.executable, SERVER, str(PORT), MODE, LOG])
time.sleep(0.5)
BASE = f"http://127.0.0.1:{PORT}/v1"
os.environ.update({"OPENAI_API_KEY": "sk-fake-local-only", "OPENAI_BASE_URL": BASE,
                   "CREWAI_DISABLE_TELEMETRY": "true", "OTEL_SDK_DISABLED": "true", "CREWAI_TRACING_ENABLED": "false"})

from crewai import Agent, Crew, LLM, Task  # noqa: E402
from crewai.tools import tool  # noqa: E402
from crewai.experimental.agent_executor import AgentExecutor  # noqa: E402

# Pass-through wrappers that only count calls, so the restart path is observed at runtime, not inferred.
calls = {"Agent.execute_task": 0, "Agent._handle_execution_error": 0, "AgentExecutor.invoke": 0}


def counted(cls, name, key):
    orig = getattr(cls, name)

    def wrapper(*a, **k):
        calls[key] += 1
        return orig(*a, **k)
    setattr(cls, name, wrapper)


counted(Agent, "execute_task", "Agent.execute_task")
counted(Agent, "_handle_execution_error", "Agent._handle_execution_error")
counted(AgentExecutor, "invoke", "AgentExecutor.invoke")

executions = []


@tool("counter")
def counter() -> str:
    """Increment the counter. Call this once."""
    executions.append([f"{f.filename.split('site-packages/')[-1]}:{f.lineno} {f.name}"
                       for f in traceback.extract_stack() if "/crewai/" in f.filename])
    return f"COUNTER_OK n={len(executions)}"


kw = {} if LIMIT is None else {"max_retry_limit": LIMIT}
agent = Agent(role="counter user", goal="call the counter tool once", backstory="tester", tools=[counter],
              llm=LLM(model="openai/fake-model", base_url=BASE, api_key="sk-fake-local-only"), **kw)
task = Task(description="Call the counter tool exactly once, then answer Done.", expected_output="Done.", agent=agent)
try:
    out = f"returned {str(Crew(agents=[agent], tasks=[task]).kickoff())!r}"
except Exception as e:  # noqa: BLE001
    out = f"raised {type(e).__module__}.{type(e).__name__}"
finally:
    srv.terminate(); srv.wait()

reqs = [json.loads(l) for l in open(LOG) if '"action"' in l]
print(json.dumps({"crewai_mode": MODE, "max_retry_limit": agent.max_retry_limit, "outcome": out,
                  "counter": len(executions), "model_requests": len(reqs),
                  "requests_without_tool_result": sum(not r["has_tool_result"] for r in reqs),
                  "calls": calls, "executor_class": agent.executor_class.__module__ + "." + agent.executor_class.__name__,
                  "stack_per_execution": executions}))
