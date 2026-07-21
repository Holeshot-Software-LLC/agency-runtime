"""Environment detection for `agency configure` wizard.

Probes the local machine for LLM providers, API keys, and host adapters
to generate a config that matches what's actually installed.

Model discovery:
- Ollama: GET /api/tags → real installed models
- OpenAI: GET /v1/models → real available models (if key is set)
- LiteLLM: GET /v1/models → real model groups (if proxy is running)
- LM Studio / custom: GET /v1/models → whatever the endpoint exposes
"""

from __future__ import annotations

import os
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.cli_transport import (
    SUPPORTED_CLI_TRANSPORTS,
    CLIProviderStatus,
    inspect_cli_transport,
)
from agency_runtime.core.config import (
    MAX_PROVIDER_CHAIN_ENTRIES,
    is_safe_credential_url,
)
from agency_runtime.core.http_safety import open_no_redirect

_MAX_HTTP_JSON_BYTES = 1024 * 1024
_MAX_DISCOVERED_MODELS = 1000
_MAX_MODEL_ID_CHARS = 512


@dataclass
class ProviderDetection:
    ollama_available: bool = False
    ollama_models: list[str] = field(default_factory=list)
    ollama_base_url: str = "http://127.0.0.1:11434"

    openai_key_present: bool = False
    openai_key_env: str = "OPENAI_API_KEY"
    openai_models: list[str] = field(default_factory=list)

    anthropic_key_present: bool = False
    anthropic_key_env: str = "ANTHROPIC_API_KEY"

    litellm_available: bool = False
    litellm_base_url: str = "http://127.0.0.1:4000"
    litellm_models: list[str] = field(default_factory=list)

    # For display backwards compat
    @property
    def openai_key(self) -> bool:
        return self.openai_key_present

    @property
    def anthropic_key(self) -> bool:
        return self.anthropic_key_present


@dataclass
class AdapterDetection:
    hermes: bool = False
    openclaw: bool = False
    codex: bool = False
    claude: bool = False


@dataclass
class DetectionResult:
    providers: ProviderDetection = field(default_factory=ProviderDetection)
    adapters: AdapterDetection = field(default_factory=AdapterDetection)
    cli_providers: dict[str, CLIProviderStatus] = field(default_factory=dict)

    @property
    def has_any_provider(self) -> bool:
        return (
            self.providers.ollama_available
            or self.providers.openai_key_present
            or self.providers.anthropic_key_present
            or self.providers.litellm_available
            or any(item.usable for item in self.cli_providers.values())
        )

    @property
    def has_any_adapter(self) -> bool:
        return any(
            [
                self.adapters.hermes,
                self.adapters.openclaw,
                self.adapters.codex,
                self.adapters.claude,
            ]
        )


# ── HTTP helpers ──────────────────────────────────────────────


