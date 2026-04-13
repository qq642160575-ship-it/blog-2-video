import os
import unittest
from unittest.mock import patch

from domain.tasks.state_machine import TaskStateMachine, TaskStateTransitionError
from layout.repair import RepairService
from layout.schemas import CanvasSpec, LayoutBox, LayoutElement, SceneLayoutSpec
from layout.text_metrics import TextMetrics
from layout.validator import LayoutValidator
from orchestration.event_publisher import InMemoryEventPublisher
from utils.cache import build_cache_key


class FoundationTests(unittest.IsolatedAsyncioTestCase):
    def build_scene(self) -> SceneLayoutSpec:
        return SceneLayoutSpec(
            scene_id="scene-001",
            canvas=CanvasSpec(),
            elements=[
                LayoutElement(
                    id="hero",
                    primitive_type="HeroTitle",
                    role="hero_title",
                    box=LayoutBox(x=20, y=40, width=760, height=90, z_index=0),
                    style={"font_size": 36, "line_height": 1.2, "padding": 12},
                    content={"text": "这里是一段非常非常长的标题文本，用来触发文本溢出检查"},
                    reveal_order=2,
                ),
                LayoutElement(
                    id="body",
                    primitive_type="BodyCard",
                    role="supporting_fact",
                    box=LayoutBox(x=120, y=120, width=760, height=180, z_index=1),
                    style={"font_size": 24, "line_height": 1.3, "padding": 16},
                    content={"text": "正文内容"},
                    reveal_order=1,
                ),
            ],
        )

    def test_text_metrics_wraps_mixed_language_text(self):
        metrics = TextMetrics()
        lines = metrics.estimate_lines(
            "hello world 这是一个很长的中文句子 mixed content",
            font_size=32,
            width=220,
        )
        self.assertGreaterEqual(lines, 2)

    def test_layout_validator_detects_overflow_and_collision(self):
        spec = self.build_scene()
        report = LayoutValidator().validate(spec)
        codes = {issue.code for issue in report.issues}

        self.assertIn("SAFE_AREA_OVERFLOW", codes)
        self.assertIn("TEXT_OVERFLOW", codes)
        self.assertIn("ELEMENT_COLLISION", codes)
        self.assertIn("FONT_SIZE_TOO_SMALL", codes)
        self.assertIn("ZINDEX_REVEAL_MISMATCH", codes)
        self.assertFalse(report.passed)

    def test_repair_service_resolves_primary_layout_issues(self):
        spec = self.build_scene()
        repair_result = RepairService().repair(spec)

        self.assertTrue(repair_result.repaired)
        repaired_codes = {issue.code for issue in repair_result.validation_report.issues}
        self.assertNotIn("SAFE_AREA_OVERFLOW", repaired_codes)
        self.assertNotIn("FONT_SIZE_TOO_SMALL", repaired_codes)
        self.assertNotIn("ELEMENT_COLLISION", repaired_codes)

    def test_task_state_machine_allows_retry_path(self):
        self.assertTrue(TaskStateMachine.can_transition("pending", "queued"))
        self.assertTrue(TaskStateMachine.can_transition("queued", "running"))
        self.assertTrue(TaskStateMachine.can_transition("running", "failed"))
        self.assertTrue(TaskStateMachine.can_transition("failed", "retrying"))
        self.assertTrue(TaskStateMachine.can_transition("retrying", "queued"))

    def test_task_state_machine_rejects_invalid_transition(self):
        with self.assertRaises(TaskStateTransitionError):
            TaskStateMachine.ensure_transition("succeeded", "queued")

    async def test_in_memory_event_publisher_stores_task_events(self):
        publisher = InMemoryEventPublisher()
        event = await publisher.publish(
            "task.started",
            task_id="task_1",
            session_id="sess_1",
            branch_id="br_1",
            payload={"percent": 10},
        )

        self.assertEqual(event.event_type, "task.started")
        self.assertEqual(len(publisher.list_by_task("task_1")), 1)
        self.assertEqual(publisher.list_by_task("task_1")[0].payload["percent"], 10)

    def test_cache_key_changes_with_prompt_version(self):
        with patch.dict(os.environ, {"VIDEO_BACK_PROMPT_VERSION": "v1"}, clear=False):
            key_v1 = build_cache_key("writer", "same-input")
        with patch.dict(os.environ, {"VIDEO_BACK_PROMPT_VERSION": "v2"}, clear=False):
            key_v2 = build_cache_key("writer", "same-input")

        self.assertNotEqual(key_v1, key_v2)


if __name__ == "__main__":
    unittest.main()
