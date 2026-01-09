
import os, json, argparse, datetime, requests, textwrap

def build_prompt(question: str, template_path: str):
    with open(template_path, "r", encoding="utf-8") as f:
        tpl = f.read()
    return tpl.replace("<RESEARCH_QUESTION_HERE>", question)

def call_openrouter(prompt: str) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return "[OpenRouter] Set OPENROUTER_API_KEY to query. Prompt was:\n" + prompt
    model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://localhost/scene-lab",
        "X-Title": "Scene Lab Deep Research"
    }
    data = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a meticulous technical researcher."},
            {"role": "user", "content": prompt}
        ],
        "temperature": float(os.getenv("OPENROUTER_TEMPERATURE","0.3"))
    }
    r = requests.post(url, headers=headers, json=data, timeout=120)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def call_gemini(prompt: str) -> str:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return "[Gemini] Set GOOGLE_API_KEY to query. Prompt was:\n" + prompt
    # Gemini 1.5 via REST (text-only prompt wrapped as contents)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = {"contents":[{"parts":[{"text": prompt}]}]}
    r = requests.post(url, json=payload, timeout=120)
    r.raise_for_status()
    data = r.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return json.dumps(data, ensure_ascii=False, indent=2)

def main():
    ap = argparse.ArgumentParser(description="Run deep research on ChatGPT (via OpenRouter) and Gemini")
    ap.add_argument("question", help="The research question/task to investigate")
    ap.add_argument("--template", default="prompt-lab/deep_research_prompt.md")
    ap.add_argument("--outdir", default="prompt-lab/research_logs")
    args = ap.parse_args()

    prompt = build_prompt(args.question, args.template)

    or_text = call_openrouter(prompt)
    gm_text = call_gemini(prompt)

    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    base = os.path.join(args.outdir, f"research-{ts}")
    os.makedirs(base, exist_ok=True)

    with open(os.path.join(base, "question.txt"), "w", encoding="utf-8") as f:
        f.write(args.question)
    with open(os.path.join(base, "openrouter.md"), "w", encoding="utf-8") as f:
        f.write(or_text)
    with open(os.path.join(base, "gemini.md"), "w", encoding="utf-8") as f:
        f.write(gm_text)

    print("Saved research to", base)

if __name__ == "__main__":
    main()
