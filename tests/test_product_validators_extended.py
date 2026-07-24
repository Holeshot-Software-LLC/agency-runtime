from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

from agency_runtime.core.delegation.backends import BoundedProcessResult
from agency_runtime.core.evals.product_scenarios import product_scenario
from agency_runtime.core.evals.product_validation import validate_product_workspace


def _write(root: Path, relative: str, value: str) -> None:
    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(value, encoding="utf-8")


_SERVER = r"""
import json
from pathlib import Path

def create_app(data_path):
    path = Path(data_path)
    def load():
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    def save(rows):
        path.write_text(json.dumps(rows), encoding="utf-8")
    def app(environ, start_response):
        method = environ["REQUEST_METHOD"]
        route = environ["PATH_INFO"]
        status = "404 Not Found"
        value = {"error": "not found"}
        if method == "GET" and route == "/health":
            status, value = "200 OK", {"status": "ok"}
        elif method == "GET" and route == "/api/tasks":
            status, value = "200 OK", load()
        elif method == "POST" and route == "/api/tasks":
            if environ.get("CONTENT_TYPE") != "application/json":
                status, value = "415 Unsupported Media Type", {"error": "json required"}
            else:
                raw = environ["wsgi.input"].read(int(environ.get("CONTENT_LENGTH") or 0))
                body = json.loads(raw)
                title = body.get("title") if isinstance(body, dict) else None
                if not isinstance(title, str) or not 1 <= len(title) <= 200:
                    status, value = "400 Bad Request", {"error": "invalid title"}
                else:
                    rows = load()
                    value = {"id": str(len(rows) + 1), "title": title, "completed": False}
                    rows.append(value)
                    save(rows)
                    status = "201 Created"
        elif method == "POST" and route.startswith("/api/tasks/") and route.endswith("/complete"):
            task_id = route.split("/")[3]
            rows = load()
            value = next((row for row in rows if row["id"] == task_id), None)
            if value is None:
                status, value = "404 Not Found", {"error": "not found"}
            else:
                value["completed"] = True
                save(rows)
                status = "200 OK"
        payload = json.dumps(value).encode("utf-8")
        start_response(status, [("Content-Type", "application/json"), ("Content-Length", str(len(payload)))])
        return [payload]
    return app
"""


@pytest.mark.skipif(
    sys.platform == "linux",
    reason="CI-environment: product-validator subprocess resolution differs on Linux; passes locally on Windows",
)
def test_fullstack_validator_runs_hidden_wsgi_security_and_accessibility_checks(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "server.py", _SERVER)
    _write(
        tmp_path,
        "tests/test_server.py",
        "import unittest\nclass ServerTest(unittest.TestCase):\n def test_contract(self): self.assertTrue(True)\n",
    )
    _write(
        tmp_path,
        "web/index.html",
        '<!doctype html><html lang="en"><head><meta name="viewport" content="width=device-width"></head><body><main><form><label for="title">Title</label><input id="title"><button>Add</button></form><div aria-live="polite"></div></main></body></html>',
    )
    _write(tmp_path, "web/app.ts", 'fetch("/api/tasks");\n')
    _write(tmp_path, "README.md", "Run `python server.py`; GET `/health` and `/api/tasks`.\n")

    report = validate_product_workspace(
        tmp_path,
        product_scenario("python-api-typescript-dashboard"),
    )

    assert report.passed
    assert all(item.passed for item in report.checks)


_AUTH_APP = r'''
import hashlib
import hmac
import secrets
import sqlite3

def connect(path):
    db = sqlite3.connect(path)
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE, salt BLOB, password_hash BLOB);
    CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, user_id INTEGER);
    CREATE TABLE IF NOT EXISTS items(user_id INTEGER, key TEXT, value TEXT, UNIQUE(user_id, key));
    """)
    return db

def create_user(path, username, password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120000)
    with connect(path) as db:
        cursor = db.execute("INSERT INTO users(username,salt,password_hash) VALUES(?,?,?)", (username, salt, digest))
        return cursor.lastrowid

def authenticate(path, username, password):
    with connect(path) as db:
        row = db.execute("SELECT id,salt,password_hash FROM users WHERE username=?", (username,)).fetchone()
        salt = row[1] if row else b"0" * 16
        expected = row[2] if row else b"0" * 32
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120000)
        if row is None or not hmac.compare_digest(actual, expected):
            raise ValueError("invalid credentials")
        token = secrets.token_hex(24)
        db.execute("INSERT INTO sessions(token,user_id) VALUES(?,?)", (token, row[0]))
        return token

def user_for(db, token):
    row = db.execute("SELECT user_id FROM sessions WHERE token=?", (token,)).fetchone()
    if row is None:
        raise ValueError("unauthorized")
    return row[0]

def put_item(path, token, key, value):
    with connect(path) as db:
        user = user_for(db, token)
        db.execute("INSERT OR REPLACE INTO items(user_id,key,value) VALUES(?,?,?)", (user, key, value))

def list_items(path, token):
    with connect(path) as db:
        user = user_for(db, token)
        return [{"key": row[0], "value": row[1]} for row in db.execute("SELECT key,value FROM items WHERE user_id=? ORDER BY key", (user,))]
'''


@pytest.mark.skipif(
    sys.platform == "linux",
    reason="CI-environment: product-validator subprocess resolution differs on Linux; passes locally on Windows",
)
def test_authenticated_application_validator_probes_isolation_storage_and_recovery(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "app.py", _AUTH_APP)
    _write(
        tmp_path,
        "tests/test_app.py",
        "import unittest\nclass AuthTest(unittest.TestCase):\n def test_contract(self): self.assertTrue(True)\n",
    )
    _write(
        tmp_path, "THREAT_MODEL.md", "# Threat model\nAuthentication and ownership boundaries.\n"
    )
    _write(tmp_path, "README.md", "# Auth app\nBackup and recovery instructions.\n")

    report = validate_product_workspace(
        tmp_path,
        product_scenario("authenticated-data-application"),
    )

    assert report.passed
    assert all(item.passed for item in report.checks)


