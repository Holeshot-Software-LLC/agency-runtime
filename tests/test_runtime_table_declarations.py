"""Every runtime table `agency db trim` walks must be declared everywhere it is indexed."""

from __future__ import annotations

from agency_runtime.core.store.queries import _OPEN_TRACE_RETENTION_GUARDS
from agency_runtime.core.store.schema import RUNTIME_DELETE_ORDER, RUNTIME_TABLE_TIMESTAMPS


def test_every_trimmable_table_declares_a_timestamp_and_an_open_trace_guard() -> None:
    """Adding a runtime table in one place must not break `agency db trim` in another.

    `routing_intent` shipped declared in the schema and the delete order but not in
    the retention guards, so the first `agency db trim` after it landed raised
    KeyError instead of trimming. Trim walks the delete order and indexes both other
    maps by table name, so any table it walks must exist in all three.
    """

    trimmable = set(RUNTIME_DELETE_ORDER)
    assert not trimmable - set(RUNTIME_TABLE_TIMESTAMPS)
    assert not trimmable - set(_OPEN_TRACE_RETENTION_GUARDS)
