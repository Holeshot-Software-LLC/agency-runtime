"""Dedicated-runtime safety envelope for chaos experiments (AR-362).

Every experiment runs inside one armed envelope: a freshly allocated
owner-private runtime home with its own Store underneath it, synthetic
``chaos-`` session ids, a process-wide gate variable that effects check
before injecting anything, and a rollback that removes the home on exit
even when the experiment raises. The live configured database is refused
by canonical-path comparison, not by convention, and while the envelope is
armed the process-wide ``AGENCY_DB_PATH`` names the dedicated store so an
unqualified ``Store()`` inside the experiment cannot reach the live one.
"""

from __future__ import annotations

import os
import re
import secrets
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agency_runtime.core.chaos.contracts import (
    CHAOS_GATE_VARIABLE,
    CHAOS_SESSION_PREFIX,
    ChaosSafetyError,
    Safety,
    chaos_name,
)
from agency_runtime.core.config import StoreConfig, load_config, reset_config_cache
from agency_runtime.core.correlation import validate_correlation_id
from agency_runtime.core.private_paths import (
    allocate_private_directory,
    private_temporary_directory,
    remove_private_directory,
)
from agency_runtime.core.store.sqlite import Store
from agency_runtime.core.workforce.cache import clear_workforce_caches

_DATABASE_VARIABLE = "AGENCY_DB_PATH"
_RUNTIME_HOME_PREFIX = "chaos"
_STORE_DIRECTORY = "store"
_STORE_FILE = "agency.db"
_LABEL = re.compile(r"[^a-z0-9]+")


def _canonical(value: str | os.PathLike[str]) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(Path(value).expanduser())))


def _label(value: object) -> str:
    normalized = _LABEL.sub("-", str(value or "").strip().casefold()).strip("-")
    if not normalized or len(normalized) > 48:
        raise ValueError("chaos identity label must be 1 to 48 alphanumeric characters")
    return normalized


def live_database_paths(environ: Mapping[str, str]) -> tuple[str, ...]:
    """Name every path the live configured database could resolve to.

    The default store path, the environment override, and the live config's
    resolved store path are all refused. An unreadable live config cannot name
    a database, so it drops out; the default and override still guard it.
    """

    candidates = [_canonical(StoreConfig().resolved_path())]
    configured = str(environ.get(_DATABASE_VARIABLE) or "").strip()
    if configured:
        candidates.append(_canonical(configured))
    try:
        live = load_config()
    except Exception:
        live = None
    if live is not None:
        candidates.append(_canonical(live.store.resolved_path()))
    return tuple(dict.fromkeys(candidates))


@dataclass(frozen=True)
class ChaosEnvelope:
    """One armed experiment boundary: where it may write and who it may be."""

    experiment: str
    runtime_home: Path
    db_path: Path
    child_environ: Mapping[str, str]
    live_database_paths: tuple[str, ...]
    session_prefix: str = CHAOS_SESSION_PREFIX
    gate_variable: str = CHAOS_GATE_VARIABLE

    def require_armed(self) -> None:
        """Raise unless this process is inside this envelope's gate."""

        if os.environ.get(self.gate_variable) != "1":
            raise ChaosSafetyError("chaos effects apply only inside an armed chaos envelope")
        if self.child_environ.get(self.gate_variable) != "1":
            raise ChaosSafetyError("chaos child environment lost its gate")
        if _canonical(os.environ.get(_DATABASE_VARIABLE) or "") != _canonical(self.db_path):
            raise ChaosSafetyError("the process database is not the envelope's dedicated store")
        if not self.runtime_home.is_dir():
            raise ChaosSafetyError("the chaos runtime home is gone")

    def require_session(self, session_id: object) -> str:
        """Return a validated session id or refuse one outside the prefix."""

        normalized = validate_correlation_id(session_id, field="session_id")
        if not normalized.startswith(self.session_prefix):
            raise ChaosSafetyError("chaos experiments run only in dedicated chaos sessions")
        return normalized

    def mint_session_id(self, label: str) -> str:
        return self.require_session(
            f"{self.session_prefix}{_label(label)}-{secrets.token_hex(8)}",
        )

    def mint_trace_id(self, label: str) -> str:
        return validate_correlation_id(
            f"{self.session_prefix}{_label(label)}-trace-{secrets.token_hex(8)}",
            field="trace_id",
        )

    def open_store(self, db_path: str | os.PathLike[str] | None = None) -> Store:
        """Open a Store only below the runtime home and never the live one."""

        target = self.db_path if db_path is None else Path(db_path)
        canonical = _canonical(target)
        if canonical in self.live_database_paths:
            raise ChaosSafetyError("chaos experiments never open the live configured database")
        if not canonical.startswith(_canonical(self.runtime_home) + os.sep):
            raise ChaosSafetyError("chaos stores live only under the dedicated runtime home")
        self.require_armed()
        return Store(target)

    def receipt(self) -> dict[str, Any]:
        """Project the enforced bounds for a receipt without any path content."""

        return {
            "session_prefix": self.session_prefix,
            "gate_variable": self.gate_variable,
            "dedicated_runtime_home": True,
            "dedicated_store": True,
            "live_database_paths_refused": len(self.live_database_paths),
            "runtime_home_removed": not self.runtime_home.exists(),
        }


