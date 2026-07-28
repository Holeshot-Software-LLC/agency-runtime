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
evidence_commit: 8fdc186fdc86958d89ff6bc2e585d58fadc71737
minimum_ledger_commit: 1a58e5e307237e1549c96c03f1200b4531c57cd5
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Bounded current-state projection for the same persistent production-readiness
task. The [canonical issue](../issue-AR-119-inference-first-workforce.md) owns
the full acceptance history.

## checkpoint

- Latest clean recovery pair is AR-180 `8fdc186`/`1a58e5e`; its exact Windows
  wheel/source pair and fresh installed-package checks are verified.
- Branch `main` resolves to `1a58e5e`; `origin/main` remains `194d697`. The user
  authorized pushing the verified result. No manual/exhaustive workflow was
  dispatched.
- User draft `docs/analysis/2026-07-25-deep-audit-findings.md` remains unchanged
  and excluded from every commit.
- Exact checkpoint `194d697` is installed as plugin
  `0.1.0+codex.edc73d72c476`; all eight hooks are currently trusted for that
  exact launcher. The source correction is intentionally not installed while
  the operator is remote because its changed launcher will need attended trust.

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
- Exact `194d697` is installed. A fresh Codex process now reports all eight
  current plugin hooks enabled and trusted. A zero-token no-bypass startup probe
  persisted the nonce-bound one-unit `code-reviewer` route and ready preflight;
  one bounded live activation proof is the remaining AR-180 gate.
- The 02:47 UTC bounded canary again proved trusted routing and one exact
  `code-reviewer` unit, then failed truthfully with zero native activation
  evidence. Controlled native Codex runs isolated the cause: V2 delegation
  with `--ephemeral` could not recover its parent history and failed after about
  73.5 seconds, while the non-ephemeral form completed in about 13.5 seconds and
  persisted one spawn, one wait, one child edge, and child completion.
- The `1a58e5e` candidate makes exact rollout reconciliation an explicit
  activation-only contract. It removes `--ephemeral`, forces V2, uses
  `fork_turns="none"`, and validates owner-private bounded parent/child rollouts
  without retaining prompt or reasoning content. Deferred product trials keep
  their custom response contract; native-only remains ephemeral and no-tool.
  Its 7,528,969-byte wheel (`e6a94cd9...e43bf5`) and 18,402,728-byte sdist
  (`7d7d003e...a2209`) pass strict Twine and independent exact-commit
  verification. Fresh Python 3.13 install, dependency checks, all 8 packaged
  smoke checks, the installed option split, and every offline routing gate pass.
- AR-185 now routes the exact verification-only command before generic install,
  binds success to a temporally fresh exact attestation, propagates no-create/
  migrate/repair Store mode through spawned hooks, and suppresses roster
  reconciliation and gap hiring. Its focused package passed 324 tests with 6
  platform skips; 35 dedicated regressions pass in under two seconds.
- AR-186 replaces open-ended review/certification with one visible outcome,
  two bounded review passes, fast verification, and an early live-demo
  checkpoint. Exhaustive CI is optional; human steps wait without retry loops.

## exact-blocker

- The installed `194d697` candidate has current eight-hook trust and a successful
  zero-token no-bypass routing probe, but it predates the persisted-parent fix.
  Exact packaged candidate `1a58e5e` is ready; after the operator returns it
  needs one attended refresh, changed-hook trust, and fresh current-profile
  canary. No preexisting attestation may satisfy that recheck.
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

1. After the operator returns, install exact candidate `1a58e5e` through one
   attended refresh, then trust the changed eight-hook inventory and run one
   bounded current-profile activation verification.
2. If it passes, record the exact attestation and demo verdict. If it fails,
   preserve the failure and fix only the smallest evidenced defect before one
   more bounded attempt.

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
