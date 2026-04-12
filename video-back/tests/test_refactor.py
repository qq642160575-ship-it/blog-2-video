import json
import unittest
import uuid
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
from utils.structured_output import invoke_structured
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
    async def astream(self, initial_state, **kwargs):
        yield {"content_writer": {"current_script": "demo"}}

    def get_state(self, config):
        return SimpleNamespace(config={"configurable": {"checkpoint_id": "cp-1"}})


class AsyncWorkflowError:
    async def astream(self, initial_state, **kwargs):
        raise RuntimeError("boom")
        yield

    def get_state(self, config):
        return SimpleNamespace(config={"configurable": {"checkpoint_id": "cp-1"}})


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


class FailingStructuredModel:
    def with_structured_output(self, schema):
        return self

    def invoke(self, messages):
        return SimpleNamespace(status="Fail", suggestions="broken")


class MethodSensitiveStructuredModel:
    def __init__(self, payload: str):
        self.payload = payload

    def with_structured_output(self, schema, method="function_calling"):
        if method == "json_schema":
            raise RuntimeError("json_schema unsupported")
        return self

    def invoke(self, messages):
        return SimpleNamespace(content=self.payload)


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
        with patch("services.workflow_service.resolve_workflow", return_value=AsyncWorkflowSuccess()):
            response = self.client.post("/api/generate_script_sse", json={"source_text": "hello"})

        self.assertEqual(response.status_code, 200)
        payloads = parse_sse_payloads(response.text)
        self.assertEqual([payload["type"] for payload in payloads], ["setup", "updates", "end"])
        self.assertEqual(len({payload["request_id"] for payload in payloads}), 1)

    def test_generate_script_sse_returns_error_event(self):
        with patch("services.workflow_service.resolve_workflow", return_value=AsyncWorkflowError()):
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
                duration=4.5,
                animation_marks={"start": 0},
            ),
            visual_architect=build_visual_protocol(),
        )

        with patch.object(PromptManager, "get_langchain_messages", return_value=[]):
            with patch.dict(animation_module.__dict__, {"coder_cache": SimpleCache()}):
                with patch.dict(coder_module.coder_agent, {"model": RaisingStructuredModel()}):
                    result = animation_module.coder_node(task, PromptManager())

        self.assertEqual(result["coder"], [])
        self.assertEqual(result["failed_scenes"], ["scene-1"])

    def test_content_writer_cache_hits_on_same_input(self):
        oral_content = f"same input {uuid.uuid4()}"
        state = {
            "oral_content": oral_content,
            "current_script": "",
            "review_score": None,
            "last_feedback": None,
            "loop_count": 0,
            "last_action": None,
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
                duration=4.5,
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

        with patch.object(PromptManager, "get_langchain_messages", return_value=[]):
            with patch.dict(animation_module.__dict__, {"coder_cache": SimpleCache(), "qa_cache": SimpleCache()}):
                with patch.dict(coder_module.coder_agent, {"model": SuccessfulCoderModel()}):
                    with patch.dict(qa_module.qa_guard_agent, {"model": FailingStructuredModel()}):
                        result = animation_module.coder_node(task, PromptManager())

        self.assertEqual(len(result["coder"]), 1)
        self.assertEqual(result["coder"][0].scene_id, "scene-qa")
        self.assertEqual(result["coder"][0].code, "render(<Scene />);")
        self.assertEqual(result["failed_scenes"], ["scene-qa"])

    def test_dispatch_coders_preserves_visual_architect_payload(self):
        state = {
            "script": "demo",
            "director": {
                "scenes": [
                    {"scene_id": "scene-1", "script": "a"},
                    {"scene_id": "scene-2", "script": "b"},
                ]
            },
            "visual_architect": build_visual_protocol().model_dump(),
            "coder": [],
            "failed_scenes": [],
            "max_parallel_coders": 4,
            "last_action": None,
        }

        sends = animation_module.dispatch_coders(state)

        self.assertEqual(len(sends), 2)
        for send in sends:
            self.assertIsNotNone(send.arg["visual_architect"])

    def test_invoke_structured_falls_back_to_raw_json(self):
        class DemoSchema(content_reviewer_agent["response_format"]):
            pass

        model = MethodSensitiveStructuredModel('{"score": 88, "feedback": "ok"}')
        result = invoke_structured(
            model=model,
            schema=DemoSchema,
            messages=[],
            operation="test_fallback",
        )

        self.assertEqual(result.score, 88)
        self.assertEqual(result.feedback, "ok")


if __name__ == "__main__":
    unittest.main()
