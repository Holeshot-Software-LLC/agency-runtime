---
title: "AR-290 active recovery capsule"
status: active
category: roadmap
created: 2026-08-25
updated: 2026-08-25
tags: [handoff, onboarding, install, configuration, dashboard]
related:
  - docs/roadmap/issue-AR-290-end-to-end-guided-setup.md
  - docs/decisions/0172-compose-first-run-setup-from-guarded-owner-operations.md
  - README.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-290
branch: codex/ar290-guided-setup-readme
evidence_commit: 737495633f0343e5a7553c1f00f166d493100d84
minimum_ledger_commit: 737495633f0343e5a7553c1f00f166d493100d84
hard_checkpoint_percent: 50
tracker_url: null
---

# AR-290 active recovery capsule

## checkpoint

- Isolated worktree
  `C:/Users/lucas/.codex/visualizations/2026/08/25/01a039fe-b601-7710-828e-6dc4f32dc4bb/agency-runtime-ar290-guided-setup`
  is on `codex/ar290-guided-setup-readme`, stacked from the clean AR-289 ledger
  checkpoint `73749563`; the dirty shared `main` checkout remains untouched.
- AR-290 and ADR-0172 define the bounded first-run orchestration and dashboard
  guidance contract. Tracker creation remains pending explicit authorization.
- Bootstrap telemetry reported 69.8 percent remaining, so no hard checkpoint
  was required before recording this clean planning pair.

## completed-evidence

- Existing `agency configure`, `agency install`, `agency config validate`,
  `agency doctor`, `agency smoke --all`, dashboard provider editing, and release
  checklist boundaries were audited.
- The current release checklist explicitly says the exact candidate is not
  release-ready: five-host Rule-4 evidence, benchmark outcomes, current artifact
  matrices, tracker synchronization, and publication authorization remain open.
- Product design preserves existing guarded mutations and keeps dashboard host
  installation copy-only.

## exact-blocker

- No implementation blocker is known. The release itself remains blocked by
  the canonical checklist; more local smoke alone cannot establish missing
  artifact, exact-host, tracker, signing, or publication evidence.
- Tracker creation, push, pull request, merge, hosted workflows, tag, and
  release creation are outward actions and remain unauthorized.

## same-task-continuity

Continue implementation and verification in this worktree. Recheck telemetry
before live evaluation and at package closeout. If the fixed threshold is met,
finish the smallest safe slice and create a clean substantive/ledger pair; do
not create another task or treat the threshold as publication authority.

## next-bounded-work-package

1. Add the setup orchestrator and parser/facade contract with focused tests.
2. Add the dashboard walkthrough and consumer README journey/prompt.
3. Run focused verification, the named fast spine, dashboard, documentation,
   routing, decision conformance, and release-readiness diagnostics.
4. Record exact evidence in this capsule and create the local implementation
   and worklog ledger commits.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python -m pytest <focused setup/config/install/parser tests> -q -W error
python -m pytest <named fast spine from AGENTS.md> -q -W error
node --test tests/dashboard_ui.test.mjs
agency eval routing --json --no-details
agency eval decision-conformance --repository . --json
git diff --check
~~~

## constraints

- Do not mutate, switch, clean, stage, or commit the shared checkout or the
  clean AR-289 worktree.
- Reuse guarded configuration, install, service, doctor, and smoke operations;
  do not duplicate their writers or bypass native harness trust.
- Do not add a dashboard host-install endpoint, shell execution surface, or
  claim that deterministic smoke is live host proof.
- Never put provider secrets in argv, output, documentation examples, Store
  evidence, or committed config. Use hidden input or environment-variable names.
- Keep `agency configure` backward-compatible and provider-focused.
- Do not create a tracker, push, open a PR, dispatch hosted workflows, publish,
  tag, sign, merge, or mutate this machine's installed runtime without explicit
  authorization.
