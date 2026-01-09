import json, argparse, shutil, os

def load_json(p):
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    ap = argparse.ArgumentParser(description="Backfill endings[].narration if missing")
    ap.add_argument("expanded_path", help="Path to expanded.scene.json (output from expand.py)")
    ap.add_argument("--structure", default="scene-kit/scene.structure.json", help="Path to scene structure (to borrow ending summaries)")
    ap.add_argument("--inplace", action="store_true", help="Write back into the same file")
    ap.add_argument("--out", default=None, help="Output path if not --inplace")
    args = ap.parse_args()

    data = load_json(args.expanded_path)
    struct = load_json(args.structure)

    # Build map endingId -> summary (from structure)
    summary_by_eid = {}
    for e in struct.get("choiceGraph", {}).get("endings", []):
        summary_by_eid[e["endingId"]] = e.get("summary", "")

    changed = False
    for e in data.get("endings", []):
        if not e.get("narration"):
            # Synthesize a 2–4 sentence narration from title/type/summary
            title = e.get("title", "Outcome")
            etype = e.get("type", "mixed")
            base = summary_by_eid.get(e.get("endingId",""), "").strip()
            parts = []
            parts.append(f"{title} ({etype}).")
            if base:
                parts.append(base)
            else:
                parts.append("The scene resolves with clear consequences that reframe the next steps.")
            parts.append("Threads from this encounter carry forward as new flags and pressures.")
            e["narration"] = " ".join(parts)
            changed = True

    if not changed:
        print("No changes needed; all endings already have narration.")
        return

    # Decide where to write
    out_path = args.expanded_path if args.inplace else (args.out or args.expanded_path.replace(".json", ".patched.json"))

    # Make a safety backup if writing in place
    if args.inplace:
        bak = out_path + ".bak"
        shutil.copyfile(args.expanded_path, bak)
        print("Backup created:", bak)

    # Write
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("Wrote:", out_path)

if __name__ == "__main__":
    main()