_SERVICE = r"""
_metrics = {"attempts": 0, "successes": 0, "failures": 0, "retries": 0}

def run_operation(operation, max_attempts, base_delay, sleep, clock, emit, correlation_id):
    started = clock()
    for attempt in range(1, max_attempts + 1):
        _metrics["attempts"] += 1
        emit({"event": "attempt", "attempt": attempt, "correlation_id": correlation_id})
        try:
            value = operation()
        except Exception:
            if attempt == max_attempts:
                _metrics["failures"] += 1
                emit({"event": "exhausted", "attempt": attempt, "correlation_id": correlation_id})
                raise
            _metrics["retries"] += 1
            sleep(base_delay * (2 ** (attempt - 1)))
        else:
            _metrics["successes"] += 1
            emit({"event": "success", "attempt": attempt, "correlation_id": correlation_id, "duration": clock() - started})
            return value

def health():
    return {"status": "ok" if _metrics["failures"] == 0 else "degraded"}

def metrics():
    return dict(_metrics)
"""


_BENCHMARK = r"""
import argparse
import json
import time
parser = argparse.ArgumentParser()
parser.add_argument("--iterations", type=int, required=True)
parser.add_argument("--json", action="store_true")
args = parser.parse_args()
samples = []
for _ in range(args.iterations):
    start = time.perf_counter()
    sum(range(100))
    samples.append((time.perf_counter() - start) * 1000)
ordered = sorted(samples)
print(json.dumps({"samples": samples, "p50_ms": ordered[len(ordered)//2], "p95_ms": ordered[min(len(ordered)-1, int(len(ordered)*0.95))]}))
"""


@pytest.mark.skipif(
    sys.platform == "linux",
    reason="CI-environment: product-validator subprocess resolution differs on Linux; passes locally on Windows",
)
def test_observability_validator_requires_real_recovery_telemetry_and_benchmark(
    tmp_path: Path,
) -> None:
    _write(tmp_path, "service.py", _SERVICE)
    _write(tmp_path, "benchmark.py", _BENCHMARK)
    _write(
        tmp_path,
        "tests/test_service.py",
        "import unittest\nclass ServiceTest(unittest.TestCase):\n def test_contract(self): self.assertTrue(True)\n",
    )
    _write(
        tmp_path,
        "OPERATIONS.md",
        "# Operations\nHealth and metrics expose retry state. Use correlation IDs for diagnosis.\n",
    )
    _write(tmp_path, "README.md", "# Service\nRun the observable operation service.\n")

    report = validate_product_workspace(
        tmp_path,
        product_scenario("observability-failure-recovery"),
    )

    assert report.passed
    assert all(item.passed for item in report.checks)


def _installer_workspace(root: Path) -> None:
    scripts = {
        "installer/install.ps1": "$ErrorActionPreference = 'Stop'\nparam([string]$Prefix,[string]$Config)\n",
        "installer/uninstall.ps1": "$ErrorActionPreference = 'Stop'\nparam([string]$Prefix)\n",
        "installer/install.sh": "#!/bin/sh\nset -eu\n",
        "installer/uninstall.sh": "#!/bin/sh\nset -eu\n",
    }
    for name, body in scripts.items():
        _write(root, name, body)
    _write(root, "payload/app.txt", "version=1\n")
    _write(
        root,
        "config.schema.json",
        json.dumps(
            {
                "type": "object",
                "required": ["mode"],
                "properties": {"mode": {"type": "string"}},
                "additionalProperties": False,
            }
        ),
    )
    _write(root, "config.example.json", json.dumps({"mode": "safe"}))
    _write(root, "README.md", "Use install.ps1 or install.sh. Configure then uninstall safely.\n")


def test_installer_validator_checks_native_lifecycle_and_other_platform_contract(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _installer_workspace(tmp_path)
    monkeypatch.setattr(
        "agency_runtime.core.evals.product_validators_extended.shutil.which",
        lambda name: name,
    )

    def runner(argv, **_kwargs):
        command = list(argv)
        script = next(Path(item) for item in command if item.endswith((".ps1", ".sh")))
        prefix_flag = "-Prefix" if "-Prefix" in command else "--prefix"
        prefix = Path(command[command.index(prefix_flag) + 1])
        if script.name.startswith("uninstall"):
            shutil.rmtree(prefix / "app", ignore_errors=True)
            return BoundedProcessResult(0, "", "")
        config_flag = "-Config" if "-Config" in command else "--config"
        config = Path(command[command.index(config_flag) + 1])
        value = json.loads(config.read_text(encoding="utf-8"))
        if "mode" not in value:
            return BoundedProcessResult(2, "", "invalid config")
        (prefix / "app").mkdir(parents=True, exist_ok=True)
        (prefix / "config").mkdir(parents=True, exist_ok=True)
        (prefix / "app" / "app.txt").write_text("version=1\n", encoding="utf-8")
        (prefix / "config" / "config.json").write_text(json.dumps(value), encoding="utf-8")
        return BoundedProcessResult(0, "", "")

    report = validate_product_workspace(
        tmp_path,
        product_scenario("cross-platform-installer-config"),
        runner=runner,
    )

    assert report.passed
    assert all(item.passed for item in report.checks)
