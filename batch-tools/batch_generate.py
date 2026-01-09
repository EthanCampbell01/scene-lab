
import argparse, os, subprocess, sys, json, shlex

def run(cmd):
    print(">", cmd)
    res = subprocess.run(cmd, shell=True)
    if res.returncode != 0:
        sys.exit(res.returncode)

def main():
    ap = argparse.ArgumentParser(description="Batch-generate expanded scenes for multiple variants")
    ap.add_argument("--variants", nargs="+", required=True, help="Variant IDs to generate")
    ap.add_argument("--provider", choices=["openrouter","ollama"], default="ollama")
    ap.add_argument("--structure", default="scene-kit/scene.structure.json")
    ap.add_argument("--aesthetics", default="scene-kit/scene.aesthetics.json")
    ap.add_argument("--prompt", default="scene-kit/prompts/scene_expansion_prompt.md")
    ap.add_argument("--outdir", default="scene-kit/output/batch")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    for v in args.variants:
        out = os.path.join(args.outdir, f"expanded.{v}.json")
        cmd = f'python scene-kit/expand.py --provider {args.provider} --structure {args.structure} --aesthetics {args.aesthetics} --variant {v} --prompt {args.prompt} --out {out}'
        run(cmd)
    print("Batch done. Files in", args.outdir)

if __name__ == "__main__":
    main()
