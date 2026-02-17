from __future__ import annotations

import re
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


def _node_map(scene: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    nodes = scene.get("nodes")
    if not isinstance(nodes, list):
        return {}
    m: Dict[str, Dict[str, Any]] = {}
    for n in nodes:
        if isinstance(n, dict) and isinstance(n.get("nodeId"), str):
            m[n["nodeId"]] = n
    return m


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
    Returns (reachableNodesCount, reachableEndingsCount) using BFS from the first node in nodes[].
    """
    node_ids = _get_node_ids(scene)
    ending_ids = _get_ending_ids(scene)
    node_map = _node_map(scene)

    if not node_ids:
        return (0, 0)

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


def _choices_total(scene: Dict[str, Any]) -> int:
    nodes = scene.get("nodes")
    if not isinstance(nodes, list):
        return 0
    total = 0
    for n in nodes:
        if not isinstance(n, dict):
            continue
        choices = n.get("choices")
        if isinstance(choices, list):
            total += len(choices)
    return total


def _terminal_node_ratio(scene: Dict[str, Any]) -> float:
    """
    Ratio of nodes where ALL choices lead to an ending (i.e. terminal-ish wrappers).
    """
    node_map = _node_map(scene)
    ending_ids = _get_ending_ids(scene)
    nodes = scene.get("nodes")
    if not isinstance(nodes, list) or len(node_map) == 0:
        return 0.0

    terminal = 0
    total = 0

    for n in nodes:
        if not isinstance(n, dict) or not isinstance(n.get("nodeId"), str):
            continue
        total += 1
        choices = n.get("choices")
        if not isinstance(choices, list) or len(choices) == 0:
            terminal += 1
            continue

        all_to_endings = True
        for c in choices:
            if not isinstance(c, dict):
                continue
            to = c.get("to")
            if not isinstance(to, str):
                continue
            if to in node_map:
                all_to_endings = False
                break
            # to in ending_ids is fine, unknown targets would be counted elsewhere
        if all_to_endings:
            terminal += 1

    return (terminal / total) if total else 0.0


def _unique_target_ratio(scene: Dict[str, Any]) -> float:
    """
    Unique 'to' targets across all choices / total choices.
    Higher suggests more diverse branching.
    """
    nodes = scene.get("nodes")
    if not isinstance(nodes, list):
        return 0.0

    targets: Set[str] = set()
    total = 0

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
            if isinstance(to, str) and to.strip():
                targets.add(to.strip())
            total += 1

    return (len(targets) / total) if total else 0.0


def _max_shortest_path_depth(scene: Dict[str, Any]) -> int:
    """
    Max shortest-path depth from the start node.
    Uses BFS distances (safe with cycles).
    """
    node_ids = _get_node_ids(scene)
    node_map = _node_map(scene)
    ending_ids = _get_ending_ids(scene)

    if not node_ids:
        return 0

    start = node_ids[0]
    q = deque([start])
    dist: Dict[str, int] = {start: 0}

    while q:
        nid = q.popleft()
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
            if to in ending_ids:
                continue
            if to in node_map and to not in dist:
                dist[to] = dist[nid] + 1
                q.append(to)

    return max(dist.values()) if dist else 0


def _effects_total(scene: Dict[str, Any]) -> int:
    nodes = scene.get("nodes")
    if not isinstance(nodes, list):
        return 0
    total = 0
    for n in nodes:
        if not isinstance(n, dict):
            continue
        choices = n.get("choices")
        if not isinstance(choices, list):
            continue
        for c in choices:
            if not isinstance(c, dict):
                continue
            eff = c.get("effects")
            if isinstance(eff, list):
                total += len([x for x in eff if isinstance(x, str) and x.strip()])
    return total


def _ending_type_diversity(scene: Dict[str, Any]) -> int:
    endings = scene.get("endings")
    if not isinstance(endings, list):
        return 0
    types: Set[str] = set()
    for e in endings:
        if not isinstance(e, dict):
            continue
        t = e.get("type")
        if isinstance(t, str) and t.strip():
            types.add(t.strip())
    return len(types)


_word_re = re.compile(r"[A-Za-z0-9']+")


def _gather_text(scene: Dict[str, Any]) -> str:
    parts: List[str] = []

    intro = scene.get("intro")
    if isinstance(intro, dict):
        n = intro.get("narration")
        if isinstance(n, str):
            parts.append(n)

    nodes = scene.get("nodes")
    if isinstance(nodes, list):
        for n in nodes:
            if isinstance(n, dict):
                nar = n.get("narration")
                if isinstance(nar, str):
                    parts.append(nar)
                choices = n.get("choices")
                if isinstance(choices, list):
                    for c in choices:
                        if isinstance(c, dict):
                            t = c.get("text")
                            if isinstance(t, str):
                                parts.append(t)

    endings = scene.get("endings")
    if isinstance(endings, list):
        for e in endings:
            if isinstance(e, dict):
                t = e.get("title")
                if isinstance(t, str):
                    parts.append(t)
                nar = e.get("narration")
                if isinstance(nar, str):
                    parts.append(nar)

    return "\n".join(parts)


def _lexical_diversity(scene: Dict[str, Any]) -> float:
    text = _gather_text(scene).lower()
    words = _word_re.findall(text)
    if not words:
        return 0.0
    return len(set(words)) / len(words)


def _avg_narration_words(scene: Dict[str, Any]) -> float:
    nodes = scene.get("nodes")
    if not isinstance(nodes, list):
        return 0.0
    counts: List[int] = []
    for n in nodes:
        if not isinstance(n, dict):
            continue
        nar = n.get("narration")
        if isinstance(nar, str):
            words = _word_re.findall(nar)
            counts.append(len(words))
    return (sum(counts) / len(counts)) if counts else 0.0


def score_scene(scene: Dict[str, Any], m: Dict[str, Any]) -> Dict[str, Any]:
    def clamp01(x: float) -> float:
        return max(0.0, min(1.0, x))

    node_count = float(m.get("nodeCount") or 0)
    reachable_nodes = float(m.get("reachableNodesCount") or 0)
    invalid = int(m.get("invalidChoiceTargetsPostNormalize") or 0)

    # features you already compute
    max_depth = _max_shortest_path_depth(scene)
    unique_targets = _unique_target_ratio(scene)
    avg_words = _avg_narration_words(scene)
    lex = _lexical_diversity(scene)

    # ---- normalize to 0..1 ----
    valid_score = 1.0 if invalid == 0 else 0.0                       # hard gate
    reach_score = clamp01(reachable_nodes / node_count) if node_count else 0.0
    depth_score = clamp01(max_depth / 6.0)                            # 6 = "good depth" target
    branch_score = clamp01(unique_targets / 0.7)                      # ~0.7 is strong variety
    length_score = clamp01(avg_words / 45.0)                          # ~45 words/node = solid
    lex_score = clamp01(lex / 0.55)                                   # ~0.55 is strong diversity

    # ---- weighted composite ----
    total = (
        0.35 * valid_score +
        0.15 * reach_score +
        0.20 * depth_score +
        0.15 * branch_score +
        0.10 * length_score +
        0.05 * lex_score
    )

    final = round(total * 100.0, 2)

    return {
        "finalScore": final,
        # keep a few interpretable sub-scores (optional, but still clean)
        "validScore": round(valid_score, 3),
        "reachScore": round(reach_score, 3),
        "depthScore": round(depth_score, 3),
        "branchVarScore": round(branch_score, 3),
        "lengthScore": round(length_score, 3),
        "lexScore": round(lex_score, 3),

        # keep feature values (useful for analysis/plots)
        "maxDepth": int(max_depth),
        "uniqueTargetRatio": round(unique_targets, 4),
        "avgNarrationWords": round(avg_words, 2),
        "lexicalDiversity": round(lex, 4),
    }


def compute_metrics(
    scene: Dict[str, Any],
    *,
    invalid_targets_pre: int | None = None,
    invalid_targets_post: int | None = None
) -> Dict[str, Any]:
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

    base = {
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

    scoring = score_scene(scene, base)
    base.update(scoring)
    return base
