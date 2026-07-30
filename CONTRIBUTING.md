---
title: "Contributing to Agency Runtime"
status: active
category: governance
created: 2026-07-10
updated: 2026-07-29
tags: [contributing, development]
related:
  - AGENTS.md
  - CODE_OF_CONDUCT.md
  - SECURITY.md
  - docs/THREAT_MODEL.md
  - docs/roadmap/README.md
  - docs/decisions/README.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - docs/RELEASE_CHECKLIST.md
  - docs/roadmap/issue-AR-186-bound-delivery-to-live-demo-checkpoints.md
supersedes: []
superseded_by: null
---

# Contributing to Agency Runtime

Agency Runtime is prerelease software with correctness-sensitive host,
delegation, and evidence boundaries. Contributions are welcome, but a passing
unit test is not enough when a change affects native host discovery, persisted
evidence, or security claims.

Participation is governed by [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md). Review
the [threat model](docs/THREAT_MODEL.md) before changing a trust boundary.

## Set up a development environment

Use Python 3.10 or newer in an isolated environment:

```bash
python -m venv .venv
# PowerShell: .venv\Scripts\Activate.ps1
# POSIX:      . .venv/bin/activate
python -m pip install -e ".[dev,release,security]"
ruff check agency_runtime tests scripts
node --test tests/dashboard_ui.test.mjs
```

Run the named fast Python production spine in the Validation section before a
handoff. The exhaustive integration suites are deliberately not part of routine
local setup.

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

Run focused tests for every changed behavior and the automatic-equivalent gate
before handoff. Its named fast Python production spine is:

```bash
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python -m pytest \
  tests/test_senior_audit_hardening.py \
  tests/test_configuration_namespace_security.py \
  tests/test_executable_namespace_security.py \
  tests/test_dashboard_auth_boundary_regression.py \
  tests/test_dashboard_transaction_refactors.py \
  tests/test_routing_correctness.py \
  tests/test_workforce_hiring_contract.py \
  tests/test_workforce_selection_safety.py \
  tests/test_workforce_dynamic_hiring.py \
  tests/test_decision_conformance.py \
  tests/test_delegation_p1_correctness.py \
  tests/test_store_turn_atomicity.py \
  tests/test_roster_snapshot_generation.py \
  tests/test_mcp_protocol_hardening.py \
  tests/test_cli_parser_contract.py \
  tests/test_cli_upgrade.py \
  tests/test_update_service.py \
  tests/test_native_installer.py \
  tests/test_host_boundary_hardening.py \
  tests/test_cli_operator_presence.py \
  tests/test_security_turn_boundaries.py \
  -q -W error
node --test tests/dashboard_ui.test.mjs
agency eval routing --json --no-details
agency eval decision-conformance --repository . --json
git diff --check
```

Pull-request and push automation intentionally does not run the complete
warning-strict Python corpus, four-shard 97-percent coverage gate, or full
Ubuntu/Windows six-interpreter compatibility matrix. Those are exhaustive
integration gates and run only when an authorized maintainer explicitly starts
the CI workflow with `workflow_dispatch`. They are optional diagnostics rather
than issue-completion, demo, production, or release requirements. Record whether
they ran when relevant, but do not treat missing manual evidence as an automatic
`NO-GO`.

Each contribution package should define one observable outcome, run focused
tests plus the named fast spine, and reach an installed or live demo checkpoint
before unrelated cleanup expands scope. Two independent review passes are the
default maximum unless unresolved Critical/High evidence or a maintainer request
justifies more. Human-owned steps are recorded as `waiting_for_operator` and are
not retried in an unattended loop.

When tracker access is authorized and the local records should be in parity:

```bash
python scripts/verify_docs.py --require-tracker
python scripts/verify_tracker.py
```

For packaging or release-facing changes also run the applicable checks below
and follow [the release checklist](docs/RELEASE_CHECKLIST.md):

