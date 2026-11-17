# Specification: Per-Persona LLM Model Routing

## Purpose

Define the permanent system invariant for routing each agent persona to its own LLM model and API key, resolved per turn based on configuration.

## Context

TeDDy orchestrates specialized AI personas (Pathfinder, Architect, Developer, Debugger, Assistant, Prototyper), each following a distinct workflow. Currently, the LLM model and API key are configured globally via `llm.model` and `llm.api_key` in `.teddy/config.yaml`. This limits the ability to use different models for different agent roles, even though the agents have different prompt instructions and task scopes.

This spec defines the behavior when per-persona model configuration is present.

## Permanent Invariants

### Config Schema

The `.teddy/config.yaml` file supports an optional `agents:` top-level map:

```yaml
llm:
  model: "openai/gpt-4o"  # fallback when agents.*.model is missing
  api_key: "${TEDDY_LLM_API_KEY}"

agents:
  pathfinder:
    model: "openai/gpt-4o"
    api_key: "${TEDDY_LLM_API_KEY_PATHFINDER}"
  architect:
    model: "anthropic/claude-3-5-sonnet-20240620"
    api_key: "${TEDDY_LLM_API_KEY_ARCHITECT}"
  developer:
    model: "ollama/llama3"
  debugger:
    model: "openai/gpt-4o"
  assistant:
    model: "openai/gpt-3.5-turbo"
  prototyper:
    model: "anthropic/claude-3-opus-20240229"
```

- If `agents.<persona>.model` is absent, the system MUST fall back to `llm.model`.
- If `agents.<persona>.api_key` is absent, the system MUST fall back to `llm.api_key`.
- If both are absent, the session will fail at runtime with the same error as today (no valid model).

### Resolution Behavior

On every turn, the system MUST resolve the model and API key with the following priority (highest to lowest):

**Model Resolution:**
1. CLI flag `--model` (if provided)
2. Per-persona `agents.<persona>.model` in config
3. Global `llm.model` config (fallback when persona config is absent)

**API Key Resolution:**
1. Per-persona `agents.<persona>.api_key` in config
2. Global `llm.api_key` config (fallback when persona config is absent)

The CLI flag `--model` takes precedence over all config-based model routing.

### Contract Boundaries

- The `PlanningService` MUST expose `get_agent_model(agent_name: str) -> str` and `get_agent_api_key(agent_name: str) -> str`.
- The `LiteLLMAdapter` MUST accept a `model` parameter on each call to `completion()` and pass it through.
- The config loading layer MUST support optional `agents.*` keys without breaking existing configs.

## Acceptance Criteria

- A session using only a global `llm.model` config behaves identically to before (backwards compatibility).
- A session with per-persona `agents.*.model` values selects the correct model for each agent turn.
- A session with partial `agents.*.model` entries (some missing) falls back to `llm.model` for the missing entries.
- The CLI flag `--model` overrides all config-based routing when provided.
- The API key fallback logic works identically to model fallback.

## Out of Scope

- Dynamic model switching mid-turn (not supported).
- Per-turn `--model` CLI flag override per persona (CLI flag remains session-wide).
- Dynamic config reload without session restart.
