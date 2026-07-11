"""Optional LiteLLM callback and proxy bridge.

The package deliberately does not depend on LiteLLM.  When LiteLLM is
installed this module subclasses its ``CustomLogger`` contract; otherwise it
remains importable and the programmatic registration helper returns a safe,
explicit no-op result.

Only bounded operational metadata is persisted by default.  Request content is
used in memory for routing, but is written only when Agency Runtime's explicit
content-capture setting is enabled, and even then common credentials and PII are
redacted first.
"""

from __future__ import annotations

import asyncio
import importlib
import logging
import re
import threading
import uuid
import weakref
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from types import ModuleType
from typing import Any, Mapping, MutableMapping, Sequence
from urllib.parse import urlsplit, urlunsplit
import urllib.request

from agency_runtime.adapters.base import BaseAdapter
from agency_runtime.core.config import AgencyConfig, load_config
from agency_runtime.core.store.sqlite import Store

logger = logging.getLogger("agency_runtime.adapters.litellm")

try:  # LiteLLM is an optional integration, never a package requirement.
    from litellm.integrations.custom_logger import CustomLogger as _CustomLogger
except ImportError:  # pragma: no cover - the fallback is exercised indirectly
    class _CustomLogger:  # type: ignore[no-redef]
        """Small compatibility base used when LiteLLM is not installed."""

        def __init__(self, **_: Any) -> None:
            pass


_PROXY_CALLBACK_PATH = "agency_runtime.adapters.litellm.callback.proxy_handler_instance"
_MAX_DEDUPE_EVENTS = 4096
_MAX_ROUTE_CONTEXTS = 1024
_registration_lock = threading.RLock()

_BEARER_RE = re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._~+/=-]{8,}")
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(api[_-]?key|token|password|passwd|secret)\s*([:=])\s*([^\s,;]{4,})"
)
_KEY_RE = re.compile(r"\b(?:sk|rk|pk)-[A-Za-z0-9_-]{8,}\b")
_EMAIL_RE = re.compile(r"(?<![\w.+-])[\w.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![\w.-])")


def litellm_health_check(base_url: str | None = None, config: AgencyConfig | None = None) -> bool:
    """Return whether the configured LiteLLM gateway liveness URL responds."""
    cfg = config or load_config()
    url = (base_url or cfg.adapters.litellm.base_url).rstrip("/")
    try:
        req = urllib.request.Request(f"{url}/health/liveness")
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def _clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _bounded(value: Any, limit: int) -> str:
    return _clean(value)[:limit]


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _first(*values: Any) -> str:
    for value in values:
        cleaned = _clean(value)
        if cleaned:
            return cleaned
    return ""


