# Scene Kit: One-command Expanded Scene Generator

The recommended way to use this project now is **one command** that:

1. Generates a valid **expanded scene JSON** (matching `validator/schema/expanded_scene.schema.json`)
2. Writes it to `scene-kit/output/`
3. Automatically copies it to `previewer/public/latest.json` so the React previewer auto-loads it.

## ✅ Quick start (new)

From `scene-lab/scene-kit`:

```bash
python pipeline.py --brief "You have been kidnapped and are held in a warehouse..." --variant cia-safe-house --provider ollama
```

Then (in another terminal) run the previewer:

```bash
cd ../previewer
npm install
npm run dev
```

Open the shown URL; it will auto-load `latest.json`.

---

# Legacy workflow (structure → aesthetics → expand)

This kit turns a **high-level scene structure** + **aesthetic variant** into a **detailed visual-novel / CYOA JSON** using either **OpenRouter** or **Ollama**.

## Contents
- `scene.structure.json` — abstract logic (beats, nodes, options, endings)
- `scene.aesthetics.json` — settings/tones/constraints/likelihoods
- `prompts/scene_expansion_prompt.md` — provider-agnostic expansion prompt
- `expand.py` — compiles + calls LLM (OpenRouter or Ollama)
- `output/expanded.scene.json` — generated detailed VN JSON (after running)
- Example compiled file from earlier: `compiled.interrogation.cia-safe-house.json`

