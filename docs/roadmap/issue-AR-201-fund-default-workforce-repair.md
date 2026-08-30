---
title: "AR-201: Fund the default workforce repair path"
status: in_progress
category: roadmap
created: 2026-07-30
updated: 2026-07-30
tags: [workforce, inference, configuration, budgets, routing, regression, multi-harness]
related:
  - docs/decisions/0114-fund-one-default-workforce-semantic-repair.md
  - docs/roadmap/issue-AR-200-diagnosable-decision-conformance.md
  - docs/roadmap/handoffs/issue-AR-201.md
  - docs/roadmap/issue-AR-202-make-recruiter-repair-converge.md
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: routing
issue_id: AR-201
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/180
depends_on: [AR-119]
blocks: [AR-200, AR-202, AR-203]
---

# AR-201: Fund the default workforce repair path

## Problem

Configured fast mode always spends one provider call on planning and one on
recruitment. Its explicit semantic-validation contract allows one bounded retry,
but the installed default total budget was two calls. AR-200 trial
`ar200-57c34e6-ordinary-03` therefore accepted the planner, rejected the
recruiter contract, and stopped with `workforce_call_budget_exhausted` before
the promised repair could run.

Fresh bundled configuration was even less coherent: it declared a one-call
fast budget while the Python dataclass fallback declared two. A green repair
test had supplied an explicit three-call balanced budget, so it did not prove
the production default path.

## Current state

The exact production sequence now has a regression that failed first with the
two-call default and passed after the repair. Fresh bundled, dataclass, loader,
and partial-document validation defaults all use three fast calls: planner,
recruiter, and one bounded semantic repair. Balanced and strict budgets remain
four and five.

Explicit persisted values remain operator-owned. Loading an older explicit
two-call value still yields two, so an update does not silently enlarge a
deliberately constrained provider budget. Generated hook timeout calculation
already derives from the effective configured call budget; a new test proves
the default three-call path receives the corresponding timeout.

The full focused inference, configuration, installer, and conformance suite
passes 234 tests with 1 skip. The isolated decision gate proves a green
baseline and kills all 10 curated mutations with zero survivors or invalid
results while leaving the source checkout unchanged. The named Python spine
passes 665 tests with 6 skips, all 109 dashboard UI tests pass, 603 Python files
pass Ruff format, and 542 Markdown files validate. Every routing, policy,
delegation, CLI-startup, latency, and 263/1,000/10,000-worker scale gate passes;
routing p95 is 4.328 ms and cache-hit p95 is 1.311 ms. Those deterministic
gates established the exact merge candidate later installed below.

PR 181 merged as exact revision
`ed4450e9cb55c656d70c94026b22f6caebbd45e1`, installed as build
`0.1.0+ged4450e9cb55`. The operator deliberately set the persisted fast budget
to three before Codex and ZCode refresh. Codex bundle
`0.1.0+codex.2743f1b2ec20` uses 185-second hook timeouts and ZCode uses
185000-millisecond timeouts.

The one bounded trial `ar201-ed4450e-ordinary-01` is terminal `NO-GO`. It
proves the repair call is now reachable: the planner applied, then recruiter
calls two and three were both rejected as
`provider_response_contract_invalid`. No specialist was selected, loaded, or
delegated; no finalization was accepted; correction count is null; and the
workspace failed all five checks. AR-202 owns recruiter convergence. AR-203
owns the product evaluator's wrong evidence projection and unproven effective
workspace-write policy.

## Approach

1. Align every fresh fast-mode default at three total workforce calls.
2. Preserve persisted explicit values as user-owned opt-outs; do not infer that
   an existing value of one or two was generated rather than chosen.
3. Prove the live failure sequence with a valid planner response, invalid
   recruiter contract, and accepted recruiter repair under default fast mode.
4. Bind generated hook timeouts to the enlarged fresh default.
5. Add a curated mutation that lowers the Python fast default back to two and
   require the exact production-sequence regression to kill it.
6. Run the named fast gate and merge. Install the exact tool revision, set this
   machine's explicit older override to three, refresh Codex and ZCode so their
   generated timeout covers that effective budget, then run one bounded canary.

## Dependencies

AR-119 owns inference-first selection. AR-200 supplied the terminal live trace
and remains blocked on a successful ordinary workforce proof. ADR-0114 governs
the default and explicit-override boundary.

## Acceptance

- [x] Fresh bundled, dataclass, loader, and partial-validation defaults use a
  three-call fast workforce budget.
- [x] An explicit older one- or two-call value remains authoritative and is not
  silently migrated.
- [x] Default fast mode accepts planner plus recruiter plus one corrected
  recruiter response and records three provider attempts.
- [x] Generated host timeout calculation covers the three-call default.
- [x] The curated decision-conformance manifest reverses this default and names
  the exact regression that must kill it.
- [x] Focused tests, the 10-mutation proof, and the named fast production gate
  pass on the exact source revision.
- [x] The PR is merged and the exact tool revision is installed.
- [x] This machine's explicit older fast budget is deliberately set to three
  before Codex and ZCode are refreshed from the exact tool revision.
- [x] The refreshed Codex and ZCode bundles use timeout evidence derived from
  the effective three-call budget.
- [ ] **codex**: One fresh exact-build product trial passes with zero corrections.
- [ ] **zcode**: One fresh exact-build product trial passes with zero corrections.
- [ ] **claude**: One fresh exact-build product trial passes with zero corrections.
- [ ] **hermes**: One fresh exact-build product trial passes with zero corrections.
- [ ] **openclaw**: One fresh exact-build product trial passes with zero corrections.
- [x] The local evidence page and tracker contain the terminal scoped verdict.

## Harness scope

This issue's concept applies across all supported execution hosts (codex,
claude, zcode, hermes, openclaw). The shared code path lives in
`agency_runtime/core/workforce/inference.py` and the fast-mode budget
configuration consumed by every host, while per-host trial execution is routed
through `agency_runtime/adapters/hooks.py` (codex/claude/zcode via HookBridge)
and `agency_runtime/adapters/base.py` (hermes/openclaw via BaseAdapter). Each
host's live-trial checkbox above is independent.
