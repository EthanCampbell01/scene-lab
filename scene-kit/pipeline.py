"""scene-kit/pipeline.py

One-command pipeline to generate an *expanded* scene JSON that the React previewer
can load automatically.

What it does:
  1) Calls your chosen provider (OpenRouter or Ollama)
  2) Asks for a JSON object that matches validator/schema/expanded_scene.schema.json
  3) Writes it to scene-kit/output/
  4) Copies it to previewer/public/latest.json (so the previewer auto-loads)

This removes the manual steps of renaming/moving JSON files.

Usage (from scene-lab/scene-kit):
  python pipeline.py --provider ollama --brief "..." --variant "cia-safe-house" --serve

Notes:
  - Requires Ollama running locally if provider=ollama
  - For OpenRouter, set OPENROUTER_API_KEY
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import time
import webbrowser
from scene_normalizer import normalize_scene_targets
from typing import Any, Dict, Optional

import requests


ROOT = os.path.dirname(os.path.dirname(__file__))  # scene-lab/
SCHEMA_PATH = os.path.join(ROOT, "validator", "schema", "expanded_scene.schema.json")

def _strip_json_comments(s: str) -> str:
    """
    Remove // and /* */ comments from a JSON-like string, without breaking URLs
    or anything inside quotes.
    """
    out = []
    i = 0
    in_str = False
    esc = False
    while i < len(s):
        ch = s[i]

        if in_str:
            out.append(ch)
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            i += 1
            continue

        # not in string
        if ch == '"':
            in_str = True
            out.append(ch)
            i += 1
            continue

        # // comment
        if ch == "/" and i + 1 < len(s) and s[i + 1] == "/":
            i += 2
            while i < len(s) and s[i] not in "\r\n":
                i += 1
            continue

        # /* */ comment
        if ch == "/" and i + 1 < len(s) and s[i + 1] == "*":
            i += 2
            while i + 1 < len(s) and not (s[i] == "*" and s[i + 1] == "/"):
                i += 1
            i += 2  # consume */
            continue

        out.append(ch)
        i += 1

    return "".join(out)


def _json_salvage(s: str) -> str:
    s = (s or "").strip().lstrip("\ufeff")
    s = _strip_json_comments(s)
    # Remove trailing commas before } or ]
    s = re.sub(r",\s*([}\]])", r"\1", s)
    return s.strip()



def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _slugify(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.strip().lower()).strip("-")
    return s or f"scene-{int(time.time())}"


def _extract_first_json(text: str) -> str:
    """
    Extract the first valid-looking JSON object/array from a messy LLM response.
    Handles: preamble text, ```json fences, trailing commentary.
    """
    t = (text or "").strip()

    # If fenced, prefer fenced content
    if "```" in t:
        parts = t.split("```")
        for p in parts:
            p = p.strip()
            if p.lower().startswith("json"):
                p = p[4:].strip()
            if p.startswith("{") or p.startswith("["):
                t = p
                break

    # Find first { or [
    start_candidates = [i for i in (t.find("{"), t.find("[")) if i != -1]
    if not start_candidates:
        raise ValueError("No JSON object/array start found in model output.")

    start = min(start_candidates)
    t = t[start:]

    opener = t[0]
    closer = "}" if opener == "{" else "]"
    depth = 0
    in_str = False
    esc = False

    for i, ch in enumerate(t):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue

        if ch == '"':
            in_str = True
            continue

        if ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                return t[: i + 1]

    raise ValueError("JSON appears truncated (no matching closing bracket found).")


def _call_openrouter(system: str, user: str, timeout_s: int) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY env var is required for provider=openrouter")

    model = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://localhost/scene-kit",
        "X-Title": "Scene Kit Pipeline",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": float(os.getenv("OPENROUTER_TEMPERATURE", "0.7")),
    }
    r = requests.post(url, headers=headers, json=payload, timeout=timeout_s)
    r.raise_for_status()
    data = r.json()
    return data["choices"][0]["message"]["content"]


