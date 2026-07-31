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
branch: codex/ar-207-codex-host-notice
evidence_commit: 3b5a00f7564e29aaf0ec68bd09547f8b8fa42c2e
minimum_ledger_commit: 71ba70633b32ab3e7db81d99b59f0d4815ed3085
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
- The repair and two bounded review passes are complete on
  `codex/ar-207-codex-host-notice`; all 25 warning-strict activation-canary
  tests pass, and all 63 curated mutations are killed with zero survivors or
  invalid mutations. This capsule is part of the substantive recovery
  checkpoint; the following ledger commit records its exact SHA.
- Context telemetry reported 48.5 percent remaining; the clean merged
  substantive/ledger checkpoint was reused before this bounded package.

## completed-evidence

- Activation session `019fb8da-969a-75d3-9ad7-686094d35324`, trace
  `019fb8da-a3c4-78d0-bfc5-44cf6d9ea1c1` proved `code-reviewer`, one grant,
  consumption, load, worker, native child, completed delegation, accepted
  finalization, valid first-pass header, and correction count zero.
- Its persisted parent rollout contains only `spawn_agent` and `wait_agent`;
  Store activation evidence is proven. No repository, shell, MCP, or product
  tool ran in the parent.
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
  dashboard UI passed 110 tests; routing passed every gate; all 62 curated
  decision mutations were killed with zero survivors or invalid mutations;
  source restoration and `git diff --check` passed.
- Documentation validation passed all 582 maintained Markdown files, and
  context telemetry reported 85.2 percent remaining before the prior
  checkpoint.
- Builds and trials `cc322381`, `f0fde9ee`, and `6b49f17d` remain consumed and
  must not be rerun.

## exact-blocker

The post-merge Codex 0.146 host-notice contradiction is repaired, reviewed,
focused-green, and mutation-sensitive. The next gate is the named fast spine,
then merge, exact install, and one fresh activation canary. The product trial
remains unspent until activation is green.

## same-task-continuity

Keep inference authoritative and the parent non-generalist. Do not rerun any
trial on `cc322381`, `f0fde9ee`, or `6b49f17d`. Do not mutate private trust
state, label bypass as trust, dispatch hosted Actions, or touch the owner's two
untracked files.

## next-bounded-work-package

1. Run the named fast spine for the host-notice repair.
2. Create the substantive and ledger checkpoints, push, review, merge, and
   exact-install Codex, ZCode, and dashboard once.
3. Prove exact-build activation with the supported hook bypass.
4. Spend one fresh 1,800-second product trial on that exact build.
5. Prove a fresh-task `agency-steward` plus specialist header, then produce the
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
- Durable diagnostics are content-free and allowlisted.
- Hosted Actions remain out of scope while GitHub spending is unavailable.
