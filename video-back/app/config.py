from __future__ import annotations

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./dev.db"
    redis_url: str | None = None
    object_storage_root: str = ".cache/artifacts"
    queue_backend: str = "inline"
    enable_workflow_compat: bool = True
    prompt_version: str = "v1"
    canvas_width: int = 1080
    canvas_height: int = 1920
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


_settings: Settings | None = None
