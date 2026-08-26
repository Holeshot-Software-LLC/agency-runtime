---
title: "AR-297 active recovery capsule"
status: active
category: roadmap
created: 2026-08-25
updated: 2026-08-26
tags: [handoff, containers, unattended, codex, claude, hermes, openclaw, release]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-298-expose-complete-workforce-prompts.md
  - docs/roadmap/issue-AR-299-local-ollama-canary-child-judge.md
  - docs/roadmap/issue-AR-300-bind-explicit-install-config-to-managed-canary.md
  - docs/roadmap/issue-AR-301-private-systemd-dashboard-namespace.md
  - docs/roadmap/issue-AR-302-owner-private-local-verification.md
  - docs/roadmap/issue-AR-303-bound-full-roster-embedding-requests.md
  - docs/roadmap/issue-AR-304-preserve-recruiter-critic-validation-diagnostics.md
  - docs/roadmap/issue-AR-305-normalize-planner-novelty-absence.md
  - docs/roadmap/issue-AR-306-bind-strict-critic-semantics.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - docs/decisions/0174-admit-local-ollama-canary-child-judges.md
  - docs/decisions/0175-batch-complete-embedding-input-sets.md
  - README.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-297
branch: codex/ar297-production-container-live-evidence
evidence_commit: 3e188c9fe0761394e31ebd2ffa3269e136d13df8
minimum_ledger_commit: eb9da40f4e5662b4671885da004bf93289f8fdeb
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/335
---

# AR-297 active recovery capsule

## checkpoint

- PR #326 is merged. The dedicated Linux worktree remains on
  `codex/ar297-production-container-live-evidence`, descended from clean
  `origin/main` `0a23983aa7b99ec27ef18b1a950f6a0327961f72`.
- Telemetry exited 0 at 77.2, 60.1, 49.5, 27.8, 26.5, 18.2, and 9.2 percent;
  the bounded-package end check exited 0 at 41.8 percent after compaction.
  Every live attempt at or below the threshold followed a clean recovery pair:
  `14a4346c` / `3841fcce`, `dbd3eda9` / `95c323eb`, then `5acfbf41` /
  `8eb54c96`.
- Fresh telemetry crossed the threshold at 49.4 percent after the recruiter A/B
  and planner diagnostic. This recovery pair records the smallest safe repair
  before any post-fix live evaluation.
- The exact unsigned Linux candidate remains
  `987cee8ff01a4a16780eac15bb8120f828d4193d`. Its scoped verdict is **NO-GO**.
  AR-297 and tracker #335 remain open.

## completed-evidence

- Exact Agency config mode 0600, 3,642 bytes, SHA-256
  `cb569bf027133305df594d8ff029dffb8d38f545e960517d4431dfbf1b2bc2e1`
  remains strict/additive with Qwen 14B abliterated generation, Mistral 24B
  critic/reranker/child judge, and LiteLLM `qwen3-embedding` at 4,096
  dimensions. Jina is absent and was not called.
- The retained exact artifacts remain wheel
  `17a3bc0053a882b22ff72d8b3a2ebcd23ef602c2b5c034e7a05e8ae10ff929f1`
  and sdist
  `6551c43fc6fc7dfe7d8b9318e5b7605d1ecc8e214490eb7d0d2af001ffa9adb5`.
  Clean installs previously passed for Claude, Hermes, and OpenClaw; Codex
  installed managed policy but its two canaries failed before attestation.
- The prior ordinary Claude and OpenClaw processes timed out. Hermes session
  `20260826_143220_d88838` exited 0 only after Agency replaced an unverified
  draft with a refusal; Store run `ecdff898-6dc7-42c9-b0f9-db3447f46623`
  remained `preflight_failed`. No harness has a successful ordinary Agency turn.
- Authenticated dashboard evidence remains valid: unauthenticated health is
  401; authenticated health/detail are 200 and `no-store`; Accessibility
  Auditor renders all 2,657 characters at SHA-256
  `c3cfc0981cb980d700ee6b115c3669f5533108598419ca83f26bd5f30e185848`.
  Runtime delivery was not asserted.
- All named repository gates pass on the checkpointed implementation: the
  OS-owned Linux fast spine exits 0 with 858 passed and 3 skipped; UI passes
  138; routing passes every threshold; conformance kills 160/160 mutations with
  source unchanged. The optional exhaustive workflow was not dispatched. All
  five proof containers remain removed; no container was created this package.
- AR-303 now prevalidates one complete logical embedding set and permits at
  most two ordered scalar-safe calls. The exact 263-card/4,096-dimension test
  uses batches 243 and 21 including one query; warm uses one. Partial failure,
  model drift, and dimension drift discard all vectors and never seed cache.
  Cold recall and host timeouts cover two embeddings plus one reranker.
