# Slice: 07-03-Tests

- **Status:** In Progress
- **Milestone:** [07-per-persona-model-routing](../milestones/07-per-persona-model-routing.md)
- **Depends On:** [07-02-Adapters](07-02-Adapters.md)
- **Specs:** [per-persona-model-routing](../../specs/per-persona-model-routing.md)
- **Prototype:** N/A
- **Component Docs:** N/A
- **Scope Slug:** `end-to-end-routing`

## Goal
Verify per-persona routing in a real multi-turn session with persona switching.

## Context
- 07-01-Env and 07-02-Adapters implement config schema and resolution logic.
- This slice validates end-to-end behavior with real LLM calls (using LiteLLM mocks).

## Scenarios
Primary user journeys and happy paths.

> As a TeDDy user, I want to confirm that a real session with persona switching uses the correct models per turn, so I trust the routing logic works end-to-end.

```gherkin
Given a `.teddy/config.yaml` with `agents.pathfinder.model: "openai/gpt-4o"` and `agents.architect.model: "anthropic/claude-3-5-sonnet"`
When I start a session as pathfinder, then switch to architect, then back to pathfinder
Then turn 1's `report.md` contains `openai/gpt-4o`
And turn 2's `report.md` contains `anthropic/claude-3-5-sonnet`
And turn 3's `report.md` contains `openai/gpt-4o`
```

## Edge Cases
- If config is missing `agents.*` section, fallback to global `llm.model` for all turns.
- If persona config is partially missing, missing entries use fallbacks.

## Key Unknowns

**Format:**
- [ ] [Functional] Should the test use a real CLI session or programmatic API? Design Sensitivity: if CLI → real-world fidelity; if programmatic → faster, more deterministic.

## Impact
1. `[NEW]` Acceptance test module `tests/suites/acceptance/test_per_persona_routing.py` — End-to-end routing verification.
   - **Design Sensitivity:** If test coverage is insufficient → routing bugs escape to production; if test complexity grows → maintenance burden increases.

## Deliverables

- [ ] **Interface** - N/A — Existing test harness suffices.
- [ ] **Harness** - N/A — Existing `CliTestAdapter` and `MarkdownPlanBuilder` suffice.
- [ ] **Wiring** - Create acceptance test that starts as pathfinder, switches to architect, and asserts resolved model in each `report.md`.
- [ ] **Core** - N/A — No new logic.
- [ ] **Adapter** - N/A — LiteLLM adapter already records resolved model in `meta`.

## Implementation Notes
- Use LiteLLM's `model_map` or fixture-based mocking to ensure deterministic output.
- Test must verify model in `meta.yaml` (already stored by `PromptManager.update_meta()`).

## Verification
1. **Title:** Verify end-to-end routing
   Run `uv run pytest tests/suites/acceptance/test_per_persona_routing.py::test_agent_switching_models`.
   Verify each `report.md` contains the correct resolved model per persona.
