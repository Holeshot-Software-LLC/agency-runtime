"""Rule 5 on every host: Agency never decides to spawn, and staffs what exists.

The rule has two halves and needs both. The negative half is an absence, so it
is measured rather than asserted: every seam that can create a process is
replaced with a detector for the duration of a complete user turn, including a
turn whose request openly asks to be broken into pieces and handed out. Nothing
may reach a detector. A positive control proves the detectors would fire, so a
clean run means "Agency started nothing", not "the guard was never wired".

The positive half is that Agency's job is to staff whoever exists: when the
*host* decides to delegate, Agency records that decision and still starts
nothing itself.

Inference is stubbed, which is the point rather than a caveat -- with the one
legitimate outbound call answered in-process, any process created during the
turn would be Agency starting something on its own initiative.
"""

from __future__ import annotations

import subprocess
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from agency_runtime.adapters.claude.wrapper import ClaudeAdapter
from agency_runtime.adapters.codex.wrapper import CodexAdapter
from agency_runtime.adapters.hermes.plugin import HermesAdapter
from agency_runtime.adapters.hooks import HookBridge, hook_host_adapter
from agency_runtime.adapters.openclaw.plugin import OpenClawAdapter
from agency_runtime.core.store.sqlite import Store

# A request that asks, in as many words, to be split up and handed out. If any
# code path in Agency were willing to act on that, this is the turn that would
# make it act.
_DELEGATING_MESSAGE = (
    "1. Audit the delegation layer for unsafe process handling.\n"
    "2. Add regression coverage for whatever the audit finds."
)

_HOSTS = ("claude", "codex", "zcode", "hermes", "openclaw")

_CONFIG = """judge:
  model: ""
ollama:
  enabled: false
providers:
  - name: task-agency-router
    type: litellm
    model: router-alias
    base_url: https://router.example.test/v1
    api_key: secret
store:
  db_path: {db_path}
"""

# Every seam Agency has for creating an operating-system process. The owned
# process policy is the sanctioned one; `subprocess` itself is watched too, so
# a path that bypassed the policy would still be seen.
_LAUNCH_SEAMS: tuple[tuple[str, str], ...] = (
    ("agency_runtime.core.owned_process", "_spawn_owned_process"),
    ("agency_runtime.core.owned_process", "_spawn_owned_binary_process"),
    ("subprocess", "Popen"),
    ("subprocess", "run"),
)


class _LaunchDetector:
    """Record and refuse every attempt to create a process."""

    def __init__(self) -> None:
        self.attempts: list[str] = []

    def install(self, monkeypatch: pytest.MonkeyPatch) -> None:
        for module_name, attribute in _LAUNCH_SEAMS:

            def _refuse(*args: Any, _seam: str = f"{module_name}.{attribute}", **kwargs: Any):
                self.attempts.append(f"{_seam}{args[:1]}")
                raise AssertionError(f"Agency decided to start a process via {_seam}")

            monkeypatch.setattr(f"{module_name}.{attribute}", _refuse, raising=True)


