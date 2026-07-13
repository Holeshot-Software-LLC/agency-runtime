"""Credential-isolated, bounded subprocess backends for live host canaries."""

from __future__ import annotations

import stat
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agency_runtime.core.bounded_io import FileSizeLimitError


def _facade():
    """Resolve canary dependencies at call time for monkeypatch compatibility."""

    from agency_runtime.core import canary

    return canary


def copy_bounded_auth(source: Path, destination: Path, *, host: str) -> None:
    """Copy one allowlisted bounded auth artifact into a private temp home."""
    facade = _facade()
    try:
        payload = facade.read_bounded_regular_file(
            source,
            limit=1024 * 1024,
            label=f"{host} auth artifact",
        )
    except FileSizeLimitError:
        raise ValueError(f"{host} auth artifact exceeds the safety limit") from None
    except OSError:
        raise ValueError(f"{host} auth artifact is unavailable or unsafe") from None
    from agency_runtime.core.configuration import (
        restrict_private_directory,
        restrict_private_file,
    )

    os_module = facade.os
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    restrict_private_directory(destination.parent)
    fd = os_module.open(
        destination,
        os_module.O_CREAT
        | os_module.O_EXCL
        | os_module.O_WRONLY
        | getattr(os_module, "O_BINARY", 0),
        stat.S_IRUSR | stat.S_IWUSR,
    )
    try:
        restrict_private_file(destination)
        with os_module.fdopen(fd, "wb") as stream:
            fd = -1
            stream.write(payload)
            stream.flush()
            os_module.fsync(stream.fileno())
        restrict_private_file(destination)
    except BaseException:
        if fd >= 0:
            os_module.close(fd)
        destination.unlink(missing_ok=True)
        raise


def codex_isolated_plugin_enabled(value: Any) -> bool:
    if isinstance(value, dict):
        identity = str(value.get("pluginId") or value.get("name") or "").casefold()
        if (
            identity
            in {
                "agency-preflight",
                "agency-preflight@agency-runtime",
            }
            and value.get("installed") is True
            and value.get("enabled") is True
        ):
            return True
        return any(codex_isolated_plugin_enabled(child) for child in value.values())
    if isinstance(value, list):
        return any(codex_isolated_plugin_enabled(child) for child in value)
    return False


def isolated_canary_environment(
    source_env: Mapping[str, str],
    runtime_home: Path,
    db_path: Path,
) -> dict[str, str]:
    from agency_runtime.core.cli_transport import safe_cli_environment

    env = safe_cli_environment(source_env)
    isolated_home = runtime_home / "home"
    isolated_temp = runtime_home / "tmp"
    isolated_home.mkdir(parents=True, exist_ok=True, mode=0o700)
    isolated_temp.mkdir(parents=True, exist_ok=True, mode=0o700)
    for name in (
        "APPDATA",
        "HOME",
        "LOCALAPPDATA",
        "USERPROFILE",
        "XDG_CACHE_HOME",
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
        "XDG_STATE_HOME",
    ):
        env[name] = str(isolated_home)
    for name in ("TEMP", "TMP", "TMPDIR"):
        env[name] = str(isolated_temp)
    env["AGENCY_DB_PATH"] = str(db_path.resolve())
    env["AGENCY_CANARY_MODE"] = "1"
    return env


def prepare_private_host_home(
    runtime_home: Path,
    *,
    directory_name: str,
    auth_source: Path,
    auth_name: str,
    host: str,
) -> Path:
    from agency_runtime.core.configuration import restrict_private_directory

    restrict_private_directory(runtime_home)
    host_home = runtime_home / directory_name
    host_home.mkdir(mode=0o700)
    restrict_private_directory(host_home)
    _facade()._copy_bounded_auth(auth_source, host_home / auth_name, host=host)
    return host_home


def process_succeeded(result: Any) -> bool:
    return (
        result.returncode == 0
        and not result.timed_out
        and not result.stdout_truncated
        and not result.stderr_truncated
    )


