def build_prompts(schema_text, scene_id, variant_id, brief):

    system = (
        "You are a creative writer generating branching narrative JSON."
        "Output only valid JSON."
    )

    user = f"""
Generate a branching narrative scene.

Schema:
{schema_text}

Constraints:
- sceneId: "{scene_id}"
- variantId: "{variant_id}"
- 6–12 nodes
- 2–3 choices per node
- 2–5 endings

Writing style:
- immersive narration
- distinct character voices
- varied tone
- allow unexpected twists

Scene brief:
"{brief}"
"""

    return system, user