def _configured_store(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Store:
    from tests.runtime_support import harden_private_test_file

    db_path = tmp_path / "agency.db"
    config_path = tmp_path / "agency.yaml"
    config_path.write_text(_CONFIG.format(db_path=db_path), encoding="utf-8")
    harden_private_test_file(config_path)
    monkeypatch.setenv("AGENCY_CONFIG_PATH", str(config_path))
    from agency_runtime.core.config import reset_config_cache

    reset_config_cache()
    return Store(db_path)


def _stub_inference(monkeypatch: pytest.MonkeyPatch) -> None:
    """Answer the one legitimate outbound call in-process."""

    from agency_runtime.core.workforce import inference as workforce_inference
    from tests.runtime_support import stub_inference_invoker

    monkeypatch.setattr(
        workforce_inference,
        "invoke_structured_provider_result",
        stub_inference_invoker(("code-reviewer",)),
    )


def _adapter_for(host: str, store: Store) -> Any:
    builders: Mapping[str, Any] = {
        "claude": lambda: ClaudeAdapter(store=store),
        "codex": lambda: CodexAdapter(store=store),
        "zcode": lambda: hook_host_adapter("zcode", store),
        "hermes": lambda: HermesAdapter(store=store),
        "openclaw": lambda: OpenClawAdapter(store=store),
    }
    adapter = builders[host]()
    assert adapter.host_name == host
    return adapter


def _take_a_turn(host: str, store: Store, *, session_id: str, trace_id: str) -> str:
    if host in {"claude", "codex", "zcode"}:
        result = HookBridge(host, store=store).handle(
            {
                "hook_event_name": "UserPromptSubmit",
                "session_id": session_id,
                "turn_id": trace_id,
                "prompt": _DELEGATING_MESSAGE,
            }
        )
        output = result.get("hookSpecificOutput") or {}
        return str(output.get("additionalContext") or "")

    adapter = _adapter_for(host, store)
    projection = adapter.pre_llm_call_handler(session_id, _DELEGATING_MESSAGE, trace_id=trace_id)
    return str((projection or {}).get("context") or "")


def test_the_launch_detector_actually_detects_a_launch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A clean run must mean "nothing started", not "the guard was never wired"."""

    detector = _LaunchDetector()
    detector.install(monkeypatch)

    with pytest.raises(AssertionError, match="decided to start a process"):
        subprocess.run(["cmd", "/c", "echo", "hello"], check=False)

    assert detector.attempts, "the detector observed nothing"


@pytest.mark.parametrize("host", _HOSTS)
def test_a_delegating_turn_makes_agency_start_nothing(
    host: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rule 5's negative half, measured on every host."""

    store = _configured_store(tmp_path, monkeypatch)
    _stub_inference(monkeypatch)
    session_id = f"{host}-r5-session"
    trace_id = f"{host}-r5-turn"
    detector = _LaunchDetector()
    detector.install(monkeypatch)

    context = _take_a_turn(host, store, session_id=session_id, trace_id=trace_id)

    assert detector.attempts == []

    # Not vacuous, and the check is the turn's own evidence rather than a
    # restatement of the stub: this request was planned, staffed, and dealt a
    # card, so the absence below is an absence at full depth.
    from agency_runtime.core.selector.delegation_detection import detect_work_units

    assert detect_work_units(_DELEGATING_MESSAGE)["delegate"] is True
    assert store.get_specialists_for_trace(session_id, trace_id) == ["code-reviewer"]
    assert "[AGENCY LOADED]" in context, context

    # Nothing was handed to anyone: no child, no worker, no delegation.
    assert store.get_delegations(trace_id) == []


@pytest.mark.parametrize("host", _HOSTS)
def test_agency_records_the_hosts_own_delegation_without_starting_it(
    host: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rule 5's positive half: spawning is the host's call, and Agency staffs it."""

    store = _configured_store(tmp_path, monkeypatch)
    adapter = _adapter_for(host, store)
    trace_id = f"{host}-r5-host-delegation"
    store.create_run(
        trace_id=trace_id,
        session_id=f"{host}-r5-host-session",
        host=host,
        user_message=_DELEGATING_MESSAGE,
        metadata={"source": "spawn-origin-absence", "request_kind": "nontrivial"},
    )
    detector = _LaunchDetector()
    detector.install(monkeypatch)

    # The host has already made its own decision and started its own child; it
    # is telling Agency after the fact.
    adapter.post_tool_call_handler(
        tool_name="delegate_task",
        args={"agent": "code-reviewer", "goal": "audit the delegation layer"},
        result={
            "agent_id": f"{host}-child",
            "native_run_id": f"{host}-run",
            "status": "completed",
        },
        session_id=f"{host}-r5-host-session",
        trace_id=trace_id,
    )

    assert detector.attempts == []
    [row] = store.get_delegations(trace_id)
    assert row["host"] == host
    assert row["backend"] == "delegate_task"
