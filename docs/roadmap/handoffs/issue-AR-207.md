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
  - docs/decisions/0122-use-one-agency-native-resident-steward.md
  - docs/decisions/0124-grade-product-trials-against-the-inferred-unit-graph.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-207
branch: codex/ar-207-codex-host-notice-percent
evidence_commit: 5328070cd048f42ce88e3bcb16e42f1e69cfae24
minimum_ledger_commit: e492782cd2ce68bb1a69347eb7f2aa9e6bc41cf9
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/196
---

# AR-207 active recovery capsule

## checkpoint

- The active goal remains `README's main story works in reality.`
- PR 197 merged exact revision
  `3b5a00f7564e29aaf0ec68bd09547f8b8fa42c2e`; VCS build
  `0.1.0+g3b5a00f7564e` was exact-installed for Codex, ZCode, and dashboard.
- Activation execution on that build completed the exact specialist lifecycle
  with zero corrections, but the canary failed because one Codex 0.146
  non-critical warning was classified as a non-allowlisted tool.
- No product trial was spent on `3b5a00f`. Three bounded activation diagnostics
  are consumed and must not be rerun on that build.
- PR 198 merged the first repair as
  `5328070cd048f42ce88e3bcb16e42f1e69cfae24`; it was exact-installed as an
  official VCS package. The default install discovered Codex and ZCode,
  registered both, and installed a reachable dashboard.
- Activation on `5328070` completed the exact `code-reviewer` lifecycle and
  zero-correction header, then failed closed on Codex's exact `2% skills
  context budget` sentence. One bounded raw-JSONL diagnostic proved two exact
  bypass notices plus that one sentence with Codex exit zero.
- The installed Codex binary contains both its generic and `2%` skill notice
  spellings. The follow-up branch admits only that second exact sentence under
  the existing content-free notice type. All 25 warning-strict
  activation-canary tests pass; arbitrary and near-miss errors remain fatal.
- The follow-up named fast spine is green: 636 Python tests passed with six
  skips, dashboard UI passed 110, docs validated 584, Ruff checked/formatted
  603, routing passed every gate, and all 63 curated mutations were killed with
  zero survivors or invalid mutations. Source restoration passed.
- End-of-package context telemetry reported 37.1 percent remaining and requires
  this fast-green follow-up to be sealed as a substantive/ledger recovery pair
  before push. Continue in this same task after that checkpoint.

## completed-evidence

- Activation session `019fb8da-969a-75d3-9ad7-686094d35324`, trace
  `019fb8da-a3c4-78d0-bfc5-44cf6d9ea1c1` proved `code-reviewer`, one grant,
  consumption, load, worker, native child, completed delegation, accepted
  finalization, valid first-pass header, and correction count zero.
- Its persisted parent rollout contains only `spawn_agent` and `wait_agent`;
  Store activation evidence is proven. No repository, shell, MCP, or product
  tool ran in the parent.
- Exact-installed activation session `019fb90b-dc97-7db0-891a-3aeea357ed3b`,
  trace `019fb90b-e95d-7bf2-84ae-fd0efb150816`, selected `code-reviewer` and
  persisted one route, unit, grant, consumption, load, worker, native child,
  completed delegation, and accepted finalization. Its header was valid and
  correction count was zero; Store evidence was `proven=true`.
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
- The named warning-strict Python spine passed 636 tests with six skips;
  dashboard UI passed 110 tests; routing passed every gate; all 63 curated
  decision mutations were killed with zero survivors or invalid mutations;
  source restoration and `git diff --check` passed.
- Documentation validation passed all 584 maintained Markdown files.
- Builds and trials `cc322381`, `f0fde9ee`, and `6b49f17d` remain consumed and
  must not be rerun.

## exact-blocker

The first host-notice repair admitted Codex's generic packaged sentence but the
live 0.146 host emitted its packaged `2%` variant. The narrow follow-up is now
fast-green and mutation-sensitive; it still needs review, merge, exact install,
and one new-build activation canary. The product trial remains unspent until
activation is green.

## same-task-continuity

Keep inference authoritative and the parent non-generalist. Do not rerun any
trial on `cc322381`, `f0fde9ee`, or `6b49f17d`. Do not mutate private trust
state, label bypass as trust, dispatch hosted Actions, or touch the owner's two
untracked files.

## next-bounded-work-package

1. Commit, review, merge, and exact-install the narrow `2%` notice follow-up.
2. Prove exact-build activation with the supported hook bypass once.
3. Spend one fresh 1,800-second product trial on that exact build.
4. Prove a fresh-task `agency-steward` plus specialist header, then produce the
   local shareable evidence page and OpenClaw handoff.

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
- Do not rerun activation diagnostics on exact build `3b5a00f`.
- Do not rerun activation on exact build `5328070`; its one canary and bounded
  raw-message diagnostic are complete.
- Durable diagnostics are content-free and allowlisted.
- Hosted Actions remain out of scope while GitHub spending is unavailable.
