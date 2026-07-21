---
title: "Agency Runtime North-Star Acceptance"
status: active
category: testing
created: 2026-07-21
updated: 2026-07-21
tags: [acceptance, installation, routing, delegation, portability]
related:
  - docs/roadmap/issue-AR-115-live-routing-trust.md
  - docs/roadmap/issue-AR-116-bound-child-routing-and-oauth-model-selection.md
  - docs/roadmap/issue-AR-118-reconcile-native-child-activation-evidence.md
  - docs/RELEASE_CHECKLIST.md
supersedes: []
superseded_by: null
---

# Agency Runtime North-Star Acceptance

Agency Runtime is complete only when the exact candidate artifact works in a
normal installed host after restart. Source tests, an isolated profile, hook
registration, or a valid header alone are necessary evidence, not completion.

## Evidence identity

Every run records the source commit, artifact hash, installed package version,
native plugin version, and active plugin-cache path. They must all identify the
same candidate before behavioral evidence counts.

## Required Codex journeys

| Journey | Required observation | Status |
|---|---|---|
| Clean install | Hooks, MCP, dashboard choice, and activation guidance are installed without hidden manual file copying | unproven |
| Upgrade | A prior installation upgrades without stale launchers or plugin-cache code | unproven |
| Normal-profile restart | A fresh Codex task uses the candidate after Codex restarts | unproven |
| Safe inferred selection | Configured Codex OAuth inference chooses a relevant compatible specialist, records the resolved model, and rejects forbidden specialists | unproven |
| Safe deterministic selection | With inference disabled, a strong match chooses the relevant specialist and a weak or ambiguous match abstains | unproven |
| Conflict control | Conflicting instructions never share one context; required specialists are ordered or isolated | unproven |
| Planned child | The child consumes its exact parent-issued activation without another inference call | unproven |
| Unplanned fan-out | Parent budget, cache, concurrency, and singleflight bound child inference | unproven |
| Activation reconciliation | Consumed child evidence links to the parent event and finalization exits without a Stop retry | unproven |
| Header | Six readable lines contain only current-turn receipt-backed facts | unproven |
| Master switch | Fresh Agency-on and native-only tasks behave differently and restore the configured state | unproven |
| Configuration | CLI and dashboard read and write the same protected configuration, including provider, model, LiteLLM alias, agent toggles, and Agency master state | unproven |
| Dashboard | The installed service starts, streams live state, authenticates local mutations, and reports its exact URL | unproven |

The unsafe-selection regression must explicitly forbid clinical, geography,
translation, and generic business-operations specialists for Agency runtime,
header, selection-testing, and dashboard prompts. A test that merely obtains a
different specialist does not pass.

## Candidate artifact gate

The wheel and source archive are installed into clean environments outside the
checkout on Windows and Linux. `scripts/smoke_installed_distribution.py` runs
the exact Agency runtime/dashboard prompt against the complete approved roster
and requires `multi-agent-systems-architect`; it then requires an ambiguous
prompt to abstain. The report includes every selected slug and the forbidden
set. Source-only execution is useful while developing, but only the isolated
artifact jobs count for this gate.

## Portability evidence

After Codex passes, run equivalent installed canaries for each available Claude
Code, OpenClaw, and Hermes host on Windows and Linux. Mark an unavailable host
or operating system as unproven. Contract simulation cannot be relabeled as a
live native result.

## Completion rule

Do not merge the release candidate, close its P0 issues, or describe the north
star as complete until every applicable row is green with a dated evidence
receipt and the installed identity matches the tested source. Merge then runs
the deferred full compatibility matrix; reinstall the merged artifact and run
one final fresh-task smoke before closure.
