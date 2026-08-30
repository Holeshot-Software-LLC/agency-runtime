---
title: "Redact failed dashboard manager probe output"
status: active
category: worklog
created: 2026-07-19
updated: 2026-07-19
tags: [dashboard, systemd, security, redaction]
related:
  - docs/roadmap/issue-AR-38-dashboard-service-environment-durability.md
  - docs/decisions/0006-config-first-redacted-configuration.md
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 3f9eb96
short: 3f9eb96
date: 2026-07-19
pr: "https://github.com/Holeshot-Software-LLC/agency-runtime/pull/104"
related_issues:
  - docs/roadmap/issue-AR-38-dashboard-service-environment-durability.md
---

# Worklog detail: Redact failed dashboard manager probe output

## Purpose

Prevent a failed Linux user-manager environment probe from copying secret or
configuration values from stdout or stderr into public dashboard-service plans.

## Approach

Give command results an explicit public-projection option that suppresses
failure streams. Linux manager plans use that projection, replace the detail
with a fixed redacted error, and expose only allowlisted runtime or configured
credential variable names parsed from either stream.

## Challenges encountered

The success path already parsed `systemctl --user show-environment` into names
only. The unavailable-manager path reused the generic command projection,
however, which selected raw stderr or stdout as its public error detail. A
failed systemd command or intermediary can echo the very values the success
path intentionally removes.

## Decisions and alternatives

- Retain the fixed command and integer return code for diagnosis.
- Parse only exact allowlisted assignment names; never publish values or
  unrelated output.
- Redact both streams, not only stderr, because either can carry values.
- Keep generic command failure details for non-environment probes.

## Verification

- `90 passed` in the focused dashboard-service suite.
- `399 passed, 2 skipped` in the combined dashboard-service, MCP, and
  configuration identity regression set.
- Adversarial tests placed distinct secrets in stdout, stderr, unrelated
  assignments, and prose, then proved none reached serialized plan output.
- Repository-wide Python Ruff check and format check passed.
- `git diff --check` passed.

## Follow-ups

None.
