import os
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv

try:
    from langchain_anthropic import ChatAnthropic
except ImportError:  # pragma: no cover - environment fallback
    ChatAnthropic = None  # type: ignore[assignment]

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

_MODEL_CACHE: Dict[str, object] = {}


class FallbackModel:
    def __init__(self, role: str) -> None:
        self.role = role

    def invoke(self, messages):
        raise RuntimeError(
            f"Model dependency unavailable for role={self.role}. Install langchain-anthropic to enable LLM calls."
        )

    def with_structured_output(self, schema, method=None):
        return self


def get_model(role: str = "writer"):
    if role not in MODEL_MAP:
        supported_roles = ", ".join(sorted(MODEL_MAP))
        raise ValueError(f"Unsupported model role: {role}. Supported roles: {supported_roles}")

    if role not in _MODEL_CACHE:
        if ChatAnthropic is None:
            _MODEL_CACHE[role] = FallbackModel(role)
        else:
            _MODEL_CACHE[role] = ChatAnthropic(
                model=MODEL_MAP[role],
                temperature=0.3,
                max_tokens=81920,
                base_url=os.getenv("ANTHROPIC_BASE_URL"),
                api_key=os.getenv("ANTHROPIC_API_KEY"),
            )

    return _MODEL_CACHE[role]
