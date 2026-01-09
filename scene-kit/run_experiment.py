import os, json, argparse, subprocess, uuid, time, glob
ROOT = os.path.dirname(os.path.dirname(__file__))
SCENEKIT = os.path.join(ROOT, 'scene-kit')

def run(cmd):
    subprocess.check_call(cmd)

def main():
    ap = argparse.ArgumentParser(description='Run generation experiments across pipelines/variants and optionally judge results')
    ap.add_argument('--brief', required=True, help='High-level scenario brief')
    ap.add_argument('--variants', nargs='*', default=['cia-safe-house'], help='Variant IDs to generate')
    ap.add_argument('--n', type=int, default=5, help='Number of runs per variant per pipeline')
    ap.add_argument('--pipelines', nargs='*', default=['topDown','bottomUp'], choices=['topDown','bottomUp'])
    ap.add_argument('--provider', choices=['openrouter','ollama'], default='openrouter')
    ap.add_argument('--judge', action='store_true', help='If set, run judge_scene.py on each generated expanded scene')
    args = ap.parse_args()

    results_dir = os.path.join(SCENEKIT, 'results')
    os.makedirs(results_dir, exist_ok=True)
    manifest_path = os.path.join(results_dir, 'manifest.jsonl')

    for pipeline in args.pipelines:
        for variant in args.variants:
            for i in range(args.n):
                run_id = uuid.uuid4().hex[:8]
                if pipeline == 'topDown':
                    # gen_scene creates structure+aesthetics then expand (writes output/expanded.<sceneId>.<variant>.json)
                    run(['python', os.path.join(SCENEKIT,'gen_scene.py'),
                         '--brief', args.brief, '--variant', variant, '--provider', args.provider])
                    # pick latest expanded file
                    outs = sorted(glob.glob(os.path.join(SCENEKIT,'output','expanded.*.%s.json' % variant)), key=os.path.getmtime)
                    out_scene = outs[-1] if outs else None
                else:
                    # bottomUp: create linear expanded, branch to structure, then expand with aesthetics
                    linear_out = os.path.join(SCENEKIT,'output', f'linear.{run_id}.json')
                    # build linear via expand-like LLM call using prompt
                    from llm_utils import load_prompt_sections, run_llm, parse_json_response
                    p = os.path.join(SCENEKIT,'prompts','linear_scene_prompt.md')
                    system, user_t = load_prompt_sections(p)
                    user = user_t.replace('<BRIEF_HERE>', args.brief)
                    resp = run_llm(args.provider, system, user, temperature=0.5)
                    linear_scene = parse_json_response(resp)
                    with open(linear_out,'w',encoding='utf-8') as f:
                        json.dump(linear_scene, f, ensure_ascii=False, indent=2)

                    branched_struct = os.path.join(SCENEKIT,'output', f'structure.{run_id}.json')
                    run(['python', os.path.join(SCENEKIT,'branch_scene.py'),
                         '--linear', linear_out, '--out', branched_struct, '--provider', args.provider])
                    # use existing aesthetics from scene-kit/scene.aesthetics.json (user can swap)
                    run(['python', os.path.join(SCENEKIT,'expand.py'),
                         '--structure', branched_struct,
                         '--aesthetics', os.path.join(SCENEKIT,'scene.aesthetics.json'),
                         '--variant', variant,
                         '--provider', args.provider,
                         '--out', os.path.join(SCENEKIT,'output', f'expanded.bottomUp.{run_id}.{variant}.json')])
                    out_scene = os.path.join(SCENEKIT,'output', f'expanded.bottomUp.{run_id}.{variant}.json')

                if not out_scene or not os.path.exists(out_scene):
                    print('No output scene found for', pipeline, variant)
                    continue

                rec = {
                    'runId': run_id,
                    'pipeline': pipeline,
                    'variantId': variant,
                    'outScene': os.path.relpath(out_scene, ROOT),
                    'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
                }
                with open(manifest_path,'a',encoding='utf-8') as mf:
                    mf.write(json.dumps(rec, ensure_ascii=False)+'\n')

                if args.judge:
                    run(['python', os.path.join(SCENEKIT,'judge_scene.py'), out_scene, '--provider', args.provider])

    print('Wrote manifest:', manifest_path)

if __name__ == '__main__':
    main()
