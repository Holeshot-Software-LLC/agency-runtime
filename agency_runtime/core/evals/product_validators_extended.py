"""Independent probes for full-stack, installer, auth, and observability trials."""

from __future__ import annotations

import os
import re
import shutil
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Final

from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.delegation.backends import BoundedProcessResult
from agency_runtime.core.evals.product_validation import (
    MAX_PRODUCT_FILE_BYTES,
    ProcessRunner,
    ProductCheck,
    _docs_check,
    _json_stdout,
    _python_runtime,
    _read_text,
    _run,
    _successful,
)

_FULLSTACK_PROBE = r"""
import importlib.util
import io
import json
import pathlib
import sys

MAX_RESPONSE_BYTES = 1_048_576

root = pathlib.Path(sys.argv[1])
data = pathlib.Path(sys.argv[2])
spec = importlib.util.spec_from_file_location("candidate_server", root / "server.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
app = module.create_app(data)

def call(method, path, body=None, content_type="application/json"):
    payload = b"" if body is None else json.dumps(body).encode("utf-8")
    status = []
    headers = []
    def start_response(value, values):
        status.append(value)
        headers.extend(values)
    environ = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "QUERY_STRING": "",
        "CONTENT_TYPE": content_type,
        "CONTENT_LENGTH": str(len(payload)),
        "SERVER_NAME": "localhost",
        "SERVER_PORT": "80",
        "SERVER_PROTOCOL": "HTTP/1.1",
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": "http",
        "wsgi.input": io.BytesIO(payload),
        "wsgi.errors": sys.stderr,
        "wsgi.multithread": False,
        "wsgi.multiprocess": False,
        "wsgi.run_once": False,
    }
    response = app(environ, start_response)
    chunks = []
    response_size = 0
    try:
        for chunk in response:
            if not isinstance(chunk, bytes):
                raise TypeError("WSGI response chunks must be bytes")
            response_size += len(chunk)
            if response_size > MAX_RESPONSE_BYTES:
                raise ValueError("WSGI response exceeds the probe limit")
            chunks.append(chunk)
    except Exception:
        chunks = []
    finally:
        close = getattr(response, "close", None)
        if callable(close):
            close()
    raw = b"".join(chunks)
    code = int(status[0].split()[0])
    try:
        # JSON_LOAD_OWNERSHIP: this dependency-isolated generated probe cannot
        # import Agency helpers; the candidate response is byte-capped above.
        value = json.loads(raw.decode("utf-8"))
    except Exception:
        value = None
    return code, value, dict(headers)

health = call("GET", "/health")
created = call("POST", "/api/tasks", {"title": "hidden-fullstack-task"})
row = created[1] if isinstance(created[1], dict) else {}
task_id = str(row.get("id", ""))
listed = call("GET", "/api/tasks")
completed = call("POST", f"/api/tasks/{task_id}/complete") if task_id else (0, None, {})
before_bad = call("GET", "/api/tasks")[1]
bad = call("POST", "/api/tasks", {"title": "bad"}, "text/plain")
after_bad = call("GET", "/api/tasks")
rows = listed[1].get("tasks") if isinstance(listed[1], dict) else listed[1]
after_rows = after_bad[1].get("tasks") if isinstance(after_bad[1], dict) else after_bad[1]
print(json.dumps({
    "health": health[0] == 200 and isinstance(health[1], dict) and health[1].get("status") == "ok",
    "created": created[0] in {200, 201} and row.get("title") == "hidden-fullstack-task" and bool(task_id),
    "listed": listed[0] == 200 and isinstance(rows, list) and any(str(item.get("id")) == task_id for item in rows if isinstance(item, dict)),
    "completed": completed[0] == 200 and isinstance(completed[1], dict) and completed[1].get("completed") is True,
    "content_type_rejected": bad[0] in {400, 415} and before_bad == after_bad[1],
    "bounded": isinstance(after_rows, list) and len(after_rows) == 1,
}))
"""

