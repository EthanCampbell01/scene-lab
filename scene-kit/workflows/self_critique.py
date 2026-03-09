import json

from experiments.critic import evaluate_narrative
from workflows.robust import build_prompts as robust_prompts


def run_self_critique(provider, schema_text, scene_id, variant_id, brief, timeout, retries, model_call):
    # ---------------------------------
    # PASS 1: Generate initial draft
    # ---------------------------------
    system, user = robust_prompts(
        schema_text=schema_text,
        scene_id=scene_id,
        variant_id=variant_id,
        brief=brief,
    )

    raw_draft = model_call(provider, system, user, timeout_s=timeout, retries=retries)

    # Parse JSON now so critic can inspect it
    try:
        draft_obj = json.loads(raw_draft)
    except Exception:
        # Let pipeline salvage/extract later if needed
        draft_obj = None

    # ---------------------------------
    # PASS 2: Critic evaluation
    # ---------------------------------
    critic = None
    if isinstance(draft_obj, dict):
        try:
            critic = evaluate_narrative(draft_obj)
        except Exception:
            critic = None

    # ---------------------------------
    # PASS 3: Revision pass
    # ---------------------------------
    revision_system = (
        "You are a JSON scene reviser. "
        "Return ONLY valid JSON. Do not use markdown. "
        "Preserve the branching scene structure while improving narrative quality."
    )

    revision_user = f"""
You are revising a branching narrative scene.

Your job is to improve:
- dialogue naturalness
- emotional coherence
- character consistency
- dramatic tension
- originality of phrasing
- distinction between choices

Do NOT break schema validity.
Do NOT add commentary.
Return ONLY valid JSON matching the schema.

Schema:
{schema_text}

Original draft scene:
{json.dumps(draft_obj, ensure_ascii=False) if draft_obj else raw_draft}

Critic feedback:
{json.dumps(critic, ensure_ascii=False) if critic else '{"note": "No critic feedback available; improve awkwardness, cliché, and dialogue where possible."}'}

Constraints:
- Keep sceneId: "{scene_id}"
- Keep variantId: "{variant_id}"
- Keep the same overall branching structure where possible
- Preserve node ids and ending ids if already present
- Improve awkward, cliché, or generic narration
- Make choices feel more meaningfully distinct
- Make dialogue sound less generic and more character-specific
""".strip()

    revised_raw = model_call(
        provider,
        revision_system,
        revision_user,
        timeout_s=timeout,
        retries=retries,
    )

    # Evaluate revised version
    revised_obj = None
    revised_critic = None

    try:
        revised_obj = json.loads(revised_raw)
        revised_critic = evaluate_narrative(revised_obj)
    except Exception:
        pass

    return {
    "draft_raw": raw_draft,
    "draft_obj": draft_obj,
    "critic": critic,
    "revised_raw": revised_raw,
    "revised_obj": revised_obj,
    "critic_after": revised_critic,
}