def _call_ollama(system: str, user: str, timeout_s: int) -> str:
    model = os.getenv("OLLAMA_MODEL", "mistral:7b-instruct")
    base = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")

    # Make output more reliable + less likely to ramble
    temperature = float(os.getenv("OLLAMA_TEMPERATURE", "0.3"))

    # Increase if you still see truncation, decrease if it rambles too long
    num_predict = int(os.getenv("OLLAMA_NUM_PREDICT", "2048"))

    chat_url = f"{base}/api/chat"
    chat_payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,

        # Ollama JSON mode (critical)
        "format": "json",

        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
        },
    }

    r = requests.post(chat_url, json=chat_payload, timeout=timeout_s)
    r.raise_for_status()
    data = r.json()

    # /api/chat usually returns: {"message": {"role": "...", "content": "..."}}
    msg = data.get("message")
    if isinstance(msg, dict) and "content" in msg:
        return msg["content"]

    # fallback
    return data.get("response", "")


def _model_call(provider: str, system: str, user: str, timeout_s: int, retries: int = 2) -> str:
    last_err: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            if provider == "openrouter":
                return _call_openrouter(system, user, timeout_s)
            return _call_ollama(system, user, timeout_s)
        except Exception as e:
            last_err = e
            if attempt < retries:
                time.sleep(1.5 * (attempt + 1))
            else:
                raise
    raise last_err  # pragma: no cover


def _validate_or_repair(scene: Dict[str, Any]) -> Dict[str, Any]:
    """
    Best-effort normalization to the expanded schema.

    Important: this does NOT invent story content. It only fixes shape so the
    previewer doesn't go blank.
    """
    # Unwrap common wrappers
    if "scene" in scene and isinstance(scene["scene"], dict):
        scene = scene["scene"]

    if isinstance(scene, list):
        raise ValueError("Model returned a JSON array, expected an object. Regenerate.")

    # Required top-level keys
    if "sceneId" not in scene:
        scene["sceneId"] = "scene-" + str(int(time.time()))
    if "variantId" not in scene:
        scene["variantId"] = "default"
    if "intro" not in scene or not isinstance(scene.get("intro"), dict):
        scene["intro"] = {"narration": "The scene begins."}

    if "nodes" not in scene or not isinstance(scene.get("nodes"), list) or not scene["nodes"]:
        raise ValueError("Model output missing nodes[]. Regenerate.")
    if "endings" not in scene or not isinstance(scene.get("endings"), list) or not scene["endings"]:
        raise ValueError("Model output missing endings[]. Regenerate.")

    # Fix nodes/choices shape
    for n_i, node in enumerate(scene["nodes"]):
        if "nodeId" not in node:
            node["nodeId"] = f"n{n_i}"

        if "narration" not in node:
            node["narration"] = node.get("content") or node.get("text") or "(Missing narration)"

        if "choices" not in node or not isinstance(node.get("choices"), list) or not node["choices"]:
            alt = node.get("options") or []
            node["choices"] = alt if isinstance(alt, list) else []

        fixed_choices: list[dict[str, Any]] = []
        for c_i, c in enumerate(node["choices"]):
            if not isinstance(c, dict):
                continue

            if "choiceId" not in c:
                c["choiceId"] = c.get("id") or f"{node['nodeId']}-{c_i}"
            if "text" not in c:
                c["text"] = c.get("content") or c.get("label") or "Proceed"
            if "to" not in c:
                c["to"] = c.get("nextNodeId") or c.get("toNode") or c.get("target") or "END"

            # Normalize effects dict -> list[str]
            if "effects" in c and isinstance(c["effects"], dict):
                effs: list[str] = []

                stats = c["effects"].get("stats")
                if isinstance(stats, dict):
                    for k, v in stats.items():
                        if isinstance(v, (int, float)):
                            sign = "+" if v >= 0 else ""
                            effs.append(f"stat:{k}{sign}{v}")

                goals = c["effects"].get("goals")
                if isinstance(goals, dict):
                    for gk, gv in goals.items():
                        if isinstance(gv, dict):
                            for kk, vv in gv.items():
                                if isinstance(vv, (int, float)):
                                    sign = "+" if vv >= 0 else ""
                                    effs.append(f"goal:{gk}.{kk}{sign}{vv}")

                facts = c["effects"].get("facts")
                if isinstance(facts, list):
                    for f in facts:
                        if isinstance(f, str) and f.strip():
                            effs.append(f"fact:{_slugify(f)}")

                c["effects"] = effs
            elif "effects" in c and not isinstance(c.get("effects"), list):
                c.pop("effects", None)

            if "guards" in c and not isinstance(c.get("guards"), list):
                c.pop("guards", None)

            fixed_choices.append(
                {
                    "choiceId": str(c["choiceId"]),
                    "text": str(c["text"]),
                    "to": str(c["to"]),
                    **({"guards": c["guards"]} if isinstance(c.get("guards"), list) and c["guards"] else {}),
                    **({"effects": c["effects"]} if isinstance(c.get("effects"), list) and c["effects"] else {}),
                    **({"moveType": c["moveType"]} if "moveType" in c else {}),
                    **({"weight": c["weight"]} if "weight" in c else {}),
                }
            )

        node["choices"] = fixed_choices

    # Fix endings
    for e_i, e in enumerate(scene["endings"]):
        if "endingId" not in e:
            e["endingId"] = e.get("id") or f"end{e_i}"
        if "title" not in e:
            e["title"] = f"Ending {e_i + 1}"
        if e.get("type") not in {"success", "mixed", "failure", "twist"}:
            e["type"] = "mixed"
        if "narration" not in e:
            e["narration"] = "The scene resolves with consequences that set up what happens next."

    return scene

