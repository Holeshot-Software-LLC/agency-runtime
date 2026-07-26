---
title: "AR-119 active recovery capsule"
status: active
category: roadmap
created: 2026-07-23
updated: 2026-07-26
tags: [handoff, routing, workforce, evaluation, recovery, production-readiness]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/decisions/0087-inference-decides-from-a-relevance-shortlist.md
  - docs/decisions/0088-deterministic-typed-recall-offline-floor.md
  - docs/analysis/2026-07-26-production-readiness-review.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
branch: main
evidence_commit: c5e3575beacfb3170d2f2b0092c0e7379347011f
minimum_ledger_commit: de47a8c690280f07757437cd5aed11d416d7b9a1
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Bounded current-state projection for AR-119. The
[canonical issue](../issue-AR-119-inference-first-workforce.md) owns the full
acceptance contract. ADR-0087 governs configured inference; ADR-0088 adds the
truthfully stamped deterministic typed-recall floor only when inference is not
configured.

## checkpoint

- `origin/main` remains `5001d78`; local `main` was four governed commits
  ahead at `22c9f33` before the current Wave 1 implementation checkpoint.
- The pre-existing untracked
  `docs/analysis/2026-07-25-deep-audit-findings.md` is preserved unchanged and
  excluded from checkpoint commits until its hypotheses are independently
  verified and promoted through roadmap governance.
- Live umbrella [#132](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132)
  remains open. AR-125 also remains open; tracker mutation and closure are not
  authorized by this local package.

## completed-evidence

- Fresh Codex installation removed and re-added the managed plugin, retained a
  backup at `20260726T020704.952997Z`, installed bundle digest
  `f6a49f839765a94be5de481a73fa5483bfa9bb1df17d59f862fe0bc985b38366`,
  preserved 9 governed contractors, and started the owner-scoped dashboard from
  immutable launcher root `runtime-sha256-3caf93fd3dc3acb9bb5c001f91908c074b61b1246b5fc847018f7c62844edc2a`.
- Installation truth is partial, not promoted: Codex is registered and enabled,
  while normal-profile hook trust is `activation-required`; no trust store was
  read or changed and no host restart was claimed.
- `agency doctor --json --verbose` passed config, SQLite integrity, schema 35,
  the 272-agent roster, authenticated Codex judge, and its one-provider chain.
  Overall status is `DEGRADED` solely because normal-profile Codex hook trust is
  unverified.
- The freshly installed dashboard service is registered, definition-current,
  reachable, and authenticated on loopback. Browser QA found a clean console,
  no page-level overflow at a 390 px viewport, accessible section navigation,
  272 active specialists, and truthful Codex `activation-required` / ZCode
  `staged-not-registered` labels.
- The current task's already-loaded MCP process fails closed for both preflight
  and status with only a generic diagnostic. This is not evidence about the
  refreshed plugin in a new Codex task; the isolated canary and a fresh-task
  check remain required.
- Independent security, optimization, UI-to-HTTP, HTTP-to-service, CLI/MCP,
  host-hook, Store-to-SQL, and schema traces are complete. The governed report
  is `docs/analysis/2026-07-26-production-readiness-review.md` and the reproduced
  remediation queue is AR-128 through AR-142.
- A telemetry-gated installed Routing Lab replay produced the canonical
  `required_agents_missing` / `no_safe_sufficient_team` gap and no hire. Direct
  reproduction proved the hiring allowlist omits that legitimate reason.
- Focused probes reproduced three unreachable MCP tools, a 206-byte release
  asset overage, stale Store trust, incomplete schema currentness, ZCode
  install/activation failure, process-local child correlation, and planned
  delegation fail-open behavior. No Critical security finding was confirmed.
- Wave 1 plus schema 36 is locally coherent: MCP/broker reads are bounded and
  read-only, subprocess environments are least-privilege, Store trust is
  revalidated, canonical safe staffing gaps can hire cumulatively, critical
  SQLite objects are exact-current, and packaged assets are 263,151 bytes
  against the unchanged 263,168-byte ceiling.
- Independent checkpoint verification passed 785 Python tests with 9 skips, 97
  dashboard interaction tests, full Ruff and format checks across 543 files,
  and `git diff --check`.
- A second security pass reproduced a new High: the model-callable in-app
  Browser can automate the owner dashboard's static-confirmation mutations.
  AR-143 and ADR-0096 now govern genuine operator presence; AR-128 remains open.
- AR-136 now includes the forged parseable activation-marker bypass. AR-135
  records the exact local ZCode 3.5.2 seven-event config/payload contract and
  rejects invented marketplace commands.

## exact-blocker

- Normal-profile Codex activation requires user-owned terminal-TUI hook review
  and a subsequent fresh task. The installer correctly refuses to automate or
  bypass that trust decision.
- AR-128 through AR-139 plus AR-143 include P0 production blockers and must
  close before renewed production claims. AR-140 through AR-142 own measured
  performance, compatibility/consolidation, and cross-layer instrumentation.
- AR-119/AR-125 still lack a benchmark-valid completed value corpus and current
  production-candidate evidence across all claimed host/OS surfaces. Historical
  malformed or timed-out upstream arms remain validity failures, never losses.
- Tracker creation for AR-128 through AR-142, push/PR/hosted checks, and
  normal-profile Codex trust remain authorization or user-presence boundaries.

## same-task-continuity

Context thresholds never create, fork, transfer, or stop this task. At or below
50 percent, create a durable local recovery/ledger pair and continue in the
same persistent goal through normal compaction.

## next-bounded-work-package

1. Create the current substantive/ledger checkpoint without touching the
   preserved untracked 2026-07-25 draft.
2. Implement AR-143's read-only dashboard/operator-boundary correction, then
   AR-133 atomic finalization and AR-135/AR-136 ZCode/native lineage as isolated
   packages.
3. Continue complete dashboard collections/coherence/instrumentation, then
   performance and compatibility work.
4. Reinstall canonical source, run installed protocol/UI/hiring/native dogfood,
   complete AR-125, and finish the full repository/release gates.

## verification

~~~text
git pull --ff-only origin main                         # already up to date
agency install --agent codex --dry-run --json          # complete plan
agency install --agent codex --json                    # partial: activation-required
agency doctor --json --verbose                         # DEGRADED: hook trust only
in-app dashboard desktop/mobile/authenticated smoke    # clean console, no overflow
focused MCP protocol / release / Store / hook probes   # reproduced blockers
combined Wave 1 checkpoint suite                       # 785 passed, 9 skipped
node --test tests/dashboard_ui.test.mjs                # 97 passed
python scripts/context_handoff_status.py --json --threshold 50
~~~

## constraints

- Telemetry immediately before every live evaluation or canary.
- Never weaken typed coverage/parser validation, add scenario routes, increase
  the fixed 15000 ms cold or one-call fast budgets after observing results, or
  reinterpret malformed upstream output.
- Do not claim Agency superiority without a benchmark-valid measured corpus.
- Do not claim native loading, a model receipt, specialist load, delegation,
  contractor hire, or host canary without the exact corresponding evidence.
- No push, PR, hosted Actions, publication, tracker creation/edit/closure, tag,
  or release without explicit outward-action authorization.
