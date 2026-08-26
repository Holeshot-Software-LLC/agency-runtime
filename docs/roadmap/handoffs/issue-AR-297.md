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
  - docs/roadmap/issue-AR-307-project-canary-inference-credentials.md
  - docs/roadmap/issue-AR-308-bind-activation-canary-delegation.md
  - docs/roadmap/issue-AR-309-restore-codex-0149-activation-proof.md
  - docs/roadmap/issue-AR-310-require-managed-codex-canary-store.md
  - docs/roadmap/issue-AR-311-inject-exact-codex-canary-native-plan.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - docs/decisions/0174-admit-local-ollama-canary-child-judges.md
  - docs/decisions/0175-batch-complete-embedding-input-sets.md
  - docs/decisions/0176-use-owner-runtime-temp-for-nonroot-user-services.md
  - docs/decisions/0177-make-local-verification-private-by-construction.md
  - docs/decisions/0178-project-config-declared-credentials-into-tool-reduced-canaries.md
  - README.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-297
branch: codex/ar297-production-container-live-evidence
evidence_commit: 6bf3b5ec453dbeacdd075b2683e89a6efbfdc3c6
minimum_ledger_commit: c60678ef352e43db253b2d3d6e0fb162f80bfbf7
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/335
---

# AR-297 active recovery capsule

## checkpoint

- Work remains in dedicated worktree `/tmp/agency-runtime-ar297.WQUbF2` on
  `codex/ar297-production-container-live-evidence`, based on `origin/main`
  `0a23983a`. Never use the shared checkout.
- Last clean recovery pair: AR-310 repair `6bf3b5ec` and worklog `c60678ef`.
  AR-311's canary-only native-plan repair passes focused verification and is
  awaiting its clean recovery pair before the next live run.
- Linux remains **NO-GO**. AR-297/#335 stay open. Tracker writes, push, PR,
  merge, tag, signing, publication, release, and hosted workflow actions are
  not authorized.

## completed-evidence

- Exact mode-0600 config SHA is `87551b5bc936a41742d6846523377e3cf869d8e5c2ce2e4941c447848e125628`:
  strict assurance, additive dense recall, Qwen 14B abliterated generation,
  Mistral 24B critic/reranker/recruiter/child judge, and LiteLLM
  `qwen3-embedding` at 4,096 dimensions. Jina is absent and was not called.
- Exact `c60678ef` caller-umask-0002 build, strict Twine, and independent
  verification exit 0. Mode-0644 wheel `3c8eb01b...09c4e` is 9,291,980 bytes;
  sdist `8b8db82c...39131` is 25,489,348 bytes.
- Codex image `49493058...c9a5c` binds full candidate, wheel, Codex 0.149.1,
  and AR-297 labels. Fresh container `30b2b90c...be88` has absence receipt
  `a5c70707...28b0d` and no Agency targets before installation.
- Earlier exact candidate `1f32915d` passed every named gate: 860 Python spine
  tests (three skips), 138 dashboard tests, routing, and 161/161 killed
  decision mutations. These gates must still be refreshed for the final exact
  candidate.
- AR-309 implements exact 0.149 `SubAgentActivity`/quiet-root parsing,
  child-UUID v6 delivery, one-use canonical-rollout verification, post-spawn
  reconciliation, and receipt-backed final headers. Its 437 focused tests pass.
- AR-310's managed existing-Store call contract passes 268 focused tests and is
  live-proven by `c60678ef`: the invocation reaches native Codex, exact route,
  fixed delegate work unit, and one `code-reviewer` load with no trust bypass.
- AR-311 renders one Store-proven canary-only plan with exact
  `native_task_name=code_reviewer`, fixed goal, unit, and empty dependencies.
  Ordinary/mismatched routes receive no plan; 545 warning-strict focused Codex,
  hook, Store, installer, and security tests pass.

## exact-blocker

- Codex still lacks an attestation. Exact `c60678ef` install exits 1 with empty
  stderr and mode-0600 JSON SHA `a58dae29...4ad7`. Session
  `01a03fe6-c434-7432-a7ef-8d5535109e8c`, trace
  `01a03fe6-c43f-7790-b15d-582199c78b2b`, and query `eab71210...97d80`
  have one route/load but zero delegations, workers, or deliveries.
- Canonical parent rollout `fe8aedb9...2d6` records the sole call with invalid
  `task_name=code-reviewer`; Codex rejects the hyphen before child creation.
  Finalization `d7160d7b-7e22-40f4-b13d-4bbba01be04c` is
  `response_invalid` with missing `evidence_verification`.
- Rebuild AR-311, replace the mutated proof container, then require exactly one
  `code_reviewer` child artifact, consumed receipt, current header, accepted
  first finalization, and no-bypass attestation in one invocation.
- No later ordinary Codex, Claude, Hermes, or OpenClaw process has a current
  successful Agency-turn receipt on this source.
- Refresh the host install/dashboard and named repository gates for the exact
  candidate, then remove both old and new AR-297 proof containers.
- AR-299 through AR-311 tracker parity, hosted cross-OS artifacts, signing,
  push, PR, merge, tag, publication, release, and exhaustive workflow dispatch
  remain unauthorized.

## same-task-continuity

Exact artifacts: `~/.agency-runtime/release-artifacts/`
`dist-c60678ef352e43db253b2d3d6e0fb162f80bfbf7-linux-ar297`. Evidence:
`~/.agency-runtime/evidence/ar297-go-c60678ef`. Current Codex proof container is
`agency-ar297-codex-c60678ef`; historical evidence remains retained. All
AR-297-labelled containers await final teardown. Secret-safe helper:
`/tmp/agency-runtime-ar297-evidence.pcLOZn/run_with_litellm_key.py`.

## next-bounded-work-package

After compaction, reread this capsule and `git status`, then resume at the first
unchecked line. Mark an item complete only with exact retained evidence.

1. [x] Rebuild and verify exact `c60678ef` artifacts plus the Codex image.
2. [ ] Prove fresh Codex absence, then one exact no-bypass V2 install with one
   canonical child artifact, consumed receipt, current header, accepted
   finalization, Store correlation, and attestation.
3. [ ] Build and prove separate clean exact Claude, native-UID Hermes, and
   OpenClaw systemd production-container installs.
4. [ ] Run later ordinary unattended Conveyor-equivalent processes for all four
   harnesses; retain native artifacts, Store correlations, and full workforce
   prompt visibility without treating definition presence as runtime delivery.
5. [ ] Install the exact candidate on this Linux host and prove the private
   authenticated dashboard plus the approved service-manager contract.
6. [ ] Run every named repository gate and record exact exits and hashes.
7. [ ] Update canonical issues/capsule and make the required local substantive
   and `docs(worklog):` ledger commits.
8. [ ] Resolve and remove every container labelled `AR-297`; retain teardown
   evidence and verify zero labelled survivors.
9. [ ] Issue the Linux-scoped GO/NO-GO and complete the persistent goal only
   when all required items above are truthfully closed.

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
- No tracker, push, PR, merge, tag, signing, publication, release, hosted
  workflow, or new model/config choice is authorized.
