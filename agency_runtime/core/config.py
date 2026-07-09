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

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


# ── Config path resolution ────────────────────────────────────

_BUNDLED_DEFAULTS = Path(__file__).parent / "config_defaults.yaml"


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
        if self.type == "ollama":
            return "none"
        if self.api_key:
            return "api_key"
        if self.api_key_env and os.environ.get(self.api_key_env):
            return "env_key"
        if self.type == "cli":
            return "oauth"
        return "none"

    def is_available(self) -> bool:
        """Quick check: does this provider have auth and a model?"""
        if self.type == "ollama":
            return bool(self.model and self.base_url)
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
    trivial_msg_threshold: int = 12


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
    adapters: AdaptersConfig = field(default_factory=AdaptersConfig)
    profile: str = "standard"
    companion_policy_path: str | None = None
    config_path: str = ""  # where this config was loaded from


# ── YAML loading helpers ──────────────────────────────────────


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with open(path) as f:
        data = yaml.safe_load(f)
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
    return tuple(_build_provider_entry(p) for p in raw if isinstance(p, dict))


def _build_adapters(raw: dict[str, Any]) -> AdaptersConfig:
    litellm_raw = raw.get("litellm", {})
    if isinstance(litellm_raw, dict):
        # Ensure skip_models default is preserved if not overridden
        if "skip_models" not in litellm_raw:
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
    adapters_raw = raw.get("adapters", {})

    return AgencyConfig(
        judge=JudgeConfig(
            model=str(judge_raw.get("model", "")),
            base_url=str(judge_raw.get("base_url", "")),
            api_key_env=str(judge_raw.get("api_key_env", "")),
            api_key=str(judge_raw.get("api_key", "")),
            ollama_mode=bool(judge_raw.get("ollama_mode", False)),
            timeout=float(judge_raw.get("timeout", 15.0)),
            max_selected=int(judge_raw.get("max_selected", 3)),
            confidence_bypass_threshold=float(
                judge_raw.get("confidence_bypass_threshold", 15.0)
            ),
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
        adapters=_build_adapters(adapters_raw),
        profile=str(raw.get("profile", "standard")),
        companion_policy_path=raw.get("companion_policy_path"),
        config_path=config_path,
    )


# ── Env var override layer ────────────────────────────────────


def _apply_env_overrides(cfg: AgencyConfig) -> AgencyConfig:
    """Apply environment variable overrides on top of the config."""
    from dataclasses import asdict

    judge_replacements: dict[str, Any] = {}
    if v := os.environ.get("AGENCY_JUDGE_MODEL"):
        judge_replacements["model"] = v
    if v := os.environ.get("AGENCY_JUDGE_BASE_URL"):
        judge_replacements["base_url"] = v
    if v := os.environ.get("AGENCY_JUDGE_API_KEY"):
        judge_replacements["api_key"] = v
    elif v := os.environ.get("LITELLM_API_KEY"):
        if not cfg.judge.resolve_api_key():
            judge_replacements["api_key"] = v
    if v := os.environ.get("AGENCY_JUDGE_TIMEOUT"):
        try:
            judge_replacements["timeout"] = float(v)
        except ValueError:
            pass
    if v := os.environ.get("AGENCY_MAX_SELECTED"):
        try:
            judge_replacements["max_selected"] = int(v)
        except ValueError:
            pass
    if v := os.environ.get("AGENCY_BYPASS_THRESHOLD"):
        try:
            judge_replacements["confidence_bypass_threshold"] = float(v)
        except ValueError:
            pass

    if "model" in judge_replacements or "base_url" in judge_replacements:
        base = judge_replacements.get("base_url", cfg.judge.base_url)
        if "11434" not in base:
            judge_replacements["ollama_mode"] = False

    if judge_replacements:
        new_judge = JudgeConfig(**{**asdict(cfg.judge), **judge_replacements})
    else:
        new_judge = cfg.judge

    ollama_replacements: dict[str, Any] = {}
    if v := os.environ.get("OLLAMA_BASE_URL"):
        ollama_replacements["base_url"] = v
    if v := os.environ.get("AGENCY_OLLAMA_FALLBACK_MODEL"):
        ollama_replacements["model"] = v
    if ollama_replacements:
        new_ollama = OllamaConfig(**{**asdict(cfg.ollama), **ollama_replacements})
    else:
        new_ollama = cfg.ollama

    store_replacements: dict[str, Any] = {}
    if v := os.environ.get("AGENCY_DB_PATH"):
        store_replacements["db_path"] = v
    if store_replacements:
        new_store = StoreConfig(**{**asdict(cfg.store), **store_replacements})
    else:
        new_store = cfg.store

    return AgencyConfig(
        judge=new_judge,
        ollama=new_ollama,
        providers=cfg.providers,
        selector=cfg.selector,
        store=new_store,
        server=cfg.server,
        adapters=cfg.adapters,
        profile=cfg.profile,
        companion_policy_path=cfg.companion_policy_path,
        config_path=cfg.config_path,
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
        for key in ("judge", "ollama", "selector", "store", "server", "adapters"):
            if key in defaults_raw and key in file_raw:
                merged[key] = {**defaults_raw[key], **file_raw[key]}
        cfg = _dict_to_config(merged, config_path=str(config_path))

    # 3. Environment variable overrides
    cfg = _apply_env_overrides(cfg)

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
        "adapters": {
            "litellm": {
                "enabled": cfg.adapters.litellm.enabled,
                "base_url": cfg.adapters.litellm.base_url,
                "api_key": "***REDACTED***" if redact and cfg.adapters.litellm.api_key else cfg.adapters.litellm.api_key,
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
