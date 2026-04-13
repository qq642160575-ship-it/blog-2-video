from __future__ import annotations

from typing import Annotated, TypedDict

from langgraph.constants import END
from langgraph.graph import StateGraph

from compiler.code_generator import generate_scene_code
from compiler.dsl_generator import generate_dsl
from compiler.layout_compiler import compile_layouts
from compiler.marks_engine import build_marks
from compiler.motion_compiler import compile_motions
from compiler.parser import parse_script
from compiler.repair import repair_scene_bundle
from compiler.scene_planner import build_scene_plan
from compiler.schemas import LayoutSpec, MarksBundle, MotionSpec, ParsedScript, RemotionDSL, SceneCode, ScenePlan, ValidationResult
from compiler.validator import validate_scene_bundle
from utils.logger import get_logger

logger = get_logger(__name__)


def reduce_last_action(left: str | None, right: str | list[str] | None) -> str | None:
    if not right:
        return left
    if isinstance(right, list):
        return right[-1]
    return right


class State(TypedDict):
    oral_script: str
    oral_script_result: dict | None
    parsed_script: dict | None
    scenes: list[dict]
    marks: dict | None
    layouts: dict[str, dict]
    motions: dict[str, dict]
    dsl: dict[str, dict]
    codes: dict[str, dict]
    validations: dict[str, dict]
    patches: dict[str, list[dict]]
    failed_scenes: list[str]
    repairable_scenes: list[str]
    theme_profile: dict | None
    compile_config: dict
    regenerate_scene_id: str | None
    recompile_from: str | None
    last_action: Annotated[str | None, reduce_last_action]


def parse_oral_script_node(state: State) -> dict:
    logger.info("Animation parse oral script node started")
    oral_script_result = state.get("oral_script_result") or {}
    if oral_script_result.get("script_segments"):
        parsed = ParsedScript(
            source_id="oral-script",
            intent="oral_script",
            tone=oral_script_result.get("script_metadata", {}).get("tone", "conversational"),
            emotion_curve=[],
            segments=oral_script_result["script_segments"],
        )
    else:
        parsed = parse_script(state["oral_script"])
    return {
        "parsed_script": parsed.model_dump(),
        "last_action": "口语稿解析完成",
    }


def plan_scenes_node(state: State) -> dict:
    logger.info("Scene planner node started")
    parsed_payload = state.get("parsed_script") or parse_script(state["oral_script"]).model_dump()
    scene_plans = build_scene_plan(ParsedScript(**parsed_payload))
    return {
        "scenes": [scene.model_dump() for scene in scene_plans],
        "last_action": f"分镜规划完成 ({len(scene_plans)} 个场景)",
    }


def generate_marks_node(state: State) -> dict:
    logger.info("Marks engine node started")
    scenes = [ScenePlan(**scene) for scene in state["scenes"]]
    updated_scenes, marks = build_marks(scenes, fps=state.get("compile_config", {}).get("fps", 30))
    return {
        "scenes": [scene.model_dump() for scene in updated_scenes],
        "marks": marks.model_dump(),
        "last_action": "时间轴生成完成",
    }


def compile_layout_node(state: State) -> dict:
    logger.info("Layout compiler node started")
    scenes = [ScenePlan(**scene) for scene in state["scenes"]]
    layouts = compile_layouts(scenes)
    if state.get("regenerate_scene_id") and state.get("layouts"):
        merged = dict(state["layouts"])
        merged.update({scene_id: layout.model_dump() for scene_id, layout in layouts.items()})
        layouts_payload = merged
    else:
        layouts_payload = {scene_id: layout.model_dump() for scene_id, layout in layouts.items()}
    return {
        "layouts": layouts_payload,
        "last_action": "布局编译完成",
    }


def compile_motion_node(state: State) -> dict:
    logger.info("Motion compiler node started")
    scenes = [ScenePlan(**scene) for scene in state["scenes"]]
    layouts = {scene_id: LayoutSpec(**layout) for scene_id, layout in state["layouts"].items()}
    motions = compile_motions(scenes, MarksBundle(**state["marks"]), layouts)
    return {
        "motions": {scene_id: motion.model_dump() for scene_id, motion in motions.items()},
        "last_action": "动效编译完成",
    }


def generate_dsl_node(state: State) -> dict:
    logger.info("DSL generator node started")
    scenes = [ScenePlan(**scene) for scene in state["scenes"]]
    layouts = {scene_id: LayoutSpec(**layout) for scene_id, layout in state["layouts"].items()}
    motions = {scene_id: MotionSpec(**motion) for scene_id, motion in state["motions"].items()}
    dsl_map = generate_dsl(scenes, layouts, motions)
    return {
        "dsl": {scene_id: dsl.model_dump() for scene_id, dsl in dsl_map.items()},
        "last_action": "DSL 生成完成",
    }


