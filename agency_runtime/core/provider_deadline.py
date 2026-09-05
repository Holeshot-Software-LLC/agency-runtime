"""One request-scoped deadline shared by every preflight inference call."""

from __future__ import annotations

import math
import time
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from typing import Any

PREFLIGHT_CLOSE_MARGIN_SECONDS = 10.0
PROVIDER_DEADLINE_EXHAUSTED = "provider_deadline_exhausted"
HIRING_DEADLINE_EXHAUSTED = "hiring_lease_budget_exhausted"

_DEADLINE: ContextVar[float | None] = ContextVar("agency_provider_deadline", default=None)


def _earliest(deadline: float | None) -> float | None:
    current = _DEADLINE.get()
    if deadline is None:
        return current
    if not math.isfinite(deadline):
        raise ValueError("provider deadline must be finite")
    return deadline if current is None else min(deadline, current)


@contextmanager
def inference_deadline(deadline: float | None) -> Iterator[None]:
    """Bind an absolute monotonic cutoff; nested work can never extend it.

    The synchronous routing path and its transports share this context. Reset
    on every exit so another turn (or concurrent thread/task) does not inherit
    an expired budget. Direct calls without a preflight remain unchanged.
    """

    token = _DEADLINE.set(_earliest(deadline))
    try:
        yield
    finally:
        _DEADLINE.reset(token)


def remaining_provider_timeout(timeout: float, *, deadline: float | None = None) -> float:
    cutoff = _earliest(deadline)
    return float(timeout) if cutoff is None else max(0.0, min(timeout, cutoff - time.monotonic()))


def require_provider_time(timeout: float) -> float:
    remaining = remaining_provider_timeout(timeout)
    if remaining <= 0:
        raise TimeoutError(PROVIDER_DEADLINE_EXHAUSTED)
    return remaining


def bounded_preflight_route(function):
    """Apply the route request's lease to planning, recall, hiring and repairs."""

    @wraps(function)
    def bounded(*args: Any, **kwargs: Any):
        request = kwargs.get("request")
        lease = getattr(request, "hiring_deadline_monotonic", None)
        cutoff = None if lease is None else lease - PREFLIGHT_CLOSE_MARGIN_SECONDS
        with inference_deadline(cutoff):
            return function(*args, **kwargs)

    return bounded
