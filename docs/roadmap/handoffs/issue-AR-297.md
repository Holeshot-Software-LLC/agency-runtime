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
evidence_commit: 105ce02180cde503a39189fd9f158f6121704e9d
minimum_ledger_commit: 1f32915d14a9760d8cd12d21fbc6e7f3d8940a66
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/335
---

# AR-297 active recovery capsule

## checkpoint

- Work remains in the dedicated Linux worktree on
  `codex/ar297-production-container-live-evidence`, descended from clean
  `origin/main` `0a23983aa7b99ec27ef18b1a950f6a0327961f72`.
- The last implementation candidate is substantive `105ce021` plus ledger
  `1f32915d`; the AR-309 recovery pair is `6c01811a` plus `c89d80c3`.
  Telemetry before the bounded stable comparison exited 0 at 10.4 percent, so
  this checkpoint records that completed comparison before implementation.
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
  Wheel SHA is `a81338f5...ca78` (9,244,572 bytes); sdist SHA is
  `22e4286f...a15a` (25,397,183 bytes). Both are mode 0644.
- Five exact image IDs begin `226afba9` (Codex), `507328b7` (Claude),
  `8a50f5cb` (Hermes), `fd9967a0` (OpenClaw base), and `893b88eb`
  (OpenClaw systemd). Four fresh containers bind candidate `1f32915d`; their
  pre-install absence receipt passes at SHA `58e279f1...d128`.
- All named repository gates already pass at `1f32915d`: 860 Python spine
  tests with three skips, 138 dashboard tests, routing, and 161/161 killed
  decision mutations. The decision-conformance JSON SHA is
  `b0636470...0a6`, and source remained unchanged.
- The sole fresh Codex install exits 1 with empty stderr and exact JSON SHA
  `72c4ba0...6e4ab`. Managed-only policy and no bypass are preserved. Session
  `01a03f83-bb05-7c43-b9b3-38cb8d9e30dd` proves Qwen planning, exact
  4,096-wide LiteLLM embedding, Mistral recruiting/criticism, accepted
  `delivery=delegate`, one loaded `code-reviewer`, one native spawn, one child
  answer, and one completed wait.
- Parent/child rollout SHAs `5a548331...2af2` and `4732afb2...225e` prove the
  actual Codex 0.149 lifecycle. The newer V2 envelope redacts the decrypted
  child launch and omits Agency's post-wait header context; Store finalization
  is `response_invalid`, no host delivery verifies, and no attestation exists.
- The one supported-`multi_agent` comparison exits 0 but records zero native
  deliveries/delegations/worker runs for session `01a03f94...e55`, trace
  `01a03f94...a`, and query hash `4d160cfe...c652`. Its mode-0600 stdout,
  stderr, Store, and rollout SHAs are `356d36d1...bc6`, `dc6b6525...f5a`,
  `bb518e7c...20d`, and `95329525...a3`: the actual plan row is absent, so
  stable cannot replace the V2 surface that spawned the child.
- AR-308 is therefore live-proven through its exact delivery boundary. AR-309
  now owns the later host-artifact/header defect. No model, endpoint, dimension,
  reranker, thinking, judge, auth, or service-manager choice changed.

## exact-blocker

- Codex still lacks an attestation because its 0.149.1 V2 child artifact does
  not expose the pre-speech card and its final parent header retains stale
  `delegated: none`. ADR-0156 forbids substituting Store rows or model prose.
- Stable `multi_agent` cannot execute the accepted plan. The next bounded
  package keeps V2, allowlists its exact Codex 0.149 collaboration envelope,
  and adds a one-use host-persisted child receipt bound to the exact card plus a
  conditional header contract. It must remain failed closed on any mismatch.
- No later ordinary Codex, Claude, Hermes, or OpenClaw process has a current
  successful Agency-turn receipt on this source.
- Refresh the host install/dashboard and named repository gates for the exact
  candidate, then remove both old and new AR-297 proof containers.
- AR-299 through AR-309 tracker parity, hosted cross-OS artifacts, signing,
  push, PR, merge, tag, publication, release, and exhaustive workflow dispatch
  remain unauthorized.

## same-task-continuity

Exact artifacts are under `~/.agency-runtime/release-artifacts/`
`dist-1f32915d14a9760d8cd12d21fbc6e7f3d8940a66-linux-ar297`. Private current
evidence is `~/.agency-runtime/evidence/ar297-go-1f32915d`; historical evidence
remains retained. Current container IDs begin `e6075282`, `792ed3e9`,
`4938a43d`, and `62df9b7b`; older labelled proof containers remain. The
secret-safe helper remains
`/tmp/agency-runtime-ar297-evidence.pcLOZn/run_with_litellm_key.py`.

## next-bounded-work-package

1. Record the delivery-receipt authority decision, implement the bounded
   AR-309 V2 parser/receipt/header repair, checkpoint it, and rebuild one exact
   no-bypass Codex transaction.
2. Complete fresh Claude, Hermes, and OpenClaw installs, then run later ordinary
   Conveyor-equivalent Codex, Claude, Hermes, and OpenClaw
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
