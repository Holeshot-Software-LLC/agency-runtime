---
title: "AR-290 active recovery capsule"
status: active
category: roadmap
created: 2026-08-25
updated: 2026-08-26
tags: [handoff, onboarding, install, configuration, dashboard, release]
related:
  - docs/roadmap/issue-AR-290-end-to-end-guided-setup.md
  - docs/roadmap/issue-AR-293-safe-inference-profile-config-operations.md
  - docs/roadmap/issue-AR-295-audit-guided-dashboard-asset-budget.md
  - docs/roadmap/issue-AR-296-project-effective-inference-topology.md
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-298-expose-complete-workforce-prompts.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0172-compose-first-run-setup-from-guarded-owner-operations.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - README.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-290
branch: codex/ar290-guided-setup-readme
evidence_commit: 3023f0557e72911c4d42be53dccca3369b05ca8e
minimum_ledger_commit: a5cd7cae5f5874d50c75cb0c0a3d680e2195ab15
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/328
---

# AR-290 active recovery capsule

## checkpoint

- Work remains isolated on `codex/ar290-guided-setup-readme`; the shared
  `main` checkout was not switched, staged, cleaned, or committed.
- AR-289 through AR-298 source implementation is preserved through substantive
  `3023f055` and ledger `a5cd7cae`. Draft PR #326 is the publication
  surface.
- Last verified remote `main` at `a19a1669` was merged without rewriting in
  `7487b31b`. Fetch again before push or merge and preserve concurrent work.
- Trackers #327 through #336 are linked with exact labels and states. Scoped
  AR-289 through AR-298 parity passes; PR #326 merge is explicitly authorized
  after required checks, which are green.
- Current telemetry is above the 50-percent checkpoint threshold; continue the
  same task after every clean checkpoint.

## completed-evidence

- Guided setup, guarded config operations, Jina-compatible embedding and
  reranker transports, complete inference topology, production-container
  bootstrap, and workforce prompt visibility are implemented and documented.
- Windows is configured with strict assurance and additive dense recall. Jina
  credentials remain environment-only and were not written to config, argv,
  repository, Store evidence, or dashboard output.
- Installed Codex, Claude Code, ZCode, and dashboard projections are registered,
  enabled, current, and drift-free. OpenClaw and Hermes are absent and were
  skipped. Dashboard service is owned, enabled, active, current, reachable, and
  opened on loopback.
- The attended Windows install is incomplete only for ungranted Codex hook trust;
  doctor also reports all three installed harnesses cold. No production managed
  policy was installed on this workstation.
- Installed deterministic smoke passes 8/8. The installed dashboard renderer,
  managed-policy module, and workforce Store reader hash-match source.
- Installed workforce prompt lookup exits 0 and returns exact stored-definition
  provenance, immutable version, standing, hash, bounded body/truncation data,
  and `runtime_delivery_proof=not_asserted`.
- The dashboard's prior authenticated topology inspection proved strict/additive
  state, redacted Jina roles, generation/judge models, thinking levels, and the
  Agency-selection/native-host-execution boundary. Its refreshed token expired
  before AR-297 policy and AR-298 complete-prompt surfaces could be visually
  inspected, so that new installed visual claim remains open.
- Final source gates pass: 840 fast-spine tests with 20 skips, 138 dashboard UI
  tests, Ruff and docs checks, all routing thresholds, and decision conformance
  with a passing baseline, every curated mutation killed, and source unchanged.

## exact-blocker

- AR-297 needs clean Linux Codex, Claude Code, and OpenClaw production-container
  evidence, including a later ordinary Conveyor-equivalent invocation.
- AR-298 needs installed authenticated owner-detail visual proof.
- Exact release artifacts, fresh-environment portability, signing, tag,
  publication, and release gates remain open or unauthorized.
- The global strict tracker audit still exposes older AR-128 through AR-288
  repository debt outside the AR-289 through AR-298 authorization.
- AR-119 still lacks complete all-host exact-candidate Rule-4 proof; no Store
  row, copied plugin, model prose, or deterministic smoke can substitute.

## same-task-continuity

Recheck remote `main`, branch, PR, and both active capsules before
publication. Keep discovery, registration, enablement, loading, live canary,
host-written delivery, Store correlation, and model output separate. Missing
or pre-allocation evidence remains unknown, never healthy.

## next-bounded-work-package

Checkpoint and push the tracker-link pair, mark PR #326 ready, merge it after
the required checks remain green, and verify the exact remote `main` merge.
The cross-machine execution prompt lives in
`docs/roadmap/handoffs/issue-AR-297.md`; use it for the still-open Linux
release evidence. Do not tag, sign, publish, or create a release.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python -m pytest <focused configuration/provider/setup/security tests> -q -W error
python -m pytest <named fast spine from AGENTS.md> -q -W error
node --test tests/dashboard_ui.test.mjs
agency eval routing --json --no-details
python -m agency_runtime.cli eval decision-conformance --repository . --json
git diff --check
~~~

## constraints

- Never expose the Jina credential; the owner intends to rotate it.
- Do not touch the shared `main` checkout or another linked worktree.
- Preserve exact historical subjects and non-rewriting worklog SHAs.
- This turn authorizes trackers AR-289 through AR-298 and PR #326 merge only.
  It does not authorize a tag, signing, package publication, or release.
