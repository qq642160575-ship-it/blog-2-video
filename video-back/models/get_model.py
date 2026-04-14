import os
from pathlib import Path
from typing import Dict
from langchain_anthropic import ChatAnthropic

import os
from dotenv import load_dotenv
load_dotenv()

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
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic

load_dotenv(dotenv_path=Path(__file__).resolve().parents[1] / ".env", override=True)

DEFAULT_MODEL = "deepseek-chat"

MODEL_MAP = {
    "writer": DEFAULT_MODEL,
    "reviewer": DEFAULT_MODEL,
    "director": DEFAULT_MODEL,
    "visual_architect": DEFAULT_MODEL,
    "coder": DEFAULT_MODEL,
    "qa": DEFAULT_MODEL,
}

_MODEL_CACHE: Dict[str, ChatAnthropic] = {}


def get_model(role: str = "writer") -> ChatAnthropic:
    if role not in MODEL_MAP:
        supported_roles = ", ".join(sorted(MODEL_MAP))
        raise ValueError(f"Unsupported model role: {role}. Supported roles: {supported_roles}")

    if role not in _MODEL_CACHE:
        _MODEL_CACHE[role] = ChatAnthropic(
            model=MODEL_MAP[role],
            temperature=0.3,
            max_tokens=81920,
            base_url=os.getenv("ANTHROPIC_BASE_URL"),
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            default_headers={
                "Authorization": f"Bearer {os.getenv("ANTHROPIC_API_KEY")}",
            }
        )

    return _MODEL_CACHE[role]
