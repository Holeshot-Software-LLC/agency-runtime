"""Stable facade for native host installation and lifecycle management.

Implementation lives in focused modules, but every historical symbol remains
available here.  Installer internals resolve facade dependencies at invocation
time so existing monkeypatches and third-party integrations retain their
behavior across the modular split.
"""

from __future__ import annotations

# ruff: noqa: F401 -- this facade intentionally preserves import-era attributes.
# Keep the original module objects available for compatibility with callers
# that patch stdlib behavior through this long-standing module namespace.
import hashlib
import json
import math
import os
import platform
import re
import shlex
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import uuid
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agency_runtime.core import (
    installer_filesystem as _filesystem,
)
from agency_runtime.core import (
    installer_inventory as _inventory,
)
from agency_runtime.core import (
    installer_native as _native,
)
from agency_runtime.core import (
    installer_orchestration as _orchestration,
)
from agency_runtime.core import (
    installer_payloads as _payloads,
)
from agency_runtime.core import (
    installer_registration as _registration,
)
from agency_runtime.core import installer_zcode as _zcode
from agency_runtime.core.agent_identity import agent_identity
from agency_runtime.core.config import AgencyConfig, load_config
from agency_runtime.core.installer_contracts import (
    HOOK_TIMEOUT_BUFFER_SECONDS,
    HOSTS,
    INSTALL_MANIFEST,
    MARKETPLACE_ID,
    MAX_HOOK_TIMEOUT_SECONDS,
    MAX_NATIVE_OUTPUT_CHARS,
    PLUGIN_ID,
    PLUGIN_VERSION,
    BinaryResolver,
    CommandRunner,
    NativeCommandResult,
)
from agency_runtime.core.policy.defaults import NO_MATCH_FALLBACK_SLUGS, STARTER_ROSTER
from agency_runtime.core.process_argv import prepare_process_argv
from agency_runtime.core.store.roster import BundledRosterReconciliation
from agency_runtime.core.store.sqlite import Store, _default_db_path

# Host discovery and native command compatibility surface.
_utc_stamp = _native._utc_stamp
_explicit_home = _native._explicit_home
_home_path = _native.home_path
_host_path = _home_path
_host_root = _native.host_root
_runtime_home = _native.runtime_home
_plugin_target = _native.plugin_target
_host_evidence_paths = _native._host_evidence_paths
_resolve_binary = _native.resolve_binary
_root_state = _native.root_state
_is_host_installed = _native.is_host_installed
detect_installed_agents = _native.detect_installed_agents
_command_environment = _native._command_environment
_prepare_process_argv = _native.prepare_native_argv
_owned_process_kwargs = _native.owned_process_kwargs
_bounded_native_text = _native._bounded_native_text
_run_native = _native.run_native
_json_output = _native._json_output
_walk_objects = _native._walk_objects
_plugin_record = _native._plugin_record
_hermes_text_plugin_record = _native._hermes_text_plugin_record
_marketplace_registered = _native._marketplace_registered
_bool_field = _native._bool_field
_can_execute_native = _native._can_execute_native
_inventory_command = _inventory._inventory_command
_read_canary_attestation = _inventory._read_canary_attestation
_invalidate_canary_attestation = _inventory._invalidate_canary_attestation
_managed_bundle_identity = _inventory._managed_bundle_identity
_bundle_digest = _inventory._bundle_digest
_managed_bundle_matches = _inventory._managed_bundle_matches
_native_plugin_version_matches = _inventory._native_plugin_version_matches
_sanitize_host_version = _inventory._sanitize_host_version
_canary_attestation_state = _inventory._canary_attestation_state
inspect_host_installations = _inventory.inspect_host_installations
inspect_host_installation = _inventory.inspect_host_installation

# Generated payload and install-time configuration compatibility surface.
_python_commands = _payloads.python_commands
_launcher_artifact_paths = _payloads.launcher_artifact_paths
_runtime_python_argv = _payloads.runtime_python_argv
_resolve_install_config = _payloads.resolve_install_config
_effective_judge_budget_seconds = _payloads.effective_judge_budget_seconds
_hook_timeout_seconds = _payloads.hook_timeout_seconds
_mcp_config = _payloads.mcp_config
_codex_hooks = _payloads.codex_hooks
_claude_hooks = _payloads.claude_hooks
_zcode_hooks = _payloads.zcode_hooks
_agency_control_skill = _payloads.agency_control_skill
_openclaw_index = _payloads.openclaw_index
_codex_plugin_version = _payloads.codex_plugin_version
_bundle_files = _payloads.bundle_files