_AUTH_PROBE = r"""
import importlib.util
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
database = pathlib.Path(sys.argv[2])
spec = importlib.util.spec_from_file_location("candidate_auth", root / "app.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
first = module.create_user(database, "alice", "correct-horse-battery")
second = module.create_user(database, "bob", "different-secret")
token_a = module.authenticate(database, "alice", "correct-horse-battery")
token_b = module.authenticate(database, "bob", "different-secret")
module.put_item(database, token_a, "alpha", "one")
module.put_item(database, token_b, "beta", "two")
rows_a = module.list_items(database, token_a)
rows_b = module.list_items(database, token_b)

def keys(rows):
    values = rows.get("items") if isinstance(rows, dict) else rows
    return {str(item.get("key")) for item in values if isinstance(item, dict)} if isinstance(values, list) else set()

injection = "mallory' OR 1=1 --"
module.create_user(database, injection, "injection-secret")
token_i = module.authenticate(database, injection, "injection-secret")
injection_rows = module.list_items(database, token_i)
errors = []
for username, password in (("alice", "wrong"), ("missing", "wrong")):
    try:
        module.authenticate(database, username, password)
    except Exception as error:
        errors.append((type(error).__name__, str(error)))
    else:
        errors.append(("", ""))
corrupt = database.with_name("corrupt.db")
corrupt.write_bytes(b"not sqlite")
try:
    module.list_items(corrupt, token_a)
except Exception:
    corrupt_closed = True
else:
    corrupt_closed = False
print(json.dumps({
    "workflow": bool(first is not None and second is not None and token_a and token_b and keys(rows_a) == {"alpha"} and keys(rows_b) == {"beta"}),
    "injection": bool(token_i and not keys(injection_rows) and keys(rows_a) == {"alpha"}),
    "auth_uniform": len(errors) == 2 and errors[0] == errors[1] and bool(errors[0][0]),
    "corrupt_closed": corrupt_closed,
}))
"""

_OBSERVABILITY_PROBE = r"""
import importlib.util
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("candidate_service", root / "service.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
attempts = []
sleeps = []
events = []
ticks = iter(float(value) for value in range(100))

def operation():
    attempts.append(1)
    if len(attempts) < 3:
        raise RuntimeError("transient secret=do-not-log")
    return "ok"

result = module.run_operation(
    operation,
    max_attempts=3,
    base_delay=0.01,
    sleep=sleeps.append,
    clock=lambda: next(ticks),
    emit=events.append,
    correlation_id="corr-hidden-1",
)
failed_events = []
try:
    module.run_operation(
        lambda: (_ for _ in ()).throw(RuntimeError("permanent")),
        max_attempts=2,
        base_delay=0.02,
        sleep=lambda value: None,
        clock=lambda: next(ticks),
        emit=failed_events.append,
        correlation_id="corr-hidden-2",
    )
except Exception:
    exhausted = True
else:
    exhausted = False
metrics = module.metrics()
health = module.health()
serialized = json.dumps(events)
print(json.dumps({
    "recovered": result == "ok" and len(attempts) == 3 and sleeps == [0.01, 0.02],
    "events": bool(events) and all(isinstance(item, dict) and item.get("correlation_id") == "corr-hidden-1" for item in events),
    "redacted": "do-not-log" not in serialized,
    "exhausted": exhausted and bool(failed_events),
    "metrics": isinstance(metrics, dict) and any(isinstance(value, (int, float)) and value > 0 for value in metrics.values()),
    "health": isinstance(health, dict) and bool(health.get("status")),
}))
"""


def _python_probe(
    root: Path,
    temporary: Path,
    script: str,
    runner: ProcessRunner,
    *arguments: str,
) -> Mapping[str, object] | None:
    python = _python_runtime()
    if not python:
        return None
    result = _run(
        runner,
        (python, "-I", "-c", script, str(root), *arguments),
        root=root,
        temporary=temporary,
        timeout=60.0,
    )
    value = _json_stdout(result)
    return value if isinstance(value, Mapping) else None


def _project_tests(
    root: Path,
    temporary: Path,
    runner: ProcessRunner,
    check_id: str,
) -> ProductCheck:
    python = _python_runtime()
    if not python:
        return ProductCheck(check_id, "tests", False, "Python runtime unavailable")
    result = _run(
        runner,
        (python, "-m", "unittest", "discover", "-s", "tests", "-v"),
        root=root,
        temporary=temporary,
        timeout=60.0,
    )
    return ProductCheck(check_id, "tests", _successful(result), "project test command")


