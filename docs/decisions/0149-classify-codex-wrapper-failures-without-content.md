---
title: "Classify Codex wrapper failures without content"
status: accepted
category: decisions
created: 2026-08-02
updated: 2026-08-02
tags: [codex, delegation, diagnostics, evidence, privacy, store]
related:
  - docs/roadmap/issue-AR-223-prove-codex-child-task-execution.md
  - docs/roadmap/handoffs/issue-AR-207.md
  - docs/decisions/0146-preserve-content-free-codex-child-tool-outcomes.md
  - docs/decisions/0147-persist-codex-child-tool-evidence-on-worker-receipts.md
  - docs/decisions/0148-classify-nested-codex-exec-tools-without-content.md
  - agency_runtime/core/codex_child_tool_evidence.py
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/evals/decision_conformance.py
  - tests/test_codex_activation_canary.py
  - tests/test_native_child_lifecycle.py
  - tests/test_product_host.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0149
type: decision
deciders: [maintainers]
---

# ADR-0149: Classify Codex wrapper failures without content

## Context

ADR-0148 made a failed nested Codex wrapper visible without retaining its
input or output. Consumed writer trial `ar223-agency-writer-5a97976-01` proves
one nested `apply_patch` entered the wrapper and failed, but v2 cannot
distinguish sandbox setup, approval, permission, or another process failure.
Retrying immutable product trials without that distinction wastes the only
useful live sample and leaves the next repair speculative.

## Decision

1. Child tool evidence v3 retains every v1 and v2 count and adds only counts
   for `windows_split_writable_roots`, `windows_sandbox_setup_failed`,
   `approval_rejected`, `permission_denied`, `process_failed_other`, and
   `failure_unknown`.
2. Classification transiently reads at most the existing one-million-character
   wrapper-output bound. It serializes only the fixed category count and never
   stores output text, commands, paths, prompts, or errors.
3. Specific Windows split-root evidence wins over its enclosing sandbox-setup
   text. Exact approval and OS-permission markers precede the residual
   process-failure category. Malformed, mixed, or oversized output is unknown.
4. The six v3 failure counts must sum exactly to the existing failed-wrapper
   count. New Store rows use canonical v3; canonical v1 and v2 rows remain
   readable and are not reinterpreted.
5. A curated mutation collapses the fixed category to the residual process
   failure and must be killed by the content-free product projector test.

## Consequences

- The next failed immutable writer identifies the first wrapper boundary
  without exposing repository or command content.
- The categories are diagnostics, not execution or workspace-write proof.
- New host wording fails closed to `process_failed_other` only when it retains
  a valid failed envelope; unsafe output structure becomes `failure_unknown`.

## Alternatives

- **Persist the raw error.** Rejected because it can contain private paths,
  commands, content, and task material.
- **Infer the cause from an empty workspace.** Rejected because multiple
  unrelated wrapper failures produce the same absence of artifacts.
- **Retry v2 builds until one works.** Rejected because consumed trials are
  immutable evidence and repetition cannot diagnose the boundary.
- **Create an unrestricted free-text reason.** Rejected because it would
  weaken both privacy and canonical Store validation.
