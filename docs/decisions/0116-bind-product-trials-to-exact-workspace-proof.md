---
title: "Bind product trials to exact isolated workspace proof"
status: accepted
category: decisions
created: 2026-07-30
updated: 2026-08-01
tags: [evaluation, codex, activation, sandbox, trust, evidence]
related:
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-219-preserve-exact-multi-unit-product-execution-evidence.md
  - docs/roadmap/issue-AR-207-persist-preflight-delegation-failure-diagnostics.md
  - docs/decisions/0077-prove-codex-activation-behaviorally.md
  - docs/decisions/0112-stage-preflight-workforce-evidence-until-ready.md
  - docs/THREAT_MODEL.md
  - docs/TROUBLESHOOTING.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0116
type: decision
deciders: [maintainers]
---

# ADR-0116: Bind product trials to exact isolated workspace proof

## Context

The AR-201 product trial completed a Codex process and persisted a proven exact
activation snapshot, but its report consumed the legacy recent-activity
projection and declared the activation schema unavailable. The same fresh
isolated Codex profile also reported a read-only workspace even though the
command requested the workspace-write sandbox. Because no artifact was created,
product grading could not distinguish a model-quality failure from missing
effective write authority.

Copying the owner's persistent trusted-project configuration into a live trial
would broaden authority and make autonomous execution depend on prior manual
profile state. An outer Python write would prove only the harness process, not
the effective policy seen by the Codex model.

## Decision

Each Codex product trial keeps a private disposable Codex home. Before plugin
installation, that home receives one generated configuration entry trusting
only the canonical existing trial workspace. The source profile contributes
only its bounded authentication file; its persistent configuration is neither
read into the trial nor changed. The host command remains
`--sandbox workspace-write`, supplies no additional write root, and does not
use a general sandbox bypass.

The harness prepends a content-free instruction requiring the same Codex model
invocation to create one fixed sentinel containing a token derived from the
canonical product prompt hash. The workspace must not contain that sentinel
before execution. Afterward the harness accepts only a bounded real regular
file with the exact token, removes it before artifact validation, and records a
content-free write-proof result. Missing, mismatched, linked, oversized, or
uncleanable proof fails closed before product grading.

The report retains both the canonical product prompt hash and the wrapped
executed prompt hash. Codex Agency activation evidence is read through
`get_canary_activation_snapshot` for that exact executed hash. A product
runtime contract passes only when activation, exact-workspace trust, and the
model-written sentinel are all proven.

## Consequences

- Autonomous isolated trials do not require a human to trust the disposable
  workspace in a persistent Codex profile.
- The persistent user configuration remains byte-for-byte outside the
  mutation boundary.
- Product-quality validation cannot run on an unproven or merely requested
  workspace-write state.
- The sentinel proves one exact in-workspace write by the evaluated invocation;
  it does not claim that one trial exhaustively proves the host sandbox.
- Exact activation correlation follows the prompt the host actually executed
  while preserving the original product request identity in the report.

## Alternatives

- **Copy the owner's complete Codex configuration.** Rejected because it imports
  unrelated trust and mutable profile state.
- **Trust the requested sandbox flag alone.** Rejected because the failed trial
  demonstrated that requested and effective behavior can differ.
- **Write a probe from the outer harness.** Rejected because it does not prove
  authority available to the Codex model process.
- **Grade any files left after a failed write proof.** Rejected because that
  conflates harness authority, product execution, and product quality.
