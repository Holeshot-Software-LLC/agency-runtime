"""AR-372: a stdio server the client abandoned must end itself.

Measured 2026-09-02. An operator's Windows box reached 98.6% commit charge
behind roughly 2,100 live Agency MCP/CLI processes with live parents, and
process creation started failing. The same shape reproduced on Linux in the
maintainer's session: two `agency_runtime.server.mcp --stdio` processes alive
16h13m and 15h28m, each still parented by a running host, each pinned to a
launcher tree two deploys old, each asleep on a stdin socket nobody would
write to again.

Closing stdin already exits cleanly. These tests pin the two bounds that
cover a client which keeps the pipe open and stops talking, and pin that
neither fires while a client is merely slow.
"""

from __future__ import annotations

import io

import pytest

from agency_runtime.core.stdio_lifetime import (
    DEFAULT_IDLE_TIMEOUT_SECONDS,
    EXIT_IDLE,
    EXIT_PARENT_GONE,
    IDLE_TIMEOUT_ENVIRONMENT_VARIABLE,
    MAX_IDLE_TIMEOUT_SECONDS,
    MIN_IDLE_TIMEOUT_SECONDS,
    ParentWatch,
    StdioLifetimeBound,
    configured_idle_timeout_seconds,
)
from agency_runtime.server.mcp import run_stdio


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _bound(clock: _Clock, **kwargs: object) -> StdioLifetimeBound:
    kwargs.setdefault("idle_timeout_seconds", 100.0)
    kwargs.setdefault("parent_watch", ParentWatch(parent_pid=1234, windows=True))
    return StdioLifetimeBound(monotonic=clock, **kwargs)  # type: ignore[arg-type]


def test_an_idle_server_ends_and_a_busy_one_does_not() -> None:
    clock = _Clock()
    bound = _bound(clock)

    clock.advance(99.0)
    assert bound.expired_reason() is None, "a slow client is not an abandoned one"

    bound.record_activity()
    clock.advance(99.0)
    assert bound.expired_reason() is None, "activity restarts the idle window"

    clock.advance(1.0)
    assert bound.expired_reason() == EXIT_IDLE


def test_a_departed_parent_ends_the_server_before_the_idle_window() -> None:
    clock = _Clock()
    alive = {"value": True}

    class _Watch(ParentWatch):
        @property
        def observable(self) -> bool:
            return True

        def alive(self) -> bool | None:
            return alive["value"]

    bound = _bound(clock, parent_watch=_Watch(parent_pid=4321, windows=False))
    assert bound.expired_reason() is None

    alive["value"] = False
    assert bound.expired_reason() == EXIT_PARENT_GONE


def test_an_unknowable_parent_never_ends_a_server() -> None:
    """Windows reuses process ids, so a pid comparison there answers about a stranger."""

    clock = _Clock()
    watch = ParentWatch(parent_pid=4321, windows=True)
    assert watch.observable is False
    assert watch.alive() is None

    bound = _bound(clock, parent_watch=watch)
    assert bound.expired_reason() is None
    clock.advance(100.0)
    # Only the idle bound may end it; an unevaluable parent check never does.
    assert bound.expired_reason() == EXIT_IDLE


def test_a_posix_parent_change_reads_as_a_departure() -> None:
    watch = ParentWatch(parent_pid=-1, windows=False)
    assert watch.observable is True
    assert watch.alive() is False, "our real ppid is never -1"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("", DEFAULT_IDLE_TIMEOUT_SECONDS),
        ("not-a-number", DEFAULT_IDLE_TIMEOUT_SECONDS),
        ("nan", DEFAULT_IDLE_TIMEOUT_SECONDS),
        ("inf", DEFAULT_IDLE_TIMEOUT_SECONDS),
        ("1", MIN_IDLE_TIMEOUT_SECONDS),
        ("999999999", MAX_IDLE_TIMEOUT_SECONDS),
        ("900", 900.0),
    ],
)
def test_the_operator_override_is_bounded(raw: str, expected: float) -> None:
    assert configured_idle_timeout_seconds({IDLE_TIMEOUT_ENVIRONMENT_VARIABLE: raw}) == float(
        expected
    )


def test_closing_stdin_still_exits_cleanly_and_stops_the_watchdog() -> None:
    clock = _Clock()
    bound = _bound(clock)

    assert run_stdio(input_stream=io.BytesIO(b""), output_stream=io.BytesIO(), lifetime=bound) == 0

    # A returned server must not leave a watchdog able to kill a later process.
    clock.advance(1_000.0)
    bound.stop()


def test_serving_a_request_records_activity() -> None:
    clock = _Clock()
    bound = _bound(clock)
    request = (
        b'{"jsonrpc":"2.0","id":1,"method":"initialize",'
        b'"params":{"protocolVersion":"2024-11-05","capabilities":{}}}\n'
    )
    clock.advance(99.0)

    run_stdio(input_stream=io.BytesIO(request), output_stream=io.BytesIO(), lifetime=bound)

    # The request reset the window, so the server is not idle-expired.
    assert bound.expired_reason() is None
