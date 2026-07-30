---
title: "AR-204: Reconcile the README story contract"
status: in_progress
category: roadmap
created: 2026-07-30
updated: 2026-07-30
tags: [product, dashboard, cli, inference, activation, evidence, automation]
related:
  - README.md
  - docs/decisions/0117-unify-owner-control-authority.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0119-separate-native-trust-modes-from-activation-proof.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
  - docs/roadmap/issue-AR-196-authorize-prepared-dashboard-service-repair.md
  - docs/roadmap/issue-AR-197-remove-agency-owned-windows-hello.md
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/THREAT_MODEL.md
  - docs/worklog/README.md
supersedes:
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
  - docs/roadmap/issue-AR-196-authorize-prepared-dashboard-service-repair.md
superseded_by: null
type: issue
epic: product
issue_id: AR-204
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/189
depends_on: []
blocks: []
---

# AR-204: Reconcile the README story contract

## Problem

The README's short product story and several later security, routing, and live-
proof changes no longer describe one executable system. The default installer
includes the dashboard but production disables its controls; owner CLI commands
enter a verifier whose implementation was intentionally removed; `dashboard
service open` can repair a service but is classified as a presence-gated
mutation; deterministic staffing remains available despite the inference-first
claim; native hook trust is sometimes treated as activation; and response or
dashboard surfaces can look healthy without underlying execution evidence.

These contradictions have repeatedly moved the live demo boundary instead of
letting one stable README story reach proof.

## Current state

The underlying configuration writers, dashboard mutation handlers, lifecycle
transactions, inference receipts, specialist activation records, and product
trial evaluator already exist. Blanket production gates and stale governing
records prevent those pieces from forming the advertised product. The exact
installed build `5e3fab622b75f257e0ab4b74f1cc2c6d43b1d748` proves the dashboard
service is healthy and the Codex plugin is registered, but it does not prove an
authenticated rendered dashboard, a successful prompt route, specialist
injection, delegation, or workspace write.

## Approach

1. Establish one authority model: normal owner CLI commands and the
   owner-authenticated dashboard are equivalent local configuration/control
   surfaces. Hook, MCP, and broker credentials remain read-only. Exact
   confirmation, revision/CAS, dry-run, ownership, and rollback checks remain
   safety controls; they do not pretend to prove a human is present.
2. Keep the dashboard an optional component that bare `agency install` selects
   by default. `--no-dashboard` opts out. `dashboard service open` may install,
   repair, or start an owned service before opening it.
3. Require a valid inference decision for every substantive specialist-
   selection turn. Deterministic code may classify, recall, filter, and verify,
   but may not choose, rank, recommend, or hire a specialist when inference is
   unavailable or invalid.
4. Separate native host registration, trust mode, hook start, route,
   specialist injection, delegation, and finalization as distinct evidence
   stages. Support both attended native trust and an explicit autonomous mode
   for isolated/container installations without claiming bypassed hooks are
   trusted.
5. Make a missing, malformed, corrected, or evidence-mismatched response header
   a loud terminal product failure. The header is a projection of Store
   evidence, never independent proof of execution.
6. Require dashboard proof to authenticate, render the packaged application,
   read configuration, perform a reversible owner configuration mutation, and
   restore the prior value. HTTP reachability alone is service health only.
7. Keep tests as the shared runtime backbone and add host-adapter contract tests
   plus bounded live canaries for the remaining harness-specific behavior.

## Dependencies

ADR-0117 owns local owner authority and default-suite semantics. ADR-0118 owns
inference-only staffing. ADR-0119 owns attended and autonomous native trust
modes and separates trust from activation evidence. AR-119 retains the complete
workforce implementation, while AR-203 retains exact Codex workspace and live
product proof.

## Implementation evidence

Commit `ffec102` removes the retired shared presence dispatcher and parser
metadata, restores prepared roster rollback to normal owner authority while
retaining its exact Store/generation/revision revalidation, and keeps model-
facing native controls read-only under an explicit `owner_control_required`
result. The obsolete AR-143 and AR-196 contracts are now marked `wont_do` and
superseded by this issue rather than left as apparently active requirements.

Focused verification passed 708 tests with one platform skip across owner CLI,
parser, install/uninstall, Codex activation-shape, prepared transaction,
dashboard-service recovery, host-control, security-turn, native-installer,
upgrade, and release-contract boundaries. Ruff, formatting, metadata, policy,
documentation, worklog-currentness, and staged whitespace checks passed.

Commit `c8c8020` restores the owner dashboard surface end to end. The owner
bearer now reaches the existing confirmation- and revision-bound mutation
handlers; the broker bearer receives `403 owner control required` before its
bounded request body can reach a handler. The packaged client again exposes
configuration, maintenance, master, host, roster, workforce, and hiring
controls while retaining current request correlation, lifecycle cancellation,
bounded collections, activation disclosure, and stale-Store interlocks.

The complete dashboard client suite passed 110 tests, including exact request
bodies for all eight mutation endpoints. The dashboard authentication and
server suite passed 145 tests with three platform skips. The restored HTML is
byte-identical to the last owner-capable pre-regression Git blob, so no
display-truncated or hand-reconstructed shell content remains.

## Acceptance

- [x] Owner CLI configuration/control commands dispatch without the retired
  Agency-owned human-presence verifier.
- [x] The owner dashboard exposes the same supported configuration and runtime
  controls as the CLI, while broker, hook, and MCP identities cannot mutate.
- [x] `agency dashboard service open` can ensure an owned default-installed
  service is healthy and open it without an unavailable-presence error.
- [x] Bare install selects the supported dashboard by default and
  `--no-dashboard` remains a complete opt-out.
- [ ] A substantive turn without a valid inference provider decision fails
  visibly and selects, recommends, delegates, and hires no specialist.
- [ ] Deterministic recall and validation cannot become an online or offline
  specialist decider.
- [ ] Attended and explicit autonomous native-install modes are both covered by
  the shared adapter contract; trust status is never reported as activation.
- [ ] Current Codex carries the exact activation contract into hook processes
  and proves hook start, route, exact specialist injection, and native child
  lifecycle separately.
- [ ] Missing, malformed, corrected, or evidence-mismatched headers cannot be
  accepted as a successful turn; success requires correction count zero.
- [ ] Dashboard success proves automatic token authentication, packaged render,
  configuration read, one reversible owner write, and exact restoration.
- [ ] README, troubleshooting, threat model, roadmap, decisions, and tests state
  the same contract without stale operator-presence or offline-selection text.
- [ ] The named fast verification spine passes before the live demo resumes.
- [ ] One exact installed build completes the README product trial with a real
  inferred specialist team, actual delegation where planned, a workspace
  artifact, and zero response corrections.
