"""Plan-bound operator authority for attended host-integration uninstall."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any, NamedTuple

from agency_runtime.core.host_lifecycle_lock import HostLifecycleLockError, host_integrations_lock
from agency_runtime.core.installer_contracts import HOSTS, BinaryResolver, CommandRunner
from agency_runtime.core.installer_native import runtime_home

HOST_UNINSTALL_ACTION = "uninstall.host-integrations.v1"
_PLAN_SCHEMA = "agency.host-uninstall-plan.v1"
_BINDING_DOMAIN = b"agency.prepared-host-uninstall.v1\0"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_PRESERVATION_POLICY = "runtime-data-and-marketplaces.v1"
_RECOVERY_POLICY = "retained-owned-bundles.v1"
_TRANSITIONS = frozenset(
    {
        "disable+retain",
        "unregister+retain",
        "remove-handlers+retain",
        "retain-only",
    }
)
_HOST_TRANSITIONS = {
    "hermes": frozenset({"disable+retain", "retain-only"}),
    "openclaw": frozenset({"unregister+retain", "retain-only"}),
    "codex": frozenset({"unregister+retain", "retain-only"}),
    "claude": frozenset({"unregister+retain", "retain-only"}),
    "zcode": frozenset({"remove-handlers+retain", "retain-only"}),
}


class PreparedHostUninstallError(RuntimeError):
    """An exact attended uninstall could not be prepared or committed safely."""


class _HostUninstallBinding(NamedTuple):
    action: str
    operation_id: str
    selection: str
    targets_csv: str
    transitions_csv: str
    host_count: int
    confirmed_plan_sha256: str
    host_bindings_sha256: str
    preservation_policy: str
    recovery_policy: str
    binding_sha256: str


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _binding_digest(values: Sequence[str | int]) -> str:
    return hashlib.sha256(_BINDING_DOMAIN + _canonical_json(list(values))).hexdigest()


def _host_uninstall_binding_primitives(binding: object) -> tuple[str | int, ...]:
    """Return exact primitive fields and reject forged or malformed bindings."""

    if type(binding) is not _HostUninstallBinding:
        raise PreparedHostUninstallError("prepared host uninstall binding is invalid")
    if any(type(value) is not str for value in binding[:-1] if not isinstance(value, int)):
        raise PreparedHostUninstallError("prepared host uninstall binding is invalid")
    if type(binding.host_count) is not int:
        raise PreparedHostUninstallError("prepared host uninstall binding is invalid")
    hosts = binding.targets_csv.split(",") if binding.targets_csv else []
    transitions = binding.transitions_csv.split(",") if binding.transitions_csv else []
    canonical = [host for host in HOSTS if host in hosts]
    try:
        canonical_operation_id = str(uuid.UUID(binding.operation_id))
    except (AttributeError, ValueError):
        canonical_operation_id = ""
    if (
        binding.action != HOST_UNINSTALL_ACTION
        or binding.operation_id != canonical_operation_id
        or binding.selection not in {"agent", "all"}
        or not hosts
        or hosts != canonical
        or len(set(hosts)) != len(hosts)
        or binding.host_count != len(hosts)
        or not 1 <= binding.host_count <= len(HOSTS)
        or (binding.selection == "agent" and len(hosts) != 1)
        or len(transitions) != len(hosts)
        or any(
            transition != f"{host}:{transition.rsplit(':', 1)[-1]}"
            or transition.rsplit(":", 1)[-1] not in _TRANSITIONS
            or transition.rsplit(":", 1)[-1] not in _HOST_TRANSITIONS[host]
            for host, transition in zip(hosts, transitions, strict=True)
        )
        or _SHA256.fullmatch(binding.confirmed_plan_sha256) is None
        or _SHA256.fullmatch(binding.host_bindings_sha256) is None
        or binding.preservation_policy != _PRESERVATION_POLICY
        or binding.recovery_policy != _RECOVERY_POLICY
        or _SHA256.fullmatch(binding.binding_sha256) is None
        or _binding_digest(tuple(binding)[:-1]) != binding.binding_sha256
    ):
        raise PreparedHostUninstallError("prepared host uninstall binding is invalid")
    return tuple(binding)


def _transition(plan: Mapping[str, Any]) -> str:
    commands = plan.get("native_command_plan")
    if not isinstance(commands, list) or not commands:
        return "retain-only"
    host = str(plan.get("host") or "")
    return (
        "disable+retain"
        if host == "hermes"
        else "remove-handlers+retain"
        if host == "zcode"
        else "unregister+retain"
    )


def _retained_path(
    host: str,
    *,
    operation_id: str,
    home_dir: str | Path | None,
) -> Path:
    return (
        runtime_home(home_dir=home_dir) / "backups" / host / f"uninstall-{operation_id}"
    ).resolve()


def _make_binding(
    *,
    operation_id: str,
    selected_by: str,
    targets: Sequence[str],
    plans: Sequence[Mapping[str, Any]],
    plan_sha256: str,
    home_dir: str | Path | None,
) -> _HostUninstallBinding:
    transitions = [_transition(plan) for plan in plans]
    host_bindings = [
        {
            "host": host,
            "transition": transition,
            "plan_binding_sha256": plan.get("binding_digest"),
            "target": plan.get("target"),
            "retained_path": str(
                _retained_path(host, operation_id=operation_id, home_dir=home_dir)
            ),
        }
        for host, transition, plan in zip(targets, transitions, plans, strict=True)
    ]
    values: tuple[str | int, ...] = (
        HOST_UNINSTALL_ACTION,
        operation_id,
        selected_by,
        ",".join(targets),
        ",".join(
            f"{host}:{transition}" for host, transition in zip(targets, transitions, strict=True)
        ),
        len(targets),
        plan_sha256,
        hashlib.sha256(
            b"agency.host-uninstall-host-bindings.v1\0" + _canonical_json(host_bindings)
        ).hexdigest(),
        _PRESERVATION_POLICY,
        _RECOVERY_POLICY,
    )
    binding = _HostUninstallBinding(*values, _binding_digest(values))
    _host_uninstall_binding_primitives(binding)
    return binding


def is_exact_prepared_host_uninstall(namespace: object) -> bool:
    """Recognize only the reviewed dry-run or exact-confirm uninstall shape."""

    agent = getattr(namespace, "agent", None)
    all_hosts = getattr(namespace, "all", False)
    dry_run = getattr(namespace, "dry_run", False)
    confirm_plan = getattr(namespace, "confirm_plan", None)
    target_exact = type(all_hosts) is bool and (
        (all_hosts and agent is None) or (not all_hosts and agent in HOSTS)
    )
    mode_exact = type(dry_run) is bool and (
        (dry_run and confirm_plan is None)
        or (
            not dry_run
            and isinstance(confirm_plan, str)
            and _SHA256.fullmatch(confirm_plan) is not None
        )
    )
    return bool(
        getattr(namespace, "command", None) == "uninstall"
        and target_exact
        and mode_exact
        and type(getattr(namespace, "json", False)) is bool
    )


def _plan_projection(plan: Mapping[str, Any]) -> dict[str, Any]:
    ownership = plan.get("ownership")
    if not isinstance(ownership, Mapping):
        ownership = {}
    return {
        "host": plan.get("host"),
        "target": plan.get("target"),
        "install_id": ownership.get("install_id"),
        "bundle_digest": ownership.get("bundle_digest"),
        "binding_digest": plan.get("binding_digest"),
        "status": plan.get("status"),
        "would_change": plan.get("would_change") is True,
        "native_command_plan": plan.get("native_command_plan", []),
    }


def uninstall_plan_digest(
    plans: Sequence[Mapping[str, Any]],
    *,
    selected_by: str,
    targets: Sequence[str],
) -> str:
    """Hash one canonical selector plus its exact per-host plans."""

    canonical_targets = [host for host in HOSTS if host in targets]
    if (
        selected_by not in {"all", "agent"}
        or list(targets) != canonical_targets
        or len(set(targets)) != len(targets)
        or (selected_by == "agent" and len(targets) != 1)
        or len(plans) != len(targets)
        or [plan.get("host") for plan in plans] != list(targets)
    ):
        raise PreparedHostUninstallError("host uninstall plan selection is invalid")
    payload = {
        "schema_version": _PLAN_SCHEMA,
        "selected_by": selected_by,
        "targets": list(targets),
        "plans": [_plan_projection(plan) for plan in plans],
        "retains_owned_bundles": True,
        "removes_marketplaces": False,
        "removes_agency_data": False,
    }
    return hashlib.sha256(_canonical_json(payload)).hexdigest()


def _require_host_uninstall_authority(binding: _HostUninstallBinding) -> None:
    """Keep host uninstall closed after retirement of Agency-owned authority."""

    _host_uninstall_binding_primitives(binding)
    raise PreparedHostUninstallError(
        "host integration uninstall is unavailable; no host mutation was made"
    )


def _canonical_targets(targets: Sequence[str], *, selected_by: str) -> tuple[str, ...]:
    values = tuple(targets)
    canonical = tuple(host for host in HOSTS if host in values)
    if (
        selected_by not in {"all", "agent"}
        or values != canonical
        or len(set(values)) != len(values)
        or (selected_by == "agent" and len(values) != 1)
    ):
        raise PreparedHostUninstallError("host uninstall selection is invalid")
    return values


def _canonical_operation_id(value: str) -> str:
    try:
        if str(uuid.UUID(value)) != value:
            raise ValueError
    except (AttributeError, ValueError) as exc:
        raise PreparedHostUninstallError("host uninstall operation ID is invalid") from exc
    return value


@contextmanager
def _uninstall_lock(*, home_dir: str | Path | None) -> Iterator[None]:
    try:
        with host_integrations_lock(home_dir=home_dir):
            yield
    except HostLifecycleLockError as exc:
        raise PreparedHostUninstallError("another host integration transaction is active") from exc


def _plan_targets(
    targets: Sequence[str],
    *,
    home_dir: str | Path | None,
    binary_resolver: BinaryResolver | None,
    command_runner: CommandRunner | None,
) -> list[dict[str, Any]]:
    from agency_runtime.core.installer_uninstall import plan_agent_uninstall

    return [
        plan_agent_uninstall(
            host,
            home_dir=home_dir,
            binary_resolver=binary_resolver,
            command_runner=command_runner,
        )
        for host in targets
    ]


def _plan_has_agency_evidence(plan: Mapping[str, Any]) -> bool:
    inspection = plan.get("inspection")
    ownership = plan.get("ownership")
    if not isinstance(inspection, Mapping):
        inspection = {}
    if not isinstance(ownership, Mapping):
        ownership = {}
    managed = all(
        isinstance(inspection.get(field), str) and bool(inspection.get(field))
        for field in ("managed_plugin_version", "install_id", "bundle_digest")
    )
    return bool(managed or inspection.get("registered") is True or ownership.get("present") is True)


def _replan_selection(
    expected_targets: Sequence[str],
    *,
    selected_by: str,
    home_dir: str | Path | None,
    binary_resolver: BinaryResolver | None,
    command_runner: CommandRunner | None,
) -> list[dict[str, Any]]:
    candidates = tuple(HOSTS) if selected_by == "all" else tuple(expected_targets)
    plans = _plan_targets(
        candidates,
        home_dir=home_dir,
        binary_resolver=binary_resolver,
        command_runner=command_runner,
    )
    if selected_by == "all":
        plans = [plan for plan in plans if _plan_has_agency_evidence(plan)]
    if [plan.get("host") for plan in plans] != list(expected_targets):
        raise PreparedHostUninstallError(
            "host uninstall selection changed after planning; no host mutation was made"
        )
    return plans


def _apply_prepared_host_uninstall(
    targets: Sequence[str],
    *,
    expected_plan_digest: str,
    operation_id: str,
    selected_by: str,
    home_dir: str | Path | None = None,
    binary_resolver: BinaryResolver | None = None,
    command_runner: CommandRunner | None = None,
    on_authorized: Callable[[], None] | None = None,
    on_result: Callable[[dict[str, Any]], None] | None = None,
) -> list[dict[str, Any]]:
    """Verify one exact aggregate plan, lock it, and commit its hosts in order."""

    selected = _canonical_targets(targets, selected_by=selected_by)
    if _SHA256.fullmatch(expected_plan_digest) is None:
        raise PreparedHostUninstallError("host uninstall plan digest is invalid")
    operation_id = _canonical_operation_id(operation_id)
    plans = _replan_selection(
        selected,
        selected_by=selected_by,
        home_dir=home_dir,
        binary_resolver=binary_resolver,
        command_runner=command_runner,
    )
    digest = uninstall_plan_digest(plans, selected_by=selected_by, targets=selected)
    if digest != expected_plan_digest or any(plan.get("ok") is not True for plan in plans):
        raise PreparedHostUninstallError(
            "host uninstall plan changed before operator verification; no host mutation was made"
        )
    mutating = any(plan.get("would_change") is True for plan in plans)
    if mutating:
        binding = _make_binding(
            operation_id=operation_id,
            selected_by=selected_by,
            targets=selected,
            plans=plans,
            plan_sha256=digest,
            home_dir=home_dir,
        )
        primitives = _host_uninstall_binding_primitives(binding)
        _require_host_uninstall_authority(binding)

    outcomes: list[dict[str, Any]] = []
    with _uninstall_lock(home_dir=home_dir):
        current = _replan_selection(
            selected,
            selected_by=selected_by,
            home_dir=home_dir,
            binary_resolver=binary_resolver,
            command_runner=command_runner,
        )
        current_digest = uninstall_plan_digest(
            current,
            selected_by=selected_by,
            targets=selected,
        )
        if current_digest != expected_plan_digest or any(
            plan.get("ok") is not True for plan in current
        ):
            raise PreparedHostUninstallError(
                "host uninstall plan changed after operator verification; no host mutation was made"
            )
        if mutating:
            current_binding = _make_binding(
                operation_id=operation_id,
                selected_by=selected_by,
                targets=selected,
                plans=current,
                plan_sha256=current_digest,
                home_dir=home_dir,
            )
            if _host_uninstall_binding_primitives(current_binding) != primitives:
                raise PreparedHostUninstallError(
                    "host uninstall binding changed after operator verification; "
                    "no host mutation was made"
                )

        if mutating and on_authorized is not None:
            on_authorized()

        from agency_runtime.core.installer_uninstall import _commit_agent_uninstall

        for plan in current:
            if plan.get("status") == "not_installed":
                result = dict(plan)
            else:
                ownership = plan.get("ownership")
                if not isinstance(ownership, Mapping):
                    raise PreparedHostUninstallError("host uninstall ownership plan is invalid")
                result = _commit_agent_uninstall(
                    str(plan["host"]),
                    expected_install_id=str(ownership.get("install_id") or ""),
                    expected_bundle_digest=str(ownership.get("bundle_digest") or ""),
                    expected_binding_digest=str(plan.get("binding_digest") or ""),
                    retained_path=_retained_path(
                        str(plan["host"]),
                        operation_id=operation_id,
                        home_dir=home_dir,
                    ),
                    home_dir=home_dir,
                    binary_resolver=binary_resolver,
                    command_runner=command_runner,
                )
            outcomes.append(result)
            if on_result is not None:
                on_result(result)
            if result.get("ok") is not True:
                break
    return outcomes


def apply_prepared_host_uninstall(
    targets: Sequence[str],
    *,
    expected_plan_digest: str,
    operation_id: str,
    selected_by: str,
    on_authorized: Callable[[], None] | None = None,
    on_result: Callable[[dict[str, Any]], None] | None = None,
) -> list[dict[str, Any]]:
    """Apply one attended production plan without injectable host boundaries."""

    return _apply_prepared_host_uninstall(
        targets,
        expected_plan_digest=expected_plan_digest,
        operation_id=operation_id,
        selected_by=selected_by,
        on_authorized=on_authorized,
        on_result=on_result,
    )


__all__ = [
    "HOST_UNINSTALL_ACTION",
    "PreparedHostUninstallError",
    "apply_prepared_host_uninstall",
    "is_exact_prepared_host_uninstall",
    "uninstall_plan_digest",
]
