---
title: "AR-337: Run the harness canary battery on any host version change"
status: open
category: roadmap
created: 2026-08-30
updated: 2026-08-30
tags: [reliability, host-integrations, canary, automation, observability]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-334-support-codex-0151-collaboration-and-hook-contract.md
  - docs/decisions/0193-admit-newer-codex-releases-under-the-newest-proven-child-contract.md
  - docs/decisions/0194-admit-host-encrypted-codex-canary-task-delivery.md
  - agency_runtime/core/canary.py
  - agency_runtime/core/doctor.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-337
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/362
depends_on: []
blocks: []
---

# AR-337: Run the harness canary battery on any host version change

## Problem

Host CLIs (codex-cli, claude-code, openclaw, hermes) auto-update on their
own cadence, and by owner directive nothing on the host is pinned: the code
accounts for new versions (ADR-0193, ADR-0194). The cost of that posture is
that contract drift lands silently and surfaces only when a live engagement
fails. AR-334 absorbed four stacked codex 0.151 drifts — a removed hook
event, changed hook identity semantics, a removed payload field, and
end-to-end channel encryption — at the price of a full forensic day across
multiple attended trust rounds. Separately, host npm self-updates have
regressed their trees to group-writable permissions three times (claude-code
twice, openclaw once), each time refusing executable-posture probes with
content-free errors until manually re-tightened. Nothing tells the operator
"a harness changed underneath you" before the next real turn pays for it.

## Approach

Trigger on change, not on a clock (owner directive 2026-08-30): keep a
per-harness version fingerprint recorded at install and after each battery
pass, and when any harness's observed version differs from its last-proven
fingerprint, run one bounded battery for that harness:

- the proven canary mode where one exists (Claude agency canary from the
  ambient shell; Codex restricted current-profile canary, whose attended
  trust survives host version changes because the launcher digest does not
  rotate with them);
- the staffing-complete ordinary check where no canary mode exists (hermes,
  openclaw, per their host contracts);
- content-free posture checks on the harness trees (the recurring
  group-writable regression), reported rather than silently remediated.

Retain receipts under the evidence namespace, record the outcome per
harness, and surface the last battery result through doctor so a failed or
stale battery is loud. The trigger and service mechanism (systemd user
timer, dashboard-service piggyback, or login-shell check) is an owner
interview before implementation, per the standing service-manager
constraint. Battery model spend stays bounded to the existing canary and
ordinary-turn budgets and runs only on change.

## Dependencies

AR-297's verified four-host baseline (closed). Owner interview for the
trigger/service mechanism. No new inference routes.

## Acceptance

- [ ] A version fingerprint per supported harness is recorded at install and
      after each battery pass.
- [ ] A battery run triggers when any harness version fingerprint changes,
      and not otherwise.
- [ ] The battery runs each host's proven canary mode where one exists and
      the staffing-complete ordinary check where none does, retaining
      receipts.
- [ ] Harness-tree posture regressions are detected and reported
      content-free.
- [ ] Doctor surfaces the last battery outcome per harness; a failed battery
      is loud.
- [ ] The trigger/service mechanism is recorded through an owner interview
      before implementation.
