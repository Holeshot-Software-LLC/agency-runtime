---
title: "Contributing to Agency Runtime"
status: active
category: governance
created: 2026-07-10
updated: 2026-07-11
tags: [contributing, development]
related:
  - AGENTS.md
  - docs/roadmap/README.md
  - docs/decisions/README.md
  - docs/RELEASE_CHECKLIST.md
supersedes: []
superseded_by: null
---

# Contributing to Agency Runtime

Agency Runtime is prerelease software with correctness-sensitive host,
delegation, and evidence boundaries. Contributions are welcome, but a passing
unit test is not enough when a change affects native host discovery, persisted
evidence, or security claims.

## Set up a development environment

Use Python 3.10 or newer in an isolated environment:

```bash
python -m venv .venv
# PowerShell: .venv\Scripts\Activate.ps1
# POSIX:      . .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest tests -q
```

Tests that generate host files must use an explicit temporary home and database.
Do not point a test at the real `HOME`, `USERPROFILE`, `CODEX_HOME`,
`CLAUDE_CONFIG_DIR`, `HERMES_HOME`, `OPENCLAW_HOME`, or `AGENCY_DB_PATH`.

## Before changing code

Read [AGENTS.md](AGENTS.md). Any newly surfaced feature, enhancement, or bug
needs a stable `AR-NN` roadmap record and same-repository tracker issue before
the change is complete. Durable architecture, product, security, data, or
operating choices need the next ADR in the single decision number space.

Keep changes focused. Preserve unrelated user work in a dirty checkout and do
not rewrite faithful historical records. Documentation must remain usable from
this repository without sibling-repository links or machine-specific paths.

## Implementation expectations

- Treat native files, registration, enablement, loading, and canary execution as
  separate facts.
- Never infer successful evidence from an attempted or failed tool call.
- Use subprocess argv arrays, bounded output, deadlines, and validated success
  protocols. Do not invoke agent commands through a shell.
- Keep LiteLLM, host CLIs, Node.js, and network providers optional.
- Default to metadata-only storage. New content capture requires an explicit
  configuration choice, bounded retention, and documented redaction limits.
- Preserve Windows and POSIX paths, executable shims, quoting, and isolated-home
  behavior.
- Prefer small idempotent helpers and deterministic offline tests.

## Validation

Run the checks applicable to the change, and run the complete gate before
handoff:

```bash
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
python -m pytest tests -q
agency eval routing --json --no-details
git diff --check
```

When tracker access is authorized and the local records should be in parity:

```bash
python scripts/verify_docs.py --require-tracker
python scripts/verify_tracker.py
```

For packaging or release-facing changes also run:

```bash
python scripts/verify_release_hygiene.py
python -m build --sdist --wheel
python -m twine check --strict dist/*
python scripts/verify_distribution.py dist
```

The CI matrix runs the test suite on Ubuntu with Python 3.10 through 3.14 and on
Windows at the 3.10/3.14 support endpoints, then installs the built wheel in
isolated Windows and Ubuntu jobs. A green contract suite does not replace a live
host canary when the public claim says a host is runtime-verified.

## Commit and documentation records

Use a clear imperative commit subject. Every substantive commit needs one exact
row in `docs/worklog/README.md`; reasoning-rich commits also need a detail file.
Because a commit cannot contain its own SHA, record it in the immediately
following `docs(worklog):` ledger-only commit as defined in [AGENTS.md](AGENTS.md).

Do not push, publish, create a release, close issues, or open a pull request
without the required outward-facing authorization.
