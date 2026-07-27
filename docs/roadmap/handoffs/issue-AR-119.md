---
title: "AR-119 active recovery capsule"
status: active
category: roadmap
created: 2026-07-23
updated: 2026-07-27
tags: [handoff, routing, workforce, evaluation, recovery, production-readiness]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/issue-AR-178-evaluate-one-shot-applications-post-production.md
  - docs/decisions/0102-defer-one-shot-application-evaluation.md
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/roadmap/issue-AR-159-enforce-production-branch-protection.md
  - docs/roadmap/issue-AR-160-publish-platform-honest-native-release-artifacts.md
  - docs/roadmap/issue-AR-161-sign-and-license-windows-operator-presence-delivery.md
  - docs/roadmap/issue-AR-179-fail-named-regulated-assurance-gaps-closed.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/issue-AR-183-normalize-private-posix-wheel-modes.md
  - docs/roadmap/issue-AR-184-normalize-private-posix-sdist-modes.md
  - docs/decisions/0103-bind-named-regulated-assurance-to-typed-staffing.md
  - docs/decisions/0104-refresh-existing-codex-through-an-exact-attended-transaction.md
  - docs/roadmap/issue-AR-185-bind-codex-activation-verification.md
  - docs/roadmap/issue-AR-186-bound-delivery-to-live-demo-checkpoints.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
branch: main
evidence_commit: bc6589b06c7fe10d70eee6e07e14629ebc276303
minimum_ledger_commit: c48f2bfd5335486381b41a6c23b13c481bf53882
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Bounded current-state projection for the same persistent production-readiness
task. The [canonical issue](../issue-AR-119-inference-first-workforce.md) owns
the full acceptance history.

## checkpoint

- Exact recovery pairs: AR-185 `bc6589b`/`c48f2bf`; capsule refresh `6bbf29b`/`602a817`.
- Branch `main` resolves to `c48f2bf`; `origin/main` remains `880a5ce` because
  no new push was authorized. No manual/exhaustive workflow was dispatched.
- User draft `docs/analysis/2026-07-25-deep-audit-findings.md` remains unchanged
  and excluded from every commit.
- The source candidate is not yet live-demo proven. AR-185 must be checkpointed,
  then one exact artifact must be built, installed, and exercised through a
  fresh Codex task; signing and external platform evidence remain separate.

## completed-evidence

- Deep security, optimization, traceability, and UI review is complete. No open
  Critical or High source finding remains; repaired lower findings have
  cross-layer regressions. The complete warning-strict corpus remains historical
  evidence only and is no longer a routine local/automatic gate.
- Exhaustive coverage and six-version compatibility are manual-only
  `workflow_dispatch` work. They do not run on PR/push and will not be run
  locally unless the owner explicitly asks. No hosted Actions ran here.
- A packaged dashboard authenticated and rendered all seven views and six
  evidence tabs. Desktop 1440x900 and mobile 390x844 had no horizontal overflow;
  Settings showed effective `delegation.mode=prefer`; request IDs correlated
  header-to-body; console warnings/errors were empty. The listener is stopped.
- The named fast spine passes 522 tests with 5 platform skips; all 106 dashboard
  tests and every routing/delegation evaluation gate pass. Exhaustive coverage
  and six-version compatibility now run only on explicit `workflow_dispatch`.
- ADR-0104's exact existing-install Codex refresh passes attended Windows Hello,
  atomic publication, native remove/add, and postcondition proof. New install ID
  is `7761d792-3dc3-4c92-8084-5cd524c63103`; bundle is `0c3696e1...084f3`;
  native version is `0.1.0+codex.a106953cb0c7`; the exact prior backup remains.
- AR-179 binds named standards to typed review. A fresh live route with two
  serial Codex provider calls took about 59 seconds and truthfully abstained
  when installed native capability could not satisfy eight planned units; it
  did not fabricate activation, delegation, or a contractor hire.
- One-shot application evaluation is deferred to post-production AR-178 and is
  not an AR-119/125 release gate.
- AR-180's local candidate now deterministically plans one child and proves the
  exact Codex JSONL tool call, native-hook grant provenance, child lifecycle,
  single consumption, model receipt, delegation, accepted finalization, header,
  and install-bound attestation. Ambiguous/unmatched native calls remain Codex
  scheduler decisions. Focused suites pass 33 canary/output tests, 11 schema/
  provenance migrations, dashboard API checks, and all 106 UI tests.
- Expired dashboard host inspection now neutralizes canary and maturity claims;
  the Codex card labels verified evidence as the last successful activation
  proof and renders its full content-free fingerprint without an execute button.
