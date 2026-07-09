"""Agency Runtime — Core Selector.

The 8-layer routing pipeline for specialist selection.

Public API:
    route(session_id, user_message, catalog) -> dict
    detect_work_units(message) -> dict
    build_routing_context(routing) -> str
    route_and_build_context(session_id, user_message, catalog) -> str | None
"""

from agency_runtime.core.selector.pipeline import (
    route,
    detect_work_units,
    build_routing_context,
    route_and_build_context,
    is_trivial,
    refine_query,
)
from agency_runtime.core.selector.policy import detect_actions, load_policy
from agency_runtime.core.selector.domain_expansion import expand_query
from agency_runtime.core.selector.candidate_narrow import tokenize, score_agent, pre_narrow
from agency_runtime.core.selector.judge import query_judge
from agency_runtime.core.selector.cache import cache_get, cache_put, cache_key, clear_cache
from agency_runtime.core.selector.stickiness import session_check, session_put

__all__ = [
    "route",
    "detect_work_units",
    "build_routing_context",
    "route_and_build_context",
    "is_trivial",
    "refine_query",
    "detect_actions",
    "load_policy",
    "expand_query",
    "tokenize",
    "score_agent",
    "pre_narrow",
    "query_judge",
    "cache_get",
    "cache_put",
    "cache_key",
    "clear_cache",
    "session_check",
    "session_put",
]
