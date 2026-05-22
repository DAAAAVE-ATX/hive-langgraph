"""Demo runner. Loads a sample spec, runs the graph, prints a trace."""

import argparse
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

from hive_lg.graph import build_graph
from hive_lg.llm import get_llm
from hive_lg.state import initial_state


SAMPLE_SPECS_PATH = Path(__file__).resolve().parent.parent / "examples" / "sample_specs.md"


def load_specs(path=SAMPLE_SPECS_PATH):
    """Parse sample_specs.md into a list of dicts with id, spec, criteria.

    The file format expected:
        ## Spec <id>: <title>
        **Spec:** <task description>
        **Acceptance criteria:** <criteria>
    """
    text = Path(path).read_text(encoding="utf-8")
    blocks = re.split(r"^##\s+Spec\s+", text, flags=re.MULTILINE)
    specs = []
    for block in blocks[1:]:
        head, _, body = block.partition("\n")
        sid_match = re.match(r"(\d+)", head.strip())
        if not sid_match:
            continue
        sid = int(sid_match.group(1))
        spec_match = re.search(r"\*\*Spec:\*\*\s*(.+?)(?=\n\*\*|\Z)", body, flags=re.DOTALL)
        crit_match = re.search(r"\*\*Acceptance criteria:\*\*\s*(.+?)(?=\n##|\Z)", body, flags=re.DOTALL)
        if not spec_match or not crit_match:
            continue
        specs.append(
            {
                "id": sid,
                "spec": spec_match.group(1).strip(),
                "acceptance_criteria": crit_match.group(1).strip(),
            }
        )
    return specs


def print_trace(final_state):
    """Print a readable execution trace of a finished graph run."""
    print("=" * 70)
    print("EXECUTION TRACE")
    print("=" * 70)
    for i, (node, output) in enumerate(final_state.get("history", []), 1):
        print(f"\n[{i}] {node}")
        print("-" * 70)
        print(output)
    print()
    print("=" * 70)
    print("FINAL RESULT")
    print("=" * 70)
    print(f"worker_type:           {final_state.get('worker_type')}")
    print(f"attempts:              {final_state.get('attempt_count')}")
    print(f"bat_verdict:           {final_state.get('bat_verdict')}")
    print(f"max_retries_exceeded:  {final_state.get('max_retries_exceeded')}")
    print()
    print("Final worker output:")
    print("-" * 70)
    print(final_state.get("worker_output", ""))


def main():
    """CLI entry. Picks a sample spec by id and runs the graph."""
    load_dotenv()

    parser = argparse.ArgumentParser(description="Run the hive-langgraph demo on a sample spec.")
    parser.add_argument("--spec-id", type=int, default=1, help="Sample spec id (1, 2, or 3).")
    args = parser.parse_args()

    specs = load_specs()
    chosen = next((s for s in specs if s["id"] == args.spec_id), None)
    if chosen is None:
        print(f"No spec with id {args.spec_id}. Available: {[s['id'] for s in specs]}")
        sys.exit(1)

    provider = os.getenv("HIVE_LG_PROVIDER", "anthropic")
    print(f"Provider: {provider}")
    print(f"Spec {chosen['id']}: {chosen['spec']}")
    print(f"Acceptance criteria: {chosen['acceptance_criteria']}")
    print()

    try:
        get_llm()
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(2)

    graph = build_graph()
    final = graph.invoke(initial_state(chosen["spec"], chosen["acceptance_criteria"]))
    print_trace(final)


if __name__ == "__main__":
    main()
