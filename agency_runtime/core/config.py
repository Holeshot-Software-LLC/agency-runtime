"""Centralized configuration for Agency Runtime.

Layered precedence (highest wins):
    1. Environment variables (AGENCY_JUDGE_MODEL, etc.) — override/CI only
    2. User config file (~/.agency-runtime/agency.yaml) — primary source
    3. Bundled defaults (config_defaults.yaml) — safe Ollama-only baseline

The config file is the single source of truth for runtime behavior.
Secrets (API keys) can be stored directly in agency.yaml (file permissions
should be 0600) or referenced via api_key_env for CI/container environments.
Env vars are override-only, never the primary mechanism.
"""

from __future__ import annotations

import ipaddress
import math
import os
import re
import stat
import threading
from collections import OrderedDict
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml

from agency_runtime.core.agent_activation import normalize_disabled_agents
from agency_runtime.core.bounded_io import FileSizeLimitError, read_bounded_regular_file
from agency_runtime.core.bounded_yaml import BoundedYAMLError, safe_load_bounded
from agency_runtime.core.configuration_contracts import ConfigValidationError
from agency_runtime.core.configuration_persistence import (
    assert_config_namespace,
    resolve_config_path,
)
from agency_runtime.core.filesystem_trust import absolute_path as _absolute_path
from agency_runtime.core.filesystem_trust import (
    metadata_is_link_or_reparse_point as _metadata_is_link_or_reparse,
)
from agency_runtime.core.policy.profiles import PROFILES

# ── Config path resolution ────────────────────────────────────

_BUNDLED_DEFAULTS = Path(__file__).parent / "config_defaults.yaml"
MAX_PROVIDER_CHAIN_ENTRIES = 4
CODEX_REASONING_EFFORTS = frozenset({"low", "medium", "high", "xhigh", "max", "ultra"})
_CLI_MODEL_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+\-]{0,255}\Z")


def is_safe_cli_model_id(value: str) -> bool:
    """Accept an empty CLI default or one shell-neutral bounded model token."""

    return value == "" or (
        isinstance(value, str) and _CLI_MODEL_ID_PATTERN.fullmatch(value) is not None
    )


def _default_config_path() -> Path:
    """Return the user config path, checking env override."""
    return resolve_config_path()


def _resolve_config_relative_path(value: str, config_path: Path) -> str:
    """Resolve one configured runtime path against its config identity.

    Configuration can be consumed by an interactive CLI, a host hook, or a
    reboot-persistent service whose working directories are unrelated.  Bind
    relative paths while materializing the configuration so those consumers
    cannot silently select different files later.
    """

    candidate = Path(os.path.expanduser(value))
    if not candidate.is_absolute():
        candidate = config_path.parent / candidate
    # ``Path.resolve`` follows the final component and could turn a configured
    # symlink into an apparently safe regular target before Store/policy checks
    # see it.  Normalize dot segments without dereferencing any component.
    normalized = _absolute_path(candidate)
    for component in (*reversed(normalized.parents), normalized):
        try:
            metadata = os.lstat(component)
        except FileNotFoundError:
            continue
        if _metadata_is_link_or_reparse(metadata):
            raise ValueError(
                "configured runtime paths must not traverse a symlink or reparse point"
            )
    return str(normalized)


def _bind_runtime_paths(cfg: AgencyConfig, config_path: Path) -> AgencyConfig:
    """Return a configuration whose file-backed runtime paths are absolute."""

    store = replace(
        cfg.store,
        db_path=_resolve_config_relative_path(cfg.store.db_path, config_path),
    )
    companion_policy_path = cfg.companion_policy_path
    if companion_policy_path is not None:
        companion_policy_path = _resolve_config_relative_path(
            companion_policy_path,
            config_path,
        )
    return replace(
        cfg,
        store=store,
        companion_policy_path=companion_policy_path,
        config_path=str(config_path),
    )


# ── Dataclass config shapes ───────────────────────────────────


@dataclass(frozen=True, slots=True)
class ProviderEntry:
    """A single LLM provider in the fallback chain.

    Auth methods (in priority order at runtime):
    1. api_key (stored directly in config)
    2. api_key_env (environment variable name)
    3. oauth (CLI-based auth like Claude Code / Codex)
    4. none (local/free providers like Ollama)
    """

    name: str = ""
    type: str = "openai-compatible"  # openai-compatible, anthropic, ollama, litellm, cli
    transport: str = ""  # allowlisted CLI transport: codex or claude
    model: str = ""
    base_url: str = ""
    api_key: str = ""
    api_key_env: str = ""
    ollama_mode: bool = False
    timeout: float = 15.0
    reasoning_effort: str = ""

    def resolve_api_key(self) -> str:
        """Return the API key: direct value first, then env var."""
        if self.api_key:
            return self.api_key
        if self.api_key_env:
            return os.environ.get(self.api_key_env, "")
        return ""

    def auth_method(self) -> str:
        """Return how this provider authenticates."""
        provider_type = self.type.strip().lower()
        if provider_type == "ollama":
            return "none"
        if self.api_key:
            return "api_key"
        if self.api_key_env and os.environ.get(self.api_key_env):
            return "env_key"
        if provider_type == "cli":
            return "oauth"
        return "none"

    def is_available(self) -> bool:
        """Quick check: does this provider have auth and a model?"""
        provider_type = self.type.strip().lower()
        if provider_type == "ollama":
            return bool(self.model and self.base_url)
        if provider_type == "cli":
            return self.transport.strip().lower() in {
                "codex",
                "claude",
            } and is_safe_cli_model_id(self.model)
        if provider_type in {
            "openai",
            "openai-compatible",
            "litellm",
        } and _is_loopback_http_url(self.base_url):
            return bool(self.model)
        return bool(self.model and self.resolve_api_key())


