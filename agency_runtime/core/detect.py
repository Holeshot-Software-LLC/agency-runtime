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

import importlib.util
import json
import os
import shutil
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


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

    @property
    def has_any_provider(self) -> bool:
        return (
            self.providers.ollama_available
            or self.providers.openai_key_present
            or self.providers.anthropic_key_present
            or self.providers.litellm_available
        )

    @property
    def has_any_adapter(self) -> bool:
        return any([
            self.adapters.hermes,
            self.adapters.openclaw,
            self.adapters.codex,
            self.adapters.claude,
            self.providers.litellm_available,
        ])


# ── HTTP helpers ──────────────────────────────────────────────


def _http_get_json(
    url: str,
    *,
    timeout: float = 2.0,
    headers: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    try:
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(_MAX_HTTP_JSON_BYTES + 1)
        if len(raw) > _MAX_HTTP_JSON_BYTES:
            return None
        parsed = json.loads(raw.decode("utf-8"))
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _http_check(url: str, timeout: float = 2.0) -> bool:
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def _fetch_model_list(base_url: str, api_key: str | None = None) -> list[str]:
    """Fetch available models from an OpenAI-compatible /v1/models endpoint."""
    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    normalized = base_url.rstrip("/")
    models_url = f"{normalized}/models" if normalized.lower().endswith("/v1") else f"{normalized}/v1/models"
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
        model_id = model_id.strip()
        if model_id and len(model_id) <= _MAX_MODEL_ID_CHARS:
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

    # Ollama — get real installed models
    tags = _http_get_json(f"{ollama_base_url}/api/tags", timeout=2)
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
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    result.openai_key_present = bool(openai_key)
    if openai_key:
        result.openai_models = _fetch_model_list("https://api.openai.com/v1", openai_key)

    # Anthropic — just check key (Anthropic doesn't have a /models endpoint)
    result.anthropic_key_present = bool(os.environ.get("ANTHROPIC_API_KEY", ""))

    # LiteLLM — check health, then list model groups
    result.litellm_available = _http_check(f"{litellm_base_url}/health/liveness", timeout=2)
    if result.litellm_available:
        litellm_key = os.environ.get("LITELLM_API_KEY", "")
        result.litellm_models = _fetch_model_list(litellm_base_url, litellm_key or None)

    return result


def detect_adapters() -> AdapterDetection:
    """Detect installed host adapters."""
    result = AdapterDetection()

    result.hermes = bool(
        shutil.which("hermes")
        or importlib.util.find_spec("hermes")
    )
    result.openclaw = bool(
        shutil.which("openclaw")
        or Path.home().joinpath(".openclaw").exists()
    )
    result.codex = bool(shutil.which("codex"))
    result.claude = bool(shutil.which("claude"))

    return result


def detect_all() -> DetectionResult:
    """Run full detection."""
    return DetectionResult(
        providers=detect_providers(),
        adapters=detect_adapters(),
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


def generate_config_from_detection(
    detection: DetectionResult,
    profile: str = "standard",
) -> dict[str, Any]:
    """Generate a config dict from detection results.

    Used by non-interactive mode and as defaults for interactive mode.
    """
    p = detection.providers
    a = detection.adapters

    # Determine judge config based on best-available provider
    if profile == "local-only":
        model = p.ollama_models[0] if p.ollama_models else "qwen3.5:2b"
        judge_cfg = {
            "model": model,
            "base_url": p.ollama_base_url,
            "api_key": "",
            "ollama_mode": True,
        }
    elif p.litellm_available and p.litellm_models:
        # Pick the first model — user can change via config
        judge_cfg: dict[str, Any] = {
            "model": p.litellm_models[0],
            "base_url": p.litellm_base_url,
            "api_key_env": "LITELLM_API_KEY",
            "ollama_mode": False,
        }
    elif p.openai_key_present:
        model = _preferred_model(
            p.openai_models,
            _OPENAI_SUGGESTIONS,
            _PROVIDER_DEFAULTS["openai"]["model"],
        )
        judge_cfg = {
            "model": model,
            "base_url": _PROVIDER_DEFAULTS["openai"]["base_url"],
            "api_key_env": "OPENAI_API_KEY",
            "ollama_mode": False,
        }
    elif p.ollama_available:
        model = p.ollama_models[0] if p.ollama_models else "qwen3.5:2b"
        judge_cfg = {
            "model": model,
            "base_url": p.ollama_base_url,
            "api_key": "",
            "ollama_mode": True,
        }
    else:
        # Nothing detected — default to Ollama URL, will fail gracefully
        judge_cfg = {
            "model": "qwen3.5:2b",
            "base_url": "http://127.0.0.1:11434",
            "api_key": "",
            "ollama_mode": True,
        }

    # Ollama fallback config
    ollama_cfg: dict[str, Any] = {
        "enabled": p.ollama_available,
        "base_url": p.ollama_base_url,
    }
    if p.ollama_available and p.ollama_models:
        ollama_cfg["model"] = p.ollama_models[0]

    # Adapter config
    def adapter_enabled(detected: bool) -> str:
        if profile == "local-only":
            return "false"
        return "true" if detected else "auto"

    # If LiteLLM is the judge provider, add the chosen model to skip_models
    # so routing doesn't recurse into itself
    litellm_skip = ["complexity_router", "auto_router/"]
    if judge_cfg.get("base_url") == p.litellm_base_url and judge_cfg.get("model"):
        skip_model = judge_cfg["model"]
        if skip_model not in litellm_skip:
            litellm_skip.append(skip_model)

    # Build providers fallback chain — ordered list of all detected providers
    providers_list: list[dict[str, Any]] = []

    # LiteLLM proxy (highest priority if detected)
    if profile != "local-only" and p.litellm_available:
        litellm_model = p.litellm_models[0] if p.litellm_models else judge_cfg.get("model", "")
        if litellm_model:
            providers_list.append({
                "name": "litellm",
                "type": "litellm",
                "model": litellm_model,
                "base_url": p.litellm_base_url,
                "api_key_env": "LITELLM_API_KEY",
                "ollama_mode": False,
            })

    # OpenAI API
    if profile != "local-only" and p.openai_key_present:
        openai_model = _preferred_model(
            p.openai_models,
            _OPENAI_SUGGESTIONS,
            _PROVIDER_DEFAULTS["openai"]["model"],
        )
        providers_list.append({
            "name": "openai",
            "type": "openai-compatible",
            "model": openai_model,
            "base_url": _PROVIDER_DEFAULTS["openai"]["base_url"],
            "api_key_env": "OPENAI_API_KEY",
            "ollama_mode": False,
        })

    # Anthropic API
    if profile != "local-only" and p.anthropic_key_present:
        providers_list.append({
            "name": "anthropic",
            "type": "anthropic",
            "model": _ANTHROPIC_SUGGESTIONS[0],
            "base_url": _PROVIDER_DEFAULTS["anthropic"]["base_url"],
            "api_key_env": "ANTHROPIC_API_KEY",
            "ollama_mode": False,
        })

    # Ollama (local, free — always last in the chain if available)
    if p.ollama_available:
        ollama_model = p.ollama_models[0] if p.ollama_models else "qwen3.5:2b"
        providers_list.append({
            "name": "ollama",
            "type": "ollama",
            "model": ollama_model,
            "base_url": p.ollama_base_url,
            "api_key": "",
            "ollama_mode": True,
        })

    adapters_cfg: dict[str, Any] = {
        "litellm": {
            "enabled": (
                "false"
                if profile == "local-only"
                else ("true" if p.litellm_available else "auto")
            ),
            "base_url": p.litellm_base_url,
            "api_key_env": "LITELLM_API_KEY",
            "skip_models": litellm_skip,
        },
        "hermes": {"enabled": adapter_enabled(a.hermes)},
        "openclaw": {"enabled": adapter_enabled(a.openclaw)},
        "codex": {"enabled": adapter_enabled(a.codex)},
        "claude": {"enabled": adapter_enabled(a.claude)},
    }

    return {
        "providers": providers_list,
        "judge": judge_cfg,
        "ollama": ollama_cfg,
        "selector": {
            "min_confidence": 0.4,
            "max_user_msg_len": 4000,
            "trivial_msg_threshold": 12,
        },
        "store": {"db_path": "~/.agency-runtime/agency.db"},
        "server": {"host": "127.0.0.1", "port": 7800},
        "observability": {"capture_content": False, "retention_days": 30},
        "adapters": adapters_cfg,
        "profile": profile,
        "companion_policy_path": None,
    }
