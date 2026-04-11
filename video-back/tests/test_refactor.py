import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

import agents.coder as coder_module
import agents.qa_guard as qa_module
import main as app_main
from agents.content_reviewer import content_reviewer_agent
from agents.content_writer import content_writer_agent
from agents.director import Scene
from agents.visual_architect import LayoutBlueprintItem, ThemePalette, VisualProtocol
from models.get_model import get_model
from prompts.manager import PromptManager
from utils.cache import SimpleCache
from workflow import animation_work_flow as animation_module
from workflow import conversational_tone_work_flow as conversational_module
from workflow.animation_work_flow import CoderTaskState


def parse_sse_payloads(raw_text: str) -> list[dict]:
    payloads = []
    for block in raw_text.strip().split("\n\n"):
        if block.startswith("data: "):
            payloads.append(json.loads(block[6:]))
    return payloads


class AsyncWorkflowSuccess:
    async def astream(self, initial_state, stream_mode="updates", version="v2"):
        yield {"content_writer": {"current_script": "demo"}}


class AsyncWorkflowError:
    async def astream(self, initial_state, stream_mode="updates", version="v2"):
        raise RuntimeError("boom")
        yield


class CountingInvokeModel:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        return SimpleNamespace(content=self.result)


class RaisingStructuredModel:
    def with_structured_output(self, schema):
        return self

    def invoke(self, messages):
        raise RuntimeError("coder failed")


class PassingStructuredModel:
    def with_structured_output(self, schema):
        return self

    def invoke(self, messages):
        return SimpleNamespace(status="Success", suggestions="")


class FailingStructuredModel:
    def with_structured_output(self, schema):
        return self

    def invoke(self, messages):
        return SimpleNamespace(status="Fail", suggestions="broken")


def build_visual_protocol() -> VisualProtocol:
    return VisualProtocol(
        theme_palette=ThemePalette(
            background="#000000",
            primary_accent="#FFFFFF",
            secondary_accent="#CCCCCC",
            text_main="#FFFFFF",
            text_muted="#999999",
            highlight="#00FFFF",
            warning="#FFAA00",
            error="#FF0000",
        ),
        layout_blueprint=[
            LayoutBlueprintItem(
                id="root",
                type="Frame",
                position={"x": 0, "y": 0},
                size={"width": 100, "height": 100},
                style={"opacity": 1},
            )
        ],
        marks_definition={"start": 0},
        animation_formulas="fade in",
    )


class RefactorTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app_main.app)

    def test_generate_script_sse_returns_setup_updates_end(self):
        with patch.object(app_main, "workflow_app", AsyncWorkflowSuccess()):
            response = self.client.post("/api/generate_script_sse", json={"source_text": "hello"})

        self.assertEqual(response.status_code, 200)
        payloads = parse_sse_payloads(response.text)
        self.assertEqual([payload["type"] for payload in payloads], ["setup", "updates", "end"])
        self.assertEqual(len({payload["request_id"] for payload in payloads}), 1)

    def test_generate_script_sse_returns_error_event(self):
        with patch.object(app_main, "workflow_app", AsyncWorkflowError()):
            response = self.client.post("/api/generate_script_sse", json={"source_text": "hello"})

        self.assertEqual(response.status_code, 200)
        payloads = parse_sse_payloads(response.text)
        self.assertEqual([payload["type"] for payload in payloads], ["setup", "error", "end"])
        self.assertEqual(payloads[1]["message"], "boom")

    def test_writer_and_reviewer_use_distinct_roles(self):
        self.assertEqual(content_writer_agent["model_role"], "writer")
        self.assertEqual(content_reviewer_agent["model_role"], "reviewer")
        self.assertIsNot(get_model("writer"), get_model("reviewer"))

    def test_animation_coder_failure_is_isolated(self):
        task = CoderTaskState(
            scene=Scene(
                scene_id="scene-1",
                script="line",
                visual_design="design",
                camera_language="camera",
                visual_elements="elements",
                visual_transition="transition",
                emotion_rhythm="emotion",
                code_render_model="react",
                animation_marks={"start": 0},
            ),
            visual_architect=build_visual_protocol(),
        )

        with patch.dict(animation_module.__dict__, {"coder_cache": SimpleCache()}):
            with patch.dict(coder_module.coder_agent, {"model": RaisingStructuredModel()}):
                result = animation_module.coder_node(task, PromptManager())

        self.assertEqual(result["coder"], [])
        self.assertEqual(result["failed_scenes"], ["scene-1"])

    def test_content_writer_cache_hits_on_same_input(self):
        state = {
            "oral_content": "same input",
            "current_script": "",
            "review_score": None,
            "last_feedback": None,
            "loop_count": 0,
        }
        model = CountingInvokeModel("cached output")

        with patch.dict(conversational_module.__dict__, {"writer_cache": SimpleCache()}):
            with patch.dict(conversational_module.content_writer_agent, {"model": model}):
                first = conversational_module.content_writer(state, PromptManager())
                second = conversational_module.content_writer(state, PromptManager())

        self.assertEqual(first["current_script"], "cached output")
        self.assertEqual(second["current_script"], "cached output")
        self.assertEqual(model.calls, 1)

    def test_qa_guard_marks_failed_scene_without_dropping_code(self):
        task = CoderTaskState(
            scene=Scene(
                scene_id="scene-qa",
                script="line",
                visual_design="design",
                camera_language="camera",
                visual_elements="elements",
                visual_transition="transition",
                emotion_rhythm="emotion",
                code_render_model="react",
                animation_marks={"start": 0},
            ),
            visual_architect=build_visual_protocol(),
        )
        coder_result = SimpleNamespace(scene_id="scene-qa", code="render(<Scene />);")

        class SuccessfulCoderModel:
            def with_structured_output(self, schema):
                return self

            def invoke(self, messages):
                return coder_result

        with patch.dict(animation_module.__dict__, {"coder_cache": SimpleCache(), "qa_cache": SimpleCache()}):
            with patch.dict(coder_module.coder_agent, {"model": SuccessfulCoderModel()}):
                with patch.dict(qa_module.qa_guard_agent, {"model": FailingStructuredModel()}):
                    result = animation_module.coder_node(task, PromptManager())

        self.assertEqual(result["coder"], [coder_result])
        self.assertEqual(result["failed_scenes"], ["scene-qa"])


if __name__ == "__main__":
    unittest.main()
