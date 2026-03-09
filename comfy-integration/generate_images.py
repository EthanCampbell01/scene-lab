
import os, json, argparse, requests

def load_scene(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_scene(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def generate_image_for_node(server, prompt, out_path):
    """
    Minimal ComfyUI call.
    Assumes a simple workflow endpoint that accepts a 'prompt' field.
    Many YouTube tutorials define a custom workflow; adapt the payload accordingly.
    """
    payload = {"prompt": prompt}
    r = requests.post(f"{server}/prompt", json=payload, timeout=120)
    r.raise_for_status()
    # In many setups, ComfyUI returns an image URL or you must poll for result.
    # Here we expect raw bytes for simplicity.
    content_type = r.headers.get("content-type","")
    if "image" in content_type or r.content[:4] == b'\x89PNG':
        with open(out_path, "wb") as f:
            f.write(r.content)
        return True
    else:
        # If server returns JSON with a URL, adapt here
        try:
            data = r.json()
            # TODO: handle actual ComfyUI job + result polling
            # For now we just save the response for inspection.
            with open(out_path.replace(".png",".json"), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return False
        except Exception:
            with open(out_path.replace(".png",".txt"), "wb") as f:
                f.write(r.content)
            return False

def main():
    ap = argparse.ArgumentParser(description="Attach images to nodes via ComfyUI + Qwen Image Edit")
    ap.add_argument("--scene", required=True, help="Expanded scene JSON path")
    ap.add_argument("--server", default="http://127.0.0.1:8188")
    ap.add_argument("--outdir", default="images")
    args = ap.parse_args()

    scene = load_scene(args.scene)
    scene_id = scene.get("sceneId","scene")
    variant = scene.get("variantId","variant")
    base = os.path.join(args.outdir, f"{scene_id}", f"{variant}")
    os.makedirs(base, exist_ok=True)

    for node in scene.get("nodes", []):
        nid = node["nodeId"]
        prompt = f"{scene_id} / {variant} — Generate an illustrative image for this node. Tone: {', '.join(scene.get('uiHints', []) if scene.get('uiHints') else [])}. Narration: {node['narration']}"
        out_path = os.path.join(base, f"{nid}.png")
        ok = generate_image_for_node(args.server, prompt, out_path)
        if ok:
            node["image"] = out_path.replace("\\\\","/")
    # Endings optional images
    for end in scene.get("endings", []):
        pass

    # Save updated scene with image paths
    save_scene(args.scene, scene)
    print("Updated scene with image paths (where generated):", args.scene)

if __name__ == "__main__":
    main()
