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
  - docs/roadmap/issue-AR-315-project-codex-canary-install-home.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - docs/decisions/0174-admit-local-ollama-canary-child-judges.md
  - docs/decisions/0175-batch-complete-embedding-input-sets.md
  - docs/decisions/0176-use-owner-runtime-temp-for-nonroot-user-services.md
  - docs/decisions/0177-make-local-verification-private-by-construction.md
  - docs/decisions/0178-project-config-declared-credentials-into-tool-reduced-canaries.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/decisions/0180-project-current-profile-canary-install-home.md
  - README.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-297
branch: codex/ar297-production-container-live-evidence
evidence_commit: e718dca062dab654bfd4fb4314c31a644099c198
minimum_ledger_commit: 1ea2686f0e75b855594299dbde76edee842fe54f
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/335
---

# AR-297 active recovery capsule

## checkpoint

- Work remains in dedicated worktree `/tmp/agency-runtime-ar297.WQUbF2` on
  `codex/ar297-production-container-live-evidence`, based on `origin/main`
  `0a23983a`. Never use the shared checkout.
- Last clean recovery pair: exact Codex abstention `e718dca0` and worklog
  `1ea2686f`. This substantive checkpoint captures retry R2 and AR-315; its
  immediately following worklog commit must record the exact SHA before the
  next live run. Current telemetry is 79.1 percent remaining.
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
- R2 installed-runtime diagnostics prove the missing owner-home capability:
  absent resolves no identity; explicit `/root` resolves a current managed
  identity with matched runtime. Both exit 0; stdout hashes are
  `550b2048...e3fff`/`1fccf6f2...ee60`. AR-315's 7 focused and 559 broader
  warning-strict tests, Ruff, and all 869 documentation checks pass at exit 0.

## exact-blocker

- Codex still lacks an attestation. Fresh R2 container `537744e9...09476`
  passes absence, then exits 1 with empty stderr and JSON SHA
  `aba8cf2d...5089`. Parent `01a04030...825f`, trace `01a04030...fa3e`, route
  `3bac13eb...366e`, and child `01a04033...9148` correlate one fixed worker
  exit 0, but zero native routes/deliveries/grants/consumptions and rejected
  finalization `a065ac2c...51e9`. Store/parent/child hashes are
  `9209d92e...c177`/`bf356b10...e309`/`e9d3c8f8...6cf93`.
- AR-315 projects the explicit owner-home authority required by canary-mode
  install identity. Checkpoint, rebuild, and require exactly one v6
  `code_reviewer` artifact, consumed receipt, current header, accepted first
  finalization, and no-bypass attestation in one invocation.
- No later ordinary Codex, Claude, Hermes, or OpenClaw process has a current
  successful Agency-turn receipt on this source.
- Refresh the host install/dashboard and named repository gates for the exact
  candidate, then remove both old and new AR-297 proof containers.
- AR-299 through AR-315 tracker parity, hosted cross-OS artifacts, signing,
  push, PR, merge, tag, publication, release, and exhaustive workflow dispatch
  remain unauthorized.

## same-task-continuity

Exact artifacts: `~/.agency-runtime/release-artifacts/`
`dist-84dd879e13550e37d0b3245a2ae49355e2912cac-linux-ar297`. Evidence:
`~/.agency-runtime/evidence/ar297-go-84dd879e`. Current Codex proof containers
are `agency-ar297-codex-84dd879e` and its `-r2` retry; evidence is retained. All
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
