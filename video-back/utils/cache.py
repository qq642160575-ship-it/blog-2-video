import hashlib
import json
import os
from pathlib import Path
from typing import Any, Optional, Type

from fastapi.encoders import jsonable_encoder

from utils.logger import get_logger

CACHE_DIR = Path(".cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
logger = get_logger(__name__)


def get_prompt_version() -> str:
    return os.getenv("VIDEO_BACK_PROMPT_VERSION") or os.getenv("PROMPT_VERSION") or "v1"


def build_cache_key(*parts: str, prompt_version: str | None = None) -> str:
    normalized_parts = [prompt_version or get_prompt_version(), *parts]
    raw = "||".join(normalized_parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class SimpleCache:
    def __init__(self) -> None:
        self.cache_dir = CACHE_DIR

    def get(self, key: str, model_type: Optional[Type] = None) -> Any:
        cache_file = self.cache_dir / f"{key}.json"
        if not cache_file.exists():
            logger.debug("Cache miss for key=%s", key)
            return None
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            if model_type is not None and hasattr(model_type, "model_validate"):
                logger.debug("Cache hit for key=%s with model_type=%s", key, model_type.__name__)
                return model_type.model_validate(data)
            logger.debug("Cache hit for key=%s", key)
            return data
        except Exception:
            logger.exception("Failed to read cache key=%s path=%s", key, cache_file)
            return None

    def set(self, key: str, value: Any) -> Any:
        cache_file = self.cache_dir / f"{key}.json"
        try:
            if hasattr(value, "model_dump"):
                data = value.model_dump()
            else:
                data = jsonable_encoder(value)

            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.debug("Cache write success for key=%s path=%s", key, cache_file)
            return value
        except Exception:
            logger.exception("Failed to write cache key=%s path=%s", key, cache_file)
            return value

    def delete(self, key: str) -> bool:
        cache_file = self.cache_dir / f"{key}.json"
        try:
            if cache_file.exists():
                cache_file.unlink()
                logger.info("Cache deleted for key=%s path=%s", key, cache_file)
                return True
        except Exception:
            logger.exception("Failed to delete cache key=%s path=%s", key, cache_file)
        return False
