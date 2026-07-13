"""Repository wrapper for the installed Agency Runtime host-canary command."""

from agency_runtime.core.canary import main

if __name__ == "__main__":
    raise SystemExit(main())
