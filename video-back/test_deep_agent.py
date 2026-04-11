from langchain_anthropic import ChatAnthropic

import os
from dotenv import load_dotenv
load_dotenv()
api_key = 'weiwenhai'
base_url = 'http://94.183.184.225:3456'

import os
for k in [
    "ALL_PROXY",
    "all_proxy",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "http_proxy",
    "https_proxy",
]:
    os.environ.pop(k, None)
# System prompt to steer the agent to be an expert researcher
research_instructions = """You are an expert researcher. Your job is to conduct thorough research and then write a polished report.

You have access to an internet search tool as your primary means of gathering information.

## `internet_search`

Use this to run an internet search for a given query. You can specify the max number of results to return, the topic, and whether raw content should be included.
"""
llm = ChatAnthropic(
    model='claude-sonnet-4.5',
    temperature=0.3,
    base_url=base_url
)
a = llm.invoke("123")
print(a)
agent = create_deep_agent(
    model=llm,
    system_prompt=research_instructions,
)
