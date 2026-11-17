# Bug: Cross-agent reply loop
- **Status:** Resolved
- **Milestone:** N/A
- **Vertical Slice:** N/A
- **Specs:** N/A

## Symptoms
After an agent emits a MESSAGE, a clear new user reply such as `yes` or `ga verder` can be followed by the same stale response from Pathfinder, Developer, or Prototyper. The same stale-response risk applies to automated correction feedback after a malformed plan.

Expected: the latest human reply or replan feedback controls the next response while prior session history remains available as context.

Actual: the new reply is resolved and registered, but the shared planning route does not explicitly send it as a distinct final user message. `spikes/debug/cross-agent-reply-loop/01-cross-agent-reply-loop-mre.py` reproduces this contract for both approval and malformed-replan; its directive-sensitive LLM double consequently emits the stale response in both scenarios.

## Context & Scope
### Regressing Delta
Commit `d010a1c5031fa50f249ccfc91858c5ce38233691` (`fix(core): resolve session loop breakage and restore system stability`, 2026-05-15) changed `src/teddy_executor/core/services/planning_service.py` from one user message containing `Context:\n{full_context}\n\nUser Message: {resolved_message}` to one user message containing only `full_context`. The same commit changed `tests/suites/unit/core/services/test_planning_service.py` to pin the context-only contract. The current affected request construction is around lines 83-91.

This was an intentional “Pure Context Strategy”, not a recent MRP edit. The proposed change is not a literal revert: it restores the active instruction as a distinct final user message while retaining context-only `input.md` and a separate context message.

### Environmental Triggers
Session-mode planning through `PlanningService`, including approval replies and `SessionReplanner` correction turns. The user-visible model response is provider- and model-dependent; the omitted request message is deterministic and agent-independent.

### Ruled Out
Per-agent prompt defects are not the originating delta: Pathfinder, Developer, and Prototyper all use the centralized `PlanningService` request builder. The recent MRP revisions also postdate the context-only delta. `SessionReplanner` builds feedback but delegates request construction, so it does not independently discard the feedback. External provider sensitivity has not been measured and is not claimed to be uniform.

## Diagnostic Analysis
### Causal Model
The following observations are verified on the current checkout:

1. `PromptManager.resolve_message()` returns the current user message.
2. `PlanningService.generate_plan()` stores a non-replan resolved message in `meta["user_request"]`.
3. `PlanningService.generate_plan()` sends exactly one system message and one user message containing `full_context`; it does not append `resolved_message` to that request.
4. `SessionReplanner.trigger_replan_turn()` passes its validation feedback through the same `generate_plan(user_message=...)` route.
5. The MRE observed `['system', 'user']` for both scenarios. The approval `yes` was registered as `user_request`, while neither that reply nor the generated correction feedback appeared as a distinct request message.
6. Under the MRE's directive-sensitive LLM double, both context-only requests emitted their configured stale response. This deterministically reproduces the suspected mechanism, but does not claim that every external provider or model reacts identically.
7. Before `d010a1c5`, the active instruction was present but combined with context in the same user message. That commit deliberately removed it from the request while introducing the pure-context test contract. Consequently, restoring role separation requires a new three-message shape rather than restoring the former combined message.

8. Before direct resolution, `spikes/debug/cross-agent-reply-loop/replica_planning_service.py` differed from production only by appending a truthy `resolved_message` as a separate final user message. Running the unchanged MRE assertions against that replica produced `['system', 'user', 'user']`, exact approval and complete correction-feedback final messages, and fresh responses in both scenarios. The same append is now directly applied to production and was verified byte-identical to the replica. Permanent regression tests confirm the current three-message contract, while the MRE's LLM double still bounds the conclusion to the deterministic request mechanism rather than uniform external-provider behavior.

### Discrepancies
- [x] A resolved approval reply was registered but was not a distinct final user message in the LLM request. (Resolved: `PlanningService` now appends every non-empty resolved message after the unchanged context message; the approval regression test verifies exact content, metadata registration, and context-only `input.md`.)
- [x] Malformed-plan correction feedback reached the same request builder and therefore had the same context-only failure. (Resolved: the shared append delivers the existing `SessionReplanner` feedback intact as the final user message; the regression test verifies the validation error, AST, original faulty response, and preservation of the original human request.)

