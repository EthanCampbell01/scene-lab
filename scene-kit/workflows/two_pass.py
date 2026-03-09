import json
from pipeline import _model_call


def run_two_pass(provider, schema_text, scene_id, variant_id, brief, timeout, retries):

    # PASS 1: outline

    system = "You are a narrative planner."

    user = f"""
Create an outline for a branching narrative.

Return JSON with:
- title
- characters
- setting
- beats (6 items)
- endings (3 items)

Scene brief:
{brief}
"""

    outline_raw = _model_call(provider, system, user, timeout_s=timeout, retries=retries)

    outline = json.loads(outline_raw)

    # PASS 2: expand

    system2 = (
        "You are a narrative generator producing valid JSON scenes."
        "Return only JSON."
    )

    user2 = f"""
Use this outline to generate a branching scene.

Outline:
{json.dumps(outline)}

Schema:
{schema_text}

Constraints:
- sceneId: "{scene_id}"
- variantId: "{variant_id}"
- 6–10 nodes
- 2 choices per node
- 2–4 endings
"""

    return _model_call(provider, system2, user2, timeout_s=timeout, retries=retries)