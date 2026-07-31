---
title: "Worklog detail: require first-pass evidence headers"
status: active
category: worklog
created: 2026-07-30
updated: 2026-07-30
tags: [finalization, evidence, headers, codex, openclaw, hermes]
related:
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/decisions/0120-construct-first-pass-evidence-headers.md
supersedes: []
superseded_by: null
type: worklog
commit: 3ec69c7
short: 3ec69c7
date: 2026-07-30
pr: null
related_issues:
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
---

# Worklog detail: require first-pass evidence headers

## Purpose

Remove the response-repair loop that could make an Agency header look healthy
after the underlying first response failed, and make zero corrections a real
success invariant across supported adapters.

## Approach

Native Codex now receives exact Store-backed initial, updated, and post-wait
final header snapshots before it publishes. Hermes and OpenClaw instruct the
model to call `agency.finalize` once before the natural final response and emit
the committed result unchanged. Invalid natural output closes terminally as
`response_invalid` or `delegation_declined`; OpenClaw no longer returns a revise
action, Hermes returns only its bounded safe failure response, and historical
`retry_exhausted` records remain readable without being produced by the current
path.

ADR-0120 records the durable first-publication contract and supersedes the
former one-correction decision. Four curated decision mutations protect the
native stop shape, initial Codex snapshot, OpenClaw no-revision path, and Hermes
no-repair transform.

## Challenges encountered

The old `retry` parameter name obscured two different native wire contracts.
Current Codex documentation and focused tests distinguish `continue: false`,
which stops the hook run, from `decision: block`, which asks Codex to continue.
ZCode retains `decision:block` because its host contract does not recognize the
Codex lifecycle shape.

## Decisions and alternatives

[ADR-0120](../decisions/0120-construct-first-pass-evidence-headers.md) owns the
decision. Post-response repair and publication-with-warning were rejected
because neither can satisfy a zero-correction evidence contract.

## Verification

- 378 warning-strict focused tests passed with five platform skips across native
  hooks, Hermes/OpenClaw parity, MCP finalization, security boundaries, and
  owned-adapter coverage.
- A 144-test post-format regression passed.
- Ruff check and format check passed for every touched Python file.
- Metadata and documentation validation passed for 564 Markdown files.
- Policy availability and `git diff --check` passed.
- The 37-mutation manifest and evaluator unit tests passed; complete isolated
  mutation execution remains the next checkpoint gate.

## Follow-ups

[AR-204](../roadmap/issue-AR-204-reconcile-readme-story-contract.md) retains the
complete 37-mutation run, rendered dashboard/configuration proof, named fast
spine, exact install, and one native Codex product trial.
