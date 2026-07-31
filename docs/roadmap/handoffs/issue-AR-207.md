---
title: "AR-207 active recovery capsule"
status: active
category: roadmap
created: 2026-07-31
updated: 2026-07-31
tags: [handoff, preflight, delegation, codex, diagnostics, evidence]
related:
  - docs/roadmap/issue-AR-207-persist-preflight-delegation-failure-diagnostics.md
  - docs/roadmap/issue-AR-209-bind-opaque-codex-child-launches.md
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-205-make-default-manager-inference-safe.md
  - docs/decisions/0112-stage-preflight-workforce-evidence-until-ready.md
  - docs/decisions/0116-bind-product-trials-to-exact-workspace-proof.md
  - docs/decisions/0120-construct-first-pass-evidence-headers.md
  - docs/decisions/0122-use-one-agency-native-resident-steward.md
  - docs/decisions/0124-grade-product-trials-against-the-inferred-unit-graph.md
  - docs/decisions/0126-authorize-exact-product-delegation-at-the-codex-developer-boundary.md
  - docs/decisions/0127-bind-opaque-codex-children-through-exact-plan-labels.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-207
branch: codex/ar-207-exact-product-proof
evidence_commit: 552eb05aa47ba1e44bf7ae8e0743bcc0cfdde513
minimum_ledger_commit: abd5ba95d3954196aedbc38a835f27494aca6b92
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/196
---

# AR-207 active recovery capsule

## checkpoint

- The active goal remains `README's main story works in reality.`
- Earlier exact-build host-notice diagnostics and the `5ad4aef` product trial
  are consumed. Their bounded evidence remains canonical in AR-207.
- PR 202 merged ADR-0126's authority repair as exact revision
  `584b949d75d013611c0fe3d26835f3057fc83466`; its official VCS package is
  exact-installed as `0.1.0+g584b949d75d0`.
- Default install discovered only Codex and ZCode, registered both, and reached
  the dashboard. Supported-bypass activation then passed with inferred and
  executed `code-reviewer`, a valid first-pass header, and zero corrections.
- Product trial `ar207-584b949-readme-01` is consumed and terminal `NO-GO`.
  Inference accepted eight units; Codex attempted the first native spawn, but
  no child started and no wait followed. All delegations remained `suggested`.

## completed-evidence

- Exact-installed activation session `019fb9ba-b711-71f1-b7a8-746ae7e4b42f`,
  trace `019fb9ba-c746-7341-8cd5-1e5b23b0f7dc`, and run
  `5df7f288-bc5e-4fbb-94fe-602c56b7d21f` passed on `584b949`. Inference
  selected `code-reviewer`; one route, grant, consumption, load, worker,
  native child, completed delegation, and accepted finalization persisted.
  Header validity and Store evidence were proven with correction count zero.
- Product session `019fb9bf-8db3-7022-8acd-da0a80f8834b`, trace
  `019fb9bf-8e2d-7691-b469-684c6e109872`, and run
  `8be205d8-dba0-4058-84b6-384cf774531c` reached an accepted eight-unit route.
  Parent rollout evidence contains one spawn call and its output, but zero
  child starts or waits. Finalization was `delegation_declined`; workspace
  trust and bypass were proven, workspace write was not, and corrections were zero.
- Two retained real-host spawns prove Codex encrypts arbitrary child messages
  before Agency's `PreToolUse` equality check. The old path recovered only the
  fixed canary goal, explaining why activation passed while product delegation
  could not start.
- AR-209's source candidate admits only a strictly shaped opaque Codex message
  whose native task label resolves exactly one persisted plan row. It preserves
  the ciphertext, stages the exact grant, injects a token-free v2 specialist
  context with the persisted goal hash at `SubagentStart`, and consumes it
  against the observed child.
- The candidate passes 97 focused warning-strict tests. Its arbitrary-goal
  real-Store regression proves grant consumption, specialist load, worker
  identity, and completed delegation. Both focused decision mutations are
  killed with unchanged source.
- The complete named fast spine is green: 593 docs, 603 Ruff files, 636
  warning-strict Python tests with six skips, 110 dashboard tests, every routing
  gate, and all 69 decision mutations with zero survivors or invalid results.
  The evaluator baseline passed and source remained unchanged.
