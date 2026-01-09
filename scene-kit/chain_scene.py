import os, json, argparse, shutil, subprocess, tempfile
from llm_utils import load_prompt_sections, run_llm, parse_json_response

ROOT = os.path.dirname(os.path.dirname(__file__))

def main():
    ap = argparse.ArgumentParser(description='Generate a follow-on scene brief from a previous scene summary and optionally generate the next scene')
    ap.add_argument('--summary', required=True, help='Path to a text file containing previous ending/summary')
    ap.add_argument('--provider', choices=['openrouter','ollama'], default='openrouter')
    ap.add_argument('--prompt', default='prompts/chain_prompt.md')
    ap.add_argument('--temperature', type=float, default=0.3)
    ap.add_argument('--generate', action='store_true', help='If set, call gen_scene.py using the produced brief')
    ap.add_argument('--variant', default='cia-safe-house')
    args = ap.parse_args()

    with open(args.summary,'r',encoding='utf-8') as f:
        prev = f.read().strip()

    system, user_t = load_prompt_sections(args.prompt)
    user = user_t.replace('<PREV_SUMMARY_HERE>', prev)
    resp = run_llm(args.provider, system, user, temperature=args.temperature)
    plan = parse_json_response(resp)

    out_plan = os.path.join(ROOT, 'scene-kit', 'output', 'next_scene_plan.json')
    os.makedirs(os.path.dirname(out_plan), exist_ok=True)
    with open(out_plan,'w',encoding='utf-8') as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    print('Wrote', out_plan)

    if args.generate:
        brief = plan.get('brief','').strip()
        if not brief:
            raise RuntimeError('No brief produced')
        # call gen_scene.py
        gen = os.path.join(ROOT, 'scene-kit', 'gen_scene.py')
        subprocess.check_call(['python', gen, '--brief', brief, '--variant', args.variant, '--provider', args.provider])
        print('Generated next scene via gen_scene.py')

if __name__ == '__main__':
    main()
