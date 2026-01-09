import os, json, argparse, requests, shutil
from copy import deepcopy

AUTO_REPAIR = True          # set False to disable post-process patching
COPY_TO_PREVIEWER = True    # copy final JSON to previewer/public/latest.json for auto-load

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def compile_scene(structure: dict, aesthetics: dict, variant_id: str) -> dict:
    if structure["sceneId"] != aesthetics["sceneId"]:
        raise ValueError("sceneId mismatch between structure and aesthetics")
    variant = next((v for v in aesthetics.get("aestheticVariants", []) if v["variantId"] == variant_id), None)
    if not variant:
        raise ValueError(f"Variant '{variant_id}' not found")
    compiled = deepcopy(structure)
    compiled["aesthetic"] = {
        "variantId": variant["variantId"],
        "label": variant.get("label",""),
        "tone": variant.get("tone", []),
        "genre": variant.get("genre", []),
        "location": variant.get("location", {}),
        "sensoryPalette": variant.get("sensoryPalette", {}),
        "castArchetypes": variant.get("castArchetypes", []),
        "uiPresentation": variant.get("uiPresentation", {}),
        "worldRules": variant.get("worldRules", [])
    }
    hard = variant.get("hardConstraints", {})
    disallowed_endings = set(hard.get("disallowedEndingIds", []))
    disallowed_tags = set(hard.get("disallowedTags", []))
    required_tags_for_options = hard.get("requiredTagsForOptions", {})

    for node in compiled["choiceGraph"]["nodes"]:
        for opt in node["options"]:
            extra = required_tags_for_options.get(opt["optionId"])
            if extra:
                reqs = set(opt.get("requires", [])) | set(extra)
                opt["requires"] = sorted(reqs)

    for node in compiled["choiceGraph"]["nodes"]:
        node["options"] = [opt for opt in node["options"]
                           if not (set(opt.get("tags", [])) & disallowed_tags)]

    kept_endings, removed_endings = [], set()
    for e in compiled["choiceGraph"]["endings"]:
        if e["endingId"] in disallowed_endings:
            removed_endings.add(e["endingId"]); continue
        kept_endings.append(e)
    compiled["choiceGraph"]["endings"] = kept_endings

    for node in compiled["choiceGraph"]["nodes"]:
        node["options"] = [opt for opt in node["options"] if opt["to"] not in removed_endings]

    lm = variant.get("likelihoodModifiers", {})
    by_ending = lm.get("byEndingId", {})
    by_tags = lm.get("byOptionTags", {})
    for e in compiled["choiceGraph"]["endings"]:
        e["weight"] = float(by_ending.get(e["endingId"], 1.0))
    for node in compiled["choiceGraph"]["nodes"]:
        for opt in node["options"]:
            base = opt.get("weights", {}).get("default", 1.0)
            mult = 1.0
            for t in opt.get("tags", []):
                mult *= float(by_tags.get(t, 1.0))
            opt["combinedWeight"] = round(base * mult, 4)
    return compiled

def build_messages(compiled: dict, prompt_path: str):
    with open(prompt_path, "r", encoding="utf-8") as f:
        template = f.read()
    payload = json.dumps(compiled, ensure_ascii=False, indent=2)
    user_content = template.replace("<COMPILED_JSON_HERE>", payload)
    # Extract system section between "## System Role" and "## User Instructions"
    lines = template.splitlines()
    system_start = user_start = None
    for i, ln in enumerate(lines):
        if ln.strip().lower().startswith("## system role"):
            system_start = i+1
        if ln.strip().lower().startswith("## user instructions"):
            user_start = i+1
            break
    system_text = ""
    if system_start is not None and user_start is not None:
        system_text = "\n".join(lines[system_start:user_start-1]).strip()
    else:
        system_text = "You expand scene graphs into VN JSON. Respond with JSON only."
    return system_text, user_content

def call_openrouter(system_text: str, user_text: str) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY env var is required")
    model = os.getenv("OPENROUTER_MODEL", "anthropic/claude-3.5-sonnet")
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://localhost/scene-kit",
        "X-Title": "Scene Kit Expander"
    }
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_text},
            {"role": "user", "content": user_text}
        ],
        "temperature": float(os.getenv("OPENROUTER_TEMPERATURE", "0.7"))
    }
    resp = requests.post(url, headers=headers, json=data, timeout=120)
    resp.raise_for_status()
    out = resp.json()
    return out["choices"][0]["message"]["content"]

