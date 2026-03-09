def build_prompts(schema_text, scene_id, variant_id, brief):

    system = (
        "You are a JSON generator. Output ONLY valid JSON. "
        "Do not use markdown fences. Do not add commentary."
    )

    user = f"""
Generate a branching interactive scene as JSON matching this schema:

{schema_text}

Constraints:
- sceneId: "{scene_id}"
- variantId: "{variant_id}"
- 6–8 nodes
- exactly 2 choices per node
- 2–4 endings
- narration: 1–3 sentences
- strong 3-act narrative structure

Scene brief:
"{brief}"
"""

    return system, user