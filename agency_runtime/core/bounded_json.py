"""Strict JSON loading with deterministic resource and structure limits."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from typing import Any


class BoundedJSONError(ValueError):
    """JSON input is malformed, ambiguous, or exceeds a safety limit."""


class DuplicateJSONKeyError(BoundedJSONError):
    """JSON contains an ambiguous duplicate object key."""


class NonFiniteJSONNumberError(BoundedJSONError):
    """JSON contains a non-standard NaN or infinity value."""


def _decode_bounded(value: str | bytes, *, maximum_bytes: int) -> str:
    if isinstance(value, bytes):
        if len(value) > maximum_bytes:
            raise BoundedJSONError("JSON exceeds the input-byte limit")
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise BoundedJSONError("JSON must be UTF-8") from exc
    if not isinstance(value, str):
        raise TypeError("JSON input must be text or bytes")
    if len(value) > maximum_bytes:
        raise BoundedJSONError("JSON exceeds the input-byte limit")
    try:
        encoded_size = len(value.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise BoundedJSONError("JSON must contain valid Unicode") from exc
    if encoded_size > maximum_bytes:
        raise BoundedJSONError("JSON exceeds the input-byte limit")
    return value


def _preflight_structure(
    text: str,
    *,
    maximum_depth: int,
    maximum_nodes: int,
) -> None:
    """Reject deep or over-wide documents before ``json.loads`` allocates them."""

    depth = 0
    nodes = 1 if text.strip() else 0
    in_string = False
    escaped = False
    containers: list[list[object]] = []

    def add_node() -> None:
        nonlocal nodes
        nodes += 1
        if nodes > maximum_nodes:
            raise BoundedJSONError("JSON exceeds the structural-node limit")

    for character in text:
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue

        if (
            containers
            and containers[-1][0] == "["
            and containers[-1][1] is False
            and not character.isspace()
            and character != "]"
        ):
            add_node()
            containers[-1][1] = True
        if character == '"':
            in_string = True
        elif character in "[{":
            depth += 1
            if depth > maximum_depth:
                raise BoundedJSONError("JSON exceeds the nesting-depth limit")
            containers.append([character, False])
        elif character == ":" or (character == "," and containers and containers[-1][0] == "["):
            add_node()
        elif character in "]}":
            depth = max(0, depth - 1)
            if containers:
                containers.pop()


def _validate(value: Any, *, maximum_depth: int, maximum_nodes: int) -> None:
    pending: list[tuple[Any, int]] = [(value, 0)]
    nodes = 0
    while pending:
        current, depth = pending.pop()
        nodes += 1
        if nodes > maximum_nodes:
            raise BoundedJSONError("JSON exceeds the structural-node limit")
        if depth > maximum_depth:
            raise BoundedJSONError("JSON exceeds the nesting-depth limit")
        if isinstance(current, Mapping):
            pending.extend((nested, depth + 1) for nested in current.values())
        elif isinstance(current, list):
            pending.extend((nested, depth + 1) for nested in current)
        elif isinstance(current, float) and not math.isfinite(current):
            raise NonFiniteJSONNumberError("JSON contains a non-finite number")
        elif current is not None and not isinstance(current, (str, bool, int, float)):
            raise BoundedJSONError(f"JSON contains unsupported value type {type(current).__name__}")


def safe_load_bounded_json(
    value: str | bytes,
    *,
    maximum_bytes: int = 8 * 1024 * 1024,
    maximum_depth: int = 64,
    maximum_nodes: int = 10_000,
) -> Any:
    """Load standards-compliant JSON while rejecting duplicates and deep trees."""
    if (
        isinstance(maximum_bytes, bool)
        or not isinstance(maximum_bytes, int)
        or not 1 <= maximum_bytes <= 64 * 1024 * 1024
    ):
        raise ValueError("maximum_bytes must be an integer from 1 through 67108864")
    if (
        isinstance(maximum_depth, bool)
        or not isinstance(maximum_depth, int)
        or not 1 <= maximum_depth <= 256
    ):
        raise ValueError("maximum_depth must be an integer from 1 through 256")
    if (
        isinstance(maximum_nodes, bool)
        or not isinstance(maximum_nodes, int)
        or not 1 <= maximum_nodes <= 1_000_000
    ):
        raise ValueError("maximum_nodes must be an integer from 1 through 1000000")
    text = _decode_bounded(value, maximum_bytes=maximum_bytes)
    _preflight_structure(
        text,
        maximum_depth=maximum_depth,
        maximum_nodes=maximum_nodes,
    )

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, nested in pairs:
            if key in result:
                raise DuplicateJSONKeyError("JSON contains a duplicate object key")
            result[key] = nested
        return result

    def reject_non_finite(_value: str) -> None:
        raise NonFiniteJSONNumberError("JSON contains a non-finite number")

    try:
        loaded = json.loads(
            text,
            object_pairs_hook=unique_object,
            parse_constant=reject_non_finite,
        )
    except BoundedJSONError:
        raise
    except (ValueError, RecursionError) as exc:
        raise BoundedJSONError("JSON is not valid bounded data") from exc
    _validate(loaded, maximum_depth=maximum_depth, maximum_nodes=maximum_nodes)
    return loaded


__all__ = [
    "BoundedJSONError",
    "DuplicateJSONKeyError",
    "NonFiniteJSONNumberError",
    "safe_load_bounded_json",
]
