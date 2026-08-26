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
  - docs/roadmap/issue-AR-312-validate-explicit-production-config.md
  - docs/roadmap/issue-AR-313-trust-normal-umask-codex-artifacts.md
  - docs/roadmap/issue-AR-314-bind-codex-default-canary-role.md
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
evidence_commit: ee357a27d0fb058ef6e704225b86a656cefa6d92
minimum_ledger_commit: 49bf11902af5eca7fae528edf75374e73f747933
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/335
---

# AR-297 active recovery capsule

## checkpoint

- Work remains in dedicated worktree `/tmp/agency-runtime-ar297.WQUbF2` on
  `codex/ar297-production-container-live-evidence`, based on `origin/main`
  `0a23983a`. Never use the shared checkout.
- Last clean recovery pair: AR-311 repair `ee357a27` and worklog `49bf1190`.
  AR-313/AR-314 pass focused verification and await their recovery pair before
  the next live run. Telemetry was 52.7 percent at this package boundary.
- Linux remains **NO-GO**. AR-297/#335 stay open. Tracker writes, push, PR,
  merge, tag, signing, publication, release, and hosted workflow actions are
  not authorized.

## completed-evidence

- Exact mode-0600 config SHA is `87551b5bc936a41742d6846523377e3cf869d8e5c2ce2e4941c447848e125628`:
  strict assurance, additive dense recall, Qwen 14B abliterated generation,
  Mistral 24B critic/reranker/recruiter/child judge, and LiteLLM
  `qwen3-embedding` at 4,096 dimensions. Jina is absent and was not called.
- Exact `84dd879e` caller-umask-0002 build, strict Twine, and independent
  verification exit 0. Mode-0644 wheel `61dbb8c6...c950b` is 9,298,676 bytes;
  sdist `3845d6e0...8329c` is 25,540,553 bytes.
- Codex image `12534257...647291` and fresh container `22ce57f2...e93bff`
  bind that wheel. Absence receipt `ae43bf47...ae4bc` exits 0.
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
- AR-311 is live-proven: exact parent `01a04003...fd20` creates child
  `01a04005...b5b0`, which completes fixed unit `unit-05d45f7553` with exit 0.
  Parent/child rollouts hash to `8b93d005...1b668`/`6e18884f...f73a0`.
- AR-313 admits normal-umask Codex artifacts by owner/link/write/ACL integrity,
  and AR-314 pins omitted MultiAgentV2 role `default` without using it for
  selection. Focused warning-strict checks pass 586 plus two helper tests.

## exact-blocker

- Codex still lacks an attestation. First exact `84dd879e` install exits 1 with
  empty stderr and JSON SHA `b138e5f6...e6800`. Session `01a0402b...4989` and
  trace `01a0402b...395f` fail preflight before route/child: planning repairs,
  embedding applies, and recruiting repairs then safely abstains with
  `no_safe_sufficient_team`/`recruiter_abstained`. Store and parent rollout
  hashes are `ff60c8c3...a5bc1`/`032f2ee6...7c4d`.
- Run one fresh unchanged retry because the identical config previously reached
  the child. Then require exactly one
  `code_reviewer` child artifact, consumed receipt, current header, accepted
  first finalization, and no-bypass attestation in one invocation.
- No later ordinary Codex, Claude, Hermes, or OpenClaw process has a current
  successful Agency-turn receipt on this source.
- Refresh the host install/dashboard and named repository gates for the exact
  candidate, then remove both old and new AR-297 proof containers.
- AR-299 through AR-314 tracker parity, hosted cross-OS artifacts, signing,
  push, PR, merge, tag, publication, release, and exhaustive workflow dispatch
  remain unauthorized.

## same-task-continuity

Exact artifacts: `~/.agency-runtime/release-artifacts/`
`dist-84dd879e13550e37d0b3245a2ae49355e2912cac-linux-ar297`. Evidence:
`~/.agency-runtime/evidence/ar297-go-84dd879e`. Current Codex proof container is
`agency-ar297-codex-84dd879e`; historical evidence remains retained. All
AR-297-labelled containers await final teardown. Secret-safe helper:
`/tmp/agency-runtime-ar297-evidence.pcLOZn/run_with_litellm_key.py`.

## next-bounded-work-package

After compaction, reread this capsule and `git status`, then resume at the first
unchecked line. Mark an item complete only with exact retained evidence.

1. [x] Rebuild and verify exact `84dd879e` artifacts plus the Codex image.
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
