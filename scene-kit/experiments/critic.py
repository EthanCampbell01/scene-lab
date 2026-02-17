from __future__ import annotations

import json
import os
import requests
from typing import Any, Dict


def _call_openrouter(system: str, user: str, timeout_s: int = 120) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY env var is required for critic evaluation")

    # Use a stronger model for judging than generation, if you want.
    # If you already set OPENROUTER_MODEL for generation, keep critic separate:
    model = os.getenv("OPENROUTER_CRITIC_MODEL", os.getenv("OPENROUTER_MODEL", "openai/gpt-4.1"))

    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://localhost/scene-kit",
        "X-Title": "Scene Kit Critic",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.0,  # deterministic judging
    }

    r = requests.post(url, headers=headers, json=payload, timeout=timeout_s)
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"]


def evaluate_narrative(scene: Dict[str, Any]) -> Dict[str, Any]:
    """
    Model-as-critic evaluation.
    Returns compact numeric dimensions + a short justification string.
    """
    system = (
        "You are a strict evaluator of branching narrative quality. "
        "Return ONLY valid JSON. No markdown. No commentary outside JSON."
    )

    # Keep input small: scene can be huge; judge based on the important parts.
    # We'll pass intro + nodes narration/choices + endings narration/title.
    payload = {
        "title": scene.get("title"),
        "intro": scene.get("intro"),
        "nodes": [
            {
                "nodeId": n.get("nodeId"),
                "narration": n.get("narration"),
                "choices": [{"text": c.get("text"), "to": c.get("to")} for c in (n.get("choices") or [])],
            }
            for n in (scene.get("nodes") or [])
            if isinstance(n, dict)
        ],
        "endings": [
            {"endingId": e.get("endingId"), "type": e.get("type"), "title": e.get("title"), "narration": e.get("narration")}
            for e in (scene.get("endings") or [])
            if isinstance(e, dict)
        ],
    }

    user = (
    "You are a strict narrative quality assessor. Your job is to DISCRIMINATE between scenes.\n"
    "Use the full 0–10 scale. Most scenes should fall between 4 and 7.\n"
    "Scores 8–10 should be rare and only for genuinely exceptional writing.\n\n"
    "Calibration anchors:\n"
    "- 9–10: exceptional, memorable voice, sharp dialogue, strong tension, minimal cliché\n"
    "- 7–8: good, coherent, some originality, minor awkwardness\n"
    "- 5–6: average, generic phrasing, some clunky lines, tension uneven\n"
    "- 3–4: poor, repetitive, unnatural dialogue, weak intent/tension\n"
    "- 0–2: incoherent/unreadable\n\n"
    "Penalise for:\n"
    "- generic/cliché phrasing (\"you feel a sense of determination\", etc.)\n"
    "- choices that feel similar or low consequence\n"
    "- flat or implausible character voice\n"
    "- repetition and filler narration\n\n"
    "Return ONLY valid JSON (no markdown) with EXACTLY these keys:\n"
    "dialogueQuality, emotionalCoherence, characterConsistency, dramaticTension, originalityAndVoice, overallNarrativeQuality,\n"
    "keyIssues, standoutLine, worstLine, justification\n\n"
    "Scoring: all score fields must be integers 0–10.\n"
    "keyIssues: array of exactly 3 short strings.\n"
    "standoutLine and worstLine: short quoted excerpts from the scene.\n"
    "justification: 2–4 sentences.\n\n"
    f"SCENE:\n{json.dumps(payload, ensure_ascii=False)}"
    )

    raw = _call_openrouter(system, user, timeout_s=120).strip()

    # Best-effort parse: critic must output JSON
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        # If the model wrapped content, attempt to salvage first {...}
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1 and end > start:
            obj = json.loads(raw[start : end + 1])
        else:
            raise

      # Enforce shape and types
    numeric_keys = [
        "dialogueQuality",
        "emotionalCoherence",
        "characterConsistency",
        "dramaticTension",
        "originalityAndVoice",
        "overallNarrativeQuality",
    ]
    text_keys = ["standoutLine", "worstLine", "justification"]

    out: Dict[str, Any] = {}

    # Pull numeric scores
    for k in numeric_keys:
        try:
            v = int(obj.get(k))
        except Exception:
            v = 0
        out[k] = max(0, min(10, v))

    # Pull keyIssues
    key_issues = obj.get("keyIssues")
    if not isinstance(key_issues, list):
        key_issues = []
    out["keyIssues"] = [str(x) for x in key_issues[:3]]

    # Pull text fields
    for k in text_keys:
        v = obj.get(k)
        out[k] = v if isinstance(v, str) else ""

    # Aggregate score (0..60)
    out["criticScore"] = sum(out[k] for k in numeric_keys)

    return out

    if not isinstance(out.get("keyIssues"), list):
        out["keyIssues"] = []
    out["keyIssues"] = [str(x) for x in out["keyIssues"][:3]]

    if not isinstance(out.get("standoutLine"), str):
        out["standoutLine"] = ""

