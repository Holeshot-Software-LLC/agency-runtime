"""Regression tests for cross-version exception note support."""

from __future__ import annotations

import pytest

from agency_runtime.core.exception_notes import add_exception_note


class _LegacyError(RuntimeError):
    add_note = None


class _NativeError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("native runtime")
        self.received_notes: list[str] = []

    def add_note(self, note: str) -> None:
        self.received_notes.append(note)


def test_exception_note_fallback_preserves_notes_on_python_310() -> None:
    error = _LegacyError("legacy runtime")

    add_exception_note(error, "first cleanup failure")
    notes = error.__notes__
    add_exception_note(error, "second cleanup failure")

    assert error.__notes__ is notes
    assert error.__notes__ == [
        "first cleanup failure",
        "second cleanup failure",
    ]


def test_exception_note_uses_native_add_note_when_available() -> None:
    error = _NativeError()

    add_exception_note(error, "native cleanup failure")

    assert error.received_notes == ["native cleanup failure"]
    assert not hasattr(error, "__notes__")


def test_exception_note_fallback_rejects_non_string_note() -> None:
    error = _LegacyError("legacy runtime")

    with pytest.raises(TypeError, match=r"note must be a str, not int"):
        add_exception_note(error, 1)  # type: ignore[arg-type]

    assert not hasattr(error, "__notes__")


def test_exception_note_fallback_rejects_non_list_notes() -> None:
    error = _LegacyError("legacy runtime")
    error.__notes__ = ("existing note",)

    with pytest.raises(TypeError, match=r"__notes__ is not a list"):
        add_exception_note(error, "another cleanup failure")

    assert error.__notes__ == ("existing note",)
