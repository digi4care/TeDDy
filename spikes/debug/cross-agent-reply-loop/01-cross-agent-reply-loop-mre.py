"""Reproduce stale replies when the active instruction is context-only."""

from copy import deepcopy
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from teddy_executor.core.domain.models import ProjectContext
from teddy_executor.core.domain.models.planning_ports import PlanningPorts
from replica_planning_service import PlanningService
from teddy_executor.core.services.session_replanner import SessionReplanner

STALE_APPROVAL = "# Old approval request\n\n## Message\nMay I proceed?"
FRESH_APPROVAL = "# Approval consumed\n\n## Message\nProceeding with the work."
STALE_REPLAN = "This is the same malformed response as before."
CORRECTED_REPLAN = "# Corrected response\n\n## Message\nValidation feedback applied."
REPLAN_ERROR = (
    "Response must contain exactly one Level 1 heading and exactly one of "
    "## Action Plan or ## Message."
)


class DirectiveSensitiveLlm:
    """Follow a standalone directive; otherwise repeat the stale response."""

    def __init__(self, stale_content: str) -> None:
        self.stale_content = stale_content
        self.requests: list[list[dict[str, str]]] = []
        self.responses: list[str] = []

    def validate_config(self, include_remote: bool) -> list[str]:
        return []

    def get_text_token_count(self, text: str, model: str = "") -> int:
        return len(text)

    def get_token_count(self, messages: list[dict[str, str]]) -> int:
        return sum(len(message["content"]) for message in messages)

    def get_context_window(self, model: str = "") -> int:
        return 100_000

    def get_completion_cost(self, response: object, model_override: str) -> float:
        return 0.0

    def get_completion(
        self, messages: list[dict[str, str]], model: str
    ) -> SimpleNamespace:
        self.requests.append(deepcopy(messages))
        directive = messages[-1]["content"] if len(messages) > 2 else ""
        if directive.strip() == "yes":
            content = FRESH_APPROVAL
        elif directive.startswith("The previous plan failed validation."):
            content = CORRECTED_REPLAN
        else:
            content = self.stale_content
        self.responses.append(content)
        choice = SimpleNamespace(
            message=SimpleNamespace(content=content), finish_reason="stop"
        )
        return SimpleNamespace(model=model, choices=[choice])


def build_service(
    turn_dir: str, history: str, llm: DirectiveSensitiveLlm, meta: dict
) -> tuple[PlanningService, dict]:
    context = Mock()
    context.get_context.return_value = ProjectContext(
        header="# Project Context",
        content=history,
        scoped_paths={},
        git_status="",
    )
    config = Mock()
    settings = {"llm.model": "fake-model", "llm.max_retries": 1}
    config.get_setting.side_effect = lambda key, default=None: settings.get(
        key, default
    )
    prompts = Mock()
    prompts.resolve_message.side_effect = lambda message, _turn_path: message
    prompts.resolve_agent_metadata.return_value = (
        "developer",
        meta,
        f"{turn_dir}/meta.yaml",
    )
    prompts.fetch_system_prompt.return_value = "Follow the current MRP contract."
    prompts.log_telemetry.return_value = 0.0
    service = PlanningService(
        PlanningPorts(
            context=context,
            llm=llm,
            fs=Mock(),
            config=config,
            prompts=prompts,
            ui=None,
            session_manager=None,
        )
    )
    return service, meta


def record(failures: list[str], condition: bool, description: str) -> None:
    if not condition:
        failures.append(description)


def report_scenario(name: str, llm: DirectiveSensitiveLlm) -> None:
    messages = llm.requests[-1]
    print(f"{name} roles: {[message['role'] for message in messages]}")
    print(f"{name} final user message: {messages[-1]['content'][:180]!r}")
    print(f"{name} emitted response: {llm.responses[-1].splitlines()[0]!r}")


def main() -> None:
    failures: list[str] = []
    approval_history = (
        "## Session History\n### Turn 01 Report\n"
        "Agent MESSAGE: May I proceed?\nUser Reply: yes"
    )
    approval_llm = DirectiveSensitiveLlm(STALE_APPROVAL)
    approval_service, approval_meta = build_service(
        "session/02", approval_history, approval_llm, {}
    )
    approval_service.generate_plan(
        user_message="yes", turn_dir="session/02", context_files={}
    )
    approval_messages = approval_llm.requests[-1]
    record(
        failures,
        approval_meta.get("user_request") == "yes",
        "Approval was not registered in metadata.",
    )
    record(
        failures,
        [message["role"] for message in approval_messages]
        == ["system", "user", "user"]
        and approval_messages[-1] == {"role": "user", "content": "yes"},
        "Approval is not a distinct final user message.",
    )
    record(
        failures,
        approval_llm.responses[-1] == FRESH_APPROVAL,
        "Approval still produces the stale MESSAGE.",
    )
    report_scenario("approval", approval_llm)

    replan_llm = DirectiveSensitiveLlm(STALE_REPLAN)
    replan_service, _ = build_service(
        "session/03",
        "## Session History\n### Turn 02 Plan\nMalformed response",
        replan_llm,
        {"is_replan": True, "user_request": "Original human request"},
    )
    replanner = SessionReplanner(Mock(), replan_service)
    replanner.trigger_replan_turn(
        next_turn_dir="session/03",
        errors=[REPLAN_ERROR],
        original_content=STALE_REPLAN,
        validation_ast="# Faulty AST view",
    )
    replan_messages = replan_llm.requests[-1]
    final_content = replan_messages[-1]["content"]
    record(
        failures,
        [message["role"] for message in replan_messages]
        == ["system", "user", "user"]
        and final_content.startswith("The previous plan failed validation.")
        and REPLAN_ERROR in final_content
        and "## Original Faulty Plan:" in final_content,
        "Malformed-replan feedback is not a complete distinct final user message.",
    )
    record(
        failures,
        replan_llm.responses[-1] == CORRECTED_REPLAN,
        "Malformed replan still produces the stale malformed response.",
    )
    report_scenario("malformed-replan", replan_llm)

    if failures:
        print("\nMRE FAILURES:")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)
    print("\nMRE PASS: both active instructions control the next response.")


if __name__ == "__main__":
    main()