- AR-304 adds closed recruiter candidate and strict-critic semantic diagnoses.
  Provider-authored prose and unknown codes cannot enter repair or preflight
  receipts. The focused warning-strict set passes 139 tests and changed files
  pass Ruff.
- The approved Mistral-only recruiter A/B config hash is `87551b5b...e125628`.
  It exited 2 after 296,074 ms on trace `d276a583-e632-49af-b80f-7bece3b34b90`:
  Mistral ranked the two correct accessibility specialists first, yet verifier
  sufficiency still found one uncovered capability.
- A planner-only diagnostic then proved Qwen emitted string
  `novel_capability: "false"`, compiled as the sole uncovered
  `capability:false`. Diagnostic hash is `8c7a2c5c...d4bf137`; no Jina or secret
  was used. AR-305 normalizes only stringified absence sentinels at both gap and
  unknown-domain boundaries. Focused tests pass 158 with one skip.
- Post-fix trace `bbf187df-29ab-495a-acb0-7f60885a8b7e` applied planner,
  embedding, reranker, recruiter, and critic, then exited 2 only at
  `staffing_critic_rejected`. Summary/Store hashes are `a4ca68e1...132371a` and
  `7b679a1d...95fb346`.
- Diagnostic `c2dbfa54...bbba2` proves Mistral selected only Accessibility
  Auditor at confidence 1.0/margin 0.1; the verifier accepted, but the critic
  claimed `unsupported-confidence` and `unsafe-composition`. AR-306 adds exact
  thresholds, pre-execution scope, and selected-only semantics without removing
  critic veto authority; 158 focused tests pass with one skip.
- Confirmation trace `a60ed00e-4f08-4a84-8135-8bbc1a2a4f1b` moved both critic
  attempts to approval, but each included reasons and failed closed at
  `critic_approval_reasons_present`. Summary/Store hashes are
  `c89620c2...d8722e` / `7d911ec3...3efe75`. AR-306 now states the conditional
  reason-array contract explicitly; focused tests remain 158/1 skipped.
- Final trace `f8af12a9-2747-489d-879a-4a8417d1ef35` exits 0 after 123,320 ms.
  Five model receipts, one accepted route, and one specialist load correlate;
  only Accessibility Auditor is selected and its complete 2,659-byte prompt is
  verbatim in context. Summary/Store hashes are `e608576c...cb8576` and
  `c0cb4beb...de8be`; no failure, Jina call, or persisted secret exists.

## exact-blocker

- AR-305 and AR-306 are direct-live proven. Native delivery remains distinct;
  the four-container ordinary-turn matrix has not been rerun on this source.
- AR-301 blocks the shipped non-root dashboard service. AR-302 blocks ordinary
  ambient-umask/trusted-interpreter repeatability. No harness has a current
  successful ordinary Agency turn or Codex canary attestation.
- AR-299 through AR-306 tracker parity, hosted cross-OS artifacts, signing,
  push, PR, merge, tag, publication, and release remain unauthorized.

## same-task-continuity

The exact artifacts remain under `~/.agency-runtime/release-artifacts/`
`dist-987cee8ff01a4a16780eac15bb8120f828d4193d-linux-ar297`; the config remains
under `~/.agency-runtime/configs/`. The corrected private probe script is
`/tmp/ar297_direct_preflight_probe.py`; final private artifacts are
`authenticated-agency.db` and `direct-preflight-authenticated-summary.json`.
The probe obtains the existing LiteLLM credential in memory and persists no
secret. A/B and planner evidence is under `ar297-mistral-recruiter-KsV0r1NA`;
post-fix and strict diagnostics are under `ar297-postfix-8vIi2aDz`.

## next-bounded-work-package

1. Run all named repository gates, resolve AR-301 and AR-302, and build and
   independently verify a fresh exact candidate.
2. Recreate the four clean harness containers and repeat unattended
   ordinary-turn evidence; interview before any further model/config choice.
3. Recheck authenticated dashboard/service evidence, update canonical records,
   tear down proof containers, and issue the Linux-scoped verdict.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python -m pytest <named fast spine from AGENTS.md> -q -W error
node --test tests/dashboard_ui.test.mjs
agency eval routing --json --no-details
agency eval decision-conformance --repository . --json
git diff --check
~~~

## constraints

- Keep registration, loading, canary, delivery, Store correlation, and model
  prose distinct. Never expose or persist a secret.
- Do not configure/call Jina, overwrite foreign policy, use an activation
  bypass, or touch the shared checkout.
- No tracker, push, PR, merge, tag, signing, publication, release, or hosted
  workflow action is authorized.