def _metadata(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    direct = _mapping(payload.get("metadata"))
    params = _mapping(payload.get("litellm_params"))
    nested = _mapping(params.get("metadata"))
    return {**direct, **nested}


def _trace_id(payload: Mapping[str, Any], response_obj: Any = None) -> str:
    metadata = _metadata(payload)
    params = _mapping(payload.get("litellm_params"))
    response_id = _response_value(response_obj, "id")
    return _first(
        metadata.get("agency_trace_id"),
        metadata.get("trace_id"),
        payload.get("litellm_call_id"),
        params.get("litellm_call_id"),
        payload.get("litellm_trace_id"),
        params.get("litellm_trace_id"),
        response_id,
    )


def _session_id(payload: Mapping[str, Any], trace_id: str) -> str:
    metadata = _metadata(payload)
    return _first(
        metadata.get("agency_session_id"),
        metadata.get("session_id"),
        payload.get("session_id"),
        trace_id,
    )


def _response_value(response_obj: Any, key: str) -> Any:
    if isinstance(response_obj, Mapping):
        return response_obj.get(key)
    return getattr(response_obj, key, None)


def _hidden_params(response_obj: Any) -> Mapping[str, Any]:
    hidden = _response_value(response_obj, "_hidden_params")
    return _mapping(hidden)


def _known_headers(response_obj: Any) -> dict[str, str]:
    """Extract only receipt headers; never copy arbitrary auth headers."""
    from agency_runtime.core.receipts.litellm import (
        LITELLM_ATTEMPTED_FALLBACKS_HEADER,
        LITELLM_MODEL_API_BASE_HEADER,
        LITELLM_MODEL_GROUP_HEADER,
        LITELLM_MODEL_ID_HEADER,
    )

    wanted = {
        LITELLM_MODEL_GROUP_HEADER,
        LITELLM_MODEL_API_BASE_HEADER,
        LITELLM_ATTEMPTED_FALLBACKS_HEADER,
        LITELLM_MODEL_ID_HEADER,
    }
    hidden = _hidden_params(response_obj)
    candidates: list[Any] = [hidden.get("additional_headers")]
    raw_response = _response_value(response_obj, "_response")
    if raw_response is not None:
        candidates.append(getattr(raw_response, "headers", None))

    extracted: dict[str, str] = {}
    for candidate in candidates:
        if not isinstance(candidate, Mapping) and not hasattr(candidate, "items"):
            continue
        for key, value in candidate.items():
            normalized = _clean(key).lower()
            if normalized in wanted and value is not None:
                extracted[normalized] = _clean(value)

    # Some LiteLLM versions expose the same routing values directly.
    direct = {
        LITELLM_MODEL_GROUP_HEADER: hidden.get("model_group"),
        LITELLM_MODEL_API_BASE_HEADER: hidden.get("api_base"),
        LITELLM_MODEL_ID_HEADER: hidden.get("model_id"),
        LITELLM_ATTEMPTED_FALLBACKS_HEADER: hidden.get("attempted_fallbacks"),
    }
    for key, value in direct.items():
        if key not in extracted and value not in (None, ""):
            extracted[key] = _clean(value)
    return extracted


def _sanitize_api_base(value: Any) -> str:
    """Remove credentials, query strings, and fragments from endpoint metadata."""
    text = _clean(value)
    if not text:
        return ""
    try:
        parts = urlsplit(text)
    except ValueError:
        return ""
    if not parts.scheme or not parts.hostname:
        # Do not persist malformed strings that may contain a credential.
        return ""
    host = parts.hostname
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    try:
        port = parts.port
    except ValueError:
        return ""
    netloc = f"{host}:{port}" if port is not None else host
    return urlunsplit((parts.scheme.lower(), netloc, parts.path.rstrip("/"), "", ""))


def _provider_model(model: Any) -> tuple[str, str]:
    value = _clean(model)
    if not value or value.lower().startswith("custom/"):
        return "", ""
    if "/" not in value:
        return "", value
    provider, resolved = value.split("/", 1)
    if not provider or not resolved or provider.lower() == "custom":
        return "", ""
    return provider, resolved


def _iso_time(value: Any) -> str:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()
    text = _clean(value)
    if text:
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc).isoformat()
        except ValueError:
            pass
    return datetime.now(timezone.utc).isoformat()


def _redact_content(value: str) -> str:
    """Return a bounded, defensively redacted content excerpt."""
    text = _BEARER_RE.sub(r"\1 [REDACTED]", value)
    text = _SECRET_ASSIGNMENT_RE.sub(r"\1\2[REDACTED]", text)
    text = _KEY_RE.sub("[REDACTED_KEY]", text)
    text = _EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    return text[:2000]


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, Sequence) or isinstance(content, (bytes, bytearray)):
        return ""
    parts: list[str] = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, Mapping) and _clean(block.get("type")).lower() in {
            "text",
            "input_text",
        }:
            parts.append(_clean(block.get("text") or block.get("content")))
    return "\n".join(part for part in parts if part)


def _last_user_message(messages: Any) -> str:
    if not isinstance(messages, Sequence) or isinstance(messages, (str, bytes, bytearray)):
        return ""
    for message in reversed(messages):
        if not isinstance(message, Mapping):
            continue
        if _clean(message.get("role")).lower() == "user":
            return _content_text(message.get("content"))
    return ""


def _has_agency_context(messages: Sequence[Any]) -> bool:
    return any(
        isinstance(message, Mapping)
        and "[AGENCY PREFLIGHT]" in _content_text(message.get("content"))
        for message in messages
    )


