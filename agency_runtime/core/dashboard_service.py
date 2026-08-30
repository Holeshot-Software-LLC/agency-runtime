"""User-scoped lifecycle management for the local operations dashboard.

The public module is intentionally a small compatibility facade. Shared
security primitives, read-only inspection, platform registration mechanics,
and mutating lifecycle transactions live in cohesive sibling modules.
"""

from agency_runtime.core.dashboard_service_core import (
    MANIFEST_SCHEMA_VERSION,
    OWNER_ID,
    OWNER_MARKER,
    SYSTEMD_UNIT_NAME,
    WINDOWS_TASK_NAME,
    build_service_worker_argv,
)
from agency_runtime.core.dashboard_service_core import (
    WINDOWS_TASK_XML_NAMESPACE as WINDOWS_TASK_XML_NAMESPACE,
)
from agency_runtime.core.dashboard_service_core import (
    _context as _context,
)
from agency_runtime.core.dashboard_service_inspection import (
    inspect_dashboard_service,
    plan_dashboard_service,
)
from agency_runtime.core.dashboard_service_install import install_dashboard_service
from agency_runtime.core.dashboard_service_lifecycle import (
    restart_dashboard_service,
    start_dashboard_service,
    stop_dashboard_service,
    uninstall_dashboard_service,
)
from agency_runtime.core.dashboard_service_manifest import (
    _restore_file as _restore_file,
)
from agency_runtime.core.dashboard_service_manifest import (
    _service_lock as _service_lock,
)
from agency_runtime.core.dashboard_service_windows import (
    _WINDOWS_TASK_PROBE_SCRIPT as _WINDOWS_TASK_PROBE_SCRIPT,
)
from agency_runtime.core.dashboard_service_windows import (
    _register_windows_xml as _register_windows_xml,
)
from agency_runtime.core.dashboard_service_windows import (
    _windows_task_content as _windows_task_content,
)
from agency_runtime.core.dashboard_service_windows import (
    _windows_task_properties as _windows_task_properties,
)

__all__ = [
    "MANIFEST_SCHEMA_VERSION",
    "OWNER_ID",
    "OWNER_MARKER",
    "SYSTEMD_UNIT_NAME",
    "WINDOWS_TASK_NAME",
    "build_service_worker_argv",
    "inspect_dashboard_service",
    "install_dashboard_service",
    "plan_dashboard_service",
    "restart_dashboard_service",
    "start_dashboard_service",
    "stop_dashboard_service",
    "uninstall_dashboard_service",
]
