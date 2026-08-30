"""Cross-version support for attaching notes to exceptions."""

from __future__ import annotations


def add_exception_note(error: BaseException, note: str) -> None:
    """Attach one note while preserving Python 3.11+ ``__notes__`` behavior."""

    native_add_note = getattr(error, "add_note", None)
    if callable(native_add_note):
        native_add_note(note)
        return
    if not isinstance(note, str):
        raise TypeError(f"note must be a str, not {type(note).__name__}")
    notes = getattr(error, "__notes__", None)
    if notes is None:
        error.__notes__ = [note]
        return
    if not isinstance(notes, list):
        raise TypeError("Cannot add note: __notes__ is not a list")
    notes.append(note)


__all__ = ["add_exception_note"]
