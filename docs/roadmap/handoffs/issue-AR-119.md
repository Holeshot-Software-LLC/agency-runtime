---
title: "AR-119 active recovery capsule"
status: active
category: roadmap
created: 2026-07-23
updated: 2026-07-25
tags: [handoff, routing, workforce, evaluation, recovery, production-readiness]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/decisions/0087-inference-decides-from-a-relevance-shortlist.md
  - docs/decisions/0088-deterministic-typed-recall-offline-floor.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
branch: main
evidence_commit: 5001d7873c80efeceaf5eeb0d347e3e559e619e3
minimum_ledger_commit: 5001d7873c80efeceaf5eeb0d347e3e559e619e3
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

- `main` and `origin/main` are aligned at `5001d78`; `git pull --ff-only origin
  main` reported already up to date on 2026-07-25.
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
- Local roster search found governed fits for the requested audits:
  `application-security-engineer`, `performance-benchmarker`, and
  `application-integration-verifier`. A configured-provider route containing
  private repository audit detail was denied by the execution boundary, so no
  inference selection or delegation receipt is claimed. Three native isolated
  read-only review workers are running with those explicit specialist contracts.

## exact-blocker

- Normal-profile Codex activation requires user-owned terminal-TUI hook review
  and a subsequent fresh task. The installer correctly refuses to automate or
  bypass that trust decision.
- AR-119/AR-125 still lack a benchmark-valid completed value corpus and current
  production-candidate evidence across all claimed host/OS surfaces. Historical
  malformed or timed-out upstream arms remain validity failures, never losses.
- The security, optimization, and per-layer UI-to-SQL trace audits are in
  progress. No unverified audit hypothesis is a finding or remediation mandate.

## same-task-continuity

Context thresholds never create, fork, transfer, or stop this task. At or below
50 percent, create a durable local recovery/ledger pair and continue in the
same persistent goal through normal compaction.

## next-bounded-work-package

1. Finish the first specialist wave and dispatch separate trace workers for
   HTTP-to-service, service-to-store, store-to-SQL/schema, and host/delegation
   authority boundaries.
2. Consolidate only reproduced findings into a severity report and governed
   AR issue records; keep suggestions and residual risks separate.
3. Immediately after telemetry, exercise the synthetic dashboard Routing Lab
   task and exact-confirmed isolated Codex canary; record source, package,
   plugin-cache, model, routing, activation, and finalization identities.
4. Implement prioritized verified findings in bounded slices with focused tests,
   reinstall after each installed-surface change, and finish with the complete
   repository/release gates.

## verification

~~~text
git pull --ff-only origin main                         # already up to date
agency install --agent codex --dry-run --json          # complete plan
agency install --agent codex --json                    # partial: activation-required
agency doctor --json --verbose                         # DEGRADED: hook trust only
in-app dashboard desktop/mobile/authenticated smoke    # clean console, no overflow
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
