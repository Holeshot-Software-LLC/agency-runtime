"""Bounded request and response protocol helpers for the semantic judge."""

from __future__ import annotations

import json
import re
import urllib.request
from typing import Any


def _facade():
    """Resolve judge dependencies at call time for monkeypatch compatibility."""

    from agency_runtime.core.selector import judge

    return judge


def read_json_object(response: Any) -> dict[str, Any] | None:
    """Read one bounded JSON object from an HTTP response."""
    facade = _facade()
    limit = facade._MAX_JUDGE_RESPONSE_BYTES
    try:
        raw = response.read(limit + 1)
        if len(raw) > limit:
            return None
        parsed = facade.safe_load_bounded_json(
            raw,
            maximum_bytes=limit,
            maximum_depth=32,
            maximum_nodes=10_000,
        )
    except (OSError, UnicodeError, ValueError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def parse_json_response(text: str) -> dict[str, Any] | None:
    """Parse one bounded JSON object from a model response."""
    facade = _facade()
    limit = facade._MAX_JUDGE_RESPONSE_BYTES
    if not isinstance(text, str) or len(text) > limit:
        return None
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    try:
        parsed = facade.safe_load_bounded_json(
            text,
            maximum_bytes=limit,
            maximum_depth=32,
            maximum_nodes=10_000,
        )
        if isinstance(parsed, dict):
            return parsed
    except (TypeError, ValueError):
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = facade.safe_load_bounded_json(
                text[start : end + 1],
                maximum_bytes=limit,
                maximum_depth=32,
                maximum_nodes=10_000,
            )
            if isinstance(parsed, dict):
                return parsed
        except (TypeError, ValueError):
            pass
    return None


def build_judge_prompt(
    task_description: str,
    candidates: list[dict[str, Any]],
    max_sel: int,
) -> str:
    """Build the bounded semantic-selection prompt shared by all transports."""
    facade = _facade()
    prompted = facade._judge_candidates(candidates)
    catalog_lines = []
    for agent in prompted:
        slug = facade._agent_id(agent)
        description = agent.get("description", "")[:80]
        catalog_lines.append(f"  {slug}: {description}")
    catalog_text = "\n".join(catalog_lines)
    # This is a bounded model prompt, not a database statement.
    return (
        f"Task: {task_description}\n\n"  # nosec B608
        f"Select 1-{max_sel} specialists from these {len(prompted)} "
        "candidates. Ignore work the task explicitly negates or excludes. "
        f"Return JSON only.\n\n"
        f"Candidates:\n{catalog_text}\n\n"
        f'Return: {{"selected_ids": ["id1"], "confidence": 0.9}}'
    )


def response_content(
    data: dict[str, Any],
    *,
    provider_type: str,
    ollama_mode: bool,
) -> str:
    """Extract only the documented text field from a provider response."""
    if ollama_mode:
        message = data.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        return content if isinstance(content, str) else ""

    if provider_type == "anthropic":
        blocks = data.get("content")
        if not isinstance(blocks, list):
            return ""
        return "".join(
            text
            for block in blocks
            if isinstance(block, dict)
            and block.get("type") == "text"
            and isinstance((text := block.get("text")), str)
        )

    choices = data.get("choices")
    first = choices[0] if isinstance(choices, list) and choices else None
    message = first.get("message") if isinstance(first, dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    return content if isinstance(content, str) else ""


def build_judge_payload(
    task_description: str,
    candidates: list[dict[str, Any]],
    max_sel: int,
    ollama_mode: bool,
    provider_type: str = "openai-compatible",
) -> tuple[bytes, str, str]:
    """Build the HTTP request payload and return body, path, and content type."""
    user_content = _facade()._build_judge_prompt(task_description, candidates, max_sel)

    if ollama_mode:
        payload = {
            "model": "",
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
        }
        return json.dumps(payload).encode("utf-8"), "/api/chat", "application/json"

    if provider_type == "anthropic":
        payload = {
            "model": "",
            "system": "You are a semantic selector. Return strict JSON only.",
            "messages": [{"role": "user", "content": user_content}],
            "max_tokens": 256,
            "temperature": 0.0,
        }
        return json.dumps(payload).encode("utf-8"), "/v1/messages", "application/json"

    payload = {
        "model": "",
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
    }
    return json.dumps(payload).encode("utf-8"), "/v1/chat/completions", "application/json"


def join_api_path(base_url: str, path: str) -> str:
    """Join API paths without producing duplicate ``/v1/v1`` segments."""
    base = base_url.rstrip("/")
    normalized_path = "/" + path.lstrip("/")
    if base.lower().endswith("/v1") and normalized_path.lower().startswith("/v1/"):
        normalized_path = normalized_path[3:]
    return f"{base}{normalized_path}"


def validated_decision(
    parsed: dict[str, Any] | None,
    candidates: list[dict[str, Any]],
    max_sel: int,
) -> tuple[list[str], float] | None:
    """Validate one provider decision against the exact prompted catalog."""
    if parsed is None:
        return None
    selected = parsed.get("selected_ids") or parsed.get("selected") or []
    if not isinstance(selected, list):
        return None
    facade = _facade()
    known_ids = {facade._agent_id(agent) for agent in candidates}
    valid_selected = list(dict.fromkeys(str(item) for item in selected if str(item) in known_ids))
    confidence = facade._bounded_confidence(parsed.get("confidence"))
    if not valid_selected or confidence is None:
        return None
    return valid_selected[:max_sel], confidence


def applied_result(
    decision: tuple[list[str], float],
    *,
    latency_ms: int,
    provider: str,
    candidate_count: int,
    top_score: float,
) -> dict[str, Any]:
    selected_ids, confidence = decision
    return {
        "selected_ids": selected_ids,
        "confidence": confidence,
        "latency_ms": latency_ms,
        "status": "applied",
        "provider": provider,
        "candidate_count": candidate_count,
        "top_score": top_score,
    }


def encoded_model_payload(
    body: bytes,
    *,
    model: str,
    use_completion_tokens: bool,
) -> bytes:
    body_json = json.loads(body)
    body_json["model"] = model
    if use_completion_tokens and model.lower().startswith("gpt-5"):
        body_json["max_completion_tokens"] = body_json.pop("max_tokens", 256)
        body_json.pop("temperature", None)
    return json.dumps(body_json).encode("utf-8")


def provider_headers(
    content_type: str,
    *,
    api_key: str,
    provider_type: str,
) -> dict[str, str]:
    headers = {"Content-Type": content_type}
    if not api_key:
        return headers
    if provider_type == "anthropic":
        headers["x-api-key"] = api_key
        headers["anthropic-version"] = "2023-06-01"
    else:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def build_http_request(
    *,
    task_description: str,
    candidates: list[dict[str, Any]],
    max_sel: int,
    base_url: str,
    model: str,
    ollama_mode: bool,
    provider_type: str,
    api_key: str,
    use_completion_tokens: bool,
) -> urllib.request.Request:
    facade = _facade()
    body, path, content_type = facade._build_judge_payload(
        task_description,
        candidates,
        max_sel,
        ollama_mode,
        provider_type,
    )
    encoded_body = facade._encoded_model_payload(
        body,
        model=model,
        use_completion_tokens=use_completion_tokens,
    )
    return urllib.request.Request(
        facade._join_api_path(base_url, path),
        data=encoded_body,
        headers=facade._provider_headers(
            content_type,
            api_key=api_key,
            provider_type=provider_type,
        ),
        method="POST",
    )


__all__ = [
    "applied_result",
    "build_http_request",
    "build_judge_payload",
    "build_judge_prompt",
    "encoded_model_payload",
    "join_api_path",
    "parse_json_response",
    "provider_headers",
    "read_json_object",
    "response_content",
    "validated_decision",
]
