"""Narrow authenticated dashboard broker for restricted agent controls."""

from __future__ import annotations

import hashlib
import json
import math
import os
import urllib.parse
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from agency_runtime.core.agent_activation import (
    PROTECTED_AGENT_SLUGS,
    normalize_agent_slug,
)
from agency_runtime.core.dashboard_runtime import dashboard_api_request
from agency_runtime.core.roster.ingress import (
    MAX_LIST_ITEM_BYTES,
    MAX_LIST_ITEMS,
    MAX_METADATA_TEXT_BYTES,
    MAX_SHORT_TEXT_BYTES,
)
from agency_runtime.core.roster.selector_projection import selector_roster_projection
from agency_runtime.core.selector.receipt_projection import RECEIPT_DESCRIPTION_BYTES

_PAGE_SIZE = 100
_MAX_AGENTS = 10_000
_REVISION_PREFIX = "sha256:"
_MAX_PATH_BYTES = 4096
_MAX_ROUTE_TEXT_BYTES = 64 * 1024
_MAX_SESSION_BYTES = 1024
_ROUTE_TIMEOUT_SECONDS = 245.0
_BROKER_EXECUTION_HOST = "codex"
_ROUTE_BYPASS_FIELDS = frozenset(
    {
        "schema_version",
        "session_id",
        "task",
        "routing",
        "selected",
        "considered_candidates",
        "rejected_candidates",
        "signals",
        "delegation_graph",
        "runtime_enabled",
        "status",
        "bypassed",
        "message",
        "master",
    }
)
_ROUTE_BYPASS_ROUTING_FIELDS = frozenset(
    {
        "runtime_enabled",
        "bypassed",
        "trace_id",
        "selected_ids",
        "semantic_ids",
        "confidence",
        "latency_ms",
        "status",
        "source",
        "provider",
    }
)
_SEARCH_BYPASS_FIELDS = frozenset(
    {
        "schema_version",
        "query",
        "agents",
        "count",
        "runtime_enabled",
        "status",
        "bypassed",
        "message",
        "master",
    }
)


def _bounded_integer(value: Any, field: str, *, maximum: int = _MAX_AGENTS) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= maximum:
        raise ValueError(f"dashboard agent response has invalid {field}")
    return value


def _config_identity(
    value: Mapping[str, Any],
    *,
    path_field: str,
    revision_field: str,
) -> tuple[str, str]:
    path = value.get(path_field)
    revision = value.get(revision_field)
    if (
        not isinstance(path, str)
        or not path
        or len(path.encode("utf-8")) > _MAX_PATH_BYTES
        or not Path(path).is_absolute()
    ):
        raise ValueError("dashboard agent response has invalid config path")
    if (
        not isinstance(revision, str)
        or len(revision) != len(_REVISION_PREFIX) + 64
        or not revision.startswith(_REVISION_PREFIX)
        or any(character not in "0123456789abcdef" for character in revision[7:])
    ):
        raise ValueError("dashboard agent response has invalid config revision")
    return path, revision


def _store_identity(value: Mapping[str, Any]) -> str:
    """Validate an active Store that still matches the desired config target."""

    path = value.get("store_path")
    desired = value.get("desired_store_path")
    if (
        not isinstance(path, str)
        or not isinstance(desired, str)
        or not path
        or not desired
        or len(path.encode("utf-8")) > _MAX_PATH_BYTES
        or len(desired.encode("utf-8")) > _MAX_PATH_BYTES
        or not Path(path).is_absolute()
        or not Path(desired).is_absolute()
        or os.path.normcase(os.path.abspath(path)) != os.path.normcase(os.path.abspath(desired))
        or value.get("store_restart_required") is not False
    ):
        raise ValueError("dashboard agent response has invalid store path")
    return path