- Product session `019fb92d-694c-7e42-b553-ee53802bac99`, trace
  `019fb92d-69c3-7541-bc96-ae0c72126a25`, and run
  `56389325-9128-470b-945c-b3951bc37248` ended `preflight_failed` with stage
  `routing`, reason `routing_failed`, exception category `validation_error`,
  and zero provider attempts. Its exact workspace remained empty.
- Cloned replay session `a851fa51-aff6-4f9a-8f6f-7941d0af7111`, trace
  `53c878e2-37e3-4c4d-ac0e-708c1e7fe72c`, and run
  `24a13190-37dc-40b0-85b8-e87ec3ad75ae` reached preflight `ready` in 73.607
  seconds. It planned eight units and selected `codebase-onboarding-engineer`,
  `python-application-engineer`, `typescript-application-engineer`,
  `software-test-engineer`, `code-reviewer`,
  `application-security-engineer`, `application-integration-verifier`, and
  `technical-writer`. It did not execute or grade the product.
- Codex 0.146 maps non-critical Warning, ConfigWarning, DeprecationNotice, and
  ModelRerouted notifications to completed JSONL items whose type is `error`.
- The exact parent catalog retained all 67 skills but removed 11,805
  description characters, averaging 177 per skill. Codex's threshold is 100,
  so its exact skill-catalog-shortening notice was deterministic. The exact
  sentence is also present in the installed Codex binary.
- The repair projects `host_notice_count` and fixed `host_notice_types` without
  retaining messages. Exact hook-bypass and skill-shortening notices pass;
  arbitrary and one-character near-miss `error` messages remain unexpected.
- Both accepted and rejected projections were proven to exclude the original
  warning and near-miss message text.
- Schema v39 now writes one immutable content-free preflight failure receipt
  atomically with terminal cleanup and exposes it through exact activation,
  status, and dashboard projections.
- Product rollout evidence now accepts one through sixteen exact specialist
  children, correlates each child to the parent session and persisted unit, and
  removes all child prompts, tool arguments, outputs, and final messages.
- Product proof requires every planned unit's delegation, grant, consumption,
  specialist load, worker lifecycle, exact child prompt delivery, and completed
  child. Extra parent product tools, missing rows, correction count above zero,
  or failed workspace-write evidence are terminal failures.
- The focused product-host suite passed 21 tests; the named warning-strict
  Python spine passed 636 tests with six skips; dashboard UI passed 110 tests;
  documentation validated 589 files; Ruff checked and formatted 603 files;
  and `git diff --check` passed.
- The workspace routing evaluation passed every gate, including 1.466 ms
  cache-hit p95 and the 10,000-agent tier. Decision conformance passed its
  63.797-second baseline, killed all 66 mutations with zero survivors or
  invalid results in 566.9 seconds, and proved the source tree unchanged.
- Builds and trials `cc322381`, `f0fde9ee`, `6b49f17d`, and `5ad4aef` remain
  consumed and must not be rerun.

## exact-blocker

Exact build `584b949` is consumed: activation passed, but its product trial is
terminal `NO-GO`. AR-209's first-spawn repair is focused- and named-fast-green
but not yet reviewed, merged, or exact-installed. No new live run is allowed
before those boundaries pass.

## same-task-continuity

Keep inference authoritative and the parent non-generalist. Do not rerun any
trial on `cc322381`, `f0fde9ee`, `6b49f17d`, or `5ad4aef`. Do not mutate private
trust state, label bypass as trust, dispatch hosted Actions, or touch the
owner's two untracked files.

## next-bounded-work-package

1. Review, merge, and exact-install the AR-208/AR-209 repair.
2. Repeat one activation and at most one product trial on the new exact build,
   then produce the local shareable evidence page and OpenClaw handoff.

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
.venv\Scripts\agency.exe eval routing --json --no-details
.venv\Scripts\agency.exe eval decision-conformance --repository . --json
git diff --check
~~~

## constraints

- Product host remains sandboxed to the exact trial workspace.
- Only Codex, ZCode, and dashboard are in machine scope.
- One live product trial per exact installed build; any correction is failure.
- Do not rerun activation diagnostics on exact build `3b5a00f`.
- Do not rerun activation on exact build `5328070`; its one canary and bounded
  raw-message diagnostic are complete.
- Do not rerun activation or the product trial on exact build `5ad4aef`; both
  terminal results are recorded.
- Do not rerun the passed activation or failed product trial on `dd85e7d`.
- Do not rerun the activation or product trial on `584b949`.
- Durable diagnostics are content-free and allowlisted.
- Hosted Actions remain out of scope while GitHub spending is unavailable.
