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
_FALLBACK_REASON: str | None = None
_PROXY_KEYS = (
    "ALL_PROXY",
    "all_proxy",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "http_proxy",
    "https_proxy",
)


class FallbackModel:
    is_fallback_model = True

    def __init__(self, role: str, reason: str | None = None) -> None:
        self.role = role
        self.reason = reason or "Model backend unavailable"

    def invoke(self, messages):
        raise RuntimeError(f"Fallback model active for role={self.role}: {self.reason}")

    def with_structured_output(self, schema, method=None):
        return self


def _clear_proxy_env() -> None:
    for key in _PROXY_KEYS:
        os.environ.pop(key, None)


def _detect_fallback_reason() -> str | None:
    if ChatAnthropic is None:
        return "langchain-anthropic is not installed"

    return None


def get_model(role: str = "writer"):
    if role not in MODEL_MAP:
        supported_roles = ", ".join(sorted(MODEL_MAP))
        raise ValueError(f"Unsupported model role: {role}. Supported roles: {supported_roles}")

    if role not in _MODEL_CACHE:
        reason = _detect_fallback_reason()
        if reason is not None:
            global _FALLBACK_REASON
            if _FALLBACK_REASON != reason:
                _FALLBACK_REASON = reason
            _MODEL_CACHE[role] = FallbackModel(role, reason=reason)
        else:
            _clear_proxy_env()
            _MODEL_CACHE[role] = ChatAnthropic(
                model=MODEL_MAP[role],
                temperature=0.3,
                max_tokens=81920,
                base_url=os.getenv("ANTHROPIC_BASE_URL"),
                api_key=os.getenv("ANTHROPIC_API_KEY"),
            )

    return _MODEL_CACHE[role]
