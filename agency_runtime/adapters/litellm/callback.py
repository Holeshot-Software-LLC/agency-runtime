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
import hashlib
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
from agency_runtime.core.config_binding import config_for_store
from agency_runtime.core.http_safety import open_no_redirect
from agency_runtime.core.store.sqlite import Store

from .evidence import (
    bounded,
    bounded_count,
    clean,
    event_identity,
    first,
    hidden_params,
    identifier,
    iso_time,
    known_headers,
    mapping,
    metadata,
    sanitize_api_base,
    session_id,
    trace_id,
)
from .reconciliation import reconcile_litellm_model
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
_RouteLockKey = tuple[str, str]
_RouteContextKey = tuple[str, str, str]


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
        self._config_input = config
        self._config = config
        self._base_url = base_url
        super().__init__(store)

    @property
    def config(self) -> AgencyConfig:
        """Return explicit config or refresh the Store-bound file-aware snapshot."""

        if self._config_input is not None:
            return self._config_input
        return config_for_store(self._store)

    @property
    def store(self) -> Store:
        """Open the configured Store lazily for enabled LiteLLM work."""

        if self._store is None:
            cfg = self.config
            self._store = (
                Store(
                    cfg.store.resolved_path(),
                    config_path=cfg.config_path or None,
                )
                if self._config_input is not None
                else Store(config_path=cfg.config_path or None)
            )
        return self._store

    @store.setter
    def store(self, value: Store) -> None:
        self._store = value

    def _uses_explicit_config(self) -> bool:
        """Keep caller-supplied config immutable and independent from file reloads."""

        return self._config_input is not None

    @property
    def base_url(self) -> str:
        return self._base_url or self.config.adapters.litellm.base_url

    def is_available(self) -> bool:
        from agency_runtime.core.runtime_control import master_enabled

        if not master_enabled():
            return False
        config = self.config
        enabled = config.adapters.litellm.enabled
        if enabled == "false":
            return False
        if enabled == "true":
            return True
        base_url = self._base_url or config.adapters.litellm.base_url
        return litellm_health_check(base_url, config)

    def get_delegate_backend(self) -> str | None:
        return None

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
        from agency_runtime.core.runtime_control import master_enabled

        if not master_enabled():
            return None
        config = self.config
        if config.adapters.litellm.enabled == "false":
            return None
        if _model_is_skipped(model, config.adapters.litellm.skip_models):
            return None
        captured_message = (
            redact_content(user_message) if config.observability.capture_content else ""
        )
        return self.build_preflight_context(
            session_id,
            user_message,
            model,
            trace_id or "",
            config=config,
            persisted_user_message=captured_message,
        )


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
        self._config_input = config
        self._config: AgencyConfig | None = None
        self._store = store
        self._adapter: LiteLLMAdapter | None = None
        self._lock = threading.RLock()
        self._recorded_events: OrderedDict[str, None] = OrderedDict()
        self._route_contexts: OrderedDict[_RouteContextKey, str] = OrderedDict()
        self._route_locks: weakref.WeakValueDictionary[_RouteLockKey, threading.Lock] = (
            weakref.WeakValueDictionary()
        )
        try:
            # Redacted opt-in capture is implemented by this callback.  Never
            # ask LiteLLM's generic logger to retain raw request/response data.
            super().__init__(turn_off_message_logging=True)
        except TypeError:  # compatibility with older LiteLLM CustomLogger versions
            super().__init__()

    @property
    def config(self) -> AgencyConfig:
        """Return explicit config or refresh the Store-bound file-aware snapshot."""

        with self._lock:
            if self._config_input is not None:
                return self._config_input
            bound_store = self._store
            if bound_store is None and self._adapter is not None:
                bound_store = self._adapter._store
        return config_for_store(bound_store)

    def _runtime_active(self) -> bool:
        """Check the master switch before config, Store, routing, or evidence work."""

        from agency_runtime.core.runtime_control import master_enabled

        return master_enabled() and self.config.adapters.litellm.enabled != "false"

    @property
    def adapter(self) -> LiteLLMAdapter:
        with self._lock:
            if self._adapter is None:
                self._adapter = LiteLLMAdapter(
                    store=self._store,
                    config=self._config_input,
                )
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

    def _discard_route_contexts(self, session_id: str, trace_id: str) -> None:
        """Discard every request fingerprint owned by one terminal model call."""

        with self._lock:
            for key in tuple(self._route_contexts):
                if key[:2] == (session_id, trace_id):
                    self._route_contexts.pop(key, None)

    def _event_key(
        self,
        payload: Mapping[str, Any],
        response_obj: Any,
        start_time: Any,
        status: str,
    ) -> tuple[str, str]:
        identity = event_identity(response_obj, start_time)
        request_trace_id = trace_id(payload, response_obj) or identifier(
            f"litellm-terminal:{identity}"
        )
        terminal_status = bounded(status, 32).casefold() or "unknown"
        return (
            request_trace_id,
            f"terminal:{request_trace_id}:{identity}:{terminal_status}",
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
        if not self._runtime_active():
            return
        event_key = ""
        try:
            trace_id, event_key = self._event_key(payload, response_obj, start_time, status)
            if not self._claim(event_key):
                return
            requested_model = bounded(payload.get("model"), 256)
            request_session_id = session_id(payload, trace_id)
            headers = known_headers(response_obj)
            receipt = self.adapter.extract_receipt_from_headers(headers, requested_model, trace_id)
            params = mapping(payload.get("litellm_params"))
            hidden = hidden_params(response_obj)
            reconciled = reconcile_litellm_model(
                payload,
                response_obj,
                receipt=receipt,
                status=status,
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

            receipt_values = {
                "trace_id": trace_id,
                "session_id": request_session_id,
                "host": self.adapter.host_name,
                "requested_model": requested_model,
                "model_group": reconciled.model_group,
                "resolved_provider": reconciled.resolved_provider,
                "resolved_model": reconciled.resolved_model,
                "api_base": bounded(api_base, 1024),
                "attempted_fallbacks": bounded_count(attempted_fallbacks),
                "model_id": bounded(
                    first(receipt.get("model_id"), hidden.get("model_id")),
                    512,
                ),
                "started_at": iso_time(start_time),
                "ended_at": iso_time(end_time),
                "status": status,
            }
            trusted_recorder = getattr(
                self.adapter.store,
                "_record_litellm_model_receipt",
                None,
            )
            if callable(trusted_recorder):
                trusted_recorder(**receipt_values)
            else:
                # Compatibility for Store-like test doubles and embedders.
                # Canonical Store instances always use the provenance-bound
                # path above; a generic Store call cannot persist this source.
                self.adapter.store.record_model_receipt(
                    source="litellm",
                    **receipt_values,
                )
            # A model-call terminal callback is not an Agency-turn terminal
            # callback. Stop/finalize owns run closure after it validates the
            # response against all correlated evidence. The request-scoped
            # routing context is no longer needed once this receipt persists.
            self._discard_route_contexts(request_session_id, trace_id)
        except Exception as exc:  # callbacks must never break model traffic
            if event_key:
                self._unclaim(event_key)
            logger.warning("LiteLLM evidence callback failed: %s", type(exc).__name__)

    def _routing_context(
        self,
        *,
        model: str,
        messages: Any,
        payload: MutableMapping[str, Any],
    ) -> str:
        if not self._runtime_active():
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
        route_lock_key = (request_session_id, request_trace_id)
        request_fingerprint = hashlib.sha256(
            f"{bounded(model, 1024)}\0{request_message}".encode(
                "utf-8",
                errors="surrogatepass",
            )
        ).hexdigest()
        route_key = (*route_lock_key, request_fingerprint)

        with self._lock:
            route_lock = self._route_locks.setdefault(
                route_lock_key,
                threading.Lock(),
            )

        with route_lock:
            with self._lock:
                cached = self._route_contexts.get(route_key)
                if cached is not None:
                    self._route_contexts.move_to_end(route_key)
                    return cached

            # Shared preflight owns trace creation and request fingerprinting.
            # The callback lock makes same-trace re-entry idempotent, while the
            # configured capture flag is applied by that shared boundary.
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
            raw_context = (result or {}).get("context")
            context = clean(raw_context) if isinstance(raw_context, str) else ""
            if len(context) > _MAX_ROUTE_CONTEXT_CHARS:
                raise RuntimeError("Agency routing context exceeds the LiteLLM delivery ceiling")
            with self._lock:
                self._route_contexts[route_key] = context
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
        if not self._runtime_active():
            return kwargs
        try:
            updated = dict(kwargs)
            cleaned_messages = inject_message_context(messages, "")
            context = await asyncio.to_thread(
                self._routing_context,
                model=model,
                messages=cleaned_messages,
                payload=updated,
            )
            original_messages = list(messages)
            if context or cleaned_messages != original_messages:
                updated["messages"] = inject_message_context(cleaned_messages, context)
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
        if not self._runtime_active():
            return data
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
            inject_proxy_context(updated, messages, "", call_type)
            messages = proxy_request_input(updated, call_type)
            context = await asyncio.to_thread(
                self._routing_context,
                model=clean(updated.get("model")),
                messages=messages,
                payload=updated,
            )
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
    from agency_runtime.core.runtime_control import master_enabled

    if not master_enabled():
        return LiteLLMRegistration(False, False, reason="Agency Runtime master switch is off")
    cfg = config_for_store(store, config)
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

        # Keep an explicitly supplied config immutable, but do not turn an
        # omitted config into a process-lifetime snapshot. Long-lived SDK and
        # proxy callbacks must observe atomic dashboard/CLI configuration
        # changes through the Store-bound file-aware loader on the next event.
        callback = AgencyLiteLLMCallback(store=store, config=config)
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
    from agency_runtime.core.runtime_control import master_enabled

    if not master_enabled():
        return {"litellm_settings": {"turn_off_message_logging": True}}
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
