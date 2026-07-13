"""Shared contracts and limits for configuration transactions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

REDACTED = "***REDACTED***"
MAX_CONFIG_BYTES = 1024 * 1024
MAX_OPERATIONS = 128
LOCK_TIMEOUT_SECONDS = 5.0
RESTART_REQUIRED_PATHS = (
    "store.db_path",
    "server.host",
    "server.port",
    "server.max_body_size",
    "dashboard.port",
)

ENV_OVERRIDE_PATHS: tuple[tuple[str, str], ...] = (
    ("AGENCY_JUDGE_MODEL", "judge.model"),
    ("AGENCY_JUDGE_BASE_URL", "judge.base_url"),
    ("AGENCY_JUDGE_API_KEY", "judge.api_key"),
    ("AGENCY_JUDGE_TIMEOUT", "judge.timeout"),
    ("AGENCY_MAX_SELECTED", "judge.max_selected"),
    ("AGENCY_BYPASS_THRESHOLD", "judge.confidence_bypass_threshold"),
    ("OLLAMA_BASE_URL", "ollama.base_url"),
    ("AGENCY_OLLAMA_FALLBACK_MODEL", "ollama.model"),
    ("AGENCY_DB_PATH", "store.db_path"),
    ("AGENCY_DASHBOARD_PORT", "dashboard.port"),
    ("AGENCY_CAPTURE_CONTENT", "observability.capture_content"),
    ("AGENCY_RETENTION_DAYS", "observability.retention_days"),
    ("AGENCY_PROFILE", "profile"),
    ("LITELLM_API_KEY", "adapters.litellm.api_key"),
)


class ConfigurationError(ValueError):
    """Base class for safe, value-free configuration errors."""


class ConfigValidationError(ConfigurationError):
    """The requested document or operation does not satisfy the schema."""


class ConfigConflictError(ConfigurationError):
    """The persisted document changed after the caller read its revision."""


class ConfigLockError(ConfigurationError):
    """The configuration lock could not be acquired before its deadline."""


@dataclass(frozen=True, slots=True)
class ConfigState:
    """Secret-free state suitable for a CLI JSON response or dashboard API."""

    path: str
    persisted: dict[str, Any]
    effective: dict[str, Any]
    revision: str
    secret_presence: dict[str, bool]
    environment_overrides: dict[str, str]
    restart_required_paths: tuple[str, ...] = RESTART_REQUIRED_PATHS


@dataclass(frozen=True, slots=True)
class ConfigUpdateResult:
    """Result of one locked, validated, atomic update transaction."""

    state: ConfigState
    changed_paths: tuple[str, ...]
    restart_required: tuple[str, ...]
    policy_enforced: bool
