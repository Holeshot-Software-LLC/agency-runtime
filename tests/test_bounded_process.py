"""Bounded-process behaviour that outlived the delegation backends.

`test_delegation_backends.py` mostly covered the ExecBackend classes and the
registry that resolved them -- Agency running a host CLI, which rule 5 says it
must not do. These two cover `run_bounded_process` itself: the hardened
subprocess primitive the installer, the host canary, and the Codex hook-trust
inspector all depend on, which only ever lived in that package by accident.
"""

from __future__ import annotations

import base64
import os
import shutil
import sys
from pathlib import Path

import pytest

from agency_runtime.core.delegation.backends import run_bounded_process

_WINDOWS_POWERSHELL_INTEGRATION_TIMEOUT_SECONDS = 60


def _fake_cli(tmp_path: Path) -> Path:
    script = tmp_path / "fake_agent.py"
    script.write_text(
        """
import json
import os
import pathlib
import sys
import time

mode = os.environ.get("FAKE_AGENT_MODE", "echo")
if mode == "echo":
    sys.stdout.write(sys.argv[-1])
elif mode == "argv":
    print(json.dumps(sys.argv[1:]))
elif mode == "env":
    names = [
        "PATH", "HTTP_PROXY", "SSL_CERT_FILE", "GH_TOKEN",
        "AWS_SECRET_ACCESS_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
        "CODEX_HOME", "CLAUDE_CONFIG_DIR",
    ]
    print(json.dumps({name: os.environ.get(name) for name in names}))
elif mode == "codex":
    prompt = sys.stdin.read()
    if capture := os.environ.get("FAKE_INPUT_CAPTURE"):
        pathlib.Path(capture).write_text(prompt, encoding="utf-8")
    print(json.dumps({"type": "thread.started", "thread_id": "thread-1"}))
    print(json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "done"}}))
    print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 1}}))
elif mode == "codex_echo":
    prompt = sys.stdin.read()
    print(json.dumps({
        "type": "item.completed",
        "item": {"type": "agent_message", "text": prompt},
        "diagnostic": prompt,
    }))
    print(json.dumps({"type": "turn.completed"}))
elif mode == "claude":
    prompt = sys.stdin.read()
    if capture := os.environ.get("FAKE_INPUT_CAPTURE"):
        pathlib.Path(capture).write_text(prompt, encoding="utf-8")
    print(json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": "done"}))
elif mode == "claude_echo":
    prompt = sys.stdin.read()
    print(json.dumps({
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "result": prompt,
        "diagnostic": prompt,
    }))
elif mode == "claude_error":
    print(json.dumps({"type": "result", "subtype": "error", "is_error": True, "result": "bad"}))
elif mode == "openclaw":
    print(json.dumps({"payloads": [{"text": "done"}], "meta": {"transport": "embedded"}}))
elif mode == "in_flight":
    print(json.dumps({"status": "in_flight", "payloads": []}))
elif mode == "invalid":
    print("not-json")
elif mode == "large":
    print("x" * 1000, end="")
elif mode == "large_both":
    chunk = "x" * 65536
    for _ in range(64):
        sys.stdout.write(chunk)
        sys.stdout.flush()
        sys.stderr.write(chunk)
        sys.stderr.flush()
elif mode == "fail":
    print("backend rejected task", file=sys.stderr)
    raise SystemExit(7)
elif mode == "fail_echo":
    print(sys.argv[-1], file=sys.stderr)
    raise SystemExit(7)
elif mode == "sleep":
    time.sleep(5)
""".lstrip(),
        encoding="utf-8",
    )
    return script


def test_bounded_process_discards_high_volume_output_while_draining(
    tmp_path: Path,
) -> None:
    script = _fake_cli(tmp_path)
    result = run_bounded_process(
        [sys.executable, str(script), "unused"],
        timeout=5,
        env={**os.environ, "FAKE_AGENT_MODE": "large_both"},
        max_output_chars=2048,
    )

    assert result.returncode == 0
    assert result.stdout_truncated is True
    assert result.stderr_truncated is True
    assert len(result.stdout) <= 2048
    assert len(result.stderr) <= 2048


@pytest.mark.skipif(
    sys.platform != "win32" or shutil.which("powershell.exe") is None,
    reason="Windows PowerShell stdin semantics",
)
@pytest.mark.parametrize(
    "payload",
    [
        "",
        "a\n" + ("é" * 2047),
        "a\nb\r\n" + ("x" * 4092),
    ],
    ids=["empty", "prefill-boundary", "asynchronous-boundary"],
)
def test_windows_powershell_receives_exact_stdin_across_pipe_boundaries(
    payload: str,
    tmp_path: Path,
) -> None:
    script = tmp_path / "read-stdin.ps1"
    script.write_text(
        "[Console]::InputEncoding = [Text.UTF8Encoding]::new($false)\n"
        "$value = [Console]::In.ReadToEnd()\n"
        "$bytes = [Text.Encoding]::UTF8.GetBytes($value)\n"
        "[Console]::Out.Write([Convert]::ToBase64String($bytes))\n",
        encoding="utf-8",
    )

    result = run_bounded_process(
        [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-File",
            str(script),
        ],
        input_text=payload,
        timeout=_WINDOWS_POWERSHELL_INTEGRATION_TIMEOUT_SECONDS,
        max_output_chars=8192,
    )

    assert result.returncode == 0
    assert base64.b64decode(result.stdout) == payload.encode("utf-8")
    assert result.stderr == ""
