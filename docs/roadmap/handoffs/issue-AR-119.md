---
title: "AR-119 active recovery capsule"
status: active
category: roadmap
created: 2026-07-23
updated: 2026-07-28
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
  - docs/decisions/0077-prove-codex-activation-behaviorally.md
  - docs/decisions/0103-bind-named-regulated-assurance-to-typed-staffing.md
  - docs/decisions/0104-refresh-existing-codex-through-an-exact-attended-transaction.md
  - docs/roadmap/issue-AR-185-bind-codex-activation-verification.md
  - docs/roadmap/issue-AR-186-bound-delivery-to-live-demo-checkpoints.md
  - docs/roadmap/issue-AR-187-isolate-native-host-lifecycle-cwd.md
  - docs/decisions/0106-isolate-native-host-lifecycle-working-directories.md
  - docs/roadmap/issue-AR-191-support-codex-v2-hook-identity.md
  - docs/roadmap/issue-AR-192-fail-fast-on-codex-hook-trust-drift.md
  - docs/decisions/0107-resolve-updates-immutably-and-keep-application-attended.md
  - docs/worklog/2026-07-28-380f899-bind-codex-v2-native-evidence.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
branch: main
evidence_commit: 380f8992fb1d728026be82673bb966a43c148b97
minimum_ledger_commit: 9a5b37c6862461b445b7380e451ee9578438fb7b
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Bounded current-state projection for the same persistent production-readiness
task. The [canonical issue](../issue-AR-119-inference-first-workforce.md) owns
the full acceptance history.

## checkpoint

- Latest clean pushed recovery pair is AR-191 `380f899`/`9a5b37c`; branch
  `main` and `origin/main` resolve to that checkpoint, and the package plus
  Codex bundle were refreshed from it.
- The in-progress AR-192 package adds a bounded read-only Codex `hooks/list`
  preflight before model-backed current-profile activation verification.
  Seventy focused tests and two independent reviews close its scoped source
  findings; the named production spine and all routine gates pass.
- User draft `docs/analysis/2026-07-25-deep-audit-findings.md` remains unchanged
  and excluded from every commit.
- Installed plugin `0.1.0+codex.9e970ea1b470`, bundle
  `355bdf7f...b517cb12`, install ID
  `f2aad1f0-03bb-4afd-8cc9-6e94dd8eff08`, has all eight hooks enabled but
  authoritatively classified `modified`. No exhaustive workflow or hosted
  Action ran.

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
- The named fast spine passes 536 tests with 5 platform skips; all 109 dashboard
  tests and every routing/delegation evaluation gate pass. Exhaustive coverage
  and six-version compatibility now run only on explicit `workflow_dispatch`.
- One-shot application evaluation is deferred to post-production AR-178 and is
  not an AR-119/125 release gate.
- AR-180/185 isolate one nonce-bound `code-reviewer` activation measurement,
  require the existing Store, suppress roster reconciliation and hiring, and
  bind success to fresh routing, child lifecycle, finalization, header, model,
  and install evidence. Ordinary requests remain inference-governed.
- AR-191's exact V1/V2 matcher, lifecycle claim, parent-trace recovery, replay
  binding, rooted result path, and truthful projection passed the named fast
  spine plus focused adversarial review before pair `380f899`/`9a5b37c` was
  pushed and installed.
- Two post-install current-profile attempts created zero Agency Store rows and
  no activation attestation. Fresh `hooks/list` calls for both relevant working
  directories returned the same eight enabled, `modified` Agency hooks. Stored
  trust hashes belonged to the pre-refresh definitions, proving a stale TUI
  approval rather than a lease, Store, or working-directory failure.
- Codex's hash invalidation is the intended security behavior. Agency's missing
  authoritative preflight caused the avoidable model-backed delay; AR-192 owns
  that fail-fast repair and does not write trust state or use the bypass.
- AR-192 passes 70 focused tests, the 536-test named production spine with 5
  platform skips, 109 dashboard tests, documentation checks, lint/format, and
  the routing evaluation. Independent security and cross-layer reviews report
  no remaining scoped Critical, High, or Medium blocker.

## exact-blocker

- AR-192 still needs a clean substantive/ledger pair, push, and exact install.
  Then one fresh TUI must approve the settled definitions; `hooks/list` must
  report 8/8 trusted before one bounded current-profile canary. No stale or
  isolated attestation may satisfy that recheck.
- AR-161 needs owner publisher identity, authorized legal/license disposition,
  protected signing/timestamp service, signed-delivery verification, and an
  attended Windows Hello success-and-denial canary. The remote session cannot
  supply human presence or invent publisher authority.
- Automatic CI excludes exhaustive suites by design. They are optional,
  operator-requested diagnostics rather than a local completion requirement.
- `main` has neither authorized branch protection nor a repository ruleset.
  Applying required contexts is an outward setting change owned by AR-159.
- Installed-host canaries other than the bounded Codex recheck remain separate
  release evidence and are not inferred from deterministic host discovery.
- AR-119/125 still require a benchmark-valid complete outcome corpus. Malformed,
  timed-out, no-response, and unknown upstream arms remain invalid, never losses.
- Tracker creation/closure for authorization-pending AR items and other writes
  remain pending owner authorization.
- No stable Agency Runtime release exists; stable discovery remains unavailable.

## same-task-continuity

Context thresholds never create, transfer, pause, or stop this task. Continue
the same persistent goal from the clean pair through normal compaction.

## next-bounded-work-package

1. Commit the verified AR-192 substantive/ledger recovery pair.
2. Push and install that exact checkpoint, close pre-install Codex TUIs, approve
   once from a fresh TUI, and require an authoritative 8/8 trusted inspection.
3. Run one bounded current-profile activation verification and report the exact
   scoped demo verdict. Do not dispatch exhaustive or hosted diagnostics.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python -m pytest tests/test_codex_hook_trust.py tests/test_codex_activation_canary.py tests/test_host_canary.py -q -W error
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
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
