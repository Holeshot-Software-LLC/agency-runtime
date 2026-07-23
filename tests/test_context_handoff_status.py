from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from scripts.context_handoff_status import find_session_file, main, read_context_status


def _event(*, used: int, window: int, timestamp: str = "2026-07-22T00:00:00Z") -> str:
    return json.dumps(
        {
            "timestamp": timestamp,
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "last_token_usage": {"total_tokens": used},
                    "model_context_window": window,
                },
            },
        }
    )


def test_reads_newest_token_count_without_loading_older_records(tmp_path: Path) -> None:
    path = tmp_path / "rollout-thread-123.jsonl"
    path.write_text(
        "\n".join(
            [
                _event(used=25, window=100, timestamp="old"),
                "not-json",
                _event(used=60, window=100, timestamp="new"),
            ]
        ),
        encoding="utf-8",
    )

    status = read_context_status(path, thread_id="thread-123", threshold_percent=50)

    assert status.timestamp == "new"
    assert status.remaining_tokens == 40
    assert status.remaining_percent == 40.0
    assert status.hard_checkpoint_required is True
    assert status.protocol_action == "ensure_clean_checkpoint_then_continue_same_task"


def test_finds_the_active_thread_record(tmp_path: Path) -> None:
    older = tmp_path / "2026" / "01" / "rollout-thread-123.jsonl"
    newer = tmp_path / "2026" / "02" / "rollout-thread-123.jsonl"
    older.parent.mkdir(parents=True)
    newer.parent.mkdir(parents=True)
    older.write_text(_event(used=10, window=100), encoding="utf-8")
    newer.write_text(_event(used=20, window=100), encoding="utf-8")
    older.touch()
    newer.touch()
    newer_mtime = older.stat().st_mtime_ns + 1_000_000
    os_times = (newer_mtime, newer_mtime)
    os.utime(newer, ns=os_times)

    assert find_session_file(tmp_path, "thread-123") == newer


def test_cli_reports_json_and_threshold(tmp_path: Path, capsys) -> None:
    path = tmp_path / "rollout-thread-123.jsonl"
    path.write_text(_event(used=49, window=100), encoding="utf-8")

    result = main(
        [
            "--thread-id",
            "thread-123",
            "--session-root",
            str(tmp_path),
            "--threshold",
            "50",
            "--json",
        ]
    )

    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["remaining_percent"] == 51.0
    assert payload["hard_checkpoint_required"] is False
    assert payload["protocol_action"] == "continue_same_task"
    assert "admission_threshold_percent" not in payload
    assert "live_evaluation_allowed" not in payload
    assert "live_evaluation_blocked" not in payload


def test_cli_requires_a_thread_id(tmp_path: Path, capsys) -> None:
    assert main(["--thread-id", "", "--session-root", str(tmp_path)]) == 2
    assert "CODEX_THREAD_ID is unavailable" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("used", "hard_checkpoint", "action"),
    [
        (49, False, "continue_same_task"),
        (50, True, "ensure_clean_checkpoint_then_continue_same_task"),
        (51, True, "ensure_clean_checkpoint_then_continue_same_task"),
    ],
)
def test_hard_checkpoint_boundary_never_blocks_same_task_continuation(
    tmp_path: Path,
    used: int,
    hard_checkpoint: bool,
    action: str,
) -> None:
    path = tmp_path / "rollout-thread-123.jsonl"
    path.write_text(_event(used=used, window=100), encoding="utf-8")

    status = read_context_status(
        path,
        thread_id="thread-123",
        threshold_percent=50,
    )

    assert status.hard_checkpoint_required is hard_checkpoint
    assert status.protocol_action == action


def test_newest_cumulative_event_never_requests_an_empty_reset_wait(tmp_path: Path) -> None:
    path = tmp_path / "rollout-thread-123.jsonl"
    path.write_text(
        "\n".join(
            [
                _event(used=60, window=100, timestamp="older-cumulative"),
                _event(used=80, window=100, timestamp="newest-cumulative"),
            ]
        ),
        encoding="utf-8",
    )

    status = read_context_status(path, thread_id="thread-123", threshold_percent=50)

    assert status.timestamp == "newest-cumulative"
    assert status.protocol_action == "ensure_clean_checkpoint_then_continue_same_task"
    assert "wait" not in status.protocol_action


def test_cli_rejects_invalid_hard_checkpoint(tmp_path: Path, capsys) -> None:
    assert (
        main(
            [
                "--thread-id",
                "thread-123",
                "--session-root",
                str(tmp_path),
                "--threshold",
                "101",
            ]
        )
        == 2
    )
    assert "--threshold must be between 0 and 100" in capsys.readouterr().err