def _infer_ending_type(node_id: str) -> str:
    nid = (node_id or "").lower()
    if "success" in nid or nid.startswith("end_success") or nid.startswith("ending_success"):
        return "success"
    if "fail" in nid or "failure" in nid:
        return "failure"
    if "twist" in nid:
        return "twist"
    if "mixed" in nid:
        return "mixed"
    return "mixed"


def _pretty_title_from_id(node_id: str) -> str:
    # end_success2 -> "Success2" (then spaced)
    s = re.sub(r"^(end|ending)[-_]+", "", node_id.strip(), flags=re.IGNORECASE)
    s = s.replace("-", " ").replace("_", " ").strip()
    if not s:
        return "Ending"
    # simple title case, keep numbers
    return " ".join(w[:1].upper() + w[1:] if w else "" for w in s.split(" "))


def _should_promote_node_to_ending(node: Dict[str, Any], scene: Dict[str, Any]) -> bool:
    """
    Heuristic:
    - nodeId starts with end_/ending_ or contains "end-" style
    OR
    - node has no choices (or empty choices)
    OR
    - ALL choices go to an endingId already (i.e. it's basically a terminal wrapper)
    """
    nid = str(node.get("nodeId", "")).lower().strip()
    if re.match(r"^(end|ending)[-_]", nid):
        return True

    choices = node.get("choices")
    if not choices or not isinstance(choices, list) or len(choices) == 0:
        return True

    # if every choice points to an ending already, treat this as terminal-ish
    endings = scene.get("endings") or []
    ending_ids = {str(e.get("endingId")) for e in endings if isinstance(e, dict) and e.get("endingId")}
    all_to_endings = True
    for c in choices:
        if not isinstance(c, dict):
            continue
        to = str(c.get("to", "")).strip()
        if to and to not in ending_ids:
            all_to_endings = False
            break
    return all_to_endings