@dataclass(frozen=True, slots=True)
class JudgeConfig:
    model: str = ""
    base_url: str = ""
    api_key_env: str = ""
    api_key: str = ""
    ollama_mode: bool = False
    timeout: float = 15.0
    max_selected: int = 3
    confidence_bypass_threshold: float = 15.0

    def resolve_api_key(self) -> str:
        """Return the API key: direct value first, then env var."""
        if self.api_key:
            return self.api_key
        if self.api_key_env:
            return os.environ.get(self.api_key_env, "")
        return ""


@dataclass(frozen=True, slots=True)
class OllamaConfig:
    enabled: bool = True
    base_url: str = "http://127.0.0.1:11434"
    model: str = "qwen3.5:2b"


@dataclass(frozen=True, slots=True)
class SelectorConfig:
    min_confidence: float = 0.8
    max_user_msg_len: int = 4000
    # Deprecated compatibility field. Turn classification is state-aware and
    # never uses character count as an authority boundary.
    trivial_msg_threshold: int = 0


DELEGATION_MODES = frozenset({"observe", "prefer", "strong"})
WORKFORCE_MODES = frozenset({"fast", "balanced", "strict"})


@dataclass(frozen=True, slots=True)
class DelegationConfig:
    """Native-host delegation guidance and bounded correction policy."""

    mode: str = "prefer"
    preferred_min_units: int = 2
    strongly_preferred_min_units: int = 4
    strongly_preferred_min_confidence: float = 0.8
    child_inference_budget: int = 4
    child_inference_concurrency: int = 2
    child_cache_ttl_seconds: int = 900


@dataclass(frozen=True, slots=True)
class WorkforceConfig:
    """Inference-first planning, staffing, hiring, and promotion policy."""

    mode: str = "fast"
    provider: str = ""
    planner_model: str = ""
    recruiter_model: str = ""
    hiring_model: str = ""
    critic_model: str = ""
    fast_call_budget: int = 4
    balanced_call_budget: int = 4
    strict_call_budget: int = 5
    hiring_call_budget: int = 4
    max_work_units: int = 16
    max_selected_per_unit: int = 4
    max_selected_total: int = 16
    min_confidence: float = 0.8
    min_margin: float = 0.1
    max_hires_per_task: int = 1
    max_hires_per_day: int = 3
    auto_promote_successes: int = 0
    contractor_review_days: int = 30


@dataclass(frozen=True, slots=True)
class AgentActivationConfig:
    """Reversible operator policy for governed specialist definitions."""

    disabled: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class StoreConfig:
    db_path: str = "~/.agency-runtime/agency.db"

    def resolved_path(self) -> Path:
        return Path(os.path.expanduser(self.db_path))


@dataclass(frozen=True, slots=True)
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 7800
    max_body_size: int = 16 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class DashboardConfig:
    """Operational settings for the user-scoped dashboard service."""

    port: int = 7810


@dataclass(frozen=True, slots=True)
class ObservabilityConfig:
    """Privacy and local retention defaults for runtime evidence."""

    capture_content: bool = False
    retention_days: int = 30


@dataclass(frozen=True, slots=True)
class AdapterEntryConfig:
    enabled: str = "auto"  # "auto", "true", "false"
    base_url: str = ""
    api_key: str = ""
    api_key_env: str = ""
    skip_models: tuple[str, ...] = field(default_factory=tuple)

    def resolve_api_key(self) -> str:
        """Return the API key: direct value first, then env var."""
        if self.api_key:
            return self.api_key
        if self.api_key_env:
            return os.environ.get(self.api_key_env, "")
        return ""


@dataclass(frozen=True, slots=True)
class AdaptersConfig:
    litellm: AdapterEntryConfig = field(
        default_factory=lambda: AdapterEntryConfig(
            enabled="auto",
            base_url="http://127.0.0.1:4000",
            api_key_env="LITELLM_API_KEY",
            skip_models=("complexity_router", "auto_router/"),
        )
    )
    hermes: AdapterEntryConfig = field(default_factory=AdapterEntryConfig)
    openclaw: AdapterEntryConfig = field(default_factory=AdapterEntryConfig)
    codex: AdapterEntryConfig = field(default_factory=AdapterEntryConfig)
    claude: AdapterEntryConfig = field(default_factory=AdapterEntryConfig)
    zcode: AdapterEntryConfig = field(default_factory=AdapterEntryConfig)


