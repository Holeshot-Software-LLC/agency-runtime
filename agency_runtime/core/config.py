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
import os
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml

from agency_runtime.core.bounded_io import FileSizeLimitError, read_bounded_regular_file
from agency_runtime.core.bounded_yaml import BoundedYAMLError, safe_load_bounded

# ── Config path resolution ────────────────────────────────────

_BUNDLED_DEFAULTS = Path(__file__).parent / "config_defaults.yaml"
MAX_PROVIDER_CHAIN_ENTRIES = 4
_CLI_MODEL_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/@+\-]{0,255}\Z")


def is_safe_cli_model_id(value: str) -> bool:
    """Accept an empty CLI default or one shell-neutral bounded model token."""

    return value == "" or (
        isinstance(value, str) and _CLI_MODEL_ID_PATTERN.fullmatch(value) is not None
    )


def _default_config_path() -> Path:
    """Return the user config path, checking env override."""
    env_path = os.environ.get("AGENCY_CONFIG_PATH", "")
    if env_path:
        return Path(env_path).expanduser()
    return Path.home() / ".agency-runtime" / "agency.yaml"


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
    min_confidence: float = 0.4
    max_user_msg_len: int = 4000
    trivial_msg_threshold: int = 5


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


@dataclass(frozen=True, slots=True)
class AgencyConfig:
    judge: JudgeConfig = field(default_factory=JudgeConfig)
    ollama: OllamaConfig = field(default_factory=OllamaConfig)
    providers: tuple[ProviderEntry, ...] = field(default_factory=tuple)
    selector: SelectorConfig = field(default_factory=SelectorConfig)
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
    try:
        data = safe_load_bounded(text)
    except BoundedYAMLError as exc:
        raise ValueError(str(exc)) from exc
    return data if isinstance(data, dict) else {}


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
    )


def _dict_to_config(raw: dict[str, Any], config_path: str = "") -> AgencyConfig:
    """Build AgencyConfig from a merged dict."""
    judge_raw = raw.get("judge", {})
    ollama_raw = raw.get("ollama", {})
    providers_raw = raw.get("providers", [])
    selector_raw = raw.get("selector", {})
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
            min_confidence=float(selector_raw.get("min_confidence", 0.4)),
            max_user_msg_len=int(selector_raw.get("max_user_msg_len", 4000)),
            trivial_msg_threshold=int(selector_raw.get("trivial_msg_threshold", 12)),
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


def _converted_env_value(
    environ: Mapping[str, str],
    name: str,
    converter: Callable[[str], Any],
) -> Any | None:
    raw = environ.get(name)
    if not raw:
        return None
    try:
        return converter(raw)
    except ValueError:
        return None


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
    for env_name, field_name, converter in (
        ("AGENCY_JUDGE_TIMEOUT", "timeout", float),
        ("AGENCY_MAX_SELECTED", "max_selected", int),
        ("AGENCY_BYPASS_THRESHOLD", "confidence_bypass_threshold", float),
    ):
        value = _converted_env_value(environ, env_name, converter)
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
        replacements["capture_content"] = capture_content.strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
    retention_days = _converted_env_value(environ, "AGENCY_RETENTION_DAYS", int)
    if retention_days is not None:
        replacements["retention_days"] = max(1, retention_days)
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
    dashboard_port = _converted_env_value(environment, "AGENCY_DASHBOARD_PORT", int)
    profile = environment.get("AGENCY_PROFILE", cfg.profile).strip() or cfg.profile
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

_cached_config: AgencyConfig | None = None


def load_config(path: str | Path | None = None, *, reload: bool = False) -> AgencyConfig:
    """Load config with precedence: env > file > bundled defaults.

    Args:
        path: Optional explicit config path (overrides AGENCY_CONFIG_PATH env).
        reload: Force a fresh load instead of returning the cached singleton.
    """
    global _cached_config
    if _cached_config is not None and not reload and path is None:
        return _cached_config

    # 1. Bundled defaults
    defaults_raw = _load_yaml(_BUNDLED_DEFAULTS)
    cfg = _dict_to_config(defaults_raw)

    # 2. User config file overlay
    config_path = Path(path).expanduser() if path else _default_config_path()
    if config_path.exists():
        file_raw = _load_yaml(config_path)
        merged = {**defaults_raw, **file_raw}
        # Deep-merge nested dicts (judge, ollama, selector, etc.)
        for key in (
            "judge",
            "ollama",
            "selector",
            "store",
            "server",
            "dashboard",
            "observability",
            "adapters",
        ):
            if key in defaults_raw and key in file_raw:
                merged[key] = {**defaults_raw[key], **file_raw[key]}
        cfg = _dict_to_config(merged, config_path=str(config_path))

    # 3. Environment variable overrides
    cfg = _apply_env_overrides(cfg)
    cfg = _enforce_profile_constraints(cfg)
    cfg = _enforce_credential_transport_constraints(cfg)

    if path is None:
        _cached_config = cfg
    return cfg


def reset_config_cache() -> None:
    """Clear the cached config singleton (for tests)."""
    global _cached_config
    _cached_config = None


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
            }
            for p in cfg.providers
        ],
        "selector": {
            "min_confidence": cfg.selector.min_confidence,
            "max_user_msg_len": cfg.selector.max_user_msg_len,
            "trivial_msg_threshold": cfg.selector.trivial_msg_threshold,
        },
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
        },
        "profile": cfg.profile,
        "companion_policy_path": cfg.companion_policy_path,
    }
    return yaml.dump(data, default_flow_style=False, sort_keys=False)
