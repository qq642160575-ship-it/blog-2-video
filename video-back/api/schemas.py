from typing import Any

from pydantic import BaseModel, Field, model_validator

from compiler.schemas import ScenePatch


class GenerateRequest(BaseModel):
    source_text: str | None = None
    oral_script: str | None = None
    thread_id: str | None = None

    @model_validator(mode="after")
    def ensure_input(self) -> "GenerateRequest":
        if not self.source_text and not self.oral_script:
            raise ValueError("Either source_text or oral_script must be provided")
        return self


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
    oral_script: str | None = None
    recompile_from: str = Field(default="layout")


class RecompileRequest(BaseModel):
    thread_id: str
    scene_id: str
    recompile_from: str = Field(default="layout")


class PatchRequest(BaseModel):
    thread_id: str
    scene_id: str
    patch: ScenePatch