- Exact `cec7d0b` Windows production passed canonical build, strict Twine,
  independent verification, fresh Python 3.10 wheel/sdist installs, packaged
  smoke, `pip check`, and both bounded 8/8 all-host smokes. Wheel SHA-256 is
  `038f9c6f...ba404`; sdist SHA-256 is `3525ace3...cbfd`.
- Running the source installer from the permissive workspace correctly failed
  before mutation. The same exact installed wheel from a private environment
  passed Windows operator presence and refreshed Codex in 182.5 seconds. The
  previous bundle remains at backup `20260727T183215.488516Z`; the new plugin is
  `0.1.0+codex.92db70112a1a`, bundle `e0c19b9d...ea387`, install ID
  `fe76121b-9911-497d-b853-685d39b0e830`.
- Exactly one current-profile canary then completed in 36.9 seconds and failed
  truthfully with `route_not_found`: zero route, header, collaboration calls,
  activations, delegations, finalizations, runs, or traces. Evidence SHA-256 is
  `b5bb99e1...4750`; no attestation persisted and no retry ran.
- Exact `cec7d0b` WSL under `umask 077` advanced past AR-183's wheel repair,
  then failed closed before publication on private sdist modes. Raw evidence
  counted 559 wheel files at `0600`, 1,353 sdist files at `0600`, 40 directories
  at `0700`, and only the expected public metadata exceptions.
- AR-184 accepts only exact ordinary `0600` and directory `0700`, canonicalizes
  to `0644`/`0755`, and rejects every other permission/type. Canonicalizer 105
  and release-package 411 tests pass; two reviews found no Critical/High/Medium.
- AR-185 now routes the exact verification-only command before generic install,
  binds success to a temporally fresh exact attestation, propagates no-create/
  migrate/repair Store mode through spawned hooks, and suppresses roster
  reconciliation and gap hiring. Its focused package passed 324 tests with 6
  platform skips; 35 dedicated regressions pass in under two seconds.
- AR-186 replaces open-ended review/certification with one visible outcome,
  two bounded review passes, fast verification, and an early live-demo
  checkpoint. Exhaustive CI is optional; human steps wait without retry loops.

## exact-blocker

- Generic/missing-host installation remains unavailable, but exact existing-
  install Codex refresh is a positive prepared transaction. The global CLI and
  installed plugin are now older than the candidate. Final refresh requires
  Windows Hello; renewed terminal-TUI hook approval must occur after that exact
  refresh, followed by one new-task current-profile canary.
  Codex has no supported trust-state read API, so this remains a bounded
  inference from the evidence, not a claimed diagnosis. No preexisting
  attestation may satisfy the next recheck.
- AR-161 needs owner publisher identity, authorized legal/license disposition,
  protected signing/timestamp service, signed-delivery verification, and an
  attended Windows Hello success-and-denial canary. The remote session cannot
  supply human presence or invent publisher authority.
- Automatic CI excludes exhaustive suites by design. They are optional,
  operator-requested diagnostics rather than a local completion requirement.
- `main` has neither authorized branch protection nor a repository ruleset.
  Applying required contexts is an outward setting change owned by AR-159.
- Five installed-host canaries remain open, including the Codex recheck after
  exact-bundle terminal-TUI trust.
- AR-119/125 still require a benchmark-valid complete outcome corpus. Malformed,
  timed-out, no-response, and unknown upstream arms remain invalid, never losses.
- Tracker creation/closure for authorization-pending AR items and other writes
  remain pending owner authorization.

## same-task-continuity

Context thresholds never create, transfer, pause, or stop this task. Continue
the same persistent goal from the clean pair through normal compaction.

## next-bounded-work-package

1. Commit AR-186 and its ledger after documentation validation.
2. Build and install one exact artifact, start a fresh Codex task, run one live
   canary, and inspect the correlated UI evidence. Backlog non-demo findings.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
node --test --experimental-test-coverage --test-coverage-lines=95 --test-coverage-branches=90 --test-coverage-functions=96 tests/dashboard_ui.test.mjs
python scripts/verify_docs.py
python -m scripts.verify_distribution <candidate-directory> --expected-commit <final-head>
git diff --check
# Optional only when the owner explicitly requests exhaustive diagnostics:
python -m pytest tests -q -W error
~~~

## constraints

- Telemetry immediately before every live evaluation, benchmark corpus, or
  attended canary; create/reuse a clean checkpoint when at or below 50 percent.
- Preserve fixed 15,000 ms cold and one-call fast AR-119 controls. Never weaken
  coverage, parser, authority, timing, artifact, or asset thresholds after data.
- Do not claim Agency superiority, activation, specialist loading, model
  receipt, delegation, contractor hire, or host canary without exact evidence.
- Do not alter unknown/unattested paths or the user draft.
- No push, PR, hosted dispatch, publication, tracker mutation, tag, release,
  trust-store action, or repository setting change without authorization.
