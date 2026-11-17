#!/usr/bin/env python3
"""Empirically verify agent name presence in all plan.md files."""

from pathlib import Path
import re
import sys


def extract_agent_from_plan(plan_path: Path) -> str:
    """Extract agent name from plan header or return None if missing."""
    try:
        content = plan_path.read_text(encoding="utf-8")
        # Match `- **Agent:** <name>` in header (first 15 lines)
        header = "\n".join(content.split("\n")[:15])
        match = re.search(r"^\s*- \*\*Agent:\*\*\s*(.+?)\s*$", header, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return None
    except Exception as e:
        return f"ERROR: {e}"


def main():
    sessions_dir = Path(".teddy/sessions")
    if not sessions_dir.exists():
        print("No session directory found.")
        sys.exit(0)

    plans = list(sessions_dir.glob("**/plan.md"))
    if not plans:
        print("No plan.md files found.")
        sys.exit(0)

    found = []
    missing = []
    errors = []

    for plan in sorted(plans):
        agent = extract_agent_from_plan(plan)
        if agent is None:
            missing.append(plan)
        elif agent.startswith("ERROR:"):
            errors.append((plan, agent))
        else:
            found.append((plan, agent))

    print(f"\nTotal plans: {len(plans)}")
    print(f"✓ Agent present: {len(found)}")
    print(f"✗ Agent missing: {len(missing)}")
    print(f"⚠ Errors: {len(errors)}")

    if missing:
        print("\nPlans missing agent metadata:")
        for m in missing:
            print(f"  - {m}")

    if errors:
        print("\nPlans with errors:")
        for p, e in errors:
            print(f"  - {p}: {e}")

    print("\n" + "=" * 60)
    if not missing and not errors:
        print("EMPIRICAL VERIFICATION: Agent name is ALWAYS present in plan metadata.")
        print("Design Sensitivity: If missing, fallback to `llm.model` is safe.")
    elif missing:
        print("RISK DETECTED: Agent name is NOT always present.")
        print("Recommendation: Implement fallback to `llm.model` or raise ConfigurationError.")
    else:
        print("INSUFFICIENT DATA: No plans found or errors encountered.")

    return 0 if not missing else 1


if __name__ == "__main__":
    sys.exit(main())