def _promote_terminal_nodes_to_endings(scene: Dict[str, Any]) -> Dict[str, Any]:
    """
    Converts 'ending-like' terminal nodes into proper endings so the previewer
    shows the success/failure badge UI.

    - Removes promoted nodes from scene["nodes"]
    - Appends to scene["endings"]
    - Keeps choice.to the same string (endingId == nodeId)
    """
    if not isinstance(scene, dict):
        return scene

    nodes = scene.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        return scene

    if "endings" not in scene or not isinstance(scene.get("endings"), list):
        scene["endings"] = []

    endings = scene["endings"]
    existing_ending_ids = {str(e.get("endingId")) for e in endings if isinstance(e, dict) and e.get("endingId")}

    kept_nodes: list[Dict[str, Any]] = []
    promoted_any = False

    for node in nodes:
        if not isinstance(node, dict):
            continue

        node_id = str(node.get("nodeId", "")).strip()
        if not node_id:
            kept_nodes.append(node)
            continue

        # Don't double-promote if an ending already exists with same id
        if node_id in existing_ending_ids:
            kept_nodes.append(node)
            continue

        if _should_promote_node_to_ending(node, scene):
            promoted_any = True
            end_obj: Dict[str, Any] = {
                "endingId": node_id,
                "title": _pretty_title_from_id(node_id),
                "type": _infer_ending_type(node_id),
                "narration": str(node.get("narration") or node.get("content") or "The story ends here."),
            }
            # keep image if present
            if node.get("image"):
                end_obj["image"] = node["image"]

            # keep weight if present (not required, but harmless)
            if "weight" in node:
                end_obj["weight"] = node["weight"]

            endings.append(end_obj)
            existing_ending_ids.add(node_id)
        else:
            kept_nodes.append(node)

    if promoted_any:
        scene["nodes"] = kept_nodes

    return scene


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate an expanded scene and auto-load it in the previewer")
    ap.add_argument("--brief", required=True, help="Short description of the scene you want")
    ap.add_argument("--variant", default="default", help="Variant id label to embed in output")
    ap.add_argument("--provider", choices=["ollama", "openrouter"], default="ollama")
    ap.add_argument("--out", default=None, help="Optional output path; default is scene-kit/output/<sceneId>.<variant>.json")
    ap.add_argument("--timeout", type=int, default=600, help="HTTP timeout seconds (Ollama can be slow)")
    ap.add_argument("--retries", type=int, default=2)
    ap.add_argument("--serve", action="store_true", help="Start the React previewer and open it in your browser.")
    ap.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("PREVIEWER_PORT", "5173")),
        help="Previewer dev server port (default 5173).",
    )
    args = ap.parse_args()

    schema_text = _read_text(SCHEMA_PATH)
    scene_id = _slugify(args.brief)
    variant_id = args.variant

    system = (
    "You are a JSON generator. Output ONLY valid JSON. "
    "Do not use markdown fences. Do not add commentary. "
    "Do not include // comments or /* */ comments. "
    "Do not include placeholder text like 'More nodes can be added here'. "
    "Return a COMPLETE JSON object."
   )

    user = f"""
Generate a branching interactive scene as JSON that matches this JSON Schema exactly:

{schema_text}

Constraints:
- Use sceneId: "{scene_id}" and variantId: "{variant_id}".
- 6 to 8 nodes.
- Exactly 2 choices per node.
- Each node narration must be 1-3 sentences (longer prose, more detail).
- Every node should include concrete action + environment detail + character intent (no filler).
- Maintain continuity: consequences, discovered facts, and emotional tone should carry forward.
- Use a clear 3-act structure:
  - Act 1  setup, hook, first complication.
  - Act 2  escalation + midpoint reversal 
  - Act 3  climax + resolution.
- Include 2 to 4 endings.
- All choice.to values must point to an existing nodeId OR an endingId.
- Effects may be used but keep them rare and meaningful (aim ~6–10 total across the whole scene).
- Guards may be used but must not soft-lock the story:
  - Never guard BOTH choices in the same node.
  - Only guard ~1 in every 4 nodes at most.
- Effects must be an array of strings using these formats (optional):
  - tag:someTag / tag:!someTag
  - stat:trust+1 / stat:suspicion-2 / stat:leverage+1
  - goal:interrogator.getConfession+1
  - fact:some_fact_key=verified
- Guards must be an array of strings using these formats (optional):
  - tag:someTag or tag:!someTag
  - stat:trust>=2
  - goal:interrogator.getConfession>=1


Scene brief:
Writing style:
- Present tense, immersive.
- Short paragraphs.
- Minimal repetition.
- Make each choice feel emotionally and strategically distinct.
- Prefer dilemmas (risk vs safety, truth vs deception, self vs others).
- Include a short, evocative scene title in a top-level field called "title".
  The title should feel like a real story title, not a summary or prompt.

"{args.brief}"
""".strip()

    raw = _model_call(args.provider, system, user, timeout_s=args.timeout, retries=args.retries)

    def _json_salvage(s: str) -> str:
        # Remove trailing commas before } or ]
        s = re.sub(r",\s*([}\]])", r"\1", s)
        # Strip BOM/odd whitespace
        return (s or "").strip().lstrip("\ufeff")

    last_err: Optional[Exception] = None
    obj: Optional[Dict[str, Any]] = None

    for attempt in range(args.retries + 1):
        raw = _model_call(args.provider, system, user, timeout_s=args.timeout, retries=0)

        try:
            extracted = _extract_first_json(raw)
            extracted = _json_salvage(extracted)
            candidate = json.loads(extracted)

            # Make sure output is usable by previewer/schema shape
            candidate = _validate_or_repair(candidate)

            obj = candidate
            last_err = None
            break

        except Exception as e:
            last_err = e

            # Save raw model output for inspection
            out_dir = os.path.join(os.path.dirname(__file__), "output")
            os.makedirs(out_dir, exist_ok=True)
            bad_path = os.path.join(out_dir, f"BAD_MODEL_OUTPUT_{int(time.time())}_try{attempt}.txt")
            with open(bad_path, "w", encoding="utf-8") as f:
                f.write(raw or "")

            print("Model output was not usable.")
            print(f"Saved raw output to:\n{bad_path}")
            print(f"Error: {e}")

            # On next attempt, slightly simplify the ask (helps Ollama a lot)
            if attempt < args.retries:
                user = user.replace("12 to 22 nodes.", "8 to 14 nodes.")
                user = user.replace("Each node narration must be 2–6 sentences", "Each node narration must be 1–4 sentences")
                time.sleep(1.0)

    if obj is None:
        raise SystemExit(
            "Model did not return usable JSON after retries.\n"
            f"Last error: {last_err}\n"
            "Tip: try a shorter brief, or reduce node count / narration length, or use a larger model."
        )

    # Make sure output is usable by previewer/schema shape
    try:
        obj = _validate_or_repair(obj)
    except Exception as e:
        raise SystemExit(f"Generated JSON shape was not usable: {e}\n\nTip: regenerate with a simpler brief.")
    
    # Auto-promote terminal "end_*" nodes into proper endings so the previewer
    # shows success/failure badges.
    obj = _promote_terminal_nodes_to_endings(obj)

    # FINAL SAFETY PASS: fix bad or unknown choice targets (endings[1], etc.)
    obj = normalize_scene_targets(obj)


    # Write output
    out_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(out_dir, exist_ok=True)
    out_path = args.out or os.path.join(out_dir, f"expanded.{obj['sceneId']}.{obj['variantId']}.json")

    # Ensure the parent directory exists even when --out points elsewhere (e.g., output/runs/...)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


    # Copy to previewer/public/latest.json
    preview_public = os.path.join(ROOT, "previewer", "public")
    os.makedirs(preview_public, exist_ok=True)
    latest_path = os.path.join(preview_public, "latest.json")
    shutil.copyfile(out_path, latest_path)

    print(f"Wrote expanded scene: {out_path}")
    print(f"Updated previewer: {latest_path}")

    if args.serve:
        previewer_dir = os.path.join(ROOT, "previewer")
        if not os.path.exists(os.path.join(previewer_dir, "package.json")):
            raise SystemExit(f"Previewer folder not found at: {previewer_dir}")

        npm_cmd = "npm.cmd" if os.name == "nt" else "npm"
        print("Starting previewer dev server...")
        proc = subprocess.Popen(
            [npm_cmd, "run", "dev", "--", "--port", str(args.port), "--strictPort"],
            cwd=previewer_dir,
        )

        time.sleep(1.2)
        url = f"http://localhost:{args.port}/"
        try:
            webbrowser.open(url)
        except Exception:
            pass

        print(f"Previewer running at: {url}")
        print("Press Ctrl+C to stop the previewer.")

        try:
            return proc.wait()
        except KeyboardInterrupt:
            try:
                proc.terminate()
            except Exception:
                pass
            return 0

    return 0



if __name__ == "__main__":
    raise SystemExit(main())
