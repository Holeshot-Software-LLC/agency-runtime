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
import threading
import urllib.request
import uuid
import weakref
from collections import OrderedDict
from collections.abc import Mapping, MutableMapping, Sequence
from dataclasses import dataclass
from types import ModuleType
from typing import Any

from agency_runtime.adapters.base import BaseAdapter
from agency_runtime.core.config import AgencyConfig, is_safe_credential_url, load_config
from agency_runtime.core.http_safety import open_no_redirect
from agency_runtime.core.store.sqlite import Store

from .evidence import (
    bounded,
    bounded_count,
    clean,
    event_identity,
    first,
    hidden_params,
    iso_time,
    known_headers,
    mapping,
    metadata,
    provider_model,
    response_value,
    sanitize_api_base,
    session_id,
    trace_id,
)
from .request_context import (
    inject_message_context,
    inject_proxy_context,
    proxy_request_input,
    redact_content,
    user_message,
)

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
_MAX_ROUTE_CONTEXT_CHARS = 16_384
_registration_lock = threading.RLock()


def litellm_health_check(base_url: str | None = None, config: AgencyConfig | None = None) -> bool:
    """Return whether the configured LiteLLM gateway liveness URL responds."""
    cfg = config or load_config()
    url = (base_url or cfg.adapters.litellm.base_url).rstrip("/")
    if not is_safe_credential_url(url):
        return False
    try:
        req = urllib.request.Request(f"{url}/health/liveness", method="GET")
        with open_no_redirect(req, timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def _model_is_skipped(model: str, patterns: Sequence[str]) -> bool:
    """Match configured model prefixes without letting an empty item match all."""

    normalized = clean(model).casefold()
    candidates = (normalized, normalized.split("/", 1)[-1])
    return any(
        candidate.startswith(prefix)
        for raw_pattern in patterns
        if (prefix := clean(raw_pattern).casefold())
        for candidate in candidates
    )


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
        self,
        headers: dict[str, str],
        requested_model: str,
        trace_id: str = "",
    ) -> dict[str, Any]:
        """Normalize LiteLLM's response routing headers."""
        from agency_runtime.core.receipts.normalize import normalize_litellm_receipt

        receipt = normalize_litellm_receipt(headers, requested_model)
        if trace_id:
            receipt["trace_id"] = trace_id
        receipt["host"] = self.host_name
        receipt["api_base"] = sanitize_api_base(receipt.get("api_base"))
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
        from agency_runtime.core.selector.pipeline import (
            is_trivial,
            route_and_build_context,
        )

        if _model_is_skipped(model, self._config.adapters.litellm.skip_models):
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
    callback: AgencyLiteLLMCallback | None = None


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
        self._route_locks: weakref.WeakValueDictionary[str, threading.Lock] = (
            weakref.WeakValueDictionary()
        )
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
        request_trace_id = trace_id(payload, response_obj) or str(uuid.uuid4())
        identity = event_identity(response_obj, start_time)
        return (
            request_trace_id,
            f"{bounded(status, 16)}:{request_trace_id}:{identity}",
        )

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
            requested_model = bounded(payload.get("model"), 256)
            request_session_id = session_id(payload, trace_id)
            headers = known_headers(response_obj)
            receipt = self.adapter.extract_receipt_from_headers(headers, requested_model, trace_id)
            params = mapping(payload.get("litellm_params"))
            hidden = hidden_params(response_obj)
            actual_provider, actual_model = provider_model(response_value(response_obj, "model"))
            resolved_provider = bounded(
                first(
                    actual_provider,
                    receipt.get("resolved_provider"),
                    params.get("custom_llm_provider"),
                    payload.get("custom_llm_provider"),
                ),
                128,
            )
            api_base = sanitize_api_base(
                first(
                    hidden.get("api_base"),
                    params.get("api_base"),
                    receipt.get("api_base"),
                )
            )
            previous_models = payload.get("previous_models")
            attempted_fallbacks = bounded_count(receipt.get("attempted_fallbacks", 0))
            if (
                not attempted_fallbacks
                and isinstance(previous_models, Sequence)
                and not isinstance(previous_models, (str, bytes, bytearray))
            ):
                attempted_fallbacks = len(previous_models)

            if status != "success":
                # A selected deployment is not proof that a failed call ran.
                actual_model = ""
                resolved_provider = ""
            resolved_model = actual_model or (
                clean(receipt.get("resolved_model")) if status == "success" else ""
            )
            if not resolved_model:
                resolved_model = "unavailable"

            self.adapter.store.record_model_receipt(
                trace_id=trace_id,
                session_id=request_session_id,
                host=self.adapter.host_name,
                requested_model=requested_model,
                model_group=bounded(
                    first(receipt.get("model_group"), requested_model),
                    256,
                ),
                resolved_provider=resolved_provider,
                resolved_model=bounded(resolved_model, 256),
                api_base=bounded(api_base, 1024),
                attempted_fallbacks=bounded_count(attempted_fallbacks),
                model_id=bounded(
                    first(receipt.get("model_id"), hidden.get("model_id")),
                    512,
                ),
                source="litellm",
                started_at=iso_time(start_time),
                ended_at=iso_time(end_time),
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
        request_message = user_message(messages)
        if not request_message:
            return ""

        request_trace_id = trace_id(payload)
        if not request_trace_id:
            request_trace_id = str(uuid.uuid4())
            request_metadata = dict(metadata(payload))
            request_metadata["agency_trace_id"] = request_trace_id
            payload["metadata"] = request_metadata
        request_session_id = session_id(payload, request_trace_id)

        with self._lock:
            route_lock = self._route_locks.setdefault(
                request_trace_id,
                threading.Lock(),
            )

        with route_lock:
            with self._lock:
                cached = self._route_contexts.get(request_trace_id)
                if cached is not None:
                    self._route_contexts.move_to_end(request_trace_id)
                    return cached

            # Establish the shared trace parent.  Passing an empty string when
            # capture is disabled prevents a differently loaded global config
            # from accidentally persisting content.
            captured = (
                redact_content(request_message)
                if self._config.observability.capture_content
                else ""
            )
            self.adapter.store.create_run(
                trace_id=request_trace_id,
                session_id=request_session_id,
                host=self.adapter.host_name,
                user_message=captured,
                metadata={
                    "callback": "agency-runtime-litellm",
                    "content_capture": bool(captured),
                },
            )
            result = self.adapter.pre_call_handler(
                request_session_id,
                request_message,
                model,
                messages=(
                    list(messages)
                    if isinstance(messages, Sequence)
                    and not isinstance(messages, (str, bytes, bytearray))
                    else None
                ),
                trace_id=request_trace_id,
            )
            context = bounded(
                (result or {}).get("context"),
                _MAX_ROUTE_CONTEXT_CHARS,
            )
            with self._lock:
                self._route_contexts[request_trace_id] = context
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

    async def async_log_pre_api_call(
        self, model: str, messages: list[Any], kwargs: dict[str, Any]
    ) -> None:
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
                updated["messages"] = inject_message_context(messages, context)
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
            if clean(call_type).casefold() not in {
                "completion",
                "chat_completion",
                "responses",
                "anthropic_messages",
            }:
                return data
            updated = dict(data)
            messages = proxy_request_input(updated, call_type)
            context = await asyncio.to_thread(
                self._routing_context,
                model=clean(updated.get("model")),
                messages=messages,
                payload=updated,
            )
            if context:
                inject_proxy_context(updated, messages, context, call_type)
            return updated
        except Exception as exc:
            logger.warning("LiteLLM proxy hook failed: %s", type(exc).__name__)
            return data

    def log_success_event(
        self, kwargs: dict[str, Any], response_obj: Any, start_time: Any, end_time: Any
    ) -> None:
        self._record_receipt(kwargs, response_obj, start_time, end_time, status="success")

    def log_failure_event(
        self, kwargs: dict[str, Any], response_obj: Any, start_time: Any, end_time: Any
    ) -> None:
        self._record_receipt(kwargs, response_obj, start_time, end_time, status="failed")

    async def async_log_success_event(
        self,
        kwargs: dict[str, Any],
        response_obj: Any,
        start_time: Any,
        end_time: Any,
    ) -> None:
        await asyncio.to_thread(self.log_success_event, kwargs, response_obj, start_time, end_time)

    async def async_log_failure_event(
        self,
        kwargs: dict[str, Any],
        response_obj: Any,
        start_time: Any,
        end_time: Any,
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
    raw message logging stays disabled; the callback separately implements
    bounded, redacted, opt-in content capture.
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
