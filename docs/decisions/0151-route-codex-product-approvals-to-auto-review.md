---
title: "Route Codex product approvals to automatic review"
status: accepted
category: decisions
created: 2026-08-02
updated: 2026-08-02
tags: [codex, automation, approvals, product, sandbox, workspace]
related:
  - docs/roadmap/issue-AR-223-prove-codex-child-task-execution.md
  - docs/roadmap/handoffs/issue-AR-207.md
  - docs/decisions/0116-bind-product-trials-to-exact-workspace-proof.md
  - docs/decisions/0119-separate-native-trust-modes-from-activation-proof.md
  - agency_runtime/core/evals/product_host.py
  - tests/test_product_host.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0151
type: decision
deciders: [maintainers]
---

# ADR-0151: Route Codex product approvals to automatic review

## Context

The Codex product harness requests `workspace-write`, confines execution to one
exact isolated workspace, and uses non-interactive `codex exec`. Current Codex
0.146.0 records that invocation with `approval_policy=never` as a managed
read-only permission profile. The nested `apply_patch` wrapper therefore fails
before touching the workspace even though the requested sandbox is writable.

A focused control using the documented `workspace-write`, `on-request`, and
`auto_review` combination created and read back the exact 21-byte sentinel.
Removing Agency hooks and the autonomous hook-trust bypass did not make the
`never` invocation writable, so hook execution is not the cause.

## Decision

1. Codex product execution keeps the exact `workspace-write` sandbox and sets
   `approval_policy="on-request"` with `approvals_reviewer="auto_review"`.
2. Product execution remains non-interactive: eligible approval requests go to
   Codex automatic review rather than requiring a human operator.
3. This approval configuration does not broaden the writable root, add another
   directory, disable sandboxing, or change persistent user configuration.
4. Autonomous hook trust remains a separate invocation-scoped authority. It
   neither grants filesystem access nor substitutes for automatic review.
5. Tests pin both positive settings and reject a silent return to
   `approval_policy="never"`.

## Consequences

- The product harness can exercise real workspace tools autonomously inside its
  exact isolated workspace on the current Codex host.
- Workspace mutations may incur an additional automatic-review model call.
- A denied automatic review remains a visible failed tool outcome and cannot be
  reinterpreted as successful product execution.
- Activation-only canaries retain their existing read-only behavior; this
  decision changes only product execution.

## Alternatives

- **Keep `approval_policy=never`.** Rejected because current authoritative turn
  evidence proves that configuration is managed read-only in the product host.
- **Use `--dangerously-bypass-approvals-and-sandbox`.** Rejected because it
  removes the exact workspace sandbox instead of repairing autonomous approval.
- **Persistently trust or reconfigure the owner profile.** Rejected because the
  product harness is isolated and must not mutate owner security state.
- **Remove Agency hooks or the hook-trust bypass.** Rejected because the no-hook
  control remained read-only and did not repair the boundary.

Implementation `263e3f5` carries this decision.