@dataclass(frozen=True, slots=True)
class AgencyConfig:
    judge: JudgeConfig = field(default_factory=JudgeConfig)
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    providers: tuple[ProviderEntry, ...] = field(default_factory=tuple)
    selector: SelectorConfig = field(default_factory=SelectorConfig)
    delegation: DelegationConfig = field(default_factory=DelegationConfig)
    workforce: WorkforceConfig = field(default_factory=WorkforceConfig)
    agents: AgentActivationConfig = field(default_factory=AgentActivationConfig)
    store: StoreConfig = field(default_factory=StoreConfig)
    server: ServerConfig = field(default_factory=ServerConfig)
    dashboard: DashboardConfig = field(default_factory=DashboardConfig)
    observability: ObservabilityConfig = field(default_factory=ObservabilityConfig)
    adapters: AdaptersConfig = field(default_factory=AdaptersConfig)
    profile: str = "standard"
    companion_policy_path: str | None = None
    config_path: str = ""  # where this config was loaded from


# ── YAML loading helpers ──────────────────────────────────────


_MAX_CONFIG_BYTES = 1024 * 1024


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        raw = read_bounded_regular_file(
            path,
            limit=_MAX_CONFIG_BYTES,
            label="configuration file",
        )
    except FileNotFoundError:
        return {}
    except FileSizeLimitError as exc:
        raise ValueError("configuration file exceeds the 1 MiB size limit") from exc
    except OSError as exc:
        raise ValueError("configuration file is unavailable or unsafe") from exc
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("configuration file must be UTF-8") from exc
    if not raw.strip():
        return {}
    try:
        data = safe_load_bounded(text)
    except BoundedYAMLError as exc:
        raise ValueError(str(exc)) from exc
    if data is None:
        raise ConfigValidationError("configuration root must be a mapping")
    if not isinstance(data, dict):
        raise ValueError("configuration root must be a mapping")
    return data


def _build_adapter_entry(raw: dict[str, Any]) -> AdapterEntryConfig:
    return AdapterEntryConfig(
        enabled=_normalize_enabled(raw.get("enabled", "auto")),
        base_url=str(raw.get("base_url", "")),
        api_key=str(raw.get("api_key", "")),
        api_key_env=str(raw.get("api_key_env", "")),
        skip_models=tuple(raw.get("skip_models", [])),
    )


def _normalize_enabled(value: Any) -> str:
    """Normalize enabled flag to 'auto', 'true', or 'false'."""
    if isinstance(value, bool):
        return "true" if value else "false"
    s = str(value).strip().lower()
    if s in ("true", "yes", "1", "on"):
        return "true"
    if s in ("false", "no", "0", "off"):
        return "false"
    return "auto"


def _build_provider_entry(raw: dict[str, Any]) -> ProviderEntry:
    return ProviderEntry(
        name=str(raw.get("name", "")),
        type=str(raw.get("type", "openai-compatible")),
        transport=str(raw.get("transport", "")),
        model=str(raw.get("model", "")),
        base_url=str(raw.get("base_url", "")),
        api_key=str(raw.get("api_key", "")),
        api_key_env=str(raw.get("api_key_env", "")),
        ollama_mode=bool(raw.get("ollama_mode", raw.get("type") == "ollama")),
        timeout=float(raw.get("timeout", 15.0)),
        reasoning_effort=str(raw.get("reasoning_effort", "")),
    )


def _build_providers(raw: list[Any] | None) -> tuple[ProviderEntry, ...]:
    if not raw or not isinstance(raw, list):
        return ()
    if len(raw) > MAX_PROVIDER_CHAIN_ENTRIES:
        raise ValueError(f"providers supports at most {MAX_PROVIDER_CHAIN_ENTRIES} entries")
    return tuple(_build_provider_entry(p) for p in raw if isinstance(p, dict))


def _build_adapters(raw: dict[str, Any]) -> AdaptersConfig:
    litellm_raw = raw.get("litellm", {})
    # Ensure skip_models default is preserved if not overridden.
    if isinstance(litellm_raw, dict) and "skip_models" not in litellm_raw:
        litellm_raw = {**litellm_raw}
    return AdaptersConfig(
        litellm=_build_adapter_entry(
            {
                "enabled": "auto",
                "base_url": "http://127.0.0.1:4000",
                "api_key_env": "LITELLM_API_KEY",
                "skip_models": ["complexity_router", "auto_router/"],
                **(litellm_raw if isinstance(litellm_raw, dict) else {}),
            }
        ),
        hermes=_build_adapter_entry(raw.get("hermes", {})),
        openclaw=_build_adapter_entry(raw.get("openclaw", {})),
        codex=_build_adapter_entry(raw.get("codex", {})),
        claude=_build_adapter_entry(raw.get("claude", {})),
        zcode=_build_adapter_entry(raw.get("zcode", {})),
    )


