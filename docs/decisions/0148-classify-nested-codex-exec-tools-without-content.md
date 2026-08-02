---
title: "Classify nested Codex exec tools without content"
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
  - docs/decisions/0149-classify-codex-wrapper-failures-without-content.md
  - agency_runtime/core/codex_child_tool_evidence.py
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/evals/decision_conformance.py
  - tests/test_codex_activation_canary.py
  - tests/test_native_child_lifecycle.py
  - tests/test_product_host.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0148
type: decision
deciders: [maintainers]
---

# ADR-0148: Classify nested Codex exec tools without content

## Context

ADR-0146 and ADR-0147 preserve and durably attach fixed child-tool counts.
Writer trial `ar223-agency-writer-2bbd885-01` proves that v1 persists correctly,
but current Codex exposes every child action as a completed `functions.exec`
custom wrapper. The wrapper input names the nested tool and its output starts
with a fixed execution envelope; neither fact appears in the v1 counts.

The Store can therefore prove that three wrappers returned outputs while still
being unable to distinguish a missing patch attempt from a failed nested tool.
Persisting raw wrapper input or output would disclose commands, paths, file
content, errors, prompts, and task text.

## Decision

1. Child tool evidence v2 retains the v1 counts and adds only bounded counts for
   classified or unclassified exec inputs, nested `apply_patch`,
   `shell_command`, or other calls, and completed, failed, yielded, or unknown
   wrapper outcomes.
2. A bounded lexical scanner recognizes only direct `tools.<identifier>(`
   calls outside quoted literals and comments. Ambiguous templates, regular
   expressions, malformed literals, non-string input, and oversized input are
   `unclassified`; they never become inferred tool calls.
3. Wrapper outcome classification reads only the fixed first line emitted by
   the host. Every other output byte is ignored and is never serialized.
4. The Store writes canonical v2 evidence for new workers and continues to
   decode canonical v1 rows. Product admission requires current v2 evidence;
   historical rows remain readable and are never backfilled or reinterpreted.
5. A curated mutation removes nested classification and must be killed by the
   fixed content-free projector test.

## Consequences

- A failed writer can distinguish “no nested patch was attempted” from a child
  that entered an `apply_patch` wrapper, without retaining private content.
- Malformed or ambiguous JavaScript remains visible as an unclassified count
  instead of producing a guessed tool identity.
- The aggregate is diagnostic, not mutation proof. Workspace bytes and the
  existing patch receipt boundary still decide successful workspace writes.
- The same projector classifies a retained sample of the current host format:
  all 36 recent exec inputs classify, with 7 nested patch, 29 shell, and 1
  other call; wrapper outcomes remain fixed counts only.

Implementation `95aec42` carries this decision.

## Alternatives

- **Persist raw wrapper input and output.** Rejected because it would retain
  private commands, paths, content, errors, and task material.
- **Treat every exec wrapper as shell execution.** Rejected because current
  wrappers can call `apply_patch`, `shell_command`, or another tool.
- **Use a regular expression over raw JavaScript.** Rejected because quoted and
  commented tool-like text would create false diagnostic claims.
- **Leave v1 unchanged.** Rejected because the exact failed writer proved that
  transport-only counts do not identify the first child mutation boundary.
