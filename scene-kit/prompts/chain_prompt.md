# Chain Scene Prompt

## System Role
You are a narrative planner. Return JSON only.

## User Instructions
Given the previous scene summary, produce a *brief* for the next scene that continues the story while allowing fresh branches.
Return JSON:
{
  "brief": "one paragraph brief for next scene",
  "factsToCarry": { "factName": "status" },
  "statTargets": { "trust": 0-5, "suspicion": 0-5, "leverage": 0-5 },
  "goalTargets": { "interrogator.getConfession": number, "suspect.avoidIncrimination": number },
  "toneNotes": ["..."]
}

Previous summary:
<PREV_SUMMARY_HERE>

Return JSON only.