def _dict_to_config(raw: dict[str, Any], config_path: str = "") -> AgencyConfig:
    """Build AgencyConfig from a merged dict."""
    judge_raw = raw.get("judge", {})
    ollama_raw = raw.get("ollama", {})
    providers_raw = raw.get("providers", [])
    selector_raw = raw.get("selector", {})
    delegation_raw = raw.get("delegation", {})
    workforce_raw = raw.get("workforce", {})
    agents_raw = raw.get("agents", {})
    store_raw = raw.get("store", {})
    server_raw = raw.get("server", {})
    dashboard_raw = raw.get("dashboard", {})
    observability_raw = raw.get("observability", {})
    adapters_raw = raw.get("adapters", {})
    if not isinstance(observability_raw, dict):
        observability_raw = {}

    return AgencyConfig(
        judge=JudgeConfig(
            model=str(judge_raw.get("model", "")),
            base_url=str(judge_raw.get("base_url", "")),
            api_key_env=str(judge_raw.get("api_key_env", "")),
            api_key=str(judge_raw.get("api_key", "")),
            ollama_mode=bool(judge_raw.get("ollama_mode", False)),
            timeout=float(judge_raw.get("timeout", 15.0)),
            max_selected=int(judge_raw.get("max_selected", 3)),
            confidence_bypass_threshold=float(judge_raw.get("confidence_bypass_threshold", 15.0)),
        ),
        ollama=OllamaConfig(
            enabled=bool(ollama_raw.get("enabled", True)),
            base_url=str(ollama_raw.get("base_url", "http://127.0.0.1:11434")),
            model=str(ollama_raw.get("model", "qwen3.5:2b")),
        ),
        providers=_build_providers(providers_raw),
        selector=SelectorConfig(
            min_confidence=float(selector_raw.get("min_confidence", 0.8)),
            max_user_msg_len=int(selector_raw.get("max_user_msg_len", 4000)),
            trivial_msg_threshold=int(selector_raw.get("trivial_msg_threshold", 0)),
        ),
        delegation=DelegationConfig(
            mode=str(delegation_raw.get("mode", "prefer")).strip().casefold(),
            preferred_min_units=int(delegation_raw.get("preferred_min_units", 2)),
            strongly_preferred_min_units=int(delegation_raw.get("strongly_preferred_min_units", 4)),
            strongly_preferred_min_confidence=float(
                delegation_raw.get("strongly_preferred_min_confidence", 0.8)
            ),
            child_inference_budget=int(delegation_raw.get("child_inference_budget", 4)),
            child_inference_concurrency=int(delegation_raw.get("child_inference_concurrency", 2)),
            child_cache_ttl_seconds=int(delegation_raw.get("child_cache_ttl_seconds", 900)),
        ),
        workforce=WorkforceConfig(
            mode=str(workforce_raw.get("mode", "fast")).strip().casefold(),
            provider=str(workforce_raw.get("provider", "")).strip(),
            planner_model=str(workforce_raw.get("planner_model", "")).strip(),
            recruiter_model=str(workforce_raw.get("recruiter_model", "")).strip(),
            hiring_model=str(workforce_raw.get("hiring_model", "")).strip(),
            critic_model=str(workforce_raw.get("critic_model", "")).strip(),
            fast_call_budget=int(workforce_raw.get("fast_call_budget", 4)),
            balanced_call_budget=int(workforce_raw.get("balanced_call_budget", 4)),
            strict_call_budget=int(workforce_raw.get("strict_call_budget", 5)),
            hiring_call_budget=int(workforce_raw.get("hiring_call_budget", 4)),
            max_work_units=int(workforce_raw.get("max_work_units", 16)),
            max_selected_per_unit=int(workforce_raw.get("max_selected_per_unit", 4)),
            max_selected_total=int(workforce_raw.get("max_selected_total", 16)),
            min_confidence=float(workforce_raw.get("min_confidence", 0.8)),
            min_margin=float(workforce_raw.get("min_margin", 0.1)),
            max_hires_per_task=int(workforce_raw.get("max_hires_per_task", 1)),
            max_hires_per_day=int(workforce_raw.get("max_hires_per_day", 3)),
            auto_promote_successes=int(workforce_raw.get("auto_promote_successes", 0)),
            contractor_review_days=int(workforce_raw.get("contractor_review_days", 30)),
        ),
        agents=AgentActivationConfig(
            disabled=normalize_disabled_agents(agents_raw.get("disabled", [])),
        ),
        store=StoreConfig(
            db_path=str(store_raw.get("db_path", "~/.agency-runtime/agency.db")),
        ),
        server=ServerConfig(
            host=str(server_raw.get("host", "127.0.0.1")),
            port=int(server_raw.get("port", 7800)),
            max_body_size=int(server_raw.get("max_body_size", 16 * 1024 * 1024)),
        ),
        dashboard=DashboardConfig(
            port=int(dashboard_raw.get("port", 7810)),
        ),
        observability=ObservabilityConfig(
            capture_content=(
                _normalize_enabled(observability_raw.get("capture_content", False)) == "true"
            ),
            retention_days=max(1, int(observability_raw.get("retention_days", 30))),
        ),
        adapters=_build_adapters(adapters_raw),
        profile=str(raw.get("profile", "standard")),
        companion_policy_path=raw.get("companion_policy_path"),
        config_path=config_path,
    )


# ── Env var override layer ────────────────────────────────────


