import os, json, argparse, subprocess, sys

def run(cmd):
    print('> ' + ' '.join(cmd))
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    print(res.stdout)
    if res.returncode != 0:
        raise SystemExit(res.returncode)

def main():
    ap = argparse.ArgumentParser(description='Batch expand scenes for multiple variants and providers')
    ap.add_argument('--variants', nargs='*', default=['family-dinner','cia-safe-house','congress-hearing','speed-date'])
    ap.add_argument('--provider', choices=['openrouter','ollama'], default='openrouter')
    ap.add_argument('--structure', default='scene.structure.json')
    ap.add_argument('--aesthetics', default='scene.aesthetics.json')
    ap.add_argument('--prompt', default='prompts/scene_expansion_prompt.md')
    ap.add_argument('--outdir', default='output/batch')
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    for v in args.variants:
        out_path = os.path.join(args.outdir, f'expanded.{v}.json')
        cmd = [
            sys.executable, 'expand.py',
            '--provider', args.provider,
            '--structure', args.structure,
            '--aesthetics', args.aesthetics,
            '--variant', v,
            '--prompt', args.prompt,
            '--out', out_path
        ]
        run(cmd)
    print('Batch complete.')

if __name__ == '__main__':
    main()