def _inject_context(messages: Any, context: str) -> list[Any]:
    copied = list(messages) if isinstance(messages, Sequence) and not isinstance(messages, (str, bytes, bytearray)) else []
    if not context or _has_agency_context(copied):
        return copied
    position = 0
    while position < len(copied):
        message = copied[position]
        if not isinstance(message, Mapping) or _clean(message.get("role")).lower() != "system":
            break
        position += 1
    copied.insert(position, {"role": "system", "content": context})
    return copied


def _inject_proxy_context(
    payload: MutableMapping[str, Any],
    messages: Any,
    context: str,
    call_type: str,
) -> None:
    """Inject context without violating Anthropic Messages' system shape."""
    if _clean(call_type).lower() != "anthropic_messages":
        payload["messages"] = _inject_context(messages, context)
        return

    system = payload.get("system")
    if isinstance(system, str):
        if "[AGENCY PREFLIGHT]" not in system:
            payload["system"] = f"{system}\n\n{context}" if system else context
        return
    if isinstance(system, Sequence) and not isinstance(system, (str, bytes, bytearray)):
        blocks = list(system)
        if not any(
            isinstance(block, Mapping)
            and "[AGENCY PREFLIGHT]" in _content_text([block])
            for block in blocks
        ):
            blocks.append({"type": "text", "text": context})
        payload["system"] = blocks
        return
    payload["system"] = context


