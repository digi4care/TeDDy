# Slice: 07-02-Adapters

- **Status:** In Progress
- **Milestone:** [07-per-persona-model-routing](../milestones/07-per-persona-model-routing.md)
- **Depends On:** [07-01-Env](07-01-Env.md)
- **Specs:** [per-persona-model-routing](../../specs/per-persona-model-routing.md)
- **Prototype:** N/A
- **Component Docs:** [PlanningService](../../../architecture/core/services/planning_service.md)
- **Scope Slug:** `per-turn-model`

## Goal
Switch `PlanningService` to resolve and pass the model per turn based on the current agent persona.

## Context
- `PlanningService.generate_plan()` currently resolves model once via `meta.get("model") or llm.model`.
- New `IConfigService.get_agent_model()` method returns persona-specific model or fallback.
- Resolution hierarchy: CLI flag `--model` (highest) → per-persona `agents.<persona>.model` → global `llm.model` (fallback).
- Model must be resolved on every turn, not just session start.

## Scenarios
Primary user journeys and happy paths.

> As a TeDDy user, I want the system to resolve the correct LLM model for each agent persona on every turn, so I can switch personas mid-session and use their configured models.

```gherkin
Given a `.teddy/config.yaml` with `agents.pathfinder.model: "openai/gpt-4o"` and `agents.architect.model: "anthropic/claude-3-5-sonnet"`
When I start a session with pathfinder (turn 1) and architect (turn 2)
Then turn 1 uses `openai/gpt-4o` and turn 2 uses `anthropic/claude-3-5-sonnet`
```

## Edge Cases
- If agent name is missing from plan metadata, fallback to `llm.model`.
- If persona config is invalid (e.g., malformed model name), raise user-facing error.

## Key Unknowns

**Format:**
- [ ] [Technical] Is the agent name always present in plan metadata (`- **Agent:**`)? Design Sensitivity: if missing → fallback to `llm.model`; if absent from metadata entirely → raise `ConfigurationError`.

## Impact
1. `[EXTEND]` `PlanningService.generate_plan()` — Call `get_agent_model()` on every turn and pass model to `ILlmClient`.
   - **Design Sensitivity:** If per-turn resolution fails → fallback to session-level model; if model parameter propagation fails → LLM call uses wrong model.
2. `[MIGRATE]` `PlanningService._run_planning_phase()` — Pass resolved model to `ILlmClient.get_completion()` instead of cached session model.
   - **Design Sensitivity:** If model parameter is omitted → LLM call uses default model; if parameter type changes → integration break.
3. `[PRUNE]` Legacy model resolution logic once per-turn resolution is active.
   - **Design Sensitivity:** If legacy logic is removed too early → regression in model resolution; if kept too long → code duplication.

## Deliverables

- [ ] **Interface** - N/A — Existing `IConfigService` interface suffices.
- [ ] **Harness** - Update `tests/suites/unit/core/services/test_planning_service.py` with per-turn model resolution tests.
- [ ] **Wiring** - Connect `PlanningService.generate_plan()` to `IConfigService.get_agent_model()` with per-turn resolution.
- [ ] **Core** - Implement `_resolve_agent_model()` helper in `PlanningService` that checks CLI flag first, then config-based resolution.
```

TL;DR: Re-applies CLI flag precedence edits to spec and slices without trailing commentary.
- [ ] **Adapter** - N/A — `YamlConfigAdapter` already implements `get_agent_model()` (07-01-Env).
- [ ] **Migration** - Update `PlanningService.generate_plan()` to use per-turn model resolution.
- [ ] **Cleanup** - Remove legacy model resolution logic once per-turn resolution is active.

## Implementation Notes
- Model resolution happens BEFORE `system_prompt` token counting (to ensure correct context window).
- Model must be persisted to `meta["model"]` for telemetry and reporting.

## Verification
1. **Title:** Verify per-turn model resolution
   Run `uv run python -m tests.suites.acceptance.test_agent_switching` with a multi-turn session that switches personas.
   Verify each `report.md` contains the correct resolved model per persona.
