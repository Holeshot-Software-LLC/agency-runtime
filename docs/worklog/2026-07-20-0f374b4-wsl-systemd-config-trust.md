---
title: "Preserve WSL systemd dashboard configuration trust"
status: active
category: worklog
created: 2026-07-20
updated: 2026-07-20
tags: [dashboard, systemd, wsl, security, portability]
related:
  - docs/roadmap/issue-AR-110-preserve-wsl-systemd-service-trust.md
  - docs/decisions/0075-preserve-config-trust-under-wsl-systemd.md
  - docs/THREAT_MODEL.md
  - docs/TROUBLESHOOTING.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 0f374b4142cf3191d3127bc8d8983d84c35be4ac
short: 0f374b4
date: 2026-07-20
pr: "https://github.com/Holeshot-Software-LLC/agency-runtime/pull/114"
related_issues:
  - docs/roadmap/issue-AR-110-preserve-wsl-systemd-service-trust.md
---

# Worklog detail: Preserve WSL systemd dashboard configuration trust

## Purpose

Make the optional dashboard user service start safely on WSL without weakening
the shared configuration namespace boundary or reducing normal-Linux hardening.

## Approach

Generate the systemd unit from bounded kernel-release evidence. A positive WSL
marker omits only `PrivateTmp`; normal Linux and every missing, malformed,
oversized, or unreadable result retain it. Keep `NoNewPrivileges`, `UMask=0077`,
restricted address families, loopback authentication, owner-private storage,
and the exact same fail-closed configuration ancestor checks.

Record the narrow portability/security decision in ADR-0075 and expose the
tradeoff in the README, threat model, and troubleshooting guide.

## Challenges encountered

The exact merged wheel started manually in WSL, while the systemd user service
failed readiness because its worker rejected the configuration ancestor chain.
Isolating the unit properties with transient services proved that
`PrivateTmp=true` alone caused root-owned ancestors to appear as overflow UID
`65534`. Disabling other hardening controls did not affect the failure.

The main-branch workflow also correctly detected that merge commit `e6e1b25`
could not have appeared in the pre-merge ledger. This ledger commit records that
faithful merge subject alongside the AR-110 implementation.

## Decisions and alternatives

ADR-0075 rejects accepting overflow UIDs in the shared trust predicate and
rejects removing `PrivateTmp` from all Linux units. Environment variables were
also rejected as WSL identity because a systemd manager can have a different
environment from the installer.

## Verification

- Focused dashboard service and namespace suites: 261 passed.
- Changed systemd module: 106 statements and 28 branches, 100.00% covered.
- Ruff lint and format checks passed for the changed Python files.
- Markdown front matter and generated policy availability checks passed.

## Follow-ups

Build an exact committed wheel, exercise real WSL `systemd --user`
install/start/health/uninstall, and complete the full local and hosted gates
before closing AR-110.