def _fullstack(
    root: Path,
    temporary: Path,
    runner: ProcessRunner,
) -> tuple[ProductCheck, ...]:
    probe = _python_probe(root, temporary, _FULLSTACK_PROBE, runner, str(temporary / "api.json"))
    api_ok = bool(
        probe
        and all(probe.get(key) is True for key in ("health", "created", "listed", "completed"))
    )
    security_ok = bool(
        probe and probe.get("content_type_rejected") is True and probe.get("bounded") is True
    )
    try:
        html = _read_text(root, "web/index.html").casefold()
        script = _read_text(root, "web/app.ts").casefold()
    except ValueError:
        html = script = ""
    accessibility = bool(
        re.search(r"<html[^>]+lang=", html)
        and "<main" in html
        and "<label" in html
        and "<button" in html
        and "aria-live" in html
        and "viewport" in html
        and "fetch(" in script
    )
    docs = _docs_check(root, "fullstack-docs", ("server.py", "/api/tasks", "health"))
    return (
        ProductCheck("fullstack-api", "integration", api_ok, "hidden WSGI workflow probe"),
        ProductCheck(
            "fullstack-dashboard",
            "accessibility",
            accessibility,
            "semantic shell and live-status contract",
        ),
        ProductCheck(
            "fullstack-security",
            "security",
            security_ok,
            "hidden malformed-content probe",
        ),
        docs,
        _project_tests(root, temporary, runner, "fullstack-tests"),
    )


def _installer_command(
    script: Path,
    *,
    prefix: Path,
    config: Path | None,
) -> tuple[str, ...] | None:
    if os.name == "nt":
        executable = shutil.which("pwsh") or shutil.which("powershell")
        if not executable:
            return None
        command = [
            executable,
            "-NoProfile",
            "-NonInteractive",
            "-File",
            str(script),
            "-Prefix",
            str(prefix),
        ]
        if config is not None:
            command.extend(("-Config", str(config)))
        return tuple(command)
    shell = shutil.which("sh")
    if not shell:
        return None
    command = [shell, str(script), "--prefix", str(prefix)]
    if config is not None:
        command.extend(("--config", str(config)))
    return tuple(command)


def _installer_native(
    root: Path,
    temporary: Path,
    runner: ProcessRunner,
) -> tuple[bool, bool]:
    install_name = "install.ps1" if os.name == "nt" else "install.sh"
    uninstall_name = "uninstall.ps1" if os.name == "nt" else "uninstall.sh"
    prefix = temporary / "installed"
    config = root / "config.example.json"
    install = _installer_command(root / "installer" / install_name, prefix=prefix, config=config)
    uninstall = _installer_command(root / "installer" / uninstall_name, prefix=prefix, config=None)
    if install is None or uninstall is None:
        return False, False
    first = _run(runner, install, root=root, temporary=temporary, timeout=60.0)
    second = _run(runner, install, root=root, temporary=temporary, timeout=60.0)
    payload = prefix / "app" / "app.txt"
    installed = bool(
        _successful(first)
        and _successful(second)
        and payload.is_file()
        and (prefix / "config" / "config.json").is_file()
    )
    bad = temporary / "invalid.json"
    bad.write_text("{}", encoding="utf-8")
    invalid_prefix = temporary / "invalid-install"
    invalid_command = _installer_command(
        root / "installer" / install_name,
        prefix=invalid_prefix,
        config=bad,
    )
    invalid = (
        _run(runner, invalid_command, root=root, temporary=temporary, timeout=60.0)
        if invalid_command is not None
        else BoundedProcessResult(0, "", "")
    )
    config_rejected = invalid.returncode != 0 and not (invalid_prefix / "app").exists()
    removed_first = _run(runner, uninstall, root=root, temporary=temporary, timeout=60.0)
    removed_second = _run(runner, uninstall, root=root, temporary=temporary, timeout=60.0)
    lifecycle = bool(
        installed
        and _successful(removed_first)
        and _successful(removed_second)
        and not (prefix / "app").exists()
        and (prefix / "config" / "config.json").is_file()
    )
    return lifecycle, config_rejected


def _installer(
    root: Path,
    temporary: Path,
    runner: ProcessRunner,
) -> tuple[ProductCheck, ...]:
    lifecycle, config_rejected = _installer_native(root, temporary, runner)
    try:
        schema = safe_load_bounded_json(
            (root / "config.schema.json").read_bytes(),
            maximum_bytes=MAX_PRODUCT_FILE_BYTES,
            maximum_depth=24,
            maximum_nodes=2_000,
        )
        example = safe_load_bounded_json(
            (root / "config.example.json").read_bytes(),
            maximum_bytes=MAX_PRODUCT_FILE_BYTES,
            maximum_depth=24,
            maximum_nodes=2_000,
        )
        scripts = {
            name: _read_text(root, "installer/" + name)
            for name in ("install.ps1", "uninstall.ps1", "install.sh", "uninstall.sh")
        }
    except (OSError, TypeError, ValueError):
        schema = example = None
        scripts = {}
    schema_ok = bool(
        isinstance(schema, Mapping)
        and schema.get("type") == "object"
        and isinstance(schema.get("required"), list)
        and isinstance(example, Mapping)
        and config_rejected
    )
    joined = "\n".join(scripts.values())
    portable = bool(
        len(scripts) == 4
        and "set -" in scripts.get("install.sh", "")
        and "erroractionpreference" in scripts.get("install.ps1", "").casefold()
        and "sudo" not in joined.casefold()
        and not re.search(r"(?i)(?:[a-z]:[\\/]|/home/|/users/)", joined)
    )
    return (
        ProductCheck("installer-native", "installation", lifecycle, "native idempotent lifecycle"),
        ProductCheck(
            "installer-config", "configuration", schema_ok, "schema and invalid-config probe"
        ),
        ProductCheck("installer-portable", "portability", portable, "dual-script static contract"),
        _docs_check(root, "installer-docs", ("install.ps1", "install.sh", "uninstall", "config")),
    )


