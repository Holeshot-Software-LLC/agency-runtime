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
  - docs/decisions/0103-bind-named-regulated-assurance-to-typed-staffing.md
  - docs/decisions/0104-refresh-existing-codex-through-an-exact-attended-transaction.md
  - docs/roadmap/issue-AR-185-bind-codex-activation-verification.md
  - docs/roadmap/issue-AR-186-bound-delivery-to-live-demo-checkpoints.md
  - docs/roadmap/issue-AR-187-isolate-native-host-lifecycle-cwd.md
  - docs/decisions/0106-isolate-native-host-lifecycle-working-directories.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
branch: main
evidence_commit: 5d390424eeb68fe94b3cf713c85a886fa196eefc
minimum_ledger_commit: 5a26dbe19ebb967f38440552b28b11635a4c5598
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Bounded current-state projection for the same persistent production-readiness
task. The [canonical issue](../issue-AR-119-inference-first-workforce.md) owns
the full acceptance history.

## checkpoint

- Latest clean recovery pair is AR-180 `5d39042`/`5a26dbe`; the deterministic
  activation-route implementation is the next bounded substantive checkpoint.
- Branch `main` resolves to `5a26dbe`; `origin/main` remains `bef478a`. The user
  authorized pushing the verified result. No manual/exhaustive workflow was
  dispatched.
- User draft `docs/analysis/2026-07-25-deep-audit-findings.md` remains unchanged
  and excluded from every commit.
- Exact checkpoint `c71ce0a` is installed as plugin
  `0.1.0+codex.4bced9ea8e5a`; its attended refresh and all eight hook approvals
  succeeded. Its live canary reached Agency but planner fanout produced two
  units, so activation correctly remained unverified.

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
- AR-180 now isolates the exact activation measurement from semantic-planner
  variance with a closed native-verified, nonce-bound one-unit fixture. It
  remains read-only, no-tool, uncached, and fails closed on roster or authority
  drift; ordinary requests remain inference-governed. The route passes durable
  preflight replay and preserves distinct Store provenance. The existing
  hook/proof chain still validates exact JSONL spawn/wait topology, native-hook
  grants, single consumption, child lifecycle, model receipt, finalization,
  header, and install-bound attestation.
- Expired dashboard host inspection now neutralizes canary and maturity claims;
  the Codex card labels verified evidence as the last successful activation
  proof and renders its full content-free fingerprint without an execute button.
- AR-187 isolates native lifecycle commands from the ambient CWD without
  relaxing repository-ancestor exclusion. Its 98 focused tests pass with one
  platform skip. Exact `f3e8961` canonical wheel/source verification and strict
  Twine pass; wheel SHA-256 is `395488c8...041fa`, sdist SHA-256 is
  `5993c6a6...e329b`, and the installed uv receipt points to that exact wheel.
- Two subsequent attended exact refreshes passed Windows owner presence and the
  user approved each generated eight-hook inventory in the terminal TUI. Their
  fresh failures were parent-only execution and then two-unit planner fanout,
  not trust-store bypass or stale evidence reuse.
- AR-185 now routes the exact verification-only command before generic install,
  binds success to a temporally fresh exact attestation, propagates no-create/
  migrate/repair Store mode through spawned hooks, and suppresses roster
  reconciliation and gap hiring. Its focused package passed 324 tests with 6
  platform skips; 35 dedicated regressions pass in under two seconds.
- AR-186 replaces open-ended review/certification with one visible outcome,
  two bounded review passes, fast verification, and an early live-demo
  checkpoint. Exhaustive CI is optional; human steps wait without retry loops.

## exact-blocker

- The deterministic activation-route candidate still needs a clean commit,
  exact artifact build/install, one attended Codex refresh, renewed terminal-TUI
  hook approval, and one fresh bounded current-profile canary. No preexisting
  attestation may satisfy that recheck.
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

## same-task-continuity

Context thresholds never create, transfer, pause, or stop this task. Continue
the same persistent goal from the clean pair through normal compaction.

## next-bounded-work-package

1. Commit and ledger the deterministic activation route after focused checks;
   build and install that exact clean checkpoint.
2. Run one attended Codex refresh, renew the generated hook inventory trust,
   then run one bounded current-profile activation verification and inspect its
   correlated read-only evidence.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python -m pytest tests/test_activation_canary_contract.py tests/test_codex_activation_canary.py tests/test_codex_activation_verification.py -q -W error
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
