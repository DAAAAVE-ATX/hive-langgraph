"""LangGraph nodes: Q33N orchestrator, three worker bees, and the BAT validator."""

from langchain_core.messages import HumanMessage, SystemMessage

from hive_lg.llm import get_llm


Q33N_SYSTEM = (
    "You are Q33N, an orchestrator. Read the spec and classify which worker "
    "should handle it. Respond with exactly one word: researcher, coder, or "
    "writer. researcher answers factual or analytical questions. coder writes "
    "code. writer produces prose or documentation. No other words."
)

RESEARCHER_SYSTEM = (
    "You are researcher_bee. Answer the spec clearly, concisely, and factually. "
    "If prior BAT feedback is given, address it directly in this revision."
)

CODER_SYSTEM = (
    "You are coder_bee. Produce a complete, working code snippet that satisfies "
    "the spec. Include a brief comment header. If prior BAT feedback is given, "
    "address it in this revision."
)

WRITER_SYSTEM = (
    "You are writer_bee. Produce polished prose that satisfies the spec. If "
    "prior BAT feedback is given, address it in this revision."
)

BAT_SYSTEM = (
    "You are BAT, the acceptance tester. Given the spec, the acceptance criteria, "
    "and the worker output, decide whether the output meets every criterion.\n"
    "Respond on exactly two lines:\n"
    "Line 1: VERDICT: pass  OR  VERDICT: fail\n"
    "Line 2: REASON: <one short sentence>\n"
    "Do not add anything else."
)


VALID_WORKER_TYPES = {"researcher", "coder", "writer"}


def _invoke(llm, system_prompt, user_content):
    """Invoke a chat model with a single system + human turn and return text."""
    messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_content)]
    response = llm.invoke(messages)
    return response.content.strip() if isinstance(response.content, str) else str(response.content).strip()


def q33n_orchestrator(state):
    """Classify the spec and set ``worker_type``.

    Args:
        state: Current HiveState.

    Returns:
        Partial state update with ``worker_type`` and a history entry.
    """
    llm = get_llm()
    raw = _invoke(llm, Q33N_SYSTEM, f"Spec:\n{state['spec']}")
    pick = raw.split()[0].lower().strip(".,:;") if raw else ""
    if pick not in VALID_WORKER_TYPES:
        pick = "researcher"
    history = list(state.get("history", []))
    history.append(("q33n", f"classified as {pick} (raw: {raw!r})"))
    return {"worker_type": pick, "history": history}


def _worker_user_content(state):
    """Build the user-side prompt for a worker, including BAT feedback on retry."""
    base = f"Spec:\n{state['spec']}\n\nAcceptance criteria:\n{state['acceptance_criteria']}"
    feedback = state.get("bat_feedback", "")
    if feedback and state.get("attempt_count", 0) > 0:
        base += f"\n\nPrior BAT feedback to address:\n{feedback}"
    return base


def _run_worker(state, node_name, system_prompt):
    """Shared worker body: prompt the LLM, increment attempt count, update history."""
    llm = get_llm()
    output = _invoke(llm, system_prompt, _worker_user_content(state))
    history = list(state.get("history", []))
    attempt = state.get("attempt_count", 0) + 1
    history.append((node_name, output))
    return {"worker_output": output, "attempt_count": attempt, "history": history}


def researcher_bee(state):
    """Researcher worker. Produces factual or analytical answers."""
    return _run_worker(state, "researcher_bee", RESEARCHER_SYSTEM)


def coder_bee(state):
    """Coder worker. Produces code snippets."""
    return _run_worker(state, "coder_bee", CODER_SYSTEM)


def writer_bee(state):
    """Writer worker. Produces prose or documentation."""
    return _run_worker(state, "writer_bee", WRITER_SYSTEM)


def bat_validator(state):
    """Validate worker output against acceptance criteria.

    Returns:
        Partial state update with ``bat_verdict`` and ``bat_feedback``.
    """
    llm = get_llm()
    user = (
        f"Spec:\n{state['spec']}\n\n"
        f"Acceptance criteria:\n{state['acceptance_criteria']}\n\n"
        f"Worker output:\n{state['worker_output']}"
    )
    raw = _invoke(llm, BAT_SYSTEM, user)

    verdict = "fail"
    reason = raw
    for line in raw.splitlines():
        stripped = line.strip()
        low = stripped.lower()
        if low.startswith("verdict:"):
            tail = stripped.split(":", 1)[1].strip().lower()
            if tail.startswith("pass"):
                verdict = "pass"
            elif tail.startswith("fail"):
                verdict = "fail"
        elif low.startswith("reason:"):
            reason = stripped.split(":", 1)[1].strip()

    history = list(state.get("history", []))
    history.append(("bat", f"{verdict}: {reason}"))
    return {"bat_verdict": verdict, "bat_feedback": reason, "history": history}
