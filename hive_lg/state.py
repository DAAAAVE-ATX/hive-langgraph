"""Shared graph state for the hive orchestration loop."""

from typing import TypedDict


class HiveState(TypedDict, total=False):
    """State carried across all nodes of the hive graph.

    Attributes:
        spec: The input task description handed to Q33N.
        acceptance_criteria: Plain-text criteria BAT evaluates the worker output against.
        worker_type: One of ``researcher``, ``coder``, ``writer``; set by Q33N.
        worker_output: The latest output produced by the routed worker.
        bat_verdict: ``pass``, ``fail``, or empty string when not yet evaluated.
        bat_feedback: BAT's reasoning, appended to the worker prompt on retry.
        attempt_count: Number of worker attempts made so far.
        history: Append-only log of (node_name, output) tuples.
        max_retries_exceeded: True if the retry cap was hit without a passing verdict.
    """

    spec: str
    acceptance_criteria: str
    worker_type: str
    worker_output: str
    bat_verdict: str
    bat_feedback: str
    attempt_count: int
    history: list
    max_retries_exceeded: bool


def initial_state(spec, acceptance_criteria):
    """Build an initial HiveState for a new graph run.

    Args:
        spec: The task description.
        acceptance_criteria: Plain-text criteria for BAT.

    Returns:
        A HiveState dict with empty intermediate fields and ``attempt_count`` at 0.
    """
    return {
        "spec": spec,
        "acceptance_criteria": acceptance_criteria,
        "worker_type": "",
        "worker_output": "",
        "bat_verdict": "",
        "bat_feedback": "",
        "attempt_count": 0,
        "history": [],
        "max_retries_exceeded": False,
    }
