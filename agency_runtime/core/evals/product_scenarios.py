"""Versioned, host-neutral contracts for complete one-shot application trials."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

PRODUCT_SCENARIO_SCHEMA_VERSION: Final[int] = 1


@dataclass(frozen=True, slots=True)
class ProductFileContract:
    path: str
    purpose: str


@dataclass(frozen=True, slots=True)
class ProductAcceptanceContract:
    check_id: str
    category: str
    requirement: str


@dataclass(frozen=True, slots=True)
class ProductScenario:
    scenario_id: str
    title: str
    outcome: str
    implementation_contract: tuple[str, ...]
    files: tuple[ProductFileContract, ...]
    acceptance: tuple[ProductAcceptanceContract, ...]
    platforms: tuple[str, ...] = ("windows", "linux")

    def prompt(self, *, trial_id: str) -> str:
        """Render a bounded build request without naming or selecting workers."""

        file_lines = "\n".join(f"- `{item.path}`: {item.purpose}" for item in self.files)
        contract_lines = "\n".join(f"- {item}" for item in self.implementation_contract)
        acceptance_lines = "\n".join(
            f"- [{item.check_id}] {item.requirement}" for item in self.acceptance
        )
        return (
            f"One-shot product evaluation `{self.scenario_id}`, trial `{trial_id}`.\n\n"
            f"Build this complete application in the current empty workspace:\n{self.outcome}\n\n"
            "Operating constraints:\n"
            "- Work only inside the current workspace.\n"
            "- Do not use network access, credentials, external services, or global installs.\n"
            "- Use only language standard libraries and runtimes already available.\n"
            "- Do not weaken, replace, or inspect the evaluator.\n"
            "- Finish implementation, tests, configuration, documentation, and recovery behavior "
            "in this single run.\n\n"
            f"Fixed implementation contract:\n{contract_lines}\n\n"
            f"Required files:\n{file_lines}\n\n"
            f"Independent acceptance contract:\n{acceptance_lines}\n\n"
            "Run the project tests before finishing. Report what was built and any genuine "
            "limitation; do not claim an acceptance check you did not execute."
        )


def _file(path: str, purpose: str) -> ProductFileContract:
    return ProductFileContract(path, purpose)


def _check(check_id: str, category: str, requirement: str) -> ProductAcceptanceContract:
    return ProductAcceptanceContract(check_id, category, requirement)


PRODUCT_SCENARIOS: Final[tuple[ProductScenario, ...]] = (
    ProductScenario(
        "python-cli-service",
        "Python task CLI",
        "A production-quality Python task manager CLI with durable JSON storage.",
        (
            "`app.py` supports `add`, `list`, and `complete` subcommands.",
            "Every command accepts `--data PATH`; machine output is JSON.",
            "Invalid input exits nonzero with a concise stderr error and never corrupts storage.",
            "Writes are atomic and portable across Windows and Linux.",
        ),
        (
            _file("app.py", "standard-library CLI implementation"),
            _file("tests/test_app.py", "meaningful unit and failure-path tests"),
            _file("README.md", "accurate setup, usage, storage, and recovery guide"),
        ),
        (
            _check("python-cli-workflow", "core-workflow", "Add, list, and complete persist."),
            _check("python-cli-errors", "error-recovery", "Malformed input is safe and clear."),
            _check("python-cli-tests", "tests", "The supplied test suite passes."),
            _check("python-cli-docs", "documentation", "README commands match behavior."),
        ),
    ),
    ProductScenario(
        "typescript-node-application",
        "TypeScript task CLI",
        "A type-safe Node.js task manager CLI implemented as directly executable TypeScript.",
        (
            "Use Node's built-in TypeScript type stripping; do not download a compiler.",
            "`src/app.ts` supports `add`, `list`, and `complete` with `--data PATH`.",
            "Machine output is JSON and durable writes are atomic.",
            "`node --experimental-strip-types --test test/app.test.ts` is the test command.",
        ),
        (
            _file("package.json", "network-free scripts and Node engine declaration"),
            _file("tsconfig.json", "strict portable TypeScript editor contract"),
            _file("src/app.ts", "typed CLI implementation"),
            _file("test/app.test.ts", "Node test-runner coverage including failure paths"),
            _file("README.md", "accurate setup, usage, and recovery guide"),
        ),
        (
            _check("typescript-cli-workflow", "core-workflow", "Typed CLI workflow persists."),
            _check("typescript-cli-errors", "error-recovery", "Invalid operations fail safely."),
            _check("typescript-cli-tests", "tests", "Node tests pass without installation."),
            _check("typescript-cli-portable", "portability", "Paths avoid shell assumptions."),
        ),
    ),
    ProductScenario(
        "python-api-typescript-dashboard",
        "Python API and TypeScript dashboard",
        "A local task API with a responsive, accessible TypeScript dashboard.",
        (
            "`server.py` exposes `create_app(data_path)` as a standard-library WSGI app.",
            "GET `/health` returns 200 JSON; GET/POST `/api/tasks` list/create tasks.",
            "POST `/api/tasks/{id}/complete` completes a task and returns its JSON record.",
            "The dashboard works without third-party assets and handles loading, empty, and error states.",
            "All state-changing API operations validate content type and input bounds.",
        ),
        (
            _file("server.py", "WSGI API, persistence, validation, and static-file service"),
            _file("tests/test_server.py", "API integration and recovery tests"),
            _file("web/index.html", "semantic accessible application shell"),
            _file("web/app.ts", "typed dashboard behavior"),
            _file("README.md", "startup, configuration, API, and dashboard guide"),
        ),
        (
            _check("fullstack-api", "integration", "API workflow and recovery are executable."),
            _check(
                "fullstack-dashboard",
                "accessibility",
                "Dashboard has keyboard and status semantics.",
            ),
            _check(
                "fullstack-security", "security", "Mutation boundaries reject malformed requests."
            ),
            _check("fullstack-docs", "documentation", "Documented startup matches the app."),
            _check("fullstack-tests", "tests", "The supplied API integration tests pass."),
        ),
    ),
    ProductScenario(
        "cross-platform-installer-config",
        "Cross-platform installer and configuration",
        "An idempotent local installer, configurator, upgrader, and uninstaller for Windows and Linux.",
        (
            "Installers accept an explicit user-writable prefix and never require elevation.",
            "PowerShell uses `-Prefix` and `-Config`; shell scripts use `--prefix` and `--config`.",
            "Install, upgrade, configure, and uninstall are idempotent and preserve user data by default.",
            "Configuration is validated against `config.schema.json` before publication.",
            "Install copies `payload/app.txt` to `<prefix>/app/app.txt` and config to `<prefix>/config/config.json`.",
            "Scripts contain no machine-specific absolute paths.",
        ),
        (
            _file("installer/install.ps1", "Windows install and upgrade flow"),
            _file("installer/uninstall.ps1", "Windows safe uninstall flow"),
            _file("installer/install.sh", "Linux install and upgrade flow"),
            _file("installer/uninstall.sh", "Linux safe uninstall flow"),
            _file("payload/app.txt", "versioned application payload used by both installers"),
            _file("config.schema.json", "bounded portable configuration contract"),
            _file("config.example.json", "valid default configuration used by smoke tests"),
            _file("README.md", "Windows/Linux install, configure, upgrade, recovery, uninstall"),
        ),
        (
            _check("installer-native", "installation", "Native platform lifecycle is idempotent."),
            _check(
                "installer-config", "configuration", "Invalid configuration is rejected safely."
            ),
            _check(
                "installer-portable",
                "portability",
                "Both platform scripts are present and portable.",
            ),
            _check("installer-docs", "documentation", "README lifecycle commands are accurate."),
        ),
    ),
    ProductScenario(
        "authenticated-data-application",
        "Authenticated SQLite application",
        "A standard-library Python application with authentication and per-user SQLite records.",
        (
            "`app.py` exposes `create_user`, `authenticate`, `put_item`, and `list_items`.",
            "Each function takes the SQLite path first; authenticated data calls take an opaque token.",
            "Passwords use salted `hashlib.pbkdf2_hmac`; plaintext passwords are never stored or logged.",
            "SQLite statements are parameterized and every data operation enforces ownership.",
            "Authentication failures do not reveal whether a user exists.",
        ),
        (
            _file("app.py", "authentication, authorization, and SQLite implementation"),
            _file("tests/test_app.py", "auth, isolation, injection, and failure-path tests"),
            _file("THREAT_MODEL.md", "assets, trust boundaries, controls, and residual risks"),
            _file("README.md", "setup, API usage, security, backup, and recovery"),
        ),
        (
            _check("auth-workflow", "core-workflow", "Users can access only their records."),
            _check("auth-passwords", "security", "Password storage uses bounded PBKDF2 evidence."),
            _check("auth-injection", "security", "SQL injection probes cannot escape ownership."),
            _check("auth-recovery", "error-recovery", "Corrupt or invalid operations fail closed."),
            _check("auth-tests", "tests", "The supplied auth and isolation tests pass."),
        ),
    ),
    ProductScenario(
        "observability-failure-recovery",
        "Observable resilient service",
        "A Python operation runner with structured telemetry and bounded failure recovery.",
        (
            "`service.py` exposes `run_operation`, `health`, and `metrics`.",
            "`run_operation(operation, max_attempts, base_delay, sleep, clock, emit, correlation_id)` "
            "accepts injectable timing and telemetry callables.",
            "The injected `emit` callable receives one JSON-serializable event dictionary.",
            "Retries use bounded exponential backoff with an injectable sleep and monotonic clock.",
            "Logs are newline-delimited JSON with correlation IDs and no secrets.",
            "A deterministic benchmark reports latency samples without inventing measurements.",
        ),
        (
            _file("service.py", "resilient operation and observability implementation"),
            _file("tests/test_service.py", "retry, exhaustion, telemetry, and concurrency tests"),
            _file("benchmark.py", "repeatable local latency measurement"),
            _file("OPERATIONS.md", "health, metrics, alerts, diagnosis, and recovery runbook"),
            _file("README.md", "configuration and startup guide"),
        ),
        (
            _check(
                "observability-signals", "observability", "Health, metrics, and logs reflect state."
            ),
            _check(
                "observability-recovery", "error-recovery", "Retries are bounded and observable."
            ),
            _check("observability-performance", "performance", "Benchmark emits real samples."),
            _check(
                "observability-operations", "documentation", "Runbook matches failure behavior."
            ),
            _check("observability-tests", "tests", "The supplied recovery tests pass."),
        ),
    ),
)

PRODUCT_SCENARIOS_BY_ID: Final[dict[str, ProductScenario]] = {
    item.scenario_id: item for item in PRODUCT_SCENARIOS
}


def product_scenario(scenario_id: str) -> ProductScenario:
    try:
        return PRODUCT_SCENARIOS_BY_ID[str(scenario_id or "").strip().casefold()]
    except KeyError as exc:
        raise ValueError("unknown product evaluation scenario") from exc


__all__ = [
    "PRODUCT_SCENARIOS",
    "PRODUCT_SCENARIOS_BY_ID",
    "PRODUCT_SCENARIO_SCHEMA_VERSION",
    "ProductAcceptanceContract",
    "ProductFileContract",
    "ProductScenario",
    "product_scenario",
]
