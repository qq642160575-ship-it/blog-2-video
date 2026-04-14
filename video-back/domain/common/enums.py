from __future__ import annotations

from enum import Enum


class SessionStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    ERROR = "error"


class TaskStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"
    BLOCKED = "blocked"


class TaskType(str, Enum):
    CREATE_VIDEO = "create_video"
    REGENERATE_SCENE = "regenerate_scene"
    REPAIR_SCENE = "repair_scene"
    RENDER_PREVIEW = "render_preview"


class ArtifactType(str, Enum):
    SOURCE_DOCUMENT = "source_document"
    SCRIPT = "script"
    STORYBOARD = "storyboard"
    VISUAL_STRATEGY = "visual_strategy"
    SCENE_INTENT_BUNDLE = "scene_intent_bundle"
    SCENE_LAYOUT_BUNDLE = "scene_layout_bundle"
    SCENE_CODE_BUNDLE = "scene_code_bundle"
    VALIDATION_REPORT = "validation_report"
    REPAIR_REPORT = "repair_report"
    PREVIEW_IMAGE = "preview_image"
