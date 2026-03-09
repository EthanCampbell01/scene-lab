import re
from typing import Any, Dict, List, Set, Tuple, Optional

TARGET_KEYS = {"to", "target", "next", "goto"}  # extend if needed


def _is_dict(x: Any) -> bool:
    return isinstance(x, dict)


def _is_list(x: Any) -> bool:
    return isinstance(x, list)


def _ensure_endings_have_ending_ids(scene: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Ensure endings exists, is a list, and each ending has an endingId (schema-correct).
    If endings missing/empty, create a minimal safe set (IDs only + neutral narration).
    """
    endings = scene.get("endings")

    if not isinstance(endings, list) or len(endings) == 0:
        endings = [
            {"endingId": "end0", "title": "Ending 1", "type": "mixed", "narration": "The scene concludes."},
            {"endingId": "end1", "title": "Ending 2", "type": "mixed", "narration": "The scene concludes."},
        ]
        scene["endings"] = endings
        return endings

    for i, e in enumerate(endings):
        if not isinstance(e, dict):
            endings[i] = {"endingId": f"end{i}", "title": f"Ending {i+1}", "type": "mixed", "narration": str(e)}
            continue

        if not isinstance(e.get("endingId"), str) or not e["endingId"].strip():
            e["endingId"] = str(e.get("id") or f"end{i}")

        if not isinstance(e.get("title"), str) or not e["title"].strip():
            e["title"] = f"Ending {i+1}"

        if e.get("type") not in {"success", "mixed", "failure", "twist"}:
            e["type"] = "mixed"

        if not isinstance(e.get("narration"), str) or not e["narration"].strip():
            e["narration"] = "The scene concludes."

    scene["endings"] = endings
    return endings


def _collect_valid_targets(scene: Dict[str, Any]) -> Set[str]:
    """Collect all valid nodeIds and endingIds."""
    valid: Set[str] = set()

    nodes = scene.get("nodes")
    if isinstance(nodes, list):
        for n in nodes:
            if isinstance(n, dict):
                nid = n.get("nodeId")
                if isinstance(nid, str) and nid.strip():
                    valid.add(nid.strip())

    endings = scene.get("endings")
    if isinstance(endings, list):
        for e in endings:
            if isinstance(e, dict):
                eid = e.get("endingId")
                if isinstance(eid, str) and eid.strip():
                    valid.add(eid.strip())

    return valid


def _build_endings_index(endings: List[Dict[str, Any]]) -> Tuple[Dict[int, str], str]:
    """Map endings[0] -> endingId, and choose a safe default endingId."""
    index_to_endingId: Dict[int, str] = {}
    default_end_id: Optional[str] = None

    for i, e in enumerate(endings):
        if isinstance(e, dict):
            eid = e.get("endingId")
            if isinstance(eid, str) and eid.strip():
                index_to_endingId[i] = eid.strip()
                if default_end_id is None:
                    default_end_id = eid.strip()

    default_end_id = default_end_id or "end0"
    return index_to_endingId, default_end_id


def _ordered_node_ids(scene: Dict[str, Any]) -> List[str]:
    nodes = scene.get("nodes")
    if not isinstance(nodes, list):
        return []
    out: List[str] = []
    for n in nodes:
        if isinstance(n, dict):
            nid = n.get("nodeId")
            if isinstance(nid, str) and nid.strip():
                out.append(nid.strip())
    return out


def normalize_scene_targets(scene: Dict[str, Any], *, verbose: bool = False) -> Dict[str, Any]:
    """
    Repairs navigation targets so the runtime never breaks.
    - Ensures endings have endingId
    - Converts 'endings[1]' style targets to real endingIds
    - Converts unknown targets (including 'END') to a *node* when possible to avoid instant endings
    """
    endings = _ensure_endings_have_ending_ids(scene)
    index_to_endingId, default_end_id = _build_endings_index(endings)

    valid_targets = _collect_valid_targets(scene)
    node_ids = _ordered_node_ids(scene)

    endings_index_re = re.compile(r"^endings\[(\d+)\]$", re.IGNORECASE)
    endings_dot_re = re.compile(r"^endings\.(\d+)$", re.IGNORECASE)
    bare_int_re = re.compile(r"^\d+$")

    def rewrite_target(t: str, current_node_id: Optional[str] = None) -> str:
        raw = (t or "").strip()
        if not raw:
            raw = "END"

        # Already valid nodeId/endingId
        if raw in valid_targets:
            return raw

        # endings[1] -> endingId
        m = endings_index_re.match(raw) or endings_dot_re.match(raw)
        if m:
            idx = int(m.group(1))
            return index_to_endingId.get(idx, default_end_id)

        # "0"/"1" -> interpret as ending index (optional)
        if bare_int_re.match(raw):
            idx = int(raw)
            return index_to_endingId.get(idx, default_end_id)

        # END or unknown: prefer routing to a node to keep play going
        if raw.upper() == "END" or raw not in valid_targets:
            if node_ids:
                if current_node_id in node_ids:
                    i = node_ids.index(current_node_id)
                    return node_ids[i + 1] if i + 1 < len(node_ids) else node_ids[0]
                return node_ids[0]
            return default_end_id

        return default_end_id

    def walk(x: Any, current_node_id: Optional[str] = None) -> None:
        if _is_dict(x):
            # if this dict looks like a node, capture nodeId context
            if "nodeId" in x and isinstance(x.get("nodeId"), str):
                current_node_id = x["nodeId"]

            for k, v in list(x.items()):
                if k in TARGET_KEYS and isinstance(v, str):
                    new_v = rewrite_target(v, current_node_id=current_node_id)
                    if verbose and new_v != v:
                        print(f"[normalize] {k}: {v!r} -> {new_v!r}")
                    x[k] = new_v
                else:
                    walk(v, current_node_id=current_node_id)

        elif _is_list(x):
            for v in x:
                walk(v, current_node_id=current_node_id)

    walk(scene)
    return scene