def codex_output(stdout: str) -> str | None:
    events: list[dict[str, Any]] = []
    try:
        for line in stdout.splitlines():
            if not line.strip():
                continue
            event = _facade()._load_canary_json(line, maximum_bytes=256_000)
            if isinstance(event, dict):
                events.append(event)
    except (TypeError, ValueError):
        return None
    completed = any(event.get("type") == "turn.completed" for event in events)
    messages = [
        str(event["item"]["text"])
        for event in events
        if event.get("type") == "item.completed"
        and isinstance(event.get("item"), dict)
        and event["item"].get("type") == "agent_message"
        and event["item"].get("text") is not None
    ]
    return messages[-1] if completed and messages else None


def codex_canary_record(result: Any) -> dict[str, Any]:
    facade = _facade()
    completed = facade._process_succeeded(result)
    record: dict[str, Any] = {
        "backend": "codex",
        "profile_scope": "isolated-profile",
        "isolated_plugin": {
            "registered": True,
            "enabled": True,
        },
        "status": "completed" if completed else "failed",
        "exit_code": result.returncode,
        "stdout_truncated": result.stdout_truncated,
        "stderr_truncated": result.stderr_truncated,
    }
    if completed and (output := facade._codex_output(result.stdout)) is not None:
        record["output"] = output
    elif completed:
        record.update(status="failed", exit_code=1)
    return record


def claude_canary_record(result: Any) -> dict[str, Any]:
    facade = _facade()
    completed = facade._process_succeeded(result)
    record: dict[str, Any] = {
        "backend": "claude",
        "profile_scope": "isolated-profile",
        "isolated_plugin": {
            "load_requested": True,
            "registered": None,
            "enabled": None,
        },
        "status": "completed" if completed else "failed",
        "exit_code": result.returncode,
        "stdout_truncated": result.stdout_truncated,
        "stderr_truncated": result.stderr_truncated,
    }
    if not completed:
        return record
    try:
        payload = facade._load_canary_json(result.stdout, maximum_bytes=256_000)
    except (TypeError, ValueError):
        payload = None
    if isinstance(payload, dict) and payload.get("result"):
        record["output"] = payload["result"]
    else:
        record.update(status="failed", exit_code=1)
    return record


def remaining_timeout(deadline: float, *, maximum: float | None = None) -> float:
    """Return the positive remainder of one end-to-end canary deadline."""
    remaining = deadline - _facade().time.monotonic()
    if maximum is not None:
        remaining = min(remaining, maximum)
    return max(0.0, remaining)


def _timeout_record(host: str) -> dict[str, Any]:
    return {
        "backend": host,
        "profile_scope": "isolated-profile",
        "status": "timed_out",
        "exit_code": 124,
        "stdout_truncated": False,
        "stderr_truncated": False,
    }


