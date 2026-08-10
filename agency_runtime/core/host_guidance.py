"""Host-accurate operator guidance shared by routing and finalization."""

SPECIALIST_TOOL_GUIDANCE = (
    "use the host's installed Agency specialist tools "
    "(`agency.search_agents` and `agency.load_specialist` on MCP surfaces)"
)

def specialist_load_guidance(host: object, session_id: str, trace_id: str) -> str:
    """Return the one loading instruction, identical on every host.

    This used to tell native hosts to "dispatch an isolated worker for every
    accepted persisted unit-agent plan row" and to "not load the specialist
    prompt body into the persistent parent transcript" -- rule 2 exactly
    inverted, forbidding the load into the caller and demanding a spawn per
    plan row. There are no plan rows, and the card goes to whoever is already
    doing the work.
    """

    del host, session_id, trace_id
    return SPECIALIST_TOOL_GUIDANCE


__all__ = [
    "SPECIALIST_TOOL_GUIDANCE",
    "specialist_load_guidance",
]
