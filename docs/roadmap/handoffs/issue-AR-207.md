---
title: "AR-207 active recovery capsule"
status: active
category: roadmap
created: 2026-07-31
updated: 2026-07-31
tags: [handoff, preflight, delegation, codex, diagnostics, evidence]
related:
  - docs/roadmap/issue-AR-207-persist-preflight-delegation-failure-diagnostics.md
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-205-make-default-manager-inference-safe.md
  - docs/decisions/0112-stage-preflight-workforce-evidence-until-ready.md
  - docs/decisions/0116-bind-product-trials-to-exact-workspace-proof.md
  - docs/decisions/0120-construct-first-pass-evidence-headers.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-207
branch: codex/ar-204-readme-product-proof
evidence_commit: 581891c124cf6a51070b190091570f32fbff3709
minimum_ledger_commit: bdd0f521c3da0eb97fe48ed1986a387482ac1c53
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/196
---

# AR-207 active recovery capsule

## checkpoint

- The active goal remains `README's main story works in reality.`
- PR 195 merged exact revision
  `6b49f17d6787823f9ba78a8f09383001b6a77535`; build
  `0.1.0+g6b49f17d6787` is installed for Codex, ZCode, and dashboard.
- Supported-bypass activation passed with zero corrections under session
  `019fb82c-61bc-7490-825e-981975e39b91`, trace
  `019fb82c-6e14-74b1-add0-8021c121fdc2`, and route
  `3634b192-94c8-4083-8559-54c8313323e3`.
- Product trial `ar205-6b49f17-readme-01` is terminal `NO-GO`; its allowance is
  consumed and must not be rerun.
- Tracker issue [#196](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/196)
  owns the newly isolated content-free failure boundary.

## completed-evidence

- Exact activation proves inference-selected `code-reviewer`, one grant and
  consumption, specialist load, native spawn/wait, completed delegation,
  worker run, accepted finalization, and correction count zero.
- The product trial ran 100.174 seconds and exited one. Isolated workspace trust
  and supported bypass were proven without persistent-profile mutation.
- Product inference accepted eight verified work units and nine specialists:
  onboarding, Python, frontend, TypeScript, test, review, security, integration,
  and documentation roles.
- The product trace retained eight suggested delegations but zero activation
  grants, consumptions, loads, worker runs, or native spawn/wait events. Stop
  finalized `delegation_declined` with missing `delegation_execution`.
- The workspace remained empty, the proof sentinel was absent, response/header
  publication was absent, and validation correctly skipped as
  `workspace_write_not_proven`.
- A disabled-Agency control returned exact `PROBE_OK` on `gpt-5.6-sol`.
- A separate enabled read-only diagnostic produced an empty Codex turn and
  trace `019fb83f-3aa8-78f2-8f7c-06aaf71a7f0c`. It ended
  `preflight_failed` after 91.146 seconds with no route or model receipt.
- Direct Store inspection proves only `runs` retained that diagnostic trace.
  The source catch path currently discards the original exception and pending
  inference attempts.
- Reconstructed product preflight context is 8,471 characters; combined with
  its header it is about 2,414 Codex tokens, below the host's default spill
  threshold. Context spill is a robustness gap, not the proven cause.

## exact-blocker

Selection and exact installation work. The README trial fails after accepted
staffing but before native delegation execution, while the adjacent preflight
failure path erases the information needed to repair that boundary without
replay.

## same-task-continuity

Keep inference authoritative and the parent non-generalist. Do not rerun any
trial on `cc322381`, `f0fde9ee`, or `6b49f17d`. Do not mutate private trust
state, label bypass as trust, dispatch hosted Actions, or touch the owner's two
untracked files.

## next-bounded-work-package

1. Persist and project a bounded content-free preflight failure receipt.
2. Add bounded parent hook/turn facts that distinguish injection, output,
   spawn/wait, and Stop reconciliation for accepted routes.
3. Run focused tests and decision mutations; use bounded diagnostics to repair
   the first demonstrated execution cause.
4. Complete at most two review passes, run the named fast spine, merge, and
   exact-install before one fresh product trial.
5. Produce the local shareable evidence page and OpenClaw handoff after the
   terminal exact-build trial.

## verification

~~~text
python scripts/context_handoff_status.py --json --threshold 50
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python -m pytest <focused AR-207 boundary> -q -W error
python -m pytest <named fast spine from AGENTS.md> -q -W error
node --test tests/dashboard_ui.test.mjs
agency eval routing --json --no-details
agency eval decision-conformance --repository . --json
git diff --check
~~~

## constraints

- Product host remains sandboxed to the exact trial workspace.
- Only Codex, ZCode, and dashboard are in machine scope.
- One live product trial per exact installed build; any correction is failure.
- Durable diagnostics are content-free and allowlisted.
- Hosted Actions remain out of scope while GitHub spending is unavailable.
