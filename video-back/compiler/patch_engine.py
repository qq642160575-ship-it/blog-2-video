from typing import Any, Dict
from compiler.schemas import ScenePatch

def apply_patch(data: Dict[str, Any], patch: ScenePatch) -> Dict[str, Any]:
    """
    Applies JSON-patch-like operations to a given scene's data.
    Ensures that critical structural parts (scene_id, marks) cannot be targeted by patch.
    """
    allowed_paths = ["/theme", "/style", "/copy", "/motion", "/props"]
    patched_data = data.copy()
    
    for op in patch.ops:
        is_allowed = any(op.path.startswith(ap) for ap in allowed_paths)
        if not is_allowed:
            raise ValueError(f"Patch path {op.path} is restricted.")
            
        # Very simple dictionary patch algorithm for v1
        parts = op.path.strip("/").split("/")
        
        target = patched_data
        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]
            
        last_part = parts[-1]
        
        if op.op == "replace" or op.op == "add":
            target[last_part] = op.value
        elif op.op == "remove":
            if last_part in target:
                del target[last_part]
                
    return patched_data
