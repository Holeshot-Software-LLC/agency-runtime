---
title: "AR-203: Prove product-canary workspace writes and exact activation"
status: open
category: roadmap
created: 2026-07-30
updated: 2026-07-30
tags: [evaluation, codex, activation, sandbox, evidence, regression]
related:
  - docs/decisions/0077-prove-codex-activation-behaviorally.md
  - docs/decisions/0112-stage-preflight-workforce-evidence-until-ready.md
  - docs/roadmap/issue-AR-200-diagnosable-decision-conformance.md
  - docs/roadmap/issue-AR-201-fund-default-workforce-repair.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-203
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/183
depends_on: [AR-201]
blocks: [AR-200]
---

# AR-203: Prove product-canary workspace writes and exact activation

## Problem

The AR-201 product trial exposed two independent harness defects. First,
`execute_product_host` collected the legacy recent-activity summary and passed
it to the Codex proof evaluator, which now requires
`agency.canary-activation-evidence.v1`. The evaluator therefore reported
`exact Codex activation evidence contract was not available` even though a
direct post-trial Store query returned that exact schema with `proven: true`.

Second, the fresh isolated Codex response reported that application work was
blocked by a read-only workspace policy despite the product command requesting
`--sandbox workspace-write`. The trial created no files. The isolated profile
does not inherit the current profile's trusted-project entries, and existing
tests assert only the requested CLI flag, not the effective model-facing write
contract.

## Current state

The Codex process completed with exit zero and the isolated Agency plugin was
registered and enabled. It emitted one route, three correlated model receipts,
and two finalization rows. The exact Store snapshot resolves the trial trace,
but the product report used the incompatible summary projection. Collaboration
projection also observed eight non-allowlisted command/MCP items and no Agency
spawn/wait chain because staffing abstained.

The product backend runs inside a private temporary Codex home and already
bypasses hook trust only for the vetted isolated plugin. It does not yet create
a trial-scoped trusted-project entry or otherwise prove the effective
workspace-write state before grading artifacts.

## Approach

1. For Codex Agency product trials, read the exact activation snapshot by host
   and prompt hash, matching the ordinary activation canary proof contract.
2. Keep legacy recent-activity summaries only for modes and hosts whose proof
   contract expects them.
3. Bind any isolated trusted-project configuration to the one existing empty
   trial directory and the private temporary Codex home; never mutate the
   owner's persistent trust configuration.
4. Add a host-level write probe whose success is attributable to the same
   effective Codex workspace policy, and fail before product grading when that
   contract is not proven.
5. Add regressions that fail under the current summary mismatch and under an
   isolated read-only profile.
6. Preserve product safety: no general sandbox bypass and no write authority
   outside the confirmed trial directory.

## Dependencies

ADR-0077 owns behavioral activation proof. ADR-0112 owns exact staged evidence
and accepted finalization. AR-201 supplies the exact terminal trace that
demonstrates both mismatches.

## Acceptance

- [ ] Codex Agency product evaluation reads
  `agency.canary-activation-evidence.v1` for the exact prompt hash and never
  reports that schema unavailable when the Store returns it.
- [ ] The isolated Codex profile proves effective workspace-write authority for
  the exact empty trial directory without changing persistent user trust.
- [ ] The product backend retains sandboxing and cannot write outside the trial
  directory.
- [ ] A failed write proof stops before grading and is reported separately from
  workforce selection or product-quality failures.
- [ ] Focused tests fail against both current defects and pass after repair.
- [ ] The next ordinary canary reports exact activation evidence and can create
  required artifacts when workforce execution reaches the parent model.
