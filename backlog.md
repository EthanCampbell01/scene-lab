# Project Backlog – Scene-Lab

This backlog documents the planned, implemented, and aspirational features of the Scene-Lab project.  
It reflects an **experimental, research-driven development process** rather than a fixed commercial roadmap.

The backlog is intentionally divided into **Now / Next / Later** to demonstrate realistic scope management.

---

## Long-Term Vision

The long-term vision of Scene-Lab is to become an AI-assisted narrative system capable of:

- Automatically generating coherent branching story scenes
- Persisting narrative state across multiple scenes
- Eventually chaining scenes into larger episodic or full-story experiences
- Supporting optional visual elements (e.g. images) aligned with player choices

This project focuses on **foundational systems and experimentation**, not full realisation of this vision.

---

## NOW – Core Implemented Features

These features are fully implemented and demonstrable in the current system.

### 1. One-Command Scene Generation
**Description:**  
Generate a complete branching narrative scene from a short text brief using a single command.

**Includes:**
- AI prompting
- Output validation
- Automatic file placement
- Previewer auto-loading

**Status:** Implemented  
**Value:** Enables rapid iteration and removes manual setup overhead

---

### 2. Schema Validation and Failure Handling
**Description:**  
Ensure AI-generated output conforms to a strict JSON schema before entering the system.

**Includes:**
- Detection of invalid or incomplete AI responses
- Safe handling of malformed output
- Prevention of UI crashes

**Status:** Implemented  
**Value:** Critical when working with probabilistic AI systems

---

### 3. Interactive Scene Previewer
**Description:**  
A React-based UI for playing through generated branching narratives.

**Includes:**
- Choice selection
- Node progression
- Ending detection
- Restart and debug tools

**Status:** Implemented  
**Value:** Makes AI output inspectable, testable, and evaluable

---

### 4. Ending Classification and Visual Feedback
**Description:**  
Automatic detection and promotion of terminal nodes into endings (success, failure, mixed, twist).

**Includes:**
- Visual indicators
- Clear narrative conclusions
- Improved player feedback

**Status:** Implemented  
**Value:** Improves narrative clarity and user understanding

---

### 5. UI Iteration and Polish
**Description:**  
Iterative improvement of the previewer UI based on usability testing and experimentation.

**Includes:**
- Retro-inspired styling
- Improved spacing and hierarchy
- Clear distinction between narrative, choices, and state

**Status:** Iterative / Ongoing  
**Value:** Improves readability and evaluation of generated content

---

## NEXT – Near-Term Planned Features

These features are intentionally **planned but not fully implemented**, demonstrating controlled scope.

### 6. Scene Chaining
**Description:**  
Allow endings of one scene to pass structured state into the next generated scene.

**Status:** Designed conceptually  
**Risks:** Narrative drift, state explosion, consistency management

---

### 7. Persistent Narrative State
**Description:**  
Allow facts, tags, or decisions to persist across scenes and influence future generation.

**Status:** Partially explored  
**Risks:** Increased complexity, reduced controllability

---

### 8. Author-Guided Constraints
**Description:**  
Allow human authors to constrain or pin key narrative beats while allowing AI variation.

**Status:** Conceptual  
**Value:** Moves system closer to practical authoring tools

---

## LATER – Aspirational / Research-Level Features

These items are intentionally out of scope for the current project timeframe.

### 9. Image Generation
**Description:**  
Generate or attach contextual images that reflect scene state or player choices.

**Status:** Out of scope  
**Risks:** Latency, cost, visual-narrative coherence

---

### 10. Full Story Arcs
**Description:**  
Support multi-act narrative structures with pacing, escalation, and resolution.

**Status:** Research-level  
**Value:** High, but non-trivial

---

## Notes on Project Scope

This backlog reflects a deliberate decision to prioritise:
- Reliability
- Validation
- Inspectability
- Working software

over speculative features.

Given the experimental nature of AI-generated content, this approach was essential for managing technical and narrative risk.
