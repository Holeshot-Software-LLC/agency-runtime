---
title: "Persist exact Codex plan authority and serialize opaque launches"
status: accepted
category: decisions
created: 2026-07-31
updated: 2026-08-01
tags: [codex, delegation, activation, security, privacy, evidence]
related:
  - docs/roadmap/issue-AR-209-bind-opaque-codex-child-launches.md
  - docs/roadmap/issue-AR-219-preserve-exact-multi-unit-product-execution-evidence.md
  - docs/roadmap/issue-AR-221-preserve-codex-product-execution-boundaries.md
  - docs/roadmap/issue-AR-207-persist-preflight-delegation-failure-diagnostics.md
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/decisions/0094-durable-native-child-correlation.md
  - docs/decisions/0126-authorize-exact-product-delegation-at-the-codex-developer-boundary.md
  - docs/decisions/0127-bind-opaque-codex-children-through-exact-plan-labels.md
  - docs/worklog/README.md
supersedes:
  - docs/decisions/0127-bind-opaque-codex-children-through-exact-plan-labels.md
superseded_by: null
id: ADR-0128
type: decision
deciders: [maintainers]
---

# ADR-0128: Persist exact Codex plan authority and serialize opaque launches

## Context

ADR-0127 made arbitrary opaque Codex children launchable by binding the visible
native task label to one accepted plan row. Two exact-head review findings
identified authority that was still too broad and lifecycle correlation that
was still ambiguous.

First, the ready recipe intentionally retained resource hashes rather than
plaintext resource paths. The later hook therefore converted every
workspace-write row to `.` even when preflight had identified one exact file.
The isolated product workspace limited the outer boundary, but this still
granted more in-repository mutation authority than the inferred work unit.

Second, Codex can acknowledge a parent spawn before the child's
`SubagentStart` hook consumes its grant. Multiple opaque launches in that
window leave the child-start hook unable to identify which unconsumed grant
belongs to the observed child. A task label cannot repair that ambiguity after
the host has removed the decrypted assignment from both hook inputs.

## Decision

Supersede ADR-0127 with these stricter boundaries while preserving its exact
label binding, unchanged ciphertext, token-free v2 context, and content-free
public evidence:

1. While preflight still holds the transient plaintext unit, derive one exact
   mutation scope for every accepted isolated Codex plan row. Only the sentinel
   resource `repository-workspace` maps to `.`; otherwise a workspace-write row
   retains its exact canonical repository-relative path prefixes. Read-only
   rows retain no writable paths and external-write rows remain forbidden.
2. Persist those scopes atomically with the ready compare-and-swap in one
   bounded canonical private Store table. Cross-check each scope against the
   ready work-unit ID, specialist version and prompt hash, goal hash, resource
   hashes, mutation mode, and evidence contract. The rows are immutable while
   active, excluded from public evidence, and deleted when the parent turn
   becomes terminal.
3. Every Codex `native_hook` activation must re-read and verify that private
   scope. A task-label match or content-free ready row alone cannot mint or
   broaden mutation authority.
4. Permit at most one unconsumed opaque Codex native-hook grant per trace. An
   exact replay of the same tool-use ID may reuse that grant idempotently; a
   different launch is denied until `SubagentStart` consumes the prior grant
   against one observed child identity.
5. In the source-controlled product scheduler, launch and await one child at a
   time. Dependency ordering still applies, but opaque Codex work does not use
   concurrent waves until the host exposes an authenticated child-to-task
   correlation that removes the ambiguity.

## Consequences

- An ordinary file-specific unit receives that file path rather than an
  unconditional repository-wide grant. An honestly unknown repository-wide
  unit still receives `.` inside the already isolated workspace.
- The private scope stores bounded resource paths for the active turn. Public
  recipes, headers, dashboard evidence, and product reports continue to expose
  only content-free hashes and lifecycle facts.
- Opaque Codex delegation is sequential. This trades potential child
  concurrency for exact lifecycle attribution and deterministic fail-closed
  behavior on the current host contract.
- Schema version 40 adds the immutable, terminally cleaned private scope table.
- A second spawn before child-start consumption is an authorization failure,
  not a best-effort scheduling hint or an ambiguous grant lookup.

## Alternatives

- **Keep `.` for every workspace-write row.** Rejected because isolation does
  not justify discarding narrower authority already known at preflight.
- **Reconstruct paths from stored hashes.** Rejected because hashes are not
  reversible and guessed paths would create fictional least privilege.
- **Persist paths in the public ready recipe.** Rejected because execution
  authority does not belong in durable public evidence or response context.
- **Allow concurrent grants and choose the oldest at child start.** Rejected
  because scheduling order is not authenticated child-to-task correlation.
- **Disable ordinary opaque Codex children.** Rejected because exact private
  scope and serialized lifecycle consumption provide a bounded working path.
