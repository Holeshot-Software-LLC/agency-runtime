"""Isolated launcher for installed Agency Runtime process boundaries.

Generated host hooks and services invoke this file by absolute path under
``python -I``.  Isolated mode removes the caller's CWD, user site, and
``PYTHONPATH``; this bootstrap then restores only the exact package parent that
owns this file, which also supports a normal ``pip install --user`` layout.
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
        "agency_runtime.server.mcp",
    }
)


def main() -> int:
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
    sys.path[:] = [package_parent, *retained]
    sys.argv = [module, *sys.argv[2:]]
    runpy.run_module(module, run_name="__main__", alter_sys=True)
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised by subprocess tests
    raise SystemExit(main())