```bash
python scripts/verify_release_hygiene.py
bandit -q -r agency_runtime scripts -lll
python scripts/audit_runtime_dependencies.py
zizmor --pedantic --strict-collection --offline .
AGENCY_RELEASE_COMMIT="$(git rev-parse --verify 'HEAD^{commit}')"
AGENCY_DIST_DIR="${HOME}/.agency-runtime/release-artifacts/dist-${AGENCY_RELEASE_COMMIT}"
python -m scripts.build_distributions "${AGENCY_DIST_DIR}" --create-private-parent \
  --expected-commit "${AGENCY_RELEASE_COMMIT}"
python -m twine check --strict "${AGENCY_DIST_DIR}"/*
python -m scripts.verify_distribution "${AGENCY_DIST_DIR}" \
  --expected-commit "${AGENCY_RELEASE_COMMIT}"
```

Capture `AGENCY_RELEASE_COMMIT` from the clean reviewed checkout before the
build. The canonical builder reads exact committed Git blobs rather than
line-ending-filtered worktree bytes and refuses to replace an existing output
directory. The output parent is owner-private and outside the checkout so an
unsafe inherited workspace ACL cannot race staging or publication. Its bounded
normalization step preserves source-derived payload bytes, canonicalizes LF only
for the shared explicit generated-metadata allowlist, rebuilds wheel `RECORD`,
and gives Windows and Linux builds the same explicitly encoded stored-ZIP,
RFC 1951 stored-block gzip, tar, ownership, mode, and timestamp container policy
without relying on host zlib output.

In PowerShell, use the same external boundary:

```powershell
$env:AGENCY_RELEASE_COMMIT = git rev-parse --verify "HEAD^{commit}"
$env:AGENCY_DIST_DIR = Join-Path $HOME `
  ".agency-runtime\release-artifacts\dist-$env:AGENCY_RELEASE_COMMIT"
python -m scripts.build_distributions $env:AGENCY_DIST_DIR `
  --create-private-parent --expected-commit $env:AGENCY_RELEASE_COMMIT
$artifacts = Get-ChildItem -LiteralPath $env:AGENCY_DIST_DIR -File |
  Select-Object -ExpandProperty FullName
python -m twine check --strict $artifacts
python -m scripts.verify_distribution $env:AGENCY_DIST_DIR `
  --expected-commit $env:AGENCY_RELEASE_COMMIT
```

Keep Twine and the distribution verifier as independent post-build gates.
Release-scoped Git inputs and archive regular files must be non-executable;
tracked inputs are exactly `100644`. Run the command from a trusted Python
environment whose executable namespace cannot be modified by another OS
account. On Windows, that normally means a private virtual environment outside
a broadly writable checkout; the builder deliberately rejects an untrusted
repository-local launcher or output parent.

The CI matrix runs the complete test suite on Ubuntu with Python 3.10 through
3.14 and on Windows at the 3.10/3.14 support endpoints. A focused native Windows
suite exercises canonical archive golden digests and atomic Job-at-creation
process ownership on Python 3.11, 3.12, and 3.13 as well. Both Ubuntu and Windows
build and strictly verify the canonical distributions. CI uploads both
platform pairs to a short-lived parity gate and requires their filenames and
bytes to match exactly; only the Ubuntu pair is also retained as the candidate
for isolated Windows and Ubuntu artifact-smoke installs. A green contract suite
does not replace a live host canary when the public claim says a host is
runtime-verified.

## Commit and documentation records

Use a clear imperative commit subject. Every substantive commit needs one exact
row in `docs/worklog/README.md`; reasoning-rich commits also need a detail file.
Because a commit cannot contain its own SHA, record it in the immediately
following `docs(worklog):` ledger-only commit as defined in [AGENTS.md](AGENTS.md).

Do not push, publish, create a release, close issues, or open a pull request
without the required outward-facing authorization.
