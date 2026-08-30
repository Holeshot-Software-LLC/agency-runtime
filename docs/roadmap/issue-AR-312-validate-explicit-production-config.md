---
title: "AR-312: Validate an explicit production config before installation"
status: open
category: roadmap
created: 2026-08-26
updated: 2026-08-26
tags: [configuration, documentation, installation, production-container]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - README.md
  - agency_runtime/cli/parser.py
  - agency_runtime/cli/config_commands.py
  - tests/test_cli_parser_contract.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: install
issue_id: AR-312
priority: p1
tracker_url: null
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
- Tracker creation is prohibited by the active AR-297 task.

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