def generate_scene_code_node(state: State) -> dict:
    logger.info("Code generator node started")
    dsl_map = {scene_id: RemotionDSL(**dsl) for scene_id, dsl in state["dsl"].items()}
    codes = generate_scene_code(dsl_map)
    return {
        "codes": {scene_id: code.model_dump() for scene_id, code in codes.items()},
        "last_action": "场景代码生成完成",
    }


def validate_scene_node(state: State) -> dict:
    logger.info("Validation node started")
    validations: dict[str, dict] = {}
    failed_scenes: list[str] = []
    repairable_scenes: list[str] = []

    for scene in state["scenes"]:
        scene_id = scene["scene_id"]
        result = validate_scene_bundle(
            scene_id,
            LayoutSpec(**state["layouts"].get(scene_id)) if scene_id in state["layouts"] else None,
            MotionSpec(**state["motions"].get(scene_id)) if scene_id in state["motions"] else None,
            RemotionDSL(**state["dsl"].get(scene_id)) if scene_id in state["dsl"] else None,
            SceneCode(**state["codes"].get(scene_id)) if scene_id in state["codes"] else None,
        )
        validations[scene_id] = result.model_dump()
        if result.status == "fail":
            failed_scenes.append(scene_id)
            if result.repairable:
                repairable_scenes.append(scene_id)

    return {
        "validations": validations,
        "failed_scenes": failed_scenes,
        "repairable_scenes": repairable_scenes,
        "last_action": "静态校验完成",
    }


def repair_scene_node(state: State) -> dict:
    logger.info("Repair node started")
    layouts = dict(state["layouts"])
    motions = dict(state["motions"])
    dsl = dict(state["dsl"])
    codes = dict(state["codes"])
    validations = dict(state["validations"])

    for scene_id in state.get("repairable_scenes", []):
        repaired_layout, repaired_motion, repaired_dsl, repaired_code, repaired_validation = repair_scene_bundle(
            scene_id,
            LayoutSpec(**layouts[scene_id]) if scene_id in layouts else None,
            MotionSpec(**motions[scene_id]) if scene_id in motions else None,
            RemotionDSL(**dsl[scene_id]) if scene_id in dsl else None,
            SceneCode(**codes[scene_id]) if scene_id in codes else None,
            ValidationResult(**validations[scene_id]),
        )
        if repaired_layout is not None:
            layouts[scene_id] = repaired_layout.model_dump()
        if repaired_motion is not None:
            motions[scene_id] = repaired_motion.model_dump()
        if repaired_dsl is not None:
            dsl[scene_id] = repaired_dsl.model_dump()
        if repaired_code is not None:
            codes[scene_id] = repaired_code.model_dump()
        validations[scene_id] = repaired_validation.model_dump()

    failed_scenes = [scene_id for scene_id, value in validations.items() if value["status"] == "fail"]
    return {
        "layouts": layouts,
        "motions": motions,
        "dsl": dsl,
        "codes": codes,
        "validations": validations,
        "failed_scenes": failed_scenes,
        "repairable_scenes": [],
        "last_action": "自动修复完成",
    }


def finalize_output_node(state: State) -> dict:
    logger.info("Finalize node started")
    return {
        "last_action": "动画编译完成",
    }


def _should_repair(state: State) -> str:
    if state.get("repairable_scenes"):
        return "repair"
    return "finalize"


def build_workflow() -> StateGraph:
    workflow = StateGraph(State)
    workflow.add_node("parse_oral_script_node", parse_oral_script_node)
    workflow.add_node("plan_scenes_node", plan_scenes_node)
    workflow.add_node("generate_marks_node", generate_marks_node)
    workflow.add_node("compile_layout_node", compile_layout_node)
    workflow.add_node("compile_motion_node", compile_motion_node)
    workflow.add_node("generate_dsl_node", generate_dsl_node)
    workflow.add_node("generate_scene_code_node", generate_scene_code_node)
    workflow.add_node("validate_scene_node", validate_scene_node)
    workflow.add_node("repair_scene_node", repair_scene_node)
    workflow.add_node("finalize_output_node", finalize_output_node)
    workflow.set_entry_point("parse_oral_script_node")
    workflow.add_edge("parse_oral_script_node", "plan_scenes_node")
    workflow.add_edge("plan_scenes_node", "generate_marks_node")
    workflow.add_edge("generate_marks_node", "compile_layout_node")
    workflow.add_edge("compile_layout_node", "compile_motion_node")
    workflow.add_edge("compile_motion_node", "generate_dsl_node")
    workflow.add_edge("generate_dsl_node", "generate_scene_code_node")
    workflow.add_edge("generate_scene_code_node", "validate_scene_node")
    workflow.add_conditional_edges(
        "validate_scene_node",
        _should_repair,
        {
            "repair": "repair_scene_node",
            "finalize": "finalize_output_node",
        },
    )
    workflow.add_edge("repair_scene_node", "finalize_output_node")
    workflow.add_edge("finalize_output_node", END)
    return workflow


def build_animation_workflow(checkpointer=None):
    workflow = build_workflow()
    if checkpointer is None:
        return workflow.compile()
    return workflow.compile(checkpointer=checkpointer)
