"""LLM judge — query a model to select specialists from candidates.

Uses the centralized config system for all model/URL/key/tuning values.
No hardcoded user-specific identifiers.

Fallback chain (in priority order):
1. Each provider in cfg.providers (user-configured priority list)
2. Legacy judge config (cfg.judge — backward compat for existing configs)
3. Ollama fallback (cfg.ollama — if enabled)
4. Token-only (no LLM call, uses pre_narrow scores)
"""

from __future__ import annotations

import json
import logging
import math
import re
import time
import urllib.request
from typing import Any

from agency_runtime.core.config import (
    MAX_PROVIDER_CHAIN_ENTRIES,
    AgencyConfig,
    JudgeConfig,
    ProviderEntry,
    _is_loopback_http_url,
    is_safe_credential_url,
    load_config,
)
from agency_runtime.core.http_safety import open_no_redirect
from agency_runtime.core.selector.candidate_narrow import pre_narrow
from agency_runtime.core.cli_transport import (
    SUPPORTED_CLI_TRANSPORTS,
    invoke_cli_judge,
)

logger = logging.getLogger("agency_runtime.selector.judge")

_MAX_JUDGE_RESPONSE_BYTES = 256 * 1024
_MAX_PROVIDER_ATTEMPTS = MAX_PROVIDER_CHAIN_ENTRIES
_MAX_JUDGE_DEADLINE_SECONDS = 60.0


def _bounded_confidence(value: Any) -> float | None:
    """Parse model confidence and constrain it to the public 0..1 contract."""
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(confidence):
        return None
    return max(0.0, min(1.0, confidence))


def _attempt_signature(
    base_url: str,
    model: str,
    ollama_mode: bool,
    provider_type: str = "openai-compatible",
    transport: str = "",
) -> tuple[str, str, str]:
    """Identify equivalent network attempts across new and legacy config."""
    normalized_type = provider_type.strip().lower()
    if normalized_type == "cli":
        return "cli", transport.strip().lower(), model.strip().lower()
    protocol = "ollama" if ollama_mode else normalized_type
    return protocol, base_url.rstrip("/").lower(), model.strip().lower()


def _provider_is_attemptable(provider: ProviderEntry) -> bool:
    provider_type = provider.type.strip().lower()
    if provider_type == "cli":
        return provider.transport.strip().lower() in SUPPORTED_CLI_TRANSPORTS
    if not provider.model or not provider.base_url:
        return False
    return (
        provider_type == "ollama"
        or provider.ollama_mode
        or bool(provider.resolve_api_key())
        or (
            provider_type in {"openai", "openai-compatible", "litellm"}
            and _is_loopback_http_url(provider.base_url)
        )
    )


def _network_target_signature(base_url: str, model: str) -> tuple[str, str]:
    """Identify a concrete endpoint/model independent of protocol metadata."""
    return base_url.rstrip("/").lower(), model.strip().lower()


def _bounded_duration(value: Any, *, maximum: float) -> float:
    """Return a finite positive duration constrained to *maximum*."""
    try:
        duration = float(value)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(duration) or duration <= 0:
        return 0.0
    return min(duration, maximum)


