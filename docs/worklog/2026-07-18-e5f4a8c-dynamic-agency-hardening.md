---
title: "Worklog detail: Harden dynamic Agency orchestration"
status: active
category: worklog
created: 2026-07-18
updated: 2026-07-18
tags: [routing, delegation, roster, security, dashboard, portability]
related:
  - docs/roadmap/README.md
  - docs/decisions/README.md
  - docs/RELEASE_CHECKLIST.md
supersedes: []
superseded_by: null
type: worklog
commit: e5f4a8c2ab6cc0411139b7ee96f22ad2befa7daf
short: e5f4a8c
date: 2026-07-18
pr: null
related_issues:
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
  - docs/roadmap/issue-AR-25-turn-scoped-specialist-evidence.md
  - docs/roadmap/issue-AR-57-durable-agency-wide-master-switch.md
  - docs/roadmap/issue-AR-79-installed-isolated-header-proof.md
  - docs/roadmap/issue-AR-85-state-aware-turn-classification.md
  - docs/roadmap/issue-AR-86-govern-complete-upstream-roster-lifecycle.md
  - docs/roadmap/issue-AR-97-reconcile-required-inference-remediation.md
---

# Worklog detail: Harden dynamic Agency orchestration

## Purpose

Turn Agency Runtime into the intended per-ask employee pool: a compact resident
coordination kernel, the complete governed specialist roster, turn-scoped
selection and evidence, compatible multi-agent loading, and complementary
native delegation across Codex, Claude Code, Hermes, and OpenClaw on Windows
and Linux. The same change closes the security, portability, dashboard,
configuration, packaging, performance, and code-quality defects discovered by
the full production review.

## Approach

Separate durable roster cards from prompt hydration, classify each turn from
durable state, retrieve against the complete approved and enabled roster, and
require configured inference for selection. Resolve hard conflicts before any
specialist enters a shared context; route independent work units separately and
let the native host own process or sub-agent execution while Agency supplies
bounded assignments and records authoritative evidence.

Package all audited upstream definitions, preserve a compact protected
Agents Orchestrator and Chief of Staff contract, expose fail-safe master/host/
agent controls through the same CLI and dashboard configuration service, and
keep requested model, LiteLLM router, and reconciled actual model as distinct
receipts. Harden storage, executable, subprocess, service, and migration
boundaries and split oversized modules along cohesive responsibilities.

For roster ingestion, repair only exact reviewed source hashes, retain immutable
offset and transformation receipts, quarantine unknown or ambiguous input, and
keep remediation separate from approval and activation. A post-audit
transaction now reconciles eligible remediation in the same required-inference
ingestion without trusting a raw resolution event.

## Challenges encountered

The review found migration-order failures that appeared only against an older
real dashboard database, restricted-Windows path and ACL races, stale
turn-correlation loops, router aliases misreported as actual models, and two
upstream prompt files with distinct encoding corruption. A final adversarial
review also found that successful required inference did not reconcile a queued
repair until a second ingestion. Exact branch coverage exposed nine residual
defensive arcs after all 5,795 non-performance tests already passed; isolated
fail-closed tests closed them without changing production behavior.

## Decisions and alternatives

Complete upstream prompts do not remain resident in the parent context.
Coordinators keep a compact hash-bound contract, selected specialists last for
one turn or one native child assignment, and all workers return to the pool.
Configured inference is mandatory rather than advisory. Agency recommends and
records native delegation but does not replace a host's executor. Conflict
resolution occurs after candidate retrieval and before prompt composition.

Broad best-effort text normalization was rejected because it could silently
change agent meaning. Known-hash remediation yields a governed candidate only;
semantic/inference audit and explicit activation remain separate authorities.
Unknown hashes stay quarantined.

## Verification

- Python: 5,795 passed, 19 skipped, 3 deselected with warnings as errors.
- Coverage: 38,692 statements and 13,054 branches at exactly 100.00 percent.
- Performance: 3 passed; routing p95 2.458 ms, cache p95 0.696 ms, and 116.75 calls/second.
- Dashboard: 87 passed at 100 percent line, branch, and function coverage.
- Routing: all 25 gates passed; top-1, top-k, and required recall were 1.0.
- Delegation: 12 of 12 passed.
- Full roster: all 263 approved agents participated; recall was 1.0 with no prompt or identity leakage.
- Security: release hygiene, Bandit high-severity, dependency audit, and zizmor passed.
- Documentation: metadata, links, tracker mapping, policy availability, and worklog validation passed.

## Follow-ups

Build and verify the committed wheel/source archive, install it into the local
Codex profile, run the isolated canary and dashboard service/browser smoke,
then obtain hosted Windows/Linux CI evidence, merge the reviewed pull request,
and reconcile tracker states. Public tagging or package publication remains a
separate authorization-gated action.
