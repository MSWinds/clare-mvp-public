# Personalized Learning Profile System — MVP Spec (v2)

## Overview

Build an AI teaching assistant that **creates** and **continuously updates** a structured learner profile using just two inputs. The assistant performs **assign-or-update (upsert)** on profile fields based on unified evidence from the initial questionnaire and ongoing interactions.

---

## Final Data Contract

### Inputs

- **`current_profile`**: the current learner profile JSON (may be `{}` for first-time initialization).
- **`evidence`**: a list of normalized evidence items derived from the initial questionnaire and/or interaction history.

### Output

- **`updated_profile`**: learner profile JSON containing **only core educational dimensions** (no IDs, versions, timestamps, or logs). External systems attach metadata as needed.

---

## Evidence Schema (Unified)

Evidence combines signals from both questionnaire and interaction logs.

```json
{
  "evidence": [
    {
      "source": "questionnaire",          // or "interaction", "manual"
      "ts": "2025-09-02T18:10:00Z",       // ISO 8601; if missing, caller may set
      "dimension": "technical_profile",   // one of: basic_info, technical_profile, cognitive_profile, learning_style, challenges_needs, ai_strategy, career
      "field": "python_skill",            // optional; if omitted, treat as whole-dimension merge
      "value": "beginner",                // scalar | array | object (example only; refine as needed)
      "confidence": 0.85,                 // 0~1; extraction certainty/quality
      "weight": 1.0,                      // source importance (policy-defined)
      "note": "Q8: reads code, not writing"
    }
  ]
}
```

> **Note:** Values shown are examples/placeholders; you can fine-tune field vocabularies later without changing this contract.

---

## Learner Profile Schema (Output — Core Dimensions Only)

No `student_id`, no `profile_version/last_updated/created_from`, no `change_log/provenance`. Those belong to the external system.

```json
{
  "basic_info": {
    "name": "Alex",
    "program": "D.Tech",
    "enrollment": { "course": "LLM Systems", "term": "Fall 2025" }
  },
  "technical_profile": {
    "prior_education": "non-CS",
    "python_skill": "beginner",
    "ai_tools_used": ["none"]
  },
  "cognitive_profile": {
    "comprehension": "with_guidance",
    "execution_ability": "low",
    "learning_pace": "slow_clear_steps",
    "reasoning_style": "reflective"
  },
  "learning_style": {
    "preferred_formats": ["visual","examples"],
    "study_patterns": ["resource_driven"],
    "motivation": "competence"
  },
  "challenges_needs": {
    "concept_gaps": ["retrieval_chunking"],
    "pain_points": ["prompt_debugging","agent_flow"],
    "misconceptions": ["treats_prompts_as_flat_QA"],
    "support_needed": ["hint_layering","guided_examples"]
  },
  "ai_strategy": {
    "feedback_tone": "encouraging",
    "guidance_mode": "socratic",
    "intervention_style": "scaffold_level_1",
    "feedback_modes": ["text","visual_cues","interactive_questions"]
  },
  "career": {
    "interests": ["Technology/IT"],
    "goals": ["applied-LLM-engineering"]
  }
}
```

---

## Consolidated Prompt (Drop-in)

### System / Instruction

```text
You are an AI learner-profile updater. Merge new evidence into a student's structured learner profile.

Rules:
- Use the schema provided below.
- If current_profile is empty → assign initial values from evidence.
- If current_profile has values → update only when evidence is sufficiently strong/recent; otherwise keep old values.
- Prefer recency; break ties by confidence×weight.
- For slow-moving fields (motivation, career, learning style), require stronger evidence or ≥2 consistent signals.
- Protect basic_info: update only from questionnaire/manual sources.
- If evidence is insufficient or ambiguous → do not change that field.
- Return ONLY the updated_profile JSON (no extra text).
```

### User

```text
current_profile = {{CURRENT_PROFILE_JSON}}
evidence = {{EVIDENCE_LIST_JSON}}
```

### Assistant

```text
# Return updated_profile JSON only, matching the schema.
```

---

## Merge Policy (Upsert)

1. **Field-level decision**: operate per `(dimension, field)`; if `field` is absent, deep-merge the dimension.  
2. **Recency first**: if conflicting, prefer more recent evidence.  
3. **Confidence×Weight**: break ties using `score = confidence * weight`.  
4. **Slow variables**: for motivation/career/learning style, require stronger signal or ≥2 consistent evidences.  
5. **Protected fields**: `basic_info` is only updated by `questionnaire`/`manual`.  
6. **No-op allowed**: weak/ambiguous evidence should not change existing values.  

---

## Workflow

1. **Initialization**  
   - Input: empty `current_profile` + questionnaire-derived evidence.  
   - Output: assigned learner profile (first version).  

2. **Update Loop**  
   - Input: existing `current_profile` + new interaction-derived evidence.  
   - Output: profile may update selected fields or remain unchanged.  

3. **External Integration**  
   - External systems attach `student_id`, do versioning/timestamps, and optionally keep change logs.  
   - The AI component focuses purely on the educational dimensions.

---

## Implementation Plan

### Phase 1: Core Infrastructure

- Update `student_profiles` database schema with JSONB dimensions
- Create evidence normalization pipeline
- Build profile merge engine with Pydantic validation

### Phase 2: Data Sources

- **Initial Questionnaire**: Streamlit UI collecting structured evidence
- **Interaction Analyzer**: Replace `summarizer.py` → `profile_analyzer.py`
- **Evidence Extractor**: Convert chat history into evidence items

### Phase 3: Integration

- Hook profile analyzer into main workflow after chat storage
- Update `agentic_workflow.py` to use structured profile context
- Configure weekly automated profile updates (class schedule-based)

### Phase 4: Adaptive Intelligence

- Implement "no-update" logic for insufficient evidence
- Add profile-based teaching tone and guidance adaptation
- Enable personalized learning path recommendations

## Key Integration Points

### Database Layer (`main.py`)

```python
# After storing chat interaction
if should_trigger_profile_update(student_id):
    evidence = extract_evidence_from_recent_history(student_id)
    updated_profile = profile_analyzer.merge(current_profile, evidence)
    store_updated_profile(student_id, updated_profile)
```

### Context Layer (`agentic_workflow.py`)

```python
# Enhanced context retrieval
profile = get_structured_profile(student_id)
personalized_context = adapt_teaching_strategy(profile)
# Use in answer generation
```

## Notes for Implementation

- Use a validation layer (e.g., Pydantic) to enforce schema and provide default coercions  
- Normalize unstructured inputs into `evidence` before merging
- Keep merge logic idempotent; repeated identical evidence should not drift values
- **Weekly Triggers**: Align with class schedule for meaningful update intervals
- **Smart Updates**: Profile analyzer decides when evidence is insufficient
- Leave room for future auditability (change logs/provenance) without changing input/output contracts

---

## Changelog (v2)

- **Removed**: `student_id`, `profile_version`, `last_updated`, `created_from`, `change_log`, `provenance` from prompt I/O  
- **Added**: Consolidated prompt block; clarified upsert rules; emphasized external metadata separation
- **Enhanced**: Implementation phases and integration points for existing Clare-AI system
