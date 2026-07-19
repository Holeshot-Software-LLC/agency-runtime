---
title: "Validate injected MCP Store identities"
status: active
category: worklog
created: 2026-07-19
updated: 2026-07-19
tags: [mcp, configuration, sqlite, security, lifecycle]
related:
  - docs/roadmap/issue-AR-47-freeze-store-config-identity-at-construction.md
  - docs/roadmap/issue-AR-48-enforce-strict-schema-on-config-read.md
  - docs/decisions/0006-config-first-redacted-configuration.md
  - docs/decisions/0012-canonical-sqlite-audit-store.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 22434e8
short: 22434e8
date: 2026-07-19
pr: "https://github.com/Holeshot-Software-LLC/agency-runtime/pull/104"
related_issues:
  - docs/roadmap/issue-AR-47-freeze-store-config-identity-at-construction.md
  - docs/roadmap/issue-AR-48-enforce-strict-schema-on-config-read.md
---

# Worklog detail: Validate injected MCP Store identities

## Purpose

Prevent an MCP server from silently ignoring explicit configuration or database
paths when it is also given an already initialized Store, while preserving the
global master switch's work-free disabled boundary.

## Approach

Compare redundant MCP `config_path` and `db_path` arguments to the Store's full
frozen binding contract using lexical canonical identities only. The constructor
performs no file or database I/O. It rejects mismatches, public identity
tampering, partial bindings, and legacy Store-like objects whose mixed explicit
form cannot be verified.

Move the Store's public-versus-frozen configuration-path comparison ahead of
`load_config`, and load only from the confirmed frozen path. Keep the existing
compatibility path for unbound Store-like objects when no redundant path is
supplied.

Reconcile AR-48's roadmap language with the implemented fail-closed schema:
missing and whitespace-only documents use defaults, while explicit YAML `null`
is a non-mapping root and is rejected.

## Challenges encountered

The first repair validated only `config_path` and reused the live binding check
inside the constructor. Adversarial review showed that this still ignored
`db_path`, performed pre-master configuration I/O, could read a tampered public
path before rejection, and accepted a partial binding that the enabled path
would later reject. The final design separates pure identity validation from
live configuration validation.

## Decisions and alternatives

- Do not open a redundant path merely to decide whether it matches.
- Validate both configuration and database identities as one runtime contract.
- Reject unverifiable mixed legacy forms; retain legacy compatibility when no
  redundant path is supplied.
- Compare public and frozen identities before any live reload.
- Keep explicit YAML null fail-closed instead of weakening the typed root.

## Verification

- `345 passed, 2 skipped` across MCP, configuration, and global master-switch
  suites after the full identity redesign.
- `145 passed, 1 skipped` in the final focused Store-binding, tampering, and
  off-mode regression set.
- Independent senior/security re-review found no remaining actionable issue
  after the full frozen-binding check was added.
- Ruff check, Ruff format check, and `git diff --check` passed.

## Follow-ups

None.
