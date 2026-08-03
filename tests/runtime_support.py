"""Shared test-runtime boundaries for host executable fixtures."""

from __future__ import annotations

import os
import sys
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from agency_runtime.core.private_paths import ensure_private_directory
from agency_runtime.core.structured_provider import StructuredProviderResult


def is_agency_product_environment_key(name: str) -> bool:
    """Separate product configuration from reserved CI authority receipts."""

    return name.startswith("AGENCY_") and not name.startswith("AGENCY_CI_")


def trusted_test_interpreter() -> Path:
    """Return the CI-private interpreter or the local environment's base Python."""

    configured = os.environ.get("AGENCY_CI_PYTHON")
    return Path(configured or getattr(sys, "_base_executable", sys.executable)).resolve()


def trusted_base_test_interpreter() -> Path:
    """Return the real base interpreter instead of a Windows venv redirector."""

    return Path(getattr(sys, "_base_executable", sys.executable)).resolve(strict=True)


def process_has_exited(pid: int) -> bool:
    """Query one process without sending it a terminating signal."""

    if os.name != "nt":
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return True
        except PermissionError:
            return False
        return False
    import ctypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    kernel32.OpenProcess.restype = ctypes.c_void_p
    kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
    kernel32.WaitForSingleObject.restype = ctypes.c_uint32
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel32.CloseHandle.restype = ctypes.c_int
    handle = kernel32.OpenProcess(0x00100000, 0, pid)
    if not handle:
        return True
    try:
        return kernel32.WaitForSingleObject(handle, 0) == 0
    finally:
        kernel32.CloseHandle(handle)


def wait_for_process_exit(pid: int, *, timeout: float = 5) -> bool:
    """Wait boundedly for one process identity to stop."""

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process_has_exited(pid):
            return True
        time.sleep(0.01)
    return process_has_exited(pid)


def ensure_private_test_directory(path: Path, *, parents: bool = False) -> Path:
    """Create an owner-private fixture directory independent of ambient umask."""

    if not parents:
        path.mkdir(mode=0o700, parents=False, exist_ok=True)
    return ensure_private_directory(path)


def harden_private_test_file(path: Path) -> Path:
    """Make a fixture file satisfy the production owner-private file contract."""

    if os.name != "nt":
        path.chmod(0o600)
    return path


def write_provider_config(
    config_path: Path,
    *,
    db_path: Path | None = None,
    provider_name: str = "task-agency-router",
) -> None:
    """Write a minimal config that declares one inference provider.

    Per ADR-0087 the workforce path runs inference only when a provider is
    configured. Tests that exercise selection through the full
    preflight -> route -> workforce stack need a provider in the config so the
    path does not decline offline.
    """

    store_line = f"\nstore:\n  db_path: {db_path!s}\n" if db_path is not None else ""
    config_path.write_text(
        "judge:\n"
        '  model: ""\n'
        "ollama:\n"
        "  enabled: false\n"
        "providers:\n"
        f"  - name: {provider_name}\n"
        "    type: litellm\n"
        "    model: router-alias\n"
        "    base_url: https://router.example.test/v1\n"
        "    api_key: secret\n"
        f"{store_line}",
        encoding="utf-8",
    )
    harden_private_test_file(config_path)


__all__ = [
    "ensure_private_test_directory",
    "harden_private_test_file",
    "is_agency_product_environment_key",
    "process_has_exited",
    "stub_inference_invoker",
    "trusted_base_test_interpreter",
    "trusted_test_interpreter",
    "wait_for_process_exit",
    "write_provider_config",
]


def _structured(value: dict[str, Any]) -> StructuredProviderResult:
    return StructuredProviderResult(
        value=value,
        provider_name="task-agency-router",
        provider_type="litellm",
        transport="",
        requested_model="router-alias",
        model_group="router-alias",
        actual_model="gpt-5.6-mini",
        model_receipt_source="response.body.model",
        latency_ms=17,
    )


def stub_inference_invoker(
    selected_slugs: tuple[str, ...],
    *,
    artifact: str = "review-report",
    domain: str = "software-engineering",
):
    """Return a stub invoker for the workforce inference funnel.

    Serves the planner stage (compact plan with one unit needing ``artifact``)
    and the recruiter stage (a nomination ranking ``selected_slugs`` as
    required). Used by tests that exercise selection through the full
    preflight -> route -> workforce stack without a live provider (ADR-0087).
    The returned callable has the StructuredInvoker signature.
    """

    unit_id = "unit-work"
    capability = {
        "analysis": "analysis",
        "architecture-record": "architecture",
        "documentation": "documentation",
        "implementation-change": "implementation",
        "plan": "planning",
        "review-report": "review",
        "test-code": "testing",
        "test-evidence": "testing",
    }.get(artifact, "analysis")

    def _invoke(_provider, _prompt, schema, **_kwargs):
        props = schema.get("properties", {}) if isinstance(schema, Mapping) else {}
        if "request_summary" in props and "units" in props:
            return _structured(
                {
                    "request_summary": "Test request.",
                    "units": [
                        {
                            "unit_id": unit_id,
                            "outcome": "Complete the requested work.",
                            "artifact_kind": artifact,
                            "domains": [domain],
                            "stacks": [],
                            "capability_ids": [capability],
                            "novel_capability": "",
                            "depends_on": [],
                        }
                    ],
                }
            )
        ranked = [
            {
                "agent_id": slug,
                "score": round(0.99 - index * 0.05, 2),
                "classification": "required" if index == 0 else "acceptable",
                "positive_evidence": ["scope-match"],
                "negative_evidence": [],
            }
            for index, slug in enumerate(selected_slugs)
        ]
        return _structured(
            {"units": [{"unit_id": unit_id, "decision": "staff", "ranked_semantic": ranked}]}
        )

    return _invoke
