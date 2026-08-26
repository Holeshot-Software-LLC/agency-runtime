---
title: "AR-301: Support private non-root systemd dashboard namespaces"
status: open
category: roadmap
created: 2026-08-26
updated: 2026-08-26
tags: [dashboard, systemd, linux, security, installation]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0176-use-owner-runtime-temp-for-nonroot-user-services.md
  - agency_runtime/core/dashboard_service_systemd.py
  - agency_runtime/core/configuration_persistence.py
  - tests/test_dashboard_systemd_namespace_security.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-301
priority: p0
tracker_url: null
depends_on: []
blocks: [AR-297]
---

# AR-301: Support private non-root systemd dashboard namespaces

## Problem

The production Linux dashboard service cannot start for an ordinary non-root
user when the shipped systemd hardening enables `PrivateTmp=true`. Inside that
unit, trusted root-owned ancestors including `/` and `/home` are reported with
UID 65534. The configuration namespace validator accepts only root or the
current account, so it correctly fails closed with `configuration parent
permits cross-account path substitution`. The installer then rolls back the
service transaction.

## Current state

- The exact AR-297 host config is owner-private, mode 0600, and byte-identical
  to the independently validated container config.
- The exact dashboard worker remains healthy for a bounded foreground run
  outside the systemd hardening namespace.
- A diagnostic transient unit with the shipped hardening reproduces UID 65534
  for trusted root ancestors and the same validation refusal.
- The dedicated root-user systemd container passes, which does not prove the
  ordinary non-root host path.
- No ownership check, service hardening, or namespace guard was bypassed.
- Tracker creation is prohibited by the active AR-297 task, so tracker parity
  is an explicit unresolved gate.

## Approach

ADR-0176 selects a service-isolation adjustment because the in-namespace UID
65534 observation cannot distinguish remapped root from a genuine overflow
owner. Non-root units use a systemd-created mode-0700 owner runtime directory
for `TMPDIR`, `TMP`, and `TEMP` without enabling the private user namespace.
Root non-WSL managers retain `PrivateTmp=true`. Do not accept arbitrary UID
65534 paths and do not weaken ordinary configuration namespace validation.

Add regressions for an ordinary non-root user manager, the remapped-root case,
genuine untrusted UID 65534 parents, rollback, and the existing WSL exception.
Then prove a real owner-scoped systemd service reaches readiness and remains
authenticated on loopback.

## Dependencies

- AR-297 owns the exact host-install and authenticated dashboard evidence.
- Existing configuration namespace validation owns the cross-account path
  substitution boundary.
- Tracker creation requires separate outward-write authorization.

## Acceptance

- [ ] A normal non-root Linux systemd user service starts with the shipped
      hardening and an owner-private exact config.
- [x] The non-root unit avoids ambiguous root remapping while a genuinely
      untrusted UID 65534 parent remains rejected.
- [x] Existing ownership, substitution, rollback, WSL, and hardening tests stay
      fail-closed and pass with warnings treated as errors.
- [ ] Authenticated loopback health succeeds from the installed service while
      unauthenticated access is rejected.
- [ ] A same-repository tracker issue is created and linked after explicit
      authorization.

## Verification evidence

The final AR-297 host check did not mutate or retry this transaction. The
unrelated OpenClaw user service remained active with authenticated RPC, proving
that the user manager itself is healthy; it does not explain away the dashboard
namespace refusal. The dedicated root-user dashboard proof container was
removed after its evidence was captured, its image was retained, and the normal
non-root dashboard acceptance items remain open without a bypass.

The implementation leaves configuration trust unchanged. A non-root unit now
sets `PrivateTmp=false`, asks systemd for `agency-runtime-dashboard` at mode
0700, and binds all three standard temporary-directory variables to that
owner-runtime path; root non-WSL units retain `PrivateTmp=true`. Focused Linux
service/configuration tests pass 128 with one skip, and the broader AR-301/302
set passes 241 with two Windows-only tests deselected on Linux, all under a
caller umask of 0002 and `-W error`. The remaining acceptance requires the real
installed non-root service and authenticated loopback probe.
