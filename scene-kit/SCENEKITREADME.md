# Scene Kit  
**One-Command AI Scene Generator for Branching Narratives**

Scene Kit is a Python-based tool that generates **fully playable branching story scenes** using a single command.  
Each generated scene is **schema-valid**, **auto-copied into the React previewer**, and immediately playable.

This tool was built as part of an experimental final-year project exploring **AI-assisted narrative generation**, **tooling reliability**, and **human-in-the-loop authoring**.

---

## What Scene Kit Does

When you run the pipeline, Scene Kit will:

1. Prompt an AI model (local or cloud) with a short story brief
2. Generate a structured branching narrative
3. Validate and repair the model output
4. Ensure it matches the required JSON schema
5. Save the result to disk for inspection
6. Automatically copy it to the previewer as `latest.json`

No manual file moving or renaming is required.

---

## Recommended Usage (Current Workflow)

### From `scene-lab/scene-kit`:

```bash
python pipeline.py --brief "You have been kidnapped and must escape a warehouse" --variant cia-safe-house --provider ollama
```

That single command will:
- Generate a complete scene
- Validate it
- Copy it to `previewer/public/latest.json`

The React previewer will auto-load the result.

---

## Running the Previewer

In a separate terminal:

```bash
cd ../previewer
npm install
npm run dev
```

Open the URL shown in the terminal.  
The latest generated scene will load automatically.

---

## Command Arguments

### `--brief`
A short natural-language description of the scene you want.

Example:
```
"A tense interrogation where the suspect may secretly be in control"
```

This is **intentionally high-level** — the system handles structure and detail.

---

### `--variant`
Controls the *tone and aesthetic constraints* applied to the scene.

Current examples:
- `cia-safe-house`
- `spooky-campsite`
- `luxurious-mansion`

Variants are used to test how different narrative “skins” affect generated output.

---

### `--provider`
Selects the AI backend.

Options:
- `ollama` — local, slower, free
- `openrouter` — cloud, faster, requires API key

---

## Output Locations

Each pipeline run produces files in two places:

### 1. Archive Output
```
scene-kit/output/
```

Contains:
- `expanded.scene.json` — validated playable scene
- `raw_model_output.json` — original AI response (for debugging)

These files are kept intentionally to support **experimentation and failure analysis**.

---

### 2. Previewer Target
```
previewer/public/latest.json
```

This file is **always overwritten** with the most recent scene and should **never be edited manually**.

---

## Scene Format (High Level)

The generated scene conforms to a strict schema and includes:

- Scene metadata
- Intro narration
- Multiple nodes with choices
- Guards (optional requirements)
- Effects (state changes)
- Structured endings (success / failure / mixed / twist)

The schema exists to prevent invalid AI output from breaking the UI.

---

## Validation and Error Handling

This project intentionally treats AI output as **untrusted**.

The pipeline:
- Strips markdown fences
- Repairs common formatting errors
- Validates structure before writing files
- Fails safely with readable error messages

Invalid scenes are never passed to the previewer.

---

## Why This Tool Exists

This project is **not** about perfect prose.

It is an experiment in:
- AI reliability
- Structured prompting
- Schema enforcement
- Tooling around unpredictable model behaviour
- Bridging creative systems with traditional software engineering

Many design decisions prioritise **robustness and debuggability** over elegance.

---

## Known Limitations

- AI output quality varies by model and temperature
- Long or complex briefs increase failure likelihood
- Guards and effects can occasionally over-constrain scenes
- This is a research prototype, not a production authoring tool

These limitations are intentional discussion points for evaluation.

---

## Key Rule

**Do not manually edit `latest.json`.**  
Always generate scenes through the pipeline.

---

If something goes wrong:
- Check the terminal output
- Inspect `raw_model_output.json`
- Re-run with a simpler brief or lower temperature