def _validated_env_number(
    environ: Mapping[str, str],
    name: str,
    converter: Callable[[str], Any],
    *,
    minimum: float,
    maximum: float,
) -> Any | None:
    """Return one bounded numeric override or reject it without echoing values."""

    raw = environ.get(name, "").strip()
    if not raw:
        return None
    try:
        value = converter(raw)
        finite = math.isfinite(float(value))
        in_range = minimum <= value <= maximum
    except (OverflowError, TypeError, ValueError) as exc:
        raise ConfigValidationError(f"{name}: environment override is invalid") from exc
    if isinstance(value, bool) or not finite or not in_range:
        raise ConfigValidationError(f"{name}: environment override is invalid")
    return value


def _judge_has_resolved_key(
    judge: JudgeConfig,
    environ: Mapping[str, str],
) -> bool:
    return bool(judge.api_key or (judge.api_key_env and environ.get(judge.api_key_env, "")))


def _judge_env_replacements(
    judge: JudgeConfig,
    environ: Mapping[str, str],
) -> dict[str, Any]:
    replacements = {
        field_name: value
        for env_name, field_name in (
            ("AGENCY_JUDGE_MODEL", "model"),
            ("AGENCY_JUDGE_BASE_URL", "base_url"),
        )
        if (value := environ.get(env_name))
    }
    direct_key = environ.get("AGENCY_JUDGE_API_KEY")
    fallback_key = environ.get("LITELLM_API_KEY")
    if direct_key:
        replacements["api_key"] = direct_key
    elif fallback_key and not _judge_has_resolved_key(judge, environ):
        replacements["api_key"] = fallback_key
    for env_name, field_name, converter, minimum, maximum in (
        ("AGENCY_JUDGE_TIMEOUT", "timeout", float, 0.05, 60.0),
        ("AGENCY_MAX_SELECTED", "max_selected", int, 1, 50),
        ("AGENCY_BYPASS_THRESHOLD", "confidence_bypass_threshold", float, 0.0, 100.0),
    ):
        value = _validated_env_number(
            environ,
            env_name,
            converter,
            minimum=minimum,
            maximum=maximum,
        )
        if value is not None:
            replacements[field_name] = value
    if replacements.keys() & {"model", "base_url"}:
        base_url = replacements.get("base_url", judge.base_url)
        if "11434" not in base_url:
            replacements["ollama_mode"] = False
    return replacements


def _observability_env_replacements(
    environ: Mapping[str, str],
) -> dict[str, Any]:
    replacements: dict[str, Any] = {}
    if capture_content := environ.get("AGENCY_CAPTURE_CONTENT"):
        normalized = capture_content.strip().lower()
        accepted = {"0", "1", "false", "true", "no", "yes", "off", "on"}
        if normalized not in accepted:
            raise ConfigValidationError("AGENCY_CAPTURE_CONTENT: environment override is invalid")
        replacements["capture_content"] = normalized in {"1", "true", "yes", "on"}
    retention_days = _validated_env_number(
        environ,
        "AGENCY_RETENTION_DAYS",
        int,
        minimum=1,
        maximum=3650,
    )
    if retention_days is not None:
        replacements["retention_days"] = retention_days
    return replacements


def _replace_if(instance: Any, replacements: dict[str, Any]) -> Any:
    return replace(instance, **replacements) if replacements else instance


def _apply_env_overrides(
    cfg: AgencyConfig,
    *,
    environ: Mapping[str, str] | None = None,
) -> AgencyConfig:
    """Apply environment variable overrides on top of the config."""

    environment = os.environ if environ is None else environ
    ollama_replacements = {
        field_name: value
        for env_name, field_name in (
            ("OLLAMA_BASE_URL", "base_url"),
            ("AGENCY_OLLAMA_FALLBACK_MODEL", "model"),
        )
        if (value := environment.get(env_name))
    }
    store_path = environment.get("AGENCY_DB_PATH")
    companion_policy_path = environment.get("AGENCY_POLICY_PATH")
    dashboard_port = _validated_env_number(
        environment,
        "AGENCY_DASHBOARD_PORT",
        int,
        minimum=1,
        maximum=65535,
    )
    raw_profile = environment.get("AGENCY_PROFILE", "").strip()
    profile = raw_profile.lower() if raw_profile else cfg.profile
    if profile not in PROFILES:
        raise ConfigValidationError("AGENCY_PROFILE: environment override is invalid")
    return replace(
        cfg,
        judge=_replace_if(
            cfg.judge,
            _judge_env_replacements(cfg.judge, environment),
        ),
        ollama=_replace_if(cfg.ollama, ollama_replacements),
        store=_replace_if(cfg.store, {"db_path": store_path} if store_path else {}),
        dashboard=_replace_if(
            cfg.dashboard,
            {"port": dashboard_port} if dashboard_port is not None else {},
        ),
        observability=_replace_if(
            cfg.observability,
            _observability_env_replacements(environment),
        ),
        companion_policy_path=companion_policy_path or cfg.companion_policy_path,
        profile=profile,
    )


