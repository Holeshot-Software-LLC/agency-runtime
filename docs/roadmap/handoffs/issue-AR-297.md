---
title: "AR-297 active recovery capsule"
status: active
category: roadmap
created: 2026-08-25
updated: 2026-08-27
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
  - docs/roadmap/issue-AR-320-bound-codex-wait-to-full-child-staffing.md
  - docs/roadmap/issue-AR-321-select-reliable-free-litellm-child-judge.md
  - docs/roadmap/issue-AR-322-bind-codex-child-session-to-canary-parent.md
  - docs/roadmap/issue-AR-324-bind-codex-canary-child-through-host-lineage.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - docs/decisions/0185-enforce-child-judge-schema-at-litellm-alias.md
  - docs/decisions/0186-bind-codex-child-session-with-canary-request-digest.md
  - docs/decisions/0187-bind-codex-canary-child-through-host-authored-lineage.md
  - docs/decisions/0188-separate-codex-hook-parent-and-child-identities.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/decisions/0180-project-current-profile-canary-install-home.md
  - docs/decisions/0181-use-litellm-aliases-as-host-inference-control-plane.md
  - docs/decisions/0182-bound-codex-activation-child-wait.md
  - docs/decisions/0183-honor-pinned-canary-judge-timeout.md
  - docs/decisions/0184-bound-codex-wait-to-full-child-staffing.md
  - README.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-297
branch: codex/ar297-production-container-live-evidence
evidence_commit: 34f41532bbc700e8b824b63a322ac6261fedba9b
minimum_ledger_commit: 9e8fa342ada3231892190bee14af4c05d7a504c8
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/335
---

# AR-297 active recovery capsule

## checkpoint

- Work remains in dedicated worktree `/tmp/agency-runtime-ar297.WQUbF2` on
  `codex/ar297-production-container-live-evidence`, based on `origin/main`
  `0a23983a`. Never use the shared checkout.
- Clean artifact ledger `9e8fa342` remains reproducible; separate-ID source
  `34f41532` awaits its recovery/worklog ledger before a fresh rebuild.
- Linux remains **NO-GO**. AR-297/#335 stay open. Tracker writes, push, PR,
  merge, tag, signing, publication, release, and hosted workflow actions are
  not authorized.

## completed-evidence

- Replacement mode-0600 config `ar297-litellm-a4e213d6b454ca90.yaml` has SHA
  `a4e213d6...97348`: strict/additive, all six Agency routes through
  authenticated LiteLLM aliases, Qwen generation with thinking disabled,
  Mistral critic/reranker/recruiter/free child judge, and 4,096-dimensional
  Qwen embedding. Direct Ollama and Jina are absent from active routes.
- Exact `9e8fa342` build/Twine/verifier exit 0. Wheel `0d3c4948...dd4a` is
  9,317,479 bytes; sdist `e443491e...fc66` is 25,755,608 bytes; manifest
  `02bd1e04...b327` records both mode-0644 artifacts.
- Codex/Claude/Hermes/OpenClaw/dashboard image IDs are `eb4d9305...17e7`,
  `c5ac6f52...c6d6`, `f7c7f279...0874`, `a3597cf8...94bf`, and
  `041b92bd...9007`; verification `92e1f908...a253` exits 0.
- AR-317 passes 158 focused tests. Six Mistral/Qwen aliases are healthy and the
  shared fallback remains `8e801fde...075f`; model snapshot `6a80b30a...be8df`.
  Child probe `5c9d6a27...800f4` uses 20,050 tokens at `n_ctx=32768` with
  `truncated=0`/fallbacks 0; embedding `fb1d9fc7...34a94` is 4,096-dimensional.
- Exact schema/load and six-deployment checks exit 0 at `fb8d3384...f680f`;
  all four adapter probes pass and CLI warnings describe only cold hosts.
- Earlier exact `1f32915d` named gates pass: 860 Python tests (three skips), 138
  dashboard tests, routing, and 161/161 decision mutations. Refresh all gates
  for the final exact candidate.

## exact-blocker

- Fresh `c1cf1793` absence passes at `7d08f8c1...c341`; one no-bypass install
  `04f8c2df...7ad` exits 1 after spawn once, wait once at 300 seconds, child
  exit 0, and `timed_out=false`. AR-320's wait repair is live-proven.
- Stable literal alias proof `54a773f7...00d3` selects sole `code-reviewer`;
  snapshot `de042cbe...6c0a` proves the exact free Mistral schema deployment,
  and temporary alias deletion leaves zero at `74a870bc...95da`.
- Fresh exact install `7197d5ff...a62` resolves route `25e06734...7484`, spawns
  child `01a041d3...b1d2`, waits once at 300 seconds, and gets exit 0 without
  timeout. Parent/child rollouts and Store hash to `f83e31f3...02fc`,
  `b4215dc8...0394`, and `56518a59...53b0`, but only generic identity lands.
- Exact source proves hook `session_id` is the parent and `agent_id` the child;
  ADR-0187's equality rejected every real child. ADR-0188/source `34f41532`
  joins them separately. Focused warning-strict sets pass 192 and 258 tests
  with two expected skips; rebuild and live proof remain.
- No later ordinary Codex, Claude, Hermes, or OpenClaw process has a current
  successful Agency-turn receipt on this source.
- Refresh the host install/dashboard and named repository gates for the exact
  candidate, then remove both old and new AR-297 proof containers.
- AR-299 through AR-317 tracker parity, hosted cross-OS artifacts, signing,
  push, PR, merge, tag, publication, release, and exhaustive workflow dispatch
  remain unauthorized.

## same-task-continuity

Exact artifacts: `~/.agency-runtime/release-artifacts/`
`dist-9e8fa342ada3231892190bee14af4c05d7a504c8-linux-ar297`; config is
`~/.agency-runtime/configs/`
`ar297-litellm-a4e213d6b454ca90.yaml`. Current evidence is
`~/.agency-runtime/evidence/ar297-go-9e8fa342`; Codex container
`agency-ar297-codex-9e8fa342` remains running with older labelled containers.
AR-321 evidence is under `ar321-child-judge`; all await final teardown. Helper:
`/tmp/agency-runtime-ar297-evidence.pcLOZn/run_with_litellm_key.py`.

## next-bounded-work-package

After compaction, reread this capsule and `git status`, then resume at the first
unchecked line. Mark an item complete only with exact retained evidence.

1. [x] Build and independently verify exact `9e8fa342` artifacts/images.
2. [ ] Ledger `34f41532`, rebuild exact artifacts/images, then prove Codex delivery,
   consumption, header, finalization, Store correlation, and attestation.
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
- Free local child-judge alias tests/download are approved; keep every Agency
  route behind LiteLLM. No tracker, push, PR, merge, tag, signing, publication,
  release, hosted workflow, or unrelated model/config choice is authorized.