### Investigation History
1. Inspected `PlanningService`, `PromptManager`, `SessionPlanner`, `SessionOrchestrator`, `SessionReplanner`, their callers, and the current MRP; observed the shared context-only request construction and confirmed that approval and malformed-replan coverage are both required.
2. Searched existing debugging artifacts; found no Case File or source MRE for this defect, so a new deterministic reproduction is required.
3. Investigated whether approval and malformed-replan omit their active instruction by running `uv run python spikes/debug/cross-agent-reply-loop/01-cross-agent-reply-loop-mre.py` against unmodified production services; observed the expected exit code 1, context-only requests, and stale responses from the directive-sensitive double, which confirms the missing request contract and establishes the sandbox comparison baseline.
4. Investigated whether the omission was a recent regression by using blame, pickaxe, and patches from `b34f757d` and `d010a1c5`; observed that the original implementation combined context and instruction, while `d010a1c5` deliberately made the request context-only and pinned that behavior in a unit test. This isolates the regressing delta and rules out per-agent prompts and the recent MRP changes as its origin.
5. Tested the proposed separate final user message by creating an otherwise exact PlanningService replica and switching only the MRE import to that replica; observed exit code 0, three-message requests for approval and malformed-replan, exact `yes` and complete replan feedback as the respective final messages, and fresh responses from the double. This empirically proves the central fix in the sandbox without modifying `src/` or `tests/`; it does not measure external-provider behavior.
6. Investigated integrated impact by adding approval and malformed-replan regression tests, observing both fail only on the missing third request message before the production append, and then observing all 26 targeted PlanningService, SessionReplanner, and instruction-bridge tests pass after the append. A subsequent `make test` produced 2301 passes and 5 skips but 3 setup errors in filesystem-recursion tests: pyfakefs could not open the real `validation_rules/message.py` during container creation. Those errors occur before the test bodies and have not yet been attributed to this fix, test ordering, or pre-existing harness behavior; resolution and full-suite verification remain pending.
7. Investigated whether the filesystem errors depended on full-suite ordering by running only `test_file_system_adapter_recursion.py`; observed the same three setup errors, now with `console_interactor.py` as the first missing lazy import. This isolates a pyfakefs/container fixture-boundary failure independent of PlanningService calls, while the varying missing module reflects which imports earlier tests already loaded. Running that identical test file in a detached clean-HEAD worktree at `8d6b9def` reproduced all three setup errors, proving the harness failure predates and is independent of this change.
8. Investigated whether replacing the unused mocked edit simulator and its container fixture was sufficient by running a sandbox replica with a real stateless `EditSimulator`; observed all three tests reach their bodies but fail when `list_directory_recursive()` lazily imports `filesystem_helpers.py` after pyfakefs activation. This disproves the container-only correction and identifies a second lazy-import boundary; preloading that helper before fixture activation remains to be tested.
9. Investigated whether preloading `filesystem_helpers` completed the correction by adding its import during test collection; observed all three tests advance into `load_ignore_spec()` and fail on its function-local `import pathspec`, because the real site-packages tree is then hidden by pyfakefs. This disproves the helper-only correction and isolates the external dependency as the next import boundary; preloading `pathspec` before fixture activation remains to be tested.
10. Investigated whether preloading both lazy modules completed the correction by importing `pathspec` and `filesystem_helpers` during collection while retaining the real stateless `EditSimulator` and omitting the container fixture; observed all three sandbox tests pass. This proves the minimal test-only correction for the pre-existing suite blockage.
11. Transferred the combined correction to the permanent recursion tests. An initial broad EDIT transfer dropped two path arguments and skipped one old constructor; Ruff stopped before test execution, so the call sites were restored exactly to the proven builder form without changing production code. The subsequent run passed Ruff, all three isolated recursion tests, and the full `make test` gate with 2304 passes and 5 skips. This verifies both the direct reply-loop resolution and the independent pre-existing harness correction with no remaining failures or errors.

## Solution
### Root Cause
`PlanningService` resolved the active human reply or automated correction feedback but omitted it from the LLM request, leaving only system instructions and project/session context. The context-only delta originated in `d010a1c5`. The fix was first proven in `spikes/debug/cross-agent-reply-loop/replica_planning_service.py` and then directly applied to `src/teddy_executor/core/services/planning_service.py`: a truthy `resolved_message` is appended as a distinct final user message. Session history and `input.md` remain context-only, and an empty continuation adds no message. No per-agent prompt changed.

The approval and malformed-replan regression tests both failed before the production append solely because the third message was absent, then passed afterward. All 26 targeted PlanningService, SessionReplanner, and instruction-bridge tests passed, followed by the full suite with 2304 passes and 5 skips. The preserved end-to-end proof is `spikes/debug/cross-agent-reply-loop/01-cross-agent-reply-loop-mre.py`; its directive-sensitive double verifies the request mechanism and fresh-response behavior without claiming identical behavior from every external LLM provider.

### Affected Components
- `PlanningService`: directly received the sandbox-proven append in the central request builder; no signature, port, composition-root, or per-agent prompt change was required.
- `SessionReplanner`: remains unchanged as the upstream producer of malformed-plan correction feedback; the MRE and permanent regression test prove its existing output arrives intact through the shared route.
- `tests/suites/unit/core/services/test_planning_service.py`: now permanently covers approval and malformed-replan message separation, exact feedback content, context-only `input.md`, metadata registration, and preservation of the original human request during replans.
- `docs/architecture/core/services/planning_service.md`: the obsolete pure-context invariant and planning-phase precondition now describe the verified context/instruction-separation contract.
- `tests/suites/unit/adapters/outbound/test_file_system_adapter_recursion.py`: independently corrected the pre-existing pyfakefs suite blockage with a real stateless `EditSimulator`, no container fixture, and collection-time loading of `filesystem_helpers` and `pathspec`; filesystem production code remains unchanged.
- `spikes/debug/cross-agent-reply-loop/test_file_system_adapter_recursion_replica.py`: preserved sandbox proof for the independent harness correction.
