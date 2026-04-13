from __future__ import annotations

import json
import re

from compiler.schemas import DSLNode, RemotionDSL, SceneCode


def _component_name(scene_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9]+", " ", scene_id).title().replace(" ", "")
    return safe or "GeneratedScene"


def _js_object_literal(value: dict[str, int]) -> str:
    return "{ " + ", ".join(f"{key}: {value[key]}" for key in ("x", "y", "width", "height")) + " }"


def _render_node(node: DSLNode, marks_var: str = "marks") -> str:
    props = node.props
    box = props.get("box", {})
    node_id = props.get("node_id", "node")
    motion = props.get("motion") or {}
    motion_start = int(motion.get("start", 0))
    distance = int((motion.get("params") or {}).get("distance", 24))
    style_name = "title" if node_id == "headline" else "body"
    box_literal = _js_object_literal(
        {
            "x": box.get("x", 120),
            "y": box.get("y", 220),
            "width": box.get("width", 840),
            "height": box.get("height", 180),
        }
    )

    if node.type == "TextNode":
        text = json.dumps(props.get("content", {}).get("text", ""), ensure_ascii=False)
        return (
            "{(() => {\n"
            f"  const box = fitBox({_js_object_literal({'x': box.get('x', 120), 'y': box.get('y', 220), 'width': box.get('width', 840), 'height': box.get('height', 180)})});\n"
            f"  const progress = spring({{ frame: Math.max(0, frame - safeFrame({marks_var}, '{node_id}In', {motion_start})), fps, config: {{ damping: 14, stiffness: 120 }} }});\n"
            "  return (\n"
            "    <div\n"
            "      style={{\n"
            "        position: 'absolute',\n"
            "        left: box.x,\n"
            "        top: box.y,\n"
            "        width: box.width,\n"
            "        height: box.height,\n"
            f"        transform: `translateY(${{(1 - progress) * {distance}}}px)`,\n"
            "        opacity: progress,\n"
            f"        zIndex: {props.get('z_index', 1)},\n"
            "      }}\n"
            "    >\n"
            f"      <div style={{{{ ...createMobileTextStyle('{style_name}'), whiteSpace: 'pre-wrap' }}}}>\n"
            f"        {{{text}}}\n"
            "      </div>\n"
            "    </div>\n"
            "  );\n"
            "})()}"
        )

    box_literal = _js_object_literal(
        {
            "x": box.get("x", 140),
            "y": box.get("y", 760),
            "width": box.get("width", 800),
            "height": box.get("height", 220),
        }
    )
    label = json.dumps(props.get("content", {}).get("label", node_id), ensure_ascii=False)
    return (
        "{(() => {\n"
        f"  const box = fitBox({box_literal});\n"
        f"  const progress = spring({{ frame: Math.max(0, frame - safeFrame({marks_var}, '{node_id}In', {motion_start})), fps, config: {{ damping: 14, stiffness: 120 }} }});\n"
        "  return (\n"
        "    <div\n"
        "      style={{\n"
        "        position: 'absolute',\n"
        "        left: box.x,\n"
        "        top: box.y,\n"
        "        width: box.width,\n"
        "        height: box.height,\n"
        "        border: '4px solid #000',\n"
        "        borderRadius: 24,\n"
        "        boxShadow: '8px 8px 0px rgba(0,0,0,0.15)',\n"
        "        backgroundColor: '#fff',\n"
        "        padding: 24,\n"
        "        transform: `scale(${0.92 + progress * 0.08})`,\n"
        "        opacity: progress,\n"
        f"        zIndex: {props.get('z_index', 1)},\n"
        "      }}\n"
        "    >\n"
        "      <div style={{ ...createMobileTextStyle('label') }}>\n"
        f"        {{{label}}}\n"
        "      </div>\n"
        "    </div>\n"
        "  );\n"
        "})()}"
    )


def generate_scene_code(dsls: dict[str, RemotionDSL]) -> dict[str, SceneCode]:
    results: dict[str, SceneCode] = {}
    for scene_id, dsl in dsls.items():
        component_name = _component_name(scene_id)
        children = "\n        ".join(_render_node(child) for child in dsl.component_tree.children)
        code = (
            f"function {component_name}({{ marks }}) {{\n"
            f"  const frame = useCurrentFrame();\n"
            f"  const {{ fps }} = useVideoConfig();\n"
            f"  return (\n"
            f"    <AbsoluteFill\n"
            f"      style={{{{\n"
            f"        backgroundColor: '#FDFBEE',\n"
            f"        backgroundImage: 'radial-gradient(#E2E8F0 1px, transparent 0)',\n"
            f"        backgroundSize: '24px 24px',\n"
            f"      }}}}\n"
            f"    >\n"
            f"      <SafeArea>\n"
            f"        {children}\n"
            f"      </SafeArea>\n"
            f"    </AbsoluteFill>\n"
            f"  );\n"
            f"}}\n"
            f"render(<{component_name} marks={{marks}} />);"
        )
        results[scene_id] = SceneCode(scene_id=scene_id, component_name=component_name, code=code)
    return results
