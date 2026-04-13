import asyncio
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.append(str(Path(__file__).resolve().parents[1]))

from compiler.code_generator import generate_scene_code
from compiler.dsl_generator import generate_dsl
from compiler.layout_compiler import compile_layouts
from compiler.marks_engine import build_marks
from compiler.motion_compiler import compile_motions
from compiler.parser import parse_script
from compiler.scene_planner import build_scene_plan
from compiler.schemas import LayoutSpec, MarksBundle, MotionSpec, RemotionDSL, SceneCode
from compiler.validator import validate_scene_bundle
from services.workflow_service import (
    build_animation_initial_state,
    build_conversational_initial_state,
    build_run_config,
    stream_workflow_response,
)


class AsyncWorkflowSuccess:
    async def astream(self, initial_state, **kwargs):
        yield {"rewrite_oral_script_node": {"current_script": "demo oral"}}
        yield {"finalize_oral_script_node": {"oral_script_result": {"oral_script": "demo oral"}}}

    def get_state(self, config):
        return SimpleNamespace(config={"configurable": {"checkpoint_id": "cp-1"}}, values={})


class AsyncWorkflowError:
    async def astream(self, initial_state, **kwargs):
        raise RuntimeError("boom")
        yield

    def get_state(self, config):
        return SimpleNamespace(config={"configurable": {"checkpoint_id": "cp-1"}}, values={})


class RefactorTests(unittest.TestCase):
    def _collect_sse(self, workflow_name: str, initial_state: dict) -> list[str]:
        async def _runner():
            chunks = []
            async for chunk in stream_workflow_response(workflow_name, initial_state, build_run_config("test-thread")):
                chunks.append(chunk)
            return chunks

        return asyncio.run(_runner())

    def test_generate_script_sse_returns_setup_updates_end(self):
        with patch("services.workflow_service.resolve_workflow", return_value=AsyncWorkflowSuccess()):
            chunks = self._collect_sse("conversational_tone", build_conversational_initial_state("hello"))

        self.assertIn('"type": "setup"', chunks[0])
        self.assertIn('"type": "end"', chunks[-1])

    def test_generate_script_sse_returns_error_end_status(self):
        with patch("services.workflow_service.resolve_workflow", return_value=AsyncWorkflowError()):
            chunks = self._collect_sse("conversational_tone", build_conversational_initial_state("hello"))

        self.assertIn('"type": "error"', chunks[-2])
        self.assertIn('"status": "error"', chunks[-1])

    def test_conversational_initial_state_uses_source_text(self):
        state = build_conversational_initial_state("hello")
        self.assertEqual(state["source_text"], "hello")
        self.assertIsNone(state["oral_script_result"])

    def test_animation_initial_state_uses_oral_script(self):
        state = build_animation_initial_state("oral script")
        self.assertEqual(state["oral_script"], "oral script")
        self.assertEqual(state["compile_config"]["fps"], 30)

    def test_compiler_pipeline_generates_valid_scene_bundle(self):
        parsed = parse_script("你有没有发现 AI 会突然变笨？明明问题很简单。")
        scenes = build_scene_plan(parsed)
        updated_scenes, marks = build_marks(scenes, fps=30)
        layouts = compile_layouts(updated_scenes)
        motions = compile_motions(updated_scenes, marks, layouts)
        dsl_map = generate_dsl(updated_scenes, layouts, motions)
        codes = generate_scene_code(dsl_map)

        self.assertTrue(updated_scenes)
        first_scene_id = updated_scenes[0].scene_id
        validation = validate_scene_bundle(
            first_scene_id,
            LayoutSpec(**layouts[first_scene_id].model_dump()),
            MotionSpec(**motions[first_scene_id].model_dump()),
            RemotionDSL(**dsl_map[first_scene_id].model_dump()),
            SceneCode(**codes[first_scene_id].model_dump()),
        )
        self.assertEqual(validation.status, "pass")
        self.assertIn("render(", codes[first_scene_id].code)

    def test_marks_are_monotonic(self):
        parsed = parse_script("第一句。第二句。第三句。")
        scenes = build_scene_plan(parsed)
        updated_scenes, marks = build_marks(scenes, fps=30)
        starts = [scene.start for scene in updated_scenes]
        self.assertEqual(starts, sorted(starts))
        self.assertEqual(marks.global_marks[updated_scenes[0].scene_id], 0)
