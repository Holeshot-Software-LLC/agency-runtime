"""Strict YAML loading with deterministic resource and structure limits."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

import yaml
from yaml.events import (
    AliasEvent,
    MappingEndEvent,
    MappingStartEvent,
    ScalarEvent,
    SequenceEndEvent,
    SequenceStartEvent,
)


class BoundedYAMLError(ValueError):
    """YAML input exceeded a safety limit or used an ambiguous construct."""


def _decode_bounded(value: str | bytes, *, maximum_bytes: int) -> str:
    if isinstance(value, bytes):
        if len(value) > maximum_bytes:
            raise BoundedYAMLError("YAML exceeds the input-byte limit")
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise BoundedYAMLError("YAML must be UTF-8") from exc
    if not isinstance(value, str):
        raise TypeError("YAML input must be text or bytes")
    if len(value) > maximum_bytes:
        raise BoundedYAMLError("YAML exceeds the input-byte limit")
    try:
        encoded_size = len(value.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise BoundedYAMLError("YAML must contain valid Unicode") from exc
    if encoded_size > maximum_bytes:
        raise BoundedYAMLError("YAML exceeds the input-byte limit")
    return value


class _UniqueKeySafeLoader(yaml.SafeLoader):
    def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> dict[Any, Any]:
        self.flatten_mapping(node)
        result: dict[Any, Any] = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                duplicate = key in result
            except TypeError as exc:
                raise BoundedYAMLError("YAML mapping keys must be hashable") from exc
            if duplicate:
                raise BoundedYAMLError("YAML contains a duplicate mapping key")
            result[key] = self.construct_object(value_node, deep=deep)
        return result


def _preflight(text: str, *, maximum_depth: int, maximum_nodes: int) -> None:
    depth = 0
    nodes = 0
    for event in yaml.parse(text, Loader=yaml.SafeLoader):
        if isinstance(event, AliasEvent):
            raise BoundedYAMLError("YAML aliases are not supported")
        if isinstance(event, (MappingStartEvent, SequenceStartEvent)):
            depth += 1
            nodes += 1
            if depth > maximum_depth:
                raise BoundedYAMLError("YAML exceeds the nesting-depth limit")
        elif isinstance(event, (MappingEndEvent, SequenceEndEvent)):
            depth = max(0, depth - 1)
        elif isinstance(event, ScalarEvent):
            if event.value == "<<":
                raise BoundedYAMLError("YAML merge keys are not supported")
            nodes += 1
        if nodes > maximum_nodes:
            raise BoundedYAMLError("YAML exceeds the structural-node limit")


def _validate(value: Any, *, maximum_depth: int, maximum_nodes: int) -> None:
    pending: list[tuple[Any, int]] = [(value, 0)]
    containers: set[int] = set()
    nodes = 0
    while pending:
        current, depth = pending.pop()
        nodes += 1
        if nodes > maximum_nodes:
            raise BoundedYAMLError("YAML exceeds the structural-node limit")
        if depth > maximum_depth:
            raise BoundedYAMLError("YAML exceeds the nesting-depth limit")
        if isinstance(current, Mapping):
            identity = id(current)
            if identity in containers:
                raise BoundedYAMLError("YAML contains a cycle or shared container")
            containers.add(identity)
            for key, nested in current.items():
                if not isinstance(key, str):
                    raise BoundedYAMLError("YAML mapping keys must be text")
                pending.append((nested, depth + 1))
        elif isinstance(current, (list, tuple)):
            identity = id(current)
            if identity in containers:
                raise BoundedYAMLError("YAML contains a cycle or shared container")
            containers.add(identity)
            pending.extend((nested, depth + 1) for nested in current)
        elif isinstance(current, float) and not math.isfinite(current):
            raise BoundedYAMLError("YAML contains a non-finite number")
        elif current is not None and not isinstance(current, (str, bool, int, float)):
            raise BoundedYAMLError(f"YAML contains unsupported value type {type(current).__name__}")


def safe_load_bounded(
    value: str | bytes,
    *,
    maximum_bytes: int = 8 * 1024 * 1024,
    maximum_depth: int = 64,
    maximum_nodes: int = 10_000,
) -> Any:
    """Load YAML after rejecting aliases, duplicates, cycles, and oversized trees."""
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
    try:
        _preflight(text, maximum_depth=maximum_depth, maximum_nodes=maximum_nodes)
        # The custom loader inherits SafeLoader and only tightens mapping behavior.
        loaded = yaml.load(  # nosec B506
            text,
            Loader=_UniqueKeySafeLoader,
        )
    except BoundedYAMLError:
        raise
    except (yaml.YAMLError, RecursionError) as exc:
        raise BoundedYAMLError("YAML is not valid bounded data") from exc
    _validate(loaded, maximum_depth=maximum_depth, maximum_nodes=maximum_nodes)
    return loaded


__all__ = ["BoundedYAMLError", "safe_load_bounded"]
