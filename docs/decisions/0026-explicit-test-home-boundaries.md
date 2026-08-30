---
title: Require explicit home boundaries for generated-plugin tests
status: accepted
category: decisions
created: 2026-07-10
updated: 2026-07-10
tags: [testing, safety, portability, installers]
related:
  - docs/roadmap/issue-AR-09-windows-test-isolation.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0026
type: decision
deciders: []
---

# ADR-0026: Require explicit home boundaries for generated-plugin tests

## Context

Generated-plugin tests originally changed `HOME` and relied on platform home
expansion. On Windows, that did not redirect the installer away from the real
user profile, so a test run overwrote active Codex plugin files. The same suite
also depended on locale-default source encoding, POSIX path rendering, a shell
built-in presented as an executable, and an always-runnable Node binary.

## Decision

Host installation, detection, and toggle operations accept an explicit
`home_dir` boundary. Tests and smoke checks that generate host artifacts must
pass that boundary directly; changing environment variables is not an adequate
substitute. Generated text artifacts are always written as UTF-8.

Cross-platform tests compare `Path` objects and use real executable fixtures.
OpenClaw smoke validation always checks package structure and required source
tokens. It additionally runs `node --check` when Node is runnable and reports a
visible skipped syntax check when it is not.

## Consequences

- Test and smoke runs cannot redirect generated plugins into the operator's
  profile through platform-specific home discovery.
- Installer callers retain normal home discovery when no explicit boundary is
  supplied.
- Generated Python plugins import consistently across locale defaults.
- OpenClaw package structure remains testable on systems without a runnable
  Node binary, while environments with Node retain full syntax validation.
- New host-generation tests must assert that output remains below their
  allocated temporary root.

## Alternatives

- Set more Windows-specific environment variables in tests. Rejected because
  platform home resolution remains implicit and fragile.
- Monkeypatch `Path.home` or `expanduser`. Rejected because it tests patched
  globals rather than the installer's actual destination contract.
- Require Node for every smoke run. Rejected because Python-only environments
  can still validate the generated native package statically and should receive
  an explicit capability result rather than a false product failure.
- Remove generated-host smoke checks. Rejected because installer output is a
  public contract that needs direct validation.

## Provenance

AR-09 was verified with complete Windows and Ubuntu/WSL test runs. Hashes and
timestamps for the previously affected real-profile Codex plugin files remained
unchanged across the final Windows suite.
