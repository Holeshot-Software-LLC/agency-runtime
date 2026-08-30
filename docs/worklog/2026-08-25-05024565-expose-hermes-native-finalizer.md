---
title: "Worklog detail: Expose Hermes native Agency finalizer"
status: active
category: worklog
created: 2026-08-25
updated: 2026-08-25
tags: [hermes, finalization, plugin, reliability]
related:
  - docs/roadmap/issue-AR-288-expose-hermes-native-finalizer-tool.md
  - docs/roadmap/issue-AR-266-dense-hybrid-workforce-recall.md
  - docs/roadmap/handoffs/issue-AR-266.md
  - docs/decisions/0120-construct-first-pass-evidence-headers.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 0502456572b5e9002617a0173173c084434db2e4
short: 05024565
date: 2026-08-25
pr: null
related_issues:
  - docs/roadmap/issue-AR-288-expose-hermes-native-finalizer-tool.md
  - docs/roadmap/issue-AR-266-dense-hybrid-workforce-recall.md
---

# Worklog detail: Expose Hermes native Agency finalizer

## Purpose

Hermes preflight required canonical first-pass Agency finalization but the
generated plugin exposed no callable finalizer. A model could only emit its
initial header snapshot, which becomes stale after tool or provider evidence
changes and is correctly blocked at the terminal boundary.

## Approach

Register one `agency_finalize` tool through Hermes `0.20.4`'s native plugin API.
The tool accepts only draft text; session and trace identity come from Hermes
callback state. The bridge constructs the current Store-backed response without
terminalizing, enforces an inline-safe host transport ceiling, revalidates the
current evidence revision, then atomically commits and returns the exact text.
Preflight supports both direct visibility and Hermes Tool Search's deferred
`tool_call` path.

## Challenges encountered

Review found two post-commit exactness hazards: generated-plugin truncation
after a 64-KiB draft and ASCII JSON expansion above the bridge byte ceiling.
It then identified Hermes's context-scaled result spilling, which can replace a
large accepted result with a preview and path. Red-before regressions led to
UTF-8 transport and a fail-closed 4,096-character inline result ceiling. A
final regression preserved runtime-disabled passthrough before correlation and
size enforcement.

## Decisions and alternatives

No Hermes source or native config was changed. An inert packaged MCP document
was not treated as activation evidence because Hermes `0.20.4` ignores that
native-plugin key. Delaying all terminalization to a later host hook was broader
than required; the selected design commits only after current-evidence CAS and
after proving the result stays below Hermes's 8,000-character spill floor.

## Verification

- 109 focused generated-plugin, finalization, adapter, smoke, and encoding tests
  pass with warnings as errors.
- The named fast production spine passes: 856 passed, 3 skipped.
- Ruff check/format, documentation checks, dashboard tests, routing evaluation,
  the 160-mutation snippet substitute, and `git diff --check` pass.
- Independent review returned GO with no remaining correctness or security
  blocker.
- Full decision-conformance mutation execution did not start because the trusted
  system interpreter lacks `pytest`; no mutation ran.

## Follow-ups

Reinstall Agency into Hermes only, verify live native tool discovery without a
native config change, and complete one genuinely new Store-correlated response.
Tracker creation remains pending separate authorization.
