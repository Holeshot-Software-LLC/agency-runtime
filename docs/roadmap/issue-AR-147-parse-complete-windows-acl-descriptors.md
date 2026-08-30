---
title: "AR-147: Parse complete Windows ACL descriptors"
status: open
category: roadmap
created: 2026-07-26
updated: 2026-07-26
tags: [security, windows, acl, filesystem-trust]
related:
  - docs/decisions/0039-fail-before-dacl-mutation-under-restricted-windows-tokens.md
  - docs/decisions/0055-freeze-executable-identity-before-launch.md
  - docs/THREAT_MODEL.md
  - agency_runtime/core/windows_acl.py
  - tests/test_windows_acl.py
supersedes: []
superseded_by: null
type: issue
epic: security
issue_id: AR-147
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-147: Parse complete Windows ACL descriptors

## Problem

The Windows filesystem-trust classifiers extracted ACEs with a flat regular
expression. A native-valid conditional ACE can contain nested parentheses, so
the expression could discard the outer access-granting ACE and classify only a
benign-looking nested string.

## Current state

The Windows SDK accepted and round-tripped a conditional full-control ACE for a
foreign SID whose quoted claim contained `(D;;;;;BU)`. Before remediation, both
the private-directory and executable-mutation classifiers omitted the outer
grant and returned trusted. This affects configuration, Store, private-root,
restricted-host, and executable namespace attestations that rely on the shared
classifier.

## Approach

Replace flat extraction with a linear, quote-aware balanced parser for the
complete DACL and every ACE. Validate the current Windows SDK ACE types, flags,
GUID shapes, conditional payload structure, and complete input consumption.
Treat conditional allow ACEs at their maximum stated rights rather than trying
to evaluate their conditions. Reject unknown or malformed shapes until they are
explicitly supported.

## Dependencies

ADR-0039 governs fail-closed Windows DACL handling. ADR-0055 requires trusted
executable parent namespaces and pre-launch revalidation.

## Acceptance

- A native-valid nested conditional foreign grant cannot disappear from any
  filesystem-trust classifier.
- The parser consumes the complete DACL and fails closed on unbalanced,
  malformed, unknown, NUL-containing, or trailing input.
- Current Windows SDK ACE types and flags are covered by focused contract tests.
- Directory, private-root, restricted-host, and executable classifications
  retain their intended safe behavior.
- The complete Python and Windows security gates pass on the integrated source.

## Implementation evidence

The shared parser now tokenizes balanced ACEs, preserves quoted parentheses,
validates complete fields, and treats untrusted conditional grants by maximum
rights. The native reproduction now returns untrusted. Focused Windows ACL,
private-path, and executable-authority verification passes 402 tests with 6
skips; Ruff, format, and diff checks pass. The complete integrated release gate
and authorized tracker creation remain pending.
