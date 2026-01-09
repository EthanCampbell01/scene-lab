# Scene Lab — CYOA / Visual Novel Workspace

This repo contains everything you need to:
- Define **scene structures** and **aesthetic variants**
- Compile + expand into detailed **visual novel JSON** (local **Ollama** or cloud **OpenRouter**)
- **Validate** the result with JSON Schema
- **Preview** interactively in a React app
- Optionally generate **images** via **ComfyUI + Qwen Image Edit**
- Run **deep research** queries on ChatGPT (via OpenRouter) and Gemini

## Layout
- `scene-kit/` — core scene engine (+ prompt + expansion script)
- `validator/` — JSON schema and validator
- `previewer/` — React app to click through your scene
- `batch-tools/` — scripts to mass-generate across variants
- `prompt-lab/` — deep research prompt + runner (ChatGPT/Gemini)
- `comfy-integration/` — ComfyUI/Qwen image generator stub

See per-folder READMEs and comments for usage.

# Scene-Lab (Final Year Project)

## Aim
A pipeline + previewer for generating and playing branching “visual novel” scenes as JSON.

## What’s in this repo
- `scene-lab/scene-kit/` – Python pipeline that generates expanded scene JSON and publishes `latest.json`
- `scene-lab/previewer/` – React/Vite previewer that auto-loads `public/latest.json`
- `scene-lab/validator/` – JSON schema / validation assets
- `scene-lab/prompt-lab/` – prompt iteration and research logs (experiment notes)

## How to run (Previewer)
```bash
cd scene-lab/previewer
npm install
npm run dev

cd scene-lab/scene-kit
python pipeline.py --provider ollama --brief "..." --variant "..." --serve
