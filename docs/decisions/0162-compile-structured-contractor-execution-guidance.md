---
title: "Compile structured contractor execution guidance"
status: accepted
category: decisions
created: 2026-08-21
updated: 2026-08-21
tags: [contractors, hiring, prompts, security, workforce]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-122-contractor-hiring-and-lifecycle.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/handoffs/issue-AR-264.md
  - docs/decisions/0081-compile-contractors-from-governed-structured-contracts.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0162
type: decision
deciders: [maintainers]
---

# ADR-0162: Compile structured contractor execution guidance

## Context

The fixed contractor prompt protects Agency from unrestricted model-authored
instructions, but template v1 mainly serializes recruitment and safety facts.
It does not give an executing child the role-specific method, failure checks,
and verification discipline present in audited resident specialist cards.
Asking inference to write the final Agency prompt would improve apparent detail
by reopening the instruction-channel risk rejected by ADR-0081.

Existing contractor revisions are content-addressed and may have durable hiring,
lineage, outcome, and rollback evidence. Improving the compiler cannot rewrite
or reinterpret those historical prompt bytes.

## Decision

Inference emits a closed v2 employment contract containing a bounded structured
execution profile. The profile describes what to inspect, working principles,
failure modes, verification steps, and stop conditions. It is data, not prompt
prose, and remains subject to field, size, control-pattern, risk, critic, and
independent safety-review validation.

Agency's fixed compiler alone converts that data into executable specialist
context. Compiler v2 renders a readable worker capsule and excludes
recruiter-only closest-worker comparisons and positive/hard-negative selection
evaluations. The causing work unit remains the task authority; the execution
profile describes how the selected specialist should approach work within its
durable scope.

Parser/compiler v1 remains available only to reproduce historical and pending
evidence exactly. New hires and current packaged contractors use v2. A changed
packaged contractor advances through a package-authenticated amendment into a
new immutable version while preserving worker identity and prior lineage.

Owner workforce detail obtains evidence requirements from exact immutable
revision metadata. The compact recruiter contract is not widened for a
dashboard-only presentation need.

## Consequences

Contractors receive actionable, role-specific guidance without granting a model
control over prompt structure or adding a hiring provider call. Child context
uses fewer recruiter-only tokens, prompt identities remain deterministic, and
historical v1 evidence remains reproducible.

The employment and prompt template versions advance together. Packaged
contractor installation needs an idempotent immutable amendment path, and
promotion or outcome evidence must continue naming the exact delivered prompt
version and hash rather than silently transferring claims between revisions.

## Alternatives

Asking inference for a complete Agency prompt was rejected because it makes
untrusted prose the executable instruction channel. Keeping v1 unchanged was
rejected because scope labels alone do not materially improve execution.
Deterministically inventing a playbook from capability names was rejected
because generic paraphrases would look detailed without adding verified role
knowledge. Expanding the compact recruiter contract with dashboard-only fields
was rejected because immutable revision metadata already owns that evidence.