# Transactional filesystem compatibility surface.
_safe_relative = _filesystem.safe_relative
_atomic_install_tree = _filesystem.atomic_install_tree
_validate_owned_backup = _filesystem.validate_owned_backup
_zcode_config_path = _zcode.zcode_config_path
_inspect_zcode_registration = _zcode.inspect_zcode_registration
_register_zcode_config = _zcode.register_zcode_config
_toggle_zcode_registration = _zcode.toggle_zcode_registration

# Lifecycle orchestration compatibility surface.
_openclaw_gateway_live = _registration.openclaw_gateway_live
_native_registration_steps = _registration.native_registration_steps
_native_command_plan = _registration.native_command_plan
plan_agent_adapter = _registration.plan_agent_adapter
install_agent_adapter = _orchestration.install_agent_adapter
rollback_agent_adapter = _orchestration.rollback_agent_adapter
toggle_agency = _orchestration.toggle_agency


def reconcile_starter_roster(store: Store) -> BundledRosterReconciliation:
    """Add missing bundled agents and separately report proven legacy upgrades."""

    reconcile = getattr(store, "reconcile_bundled_agents", None)
    if callable(reconcile):
        result = reconcile(STARTER_ROSTER)
        if isinstance(result, BundledRosterReconciliation):
            return result
        return BundledRosterReconciliation(added=int(result), upgraded=0)
    activate_many = getattr(store, "activate_agents_if_missing", None)
    if callable(activate_many):
        added = int(activate_many(STARTER_ROSTER))
    else:
        activate_one = getattr(store, "activate_agent_if_missing", None)
        if callable(activate_one):
            added = sum(bool(activate_one(entry)) for entry in STARTER_ROSTER)
        else:
            active = {agent_identity(agent) for agent in store.get_active_roster()}
            added = 0
            for entry in STARTER_ROSTER:
                if str(entry["slug"]) in active:
                    continue
                store.activate_agent(dict(entry))
                added += 1
    return BundledRosterReconciliation(added=added, upgraded=0)


class _StarterRosterSeedCount(int):
    """Additions-only integer carrying exact workforce reconciliation detail."""

    upgraded: int
    contractors_installed: int
    contractors_existing: int

    def __new__(
        cls,
        added: int,
        *,
        upgraded: int,
        contractors_installed: int = 0,
        contractors_existing: int = 0,
    ) -> _StarterRosterSeedCount:
        value = super().__new__(cls, added)
        value.upgraded = upgraded
        value.contractors_installed = contractors_installed
        value.contractors_existing = contractors_existing
        return value


def reconcile_packaged_contractors(store: Store) -> tuple[int, int]:
    """Install contractors and refresh exact package-owned derived contracts."""

    required = (
        "create_hiring_case",
        "get_workforce_worker",
        "register_workforce_worker",
        "stage_agency_workforce_agent",
        "transition_hiring_case",
    )
    if not all(callable(getattr(store, name, None)) for name in required):
        return 0, 0
    from agency_runtime.core.workforce.known_installer import install_known_contractors

    result = install_known_contractors(store)
    reconcile_contracts = getattr(store, "reconcile_packaged_workforce_contracts", None)
    if callable(reconcile_contracts):
        reconcile_contracts()
    return len(result.installed), len(result.existing)


def seed_starter_roster(store: Store) -> int:
    """Reconcile built-ins and governed contractors behind the compatible integer API."""

    result = reconcile_starter_roster(store)
    contractors_installed, contractors_existing = reconcile_packaged_contractors(store)
    return _StarterRosterSeedCount(
        result.added,
        upgraded=result.upgraded,
        contractors_installed=contractors_installed,
        contractors_existing=contractors_existing,
    )


def ensure_no_match_fallback_roster(store: Store) -> int:
    """Idempotently add only missing governed fallback dependencies."""

    required = set(NO_MATCH_FALLBACK_SLUGS)
    active_slug_reader = getattr(store, "get_active_roster_slugs", None)
    active = (
        set(active_slug_reader(required))
        if callable(active_slug_reader)
        else {agent_identity(entry) for entry in store.get_active_roster()}
    )
    missing = required - active
    if not missing:
        return 0
    return sum(
        bool(store.activate_agent_if_missing(entry))
        for entry in STARTER_ROSTER
        if str(entry.get("slug") or "") in missing
    )
