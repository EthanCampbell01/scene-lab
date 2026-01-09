# Branch From Linear Scene Prompt

## System Role
You convert an expanded *linear* scene into an **abstract structure graph** for a choose-your-own-adventure interrogation/negotiation scene.
Return **JSON only** for `scene.structure.json` (structure format used by this project). No markdown.

## User Instructions
Given this expanded linear scene JSON, produce a structure graph that:
- Uses the same dramatic beats as nodes (`choiceGraph.nodes[]`).
- Adds **2–4 options per node** that branch to later nodes or endings.
- Adds `moveType` for each option (probe/pressure/offerDeal/revealEvidence/stall/flipPower/proceed).
- Uses `requires` and `yields` to track:
  - tags (e.g. player.prepared, subject.alert)
  - stats (stat:trust+1 etc)
  - facts (fact:alibi=disproven etc)
  - goals (goal:interrogator.getConfession+1 etc)
- Do NOT introduce new facts: only those present in the linear scene's initialState.facts.

Rules:
- Every option must have a valid `to` (nodeId or endingId).
- Avoid dead ends: at least 1 path to each ending.
- Keep nodeId values stable (reuse the linear nodeIds).

Expanded linear scene JSON:
<LINEAR_JSON_HERE>

Return JSON only.
