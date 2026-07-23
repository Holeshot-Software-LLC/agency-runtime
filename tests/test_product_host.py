from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from agency_runtime.core import canary
from agency_runtime.core.evals import product_host
from agency_runtime.core.evals.product_host import execute_product_host


def _hash(prompt: str) -> str:
    return "sha256:" + hashlib.sha256(prompt.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class _Backend:
    observed: dict
    exec_options: tuple[str, ...] | None = None

    def execute(self, *, task: str, workdir: str, check: bool):
        self.observed["invocation"] = {
            "task": task,
            "workdir": workdir,
            "check": check,
            "options": self.exec_options,
        }
        return {
            "backend": "codex",
            "profile_scope": "isolated-profile",
            "isolated_plugin": {"registered": True, "enabled": True},
            "status": "completed",
            "exit_code": 0,
            "output": "finished",
        }


@pytest.mark.parametrize(("mode", "enabled"), (("agency", True), ("native-only", False)))
def test_codex_product_host_uses_isolated_workspace_write_profile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: str,
    enabled: bool,
) -> None:
    observed: dict = {}

    def backend_factory(**kwargs):
        observed["backend_kwargs"] = kwargs
        return _Backend(observed, exec_options=product_host._codex_options(kwargs["model"]))

    monkeypatch.setattr(product_host, "_codex_product_backend", backend_factory)
    monkeypatch.setattr(
        canary,
        "_evidence_delta",
        lambda before, after: {"routing": [], "finalizations": [], "receipts": []},
    )
    monkeypatch.setattr(
        canary,
        "_evidence_summary",
        lambda *_args, **_kwargs: {
            "counts": {},
            "correlated_trace_ids": [],
            "receipt_required": False,
            "receipt_proven": False,
        },
    )
    monkeypatch.setattr(
        canary,
        "_evaluate_proof",
        lambda *_args, **_kwargs: SimpleNamespace(
            passed=True,
            failures=(),
            result_scope="isolated-profile",
            invocation={"header_valid": mode == "agency"},
        ),
    )
    prompt = "Build the requested product."

    result = execute_product_host(
        prompt=prompt,
        prompt_hash=_hash(prompt),
        host="codex",
        mode=mode,
        workspace=tmp_path,
        timeout=60,
        model="gpt-test",
        db_path=tmp_path / "agency.db",
        inspector=lambda _host: {"managed_target": str(tmp_path)},
        resolver=lambda _host: "codex",
        environ={"HOME": str(tmp_path), "PATH": ""},
    )

    assert result.runtime_contract_passed
    assert result.actual_model == ""
    assert result.requested_model == "gpt-test"
    assert result.response_summary == "nonempty response captured (8 characters)"
    assert observed["backend_kwargs"]["master_enabled"] is enabled
    assert observed["backend_kwargs"]["timeout"] == 60
    assert observed["backend_kwargs"]["model"] == "gpt-test"
    options = observed["invocation"]["options"]
    assert (
        options[options.index("--sandbox")],
        options[options.index("--sandbox") + 1],
    ) == ("--sandbox", "workspace-write")
    assert options[-3:] == ("--model", "gpt-test", "-")
    assert observed["invocation"]["workdir"] == str(tmp_path)


def test_product_host_rejects_unsupported_hosts_and_prompt_drift(tmp_path: Path) -> None:
    prompt = "Build."
    with pytest.raises(ValueError, match="no proven isolated workspace-write"):
        execute_product_host(
            prompt=prompt,
            prompt_hash=_hash(prompt),
            host="openclaw",
            mode="agency",
            workspace=tmp_path,
            timeout=60,
        )
    with pytest.raises(ValueError, match="prompt hash"):
        execute_product_host(
            prompt=prompt,
            prompt_hash="sha256:" + ("0" * 64),
            host="codex",
            mode="agency",
            workspace=tmp_path,
            timeout=60,
        )


def test_product_host_returns_bounded_failure_without_fabricating_evidence(
    tmp_path: Path,
) -> None:
    prompt = "Build."

    def failed_inspector(_host: str):
        raise RuntimeError("secret detail must not cross the boundary")

    result = execute_product_host(
        prompt=prompt,
        prompt_hash=_hash(prompt),
        host="codex",
        mode="agency",
        workspace=tmp_path,
        timeout=60,
        db_path=tmp_path / "agency.db",
        inspector=failed_inspector,
    )

    assert result.status == "failed"
    assert not result.runtime_contract_passed
    assert result.agency_evidence == {}
    assert result.actual_model == ""
    assert "RuntimeError" in result.error
    assert "secret detail" not in result.error