def _auth(
    root: Path,
    temporary: Path,
    runner: ProcessRunner,
) -> tuple[ProductCheck, ...]:
    database = temporary / "auth.db"
    probe = _python_probe(root, temporary, _AUTH_PROBE, runner, str(database))
    try:
        source = _read_text(root, "app.py").casefold()
        raw_database = database.read_bytes()
    except (OSError, ValueError):
        source = ""
        raw_database = b""
    passwords_safe = bool(
        probe
        and probe.get("auth_uniform") is True
        and "pbkdf2_hmac" in source
        and "compare_digest" in source
        and b"correct-horse-battery" not in raw_database
        and b"different-secret" not in raw_database
    )
    return (
        ProductCheck(
            "auth-workflow",
            "core-workflow",
            bool(probe and probe.get("workflow") is True),
            "hidden two-user isolation probe",
        ),
        ProductCheck(
            "auth-passwords", "security", passwords_safe, "database and uniform-auth inspection"
        ),
        ProductCheck(
            "auth-injection",
            "security",
            bool(probe and probe.get("injection") is True),
            "quoted-username ownership probe",
        ),
        ProductCheck(
            "auth-recovery",
            "error-recovery",
            bool(probe and probe.get("corrupt_closed") is True),
            "corrupt-database probe",
        ),
        _project_tests(root, temporary, runner, "auth-tests"),
    )


def _observability(
    root: Path,
    temporary: Path,
    runner: ProcessRunner,
) -> tuple[ProductCheck, ...]:
    probe = _python_probe(root, temporary, _OBSERVABILITY_PROBE, runner)
    signals = bool(
        probe
        and probe.get("events") is True
        and probe.get("redacted") is True
        and probe.get("metrics") is True
        and probe.get("health") is True
    )
    recovery = bool(probe and probe.get("recovered") is True and probe.get("exhausted") is True)
    python = _python_runtime()
    benchmark = (
        _run(
            runner,
            (python, "benchmark.py", "--iterations", "20", "--json"),
            root=root,
            temporary=temporary,
            timeout=60.0,
        )
        if python
        else BoundedProcessResult(1, "", "Python runtime unavailable")
    )
    measured = _json_stdout(benchmark)
    samples = measured.get("samples") if isinstance(measured, Mapping) else None
    performance = bool(
        isinstance(samples, list)
        and len(samples) >= 20
        and all(isinstance(item, (int, float)) and item >= 0 for item in samples)
        and isinstance(measured.get("p50_ms"), (int, float))
        and isinstance(measured.get("p95_ms"), (int, float))
    )
    try:
        operations = _read_text(root, "OPERATIONS.md").casefold()
    except ValueError:
        operations = ""
    docs = all(item in operations for item in ("health", "metrics", "retry", "correlation"))
    return (
        ProductCheck("observability-signals", "observability", signals, "hidden telemetry probe"),
        ProductCheck(
            "observability-recovery", "error-recovery", recovery, "retry and exhaustion probe"
        ),
        ProductCheck(
            "observability-performance", "performance", performance, "executed benchmark samples"
        ),
        ProductCheck(
            "observability-operations", "documentation", docs, "operations runbook contract"
        ),
        _project_tests(root, temporary, runner, "observability-tests"),
    )


EXTENDED_VALIDATORS: Final[
    dict[str, Callable[[Path, Path, ProcessRunner], tuple[ProductCheck, ...]]]
] = {
    "python-api-typescript-dashboard": _fullstack,
    "cross-platform-installer-config": _installer,
    "authenticated-data-application": _auth,
    "observability-failure-recovery": _observability,
}

__all__ = ["EXTENDED_VALIDATORS"]