def _http_get_json(
    url: str,
    *,
    timeout: float = 2.0,
    headers: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    try:
        req = urllib.request.Request(url, headers=headers or {})
        with open_no_redirect(req, timeout=timeout) as resp:
            raw = resp.read(_MAX_HTTP_JSON_BYTES + 1)
        if len(raw) > _MAX_HTTP_JSON_BYTES:
            return None
        parsed = safe_load_bounded_json(
            raw,
            maximum_bytes=_MAX_HTTP_JSON_BYTES,
            maximum_depth=32,
            maximum_nodes=10_000,
        )
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _http_check(url: str, timeout: float = 2.0) -> bool:
    try:
        req = urllib.request.Request(url)
        with open_no_redirect(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def _fetch_model_list(base_url: str, api_key: str | None = None) -> list[str]:
    """Fetch available models from an OpenAI-compatible /v1/models endpoint."""
    if api_key and not is_safe_credential_url(base_url):
        return []
    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    normalized = base_url.rstrip("/")
    models_url = (
        f"{normalized}/models" if normalized.lower().endswith("/v1") else f"{normalized}/v1/models"
    )
    data = _http_get_json(models_url, timeout=5, headers=headers)
    if data is None:
        return []
    entries = data.get("data", [])
    if not isinstance(entries, list):
        return []
    models: set[str] = set()
    for entry in entries[:_MAX_DISCOVERED_MODELS]:
        if not isinstance(entry, dict):
            continue
        model_id = entry.get("id", entry.get("model", ""))
        if not isinstance(model_id, str):
            continue
        if (
            model_id
            and model_id == model_id.strip()
            and len(model_id) <= _MAX_MODEL_ID_CHARS
            and not any(ord(char) < 32 or 127 <= ord(char) < 160 for char in model_id)
        ):
            models.add(model_id)
    return sorted(models)


# ── Provider detection ────────────────────────────────────────


def detect_providers(
    *,
    ollama_base_url: str = "http://127.0.0.1:11434",
    litellm_base_url: str = "http://127.0.0.1:4000",
) -> ProviderDetection:
    """Detect available LLM providers and discover their models."""
    result = ProviderDetection(
        ollama_base_url=ollama_base_url,
        litellm_base_url=litellm_base_url,
    )

    openai_key = os.environ.get("OPENAI_API_KEY", "")
    litellm_key = os.environ.get("LITELLM_API_KEY", "")
    with ThreadPoolExecutor(
        max_workers=4,
        thread_name_prefix="agency-detect",
    ) as executor:
        ollama_future = executor.submit(
            _http_get_json,
            f"{ollama_base_url}/api/tags",
            timeout=2,
        )
        litellm_health_future = executor.submit(
            _http_check,
            f"{litellm_base_url}/health/liveness",
            2,
        )
        litellm_models_future = executor.submit(
            _fetch_model_list,
            litellm_base_url,
            litellm_key or None,
        )
        openai_models_future = (
            executor.submit(
                _fetch_model_list,
                "https://api.openai.com/v1",
                openai_key,
            )
            if openai_key
            else None
        )

        tags = ollama_future.result()
        result.litellm_available = litellm_health_future.result()
        discovered_litellm_models = litellm_models_future.result()
        discovered_openai_models = (
            openai_models_future.result() if openai_models_future is not None else []
        )

    # Ollama — get real installed models
    if tags is not None:
        result.ollama_available = True
        entries = tags.get("models", [])
        models: set[str] = set()
        if isinstance(entries, list):
            for entry in entries[:_MAX_DISCOVERED_MODELS]:
                if not isinstance(entry, dict):
                    continue
                name = entry.get("name", entry.get("model", ""))
                if not isinstance(name, str):
                    continue
                name = name.strip()
                if name and len(name) <= _MAX_MODEL_ID_CHARS:
                    models.add(name)
        result.ollama_models = sorted(models)

    # OpenAI — check key, then try to list models
    result.openai_key_present = bool(openai_key)
    result.openai_models = discovered_openai_models

    # Anthropic — just check key (Anthropic doesn't have a /models endpoint)
    result.anthropic_key_present = bool(os.environ.get("ANTHROPIC_API_KEY", ""))

    # LiteLLM — check health, then list model groups
    if result.litellm_available:
        result.litellm_models = discovered_litellm_models

    return result


def detect_adapters() -> AdapterDetection:
    """Detect current hosts through the canonical cross-platform inventory."""

    from agency_runtime.core.installer import detect_installed_agents

    try:
        installed = set(detect_installed_agents())
    except (OSError, RuntimeError, ValueError):
        installed = set()
    return AdapterDetection(
        hermes="hermes" in installed,
        openclaw="openclaw" in installed,
        codex="codex" in installed,
        claude="claude" in installed,
    )


def detect_cli_providers() -> dict[str, CLIProviderStatus]:
    """Inspect supported CLI judge transports without invoking a model."""

    transports = sorted(SUPPORTED_CLI_TRANSPORTS)
    with ThreadPoolExecutor(
        max_workers=len(transports),
        thread_name_prefix="agency-cli-detect",
    ) as executor:
        statuses = executor.map(inspect_cli_transport, transports)
        return dict(zip(transports, statuses, strict=True))


def detect_all() -> DetectionResult:
    """Run full detection."""

    with ThreadPoolExecutor(
        max_workers=3,
        thread_name_prefix="agency-inventory",
    ) as executor:
        providers = executor.submit(detect_providers)
        adapters = executor.submit(detect_adapters)
        cli_providers = executor.submit(detect_cli_providers)
        return DetectionResult(
            providers=providers.result(),
            adapters=adapters.result(),
            cli_providers=cli_providers.result(),
        )


# ── Config generation from detection ─────────────────────────


# Known good defaults per provider — used when model discovery fails
_PROVIDER_DEFAULTS: dict[str, dict[str, Any]] = {
    "openai": {
        "model": "gpt-5.4-mini",
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
    },
    "anthropic": {
        "model": "claude-sonnet-5",
        "base_url": "https://api.anthropic.com/v1",
        "api_key_env": "ANTHROPIC_API_KEY",
    },
    "litellm": {
        "model": "",  # Must be picked — no safe default
        "base_url": "http://127.0.0.1:4000",
        "api_key_env": "LITELLM_API_KEY",
    },
}

# Common OpenAI models shown as suggestions if discovery fails
_OPENAI_SUGGESTIONS = [
    "gpt-5.4-mini",
    "gpt-5.4-nano",
    "gpt-5.4",
    "gpt-5.5",
]

_ANTHROPIC_SUGGESTIONS = [
    "claude-sonnet-5",
    "claude-haiku-4-5",
    "claude-opus-4-8",
]


def _preferred_model(discovered: list[str], preferred: list[str], fallback: str) -> str:
    """Choose a known preferred model before falling back to provider ordering."""
    available = {model.lower(): model for model in discovered}
    for model in preferred:
        if model.lower() in available:
            return available[model.lower()]
    return discovered[0] if discovered else fallback


def _local_judge_config(providers: ProviderDetection) -> dict[str, Any]:
    return {
        "model": providers.ollama_models[0] if providers.ollama_models else "qwen3.5:2b",
        "base_url": providers.ollama_base_url,
        "api_key": "",
        "ollama_mode": True,
    }


def _generated_judge_config(
    providers: ProviderDetection,
    profile: str,
) -> dict[str, Any]:
    if profile == "local-only":
        return _local_judge_config(providers)
    if providers.litellm_available and providers.litellm_models:
        return {
            "model": providers.litellm_models[0],
            "base_url": providers.litellm_base_url,
            "api_key_env": "LITELLM_API_KEY",
            "ollama_mode": False,
        }
    if providers.openai_key_present:
        return {
            "model": _preferred_model(
                providers.openai_models,
                _OPENAI_SUGGESTIONS,
                _PROVIDER_DEFAULTS["openai"]["model"],
            ),
            "base_url": _PROVIDER_DEFAULTS["openai"]["base_url"],
            "api_key_env": "OPENAI_API_KEY",
            "ollama_mode": False,
        }
    if providers.ollama_available:
        return _local_judge_config(providers)
    return {
        "model": "qwen3.5:2b",
        "base_url": "http://127.0.0.1:11434",
        "api_key": "",
        "ollama_mode": True,
    }


def _generated_ollama_config(providers: ProviderDetection) -> dict[str, Any]:
    config: dict[str, Any] = {
        "enabled": providers.ollama_available,
        "base_url": providers.ollama_base_url,
    }
    if providers.ollama_available and providers.ollama_models:
        config["model"] = providers.ollama_models[0]
    return config


def _litellm_skip_models(
    providers: ProviderDetection,
    judge: dict[str, Any],
) -> list[str]:
    skip_models = ["complexity_router", "auto_router/"]
    if judge.get("base_url") == providers.litellm_base_url and judge.get("model"):
        model = judge["model"]
        if model not in skip_models:
            skip_models.append(model)
    return skip_models


def _litellm_provider(
    providers: ProviderDetection,
    judge: dict[str, Any],
) -> dict[str, Any] | None:
    if not providers.litellm_available:
        return None
    model = providers.litellm_models[0] if providers.litellm_models else judge.get("model", "")
    if not model:
        return None
    return {
        "name": "litellm",
        "type": "litellm",
        "model": model,
        "base_url": providers.litellm_base_url,
        "api_key_env": "LITELLM_API_KEY",
        "ollama_mode": False,
    }


def _openai_provider(providers: ProviderDetection) -> dict[str, Any] | None:
    if not providers.openai_key_present:
        return None
    return {
        "name": "openai",
        "type": "openai-compatible",
        "model": _preferred_model(
            providers.openai_models,
            _OPENAI_SUGGESTIONS,
            _PROVIDER_DEFAULTS["openai"]["model"],
        ),
        "base_url": _PROVIDER_DEFAULTS["openai"]["base_url"],
        "api_key_env": "OPENAI_API_KEY",
        "ollama_mode": False,
    }


def _anthropic_provider(providers: ProviderDetection) -> dict[str, Any] | None:
    if not providers.anthropic_key_present:
        return None
    return {
        "name": "anthropic",
        "type": "anthropic",
        "model": _ANTHROPIC_SUGGESTIONS[0],
        "base_url": _PROVIDER_DEFAULTS["anthropic"]["base_url"],
        "api_key_env": "ANTHROPIC_API_KEY",
        "ollama_mode": False,
    }


def _cli_providers(detection: DetectionResult) -> list[dict[str, Any]]:
    providers: list[dict[str, Any]] = []
    for transport in ("codex", "claude"):
        status = detection.cli_providers.get(transport)
        if status is not None and status.usable:
            providers.append(
                {
                    "name": f"{transport}-cli",
                    "type": "cli",
                    "transport": transport,
                    "model": "",
                    "base_url": "",
                    "api_key": "",
                    "api_key_env": "",
                    "ollama_mode": False,
                }
            )
    return providers


def _ollama_provider(providers: ProviderDetection) -> dict[str, Any] | None:
    if not providers.ollama_available:
        return None
    return {
        "name": "ollama",
        "type": "ollama",
        "model": providers.ollama_models[0] if providers.ollama_models else "qwen3.5:2b",
        "base_url": providers.ollama_base_url,
        "api_key": "",
        "ollama_mode": True,
    }


def _generated_provider_chain(
    detection: DetectionResult,
    judge: dict[str, Any],
    profile: str,
) -> list[dict[str, Any]]:
    providers: list[dict[str, Any]] = []
    if profile != "local-only":
        providers.extend(
            item
            for item in (
                _litellm_provider(detection.providers, judge),
                _openai_provider(detection.providers),
                _anthropic_provider(detection.providers),
            )
            if item is not None
        )
        providers.extend(_cli_providers(detection))
    ollama = _ollama_provider(detection.providers)
    if ollama is not None:
        providers.append(ollama)
    return providers[:MAX_PROVIDER_CHAIN_ENTRIES]


def _adapter_enabled(profile: str, detected: bool) -> str:
    if profile == "local-only":
        return "false"
    return "true" if detected else "auto"


def _generated_adapters_config(
    detection: DetectionResult,
    profile: str,
    litellm_skip: list[str],
) -> dict[str, Any]:
    providers = detection.providers
    adapters = detection.adapters
    return {
        "litellm": {
            "enabled": _adapter_enabled(profile, providers.litellm_available),
            "base_url": providers.litellm_base_url,
            "api_key_env": "LITELLM_API_KEY",
            "skip_models": litellm_skip,
        },
        "hermes": {"enabled": _adapter_enabled(profile, adapters.hermes)},
        "openclaw": {"enabled": _adapter_enabled(profile, adapters.openclaw)},
        "codex": {"enabled": _adapter_enabled(profile, adapters.codex)},
        "claude": {"enabled": _adapter_enabled(profile, adapters.claude)},
    }


def _judge_for_provider_chain(
    judge: dict[str, Any],
    providers: list[dict[str, Any]],
) -> dict[str, Any]:
    if providers and all(item.get("type") == "cli" for item in providers):
        return {
            "model": "",
            "base_url": "",
            "api_key": "",
            "api_key_env": "",
            "ollama_mode": False,
        }
    return judge


def generate_config_from_detection(
    detection: DetectionResult,
    profile: str = "standard",
) -> dict[str, Any]:
    """Generate a config dict from detection results.

    Used by non-interactive mode and as defaults for interactive mode.
    """
    judge_cfg = _generated_judge_config(detection.providers, profile)
    ollama_cfg = _generated_ollama_config(detection.providers)
    litellm_skip = _litellm_skip_models(detection.providers, judge_cfg)
    providers_list = _generated_provider_chain(detection, judge_cfg, profile)
    judge_cfg = _judge_for_provider_chain(judge_cfg, providers_list)
    adapters_cfg = _generated_adapters_config(detection, profile, litellm_skip)

    return {
        "providers": providers_list,
        "judge": judge_cfg,
        "ollama": ollama_cfg,
        "selector": {
            "min_confidence": 0.4,
            "max_user_msg_len": 4000,
            "trivial_msg_threshold": 0,
        },
        "delegation": {
            "mode": "prefer",
            "preferred_min_units": 2,
            "strongly_preferred_min_units": 4,
            "strongly_preferred_min_confidence": 0.8,
            "child_inference_budget": 4,
            "child_inference_concurrency": 2,
            "child_cache_ttl_seconds": 900,
        },
        "store": {"db_path": "~/.agency-runtime/agency.db"},
        "server": {"host": "127.0.0.1", "port": 7800},
        "observability": {"capture_content": False, "retention_days": 30},
        "adapters": adapters_cfg,
        "profile": profile,
        "companion_policy_path": None,
    }
