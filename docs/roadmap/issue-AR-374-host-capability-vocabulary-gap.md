---
title: "AR-374: Most of the roster is permanently ineligible because hosts prove 9 capabilities and the roster demands 246"
status: open
category: roadmap
created: 2026-09-02
updated: 2026-09-02
tags: [workforce, eligibility, host-capabilities, staffing]
related:
  - docs/roadmap/issue-AR-373-recruiter-evidence-vocabulary.md
  - docs/roadmap/issue-AR-336-requalify-the-recruiter-route-for-ordinary-tasks.md
  - docs/roadmap/issue-AR-120-normalized-workforce-recruitment-index.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-374
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/540
depends_on: []
blocks: []
---

# AR-374: Most of the roster is permanently ineligible because hosts prove 9 capabilities and the roster demands 246

## Problem

`_NATIVE_HOST_CAPABILITIES` (`core/host_capabilities.py:325`) grants every
execution host the same fixed nine capabilities:

    code-execution, native-delegation, package-management, repository-read,
    repository-write, runtime-evidence, shell-execution, source-control,
    test-execution

The governed roster demands **246 distinct tool classes**. Measured
2026-09-02 against the shipped 291-worker index:

| | count |
|---|---|
| workers eligible on tools | 72 |
| workers requiring a capability no host can prove | **219 (75%)** |

Those 219 are not "hard to staff". They are unstaffable by construction:
`agent_tools_missing` fires however good the plan and however willing the
recruiter, because no host will ever prove the capability.

Top blockers: `browser-interaction` (55 workers), `web-research` (43),
`analytics-reader` (27), `database-access` (19), `current-legal-research`
(13), `spreadsheet-access` (12), `monitoring-observability` (11),
`crm-reader` (11).

The install case that surfaced this:

| worker | status |
|---|---|
| `cross-platform-installer-engineer` | eligible |
| `software-test-engineer` | eligible |
| `devops-automator` | blocked: `ci-runner`, `infrastructure-tooling` |
| `developer-tooling-engineer` | blocked: `cross-platform-test-host` |
| `desktop-app-engineer` | blocked: `build-toolchain`, `desktop-test-host` |

## Current state

Found while chasing AR-373. With only the host's nine proven, the recruiter
abstained with `no_safe_sufficient_team` and the receipt carried
`agent_tools_missing`. Proving the demanded tools in a probe context let the
recruiter's nomination through immediately, which isolates this as the gate.

The abstention is *correct* behaviour: Agency must not staff a specialist
whose required tools the host has not proven. The defect is the vocabulary
gap on either side of that rule, not the rule.

## Approach

Not yet decided; the first task is to establish which of these is true,
because they need opposite fixes:

1. **The roster over-declares.** Cards were audited from an upstream catalog
   that assumed richer tooling, and many `tool_classes` entries are
   aspirational rather than genuinely required to do the work. Then the fix
   is in the audit: require a card to justify each tool class, and drop the
   ones it does not need.
2. **The host under-declares.** Hosts really can do more than nine things —
   a host with web access can do `web-research`, one with a browser tool can
   do `browser-interaction` — and the fixed nine is a stub that never grew.
   Then the fix is capability detection per host, proven rather than assumed.
3. **The vocabulary is mis-scaled.** 246 tool classes for a 291-worker roster
   is close to one per worker, which suggests the axis is being used to
   describe specialisms rather than provable host facilities. Then the fix is
   to collapse the vocabulary to what a host can actually prove.

The measurements above do not settle it. Expect the answer to be a mix, and
expect (3) to matter most: an axis that cannot be proven is not an
eligibility gate, it is a wish.

## Dependencies

- AR-373 removed the contract failure that masked this; the recruiter now
  reaches a real judgement, which is what made this visible.

## Acceptance

- [ ] The share of the roster that is structurally unstaffable is stated,
      per host, with the tool classes responsible.
- [ ] Each of the three hypotheses above is confirmed or rejected against
      evidence, not assumed.
- [ ] An ordinary install request staffs a specialist on this installation,
      or the reason it should not is recorded.
- [ ] Whatever the fix, a regression test pins that the capabilities a host
      proves and the tool classes the roster demands cannot silently drift
      apart again.
