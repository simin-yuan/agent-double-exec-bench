import sys,time,asyncio
fw,port=sys.argv[1],sys.argv[2]; base=f"http://127.0.0.1:{port}/v1"
t=time.time()
try:
    if fw=="agents":
        from openai import AsyncOpenAI
        from agents import Agent,Runner,OpenAIChatCompletionsModel,set_tracing_disabled
        set_tracing_disabled(True)
        a=Agent(name="a",model=OpenAIChatCompletionsModel("x",AsyncOpenAI(base_url=base,api_key="d")))
        asyncio.run(Runner.run(a,"hi"))
    elif fw=="langgraph":
        from langchain_openai import ChatOpenAI
        from langgraph.prebuilt import create_react_agent
        create_react_agent(ChatOpenAI(model="x",base_url=base,api_key="d"),tools=[]).invoke({"messages":[("user","hi")]})
except Exception as e: print("raised",type(e).__name__)
print("elapsed",round(time.time()-t,1))
