from __future__ import annotations

from compiler.schemas import DSLNode, LayoutSpec, MotionSpec, RemotionDSL, ScenePlan


def _dsl_type_for_node(kind: str) -> str:
    if kind == "text":
        return "TextNode"
    if kind == "badge":
        return "BadgeNode"
    return "PanelNode"


def generate_dsl(
    scenes: list[ScenePlan],
    layouts: dict[str, LayoutSpec],
    motions: dict[str, MotionSpec],
) -> dict[str, RemotionDSL]:
    results: dict[str, RemotionDSL] = {}
    for scene in scenes:
        layout = layouts[scene.scene_id]
        motion_by_target = {item.target: item for item in motions[scene.scene_id].motions}
        children = []
        for node in layout.nodes:
            children.append(
                DSLNode(
                    type=_dsl_type_for_node(node.kind),
                    props={
                        "node_id": node.id,
                        "kind": node.kind,
                        "box": node.box,
                        "z_index": node.z_index,
                        "content": node.props,
                        "motion": motion_by_target.get(node.id).model_dump() if node.id in motion_by_target else None,
                    },
                )
            )
        results[scene.scene_id] = RemotionDSL(
            scene_id=scene.scene_id,
            component_tree=DSLNode(type="AbsoluteFill", props={"scene_id": scene.scene_id}, children=children),
        )
    return results
