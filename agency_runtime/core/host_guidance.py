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
    "zcode": "ZCode `Agent` (same native-delegation primitive as Claude)",
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
            "preserve the unchanged work_unit_id in Agency activation calls. For each "
            "row, spawn once with the exact goal and `fork_turns=none`, wait for its "
            "activation-only turn, then call Codex `followup_task` exactly once on the "
            "canonical task path returned by the spawn with that row's JSON-decoded "
            "execution_message, and wait for that execution turn before starting the next "
            "row. Never use `send_message`, retry, or reuse an execution_message."
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
        f"{dispatch} Dispatch every persisted plan row exactly once; do not merge, omit, "
        "or perform a planned specialist unit in the parent. If a row cannot be safely "
        "dispatched, call `agency.decline_delegation` once with the exact session_id, "
        "trace_id, work_unit_id, recommended agent, and a concrete bounded reason, then "
        "stop the parent turn without claiming the planned outcome."
    )


def specialist_load_guidance(host: object, session_id: str, trace_id: str) -> str:
    """Return a truthful loading instruction for ephemeral or persistent hosts."""

    normalized = str(host or "").strip().casefold()
    if normalized in _NATIVE_DELEGATION_TOOLS:
        native_tool = _NATIVE_DELEGATION_TOOLS[normalized]
        label_instruction = (
            "Use the plan row's legal `native_task_name` for Codex `task_name`; "
            "keep the unchanged internal ID in Agency tool calls. "
            if normalized == "codex"
            else (
                "Use the unchanged work-unit ID as the native `description`. "
                if normalized == "claude"
                else "Preserve the exact goal and unchanged work-unit ID in the request. "
            )
        )
        delivery = (
            "The installed PreToolUse hook injects the exact selected immutable prompt "
            "only into that native child, and PostToolUse consumes its one-use grant "
            "from authoritative child-launch evidence"
            if normalized in {"codex", "claude"}
            else "The installed child pre-LLM hook injects the exact selected immutable "
            "prompt only at that native child's inference boundary and consumes its "
            "one-use grant against host-issued child lineage"
        )
        return (
            f"dispatch an isolated {native_tool} worker for every accepted persisted "
            f"unit-agent plan row. {label_instruction}{delivery} for "
            f"`session_id={session_id}` and `trace_id={trace_id}`. Do not "
            "call `agency.prepare_delegation` or `agency.load_specialist` manually, and "
            "do not load the specialist prompt body into the persistent parent transcript"
        )
    return SPECIALIST_TOOL_GUIDANCE


__all__ = [
    "NATIVE_DELEGATION_GUIDANCE",
    "SPECIALIST_TOOL_GUIDANCE",
    "WORK_UNIT_CORRELATION_GUIDANCE",
    "native_delegation_instruction",
    "specialist_load_guidance",
]
