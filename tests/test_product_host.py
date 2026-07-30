from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest
import tomllib

from agency_runtime.core import canary
from agency_runtime.core.delegation.backends import BoundedProcessResult
from agency_runtime.core.evals import product_host
from agency_runtime.core.evals.product_host import execute_product_host


def _hash(prompt: str) -> str:
    return "sha256:" + hashlib.sha256(prompt.encode("utf-8")).hexdigest()


def _workspace_trust(workdir: str) -> dict[str, object]:
    normalized = str(Path(workdir).resolve())
    if os.name == "nt":
        normalized = normalized.casefold()
    return {
        "schema": "agency.codex-isolated-workspace-trust.v1",
        "status": "trusted",
        "scope": "exact-workspace",
        "workspace_hash": "sha256:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
        "persistent_profile_changed": False,
    }


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
        token = next(
            (
                line.strip()
                for line in task.splitlines()
                if line.startswith("agency-runtime-product-write-proof:")
            ),
            "",
        )
        if token:
            (Path(workdir) / ".agency-runtime-workspace-write-proof").write_text(
                token + "\n",
                encoding="utf-8",
            )
        return {
            "backend": "codex",
            "profile_scope": "isolated-profile",
            "isolated_plugin": {"registered": True, "enabled": True},
            "status": "completed",
            "exit_code": 0,
            "output": "finished",
            "workspace_trust": _workspace_trust(workdir),
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
    assert "danger-full-access" not in options
    assert "--add-dir" not in options
    assert options[-3:] == ("--model", "gpt-test", "-")
    assert observed["invocation"]["workdir"] == str(tmp_path)


def test_codex_agency_product_host_consumes_the_exact_activation_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict[str, object] = {}

    class ExactStore:
        def __init__(self, path: Path) -> None:
            observed["db_path"] = path

        def recent_runtime_activity(self, *, limit: int):
            raise AssertionError(f"legacy activity summary was requested with limit={limit}")

        def get_canary_activation_snapshot(self, *, host: str, query_hash: str):
            observed["exact_request"] = (host, query_hash)
            return {
                "schema": "agency.canary-activation-evidence.v1",
                "proven": True,
                "query_hash": query_hash,
            }

    def backend_factory(**kwargs):
        return _Backend(observed, exec_options=product_host._codex_options(kwargs["model"]))

    def evaluate(_host, *, result, evidence, **_kwargs):
        assert result["status"] == "completed"
        assert evidence["schema"] == "agency.canary-activation-evidence.v1"
        return SimpleNamespace(
            passed=True,
            failures=(),
            result_scope="isolated-profile",
            invocation={"header_valid": True},
        )

    monkeypatch.setattr(product_host, "Store", ExactStore)
    monkeypatch.setattr(product_host, "_codex_product_backend", backend_factory)
    monkeypatch.setattr(canary, "_evaluate_proof", evaluate)
    prompt = "Build the exact-snapshot product."

    result = execute_product_host(
        prompt=prompt,
        prompt_hash=_hash(prompt),
        host="codex",
        mode="agency",
        workspace=tmp_path,
        timeout=60,
        db_path=tmp_path / "agency.db",
        inspector=lambda _host: {"managed_target": str(tmp_path)},
        resolver=lambda _host: "codex",
        environ={"HOME": str(tmp_path), "PATH": ""},
    )

    executed_prompt = str(observed["invocation"]["task"])
    executed_hash = hashlib.sha256(executed_prompt.encode("utf-8")).hexdigest()
    assert observed["exact_request"] == ("codex", executed_hash)
    assert result.agency_evidence["runtime"]["schema"] == ("agency.canary-activation-evidence.v1")
    assert result.agency_evidence["workspace_trust"]["proven"] is True
    assert result.workspace_write_proven is True
    assert not (tmp_path / ".agency-runtime-workspace-write-proof").exists()


def test_codex_product_backend_trusts_only_the_isolated_trial_workspace(
    tmp_path: Path,
) -> None:
    source_home = tmp_path / "source-home"
    source_codex = source_home / ".codex"
    source_codex.mkdir(parents=True)
    (source_codex / "auth.json").write_text("{}", encoding="utf-8")
    persistent_config = source_codex / "config.toml"
    persistent_bytes = b"[projects.'persistent']\ntrust_level = \"trusted\"\n"
    persistent_config.write_bytes(persistent_bytes)
    workspace = tmp_path / "trial-workspace"
    workspace.mkdir()
    marketplace = tmp_path / "marketplace"
    manifest = marketplace / ".agents" / "plugins" / "marketplace.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("{}", encoding="utf-8")
    isolated_configs: list[str] = []

    def runner(argv, *, cwd, env, input_text=None, **_kwargs):
        config = Path(env["CODEX_HOME"]) / "config.toml"
        isolated_configs.append(config.read_text(encoding="utf-8"))
        if argv[1:3] == ["plugin", "list"]:
            return BoundedProcessResult(
                0,
                json.dumps(
                    {
                        "plugins": [
                            {
                                "pluginId": "agency-preflight@agency-runtime",
                                "installed": True,
                                "enabled": True,
                            }
                        ]
                    }
                ),
                "",
            )
        if "exec" in argv:
            stdout = "\n".join(
                (
                    json.dumps(
                        {
                            "type": "thread.started",
                            "thread_id": "00000000-0000-0000-0000-000000000001",
                        }
                    ),
                    json.dumps(
                        {
                            "type": "item.completed",
                            "item": {"id": "message", "type": "agent_message", "text": "done"},
                        }
                    ),
                    json.dumps({"type": "turn.completed"}),
                )
            )
            return BoundedProcessResult(0, stdout, "")
        return BoundedProcessResult(0, "{}", "")

    backend = product_host._codex_product_backend(
        native={"managed_target": str(marketplace)},
        db_path=tmp_path / "agency.db",
        timeout=60,
        master_enabled=True,
        model="",
        resolver=lambda _host: "codex",
        runner=runner,
        environ={"HOME": str(source_home), "PATH": ""},
        workspace=workspace,
    )

    result = backend.execute(task="build", workdir=str(workspace), check=False)

    expected = str(workspace.resolve())
    if os.name == "nt":
        expected = expected.casefold()
    assert result["status"] == "completed"
    assert result["workspace_trust"] == _workspace_trust(str(workspace))
    assert isolated_configs
    parsed = tomllib.loads(isolated_configs[0])
    assert parsed == {"projects": {expected: {"trust_level": "trusted"}}}
    assert persistent_config.read_bytes() == persistent_bytes


def test_product_host_reports_missing_workspace_write_proof_separately(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict = {}

    @dataclass(frozen=True)
    class NoWriteBackend(_Backend):
        def execute(self, *, task: str, workdir: str, check: bool):
            self.observed["invocation"] = {"task": task, "workdir": workdir, "check": check}
            return {
                "backend": "codex",
                "profile_scope": "isolated-profile",
                "isolated_plugin": {"registered": True, "enabled": True},
                "status": "completed",
                "exit_code": 0,
                "output": "finished",
                "workspace_trust": _workspace_trust(workdir),
            }

    monkeypatch.setattr(
        product_host,
        "_codex_product_backend",
        lambda **_kwargs: NoWriteBackend(observed),
    )
    monkeypatch.setattr(
        canary,
        "_evaluate_proof",
        lambda *_args, **_kwargs: SimpleNamespace(
            passed=True,
            failures=(),
            result_scope="isolated-profile",
            invocation={"header_valid": True},
        ),
    )
    prompt = "Build but fail the write proof."

    result = execute_product_host(
        prompt=prompt,
        prompt_hash=_hash(prompt),
        host="codex",
        mode="agency",
        workspace=tmp_path,
        timeout=60,
        db_path=tmp_path / "agency.db",
        inspector=lambda _host: {"managed_target": str(tmp_path)},
        resolver=lambda _host: "codex",
        environ={"HOME": str(tmp_path), "PATH": ""},
    )

    assert result.status == "completed"
    assert result.workspace_write_proven is False
    assert not result.runtime_contract_passed
    assert result.agency_evidence["workspace_write"]["reason"] == "proof_file_missing"
    assert "workspace_write_not_proven" in result.error


def test_product_host_requires_exact_workspace_trust_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: dict = {}

    @dataclass(frozen=True)
    class NoTrustBackend(_Backend):
        def execute(self, *, task: str, workdir: str, check: bool):
            record = super().execute(task=task, workdir=workdir, check=check)
            record.pop("workspace_trust")
            return record

    monkeypatch.setattr(
        product_host,
        "_codex_product_backend",
        lambda **_kwargs: NoTrustBackend(observed),
    )
    monkeypatch.setattr(
        canary,
        "_evaluate_proof",
        lambda *_args, **_kwargs: SimpleNamespace(
            passed=True,
            failures=(),
            result_scope="isolated-profile",
            invocation={"header_valid": True},
        ),
    )
    prompt = "Build without trust evidence."

    result = execute_product_host(
        prompt=prompt,
        prompt_hash=_hash(prompt),
        host="codex",
        mode="agency",
        workspace=tmp_path,
        timeout=60,
        db_path=tmp_path / "agency.db",
        inspector=lambda _host: {"managed_target": str(tmp_path)},
        resolver=lambda _host: "codex",
        environ={"HOME": str(tmp_path), "PATH": ""},
    )

    assert result.workspace_write_proven is True
    assert not result.runtime_contract_passed
    assert result.agency_evidence["workspace_trust"] == {
        "schema": "agency.codex-isolated-workspace-trust.v1",
        "proven": False,
        "status": "unproven",
        "scope": "exact-workspace",
        "workspace_hash": _workspace_trust(str(tmp_path))["workspace_hash"],
        "persistent_profile_changed": None,
        "reason": "workspace_trust_evidence_missing_or_mismatched",
    }
    assert "workspace_trust_not_proven" in result.error


def test_product_host_rejects_a_preexisting_write_proof(
    tmp_path: Path,
) -> None:
    proof = tmp_path / ".agency-runtime-workspace-write-proof"
    proof.write_text("agency-runtime-product-write-proof:spoofed\n", encoding="utf-8")
    prompt = "Build without accepting spoofed evidence."

    result = execute_product_host(
        prompt=prompt,
        prompt_hash=_hash(prompt),
        host="codex",
        mode="agency",
        workspace=tmp_path,
        timeout=60,
        db_path=tmp_path / "agency.db",
        inspector=lambda _host: pytest.fail("inspection ran after preexisting proof"),
        resolver=lambda _host: "codex",
        environ={"HOME": str(tmp_path), "PATH": ""},
    )

    assert result.status == "failed"
    assert result.workspace_write_proven is False
    assert not result.runtime_contract_passed
    assert result.error == "safe product backend preparation failed: ValueError"
    assert proof.read_text(encoding="utf-8") == ("agency-runtime-product-write-proof:spoofed\n")


def test_codex_product_backend_does_not_require_activation_rollout_topology(
    tmp_path: Path,
) -> None:
    marketplace = tmp_path / "marketplace"
    manifest = marketplace / ".agents" / "plugins" / "marketplace.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text("{}", encoding="utf-8")

    backend = product_host._codex_product_backend(
        native={"managed_target": str(marketplace)},
        db_path=tmp_path / "agency.db",
        timeout=60,
        master_enabled=True,
        model="",
        resolver=lambda _host: "codex",
        runner=None,
        environ={"HOME": str(tmp_path), "PATH": ""},
        workspace=tmp_path,
    )

    assert "--ephemeral" in backend.exec_options
    assert backend.require_exact_activation_rollout is False


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
