import sys,time,smolagents.models as M
from smolagents import ToolCallingAgent, OpenAIServerModel
M.RETRY_WAIT=2  # shrink smolagents' fixed 60s base wait so the test finishes; count is unaffected
m=OpenAIServerModel(model_id="x",api_base=f"http://127.0.0.1:{sys.argv[1]}/v1",api_key="d")
print("openai client max_retries =",m.client.max_retries)
t=time.time()
try: m.generate([{"role":"user","content":[{"type":"text","text":"hi"}]}])
except Exception as e: print("raised:",type(e).__name__, str(e)[:80])
print("elapsed",round(time.time()-t,1))