@dataclass(frozen=True, slots=True)
class SafeCodexCanaryBackend:
    executable: str
    db_path: Path
    timeout: float
    marketplace: Path
    auth_source: Path
    process_runner: Callable[..., Any]
    source_env: Mapping[str, str]

    def _install_plugin(
        self,
        *,
        workdir: str,
        env: Mapping[str, str],
        deadline: float | None = None,
    ) -> dict[str, Any] | None:
        facade = _facade()
        if deadline is None:
            deadline = facade.time.monotonic() + self.timeout
        setup_commands = (
            [
                self.executable,
                "plugin",
                "marketplace",
                "add",
                str(self.marketplace),
                "--json",
            ],
            [
                self.executable,
                "plugin",
                "add",
                "agency-preflight@agency-runtime",
                "--json",
            ],
        )
        for argv in setup_commands:
            timeout = facade._remaining_canary_timeout(deadline, maximum=30.0)
            if timeout <= 0:
                return _timeout_record("codex")
            setup = self.process_runner(
                argv,
                timeout=timeout,
                cwd=workdir,
                env=env,
                max_output_chars=64 * 1024,
            )
            if not facade._process_succeeded(setup):
                return {
                    "backend": "codex",
                    "status": "failed",
                    "exit_code": setup.returncode or 1,
                }
        return None

    def _verify_plugin(
        self,
        *,
        workdir: str,
        env: Mapping[str, str],
        deadline: float | None = None,
    ) -> dict[str, Any] | None:
        facade = _facade()
        if deadline is None:
            deadline = facade.time.monotonic() + self.timeout
        timeout = facade._remaining_canary_timeout(deadline, maximum=30.0)
        if timeout <= 0:
            return _timeout_record("codex")
        inventory = self.process_runner(
            [
                self.executable,
                "plugin",
                "list",
                "--marketplace",
                "agency-runtime",
                "--json",
            ],
            timeout=timeout,
            cwd=workdir,
            env=env,
            max_output_chars=64 * 1024,
        )
        try:
            payload = facade._load_canary_json(
                inventory.stdout,
                maximum_bytes=64 * 1024,
            )
        except (TypeError, ValueError):
            payload = None
        if facade._process_succeeded(inventory) and facade._codex_isolated_plugin_enabled(payload):
            return None
        return {
            "backend": "codex",
            "status": "failed",
            "exit_code": inventory.returncode or 1,
            "profile_scope": "isolated-profile",
            "isolated_plugin": {
                "registered": False,
                "enabled": None,
            },
        }

    def execute(
        self,
        *,
        task: str,
        workdir: str,
        check: bool = False,
    ) -> dict[str, Any]:
        del check
        facade = _facade()
        deadline = facade.time.monotonic() + self.timeout
        with tempfile.TemporaryDirectory(
            prefix="codex-home-",
            dir=str(self.db_path.parent),
        ) as runtime:
            runtime_home = Path(runtime)
            codex_home = facade._prepare_private_host_home(
                runtime_home,
                directory_name="codex",
                auth_source=self.auth_source,
                auth_name="auth.json",
                host="Codex",
            )
            env = facade._isolated_canary_environment(
                self.source_env,
                runtime_home,
                self.db_path,
            )
            env["CODEX_HOME"] = str(codex_home)
            failure = self._install_plugin(workdir=workdir, env=env, deadline=deadline)
            if failure is None:
                failure = self._verify_plugin(workdir=workdir, env=env, deadline=deadline)
            if failure is not None:
                return failure
            timeout = facade._remaining_canary_timeout(deadline)
            if timeout <= 0:
                return _timeout_record("codex")
            result = self.process_runner(
                [self.executable, "exec", *facade.CODEX_CANARY_EXEC_OPTIONS],
                timeout=timeout,
                cwd=workdir,
                env=env,
                input_text=task,
                max_output_chars=256_000,
            )
        return facade._codex_canary_record(result)


@dataclass(frozen=True, slots=True)
class SafeClaudeCanaryBackend:
    executable: str
    db_path: Path
    timeout: float
    plugin_dir: Path
    auth_source: Path
    process_runner: Callable[..., Any]
    source_env: Mapping[str, str]

    def execute(
        self,
        *,
        task: str,
        workdir: str,
        check: bool = False,
    ) -> dict[str, Any]:
        del check
        facade = _facade()
        deadline = facade.time.monotonic() + self.timeout
        with tempfile.TemporaryDirectory(
            prefix="claude-home-",
            dir=str(self.db_path.parent),
        ) as runtime:
            runtime_home = Path(runtime)
            claude_home = facade._prepare_private_host_home(
                runtime_home,
                directory_name="claude",
                auth_source=self.auth_source,
                auth_name=".credentials.json",
                host="Claude",
            )
            env = facade._isolated_canary_environment(
                self.source_env,
                runtime_home,
                self.db_path,
            )
            env["CLAUDE_CONFIG_DIR"] = str(claude_home)
            timeout = facade._remaining_canary_timeout(deadline)
            if timeout <= 0:
                return _timeout_record("claude")
            result = self.process_runner(
                [
                    self.executable,
                    "-p",
                    "--output-format",
                    "json",
                    "--max-turns",
                    "1",
                    "--no-session-persistence",
                    "--setting-sources",
                    "",
                    "--plugin-dir",
                    str(self.plugin_dir),
                    "--tools",
                    "",
                    "--disallowedTools",
                    "mcp__*",
                    "--strict-mcp-config",
                    "--permission-mode",
                    "dontAsk",
                ],
                timeout=timeout,
                cwd=workdir,
                env=env,
                input_text=task,
                max_output_chars=256_000,
            )
        return facade._claude_canary_record(result)


