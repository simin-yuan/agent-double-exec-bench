import sys, time
from smolagents import OpenAIModel
model = OpenAIModel(model_id="any", api_base=f"http://127.0.0.1:{sys.argv[1]}/v1", api_key="dummy")
t = time.time()
try:
    print(model.generate([{"role": "user", "content": [{"type": "text", "text": "hi"}]}]).content)
except Exception as e:
    print("raised", type(e).__name__)
print("elapsed_s", round(time.time() - t, 1))
