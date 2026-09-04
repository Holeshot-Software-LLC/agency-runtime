"""Per-stage reply budgets for structured inference replies (AR-385, ADR-0199).

The structured transport used to send every stage on every HTTP provider with
the same 2048-token completion cap, and a thinking-enabled deployment behind
the gateway spent the stage's reasoning inside that same cap. A recruiter
nomination for a five- or six-unit plan does not fit: four of nine first
recruiter replies on the 2026-09-03 install smoke stopped at exactly 2048
completion tokens as closed JSON with a row missing its ``unit_id``, and the
runtime recorded each as a contract failure with nothing attached.

The budget is the stage's to own. Each workforce stage stamps its reply budget
on the provider entry it calls with, an operator may state one per profile or
provider, and the transport adds the adapter's thinking allowance on top so
the visible reply keeps the whole budget where the gateway shares one cap
between thinking and text. Callers that stamp nothing keep the historical
transport figure, so nothing outside the workforce stages changes shape.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from types import MappingProxyType
from typing import Final

from agency_runtime.core.config import (
    MAX_REPLY_BUDGET_TOKENS,
    MIN_REPLY_BUDGET_TOKENS,
    ProviderEntry,
)

#: The historical transport figure, used only when no stage or operator states
#: a budget. The direct Anthropic adapter kept a larger fixed figure because it
#: runs without thinking; both are preserved exactly.
DEFAULT_REPLY_BUDGET_TOKENS: Final[int] = 2048
ANTHROPIC_DEFAULT_REPLY_BUDGET_TOKENS: Final[int] = 8192

#: What each workforce stage asks for. A recruiter reply needs room for up to
#: sixteen ranked rows per unit across up to sixteen units, and a hire
#: compiles a whole employment contract; a critic returns a verdict and a
#: bounded code list. Unknown stages fall back to the planner's figure.
STAGE_REPLY_BUDGET_TOKENS: Final[Mapping[str, int]] = MappingProxyType(
    {
        "planner": 4096,
        "subject": 1024,
        "recruiter": 16384,
        "critic": 2048,
        "recall_reranker": 4096,
        "hiring": 16384,
        "hiring-critic": 2048,
        "hiring-repair": 16384,
        "hiring-repair-critic": 2048,
        "security_review": 4096,
        "safety_repair": 16384,
    }
)
FALLBACK_STAGE_REPLY_BUDGET_TOKENS: Final[int] = 4096

#: The thinking budget the gateway maps a forwarded ``reasoning_effort`` to for
#: the Anthropic-style deployments it fronts (``litellm/constants.py``,
#: ``DEFAULT_REASONING_EFFORT_*_THINKING_BUDGET``, 1.94.0), and which it caps
#: at ``max_tokens - 1``. Adding it to the cap is what stops the reply and the
#: thinking from sharing one budget. The OpenAI-compatible adapter forwards the
#: same levels and gets the same allowance.
THINKING_ALLOWANCE_TOKENS: Final[Mapping[str, int]] = MappingProxyType(
    {"low": 1024, "medium": 2048, "high": 4096, "xhigh": 8192}
)
_ALLOWANCE_ADAPTERS: Final[frozenset[str]] = frozenset({"litellm", "openai-compatible"})

#: The reason code an attempt carries when the reply reached the cap and could
#: not be applied. It is a transport fact, not a contract failure.
PROVIDER_RESPONSE_TRUNCATED: Final[str] = "provider_response_truncated"

# AR-392. Every transport failure used to reach the receipt as one code,
# ``provider_no_valid_response``, because the transport returned a bare
# ``None`` from eleven places with nothing in common. These name the cause
# instead, from a closed vocabulary, and both stage loops read them from here
# so that an identical failure classifies identically wherever it is seen.
#
# Failures *after* the request left. The call was made and spent its budget.
#: The runtime's own socket deadline aborted a call the gateway may well have
#: answered. Sound because the deadline handed to the transport is never
#: raised above ``provider.timeout``, so reaching it is a fact, not a guess.
PROVIDER_CALL_TIMED_OUT: Final[str] = "provider_call_timed_out"
#: The gateway answered with a non-2xx status, kept on the attempt.
PROVIDER_HTTP_STATUS_ERROR: Final[str] = "provider_http_status_error"
#: The response body was not a JSON object.
PROVIDER_RESPONSE_NOT_JSON: Final[str] = "provider_response_not_json"
#: The body was JSON and complete, and the model text inside it was not a JSON
#: object. The sibling of ``PROVIDER_RESPONSE_TRUNCATED``: nothing was cut, the
#: reply is simply not what the schema asked for.
PROVIDER_MODEL_TEXT_NOT_JSON: Final[str] = "provider_model_text_not_json"
#: The residual. Something the blanket ``except`` caught that none of the
#: named causes above recognises; honestly distinct rather than silently
#: folded into one of them.
PROVIDER_CALL_FAILED: Final[str] = "provider_call_failed"

# Refusals *before* any request left. ``failure_reason`` has meant exactly
# this since ADR-0204, and it still does: no call was made, the stage gives
# the call budget back, and the turn does not count as called.
#: The request could never be built -- a prompt, system prompt, schema, body
#: or timeout outside its bound.
PROVIDER_REQUEST_INVALID: Final[str] = "provider_request_invalid"
#: The provider is not safe to call as configured, so no call was made.
PROVIDER_UNSAFE_CONFIGURATION: Final[str] = "provider_unsafe_configuration"
#: An allowlisted CLI adapter ran and produced no object.
PROVIDER_CLI_NO_OBJECT: Final[str] = "provider_cli_no_object"

#: Codes that mean the request left the runtime. ``call_attempted`` on the
#: result is the authority; this set is what the stage loops assert against so
#: a new code cannot be added to one half of the split and not the other.
TRANSPORT_FAILURE_AFTER_REQUEST: Final[frozenset[str]] = frozenset(
    {
        PROVIDER_CALL_TIMED_OUT,
        PROVIDER_HTTP_STATUS_ERROR,
        PROVIDER_RESPONSE_NOT_JSON,
        PROVIDER_MODEL_TEXT_NOT_JSON,
        PROVIDER_CALL_FAILED,
    }
)
#: Codes that mean no request left the runtime. ``provider_credential_env_unset``
#: (ADR-0204) belongs here too; ``structured_provider`` adds it, being where it
#: is defined.
TRANSPORT_REFUSAL_BEFORE_REQUEST: Final[frozenset[str]] = frozenset(
    {
        PROVIDER_REQUEST_INVALID,
        PROVIDER_UNSAFE_CONFIGURATION,
        PROVIDER_CLI_NO_OBJECT,
    }
)


def stage_reply_budget_tokens(stage: str) -> int:
    """Return the reply budget one workforce stage owns."""

    return STAGE_REPLY_BUDGET_TOKENS.get(
        str(stage or "").strip().casefold(), FALLBACK_STAGE_REPLY_BUDGET_TOKENS
    )


def provider_for_stage(provider: ProviderEntry, stage: str) -> ProviderEntry:
    """Stamp the stage's reply budget on a provider that does not state its own.

    An operator figure on the profile or provider entry always wins; the stage
    default fills only the empty (zero) case, so a configured deployment keeps
    exactly what it was given.
    """

    if provider.reply_budget_tokens > 0:
        return provider
    return replace(provider, reply_budget_tokens=stage_reply_budget_tokens(stage))


def bounded_reply_budget_tokens(value: object) -> int:
    """Return a stated reply budget, or zero when the value is not one."""

    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    if value < MIN_REPLY_BUDGET_TOKENS or value > MAX_REPLY_BUDGET_TOKENS:
        return 0
    return value


def thinking_allowance_tokens(provider_type: str, thinking_level_forwarded: str) -> int:
    """Return the thinking tokens added to the cap for one forwarded level."""

    adapter = str(provider_type or "").strip().casefold()
    if adapter not in _ALLOWANCE_ADAPTERS:
        return 0
    return THINKING_ALLOWANCE_TOKENS.get(str(thinking_level_forwarded or "").strip().casefold(), 0)


def completion_cap_tokens(
    provider: ProviderEntry,
    *,
    thinking_level_forwarded: str = "",
) -> tuple[int, int]:
    """Return ``(reply_budget, completion_cap)`` the transport requests.

    The reply budget is what the stage or operator asked for; the completion
    cap is that budget plus the thinking allowance the adapter will spend in
    the same request, so a reply that ends exactly at the cap is a cut reply.
    """

    adapter = provider.type.strip().casefold()
    reply_budget = bounded_reply_budget_tokens(provider.reply_budget_tokens)
    if reply_budget <= 0:
        reply_budget = (
            ANTHROPIC_DEFAULT_REPLY_BUDGET_TOKENS
            if adapter == "anthropic"
            else DEFAULT_REPLY_BUDGET_TOKENS
        )
    allowance = thinking_allowance_tokens(adapter, thinking_level_forwarded)
    return reply_budget, min(reply_budget + allowance, MAX_REPLY_BUDGET_TOKENS)


__all__ = [
    "ANTHROPIC_DEFAULT_REPLY_BUDGET_TOKENS",
    "DEFAULT_REPLY_BUDGET_TOKENS",
    "FALLBACK_STAGE_REPLY_BUDGET_TOKENS",
    "PROVIDER_CALL_FAILED",
    "PROVIDER_CALL_TIMED_OUT",
    "PROVIDER_CLI_NO_OBJECT",
    "PROVIDER_HTTP_STATUS_ERROR",
    "PROVIDER_MODEL_TEXT_NOT_JSON",
    "PROVIDER_REQUEST_INVALID",
    "PROVIDER_RESPONSE_NOT_JSON",
    "PROVIDER_RESPONSE_TRUNCATED",
    "PROVIDER_UNSAFE_CONFIGURATION",
    "STAGE_REPLY_BUDGET_TOKENS",
    "TRANSPORT_FAILURE_AFTER_REQUEST",
    "TRANSPORT_REFUSAL_BEFORE_REQUEST",
    "THINKING_ALLOWANCE_TOKENS",
    "bounded_reply_budget_tokens",
    "completion_cap_tokens",
    "provider_for_stage",
    "stage_reply_budget_tokens",
    "thinking_allowance_tokens",
]
