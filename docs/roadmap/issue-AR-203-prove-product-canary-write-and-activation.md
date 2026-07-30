---
title: "AR-203: Prove product-canary workspace writes and exact activation"
status: in_progress
category: roadmap
created: 2026-07-30
updated: 2026-07-30
tags: [evaluation, codex, activation, sandbox, evidence, regression]
related:
  - docs/decisions/0077-prove-codex-activation-behaviorally.md
  - docs/decisions/0112-stage-preflight-workforce-evidence-until-ready.md
  - docs/decisions/0116-bind-product-trials-to-exact-workspace-proof.md
  - docs/roadmap/issue-AR-200-diagnosable-decision-conformance.md
  - docs/roadmap/issue-AR-201-fund-default-workforce-repair.md
  - docs/roadmap/handoffs/issue-AR-203.md
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

The terminal AR-203 trial exposed an earlier activation boundary as well. The
ordinary product backend still launched Codex with `--ephemeral` and without
`multi_agent_v2` or `agents.enabled=true`, even though the installation
activation canary had already removed ephemeral mode and enabled both native
agent controls. The product hook child also did not require the pre-existing
evidence Store, and its result projection could not distinguish a hook that
never started from one that accepted an event and then failed.

## Current state

The Codex process completed with exit zero and the isolated Agency plugin was
registered and enabled. It emitted one route, three correlated model receipts,
and two finalization rows. The exact Store snapshot resolves the trial trace,
but the product report used the incompatible summary projection. Collaboration
projection also observed eight non-allowlisted command/MCP items and no Agency
spawn/wait chain because staffing abstained.

The product backend now writes one exact trusted-project entry into only the
private temporary Codex home and verifies a hash-only attestation for that
canonical workspace. It retains the workspace-write sandbox with no added write
directory or general sandbox bypass. The same model invocation must create a
fixed, prompt-bound sentinel; missing or unproven write evidence skips product
grading, and a preexisting sentinel is rejected.

Codex Agency mode now queries the exact activation snapshot using the hash of
the wrapped prompt actually sent to the host while retaining the canonical
product prompt hash separately. Focused review passes 85 tests. The two new
product decision mutations are killed inside the 13/13 decision-conformance
gate with zero survivors or invalid results. The named fast production spine
passes 675 tests with 6 skipped, the dashboard UI passes 109 tests, and routing
evaluation 1.3.0 passes every configured gate.

PR 184 merged normally as exact main revision
`dbd5502847b822825c7f3b99a18662949c98de0b`; exact build
`0.1.0+gdbd5502847b8` is installed and refreshed for Codex and ZCode only.
Hosted GitHub jobs did not execute repository steps because account billing or
spending-limit enforcement refused each job.

The one authorized final trial, `ar203-dbd5502-ordinary-01`, is terminal
`NO-GO`. Codex completed with host exit zero in 87.813 seconds and returned a
nonempty response, while the product command correctly exited one. The exact
isolated-workspace trust projection was proven without changing the persistent
profile, but the model-written sentinel was absent, so effective
workspace-write was not proven and product grading was skipped. The exact
activation query returned `route_not_found`; all route, run, load, delegation,
receipt, and finalization cardinalities were zero. The final response had no
Agency header. Correction count was exactly zero, but that narrow result cannot
compensate for a missing header and absent activation evidence.

The orchestration process itself required elevated authority to create the
`C:/tmp` trial directory before the restricted Codex run. That is concrete
evidence of a workspace capability mismatch and is the first next diagnostic,
but this trial does not prove it caused the separate missing Agency route.

The current bounded repair removes `--ephemeral` from product execution,
enables Codex multi-agent V2 and the agents capability, requires the exact
existing Store in the isolated hook process, and records only allowlisted
content-free accepted/completed/failed hook-stage counts. Ordinary product
trials still do not opt into the activation canary's single-child rollout
topology because the product goal requires multiple independent work units.
Codex delegation context now requires `fork_turns=none` so each child receives
only the exact hook-injected specialist context instead of inheriting the
parent's full history. The new and directly affected tests pass 26 focused
cases. Decision conformance passes its baseline and kills all 19 curated
mutations with zero survivors or invalid results. Two bounded review passes
found and repaired Windows CRLF hook-marker parsing, added real handler-failure
stage coverage, and corrected a stale multi-unit assertion that had accepted an
unevidenced model line. The complete changed-component suite passes 200 tests
under warning-strict mode. The named fast spine remains pending.

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
7. Persist the ordinary Codex parent turn and explicitly enable native
   multi-agent V2 plus the agents capability.
8. Require hook children to open the exact existing Agency Store and expose
   only bounded, allowlisted hook-stage counts in product evidence.
9. Keep multi-unit product evidence separate from the activation canary's
   deliberately single-child rollout parser, and isolate each Codex specialist
   child with `fork_turns=none`.

## Dependencies

ADR-0077 owns behavioral activation proof. ADR-0112 owns exact staged evidence
and accepted finalization. AR-201 supplies the exact terminal trace that
demonstrates both mismatches.

## Acceptance

- [x] Codex Agency product evaluation reads
  `agency.canary-activation-evidence.v1` for the exact prompt hash and never
  reports that schema unavailable when the Store returns it.
- [ ] The isolated Codex profile proves effective workspace-write authority for
  the exact empty trial directory without changing persistent user trust.
- [x] The product backend retains sandboxing and cannot write outside the trial
  directory.
- [x] A failed write proof stops before grading and is reported separately from
  workforce selection or product-quality failures.
- [x] Focused tests fail against both current defects and pass after repair.
- [x] Ordinary Codex product execution persists the parent turn, enables native
  multi-agent V2 and agents, and does not impose the single-child activation
  rollout topology.
- [x] Product hook execution requires the exact existing Store and projects
  bounded hook-stage evidence without retaining hook input or raw stderr.
- [x] Codex specialist launch instructions require `fork_turns=none` and the
  exact persisted native task name.
- [ ] The next ordinary canary reports exact activation evidence and can create
  required artifacts when workforce execution reaches the parent model.
