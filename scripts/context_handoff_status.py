#!/usr/bin/env python3
"""Report Codex context capacity for bounded same-task work.

Codex Desktop exposes context usage in its UI but does not inject that number
into the model-visible prompt. The local JSONL session record contains the same
token-count event. This helper reads only the active thread's newest cumulative
event and reports both the hard checkpoint reserve and the higher admission
gate for expensive live evaluations. A low cumulative reading never instructs
the caller to wait for a reset, stop, or create another task.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class ContextStatus:
    thread_id: str
    session_file: str
    timestamp: str
    used_tokens: int
    context_window: int
    remaining_tokens: int
    remaining_percent: float
    threshold_percent: float
    hard_checkpoint_percent: float
    admission_threshold_percent: float
    hard_checkpoint_required: bool
    live_evaluation_allowed: bool
    live_evaluation_blocked: bool
    protocol_action: str


def _reverse_lines(path: Path, *, block_size: int = 64 * 1024) -> Iterator[str]:
    """Yield UTF-8 JSONL records newest-first without loading the session file."""

    with path.open("rb") as stream:
        stream.seek(0, os.SEEK_END)
        position = stream.tell()
        remainder = b""
        while position:
            read_size = min(block_size, position)
            position -= read_size
            stream.seek(position)
            chunk = stream.read(read_size) + remainder
            parts = chunk.split(b"\n")
            remainder = parts.pop(0)
            for part in reversed(parts):
                if part:
                    yield part.decode("utf-8")
        if remainder:
            yield remainder.decode("utf-8")


def find_session_file(session_root: Path, thread_id: str) -> Path:
    matches = list(session_root.rglob(f"*{thread_id}.jsonl"))
    if not matches:
        raise FileNotFoundError(
            f"no Codex session record for thread {thread_id!r} under {session_root}"
        )
    return max(matches, key=lambda path: path.stat().st_mtime_ns)


def read_context_status(
    path: Path,
    *,
    thread_id: str,
    threshold_percent: float,
    admission_threshold_percent: float = 65.0,
) -> ContextStatus:
    for line in _reverse_lines(path):
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        payload = event.get("payload")
        if not isinstance(payload, dict) or payload.get("type") != "token_count":
            continue
        info = payload.get("info")
        if not isinstance(info, dict):
            continue
        usage = info.get("last_token_usage")
        if not isinstance(usage, dict):
            continue
        used_tokens = int(usage.get("total_tokens", 0))
        context_window = int(info.get("model_context_window", 0))
        if context_window <= 0 or used_tokens < 0:
            continue
        remaining_tokens = max(context_window - used_tokens, 0)
        remaining_percent = round(remaining_tokens / context_window * 100, 1)
        hard_checkpoint_required = remaining_percent <= threshold_percent
        live_evaluation_allowed = remaining_percent >= admission_threshold_percent
        if hard_checkpoint_required:
            protocol_action = "checkpoint_then_continue_same_task"
        elif live_evaluation_allowed:
            protocol_action = "live_evaluation_admitted"
        else:
            protocol_action = "bounded_non_live_only"
        return ContextStatus(
            thread_id=thread_id,
            session_file=str(path),
            timestamp=str(event.get("timestamp", "")),
            used_tokens=used_tokens,
            context_window=context_window,
            remaining_tokens=remaining_tokens,
            remaining_percent=remaining_percent,
            threshold_percent=threshold_percent,
            hard_checkpoint_percent=threshold_percent,
            admission_threshold_percent=admission_threshold_percent,
            hard_checkpoint_required=hard_checkpoint_required,
            live_evaluation_allowed=live_evaluation_allowed,
            live_evaluation_blocked=not live_evaluation_allowed,
            protocol_action=protocol_action,
        )
    raise RuntimeError(f"no valid token_count event found in {path}")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Report active Codex context capacity and checkpoint status."
    )
    parser.add_argument(
        "--thread-id",
        default=os.environ.get("CODEX_THREAD_ID", ""),
        help="Codex thread UUID; defaults to CODEX_THREAD_ID.",
    )
    parser.add_argument(
        "--session-root",
        type=Path,
        default=Path.home() / ".codex" / "sessions",
        help="Root containing Codex JSONL session records.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=50.0,
        help="Require a clean hard checkpoint at or below this percentage.",
    )
    parser.add_argument(
        "--admission-threshold",
        type=float,
        default=65.0,
        help="Allow a new expensive live evaluation at or above this percentage.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if not args.thread_id:
        print("CODEX_THREAD_ID is unavailable; pass --thread-id explicitly", file=sys.stderr)
        return 2
    if not 0 <= args.threshold <= 100:
        print("--threshold must be between 0 and 100", file=sys.stderr)
        return 2
    if not 0 <= args.admission_threshold <= 100:
        print("--admission-threshold must be between 0 and 100", file=sys.stderr)
        return 2
    if args.admission_threshold < args.threshold:
        print("--admission-threshold must be at least --threshold", file=sys.stderr)
        return 2
    try:
        session_file = find_session_file(args.session_root, args.thread_id)
        status = read_context_status(
            session_file,
            thread_id=args.thread_id,
            threshold_percent=args.threshold,
            admission_threshold_percent=args.admission_threshold,
        )
    except (FileNotFoundError, OSError, RuntimeError, UnicodeError) as error:
        print(str(error), file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(asdict(status), indent=2, sort_keys=True))
    else:
        print(
            f"{status.remaining_percent:.1f}% context remaining "
            f"({status.remaining_tokens}/{status.context_window} tokens): "
            f"{status.protocol_action}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
