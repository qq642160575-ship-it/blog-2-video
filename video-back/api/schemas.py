from typing import Any

from pydantic import BaseModel


class GenerateRequest(BaseModel):
    source_text: str
    thread_id: str | None = None


class ReplayRequest(BaseModel):
    thread_id: str
    checkpoint_id: str


class ForkRequest(BaseModel):
    thread_id: str
    checkpoint_id: str
    values: dict[str, Any] | None = None
    as_node: str | None = None


class RegenerateSceneRequest(BaseModel):
    thread_id: str
    scene_id: str
    script: str
    visual_design: str
