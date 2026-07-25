"""Isolated launcher for installed Agency Runtime process boundaries.

Generated host hooks and services invoke this file by absolute path under
``python -I -S``. Isolated mode removes the caller's CWD, user site, and
``PYTHONPATH`` while ``-S`` prevents the original environment from processing
executable path files. This bootstrap then restores only the exact private
package parent that owns this file.
"""

from __future__ import annotations

import os
import runpy
import sys

_ALLOWED_MODULES = frozenset(
    {
        "agency_runtime.adapters.hermes.bridge",
        "agency_runtime.adapters.hooks",
        "agency_runtime.adapters.openclaw.node_bridge",
        "agency_runtime.cli",
        "agency_runtime.server.dashboard_service",
        "agency_runtime.server.mcp",
    }
)


def _configure_utf8_stdio() -> None:
    """Make host protocol text deterministic across Windows locales."""

    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8", errors="strict")


def main() -> int:
    _configure_utf8_stdio()
    if len(sys.argv) < 2 or sys.argv[1] not in _ALLOWED_MODULES:
        print("Agency Runtime bootstrap rejected the module", file=sys.stderr)
        return 2
    module = sys.argv[1]
    package_parent = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    retained = [
        entry
        for entry in sys.path
        if entry and os.path.normcase(os.path.abspath(entry)) != os.path.normcase(package_parent)
    ]
    # Under -I -S (isolated, no site), the interpreter that launched this
    # bootstrap had its site-packages stripped. For a production install the
    # package and its deps share one site-packages dir; for a development venv
    # install the deps live in the venv's site-packages, which -S removed.
    # Restore the launching interpreter's site-packages so yaml and other
    # installed dependencies are importable. This mirrors how the host's Python
    # (which created this process) resolves installed packages.
    import site

    site_paths = [
        site_dir
        for site_dir in (*site.getsitepackages(), site.getusersitepackages())
        if site_dir and os.path.isdir(site_dir)
    ]
    sys.path[:] = [package_parent, *site_paths, *retained]
    sys.argv = [module, *sys.argv[2:]]
    runpy.run_module(module, run_name="__main__", alter_sys=True)
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised by subprocess tests
    raise SystemExit(main())