## 1) Python Setup
```bash
cd scene-kit
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 2) Choose Your Provider

### A) OpenRouter (cloud)
1. Create an API key at OpenRouter and keep it handy.
2. Export env vars:
   ```bash
   export OPENROUTER_API_KEY="YOUR_KEY"
   export OPENROUTER_MODEL="anthropic/claude-3.5-sonnet"   # or any supported model
   export OPENROUTER_TEMPERATURE=0.7
   ```

### B) Ollama (local)
1. Install Ollama and pull a model, e.g.:
   ```bash
   ollama pull llama3.1:8b-instruct
   ```
2. Export env vars (optional):
   ```bash
   export OLLAMA_MODEL="llama3.1:8b-instruct"
   export OLLAMA_URL="http://localhost:11434/api/generate"
   export OLLAMA_TEMPERATURE=0.7
   ```

## 3) Compile + Expand

You can expand *any* variant defined in `scene.aesthetics.json`. The default below uses **CIA Safe House**:

### OpenRouter
```bash
python expand.py --provider openrouter   --structure scene.structure.json   --aesthetics scene.aesthetics.json   --variant cia-safe-house   --prompt prompts/scene_expansion_prompt.md   --out output/expanded.scene.json
```

### Ollama
```bash
python expand.py --provider ollama   --structure scene.structure.json   --aesthetics scene.aesthetics.json   --variant cia-safe-house   --prompt prompts/scene_expansion_prompt.md   --out output/expanded.scene.json
```

The script:
- **Merges** structure + aesthetic (applying hard constraints and likelihood modifiers).
- **Builds** a clean system+user prompt by inlining the compiled JSON.
- **Calls** your chosen provider.
- **Writes** raw JSON to `output/expanded.scene.json` (no markdown).

## 4) Output Schema (target)
The LLM is instructed to return this structure:
```json
{
  "sceneId": "string",
  "variantId": "string",
  "intro": { "narration": "3–6 sentences" },
  "nodes": [
    {
      "nodeId": "string",
      "narration": "3–6 sentences",
      "choices": [
        {
          "choiceId": "string",
          "text": "1–2 sentences of player-facing text",
          "guards": ["state.tag"],
          "effects": ["state.tag", "subject.trust+1"],
          "to": "nodeId or endingId"
        }
      ]
    }
  ],
  "endings": [
    {
      "endingId": "string",
      "title": "string",
      "type": "success|mixed|failure|twist",
      "narration": "2–5 sentences"
    }
  ],
  "uiHints": ["..."],
  "themeSignals": ["..."]
}
```

## 5) Swap in Different Aesthetics
Update `--variant` to one of:
- `family-dinner`
- `cia-safe-house`
- `congress-hearing`
- `speed-date`

You can add more variants to `scene.aesthetics.json`. Constraints/likelihoods are applied automatically.

## 6) Add Your Own Scenes
Replace `scene.structure.json` with your new scene in the same schema. Reuse the aesthetics file (or create a new one) and run the same command.

## 7) Troubleshooting
- If the model responds with Markdown fences, the script strips them and saves raw JSON.
- If output isn't valid JSON, re-run with a different model or slightly lower temperature.
- For OpenRouter rate limits or model errors, set a different `OPENROUTER_MODEL`.

## 8) Next Steps (optional)
- Add a `validator` to enforce the target schema with Pydantic or JSON Schema.
- Chain multiple compiled scenes into a larger episode by carrying `stateResults` forward.
- Harvest great examples from films/TV/games and encode their **structure** separate from **aesthetic skins** to train consistent tension arcs.


---

## Validator
```bash
pip install -r requirements.txt
python tools/validate.py --file output/expanded.scene.json
```

## Batch Generation
```bash
python tools/batch_expand.py --provider openrouter --variants cia-safe-house speed-date
```

## Web Previewer (static)
Open `web-preview/index.html` in your browser and load a generated JSON via the file picker.
No server or build step needed.


# AI Branching Storytelling – Quick Usage Guide

This project now uses a **single-command pipeline** to generate scenes and automatically load them into the previewer.
You no longer need to rename files, move JSON manually, or debug schema mismatches.

---

## What This System Does (In Plain English)

When you generate a scene, the system will:

1. Ask the AI to generate a scene
2. Automatically clean and fix the JSON
3. Convert it into the format the previewer expects
4. Save it internally (for your records)
5. Copy it to the previewer as `latest.json`
6. (Optionally) start the previewer and open your browser

All of this happens automatically.

---

## One-Command Workflow (Recommended)

### From the `scene-lab` folder, run:

```powershell
.\run.ps1 -Brief "You have been kidnapped and must escape a warehouse" -Variant "cia-safe-house" -Provider "ollama"
```

That’s it.

What happens:
- A new scene is generated
- The previewer is launched
- Your browser opens automatically
- The scene is playable immediately

---

## What the Arguments Mean

### `-Brief`
A short description of the scene you want.
This is what the AI uses to generate the story.

Example:
```text
A tense interrogation where the suspect secretly holds power
```

### `-Variant`
The aesthetic or tone variant for the scene.

Examples:
```text
cia-safe-house
police-interrogation
corporate-blackmail
```

### `-Provider`
Which AI backend to use.

Options:
- `ollama` (local, slower, free)
- `openrouter` (cloud, faster, requires API key)

---

## If You Do NOT Want to Launch the Previewer

You can generate scenes without opening the browser:

```powershell
cd scene-lab\scene-kit
python .\pipeline.py --brief "..." --variant "cia-safe-house" --provider ollama
```

The scene will still be generated and copied to:
```
scene-lab/previewer/public/latest.json
```

You can open the previewer later with:

```powershell
cd scene-lab/previewer
npm run dev
```

---

## Where Scenes Are Stored

Every generated scene is saved here:

```
scene-lab/scenes/<scene-name>/
```

Inside each folder:
- `structure.json` – internal planning structure
- `aesthetics.json` – tone/style information
- `expanded.json` – final playable scene
- `raw_model_output.json` – original AI output (for debugging)

You do NOT need to edit these manually.

---

## Common Questions

### “Why is my preview blank?”
This should no longer happen.
If it does:
- The pipeline will print a clear error
- The previewer will show a message instead of failing silently

### “Can I keep old scenes?”
Yes. Every run creates a new scene folder.
Nothing is overwritten except `latest.json` (by design).

### “Can I add images later?”
Yes. The scene format already supports optional image fields.
You can add these manually or extend the generator later.

---

## The One Rule

**Never manually edit or move `latest.json`.**  
Always generate scenes through the pipeline.

---

If something goes wrong, check the terminal output first — errors are now designed to be human-readable.
