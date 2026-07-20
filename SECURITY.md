---
title: "Security Policy"
status: active
category: governance
created: 2026-07-10
updated: 2026-07-20
tags: [security, reporting, privacy]
related:
  - README.md
  - docs/THREAT_MODEL.md
  - docs/TROUBLESHOOTING.md
  - docs/RELEASE_CHECKLIST.md
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
supersedes: []
superseded_by: null
---

# Security Policy

Agency Runtime is prerelease software. No stable public version is currently
declared supported. Security fixes target the current maintained branch until a
versioned support policy is published.

## Report a vulnerability

Do not include secrets, exploit details, private prompts, database contents, or
personal information in a public issue. Use this repository's private security
advisory channel when it is available. If it is unavailable, contact the
repository maintainers through an existing private organizational channel and
ask for a secure reporting path before sending sensitive details.

Include:

- the affected version or commit;
- operating system and Python version;
- affected host or integration;
- the smallest safe reproduction;
- expected and observed behavior;
- impact and any known workaround.

Maintainers should acknowledge a private report, establish a disclosure plan,
and avoid publishing identifying or exploit-enabling detail before a fix is
available. This document does not promise a response-time service level.

## Security boundaries

The asset, attacker, control, and residual-risk analysis is maintained in the
[repository threat model](docs/THREAT_MODEL.md). The following boundaries are
the operator-facing summary.

The following boundaries are intentional and should be treated as part of the
product contract:

- The operations dashboard binds only to loopback. It is not designed for
  remote exposure, reverse proxying, shared workstations, or multi-user access.
- The dashboard token is temporary bearer authority. Anyone who obtains the
  active URL or token can invoke the dashboard API as that local user.
- Service mode rotates that token on every worker start and keeps it in an
  owner-restricted runtime descriptor. Service definitions, process arguments,
  logs, and status results must never contain it. A stale descriptor is not
  proof that the service is reachable.
- `agency serve` is a separate local integration surface and is not the
  authenticated operations dashboard. Do not expose it to an untrusted network.
- Configuration and SQLite state belong to the local operating-system account.
  Protect the home directory and never commit `agency.yaml`, database files,
  host credentials, or generated host state.
- A custom `AGENCY_CONFIG_PATH` or `AGENCY_DB_PATH` never grants permission
  to rewrite the mode or ACL of a pre-existing parent directory. Target files
  and SQLite sidecars remain owner-only, Windows DACL failure is fatal, and
  database symlink or reparse-point targets are rejected before open.
- Dashboard and CLI configuration mutations share one allowlisted, typed,
  revision-checked, owner-only atomic writer. Direct credentials are write-only;
  prefer environment-variable references and hidden CLI input.
- Credentialed remote providers require HTTPS. Literal loopback HTTP is the
  only exception; URLs with embedded user information, queries, or fragments
  are rejected, and authenticated requests never follow redirects.
- Delegated commands receive a minimal allowlisted environment plus only the
  chosen host's authentication root. Prompts use standard input where the host
  contract permits it, are length-bounded and recursively redacted, and owned
  descendants are terminated on timeout or after a parent exits.
- Metadata-only observability is the default. Opt-in content capture uses
  bounded defensive redaction, but no automatic redactor can guarantee removal
  of every secret or personal identifier.
- Host installers call native plugin lifecycle commands. Preview with
  `--dry-run`, inspect the command plan, retain backups, and do not run an
  untrusted executable found earlier on `PATH`.
- MCP and host-hook standard output is a machine protocol. Mixing logs into it
  can corrupt framing; operational diagnostics belong on standard error.

## Local hardening

Use a dedicated virtual environment, keep host CLIs and Python dependencies
updated, prefer environment-backed provider credentials, and review redacted
configuration with `agency config show`. Run:

```bash
python scripts/verify_release_hygiene.py
python -m bandit -q -r agency_runtime scripts -lll
python -m pip_audit . --strict
```

The release workflow performs deterministic tracked-file checks, high-severity
source scanning, and an audit of the installed runtime dependency. These checks
reduce risk; they are not proof that the program is vulnerability-free.
