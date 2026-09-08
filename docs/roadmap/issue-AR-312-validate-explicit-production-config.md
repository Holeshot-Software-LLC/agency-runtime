---
title: "AR-312: Validate an explicit production config before installation"
status: in_progress
category: roadmap
created: 2026-08-26
updated: 2026-09-08
tags: [configuration, documentation, installation, production-container]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - docs/decisions/0006-config-first-redacted-configuration.md
  - docs/roadmap/handoffs/issue-AR-312.md
  - README.md
  - agency_runtime/cli/parser.py
  - agency_runtime/cli/config_commands.py
  - tests/test_cli_parser_contract.py
  - tests/test_cli_config_validate.py
  - docs/worklog/2026-09-08-ar312-explicit-config-validation.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: install
issue_id: AR-312
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/758
depends_on: []
blocks: []
---

# AR-312: Validate an explicit production config before installation

## Problem

The unattended-container README tells an operator to materialize an exact
configuration, run `agency config validate`, and then pass that file to
`agency install --production-container --config <absolute-path>`. The validate
command has no config-path argument. In a fresh container it therefore opens
the absent default Store and host state instead of validating the file that the
following install will consume.

## Current state

- Exact AR-297 Codex image `2aed0f49...33a276b` reproduces the mismatch before
  installation: `agency config validate` exits 1 because the default
  `/root/.agency-runtime/agency.db` does not exist and Agency is not registered.
  Its mode-0600 stdout is 221 bytes at SHA-256
  `c462b0f5e6002a2ea563aaee0c965f51eeb9b7867fe3da95674298d145c252b7`;
  stderr is empty.
- The explicit config itself validates inside the production install and the
  install reaches real inference, so this is a preflight/documentation contract
  gap rather than the current Codex activation blocker.
- Tracker creation was prohibited by the historical AR-297 task. The current
  owner separately authorized the serialized write; tracker #758 is filed with
  the canonical title and epic label. The original acceptance wording is retained.
- The 2026-09-08 source slice adds
  `agency config validate --config /absolute/file.yaml`. It reads only that
  existing file through the shared link-safe identity, trusted parent namespace,
  bounded regular-file reader, bounded UTF-8 YAML parser, and the same strict
  persisted-document schema used by runtime loading. Missing, linked, special,
  oversized, malformed, and schema-invalid files are refused.
- Explicit validation does not materialize defaults or deployment overrides,
  inspect installed services/hosts, open a Store, probe providers, check secret
  availability, repair permissions, or save configuration. Empty partial documents
  retain the existing schema meaning; a YAML null is not a mapping and is refused.
  Success means document validity, not a production-ready installation.
- Bare `agency config validate` retains its existing ambient effective-config
  doctor behavior. README examples now pass the same absolute file to validation
  and installation. The parent-authorized focused wrap-up now passes 48 tests;
  no isolated acceptance verdict exists.

## Approach

Give the validation workflow one explicit, fail-closed way to validate the
same absolute config consumed by production-container installation. Keep Store
and installed-host health checks distinct from configuration structure and
secret-name validation. Update the README and parser tests together so a fresh
container does not need an already-installed default Store to preflight its
reviewed config.

## Dependencies

- ADR-0173 owns exact config binding for production-container installation.
- AR-297 retains the live four-harness acceptance package; this issue is
  recorded without expanding that package.
- Tracker creation requires separate outward-write authorization.

## Verification checkpoint

Runtime source `7de97793` and immediate ledger `a9f2fc95` freeze the implementation.
Targeted Ruff lint/format and diff checks pass. The parser-manifest golden was
mechanically regenerated without invoking test functions. The parent then
authorized only the focused pair:

```text
umask 077
python -m pytest tests/test_cli_config_validate.py tests/test_cli_parser_contract.py -q -W error
```

The first run returned 1 failed, 47 passed in 1.03s: the install-loader comparison
expected the file's Store path while the suite's normal `AGENCY_DB_PATH` override
selected its isolated Store. The test now removes only that test-local override
before comparing file-relative paths. Runtime source is unchanged. The final
run exits 0 with 48 passed in 0.65s. The canonical loader and CLI handlers run
against private fixtures, with no actual Store creation or host/provider call.

The named spine, CI, installed smoke, native/provider calls and acceptance review
have not run in this worker's slice. The parent owns coordinated main installation
and live evaluation. All five original acceptance criteria remain unchanged and
unchecked; this focused result is not an isolated acceptance verdict.

## Acceptance

- [ ] A caller can validate one explicit absolute config before any Agency
      Store or host integration exists.
- [ ] Validation checks the exact file later passed to
      `install --production-container --config` and never silently falls back
      to ambient/default state.
- [ ] README examples and CLI parser/config tests agree on the supported form.
- [ ] A fresh-container regression distinguishes config validity from Store and
      installed-host health.
- [ ] A same-repository tracker issue is created and linked after explicit
      authorization.