def _operation_identity(value: Any) -> dict[str, str]:
    """Validate one exact server-side routing snapshot identity."""

    if not isinstance(value, Mapping) or set(value) != {
        "config_path",
        "config_revision",
        "store_path",
        "desired_store_path",
        "store_restart_required",
        "roster_revision",
        "environment_overrides",
    }:
        raise ValueError("dashboard routing response has invalid operation identity")
    path, revision = _config_identity(
        value,
        path_field="config_path",
        revision_field="config_revision",
    )
    store_path = _store_identity(value)
    roster_revision = value.get("roster_revision")
    if (
        not isinstance(roster_revision, str)
        or len(roster_revision) != 64
        or any(character not in "0123456789abcdef" for character in roster_revision)
    ):
        raise ValueError("dashboard routing response has invalid roster revision")
    if value.get("environment_overrides") != {}:
        raise ValueError("dashboard service environment overrides prevent safe brokerage")
    return {
        "config_path": path,
        "config_revision": revision,
        "store_path": store_path,
        "roster_revision": roster_revision,
    }


def _validate_master_bypass(
    value: Mapping[str, Any],
    *,
    expected_fields: frozenset[str],
) -> None:
    """Validate one authoritative no-Store response after the master turns off."""

    from agency_runtime.core.runtime_control import validate_runtime_control_document

    master = validate_runtime_control_document(value.get("master"))
    if (
        set(value) != expected_fields
        or master["enabled"] is not False
        or value.get("runtime_enabled") is not False
        or value.get("status") != "disabled"
        or value.get("bypassed") is not True
    ):
        raise ValueError("dashboard master-bypass response is invalid")


def _bounded_route_argument(
    value: Any,
    *,
    field: str,
    maximum: int,
    allow_empty: bool = False,
) -> str:
    if (
        not isinstance(value, str)
        or (not value and not allow_empty)
        or len(value.encode("utf-8")) > maximum
    ):
        raise ValueError(f"dashboard routing request has invalid {field}")
    return value


def _bounded_metadata_text(value: Any, *, maximum: int, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"dashboard agent entry {label} must be text")
    if len(value.encode("utf-8")) > maximum or any(
        (ord(character) < 32 and character not in "\t\n\r") or ord(character) == 127
        for character in value
    ):
        raise ValueError(f"dashboard agent entry {label} exceeds the broker contract")
    return value


def _bounded_taxonomy(value: Any, *, label: str) -> list[str]:
    if (
        not isinstance(value, list)
        or len(value) > MAX_LIST_ITEMS
        or not all(isinstance(item, str) for item in value)
    ):
        raise ValueError("dashboard agent entry taxonomy must contain bounded string lists")
    result: list[str] = []
    for item in value:
        text = _bounded_metadata_text(
            item,
            maximum=MAX_LIST_ITEM_BYTES,
            label=f"{label} item",
        )
        if not text or text != text.strip() or text in result:
            raise ValueError("dashboard agent entry taxonomy exceeds the broker contract")
        result.append(text)
    return result


