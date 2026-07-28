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
  - docs/decisions/0103-bind-named-regulated-assurance-to-typed-staffing.md
  - docs/decisions/0104-refresh-existing-codex-through-an-exact-attended-transaction.md
  - docs/roadmap/issue-AR-185-bind-codex-activation-verification.md
  - docs/roadmap/issue-AR-186-bound-delivery-to-live-demo-checkpoints.md
  - docs/roadmap/issue-AR-187-isolate-native-host-lifecycle-cwd.md
  - docs/decisions/0106-isolate-native-host-lifecycle-working-directories.md
  - docs/roadmap/issue-AR-191-support-codex-v2-hook-identity.md
  - docs/decisions/0107-resolve-updates-immutably-and-keep-application-attended.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
branch: main
evidence_commit: 8c7d8df44aa35d4bb7ab7698abaf0f7b2a93e47b
minimum_ledger_commit: 50d0b2e249fa38d42109670804d30e7e4119041f
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Bounded current-state projection for the same persistent production-readiness
task. The [canonical issue](../issue-AR-119-inference-first-workforce.md) owns
the full acceptance history.

## checkpoint

- Latest clean recovery pair is AR-190 `8c7d8df`/`50d0b2e`; branch `main`,
  `origin/main`, and the installed package all resolve to that checkpoint.
- The AR-191 recovery candidate repairs the exact Codex V2 hook identity,
  child-turn correlation, and truthful canary projection exposed by one bounded
  live run. Focused live-shape regressions and targeted lint/format pass.
- User draft `docs/analysis/2026-07-25-deep-audit-findings.md` remains unchanged
  and excluded from every commit.
- Installed plugin `0.1.0+codex.4b511d9c4535`, bundle `c792b4bc...1cff1ae`,
  install ID `5e9f9145-1dfc-494a-8580-f9211eef8ec7`, has all eight hooks
  enabled and trusted. No manual/exhaustive workflow or hosted Action ran.

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
- AR-180 now isolates the exact activation measurement from semantic-planner
  variance with a closed native-verified, nonce-bound one-unit fixture. It
  remains read-only, no-tool, uncached, and fails closed on roster or authority
  drift; ordinary requests remain inference-governed. The route passes durable
  preflight replay and preserves distinct Store provenance. The existing
  hook/proof chain still validates exact JSONL spawn/wait topology, native-hook
  grants, single consumption, child lifecycle, model receipt, finalization,
  header, and install-bound attestation.
- AR-185 now routes the exact verification-only command before generic install,
  binds success to a temporally fresh exact attestation, propagates no-create/
  migrate/repair Store mode through spawned hooks, and suppresses roster
  reconciliation and gap hiring. Its focused package passed 324 tests with 6
  platform skips; 35 dedicated regressions pass in under two seconds.
- The trusted 12:27 local canary routed exactly one `code-reviewer` unit and
  Codex spawned one intended child. Store evidence had zero activation grants,
  consumptions, specialist loads, or completed delegations; the child received
  only generic identity context and spawned one unintended grandchild. Stop
  correctly continued and the verifier failed the canary.
- Codex 0.145 source and the parent rollout prove MultiAgentV2 wraps
  `spawn_agent` in namespace `collaboration`, then flattens the command-hook name
  to `collaborationspawn_agent`. Agency matched only `spawn_agent`, so
  `PreToolUse` never selected. Three independent read-only audits converged on
  this boundary; the lease/Store state model was not the cause.
- AR-191 now shares one exact anchored V1/V2 matcher, preserves full rewritten
  tool input including `fork_turns`, rejects lookalikes, validates child event
  trace IDs against the active parent session, keeps actual process exit codes,
  types projection failures, and binds the public current-profile canary to the
  existing Store. Every installed Codex spawn spelling requires an atomically
  unclaimed native-child start; raw JSON identity provenance is preserved, a
  returned child identity must match exactly, replays are token/tool-use bound,
  V2 task paths must be rooted, and nested denials are observed truthfully. The
  final independent security re-review reports no AR-191/live-canary blocker.

## exact-blocker

- AR-191 still needs a clean substantive/ledger pair, exact installed refresh,
  changed-hook trust, and one fresh current-profile canary. No preexisting or
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

1. Close the independent-review findings, commit the AR-191 recovery pair, push
   `main`, and install that exact package plus refreshed Codex bundle.
2. Renew changed-hook trust once, then run one bounded current-profile activation
   verification and record the exact evidence-based demo verdict.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python -m pytest tests/test_codex_activation_canary.py tests/test_codex_activation_verification.py tests/test_host_hooks.py -q -W error
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
