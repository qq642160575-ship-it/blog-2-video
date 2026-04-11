import os
from typing import Dict

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic

load_dotenv()

DEFAULT_MODEL = "claude-sonnet-4.5"

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
        )

    return _MODEL_CACHE[role]
