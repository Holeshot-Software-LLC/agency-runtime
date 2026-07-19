"""Host-accurate operator guidance shared by routing and finalization."""

SPECIALIST_TOOL_GUIDANCE = (
    "use the host's installed Agency specialist tools "
    "(`agency.search_agents` and `agency.load_specialist` on MCP surfaces)"
)

NATIVE_DELEGATION_GUIDANCE = (
    "Dispatch through the current host's native worker tool: Codex `spawn_agent`, "
    "Claude Code `Agent`, Hermes `delegate_task`, or OpenClaw `sessions_spawn`. "
    "`agency.delegate` only records an already-observed execution; it does not "
    "launch a worker."
)

WORK_UNIT_CORRELATION_GUIDANCE = (
    "When the host tool accepts `work_unit_id`, pass the bracketed value unchanged. "
    "Otherwise preserve the detected goal text exactly so Agency can reconcile its "
    "stable hash."
)

_NATIVE_DELEGATION_TOOLS = {
    "codex": "Codex `spawn_agent` (or `functions.collaboration.spawn_agent`)",
    "claude": "Claude Code `Agent`",
    "hermes": "Hermes `delegate_task`",
    "openclaw": "OpenClaw `sessions_spawn`",
}


def native_delegation_instruction(host: object) -> str:
    """Return one exact host-owned dispatch and explicit-decline instruction."""

    normalized = str(host or "").strip().casefold()
    tool = _NATIVE_DELEGATION_TOOLS.get(normalized)
    if tool is None:
        dispatch = NATIVE_DELEGATION_GUIDANCE
    elif normalized == "codex":
        dispatch = (
            f"Dispatch with {tool}; use each row's native_task_name as task_name and "
            "preserve the unchanged work_unit_id in Agency activation calls."
        )
    elif normalized == "claude":
        dispatch = (
            f"Dispatch with {tool}; use the unchanged work_unit_id as description so "
            "installed PreToolUse and SubagentStart hooks can bind the child."
        )
    else:
        dispatch = (
            f"Dispatch with {tool}; preserve the unchanged goal and work_unit_id in the "
            "native worker request and Agency evidence calls."
        )
    return (
        f"{dispatch} The native host may refine, merge, or decline the proposed topology. "
        "If it declines a preferred or strongly_preferred row, call "
        "`agency.decline_delegation` once with the exact session_id, trace_id, "
        "work_unit_id, recommended agent, and a concrete bounded reason."
    )


def specialist_load_guidance(host: object, session_id: str, trace_id: str) -> str:
    """Return a truthful loading instruction for ephemeral or persistent hosts."""

    normalized = str(host or "").strip().casefold()
    if normalized in {"codex", "claude"}:
        native_tool = "`spawn_agent`" if normalized == "codex" else "`Agent`"
        label_instruction = (
            "Use the plan row's legal `native_task_name` for Codex `task_name`; "
            "keep the unchanged internal ID in Agency tool calls. "
            if normalized == "codex"
            else "Use the unchanged work-unit ID as the native `description`. "
        )
        return (
            "call `agency.prepare_delegation` in the parent for every persisted "
            "unit-agent plan row, using its recommended agent and exact work unit, "
            f"then dispatch an isolated {native_tool} worker. "
            f"{label_instruction}Inside that child only, call "
            "`agency.load_specialist` with the returned one-use activation token, "
            f"selected slug, `session_id={session_id}`, and `trace_id={trace_id}`. "
            "Do not load the "
            "specialist prompt body into the persistent parent transcript"
        )
    return SPECIALIST_TOOL_GUIDANCE


__all__ = [
    "NATIVE_DELEGATION_GUIDANCE",
    "SPECIALIST_TOOL_GUIDANCE",
    "WORK_UNIT_CORRELATION_GUIDANCE",
    "native_delegation_instruction",
    "specialist_load_guidance",
]
