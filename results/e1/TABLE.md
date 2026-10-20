| cell (row/mode) | requests | per logical call | SDK-retry gaps (s) | gaps of retries above the SDK (s) | first→last request (s) | client wall (s) | tool runs | outcome |
|---|---|---|---|---|---|---|---|---|
| adk/429 | 3 | [3] | 1.02, 1 | – | 2.02 | 15.32 | 0 | litellm.exceptions.RateLimitError |
| adk/429-hard | 1 | [1] | – | – | 0.0 | 23.02 | 0 | litellm.exceptions.RateLimitError |
| adk/429-neutral-body | 3 | [3] | 1.01, 1.01 | – | 2.02 | 10.05 | 0 | litellm.exceptions.RateLimitError |
| adk/500-neutral | 3 | [3] | 0.46, 0.92 | – | 1.38 | 8.41 | 0 | litellm.exceptions.InternalServerError |
| adk/500-ratelimit-text | 3 | [3] | 0.51, 0.81 | – | 1.32 | 8.16 | 0 | litellm.exceptions.RateLimitError |
| adk/500-text-429 | 3 | [3] | 0.51, 0.8 | – | 1.32 | 7.75 | 0 | litellm.exceptions.InternalServerError |
| adk/after-tool-500 | 4 | [1, 3] | 0.51, 0.77 | – | 1.32 | 7.72 | 1 | litellm.exceptions.InternalServerError |
| adk/after-tool-drop | 4 | [1, 3] | 0.43, 0.9 | – | 1.39 | 8.22 | 1 | litellm.exceptions.InternalServerError |
| adk/drop | 3 | [3] | 0.48, 0.97 | – | 1.46 | 7.5 | 0 | litellm.exceptions.InternalServerError |
| adk/ok | 2 | [1, 1] | – | – | 0.06 | 11.28 | 1 | returned 'Done.' |
| adk/timeout | 3 | [3] | 600.5, 600.95 | – | 1201.44 | 1500.01 | 0 | CAPPED (killed at cap, still running) |
| adk-stream/after-tool-drop | 2 | [1, 1] | – | – | 0.2 | 6.42 | 1 | returned 'Do' |
| adk-stream/after-tool-drop-chunked | 2 | [1, 1] | – | – | 0.22 | 7.28 | 1 | litellm.exceptions.MidStreamFallbackError |
| adk-stream/drop | 1 | [1] | – | – | 0.0 | 7.33 | 0 | returned 'Do' |
| adk-stream/drop-chunked | 1 | [1] | – | – | 0.0 | 11.89 | 0 | litellm.exceptions.MidStreamFallbackError |
| adk-stream/ok | 2 | [1, 1] | – | – | 0.43 | 11.65 | 1 | returned 'Done.' |
| agents-chat/429 | 3 | [3] | 1.02, 1.01 | – | 2.03 | 14.51 | 0 | openai.RateLimitError |
| agents-chat/429-hard | 1 | [1] | – | – | 0.0 | 12.17 | 0 | openai.RateLimitError |
| agents-chat/429-neutral-body | 3 | [3] | 1.01, 1.01 | – | 2.01 | 9.2 | 0 | openai.RateLimitError |
| agents-chat/500-neutral | 3 | [3] | 0.41, 0.79 | – | 1.2 | 3.83 | 0 | openai.InternalServerError |
| agents-chat/500-ratelimit-text | 3 | [3] | 0.43, 0.78 | – | 1.21 | 3.58 | 0 | openai.InternalServerError |
| agents-chat/500-text-429 | 3 | [3] | 0.45, 0.82 | – | 1.27 | 3.22 | 0 | openai.InternalServerError |
| agents-chat/after-tool-500 | 4 | [1, 3] | 0.45, 0.79 | – | 1.25 | 3.15 | 1 | openai.InternalServerError |
| agents-chat/after-tool-drop | 4 | [1, 3] | 0.45, 0.96 | – | 1.43 | 3.55 | 1 | openai.APIConnectionError |
| agents-chat/drop | 3 | [3] | 0.43, 0.97 | – | 1.4 | 3.43 | 0 | openai.APIConnectionError |
| agents-chat/ok | 2 | [1, 1] | – | – | 0.04 | 8.2 | 1 | returned 'Done.' |
| agents-chat/timeout | 3 | [3] | 600.52, 600.95 | – | 1201.46 | 1500.0 | 0 | CAPPED (killed at cap, still running) |
| agents-chat-stream/after-tool-drop | 2 | [1, 1] | – | – | 0.25 | 2.6 | 1 | returned 'Do' |
| agents-chat-stream/after-tool-drop-chunked | 2 | [1, 1] | – | – | 0.44 | 4.44 | 1 | openai.APIConnectionError |
| agents-chat-stream/drop | 1 | [1] | – | – | 0.0 | 2.47 | 0 | returned 'Do' |
| agents-chat-stream/drop-chunked | 1 | [1] | – | – | 0.0 | 4.58 | 0 | openai.APIConnectionError |
| agents-chat-stream/ok | 2 | [1, 1] | – | – | 0.47 | 6.39 | 1 | returned 'Done.' |
| agents-responses/429 | 3 | [3] | 1.02, 1.01 | – | 2.03 | 15.34 | 0 | openai.RateLimitError |
| agents-responses/429-hard | 1 | [1] | – | – | 0.0 | 12.77 | 0 | openai.RateLimitError |
| agents-responses/429-neutral-body | 3 | [3] | 1.01, 1 | – | 2.01 | 8.62 | 0 | openai.RateLimitError |
| agents-responses/500-neutral | 3 | [3] | 0.4, 0.85 | – | 1.26 | 3.49 | 0 | openai.InternalServerError |
| agents-responses/500-ratelimit-text | 3 | [3] | 0.49, 0.76 | – | 1.26 | 3.67 | 0 | openai.InternalServerError |
| agents-responses/500-text-429 | 3 | [3] | 0.42, 0.89 | – | 1.3 | 3.57 | 0 | openai.InternalServerError |
| agents-responses/after-tool-500 | 4 | [1, 3] | 0.5, 0.77 | – | 1.36 | 3.53 | 1 | openai.InternalServerError |
| agents-responses/after-tool-drop | 4 | [1, 3] | 0.41, 0.99 | – | 1.48 | 3.72 | 1 | openai.APIConnectionError |
| agents-responses/drop | 3 | [3] | 0.46, 0.99 | – | 1.45 | 3.81 | 0 | openai.APIConnectionError |
| agents-responses/ok | 2 | [1, 1] | – | – | 0.27 | 8.58 | 1 | returned 'Done.' |
| agents-responses/timeout | 3 | [3] | 600.59, 601 | – | 1201.59 | 1500.01 | 0 | CAPPED (killed at cap, still running) |
| agents-responses-stream/after-tool-drop | 2 | [1, 1] | – | – | 0.46 | 3.11 | 1 | agents.exceptions.ModelBehaviorError |
| agents-responses-stream/after-tool-drop-chunked | 2 | [1, 1] | – | – | 1.05 | 5.56 | 1 | openai.APIConnectionError |
| agents-responses-stream/drop | 1 | [1] | – | – | 0.0 | 2.67 | 0 | agents.exceptions.ModelBehaviorError |
| agents-responses-stream/drop-chunked | 1 | [1] | – | – | 0.0 | 5.41 | 0 | openai.APIConnectionError |
| agents-responses-stream/ok | 2 | [1, 1] | – | – | 0.57 | 7.06 | 1 | returned 'Done.' |
| crewai/429 | 27 | [27] | 1.01, 1.01, 1, 1.01, 1, 1, 1.05, 1, 1, 1, 1, 1, 1.06, 1, 1, 1, 1, 1 | 1.22, 1.92, 0.02, 1.18, 1.86, 0.03, 1.11, 1.82 | 27.32 | 38.52 | 0 | openai.RateLimitError |
| crewai/429-hard | 9 | [9] | – | 1.26, 1.69, 0.08, 1.04, 1.76, 0.03, 1.04, 2.39 | 9.29 | 27.03 | 0 | openai.RateLimitError |
| crewai/429-neutral-body | 27 | [27] | 1, 1.01, 1.01, 1, 1, 1.01, 1.05, 1, 1.01, 1, 1, 1.01, 1.05, 1, 1, 1.01, 1, 1 | 1.15, 2.37, 0.02, 1.14, 1.89, 0.02, 1, 2.04 | 27.79 | 32.39 | 0 | openai.RateLimitError |
| crewai/500-neutral | 9 | [9] | 0.46, 0.97, 0.49, 0.77, 0.52, 0.91 | 0.06, 0.01 | 4.18 | 8.73 | 0 | openai.InternalServerError |
| crewai/500-ratelimit-text | 27 | [27] | 0.39, 0.78, 0.49, 0.94, 0.41, 0.77, 0.5, 0.86, 0.4, 0.94, 0.38, 0.87, 0.49, 0.95, 0.45, 0.99, 0.39, 0.98 | 1.02, 2.19, 0.04, 1.13, 2.38, 0.01, 0.81, 1.96 | 21.53 | 25.49 | 0 | openai.InternalServerError |
| crewai/500-text-429 | 9 | [9] | 0.49, 0.94, 0.45, 0.83, 0.52, 0.83 | 0.03, 0.01 | 4.1 | 8.03 | 0 | openai.InternalServerError |
| crewai/after-tool-500 | 12 | [3, 3, 3, 3] | 0.42, 0.95, 0.43, 0.92, 0.5, 0.99 | 0.02, 0.01 | 4.36 | 8.24 | 3 | openai.InternalServerError |
| crewai/after-tool-drop | 12 | [3, 3, 3, 3] | 0.42, 1, 0.5, 0.79, 0.5, 0.86 | 0.02, 0.02 | 4.13 | 8.26 | 3 | builtins.ConnectionError |
| crewai/drop | 9 | [9] | 0.43, 0.82, 0.48, 0.98, 0.39, 0.88 | 0.03, 0.02 | 4.03 | 7.66 | 0 | builtins.ConnectionError |
| crewai/ok | 2 | [1, 1] | – | – | 0.02 | 13.24 | 1 | returned 'Done.' |
| crewai/timeout | 3 | [3] | 600.52, 601.02 | – | 1201.54 | 1500.01 | 0 | CAPPED (killed at cap, still running) |
| crewai-stream/after-tool-drop | 2 | [1, 1] | – | – | 0.02 | 3.73 | 1 | returned 'Do' |
| crewai-stream/after-tool-drop-chunked | 6 | [3, 1, 1, 1] | – | 0.01, 0.01 | 0.06 | 4.97 | 3 | httpx.RemoteProtocolError |
| crewai-stream/drop | 1 | [1] | – | – | 0.0 | 4.33 | 0 | returned 'Do' |
| crewai-stream/drop-chunked | 3 | [3] | – | 0.07, 0.03 | 0.1 | 7.36 | 0 | httpx.RemoteProtocolError |
| crewai-stream/ok | 2 | [1, 1] | – | – | 0.03 | 8.7 | 1 | returned 'Done.' |
| langgraph/429 | 3 | [3] | 1.02, 1.01 | – | 2.03 | 12.26 | 0 | langchain_openai.chat_models.base.OpenAIRateLimitError |
| langgraph/429-hard | 1 | [1] | – | – | 0.0 | 11.01 | 0 | langchain_openai.chat_models.base.OpenAIRateLimitError |
| langgraph/429-neutral-body | 3 | [3] | 1.01, 1 | – | 2.01 | 7.22 | 0 | langchain_openai.chat_models.base.OpenAIRateLimitError |
| langgraph/500-neutral | 3 | [3] | 0.47, 0.8 | – | 1.27 | 3.18 | 0 | langchain_openai.chat_models.base.OpenAIAPIError |
| langgraph/500-ratelimit-text | 3 | [3] | 0.49, 0.82 | – | 1.31 | 3.16 | 0 | langchain_openai.chat_models.base.OpenAIAPIError |
| langgraph/500-text-429 | 3 | [3] | 0.46, 0.89 | – | 1.35 | 2.93 | 0 | langchain_openai.chat_models.base.OpenAIAPIError |
| langgraph/after-tool-500 | 4 | [1, 3] | 0.51, 0.88 | – | 1.41 | 3.18 | 1 | langchain_openai.chat_models.base.OpenAIAPIError |
| langgraph/after-tool-drop | 4 | [1, 3] | 0.45, 1 | – | 1.47 | 3.28 | 1 | langchain_openai.chat_models.base.OpenAIConnectionError |
| langgraph/drop | 3 | [3] | 0.4, 1 | – | 1.41 | 2.98 | 0 | langchain_openai.chat_models.base.OpenAIConnectionError |
| langgraph/ok | 2 | [1, 1] | – | – | 0.03 | 8.78 | 1 | returned 'Done.' |
| langgraph/timeout | 1 | [1] | – | – | 0.0 | 1500.01 | 0 | CAPPED (killed at cap, still running) |
| langgraph-stream/after-tool-drop | 2 | [1, 1] | – | – | 0.01 | 1.95 | 1 | returned 'Do' |
| langgraph-stream/after-tool-drop-chunked | 2 | [1, 1] | – | – | 0.04 | 3.2 | 1 | langchain_openai.chat_models.base.OpenAIConnectionError |
| langgraph-stream/drop | 1 | [1] | – | – | 0.0 | 1.68 | 0 | returned 'Do' |
| langgraph-stream/drop-chunked | 1 | [1] | – | – | 0.0 | 3.59 | 0 | langchain_openai.chat_models.base.OpenAIConnectionError |
| langgraph-stream/ok | 2 | [1, 1] | – | – | 0.06 | 5.22 | 1 | returned 'Done.' |
| pydantic-ai/429 | 3 | [3] | 1.01, 1.01 | – | 2.02 | 8.32 | 0 | pydantic_ai.exceptions.ModelHTTPError |
| pydantic-ai/429-hard | 1 | [1] | – | – | 0.0 | 10.98 | 0 | pydantic_ai.exceptions.ModelHTTPError |
| pydantic-ai/429-neutral-body | 3 | [3] | 1.01, 1.01 | – | 2.02 | 3.89 | 0 | pydantic_ai.exceptions.ModelHTTPError |
| pydantic-ai/500-neutral | 3 | [3] | 0.48, 0.85 | – | 1.33 | 3.5 | 0 | pydantic_ai.exceptions.ModelHTTPError |
| pydantic-ai/500-ratelimit-text | 3 | [3] | 0.45, 0.76 | – | 1.21 | 2.87 | 0 | pydantic_ai.exceptions.ModelHTTPError |
| pydantic-ai/500-text-429 | 3 | [3] | 0.46, 0.98 | – | 1.43 | 3.26 | 0 | pydantic_ai.exceptions.ModelHTTPError |
| pydantic-ai/after-tool-500 | 4 | [1, 3] | 0.54, 0.85 | – | 1.41 | 2.97 | 1 | pydantic_ai.exceptions.ModelHTTPError |
| pydantic-ai/after-tool-drop | 4 | [1, 3] | 0.46, 0.97 | – | 1.46 | 3.31 | 1 | pydantic_ai.exceptions.ModelAPIError |
| pydantic-ai/drop | 3 | [3] | 0.44, 1 | – | 1.44 | 3.15 | 0 | pydantic_ai.exceptions.ModelAPIError |
| pydantic-ai/ok | 2 | [1, 1] | – | – | 0.02 | 9.56 | 1 | returned 'Done.' |
| pydantic-ai/timeout | 3 | [3] | 600.56, 600.86 | – | 1201.42 | 1500.01 | 0 | CAPPED (killed at cap, still running) |
| pydantic-ai-stream/after-tool-drop | 2 | [1, 1] | – | – | 0.02 | 1.58 | 1 | returned 'Do' |
| pydantic-ai-stream/after-tool-drop-chunked | 2 | [1, 1] | – | – | 0.03 | 2.31 | 1 | pydantic_ai.exceptions.ModelAPIError |
| pydantic-ai-stream/drop | 1 | [1] | – | – | 0.0 | 1.64 | 0 | returned 'Do' |
| pydantic-ai-stream/drop-chunked | 1 | [1] | – | – | 0.0 | 3.59 | 0 | pydantic_ai.exceptions.ModelAPIError |
| pydantic-ai-stream/ok | 2 | [1, 1] | – | – | 0.07 | 5.01 | 1 | returned 'Done.' |
| smol-litellm/429 | 9 | [9] | 1, 1.01, 1, 1, 1, 1 | 201.78, 652.65 | 860.45 | 872.11 | 0 | smolagents.utils.AgentGenerationError |
| smol-litellm/429-hard | 1 | [1] | – | – | 0.0 | 21.81 | 0 | smolagents.utils.AgentGenerationError |
| smol-litellm/429-neutral-body | 3 | [3] | 1, 1.02 | – | 2.03 | 8.11 | 0 | smolagents.utils.AgentGenerationError |
| smol-litellm/500-neutral | 3 | [3] | 0.38, 0.92 | – | 1.3 | 6.69 | 0 | smolagents.utils.AgentGenerationError |
| smol-litellm/500-ratelimit-text | 9 | [9] | 0.48, 0.9, 0.39, 0.89, 0.43, 0.95 | 232.22, 703.93 | 940.18 | 945.49 | 0 | smolagents.utils.AgentGenerationError |
| smol-litellm/500-text-429 | 9 | [9] | 0.48, 0.88, 0.42, 0.76, 0.42, 0.8 | 141.56, 349.44 | 494.74 | 499.51 | 0 | smolagents.utils.AgentGenerationError |
| smol-litellm/after-tool-500 | 4 | [1, 3] | 0.46, 1 | – | 1.5 | 6.43 | 1 | smolagents.utils.AgentGenerationError |
| smol-litellm/after-tool-drop | 4 | [1, 3] | 0.4, 0.88 | – | 1.32 | 6.73 | 1 | smolagents.utils.AgentGenerationError |
| smol-litellm/drop | 3 | [3] | 0.5, 0.97 | – | 1.47 | 6.39 | 0 | smolagents.utils.AgentGenerationError |
| smol-litellm/ok | 2 | [1, 1] | – | – | 0.04 | 10.27 | 1 | returned 'Done.' |
| smol-litellm/timeout | 3 | [3] | 600.53, 601.05 | – | 1201.58 | 1500.0 | 0 | CAPPED (killed at cap, still running) |
| smol-litellm-stream/after-tool-drop | 23 | [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3] | 0.43, 0.77 | – | 1.93 | 6.9 | 1 | returned "[{'type': 'text', 'text': 'Error in generating fin |
| smol-litellm-stream/after-tool-drop-chunked | 2 | [1, 1] | – | – | 0.22 | 7.53 | 1 | smolagents.utils.AgentGenerationError |
| smol-litellm-stream/drop | 23 | [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3] | 0.45, 0.8 | – | 2.13 | 8.07 | 0 | returned "[{'type': 'text', 'text': 'Error in generating fin |
| smol-litellm-stream/drop-chunked | 1 | [1] | – | – | 0.0 | 10.81 | 0 | smolagents.utils.AgentGenerationError |
| smol-litellm-stream/ok | 2 | [1, 1] | – | – | 0.29 | 10.38 | 1 | returned 'Done.' |
| smol-openai/429 | 9 | [9] | 1.01, 1.01, 1, 1, 1, 1 | 147.85, 514.58 | 668.47 | 679.64 | 0 | smolagents.utils.AgentGenerationError |
| smol-openai/429-hard | 3 | [3] | – | 176.76, 402.71 | 579.47 | 590.78 | 0 | smolagents.utils.AgentGenerationError |
| smol-openai/429-neutral-body | 9 | [9] | 1.01, 1.01, 1, 1, 1, 1 | 226.84, 831 | 1063.86 | 1066.07 | 0 | smolagents.utils.AgentGenerationError |
| smol-openai/500-neutral | 3 | [3] | 0.46, 0.78 | – | 1.24 | 3.32 | 0 | smolagents.utils.AgentGenerationError |
| smol-openai/500-ratelimit-text | 9 | [9] | 0.46, 0.82, 0.48, 0.91, 0.39, 0.83 | 231.79, 468.21 | 703.89 | 705.94 | 0 | smolagents.utils.AgentGenerationError |
| smol-openai/500-text-429 | 9 | [9] | 0.46, 0.82, 0.45, 0.97, 0.48, 0.82 | 175.5, 439.6 | 619.11 | 621.08 | 0 | smolagents.utils.AgentGenerationError |
| smol-openai/after-tool-500 | 4 | [1, 3] | 0.43, 0.99 | – | 1.43 | 3.54 | 1 | smolagents.utils.AgentGenerationError |
| smol-openai/after-tool-drop | 4 | [1, 3] | 0.46, 0.85 | – | 1.32 | 3.37 | 1 | smolagents.utils.AgentGenerationError |
| smol-openai/drop | 3 | [3] | 0.44, 0.8 | – | 1.24 | 3.09 | 0 | smolagents.utils.AgentGenerationError |
| smol-openai/ok | 2 | [1, 1] | – | – | 0.03 | 5.38 | 1 | returned 'Done.' |
| smol-openai/timeout | 3 | [3] | 600.46, 600.83 | – | 1201.29 | 1500.01 | 0 | CAPPED (killed at cap, still running) |
| smol-openai-mr0/429 | 3 | [3] | – | 232.15, 860.8 | 1092.95 | 1095.31 | 0 | smolagents.utils.AgentGenerationError |
| smol-openai-mr0/500-neutral | 1 | [1] | – | – | 0.0 | 2.52 | 0 | smolagents.utils.AgentGenerationError |
| smol-openai-mr0/after-tool-500 | 2 | [1, 1] | – | – | 0.01 | 2.72 | 1 | smolagents.utils.AgentGenerationError |
| smol-openai-mr0/drop | 1 | [1] | – | – | 0.0 | 2.36 | 0 | smolagents.utils.AgentGenerationError |
| smol-openai-mr0/timeout | 1 | [1] | – | – | 0.0 | 602.51 | 0 | smolagents.utils.AgentGenerationError |
| smol-openai-stream/after-tool-drop | 23 | [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3] | 0.48, 0.95 | – | 1.73 | 3.61 | 1 | returned "[{'type': 'text', 'text': 'Error in generating fin |
| smol-openai-stream/after-tool-drop-chunked | 2 | [1, 1] | – | – | 0.03 | 3.73 | 1 | smolagents.utils.AgentGenerationError |
| smol-openai-stream/drop | 23 | [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3] | 0.42, 0.85 | – | 1.55 | 3.77 | 0 | returned "[{'type': 'text', 'text': 'Error in generating fin |
| smol-openai-stream/drop-chunked | 1 | [1] | – | – | 0.0 | 4.4 | 0 | smolagents.utils.AgentGenerationError |
| smol-openai-stream/ok | 2 | [1, 1] | – | – | 0.06 | 5.55 | 1 | returned 'Done.' |