def _agent_row(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("dashboard agent entry must be a JSON object")
    template = selector_roster_projection({"slug": "schema-probe"})
    expected_fields = set(template)
    if set(value) != expected_fields:
        raise ValueError("dashboard agent entry has unexpected fields")
    raw_slug = value.get("agent_slug")
    if not isinstance(raw_slug, str):
        raise ValueError("dashboard agent entry has invalid slug")
    slug = normalize_agent_slug(raw_slug)
    if raw_slug != slug:
        raise ValueError("dashboard agent entry slug must be canonical")
    enabled = value.get("enabled")
    protected = value.get("protected")
    routing_contract_valid = value.get("routing_contract_valid")
    if not all(isinstance(item, bool) for item in (enabled, protected, routing_contract_valid)):
        raise ValueError("dashboard agent entry controls must be JSON booleans")
    if protected is not (slug in PROTECTED_AGENT_SLUGS):
        raise ValueError("dashboard agent entry protection state is invalid")
    if not all(isinstance(value.get(field), str) for field in ("name", "division", "description")):
        raise ValueError("dashboard agent entry labels must be strings")
    for field, template_value in template.items():
        if field in {"agent_slug", "enabled", "protected", "routing_contract_valid"}:
            continue
        field_value = value.get(field)
        if isinstance(template_value, str):
            maximum = (
                MAX_METADATA_TEXT_BYTES
                if field in {"description", "expected_output_contract"}
                else MAX_SHORT_TEXT_BYTES
            )
            _bounded_metadata_text(field_value, maximum=maximum, label=field)
        elif isinstance(template_value, list):
            _bounded_taxonomy(field_value, label=field)
    disabled = {slug} if not enabled else set()
    canonical = selector_roster_projection(dict(value), disabled)
    if dict(value) != canonical:
        raise ValueError("dashboard agent entry is not a canonical selector projection")
    return {"slug": slug, **canonical}


def _agent_page(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("dashboard agent response must be a JSON object")
    path, revision = _config_identity(
        value,
        path_field="config_path",
        revision_field="config_revision",
    )
    store_path = _store_identity(value)
    if value.get("projection") != "selector":
        raise ValueError("dashboard agent response has invalid projection")
    environment_overrides = value.get("environment_overrides")
    if environment_overrides != {}:
        raise ValueError("dashboard service environment overrides prevent safe brokerage")
    roster_revision = value.get("roster_revision")
    if (
        not isinstance(roster_revision, str)
        or len(roster_revision) != 64
        or any(character not in "0123456789abcdef" for character in roster_revision)
    ):
        raise ValueError("dashboard agent response has invalid roster revision")
    raw_agents = value.get("agents")
    if not isinstance(raw_agents, list):
        raise ValueError("dashboard agent response must contain an agents list")
    rows = [_agent_row(agent) for agent in raw_agents]
    count = _bounded_integer(value.get("count"), "count", maximum=_PAGE_SIZE)
    total = _bounded_integer(value.get("total_count"), "total_count")
    enabled_count = _bounded_integer(value.get("enabled_count"), "enabled_count")
    disabled_count = _bounded_integer(value.get("disabled_count"), "disabled_count")
    limit = _bounded_integer(value.get("limit"), "limit", maximum=1000)
    truncated = value.get("truncated")
    cursor = value.get("next_cursor")
    if (
        count != len(rows)
        or count > limit
        or count > total
        or enabled_count + disabled_count != total
    ):
        raise ValueError("dashboard agent response counts are inconsistent")
    if not isinstance(truncated, bool):
        raise ValueError("dashboard agent response has invalid truncation state")
    if cursor is not None and not isinstance(cursor, str):
        raise ValueError("dashboard agent response has invalid cursor")
    if truncated:
        if not rows or cursor != rows[-1]["slug"]:
            raise ValueError("dashboard agent response has inconsistent pagination")
    elif cursor is not None:
        raise ValueError("dashboard terminal agent page cannot have a cursor")
    return {
        "path": path,
        "revision": revision,
        "store_path": store_path,
        "roster_revision": roster_revision,
        "rows": rows,
        "count": count,
        "total": total,
        "enabled_count": enabled_count,
        "disabled_count": disabled_count,
        "limit": limit,
        "truncated": truncated,
        "cursor": cursor,
    }


def _activation_row(value: Any) -> dict[str, Any]:
    """Validate one compact activation row used by list-only commands."""

    if not isinstance(value, Mapping) or set(value) != {
        "agent_slug",
        "name",
        "division",
        "enabled",
        "protected",
    }:
        raise ValueError("dashboard activation entry is invalid")
    raw_slug = value.get("agent_slug")
    if not isinstance(raw_slug, str):
        raise ValueError("dashboard activation entry has invalid slug")
    slug = normalize_agent_slug(raw_slug)
    enabled = value.get("enabled")
    protected = value.get("protected")
    if (
        slug != raw_slug
        or not isinstance(enabled, bool)
        or not isinstance(protected, bool)
        or protected is not (slug in PROTECTED_AGENT_SLUGS)
    ):
        raise ValueError("dashboard activation entry has invalid controls")
    return {
        "slug": slug,
        "name": _bounded_metadata_text(
            value.get("name"), maximum=MAX_SHORT_TEXT_BYTES, label="name"
        ),
        "division": _bounded_metadata_text(
            value.get("division"), maximum=MAX_SHORT_TEXT_BYTES, label="division"
        ),
        "enabled": enabled,
        "protected": protected,
    }


def _activation_page(value: Any) -> dict[str, Any]:
    """Validate one compact, revision-stable activation roster page."""

    if not isinstance(value, Mapping):
        raise ValueError("dashboard activation response must be a JSON object")
    path, revision = _config_identity(
        value,
        path_field="config_path",
        revision_field="config_revision",
    )
    store_path = _store_identity(value)
    if value.get("projection") != "activation" or value.get("environment_overrides") != {}:
        raise ValueError("dashboard activation response has invalid projection")
    roster_revision = value.get("roster_revision")
    if (
        not isinstance(roster_revision, str)
        or len(roster_revision) != 64
        or any(character not in "0123456789abcdef" for character in roster_revision)
    ):
        raise ValueError("dashboard activation response has invalid roster revision")
    raw_agents = value.get("agents")
    if not isinstance(raw_agents, list):
        raise ValueError("dashboard activation response must contain an agents list")
    rows = [_activation_row(agent) for agent in raw_agents]
    count = _bounded_integer(value.get("count"), "count", maximum=_PAGE_SIZE)
    total = _bounded_integer(value.get("total_count"), "total_count")
    enabled_count = _bounded_integer(value.get("enabled_count"), "enabled_count")
    disabled_count = _bounded_integer(value.get("disabled_count"), "disabled_count")
    limit = _bounded_integer(value.get("limit"), "limit", maximum=1000)
    truncated = value.get("truncated")
    cursor = value.get("next_cursor")
    if (
        count != len(rows)
        or count > limit
        or count > total
        or enabled_count + disabled_count != total
        or not isinstance(truncated, bool)
    ):
        raise ValueError("dashboard activation response counts are inconsistent")
    if truncated:
        if not rows or cursor != rows[-1]["slug"]:
            raise ValueError("dashboard activation response has inconsistent pagination")
    elif cursor is not None:
        raise ValueError("dashboard terminal activation page cannot have a cursor")
    return {
        "path": path,
        "revision": revision,
        "store_path": store_path,
        "roster_revision": roster_revision,
        "rows": rows,
        "count": count,
        "total": total,
        "enabled_count": enabled_count,
        "disabled_count": disabled_count,
        "limit": limit,
        "truncated": truncated,
        "cursor": cursor,
    }


def _broker_activation_rows() -> tuple[str, list[dict[str, Any]]]:
    """Read the complete compact activation projection through bounded pages."""

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    expected_path: str | None = None
    expected_revision: str | None = None
    expected_total: int | None = None
    expected_roster_revision: str | None = None
    expected_store_path: str | None = None
    expected_enabled_count: int | None = None
    expected_disabled_count: int | None = None
    after: str | None = None
    # Compact pages are fixed-width except for the terminal page. Enforcing
    # that contract caps a hostile service at 100 requests for 10,000 agents.
    maximum_pages = (_MAX_AGENTS + _PAGE_SIZE - 1) // _PAGE_SIZE
    for _page_number in range(maximum_pages):
        query: dict[str, Any] = {"limit": _PAGE_SIZE, "projection": "activation"}
        if after is not None:
            query["after"] = after
        response = dashboard_api_request(f"/api/roster?{urllib.parse.urlencode(query)}")
        page = _activation_page(response)
        identity = (
            page["path"],
            page["revision"],
            page["store_path"],
            page["roster_revision"],
            page["total"],
            page["enabled_count"],
            page["disabled_count"],
        )
        expected = (
            expected_path,
            expected_revision,
            expected_store_path,
            expected_roster_revision,
            expected_total,
            expected_enabled_count,
            expected_disabled_count,
        )
        if expected_path is None:
            (
                expected_path,
                expected_revision,
                expected_store_path,
                expected_roster_revision,
                expected_total,
                expected_enabled_count,
                expected_disabled_count,
            ) = identity
        elif identity != expected:
            raise ValueError("dashboard agent pages changed identity during pagination")
        for row in page["rows"]:
            slug = row["slug"]
            if slug in seen or (rows and slug <= rows[-1]["slug"]):
                raise ValueError("dashboard agent pages contain duplicate or unordered slugs")
            seen.add(slug)
            rows.append(row)
        if len(rows) > _MAX_AGENTS or len(rows) > int(expected_total):
            raise ValueError("dashboard agent pages exceed their bounded total")
        if not page["truncated"]:
            if len(rows) != expected_total:
                raise ValueError("dashboard agent pages do not match their total count")
            if (
                sum(bool(row["enabled"]) for row in rows) != expected_enabled_count
                or sum(not bool(row["enabled"]) for row in rows) != expected_disabled_count
            ):
                raise ValueError("dashboard agent rows disagree with their enabled counts")
            return str(expected_path), rows
        if page["count"] != page["limit"]:
            raise ValueError("dashboard agent page is unexpectedly short")
        after = str(page["cursor"])
    raise ValueError("dashboard agent pagination exceeded the page limit")


def broker_activation_rows() -> tuple[str, list[dict[str, Any]]]:
    """Return the exact compact activation-list projection."""

    return _broker_activation_rows()


def broker_explain_selection(
    *,
    session_id: str,
    task: str,
    limit: int,
) -> tuple[str | None, dict[str, Any]]:
    """Execute one selector explanation inside the owner-privileged service."""

    normalized_session = _bounded_route_argument(
        session_id,
        field="session_id",
        maximum=_MAX_SESSION_BYTES,
        allow_empty=True,
    )
    normalized_task = _bounded_route_argument(
        task,
        field="task",
        maximum=_MAX_ROUTE_TEXT_BYTES,
    )
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 50:
        raise ValueError("dashboard routing request has invalid limit")
    response = dashboard_api_request(
        "/api/route",
        method="POST",
        payload={
            "session_id": normalized_session,
            "task": normalized_task,
            "limit": limit,
            # The public broker descriptor is issued only to an attested Codex
            # client. Bind routing diagnostics to that native host so a
            # multi-host installation cannot become ambiguous or silently use
            # another host's execution capabilities.
            "host": _BROKER_EXECUTION_HOST,
        },
        timeout=_ROUTE_TIMEOUT_SECONDS,
    )
    if (
        not isinstance(response, Mapping)
        or response.get("schema_version") != "agency.selection_explain.v1"
        or response.get("session_id") != normalized_session
        or response.get("task") != normalized_task
        or not isinstance(response.get("routing"), Mapping)
        or not isinstance(response.get("selected"), list)
        or not isinstance(response.get("considered_candidates"), list)
        or not isinstance(response.get("rejected_candidates"), list)
        or not isinstance(response.get("signals"), Mapping)
    ):
        raise ValueError("dashboard routing response is invalid")
    if response.get("runtime_enabled") is False:
        _validate_master_bypass(response, expected_fields=_ROUTE_BYPASS_FIELDS)
        routing = response["routing"]
        if (
            response["selected"]
            or response["considered_candidates"]
            or response["rejected_candidates"]
            or set(routing) != _ROUTE_BYPASS_ROUTING_FIELDS
            or routing.get("runtime_enabled") is not False
            or routing.get("bypassed") is not True
            or routing.get("trace_id") != ""
            or routing.get("selected_ids") != []
            or routing.get("semantic_ids") != []
            or not isinstance(routing.get("confidence"), float)
            or routing.get("confidence") != 0.0
            or isinstance(routing.get("latency_ms"), bool)
            or not isinstance(routing.get("latency_ms"), int)
            or routing.get("latency_ms") != 0
            or routing.get("status") != "bypassed"
            or routing.get("source") != "master_control"
            or routing.get("provider") != "master_control"
            or response.get("signals") != {"source": "master_control"}
            or response.get("delegation_graph") != {"nodes": [], "edges": []}
            or response.get("message") != "Agency Runtime is disabled; Route Lab bypassed routing."
        ):
            raise ValueError("dashboard routing bypass response is inconsistent")
        return None, dict(response)
    identity = _operation_identity(response.get("operation_snapshot"))
    return identity["config_path"], dict(response)


def broker_policy_snapshot() -> tuple[str, dict[str, Any], set[str]]:
    """Read the bounded credential-free policy and active slug projection."""

    response = dashboard_api_request("/api/policy")
    if (
        not isinstance(response, Mapping)
        or response.get("schema_version") != "agency.policy_snapshot.v1"
        or not isinstance(response.get("policy"), Mapping)
    ):
        raise ValueError("dashboard policy response is invalid")
    identity = _operation_identity(response.get("operation_snapshot"))
    policy = dict(response["policy"])
    raw_slugs = response.get("active_slugs")
    if not isinstance(raw_slugs, list) or len(raw_slugs) > _MAX_AGENTS:
        raise ValueError("dashboard policy response has invalid active slugs")
    slugs: list[str] = []
    for raw_slug in raw_slugs:
        if not isinstance(raw_slug, str):
            raise ValueError("dashboard policy response has invalid active slugs")
        slug = normalize_agent_slug(raw_slug)
        if slug != raw_slug or slug in slugs:
            raise ValueError("dashboard policy response has invalid active slugs")
        slugs.append(slug)
    if slugs != sorted(slugs):
        raise ValueError("dashboard policy response active slugs are not ordered")
    policy_revision = response.get("policy_revision")
    expected_revision = hashlib.sha256(
        json.dumps(
            policy,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    if policy_revision != expected_revision:
        raise ValueError("dashboard policy response has invalid policy revision")
    return identity["config_path"], policy, set(slugs)


def broker_search_agents(*, query: str, limit: int) -> tuple[str | None, list[dict[str, Any]]]:
    """Search inside the owner service and return only bounded top summaries."""

    normalized_query = _bounded_route_argument(
        query,
        field="query",
        maximum=_MAX_ROUTE_TEXT_BYTES,
    )
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ValueError("dashboard search request has invalid limit")
    response = dashboard_api_request(
        "/api/search",
        method="POST",
        payload={"query": normalized_query, "limit": limit},
    )
    if (
        not isinstance(response, Mapping)
        or response.get("schema_version") != "agency.search.v1"
        or response.get("query") != normalized_query
        or not isinstance(response.get("agents"), list)
        or response.get("count") != len(response["agents"])
        or len(response["agents"]) > limit
    ):
        raise ValueError("dashboard search response is invalid")
    if response.get("runtime_enabled") is False:
        _validate_master_bypass(response, expected_fields=_SEARCH_BYPASS_FIELDS)
        if (
            response["agents"]
            or response["count"] != 0
            or response.get("message") != "Agency Runtime is disabled; search was bypassed."
        ):
            raise ValueError("dashboard search bypass response is inconsistent")
        return None, []
    identity = _operation_identity(response.get("operation_snapshot"))
    agents: list[dict[str, Any]] = []
    seen: set[str] = set()
    for value in response["agents"]:
        if not isinstance(value, Mapping) or set(value) != {
            "slug",
            "name",
            "division",
            "description",
            "score",
        }:
            raise ValueError("dashboard search result is invalid")
        raw_slug = value.get("slug")
        if not isinstance(raw_slug, str):
            raise ValueError("dashboard search result has invalid slug")
        slug = normalize_agent_slug(raw_slug)
        score = value.get("score")
        if (
            slug != raw_slug
            or slug in seen
            or isinstance(score, bool)
            or not isinstance(score, (int, float))
            or not math.isfinite(float(score))
        ):
            raise ValueError("dashboard search result is invalid")
        seen.add(slug)
        agents.append(
            {
                "slug": slug,
                "name": _bounded_metadata_text(
                    value.get("name"), maximum=MAX_SHORT_TEXT_BYTES, label="name"
                ),
                "division": _bounded_metadata_text(
                    value.get("division"), maximum=MAX_SHORT_TEXT_BYTES, label="division"
                ),
                "description": _bounded_metadata_text(
                    value.get("description"),
                    maximum=RECEIPT_DESCRIPTION_BYTES,
                    label="description",
                ),
                "score": float(score),
            }
        )
    return identity["config_path"], agents


def _lookup_agent(slug: str) -> tuple[dict[str, Any], str, str, str]:
    query = urllib.parse.urlencode({"slug": slug})
    response = dashboard_api_request(f"/api/agents/lookup?{query}")
    page = _agent_page(response)
    if (
        response.get("filter_slug") != slug
        or page["limit"] != 1
        or page["truncated"]
        or page["cursor"] is not None
        or len(page["rows"]) != 1
        or page["rows"][0]["slug"] != slug
    ):
        raise ValueError(f"agent is not present in the active roster: {slug}")
    selected = page["rows"][0]
    selected_bucket = page["enabled_count"] if selected["enabled"] else page["disabled_count"]
    if selected_bucket < 1:
        raise ValueError("dashboard agent lookup state contradicts roster totals")
    return selected, page["path"], page["revision"], page["store_path"]


__all__ = [
    "broker_activation_rows",
    "broker_explain_selection",
    "broker_policy_snapshot",
    "broker_search_agents",
]