def call_ollama(system_text: str, user_text: str) -> str:
    import requests
    model = os.getenv("OLLAMA_MODEL", "mistral:7b-instruct")
    base = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")

    # 1) Try /api/generate (newer API)
    prompt = f"[SYSTEM]\n{system_text}\n[/SYSTEM]\n{user_text}"
    gen_url = f"{base}/api/generate"
    gen_payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))
        }
    }
    try:
        r = requests.post(gen_url, json=gen_payload, timeout=180)
        if r.status_code == 200:
            return r.json().get("response","")
        # If endpoint exists but returns other error, raise so we see it
        if r.status_code != 404:
            r.raise_for_status()
    except requests.RequestException:
        pass  # fall through to /api/chat

    # 2) Fall back to /api/chat (older API)
    chat_url = f"{base}/api/chat"
    chat_payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_text},
            {"role": "user", "content": user_text}
        ],
        "stream": False,
        "options": {
            "temperature": float(os.getenv("OLLAMA_TEMPERATURE", "0.7"))
        }
    }
    r = requests.post(chat_url, json=chat_payload, timeout=180)
    r.raise_for_status()
    data = r.json()
    # Some old servers return {"message":{"content": "..."}}
    msg = data.get("message", {})
    if isinstance(msg, dict) and "content" in msg:
        return msg["content"]
    # Otherwise try a generic field
    return data.get("response","")

def clean_to_json_text(content: str) -> str:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()
    return cleaned

def auto_repair_json(path_data: str, schema_path: str):
    """Load JSON, patch missing fields (endings[].narration minimal), save .patched.json and overwrite original."""
    try:
        import jsonschema
    except Exception:
        jsonschema = None

    with open(path_data, "r", encoding="utf-8") as f:
        data = json.load(f)

    # endings[].narration
    for e in data.get("endings", []):
        if not e.get("narration"):
            title = e.get("title", "Outcome")
            etype = e.get("type", "mixed")
            base = "The scene resolves with consequences that set the next moves."
            e["narration"] = f"{title} ({etype}). {base}"

    # choices[].text and choices[].to
    for n in data.get("nodes", []):
        for c in n.get("choices", []):
            if not c.get("text"):
                c["text"] = "Proceed."
            if "to" not in c:
                c["to"] = data["endings"][0]["endingId"] if data.get("endings") else "END"

    out_patched = path_data.replace(".json", ".patched.json")
    with open(out_patched, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Validate if schema present
    if jsonschema and os.path.exists(schema_path):
        with open(schema_path, "r", encoding="utf-8") as sf:
            schema = json.load(sf)
        jsonschema.Draft202012Validator(schema).validate(data)

    # overwrite original
    shutil.copyfile(out_patched, path_data)

def main():
    ap = argparse.ArgumentParser(description="Compile a scene and expand via OpenRouter or Ollama (with auto-repair)")
    ap.add_argument("--structure", default="scene.structure.json")
    ap.add_argument("--aesthetics", default="scene.aesthetics.json")
    ap.add_argument("--variant", default="cia-safe-house")
    ap.add_argument("--provider", choices=["openrouter","ollama"], default="openrouter")
    ap.add_argument("--prompt", default="prompts/scene_expansion_prompt.md")
    ap.add_argument("--out", default="output/expanded.scene.json")
    args = ap.parse_args()

    structure = load_json(args.structure)
    aesthetics = load_json(args.aesthetics)
    compiled = compile_scene(structure, aesthetics, args.variant)

    system_text, user_text = build_messages(compiled, args.prompt)

    if args.provider == "openrouter":
        content = call_openrouter(system_text, user_text)
    else:
        content = call_ollama(system_text, user_text)

    cleaned = clean_to_json_text(content)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(cleaned)

    if AUTO_REPAIR:
        schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "validator", "schema", "expanded_scene.schema.json")
        try:
            auto_repair_json(args.out, schema_path)
            print("Auto-repair applied (if needed).")
        except Exception as e:
            print("Auto-repair/validate error:", e)

    if COPY_TO_PREVIEWER:
        preview_public = os.path.join(os.path.dirname(os.path.dirname(__file__)), "previewer", "public")
        os.makedirs(preview_public, exist_ok=True)
        shutil.copyfile(args.out, os.path.join(preview_public, "latest.json"))
        print("Copied to previewer/public/latest.json")

    print(f"Wrote {args.out}")

if __name__ == "__main__":
    main()
