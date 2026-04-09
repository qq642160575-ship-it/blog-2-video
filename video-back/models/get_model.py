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

from langchain_anthropic import ChatAnthropic
from dotenv import load_dotenv
load_dotenv()

def get_model(name:str = 'cc'):
    llm = None
    if name == 'cc':
        llm = ChatAnthropic(
            model='claude-sonnet-4.5',
            temperature=0.3,
            base_url=os.getenv("ANTHROPIC_BASE_URL")
        )
    return llm