def _is_loopback_http_url(value: str) -> bool:
    """Return whether *value* is an uncredentialed loopback HTTP(S) endpoint."""
    try:
        parsed = urlsplit(value)
        host = (parsed.hostname or "").rstrip(".").lower()
        _ = parsed.port
        if parsed.scheme not in {"http", "https"} or not host:
            return False
        if (
            parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or any(character.isspace() for character in value)
        ):
            return False
        if host == "localhost":
            return True
        return ipaddress.ip_address(host).is_loopback
    except (ValueError, TypeError):
        return False


def is_safe_credential_url(value: str) -> bool:
    """Require HTTPS except for HTTP URLs using a literal loopback address."""
    try:
        parsed = urlsplit(value)
        host = parsed.hostname or ""
        _ = parsed.port
        if (
            parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or not host
            or any(character.isspace() for character in value)
        ):
            return False
        if parsed.scheme.lower() == "https":
            return True
        if parsed.scheme.lower() != "http":
            return False
        return ipaddress.ip_address(host).is_loopback
    except (ValueError, TypeError):
        return False


def _enforce_credential_transport_constraints(cfg: AgencyConfig) -> AgencyConfig:
    """Fail closed before configured credentials can reach an unsafe endpoint."""
    for provider in cfg.providers:
        if (provider.api_key or provider.api_key_env) and not is_safe_credential_url(
            provider.base_url
        ):
            raise ValueError(
                f"provider {provider.name!r} credentials require HTTPS or literal loopback HTTP"
            )
    if (cfg.judge.api_key or cfg.judge.api_key_env) and not is_safe_credential_url(
        cfg.judge.base_url
    ):
        raise ValueError("judge credentials require HTTPS or literal loopback HTTP")
    litellm = cfg.adapters.litellm
    if (litellm.api_key or litellm.api_key_env) and not is_safe_credential_url(litellm.base_url):
        raise ValueError("LiteLLM adapter credentials require HTTPS or literal loopback HTTP")
    return cfg


def _enforce_profile_constraints(cfg: AgencyConfig) -> AgencyConfig:
    """Apply security invariants that configuration overlays cannot relax."""
    if cfg.profile.strip().lower() != "local-only":
        return cfg

    local_base_url = (
        cfg.ollama.base_url
        if _is_loopback_http_url(cfg.ollama.base_url)
        else "http://127.0.0.1:11434"
    )
    local_ollama = replace(cfg.ollama, base_url=local_base_url)
    local_providers = tuple(
        replace(
            provider,
            transport="",
            api_key="",
            api_key_env="",
            ollama_mode=provider.type.strip().lower() == "ollama",
        )
        for provider in cfg.providers
        if provider.type.strip().lower() in {"ollama", "openai", "openai-compatible", "litellm"}
        and _is_loopback_http_url(provider.base_url)
    )
    primary = local_providers[0] if local_providers else None
    local_judge = replace(
        cfg.judge,
        model=primary.model if primary else local_ollama.model,
        base_url=primary.base_url if primary else local_base_url,
        api_key="",
        api_key_env="",
        ollama_mode=primary.ollama_mode if primary else True,
    )

    def disabled(entry: AdapterEntryConfig) -> AdapterEntryConfig:
        return replace(entry, enabled="false")

    local_adapters = AdaptersConfig(
        litellm=disabled(cfg.adapters.litellm),
        hermes=disabled(cfg.adapters.hermes),
        openclaw=disabled(cfg.adapters.openclaw),
        codex=disabled(cfg.adapters.codex),
        claude=disabled(cfg.adapters.claude),
        zcode=disabled(cfg.adapters.zcode),
    )
    return replace(
        cfg,
        judge=local_judge,
        ollama=local_ollama,
        providers=local_providers,
        adapters=local_adapters,
        profile="local-only",
    )


# ── Public API ────────────────────────────────────────────────

_CONFIG_ENVIRONMENT_NAMES = (
    "AGENCY_BYPASS_THRESHOLD",
    "AGENCY_CAPTURE_CONTENT",
    "AGENCY_DASHBOARD_PORT",
    "AGENCY_DB_PATH",
    "AGENCY_JUDGE_API_KEY",
    "AGENCY_JUDGE_BASE_URL",
    "AGENCY_JUDGE_MODEL",
    "AGENCY_JUDGE_TIMEOUT",
    "AGENCY_MAX_SELECTED",
    "AGENCY_OLLAMA_FALLBACK_MODEL",
    "AGENCY_POLICY_PATH",
    "AGENCY_PROFILE",
    "AGENCY_RETENTION_DAYS",
    "LITELLM_API_KEY",
    "OLLAMA_BASE_URL",
)
_config_cache_lock = threading.RLock()
_CONFIG_CACHE_LIMIT = 32
_CONFIG_LOAD_STABILITY_ATTEMPTS = 4
_config_cache: OrderedDict[
    str,
    tuple[AgencyConfig, tuple[object, ...]],
] = OrderedDict()


def _config_file_signature(path: Path) -> tuple[object, ...]:
    """Return a cheap identity that changes after an external config write."""

    path = resolve_config_path(path, use_environment=False)
    normalized = str(_absolute_path(path))
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return (normalized, "missing")
    except OSError as exc:
        return (normalized, "unavailable", type(exc).__name__, exc.errno)
    if _metadata_is_link_or_reparse(metadata) or not stat.S_ISREG(metadata.st_mode):
        raise ValueError("configuration file must be a regular non-link file")
    return (
        normalized,
        "present",
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_mode,
        metadata.st_size,
        metadata.st_mtime_ns,
        metadata.st_ctime_ns,
    )


