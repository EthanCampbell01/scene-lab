from __future__ import annotations

from collections import deque
from typing import Any, Dict, List, Set, Tuple


def _get_node_ids(scene: Dict[str, Any]) -> List[str]:
    nodes = scene.get("nodes")
    if not isinstance(nodes, list):
        return []
    out: List[str] = []
    for n in nodes:
        if isinstance(n, dict) and isinstance(n.get("nodeId"), str):
            out.append(n["nodeId"])
    return out


def _get_ending_ids(scene: Dict[str, Any]) -> Set[str]:
    endings = scene.get("endings")
    if not isinstance(endings, list):
        return set()
    out: Set[str] = set()
    for e in endings:
        if isinstance(e, dict) and isinstance(e.get("endingId"), str):
            out.add(e["endingId"])
    return out


def count_invalid_targets(scene: Dict[str, Any]) -> int:
    node_ids = set(_get_node_ids(scene))
    ending_ids = _get_ending_ids(scene)
    valid = node_ids | ending_ids

    nodes = scene.get("nodes")
    if not isinstance(nodes, list):
        return 0

    bad = 0
    for n in nodes:
        if not isinstance(n, dict):
            continue
        choices = n.get("choices")
        if not isinstance(choices, list):
            continue
        for c in choices:
            if not isinstance(c, dict):
                continue
            to = c.get("to")
            if not isinstance(to, str) or to.strip() == "":
                bad += 1
            elif to not in valid:
                bad += 1
    return bad


def reachable_counts(scene: Dict[str, Any]) -> Tuple[int, int]:
    """
    Returns (reachableNodesCount, reachableEndingsCount)
    using BFS from the first node in nodes[].
    """
    node_ids = _get_node_ids(scene)
    ending_ids = _get_ending_ids(scene)

    nodes = scene.get("nodes")
    if not isinstance(nodes, list) or not node_ids:
        return (0, 0)

    node_map: Dict[str, Dict[str, Any]] = {}
    for n in nodes:
        if isinstance(n, dict) and isinstance(n.get("nodeId"), str):
            node_map[n["nodeId"]] = n

    start = node_ids[0]
    q = deque([start])
    seen_nodes: Set[str] = set()
    seen_endings: Set[str] = set()

    while q:
        nid = q.popleft()
        if nid in seen_nodes:
            continue
        seen_nodes.add(nid)

        node = node_map.get(nid)
        if not node:
            continue

        choices = node.get("choices")
        if not isinstance(choices, list):
            continue

        for c in choices:
            if not isinstance(c, dict):
                continue
            to = c.get("to")
            if not isinstance(to, str):
                continue
            if to in node_map and to not in seen_nodes:
                q.append(to)
            elif to in ending_ids:
                seen_endings.add(to)

    return (len(seen_nodes), len(seen_endings))


def compute_metrics(scene: Dict[str, Any], *, invalid_targets_pre: int | None = None, invalid_targets_post: int | None = None) -> Dict[str, Any]:
    node_ids = _get_node_ids(scene)
    ending_ids = list(_get_ending_ids(scene))

    reachable_nodes, reachable_endings = reachable_counts(scene)

    # choices per node stats
    min_choices = None
    max_choices = None
    nodes = scene.get("nodes")
    if isinstance(nodes, list):
        for n in nodes:
            if not isinstance(n, dict):
                continue
            choices = n.get("choices")
            c_count = len(choices) if isinstance(choices, list) else 0
            min_choices = c_count if min_choices is None else min(min_choices, c_count)
            max_choices = c_count if max_choices is None else max(max_choices, c_count)

    return {
        "sceneId": scene.get("sceneId"),
        "variantId": scene.get("variantId"),
        "nodeCount": len(node_ids),
        "endingCount": len(ending_ids),
        "choicesPerNodeMin": min_choices if min_choices is not None else 0,
        "choicesPerNodeMax": max_choices if max_choices is not None else 0,
        "reachableNodesCount": reachable_nodes,
        "reachableEndingsCount": reachable_endings,
        "invalidChoiceTargetsPreNormalize": invalid_targets_pre,
        "invalidChoiceTargetsPostNormalize": invalid_targets_post,
    }
