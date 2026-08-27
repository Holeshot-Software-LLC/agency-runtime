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
  - docs/roadmap/issue-AR-316-size-ollama-selector-judge-context.md
  - docs/roadmap/issue-AR-317-route-agency-inference-through-litellm-aliases.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - docs/decisions/0174-admit-local-ollama-canary-child-judges.md
  - docs/decisions/0175-batch-complete-embedding-input-sets.md
  - docs/decisions/0176-use-owner-runtime-temp-for-nonroot-user-services.md
  - docs/decisions/0177-make-local-verification-private-by-construction.md
  - docs/decisions/0178-project-config-declared-credentials-into-tool-reduced-canaries.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/decisions/0180-project-current-profile-canary-install-home.md
  - docs/decisions/0181-use-litellm-aliases-as-host-inference-control-plane.md
  - README.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-297
branch: codex/ar297-production-container-live-evidence
evidence_commit: 2fa5013fc96174195a21fd998571bb6cb20e20f5
minimum_ledger_commit: 260bd197586d3c9c9334f364aca4e86d879e9c29
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/335
---

# AR-297 active recovery capsule

## checkpoint

- Work remains in dedicated worktree `/tmp/agency-runtime-ar297.WQUbF2` on
  `codex/ar297-production-container-live-evidence`, based on `origin/main`
  `0a23983a`. Never use the shared checkout.
- Last clean recovery pair is AR-317 alias evidence `c283efac` and worklog
  `f0c11a10`. Post-compaction telemetry is 65.1 percent; continue the same task
  and checkpoint this replacement-config package before rebuilding.
- Linux remains **NO-GO**. AR-297/#335 stay open. Tracker writes, push, PR,
  merge, tag, signing, publication, release, and hosted workflow actions are
  not authorized.

## completed-evidence

- Replacement mode-0600 config `ar297-litellm-a4e213d6b454ca90.yaml` has SHA
  `a4e213d6...97348`: strict/additive, all six Agency routes through
  authenticated LiteLLM aliases, Qwen generation with thinking disabled,
  Mistral critic/reranker/recruiter/free child judge, and 4,096-dimensional
  Qwen embedding. Direct Ollama and Jina are absent from active routes.
- Exact ledger `3e42598d` caller-umask-0002 build, strict Twine, and independent
  verification exit 0. Mode-0644 wheel `0bb18a70...d983` is 9,299,031 bytes;
  sdist `73d8c201...ae55` is 25,561,038 bytes. Codex image is
  `6fbbdbd5...696c`; C1/C2 absence receipts `575a1fe3...090` and
  `abf3d278...8a4b` exit 0.
- AR-309 through AR-314 prove exact Codex 0.149 parent/child correlation,
  managed Store, fixed native plan, normal-umask artifacts, and default host
  role. AR-315 passes 7 focused and 559 broader warning-strict tests plus Ruff
  and 869-document validation.
- AR-315 is live-proven in C2: decision `1d351ac6...c63082` exists only after
  immutable install identity, stable routing state, and a 59-card catalog pass;
  it records the configured free child judge attempt without admitting a card.
- AR-317 passes 158 focused tests. Six Mistral/Qwen aliases are healthy and the
  shared fallback remains `8e801fde...075f`; model snapshot `6a80b30a...be8df`.
  Child probe `5c9d6a27...800f4` uses 20,050 tokens at `n_ctx=32768` with
  `truncated=0`/fallbacks 0; embedding `fb1d9fc7...34a94` is 4,096-dimensional.
- Exact product schema/load and current six-deployment checks exit 0 at
  `fb8d3384...f680f`. Critic/reranker/child/embedding adapter probes exit 0 at
  `f1ec2f09...e142`, `6c220204...c1dc`, `82a1abf3...c244`, and
  `0af8e0a4...92a6`; CLI validation exits 2 only on cold-host warnings.
- Earlier exact `1f32915d` named gates pass: 860 Python tests (three skips), 138
  dashboard tests, routing, and 161/161 decision mutations. Refresh all gates
  for the final exact candidate.

## exact-blocker

- Superseded Codex C1/C2 both exit 1: C1 fails planner semantics; C2 reaches
  route `9f377961...fb2d` and fixed child exit 0, then its truncated judge fails
  and the 180-second canary expires. Receipts are `86983408...0fc0` and
  `e043a745...ead5`; exact Store/rollout correlations remain in the issue.
- AR-316 proves the discarded direct route truncated C2. The operator selected
  disabled thinking and the new AR-317 config is structurally/deployment valid.
  Its first no-thinking planner probe exits 1 only for missing codebase
  discovery (`cfe56a4f...71dcc`); prove bounded repair in a fresh 600-second
  container. Require one v6 `code-reviewer` artifact, consumed receipt, current header, accepted first
  finalization, and no-bypass attestation in one invocation.
- No later ordinary Codex, Claude, Hermes, or OpenClaw process has a current
  successful Agency-turn receipt on this source.
- Refresh the host install/dashboard and named repository gates for the exact
  candidate, then remove both old and new AR-297 proof containers.
- AR-299 through AR-317 tracker parity, hosted cross-OS artifacts, signing,
  push, PR, merge, tag, publication, release, and exhaustive workflow dispatch
  remain unauthorized.

## same-task-continuity

Prior artifacts: `~/.agency-runtime/release-artifacts/`
`dist-3e42598da5eaa5b58d0bb0771cea6f90719d48d1-linux-ar297`; rebuild after
this checkpoint. Exact config is `~/.agency-runtime/configs/`
`ar297-litellm-a4e213d6b454ca90.yaml`. Evidence: `ar297-go-3e42598d` and
`ar297-litellm-routing-ioeoBe`. Current old Codex containers
are `agency-ar297-codex-3e42598d` and `-c2`; older evidence containers remain.
All AR-297 containers await final teardown. Secret-safe helper:
`/tmp/agency-runtime-ar297-evidence.pcLOZn/run_with_litellm_key.py`.

## next-bounded-work-package

After compaction, reread this capsule and `git status`, then resume at the first
unchecked line. Mark an item complete only with exact retained evidence.

1. [ ] Rebuild and independently verify artifacts/images from this exact
   LiteLLM-config checkpoint; do not reuse `3e42598d` as the candidate.
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