def _read_json_object(response: Any) -> dict[str, Any] | None:
    """Read one bounded JSON object from an HTTP response."""
    try:
        raw = response.read(_MAX_JUDGE_RESPONSE_BYTES + 1)
        if len(raw) > _MAX_JUDGE_RESPONSE_BYTES:
            return None
        parsed = json.loads(raw.decode("utf-8"))
    except (OSError, UnicodeError, ValueError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _with_cumulative_latency(
    result: dict[str, Any],
    attempts_started: float,
) -> dict[str, Any]:
    elapsed_ms = int((time.monotonic() - attempts_started) * 1000)
    result["latency_ms"] = max(int(result.get("latency_ms", 0) or 0), elapsed_ms)
    return result


def parse_json_response(text: str) -> dict[str, Any] | None:
    """Parse JSON from a model response, handling markdown fences."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(text[start : end + 1])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    return None


def _build_judge_prompt(
    task_description: str,
    candidates: list[dict[str, Any]],
    max_sel: int,
) -> str:
    """Build the bounded semantic-selection prompt shared by all transports."""

    judge_candidates = candidates[:20]
    catalog_lines = []
    for agent in judge_candidates:
        slug = agent.get("slug", "")
        desc = agent.get("description", "")[:80]
        catalog_lines.append(f"  {slug}: {desc}")
    catalog_str = "\n".join(catalog_lines)
    return (
        f"Task: {task_description}\n\n"
        f"Select 1-{max_sel} specialists from these {len(judge_candidates)} "
        f"candidates. Return JSON only.\n\n"
        f"Candidates:\n{catalog_str}\n\n"
        f'Return: {{"selected_ids": ["id1"], "confidence": 0.9}}'
    )


def _build_judge_payload(
    task_description: str,
    candidates: list[dict[str, Any]],
    max_sel: int,
    ollama_mode: bool,
    provider_type: str = "openai-compatible",
) -> tuple[bytes, str, str]:
    """Build the HTTP request payload and return (body, url_path, content_type)."""
    user_content = _build_judge_prompt(task_description, candidates, max_sel)

    if ollama_mode:
        payload = json.dumps({
            "model": "",  # filled by caller
            "stream": False,
            "think": False,
            "format": "json",
            "options": {
                "temperature": 0,
                "num_predict": 128,
                "num_ctx": 8192,
            },
            "messages": [
                {
                    "role": "system",
                    "content": "You are a semantic selector. Return strict JSON only.",
                },
                {"role": "user", "content": user_content},
            ],
        }).encode("utf-8")
        return payload, "/api/chat", "application/json"

    if provider_type == "anthropic":
        payload = json.dumps({
            "model": "",  # filled by caller
            "system": "You are a semantic selector. Return strict JSON only.",
            "messages": [{"role": "user", "content": user_content}],
            "max_tokens": 256,
            "temperature": 0.0,
        }).encode("utf-8")
        return payload, "/v1/messages", "application/json"

    payload = json.dumps({
        "model": "",  # filled by caller
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a semantic selector for AI agent specialists. "
                    "Return strict JSON only. No markdown fences."
                ),
            },
            {"role": "user", "content": user_content},
        ],
        "max_tokens": 256,
        "temperature": 0.0,
        "stream": False,
    }).encode("utf-8")
    return payload, "/v1/chat/completions", "application/json"


def _join_api_path(base_url: str, path: str) -> str:
    """Join API paths without producing duplicate `/v1/v1/...` segments."""
    base = base_url.rstrip("/")
    normalized_path = "/" + path.lstrip("/")
    if base.lower().endswith("/v1") and normalized_path.lower().startswith("/v1/"):
        normalized_path = normalized_path[3:]
    return f"{base}{normalized_path}"


def _try_provider(
    provider: ProviderEntry,
    task_description: str,
    candidates: list[dict[str, Any]],
    max_sel: int,
    candidate_count: int,
    top_score: float,
    request_timeout: float | None = None,
) -> dict[str, Any] | None:
    """Try a single provider. Returns result dict on success, None on failure."""

    api_key = provider.resolve_api_key()
    provider_type = provider.type.strip().lower()
    ollama_mode = provider.ollama_mode or provider_type == "ollama"

    if provider_type == "cli":
        prompt = _build_judge_prompt(task_description, candidates, max_sel)
        started = time.monotonic()
        try:
            parsed = invoke_cli_judge(
                provider,
                prompt,
                timeout=(
                    provider.timeout
                    if request_timeout is None
                    else request_timeout
                ),
            )
        except Exception as exc:
            logger.debug(
                "provider %s failed (%s)",
                provider.name[:80],
                type(exc).__name__,
            )
            return None
        if parsed is None:
            return None
        selected = parsed.get("selected_ids") or parsed.get("selected") or []
        if not isinstance(selected, list):
            return None
        known_ids = {agent.get("slug", "") for agent in candidates}
        valid_selected = list(dict.fromkeys(
            str(item) for item in selected if str(item) in known_ids
        ))
        confidence = _bounded_confidence(parsed.get("confidence"))
        if not valid_selected or confidence is None:
            return None
        return {
            "selected_ids": valid_selected[:max_sel],
            "confidence": confidence,
            "latency_ms": int((time.monotonic() - started) * 1000),
            "status": "applied",
            "provider": (
                f"{provider.name} (cli:{provider.transport.strip().lower()})"
            ),
            "candidate_count": candidate_count,
            "top_score": top_score,
        }

    # Auth check
    if not provider.model or not provider.base_url:
        logger.debug("provider %s: model or base URL missing, skipping", provider.name)
        return None
    keyless_loopback = (
        provider_type in {"openai", "openai-compatible", "litellm"}
        and _is_loopback_http_url(provider.base_url)
    )
    if not ollama_mode and not api_key and not keyless_loopback:
        logger.debug("provider %s: no api key, skipping", provider.name)
        return None
    if api_key and not is_safe_credential_url(provider.base_url):
        logger.debug("provider %s: unsafe credential transport, skipping", provider.name)
        return None

    body, path, content_type = _build_judge_payload(
        task_description,
        candidates,
        max_sel,
        ollama_mode,
        provider_type,
    )
    body_json = json.loads(body)
    body_json["model"] = provider.model
    if (
        provider_type in {"openai", "openai-compatible"}
        and provider.model.lower().startswith("gpt-5")
    ):
        body_json["max_completion_tokens"] = body_json.pop("max_tokens", 256)
        body_json.pop("temperature", None)
    body = json.dumps(body_json).encode("utf-8")

    request_url = _join_api_path(provider.base_url, path)
    headers = {"Content-Type": content_type}
    if api_key:
        if provider_type == "anthropic":
            headers["x-api-key"] = api_key
            headers["anthropic-version"] = "2023-06-01"
        else:
            headers["Authorization"] = f"Bearer {api_key}"

    timeout = _bounded_duration(
        provider.timeout if request_timeout is None else request_timeout,
        maximum=_MAX_JUDGE_DEADLINE_SECONDS,
    )
    if timeout <= 0:
        return None

    req = urllib.request.Request(request_url, data=body, headers=headers, method="POST")
    t0 = time.monotonic()
    try:
        with open_no_redirect(req, timeout=timeout) as resp:
            data = _read_json_object(resp)
    except Exception as exc:
        logger.debug("provider %s failed (%s)", provider.name[:80], type(exc).__name__)
        return None
    if data is None:
        logger.debug("provider %s returned an invalid or oversized response", provider.name[:80])
        return None

    elapsed = time.monotonic() - t0

    content = ""
    if provider_type == "anthropic":
        blocks = data.get("content", []) if isinstance(data, dict) else []
        if isinstance(blocks, list):
            content = "".join(
                str(block.get("text", ""))
                for block in blocks
                if isinstance(block, dict) and block.get("type") == "text"
            )
    else:
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            content = data.get("message", {}).get("content", "") if ollama_mode else str(data)

    parsed = parse_json_response(content)
    if parsed is None:
        # Parse failed; fall through to the deterministic token-only fallback.
        return None

    selected = parsed.get("selected_ids") or parsed.get("selected") or []
    if not isinstance(selected, list):
        return None

    known_ids = {a.get("slug", "") for a in candidates}
    valid_selected = list(dict.fromkeys(
        str(sid) for sid in selected if str(sid) in known_ids
    ))

    if not valid_selected:
        # A syntactically valid response that selects no catalog member is not
        # a successful attempt. Let the next provider evaluate the task.
        return None

    confidence = _bounded_confidence(parsed.get("confidence"))
    if confidence is None:
        return None

    return {
        "selected_ids": valid_selected[:max_sel],
        "confidence": confidence,
        "latency_ms": int(elapsed * 1000),
        "status": "applied",
        "provider": f"{provider.name} ({provider_type})",
        "candidate_count": candidate_count,
        "top_score": top_score,
    }


def _try_legacy_judge(
    jc: JudgeConfig,
    task_description: str,
    candidates: list[dict[str, Any]],
    max_sel: int,
    candidate_count: int,
    top_score: float,
    request_timeout: float | None = None,
) -> dict[str, Any] | None:
    """Try the legacy judge config (backward compat). Returns result or None."""

    api_key = jc.resolve_api_key()
    if not jc.model or not jc.base_url:
        return None
    if api_key and not is_safe_credential_url(jc.base_url):
        logger.debug("legacy judge: unsafe credential transport, skipping")
        return None

    ollama_mode = jc.ollama_mode
    body, path, content_type = _build_judge_payload(
        task_description, candidates, max_sel, ollama_mode
    )
    body_json = json.loads(body)
    body_json["model"] = jc.model
    if not ollama_mode and jc.model.lower().startswith("gpt-5"):
        body_json["max_completion_tokens"] = body_json.pop("max_tokens", 256)
        body_json.pop("temperature", None)
    body = json.dumps(body_json).encode("utf-8")

    request_url = _join_api_path(jc.base_url, path)
    headers = {"Content-Type": content_type}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    timeout = _bounded_duration(
        jc.timeout if request_timeout is None else request_timeout,
        maximum=_MAX_JUDGE_DEADLINE_SECONDS,
    )
    if timeout <= 0:
        return None

    req = urllib.request.Request(request_url, data=body, headers=headers, method="POST")
    t0 = time.monotonic()
    try:
        with open_no_redirect(req, timeout=timeout) as resp:
            data = _read_json_object(resp)
    except Exception as exc:
        logger.debug("legacy judge failed (%s)", type(exc).__name__)
        return None
    if data is None:
        logger.debug("legacy judge returned an invalid or oversized response")
        return None

    elapsed = time.monotonic() - t0
    result: dict[str, Any] = {
        "selected_ids": [],
        "confidence": 0.0,
        "latency_ms": int(elapsed * 1000),
        "status": "unknown",
        "error": "",
    }
    result["provider"] = jc.model

    content = ""
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        content = data.get("message", {}).get("content", "") if ollama_mode else str(data)

    parsed = parse_json_response(content)
    if parsed is None:
        return None

    selected = parsed.get("selected_ids") or parsed.get("selected") or []
    if not isinstance(selected, list):
        return None

    known_ids = {a.get("slug", "") for a in candidates}
    valid_selected = list(dict.fromkeys(
        str(sid) for sid in selected if str(sid) in known_ids
    ))

    if not valid_selected:
        return None

    confidence = _bounded_confidence(parsed.get("confidence"))
    if confidence is None:
        return None

    result["selected_ids"] = valid_selected[:max_sel]
    result["confidence"] = confidence
    result["candidate_count"] = candidate_count
    result["top_score"] = top_score
    result["status"] = "applied"
    return result


def query_judge(
    task_description: str,
    catalog: list[dict[str, Any]],
    *,
    config: AgencyConfig | None = None,
    judge_config: JudgeConfig | None = None,
    max_selected: int | None = None,
) -> dict[str, Any]:
    """Query the agency judge model to select specialists.

    Fallback chain (first success wins):
    1. Each provider in a nonempty cfg.providers chain, then token-only.
    2. For legacy configs with no provider chain: cfg.judge, cfg.ollama,
       then token-only.
    """
    cfg = config or load_config()
    jc = judge_config or cfg.judge
    max_sel = max_selected or jc.max_selected
    attempts_started = time.monotonic()
    deadline = attempts_started + _bounded_duration(
        jc.timeout,
        maximum=_MAX_JUDGE_DEADLINE_SECONDS,
    )

    result: dict[str, Any] = {
        "selected_ids": [],
        "confidence": 0.0,
        "latency_ms": 0,
        "status": "unknown",
        "error": "",
    }

    if not catalog:
        result["status"] = "no_catalog"
        result["error"] = "agent catalog not loaded"
        return result

    candidates, scores = pre_narrow(task_description, catalog)
    candidate_count = len(candidates)
    top_score = scores[0] if scores else 0.0

    # Confidence bypass — skip LLM entirely
    if top_score >= jc.confidence_bypass_threshold:
        bypass_ids = [
            a.get("slug", "")
            for a, s in zip(candidates, scores)
            if s > 0
        ][:max_sel]
        if bypass_ids:
            result["selected_ids"] = bypass_ids
            result["confidence"] = min(0.99, 0.7 + top_score / 100)
            result["latency_ms"] = 0
            result["status"] = "confidence_bypass"
            result["candidate_count"] = candidate_count
            result["top_score"] = top_score
            return result

    # Layer 1: Iterate providers list (user-configured fallback chain)
    attempted: set[tuple[str, str, str]] = set()
    attempted_targets: set[tuple[str, str]] = set()
    attempt_count = 0

    def reserve_attempt(configured_timeout: float) -> float:
        """Reserve one bounded network attempt and return its remaining timeout."""
        nonlocal attempt_count
        if attempt_count >= _MAX_PROVIDER_ATTEMPTS:
            return 0.0
        remaining = deadline - time.monotonic()
        per_attempt = _bounded_duration(
            configured_timeout,
            maximum=_MAX_JUDGE_DEADLINE_SECONDS,
        )
        timeout = min(remaining, per_attempt)
        if timeout <= 0:
            return 0.0
        attempt_count += 1
        return timeout

    for provider in cfg.providers:
        signature = _attempt_signature(
            provider.base_url,
            provider.model,
            provider.ollama_mode,
            provider.type,
            provider.transport,
        )
        if signature in attempted or not _provider_is_attemptable(provider):
            continue
        configured_timeout = _bounded_duration(
            provider.timeout,
            maximum=_MAX_JUDGE_DEADLINE_SECONDS,
        )
        if configured_timeout <= 0:
            continue
        timeout = reserve_attempt(configured_timeout)
        if timeout <= 0:
            break
        attempted.add(signature)
        attempted_targets.add(
            (
                f"cli:{provider.transport.strip().lower()}",
                provider.model.strip().lower(),
            )
            if provider.type.strip().lower() == "cli"
            else _network_target_signature(provider.base_url, provider.model)
        )
        res = _try_provider(
            provider, task_description, candidates, max_sel,
            candidate_count, top_score,
            request_timeout=timeout,
        )
        if res is not None:
            return _with_cumulative_latency(res, attempts_started)
        logger.debug("provider %s failed, trying next", provider.name)

    # A typed provider chain is authoritative. Never make a hidden legacy or
    # Ollama request after the user removed it from that ordered chain.
    if cfg.providers:
        fallback = _token_only_fallback(
            candidates,
            scores,
            candidate_count,
            top_score,
            max_sel,
        )
        return _with_cumulative_latency(fallback, attempts_started)

    # Legacy layers apply only when the typed provider chain is absent.
    legacy_signature = _attempt_signature(jc.base_url, jc.model, jc.ollama_mode)
    legacy_target = _network_target_signature(jc.base_url, jc.model)
    if (
        jc.model
        and jc.base_url
        and legacy_signature not in attempted
        and legacy_target not in attempted_targets
    ):
        legacy_timeout = reserve_attempt(jc.timeout)
        if legacy_timeout > 0:
            attempted.add(legacy_signature)
            attempted_targets.add(legacy_target)
            legacy_result = _try_legacy_judge(
                jc, task_description, candidates, max_sel,
                candidate_count, top_score,
                request_timeout=legacy_timeout,
            )
            if legacy_result is not None:
                return _with_cumulative_latency(legacy_result, attempts_started)

    # Layer 3: Ollama fallback (if enabled and configured)
    if cfg.ollama.enabled and cfg.ollama.model:
        ollama_provider = ProviderEntry(
            name="ollama-fallback",
            type="ollama",
            model=cfg.ollama.model,
            base_url=cfg.ollama.base_url,
            ollama_mode=True,
            timeout=cfg.judge.timeout,
        )
        ollama_signature = _attempt_signature(
            ollama_provider.base_url,
            ollama_provider.model,
            ollama_provider.ollama_mode,
        )
        if ollama_signature not in attempted:
            ollama_timeout = reserve_attempt(ollama_provider.timeout)
            if ollama_timeout > 0:
                attempted.add(ollama_signature)
                ollama_result = _try_provider(
                    ollama_provider, task_description, candidates, max_sel,
                    candidate_count, top_score,
                    request_timeout=ollama_timeout,
                )
                if ollama_result is not None:
                    return _with_cumulative_latency(ollama_result, attempts_started)

    # Layer 4: Token-only (no LLM)
    fallback = _token_only_fallback(
        candidates,
        scores,
        candidate_count,
        top_score,
        max_sel,
    )
    return _with_cumulative_latency(fallback, attempts_started)


def _token_only_fallback(
    candidates: list[dict[str, Any]],
    scores: list[float],
    candidate_count: int,
    top_score: float,
    max_sel: int,
) -> dict[str, Any]:
    """Last resort: return top token-scored candidates without an LLM call."""
    has_signal = top_score > 0
    result: dict[str, Any] = {
        "selected_ids": (
            [
                agent.get("slug", "")
                for agent, score in zip(candidates, scores)
                if score > 0
            ][:max_sel]
            if has_signal
            else []
        ),
        "confidence": 0.3 if has_signal else 0.0,
        "latency_ms": 0,
        "status": "token_fallback" if has_signal else "abstained",
        "error": "" if has_signal else "no positive routing signal",
        "candidate_count": candidate_count,
        "top_score": top_score,
    }
    return result
