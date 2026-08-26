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
evidence_commit: a13e3cf854b3243d37b00bf593d3afca19e65be9
minimum_ledger_commit: c52797620e804333ce15a4dec824e481c8807429
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/335
---

# AR-297 active recovery capsule

## checkpoint

- Work remains in the dedicated Linux worktree on
  `codex/ar297-production-container-live-evidence`, descended from clean
  `origin/main` `0a23983aa7b99ec27ef18b1a950f6a0327961f72`.
- The exact candidate is substantive `a13e3cf8` plus ledger `c5279762`.
  Telemetry before the latest route diagnostic exited 0 at 38.7 percent; this
  recovery pair records the smallest safe slice before another live call.
- The current Linux verdict remains **NO-GO**. AR-297 and tracker #335 remain
  open. No tracker, push, PR, merge, tag, signing, publication, release, or
  hosted workflow action is authorized.

## completed-evidence

- Exact mode-0600 config SHA-256 is
  `87551b5bc936a41742d6846523377e3cf869d8e5c2ce2e4941c447848e125628`:
  strict assurance, additive dense recall, Qwen 14B abliterated generation,
  Mistral 24B critic/reranker/recruiter/child judge, and LiteLLM
  `qwen3-embedding` at 4,096 dimensions. Jina is absent and was not called.
- Caller-umask-0002 build, strict Twine, and independent verification exit 0.
  Wheel SHA is `6677c922...90f5` (9,242,783 bytes); sdist SHA is
  `326f0907...3bf3b` (25,386,943 bytes). Both are mode 0644.
- Five new images bind `c5279762` and wheel `6677c922...90f5`: IDs begin
  `f50d8eef`, `5e482815`, `ba3551bc`, `28d1f07b`, and `9d45c40d`. Four new
  containers pass the pre-install absence receipt at SHA `dedaabba...fd82f`.
- Two unchanged Codex installs exit 1 after live routing, sessions
  `01a03f4e-27e6-7772-942f-f121ac9c487f` and
  `01a03f52-6822-72e3-9c46-d8a7dfc05e7b`. Both prove current managed-only
  policy, eight events, no bypass, Qwen planning, exact 4,096-wide LiteLLM
  embedding, and Mistral recruiting/criticism; both end
  `workforce_inference_failed` before route, child, finalization, or attestation.
- AR-307 is live-proven: the config-declared credential reaches only the
  tool-reduced child and `qwen3-embedding` applies. The later staffing failure
  remains AR-297's blocker rather than a credential or endpoint failure.
- Claude and UID-10000 Hermes clean installs exit 0 with bundle digests
  `702a880f...0724` and `eda2cb87...9858`. OpenClaw first exits 1 rather than
  invent missing native policy; after the approved SecretRef-only native
  profile at SHA `7d567996...8060`, it exits 0, is runtime-verified, and loads
  all 13 hooks with bundle `e0cd11d0...e598`.
- An ordinary route diagnostic exits 0 and proves requested/actual model plus
  4,096-dimensional recall receipts, but outside the restricted canary it
  misclassifies the review as workspace-write implementation. It is diagnostic
  model-quality evidence only, not activation or host-delivery proof.
- Historical exact-candidate host install, authenticated dashboard 401/200,
  complete 2,659-byte prompt visibility, and all repository gates passed at
  `2aa0b5a9`; they must be refreshed for `c5279762` before a final verdict.

## exact-blocker

- Codex still lacks an attestation after the fixed embedding boundary. Exact
  diagnostic `b6dc0aa...bc6e8` proves accepted inference selection was cleared
  only because deterministic staffing emitted `load` while the canary requires
  `delegate`. AR-308 binds that execution-only contract; live proof is pending.
- No later ordinary Codex, Claude, Hermes, or OpenClaw process has a current
  successful Agency-turn receipt on this source.
- Refresh the host install/dashboard and named repository gates for the exact
  candidate, then remove both old and new AR-297 proof containers.
- AR-299 through AR-307 tracker parity, hosted cross-OS artifacts, signing,
  push, PR, merge, tag, publication, release, and exhaustive workflow dispatch
  remain unauthorized.

## same-task-continuity

Exact artifacts are under `~/.agency-runtime/release-artifacts/`
`dist-c52797620e804333ce15a4dec824e481c8807429-linux-ar297`. Private current
evidence is `~/.agency-runtime/evidence/ar297-go-c5279762`; historical evidence
is `~/.agency-runtime/evidence/ar297-go-zKOPE1b8`. New container IDs begin
`847e86f5`, `6e9769aa`, `517f31e9`, and `9cef57e3`; old IDs remain separately
labelled. The secret-safe helper remains
`/tmp/agency-runtime-ar297-evidence.pcLOZn/run_with_litellm_key.py`.

## next-bounded-work-package

1. Checkpoint AR-308, rebuild the exact candidate, and run one clean no-bypass
   Codex managed-policy installation/canary.
2. Run later ordinary Conveyor-equivalent Codex, Claude, Hermes, and OpenClaw
   processes and correlate Store plus native artifacts.
3. Refresh exact host/dashboard and repository gates, update canonical records,
   remove every labelled AR-297 proof container, and issue the Linux verdict.

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