def _config_environment_signature(
    cfg: AgencyConfig | None,
    *,
    environment: Mapping[str, str] | None = None,
) -> tuple[tuple[str, str | None], ...]:
    """Fingerprint only environment values that affect the materialized config."""

    source = os.environ if environment is None else environment
    names = set(_CONFIG_ENVIRONMENT_NAMES)
    if cfg is not None and cfg.judge.api_key_env:
        names.add(cfg.judge.api_key_env)
    return tuple((name, source.get(name)) for name in sorted(names))


def _config_cache_signature(path: Path, cfg: AgencyConfig | None) -> tuple[object, ...]:
    return (_config_file_signature(path), _config_environment_signature(cfg))


def _config_cache_key(path: Path) -> str:
    """Return one platform-canonical key without dereferencing the identity."""

    return os.path.normcase(str(_absolute_path(path)))


def _cache_config(
    key: str,
    cfg: AgencyConfig,
    signature: tuple[object, ...],
) -> None:
    """Refresh one bounded LRU entry while the caller holds the cache lock."""

    _config_cache[key] = (cfg, signature)
    _config_cache.move_to_end(key)
    while len(_config_cache) > _CONFIG_CACHE_LIMIT:
        _config_cache.popitem(last=False)


def _load_config_uncached(
    config_path: Path,
    *,
    environ: Mapping[str, str] | None = None,
) -> AgencyConfig:
    """Materialize one configuration snapshot from defaults, file, and environment."""

    environment = dict(os.environ) if environ is None else environ
    config_path = resolve_config_path(config_path, use_environment=False)
    defaults_raw = _load_yaml(_BUNDLED_DEFAULTS)
    cfg = _dict_to_config(defaults_raw, config_path=str(config_path))

    file_raw = _load_yaml(config_path)
    if file_raw:
        # Keep direct runtime reads as strict as dashboard/CLI config writes.
        # This import stays local because configuration_schema intentionally
        # reuses the public config datatypes and validators.
        from agency_runtime.core.configuration_schema import validate_config_document

        file_raw = validate_config_document(file_raw)
        merged = {**defaults_raw, **file_raw}
        for key in (
            "judge",
            "ollama",
            "selector",
            "delegation",
            "workforce",
            "agents",
            "store",
            "server",
            "dashboard",
            "observability",
            "adapters",
        ):
            if key in defaults_raw and key in file_raw:
                override = file_raw[key]
                if not isinstance(override, dict):
                    raise ValueError(f"{key} must be a mapping")
                merged[key] = {**defaults_raw[key], **override}
        cfg = _dict_to_config(merged, config_path=str(config_path))

    cfg = _apply_env_overrides(cfg, environ=environment)
    cfg = _enforce_profile_constraints(cfg)
    cfg = _enforce_credential_transport_constraints(cfg)
    return _bind_runtime_paths(cfg, config_path)


def load_config(path: str | Path | None = None, *, reload: bool = False) -> AgencyConfig:
    """Load config with precedence: env > file > bundled defaults.

    Args:
        path: Optional explicit config path (overrides AGENCY_CONFIG_PATH env).
        reload: Force a fresh load instead of returning the cached identity snapshot.
    """
    # The selected config identity is this call's linearization point. A later
    # AGENCY_CONFIG_PATH change applies to the next call and selects a distinct
    # cache key; it is not a materialized setting for this already-selected file.
    config_path = resolve_config_path(path) if path is not None else _default_config_path()
    # File identity checks reject linked or changing final artifacts, while the
    # namespace check prevents another account from replacing that artifact
    # through a mutable ancestor.  Recheck even on cache hits so a previously
    # safe parent cannot become a bypass for the cached runtime truth.
    assert_config_namespace(config_path)
    cache_key = _config_cache_key(config_path)

    with _config_cache_lock:
        cached = _config_cache.get(cache_key)
        cached_config = cached[0] if cached is not None else None
        cached_signature = cached[1] if cached is not None else None
        current_signature = _config_cache_signature(config_path, cached_config)
        if cached_config is not None and not reload and current_signature == cached_signature:
            assert_config_namespace(config_path)
            _config_cache.move_to_end(cache_key)
            return cached_config

        for _attempt in range(_CONFIG_LOAD_STABILITY_ATTEMPTS):
            file_signature_before = _config_file_signature(config_path)
            environment_before = dict(os.environ)
            cfg = _load_config_uncached(config_path, environ=environment_before)
            assert_config_namespace(config_path)
            file_signature_after = _config_file_signature(config_path)
            environment_after = dict(os.environ)
            environment_signature_before = _config_environment_signature(
                cfg,
                environment=environment_before,
            )
            environment_signature_after = _config_environment_signature(
                cfg,
                environment=environment_after,
            )
            if (
                file_signature_after == file_signature_before
                and environment_signature_after == environment_signature_before
            ):
                loaded_signature = (
                    file_signature_after,
                    environment_signature_after,
                )
                _cache_config(cache_key, cfg, loaded_signature)
                return cfg
        raise ValueError("configuration inputs changed repeatedly during load")


