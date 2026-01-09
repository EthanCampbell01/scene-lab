import os, json, argparse
from llm_utils import load_prompt_sections, run_llm, parse_json_response

def main():
    ap = argparse.ArgumentParser(description='Create a structure graph by branching a linear expanded scene')
    ap.add_argument('--linear', required=True, help='Path to expanded linear scene JSON')
    ap.add_argument('--out', default='output/scene.structure.branched.json')
    ap.add_argument('--provider', choices=['openrouter','ollama'], default='openrouter')
    ap.add_argument('--prompt', default='prompts/branch_from_linear_prompt.md')
    ap.add_argument('--temperature', type=float, default=0.4)
    args = ap.parse_args()

    with open(args.linear,'r',encoding='utf-8') as f:
        linear = json.load(f)

    system, user_t = load_prompt_sections(args.prompt)
    user = user_t.replace('<LINEAR_JSON_HERE>', json.dumps(linear, ensure_ascii=False, indent=2))

    resp = run_llm(args.provider, system, user, temperature=args.temperature)
    structure = parse_json_response(resp)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out,'w',encoding='utf-8') as f:
        json.dump(structure, f, ensure_ascii=False, indent=2)
    print('Wrote', args.out)

if __name__ == '__main__':
    main()
