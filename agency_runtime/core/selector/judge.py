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
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any

from agency_runtime.core.config import AgencyConfig, JudgeConfig, ProviderEntry, load_config
from agency_runtime.core.selector.candidate_narrow import pre_narrow

logger = logging.getLogger("agency_runtime.selector.judge")


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


def _build_judge_payload(
    task_description: str,
    candidates: list[dict[str, Any]],
    max_sel: int,
    ollama_mode: bool,
) -> tuple[bytes, str, str]:
    """Build the HTTP request payload and return (body, url_path, content_type)."""
    judge_candidates = candidates[:20]
    catalog_lines = []
    for agent in judge_candidates:
        slug = agent.get("slug", "")
        desc = agent.get("description", "")[:80]
        catalog_lines.append(f"  {slug}: {desc}")
    catalog_str = "\n".join(catalog_lines)

    user_content = (
        f"Task: {task_description}\n\n"
        f"Select 1-{max_sel} specialists from these {len(judge_candidates)} "
        f"candidates. Return JSON only.\n\n"
        f"Candidates:\n{catalog_str}\n\n"
        f'Return: {{"selected_ids": ["id1"], "confidence": 0.9}}'
    )

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


def _try_provider(
    provider: ProviderEntry,
    task_description: str,
    candidates: list[dict[str, Any]],
    max_sel: int,
    candidate_count: int,
    top_score: float,
) -> dict[str, Any] | None:
    """Try a single provider. Returns result dict on success, None on failure."""

    api_key = provider.resolve_api_key()

    # Auth check
    if provider.type != "ollama" and not api_key:
        logger.debug("provider %s: no api key, skipping", provider.name)
        return None

    body, path, content_type = _build_judge_payload(
        task_description, candidates, max_sel, provider.ollama_mode,
    )
    body_json = json.loads(body)
    body_json["model"] = provider.model
    body = json.dumps(body_json).encode("utf-8")

    request_url = f"{provider.base_url.rstrip('/')}{path}"
    headers = {"Content-Type": content_type}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(request_url, data=body, headers=headers, method="POST")
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=provider.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        logger.debug("provider %s failed: %s", provider.name, exc)
        return None

    elapsed = time.monotonic() - t0

    content = ""
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        content = data.get("message", {}).get("content", "") if provider.ollama_mode else str(data)

    parsed = parse_json_response(content)
    if parsed is None:
        # Parse failed — return token fallback with this provider's name
        fallback_ids = [a.get("slug", "") for a in candidates[:max_sel]]
        if fallback_ids:
            return {
                "selected_ids": fallback_ids,
                "confidence": 0.3,
                "latency_ms": int(elapsed * 1000),
                "status": "token_fallback",
                "provider": f"{provider.name} (parse failed)",
                "candidate_count": candidate_count,
                "top_score": top_score,
            }
        return None

    selected = parsed.get("selected_ids") or parsed.get("selected") or []
    if not isinstance(selected, list):
        return None

    known_ids = {a.get("slug", "") for a in candidates}
    valid_selected = [sid for sid in selected if str(sid) in known_ids]

    if not valid_selected:
        valid_selected = [a.get("slug", "") for a in candidates[:max_sel]]
        status = "token_fallback"
    else:
        status = "applied"

    try:
        confidence = float(parsed.get("confidence", 0))
    except (TypeError, ValueError):
        confidence = 0.0

    return {
        "selected_ids": valid_selected[:max_sel],
        "confidence": confidence,
        "latency_ms": int(elapsed * 1000),
        "status": status,
        "provider": f"{provider.name} ({provider.type})",
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
) -> dict[str, Any] | None:
    """Try the legacy judge config (backward compat). Returns result or None."""

    api_key = jc.resolve_api_key()
    if not jc.model:
        return None

    ollama_mode = jc.ollama_mode
    body, path, content_type = _build_judge_payload(
        task_description, candidates, max_sel, ollama_mode
    )
    body_json = json.loads(body)
    body_json["model"] = jc.model
    body = json.dumps(body_json).encode("utf-8")

    request_url = f"{jc.base_url.rstrip('/')}{path}"
    headers = {"Content-Type": content_type}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    req = urllib.request.Request(request_url, data=body, headers=headers, method="POST")
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=jc.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        logger.debug("legacy judge failed: %s", exc)
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
        fallback_ids = [a.get("slug", "") for a in candidates[:max_sel]]
        if fallback_ids:
            result["selected_ids"] = fallback_ids
            result["confidence"] = 0.3
            result["status"] = "token_fallback"
            result["candidate_count"] = candidate_count
            result["top_score"] = top_score
            return result
        result["status"] = "parse_failed"
        result["error"] = f"could not parse JSON from response: {content[:200]}"
        return result

    selected = parsed.get("selected_ids") or parsed.get("selected") or []
    if not isinstance(selected, list):
        result["status"] = "invalid_format"
        result["error"] = "selected_ids is not a list"
        return result

    known_ids = {a.get("slug", "") for a in candidates}
    valid_selected = [sid for sid in selected if str(sid) in known_ids]

    if not valid_selected:
        valid_selected = [a.get("slug", "") for a in candidates[:max_sel]]
        if not valid_selected:
            result["status"] = "no_valid_matches"
            result["error"] = f"selected_ids {selected} not in catalog"
            return result
        result["status"] = "token_fallback"

    try:
        confidence = float(parsed.get("confidence", 0))
    except (TypeError, ValueError):
        confidence = 0.0

    result["selected_ids"] = valid_selected[:max_sel]
    result["confidence"] = confidence
    result["candidate_count"] = candidate_count
    result["top_score"] = top_score
    if result["status"] not in ("token_fallback",):
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
    1. Each provider in cfg.providers (user-configured priority list)
    2. Legacy judge config (cfg.judge — backward compat)
    3. Ollama fallback (cfg.ollama)
    4. Token-only (no LLM needed)
    """
    cfg = config or load_config()
    jc = judge_config or cfg.judge
    max_sel = max_selected or jc.max_selected

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
    for provider in cfg.providers:
        res = _try_provider(
            provider, task_description, candidates, max_sel,
            candidate_count, top_score,
        )
        if res is not None:
            return res
        logger.debug("provider %s failed, trying next", provider.name)

    # Layer 2: Legacy judge config (backward compat for existing configs)
    legacy_result = _try_legacy_judge(
        jc, task_description, candidates, max_sel,
        candidate_count, top_score,
    )
    if legacy_result is not None:
        return legacy_result

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
        ollama_result = _try_provider(
            ollama_provider, task_description, candidates, max_sel,
            candidate_count, top_score,
        )
        if ollama_result is not None:
            return ollama_result

    # Layer 4: Token-only (no LLM)
    return _token_only_fallback(candidates, candidate_count, top_score, max_sel)


def _token_only_fallback(
    candidates: list[dict[str, Any]],
    candidate_count: int,
    top_score: float,
    max_sel: int,
) -> dict[str, Any]:
    """Last resort: return top token-scored candidates without an LLM call."""
    result: dict[str, Any] = {
        "selected_ids": [a.get("slug", "") for a in candidates[:max_sel]],
        "confidence": 0.3,
        "latency_ms": 0,
        "status": "token_fallback",
        "error": "",
        "candidate_count": candidate_count,
        "top_score": top_score,
    }
    return result