def managed_target(native: Mapping[str, Any] | None, *, error: str) -> Path:
    target = str((native or {}).get("managed_target") or "").strip()
    if not target:
        raise ValueError(error)
    return Path(target)


def codex_marketplace(native: Mapping[str, Any] | None) -> Path:
    error = "managed Codex marketplace is unavailable"
    marketplace = _facade()._managed_target(native, error=error)
    manifest = marketplace / ".agents" / "plugins" / "marketplace.json"
    if not marketplace.is_dir() or not manifest.is_file():
        raise ValueError(error)
    return marketplace


def claude_plugin_dir(native: Mapping[str, Any] | None) -> Path:
    error = "managed Claude plugin is unavailable"
    marketplace = _facade()._managed_target(native, error=error)
    plugin_dir = marketplace / "plugins" / "agency-preflight"
    manifest = plugin_dir / ".claude-plugin" / "plugin.json"
    if not plugin_dir.is_dir() or not manifest.is_file():
        raise ValueError(error)
    return plugin_dir


def source_home(source_env: Mapping[str, str]) -> Path:
    return Path(source_env.get("USERPROFILE") or source_env.get("HOME") or Path.home()).expanduser()


def backend(
    host: str,
    *,
    db_path: Path,
    timeout: float,
    native: Mapping[str, Any] | None,
    resolver: Callable[[str], str | None],
    runner: Callable[..., Any] | None,
    environ: Mapping[str, str] | None,
) -> SafeCodexCanaryBackend | SafeClaudeCanaryBackend:
    from agency_runtime.core.delegation.backends import run_bounded_process

    facade = _facade()
    if host not in facade.SAFE_CANARY_HOSTS:
        raise ValueError(f"{host} has no proven safe noninteractive canary mode")
    timeout = facade._validated_timeout(timeout)
    executable = resolver(host)
    if not executable:
        raise ValueError(f"{host} executable is unavailable")
    process_runner = runner or run_bounded_process
    source_env = facade.os.environ if environ is None else environ
    home = facade._source_home(source_env)
    if host == "codex":
        original_home = Path(source_env.get("CODEX_HOME") or (home / ".codex")).expanduser()
        return SafeCodexCanaryBackend(
            executable=executable,
            db_path=db_path,
            timeout=timeout,
            marketplace=facade._codex_marketplace(native),
            auth_source=original_home / "auth.json",
            process_runner=process_runner,
            source_env=source_env,
        )

    original_home = Path(source_env.get("CLAUDE_CONFIG_DIR") or (home / ".claude")).expanduser()
    return SafeClaudeCanaryBackend(
        executable=executable,
        db_path=db_path,
        timeout=timeout,
        plugin_dir=facade._claude_plugin_dir(native),
        auth_source=original_home / ".credentials.json",
        process_runner=process_runner,
        source_env=source_env,
    )


__all__ = [
    "SafeClaudeCanaryBackend",
    "SafeCodexCanaryBackend",
    "backend",
    "claude_canary_record",
    "claude_plugin_dir",
    "codex_canary_record",
    "codex_isolated_plugin_enabled",
    "codex_marketplace",
    "codex_output",
    "copy_bounded_auth",
    "isolated_canary_environment",
    "managed_target",
    "prepare_private_host_home",
    "process_succeeded",
    "remaining_timeout",
    "source_home",
]
