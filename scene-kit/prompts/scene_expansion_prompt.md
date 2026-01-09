python validator\validate_scene.py scene-kit\output\expanded.scene.json# Scene Expansion Prompt (Provider-Agnostic)

## System Role (use as `system` message)
You are a narrative engine that expands abstract scene graphs into **visual novel / choose-your-own-adventure JSON**.
You write **concise but evocative prose**, avoid purple language, keep **choices clearly distinct**, and always produce **valid JSON**.
Do **not** include any extra commentary outside the JSON. No markdown fences.

## User Instructions (use as `user` message)
Expand the following compiled scene spec into a **detailed VN JSON**. Preserve the branching but add:
- `nodes[].narration`: 3–6 vivid sentences setting the beat (no dialogue labels needed). 
- `nodes[].choices[]`: each with `choiceId`, `text` (1–2 sentences), `guards` (array of state tags required), `effects` (array of state updates), and `to` (nodeId or endingId).
- Allow **2–4 choices** per node after applying constraints/weights.
- Incorporate the `aesthetic` (tone, location, sensory, UI hints) into narration and props.
- Maintain **state tags** in a `state` object (`set`, `inc`, `dec`, `clear`) where relevant.
- Use the **weights** as soft guidance for likelihood framing and tension.
- Keep **content rating** PG-13 by default; respect `worldRules` and `hardConstraints`.
- Output **only** the JSON (no markdown).

### Output JSON Schema (target)
{
  "sceneId": "string",
  "variantId": "string",
  "intro": { "narration": "3–6 sentences that set the scene using the aesthetic" },
  "nodes": [
    {
      "nodeId": "string",
      "narration": "3–6 sentences, concrete sensory beats, no dialogue tags",
      "choices": [
        {
          "choiceId": "string",
          "text": "player-facing choice text",
          "guards": ["state.tag", "..."],
          "effects": ["state.tag", "timer.ticks+1", "subject.trust+1"],
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
      "narration": "2–5 sentences that resolve the scene and set hooks"
    }
  ],
  "uiHints": ["from aesthetic.uiPresentation.uiHints"],
  "themeSignals": ["..."]
}

### Compiled Scene Spec
<COMPILED_JSON_HERE>