def reset_config_cache() -> None:
    """Clear every file-aware config cache entry (for tests)."""

    with _config_cache_lock:
        _config_cache.clear()


def config_to_yaml(cfg: AgencyConfig, *, redact: bool = True) -> str:
    """Serialize config back to YAML for display.

    Args:
        redact: If True, mask api_key values.
    """
    data: dict[str, Any] = {
        "judge": {
            "model": cfg.judge.model,
            "base_url": cfg.judge.base_url,
            "api_key_env": cfg.judge.api_key_env,
            "api_key": "***REDACTED***" if redact and cfg.judge.api_key else cfg.judge.api_key,
            "ollama_mode": cfg.judge.ollama_mode,
            "timeout": cfg.judge.timeout,
            "max_selected": cfg.judge.max_selected,
            "confidence_bypass_threshold": cfg.judge.confidence_bypass_threshold,
        },
        "ollama": {
            "enabled": cfg.ollama.enabled,
            "base_url": cfg.ollama.base_url,
            "model": cfg.ollama.model,
        },
        "providers": [
            {
                "name": p.name,
                "type": p.type,
                "transport": p.transport,
                "model": p.model,
                "base_url": p.base_url,
                "api_key": "***REDACTED***" if redact and p.api_key else p.api_key,
                "api_key_env": p.api_key_env,
                "ollama_mode": p.ollama_mode,
                "timeout": p.timeout,
                "reasoning_effort": p.reasoning_effort,
            }
            for p in cfg.providers
        ],
        "selector": {
            "min_confidence": cfg.selector.min_confidence,
            "max_user_msg_len": cfg.selector.max_user_msg_len,
            "trivial_msg_threshold": cfg.selector.trivial_msg_threshold,
        },
        "delegation": {
            "mode": cfg.delegation.mode,
            "preferred_min_units": cfg.delegation.preferred_min_units,
            "strongly_preferred_min_units": cfg.delegation.strongly_preferred_min_units,
            "strongly_preferred_min_confidence": (cfg.delegation.strongly_preferred_min_confidence),
            "child_inference_budget": cfg.delegation.child_inference_budget,
            "child_inference_concurrency": cfg.delegation.child_inference_concurrency,
            "child_cache_ttl_seconds": cfg.delegation.child_cache_ttl_seconds,
        },
        "workforce": {
            "mode": cfg.workforce.mode,
            "provider": cfg.workforce.provider,
            "planner_model": cfg.workforce.planner_model,
            "recruiter_model": cfg.workforce.recruiter_model,
            "hiring_model": cfg.workforce.hiring_model,
            "critic_model": cfg.workforce.critic_model,
            "fast_call_budget": cfg.workforce.fast_call_budget,
            "balanced_call_budget": cfg.workforce.balanced_call_budget,
            "strict_call_budget": cfg.workforce.strict_call_budget,
            "hiring_call_budget": cfg.workforce.hiring_call_budget,
            "max_work_units": cfg.workforce.max_work_units,
            "max_selected_per_unit": cfg.workforce.max_selected_per_unit,
            "max_selected_total": cfg.workforce.max_selected_total,
            "min_confidence": cfg.workforce.min_confidence,
            "min_margin": cfg.workforce.min_margin,
            "max_hires_per_task": cfg.workforce.max_hires_per_task,
            "max_hires_per_day": cfg.workforce.max_hires_per_day,
            "auto_promote_successes": cfg.workforce.auto_promote_successes,
            "contractor_review_days": cfg.workforce.contractor_review_days,
        },
        "agents": {"disabled": list(cfg.agents.disabled)},
        "store": {"db_path": cfg.store.db_path},
        "server": {
            "host": cfg.server.host,
            "port": cfg.server.port,
            "max_body_size": cfg.server.max_body_size,
        },
        "dashboard": {
            "port": cfg.dashboard.port,
        },
        "observability": {
            "capture_content": cfg.observability.capture_content,
            "retention_days": cfg.observability.retention_days,
        },
        "adapters": {
            "litellm": {
                "enabled": cfg.adapters.litellm.enabled,
                "base_url": cfg.adapters.litellm.base_url,
                "api_key": "***REDACTED***"
                if redact and cfg.adapters.litellm.api_key
                else cfg.adapters.litellm.api_key,
                "api_key_env": cfg.adapters.litellm.api_key_env,
                "skip_models": list(cfg.adapters.litellm.skip_models),
            },
            "hermes": {"enabled": cfg.adapters.hermes.enabled},
            "openclaw": {"enabled": cfg.adapters.openclaw.enabled},
            "codex": {"enabled": cfg.adapters.codex.enabled},
            "claude": {"enabled": cfg.adapters.claude.enabled},
            "zcode": {"enabled": cfg.adapters.zcode.enabled},
        },
        "profile": cfg.profile,
        "companion_policy_path": cfg.companion_policy_path,
    }
    return yaml.dump(data, default_flow_style=False, sort_keys=False)