class LiteLLMAdapter(BaseAdapter):
    """Agency Runtime behavior used by the LiteLLM callback."""

    host_name = "litellm"

    def __init__(
        self,
        store: Store | None = None,
        base_url: str | None = None,
        config: AgencyConfig | None = None,
    ):
        super().__init__(store)
        self._config = config or load_config()
        self._enabled = self._config.adapters.litellm.enabled != "false"
        self.base_url = base_url or self._config.adapters.litellm.base_url

    def is_available(self) -> bool:
        enabled = self._config.adapters.litellm.enabled
        if enabled == "false":
            return False
        if enabled == "true":
            return True
        return litellm_health_check(self.base_url, self._config)

    def report_skills_loaded(self, session_id: str) -> list[str]:
        return self.store.get_skills_for_session(session_id)

    def report_specialists_loaded(self, session_id: str) -> list[str]:
        return self.store.get_specialists_for_session(session_id)

    def get_delegate_backend(self) -> str | None:
        return None

    def expose_model_telemetry(self, session_id: str) -> dict[str, Any]:
        receipt = self.store.get_model_receipt_for_session(session_id)
        return receipt or {}

    def extract_receipt_from_headers(
        self, headers: dict[str, str], requested_model: str, trace_id: str = "",
    ) -> dict[str, Any]:
        """Normalize LiteLLM's response routing headers."""
        from agency_runtime.core.receipts.normalize import normalize_litellm_receipt

        receipt = normalize_litellm_receipt(headers, requested_model)
        if trace_id:
            receipt["trace_id"] = trace_id
        receipt["host"] = self.host_name
        receipt["api_base"] = _sanitize_api_base(receipt.get("api_base"))
        return receipt

    def pre_call_handler(
        self,
        session_id: str,
        user_message: str,
        model: str,
        messages: list[dict] | None = None,
        trace_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Run selector preflight and return context for one LiteLLM request."""
        del messages
        from agency_runtime.core.selector.pipeline import is_trivial, route_and_build_context

        skip_models = self._config.adapters.litellm.skip_models
        if any(pattern.lower() in model.lower() for pattern in skip_models):
            return None
        if is_trivial(user_message, self._config):
            return None

        catalog = self.store.get_active_roster_as_catalog()
        context = route_and_build_context(
            session_id,
            user_message,
            catalog,
            config=self._config,
            store=self.store,
            trace_id=trace_id,
        )
        return {"context": context} if context else None


@dataclass(frozen=True, slots=True)
class LiteLLMRegistration:
    """Outcome from process-local LiteLLM callback registration."""

    available: bool
    registered: bool
    already_registered: bool = False
    reason: str = ""
    callback: "AgencyLiteLLMCallback | None" = None


class AgencyLiteLLMCallback(_CustomLogger):
    """LiteLLM ``CustomLogger`` callback with truthful local evidence.

    Instances are thread-safe.  Every process gets its own bounded dedupe cache;
    SQLite's WAL/busy-timeout behavior provides multi-process write safety.
    """

    _agency_runtime_callback = True

    def __init__(
        self,
        *,
        store: Store | None = None,
        config: AgencyConfig | None = None,
    ) -> None:
        self._config = config or load_config()
        self._enabled = self._config.adapters.litellm.enabled != "false"
        self._store = store
        self._adapter: LiteLLMAdapter | None = None
        self._lock = threading.RLock()
        self._recorded_events: OrderedDict[str, None] = OrderedDict()
        self._route_contexts: OrderedDict[str, str] = OrderedDict()
        self._route_locks: weakref.WeakValueDictionary[str, threading.Lock] = weakref.WeakValueDictionary()
        try:
            # Redacted opt-in capture is implemented by this callback.  Never
            # ask LiteLLM's generic logger to retain raw request/response data.
            super().__init__(turn_off_message_logging=True)
        except TypeError:  # compatibility with older LiteLLM CustomLogger versions
            super().__init__()

    @property
    def adapter(self) -> LiteLLMAdapter:
        with self._lock:
            if self._adapter is None:
                self._adapter = LiteLLMAdapter(store=self._store, config=self._config)
            return self._adapter

    def _claim(self, event_key: str) -> bool:
        with self._lock:
            if event_key in self._recorded_events:
                self._recorded_events.move_to_end(event_key)
                return False
            self._recorded_events[event_key] = None
            while len(self._recorded_events) > _MAX_DEDUPE_EVENTS:
                self._recorded_events.popitem(last=False)
            return True

    def _unclaim(self, event_key: str) -> None:
        with self._lock:
            self._recorded_events.pop(event_key, None)

    def _event_key(
        self,
        payload: Mapping[str, Any],
        response_obj: Any,
        start_time: Any,
        status: str,
    ) -> tuple[str, str]:
        trace_id = _trace_id(payload, response_obj)
        if not trace_id:
            trace_id = str(uuid.uuid4())
        identity = _first(_response_value(response_obj, "id"), _iso_time(start_time), id(response_obj))
        return trace_id, f"{status}:{trace_id}:{identity}"

    def _record_receipt(
        self,
        payload: Mapping[str, Any],
        response_obj: Any,
        start_time: Any,
        end_time: Any,
        *,
        status: str,
    ) -> None:
        if not self._enabled:
            return
        trace_id, event_key = self._event_key(payload, response_obj, start_time, status)
        if not self._claim(event_key):
            return
        try:
            requested_model = _bounded(payload.get("model"), 256)
            trace_id = _bounded(trace_id, 256)
            session_id = _bounded(_session_id(payload, trace_id), 256)
            headers = _known_headers(response_obj)
            receipt = self.adapter.extract_receipt_from_headers(headers, requested_model, trace_id)
            params = _mapping(payload.get("litellm_params"))
            hidden = _hidden_params(response_obj)
            actual_provider, actual_model = _provider_model(_response_value(response_obj, "model"))
            explicit_provider = _bounded(_first(
                params.get("custom_llm_provider"),
                payload.get("custom_llm_provider"),
                actual_provider,
                receipt.get("resolved_provider"),
            ), 128)
            api_base = _sanitize_api_base(
                _first(hidden.get("api_base"), params.get("api_base"), receipt.get("api_base"))
            )
            previous_models = payload.get("previous_models")
            attempted_fallbacks = receipt.get("attempted_fallbacks", 0)
            if not attempted_fallbacks and isinstance(previous_models, Sequence) and not isinstance(previous_models, str):
                attempted_fallbacks = len(previous_models)

            if status != "success":
                # A selected deployment is not proof that a failed call ran.
                actual_model = ""
            resolved_model = actual_model or (
                _clean(receipt.get("resolved_model")) if status == "success" else ""
            )
            if not resolved_model:
                resolved_model = "unavailable"

            self.adapter.store.record_model_receipt(
                trace_id=trace_id,
                session_id=session_id,
                host=self.adapter.host_name,
                requested_model=requested_model,
                model_group=_bounded(_first(receipt.get("model_group"), requested_model), 256),
                resolved_provider=explicit_provider,
                resolved_model=_bounded(resolved_model, 256),
                api_base=_bounded(api_base, 1024),
                attempted_fallbacks=int(attempted_fallbacks or 0),
                model_id=_bounded(_first(receipt.get("model_id"), hidden.get("model_id")), 512),
                source="litellm",
                started_at=_iso_time(start_time),
                ended_at=_iso_time(end_time),
                status=status,
            )
            # Routing context can contain task excerpts for injection.  Keep it
            # only until the terminal callback for this request has persisted.
            with self._lock:
                self._route_contexts.pop(trace_id, None)
        except Exception as exc:  # callbacks must never break model traffic
            self._unclaim(event_key)
            logger.warning("LiteLLM evidence callback failed: %s", type(exc).__name__)

    def _routing_context(
        self,
        *,
        model: str,
        messages: Any,
        payload: MutableMapping[str, Any],
    ) -> str:
        if not self._enabled:
            return ""
        user_message = _last_user_message(messages)
        if not user_message:
            return ""

        trace_id = _trace_id(payload)
        if not trace_id:
            trace_id = str(uuid.uuid4())
            metadata = dict(_metadata(payload))
            metadata["agency_trace_id"] = trace_id
            payload["metadata"] = metadata
        trace_id = _bounded(trace_id, 256)
        session_id = _bounded(_session_id(payload, trace_id), 256)

        with self._lock:
            route_lock = self._route_locks.setdefault(trace_id, threading.Lock())

        with route_lock:
            with self._lock:
                cached = self._route_contexts.get(trace_id)
                if cached is not None:
                    self._route_contexts.move_to_end(trace_id)
                    return cached

            # Establish the shared trace parent.  Passing an empty string when
            # capture is disabled prevents a differently loaded global config
            # from accidentally persisting content.
            captured = _redact_content(user_message) if self._config.observability.capture_content else ""
            self.adapter.store.create_run(
                trace_id=_bounded(trace_id, 256),
                session_id=_bounded(session_id, 256),
                host=self.adapter.host_name,
                user_message=captured,
                metadata={
                    "callback": "agency-runtime-litellm",
                    "content_capture": bool(captured),
                },
            )
            result = self.adapter.pre_call_handler(
                session_id,
                user_message,
                model,
                messages=list(messages) if isinstance(messages, Sequence) else None,
                trace_id=trace_id,
            )
            context = _clean((result or {}).get("context"))
            with self._lock:
                self._route_contexts[trace_id] = context
                while len(self._route_contexts) > _MAX_ROUTE_CONTEXTS:
                    self._route_contexts.popitem(last=False)
            return context

    # LiteLLM SDK logging hook.  It cannot reliably modify request arguments,
    # but it still records the authoritative routing decision for sync calls.
    def log_pre_api_call(self, model: str, messages: list[Any], kwargs: dict[str, Any]) -> None:
        try:
            self._routing_context(model=model, messages=messages, payload=kwargs)
        except Exception as exc:
            logger.warning("LiteLLM pre-call routing failed: %s", type(exc).__name__)

    async def async_log_pre_api_call(self, model: str, messages: list[Any], kwargs: dict[str, Any]) -> None:
        await asyncio.to_thread(self.log_pre_api_call, model, messages, kwargs)

    async def async_pre_request_hook(
        self,
        model: str,
        messages: list[Any],
        kwargs: dict[str, Any],
    ) -> dict[str, Any]:
        """Inject routing context for LiteLLM SDK async requests."""
        try:
            updated = dict(kwargs)
            context = await asyncio.to_thread(
                self._routing_context,
                model=model,
                messages=messages,
                payload=updated,
            )
            if context:
                updated["messages"] = _inject_context(messages, context)
            return updated
        except Exception as exc:
            logger.warning("LiteLLM request hook failed: %s", type(exc).__name__)
            return kwargs

    async def async_pre_call_hook(
        self,
        user_api_key_dict: Any,
        cache: Any,
        data: dict[str, Any],
        call_type: str,
    ) -> dict[str, Any]:
        """Inject routing context in LiteLLM Proxy chat/message requests."""
        del user_api_key_dict, cache
        try:
            if _clean(call_type).lower() not in {
                "completion",
                "chat_completion",
                "responses",
                "anthropic_messages",
            }:
                return data
            updated = dict(data)
            messages = updated.get("messages")
            context = await asyncio.to_thread(
                self._routing_context,
                model=_clean(updated.get("model")),
                messages=messages,
                payload=updated,
            )
            if context:
                _inject_proxy_context(updated, messages, context, call_type)
            return updated
        except Exception as exc:
            logger.warning("LiteLLM proxy hook failed: %s", type(exc).__name__)
            return data

    def log_success_event(self, kwargs: dict[str, Any], response_obj: Any, start_time: Any, end_time: Any) -> None:
        self._record_receipt(kwargs, response_obj, start_time, end_time, status="success")

    def log_failure_event(self, kwargs: dict[str, Any], response_obj: Any, start_time: Any, end_time: Any) -> None:
        self._record_receipt(kwargs, response_obj, start_time, end_time, status="failed")

    async def async_log_success_event(
        self, kwargs: dict[str, Any], response_obj: Any, start_time: Any, end_time: Any,
    ) -> None:
        await asyncio.to_thread(self.log_success_event, kwargs, response_obj, start_time, end_time)

    async def async_log_failure_event(
        self, kwargs: dict[str, Any], response_obj: Any, start_time: Any, end_time: Any,
    ) -> None:
        await asyncio.to_thread(self.log_failure_event, kwargs, response_obj, start_time, end_time)


def register_litellm_callback(
    *,
    litellm_module: ModuleType | Any | None = None,
    store: Store | None = None,
    config: AgencyConfig | None = None,
) -> LiteLLMRegistration:
    """Append one callback to LiteLLM's process-local callback registry.

    Existing callbacks are preserved.  The operation is idempotent and safe to
    call concurrently.  Multi-worker applications must invoke it in each worker
    process, or use :func:`litellm_proxy_callback_config`.
    """
    cfg = config or load_config()
    if cfg.adapters.litellm.enabled == "false":
        return LiteLLMRegistration(False, False, reason="disabled by Agency Runtime config")
    if litellm_module is None:
        try:
            litellm_module = importlib.import_module("litellm")
        except ImportError:
            return LiteLLMRegistration(False, False, reason="LiteLLM is not installed")

    with _registration_lock:
        existing = getattr(litellm_module, "callbacks", None)
        if existing is None:
            callbacks: list[Any] = []
        elif isinstance(existing, (list, tuple)):
            callbacks = list(existing)
        else:
            callbacks = [existing]
        for callback in callbacks:
            if getattr(callback, "_agency_runtime_callback", False):
                return LiteLLMRegistration(
                    True,
                    True,
                    already_registered=True,
                    callback=callback,
                )

        callback = AgencyLiteLLMCallback(store=store, config=cfg)
        callbacks.append(callback)
        try:
            litellm_module.callbacks = callbacks
        except Exception as exc:
            return LiteLLMRegistration(
                True,
                False,
                reason=f"callback registry rejected assignment: {type(exc).__name__}",
            )
        return LiteLLMRegistration(True, True, callback=callback)


def litellm_proxy_callback_config(config: AgencyConfig | None = None) -> dict[str, Any]:
    """Return a mergeable LiteLLM Proxy config fragment.

    The callback import path activates once in every proxy worker.  LiteLLM's
    own message logging is disabled unless content capture was explicitly
    enabled in Agency Runtime too.
    """
    cfg = config or load_config()
    settings: dict[str, Any] = {"turn_off_message_logging": True}
    if cfg.adapters.litellm.enabled != "false":
        settings["callbacks"] = _PROXY_CALLBACK_PATH
    return {
        "litellm_settings": settings,
    }


# LiteLLM Proxy imports this dotted object from ``litellm_settings.callbacks``.
# Lazy store creation keeps ordinary imports side-effect free.
proxy_handler_instance = AgencyLiteLLMCallback()


__all__ = [
    "AgencyLiteLLMCallback",
    "LiteLLMAdapter",
    "LiteLLMRegistration",
    "litellm_health_check",
    "litellm_proxy_callback_config",
    "proxy_handler_instance",
    "register_litellm_callback",
]
