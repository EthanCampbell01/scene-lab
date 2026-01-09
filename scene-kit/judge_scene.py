import os, json, argparse, time
from llm_utils import load_prompt_sections, run_llm, parse_json_response

def heuristic_judge(scene: dict) -> dict:
    # simple fallback if no API keys; not used for dissertation-grade scoring but avoids crashes
    num_nodes = len(scene.get('nodes', []))
    avg_choices = (sum(len(n.get('choices', [])) for n in scene.get('nodes', [])) / num_nodes) if num_nodes else 0
    coherence = 3.0 if avg_choices >= 2 else 2.0
    pacing = 3.0
    agency = 2.0 if avg_choices < 2 else 3.5
    interrogation = 3.0
    variant = 3.0
    overall = round((coherence+pacing+agency+interrogation+variant)/5, 1)
    return {
        'scores': {
            'coherence': coherence,
            'pacing': pacing,
            'agency': agency,
            'interrogationRealism': interrogation,
            'variantStrength': variant,
            'overall': overall
        },
        'flags': ['heuristic'],
        'bestMoment': 'N/A (heuristic)',
        'worstMoment': 'N/A (heuristic)',
        'justifications': {}
    }

def main():
    ap = argparse.ArgumentParser(description='Judge an expanded scene with optional LLM scoring')
    ap.add_argument('scene', help='Path to expanded scene JSON')
    ap.add_argument('--out', default='results/judgements.jsonl')
    ap.add_argument('--provider', choices=['openrouter','ollama','none'], default='openrouter')
    ap.add_argument('--prompt', default='prompts/judge_prompt.md')
    ap.add_argument('--temperature', type=float, default=0.2)
    args = ap.parse_args()

    with open(args.scene,'r',encoding='utf-8') as f:
        scene = json.load(f)

    if args.provider == 'none':
        judgement = heuristic_judge(scene)
    else:
        try:
            system, user_t = load_prompt_sections(args.prompt)
            user = user_t.replace('<SCENE_JSON_HERE>', json.dumps(scene, ensure_ascii=False, indent=2))
            resp = run_llm(args.provider, system, user, temperature=args.temperature)
            judgement = parse_json_response(resp)
        except Exception as e:
            print('Judge failed, using heuristic fallback:', e)
            judgement = heuristic_judge(scene)

    record = {
        'sceneId': scene.get('sceneId'),
        'variantId': scene.get('variantId'),
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'judgement': judgement
    }

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out,'a',encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')
    print('Appended to', args.out)

if __name__ == '__main__':
    main()