@contextmanager
def _dedicated_runtime_home(runtime_root: Path | None) -> Iterator[Path]:
    """Yield one fresh owner-private home and remove it on exit, even on error."""

    if runtime_root is None:
        with private_temporary_directory(prefix=_RUNTIME_HOME_PREFIX) as path:
            yield path
        return
    identity = allocate_private_directory(Path(runtime_root), prefix=_RUNTIME_HOME_PREFIX)
    try:
        yield identity.path
    finally:
        remove_private_directory(identity)


@contextmanager
def _process_gate(gate_variable: str, db_path: Path) -> Iterator[None]:
    """Point the process at the dedicated store and raise the gate, then restore."""

    previous = {name: os.environ.get(name) for name in (gate_variable, _DATABASE_VARIABLE)}
    os.environ[gate_variable] = "1"
    os.environ[_DATABASE_VARIABLE] = str(db_path)
    reset_config_cache()
    clear_workforce_caches()
    try:
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        reset_config_cache()
        clear_workforce_caches()


def _dedicated_database_path(runtime_home: Path) -> Path:
    return runtime_home / _STORE_DIRECTORY / _STORE_FILE


def _refuse_live_database(db_path: Path, live_paths: tuple[str, ...]) -> None:
    if _canonical(db_path) in live_paths:
        raise ChaosSafetyError("chaos experiments never target the live configured database")


@contextmanager
def arm_safety(
    safety: Safety,
    experiment: str,
    *,
    environ: Mapping[str, str] | None = None,
    runtime_root: Path | None = None,
) -> Iterator[ChaosEnvelope]:
    """Arm one experiment envelope and roll it back on exit, even on error.

    ``runtime_root`` lets callers (tests, operators) keep the dedicated home
    under an explicit private root; by default it is an ephemeral Agency
    private temporary directory. The child environment is the canary-isolated
    one (private HOME/XDG/TEMP, ``AGENCY_DB_PATH`` at the dedicated store,
    ``AGENCY_CANARY_MODE=1``) plus this harness's own gate variable.
    """

    from agency_runtime.core.canary_backends import isolated_canary_environment

    name = chaos_name(experiment, label="experiment name")
    source_environ = dict(os.environ if environ is None else environ)
    live_paths = live_database_paths(source_environ)
    with _dedicated_runtime_home(runtime_root) as runtime_home:
        db_path = _dedicated_database_path(runtime_home)
        _refuse_live_database(db_path, live_paths)
        child_environ = isolated_canary_environment(source_environ, runtime_home, db_path)
        child_environ[safety.gate_variable] = "1"
        envelope = ChaosEnvelope(
            experiment=name,
            runtime_home=runtime_home,
            db_path=db_path,
            child_environ=dict(child_environ),
            live_database_paths=live_paths,
            session_prefix=safety.session_prefix,
            gate_variable=safety.gate_variable,
        )
        with _process_gate(safety.gate_variable, db_path):
            yield envelope


__all__ = ["ChaosEnvelope", "arm_safety", "live_database_paths"]
