# Milestone 7: Per-Persona Model Routing
- **Status:** In Progress
- **Specs:** [per-persona-model-routing](../specs/per-persona-model-routing.md)

## Core Goal

Enable TeDDy to route each agent persona to its own LLM model and API key, configured once in `.teddy/config.yaml` and automatically selected per turn.

## Requirements

- **Spec:** [docs/project/specs/per-persona-model-routing.md](/docs/project/specs/per-persona-model-routing.md)

### Slices

- **07-01-Env:** [Slice Details](../slices/07-01-Env.md)
  Add `agents.*` config schema and model resolution helpers.

- **07-02-Adapters:** [Slice Details](../slices/07-02-Adapters.md)
  Use per-turn model in `PlanningService`.

- **07-03-Tests:** [Slice Details](../slices/07-03-Tests.md)
  End-to-end routing verification.

- **07-04-Docs:** [Slice Details](../slices/07-04-Docs.md)
  Update bundled config example and PROJECT.md.

## Acceptance Criteria

- All slices are green (`make test` passes).
- A fresh session with per-persona config uses the correct model for each agent.
- A session with only global config continues to work unchanged.
