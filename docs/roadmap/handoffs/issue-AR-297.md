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
  - docs/roadmap/issue-AR-318-bound-codex-activation-child-wait.md
  - docs/roadmap/issue-AR-319-honor-pinned-canary-judge-timeout.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - docs/decisions/0174-admit-local-ollama-canary-child-judges.md
  - docs/decisions/0175-batch-complete-embedding-input-sets.md
  - docs/decisions/0176-use-owner-runtime-temp-for-nonroot-user-services.md
  - docs/decisions/0177-make-local-verification-private-by-construction.md
  - docs/decisions/0178-project-config-declared-credentials-into-tool-reduced-canaries.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/decisions/0180-project-current-profile-canary-install-home.md
  - docs/decisions/0181-use-litellm-aliases-as-host-inference-control-plane.md
  - docs/decisions/0182-bound-codex-activation-child-wait.md
  - docs/decisions/0183-honor-pinned-canary-judge-timeout.md
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
- Last clean recovery pair is AR-319 source `785070f6` and worklog `89a56901`.
  Its exact artifacts and five proof images pass independent verification;
  checkpoint them, then continue the same Codex proof.
- Linux remains **NO-GO**. AR-297/#335 stay open. Tracker writes, push, PR,
  merge, tag, signing, publication, release, and hosted workflow actions are
  not authorized.

## completed-evidence

- Replacement mode-0600 config `ar297-litellm-a4e213d6b454ca90.yaml` has SHA
  `a4e213d6...97348`: strict/additive, all six Agency routes through
  authenticated LiteLLM aliases, Qwen generation with thinking disabled,
  Mistral critic/reranker/recruiter/free child judge, and 4,096-dimensional
  Qwen embedding. Direct Ollama and Jina are absent from active routes.
- Exact ledger `89a56901` build, strict Twine, and independent verifier exit 0.
  Mode-0644 wheel `486b04ba...75de` is 9,300,384 bytes; sdist
  `d08d2ffc...56a2` is 25,622,478 bytes; manifest `4904e1cd...5321`.
- Codex/Claude/Hermes/OpenClaw/dashboard image IDs are `7765d320...b545`,
  `222a78c7...cdb2`, `896c03d1...0766`, `24736e64...1f3d`, and
  `4c0182f3...88e1`; exact verification exits 0 at `5edc4c29...395c`.
- AR-309 through AR-315 prove Codex 0.149 correlation, managed Store, fixed
  plan, normal-umask artifacts, default role, install identity, and a 59-card
  catalog boundary across 566 warning-strict tests.
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

- The prior `c6b7d92d` run isolated the 60,091-ms aggregate cutoff after its
  native wait succeeded. AR-319 now honors the pinned Mistral profile's
  120-second bound and passes 222 affected tests. Exact `89a56901` images are
  verified; prove full v6 delivery in a fresh container.
- No later ordinary Codex, Claude, Hermes, or OpenClaw process has a current
  successful Agency-turn receipt on this source.
- Refresh the host install/dashboard and named repository gates for the exact
  candidate, then remove both old and new AR-297 proof containers.
- AR-299 through AR-317 tracker parity, hosted cross-OS artifacts, signing,
  push, PR, merge, tag, publication, release, and exhaustive workflow dispatch
  remain unauthorized.

## same-task-continuity

Exact artifacts: `~/.agency-runtime/release-artifacts/`
`dist-89a56901edb121b32255fbac8f2e58666a9c5d03-linux-ar297`; config is
`~/.agency-runtime/configs/`
`ar297-litellm-a4e213d6b454ca90.yaml`. Evidence: `ar297-go-3e42598d` and
`ar297-litellm-routing-ioeoBe`, plus current `ar297-go-89a56901`. Old containers
are `agency-ar297-codex-3e42598d` and `-c2`; older evidence containers remain.
All AR-297 containers await final teardown. Secret-safe helper:
`/tmp/agency-runtime-ar297-evidence.pcLOZn/run_with_litellm_key.py`.

## next-bounded-work-package

After compaction, reread this capsule and `git status`, then resume at the first
unchecked line. Mark an item complete only with exact retained evidence.

1. [x] Rebuild and independently verify artifacts/images from the exact
   AR-319/LiteLLM checkpoint; `89a56901` is the candidate.
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
