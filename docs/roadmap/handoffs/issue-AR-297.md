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
evidence_commit: c34933377f7fb16431120f21d487bfbc9910cd55
minimum_ledger_commit: c34933377f7fb16431120f21d487bfbc9910cd55
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/335
---

# AR-297 active recovery capsule

## checkpoint

- Work remains in dedicated worktree `/tmp/agency-runtime-ar297.WQUbF2` on
  `codex/ar297-production-container-live-evidence`, based on `origin/main`
  `0a23983a`. Never use the shared checkout.
- Clean ledger `c3493337` binds the separate-ID repair and exact artifacts.
  Fresh live proof reaches the free child judge and fails exact compatibility.
- Linux remains **NO-GO**. AR-297/#335 stay open. Tracker writes, push, PR,
  merge, tag, signing, publication, release, and hosted workflow actions are
  not authorized.

## completed-evidence

- Replacement mode-0600 config `ar297-litellm-a4e213d6b454ca90.yaml` has SHA
  `a4e213d6...97348`: strict/additive, all six Agency routes through
  authenticated LiteLLM aliases, Qwen generation with thinking disabled,
  Mistral critic/reranker/recruiter/free child judge, and 4,096-dimensional
  Qwen embedding. Direct Ollama and Jina are absent from active routes.
- Exact `c3493337` build/Twine/verifier/manifest exit 0. Mode-0644 wheel
  `3ee91ef7...6626` is 9,317,437 bytes; sdist `5a762480...9455` is 25,765,853
  bytes; manifest `7fa7d2c1...3bfd` records both.
- Codex/Claude/Hermes/OpenClaw/dashboard image IDs are `2d0b6555...0272`,
  `c731f8c8...ba8`, `56645dba...dae8`, `f87f2ab8...218`, and
  `951618f1...66a`; verification `884a225f...821` exits 0.
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

- Fresh exact absence `a88f8e7d...deb` passes. One no-bypass install
  `0ef4c8bb...d46` exits 1 after accepted route `41ac6703...f38`, one spawn,
  one 300-second wait, child `01a041eb...1128` exit 0, and no timeout.
- Parent/child rollouts and Store hash to `2b0acaec...a11`, `3d0ef98d...d3c`,
  and `4842b81d...9c9`. The separate-ID join succeeds and persists one exact
  native worker run, live-proving AR-324 beyond the earlier generic identity.
- The restricted 59-card call reaches authenticated `local-child-judge`, then
  fails closed at 62,139 ms as `native_child_compatibility_mutated` with
  confidence 0.8. Store correlation `50bd2770...a0b6` exits 0; unchanged-alias
  repeat `6df05ca7...884` recovers exact cached IDs `code-reviewer` plus
  `software-test-engineer`, proving semantic over-selection.
- Nine temperature-zero requests reproduce that team; all temporary aliases
  are deleted and stable projection `18dd1bdd...18b3` is unchanged. Generic
  repair `2642ac10...0b1e` abstains; closed diagnostic `29a0045c...f034`
  repeats the pair. Same-model options are closed without unsafe filtering.
- No later ordinary harness process has a successful Agency-turn receipt.
- Refresh host/dashboard and named gates, then remove all AR-297 containers.
- AR-299 through AR-317 tracker parity, hosted cross-OS artifacts, signing,
  push, PR, merge, tag, publication, release, and exhaustive workflow dispatch
  remain unauthorized.

## same-task-continuity

Exact artifacts are under `~/.agency-runtime/release-artifacts/`
`dist-c34933377f7fb16431120f21d487bfbc9910cd55-linux-ar297`; config is
`~/.agency-runtime/configs/ar297-litellm-a4e213d6b454ca90.yaml`. Evidence is
`~/.agency-runtime/evidence/ar297-go-c3493337`; Codex container
`agency-ar297-codex-c3493337` remains with older labelled containers.
AR-321 evidence is under `ar321-child-judge`; all await final teardown. Helper:
`/tmp/agency-runtime-ar297-evidence.pcLOZn/run_with_litellm_key.py`.

## next-bounded-work-package

After compaction, reread this capsule and `git status`, then resume at the first
unchecked line. Mark an item complete only with exact retained evidence.

1. [x] Build and independently verify exact `c3493337` artifacts/images.
2. [x] Test deterministic temporary Mistral aliases and remove all three.
3. [ ] Waiting for owner choice; propose `gemma3:27b` behind temporary LiteLLM.
4. [ ] In a new exact Codex container, prove delivery, consumption, header,
   finalization, Store correlation, and attestation.
5. [ ] Build and prove separate clean exact Claude, native-UID Hermes, and
   OpenClaw systemd production-container installs.
6. [ ] Run later ordinary unattended Conveyor-equivalent processes for all four
   harnesses; retain native artifacts, Store correlations, and full workforce
   prompt visibility without treating definition presence as runtime delivery.
7. [ ] Install the exact candidate on this Linux host and prove the private
   authenticated dashboard plus the approved service-manager contract.
8. [ ] Run every named repository gate and record exact exits and hashes.
9. [ ] Update canonical issues/capsule and make the required local substantive
   and `docs(worklog):` ledger commits.
10. [ ] Resolve and remove every container labelled `AR-297`; retain teardown
   evidence and verify zero labelled survivors.
11. [ ] Issue the Linux-scoped GO/NO-GO and complete the persistent goal only
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
