---
title: "Agency Runtime North-Star Acceptance"
status: active
category: testing
created: 2026-07-21
updated: 2026-08-12
tags: [acceptance, vision, inference, native-child, contractors, portability]
related:
  - docs/roadmap/AR-119-founding-vision.md
  - docs/roadmap/AR-119-rule-host-evidence-matrix.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
  - docs/roadmap/issue-AR-115-live-routing-trust.md
  - docs/roadmap/issue-AR-116-bound-child-routing-and-oauth-model-selection.md
  - docs/roadmap/issue-AR-118-reconcile-native-child-activation-evidence.md
  - docs/roadmap/issue-AR-186-bound-delivery-to-live-demo-checkpoints.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0157-automatically-promote-host-verified-contractors.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - docs/RELEASE_CHECKLIST.md
supersedes: []
superseded_by: null
---

# Agency Runtime North-Star Acceptance

Agency Runtime is complete only when the exact candidate artifact demonstrates
the [founding nine-rule vision](roadmap/AR-119-founding-vision.md) in normal
installed native hosts after restart. The
[rule and host evidence matrix](roadmap/AR-119-rule-host-evidence-matrix.md) is
the sole current completion projection. Source tests, simulation, an isolated
profile, hook registration, a Store row, or a model-authored claim are useful
evidence layers, not substitutes for the proof authority required by a rule.

## Evidence identity

Every run records the source commit, artifact hash, installed package version,
native plugin version, active plugin-cache path, host version, trace identity,
and observation time. They must all identify the same candidate before
behavioral evidence counts. An unavailable host is `unproven`, never waived.

## Nine-rule acceptance

| Rule | Required observation |
|---|---|
| R1 — inference selection | A configured inference receipt is the sole source of the exact selected specialist or contractor card hashes. Deterministic code may recall candidates, enforce hard eligibility and safety, validate, budget, and correlate; it may not choose, replace, broaden, narrow, or erase the staffing decision. |
| R2 — load the caller | The selected card content is present in the current caller's context; Agency does not send a specialist to a separate worker. |
| R3 — multiple cards | A compatible multi-card inference decision reaches one caller without deterministic reduction to one card or conflicting instructions. |
| R4 — staff native children | A child the harness independently chose to spawn receives every selected card before its first speech. Only the native host's own artifact, containing the exact card hashes and parent-child correlation, can originate a green delivery claim. Agency Store rows remain diagnostics. |
| R5 — host owns spawn | Native host artifacts show the harness originated the child. No Agency decision, plan, card, or transport instructs the host to create one. |
| R6 — contractor path | A genuine roster gap causes inference to design the contractor, the safety interview accepts it, and the accepted card enters the governed pool for later turns. Deterministic code may reject an unsafe proposal but may not author or select the contractor. |
| R7 — turn scope | Loaded cards expire at the caller's turn boundary and do not silently persist into another turn. Governed roster history remains durable; context activation does not. |
| R8 — complement, never obstruct | Agency unavailability never withholds the turn. A verifier's definite negative and an unreadable malformed `Stop` envelope remain the two deliberate blocking paths; all other blind or unavailable paths publish with visible diagnostic evidence. |
| R9 — host parity | R1–R8 have current installed and live proof on Codex, Claude, OpenClaw, Hermes, and ZCode. A host-specific gap remains incomplete rather than becoming an exception. |

The unsafe-selection regression must explicitly forbid clinical, geography,
translation, and generic business-operations specialists for Agency runtime,
header, selection-testing, and dashboard prompts. A test that merely obtains a
different specialist does not pass. The fixed cold staffing control remains
15,000 ms; optimization cannot weaken inference, safety, or evidence authority.

## Required installed product journeys

| Journey | Required observation |
|---|---|
| Clean install | Hooks, MCP, dashboard choice, and activation guidance install without hidden manual file copying. |
| Upgrade | A prior installation upgrades without stale launchers, plugin-cache code, or mixed candidate identity. |
| Normal-profile restart | A fresh task uses the exact candidate after the native host restarts. |
| Inference-owned selection | Configured inference chooses the exact relevant compatible card set, actual provider/model telemetry is recorded, and hard-forbidden cards are rejected without a deterministic fallback choice. |
| Conflict control | Multiple compatible cards may share one caller; conflicting instructions never do. Required independent producer and verifier roles remain distinct. |
| Native child staffing | A harness-originated child receives the exact inference-selected multi-card set through the native host channel, with host-authored proof before first speech. |
| Delivery reconciliation | The inference decision, card hashes, native parent-child artifact, installed identity, and outcome join without a hidden retry or Agency-authored proof substitution. |
| Header | Readable current-turn headers contain only receipt-backed facts and do not overstate delivery, provider, outcome, or host maturity. |
| Master switch | Fresh Agency-on and native-only tasks behave differently and restore the configured state. |
| Configuration | CLI and dashboard read and write the same protected configuration, including provider, model, LiteLLM alias, agent toggles, and Agency master state. |
| Dashboard | The installed service starts, streams live state, authenticates local mutations, and reports its exact URL. |
| Contractor promotion | A real accepted contractor automatically promotes only after the host-backed, independent-verifier, distinct-outcome, and seven-day controls all hold. |

## Contractor production gate

Automatic contractor promotion is part of the AR-119 critical path. Production
success requires a host-backed producer artifact, an independently
inference-selected verifier artifact, and a distinct accepted outcome identity.
Only three distinct accepted outcomes after the seven-day review window may
trigger automatic promotion. A Store assignment, self-review, duplicate
outcome, elapsed time alone, or manual status edit cannot satisfy this gate.

## Candidate artifact gate

The wheel and source archive are installed into clean environments outside the
checkout on Windows and Linux. The candidate must preserve the exact inference
decision through card hydration, host delivery, verification, and evidence
correlation. The report includes every selected card hash, filtered or rejected
candidate with its hard-policy reason, actual provider/model telemetry, and the
native host artifact identity used for any R4 claim. Source-only execution is
useful while developing, but only candidate-bound installed and live evidence
can make a matrix cell `proven`.

`scripts/smoke_installed_distribution.py` exercises packaged runtime, MCP,
dashboard, configuration, and roster surfaces outside the checkout. The
installed selection regression runs against the complete approved roster:
`multi-agent-systems-architect` is the only accepted result for the exact
Agency runtime/dashboard case, an ambiguous request abstains, and the forbidden
specialist set remains absent. That deterministic expected-result assertion
tests the inference decision; it does not authorize a deterministic selector.

## Portability evidence

Run equivalent installed canaries for Codex, Claude, OpenClaw, Hermes, and
ZCode on each supported operating system. Each available host must include a
native multi-card child observation and the automatic-promotion evidence path.
Contract simulation cannot be relabeled as a live native result, and one
host's evidence cannot fill another host's cell.

## Historical acceptance language

Earlier revisions described a deterministic fallback selector and a
parent-issued planned-child activation path. Those mechanisms remain visible in
Git history and their historical ADRs, but they are not current acceptance
authority and cannot close a nine-rule or host-parity cell.

## Completion rule

Complete one bounded visible outcome at a time. Focused tests and the named
fast production spine must pass before an exact artifact is installed and
exercised through its live host/UI demo checkpoint. Findings unrelated to that
outcome are tracked separately instead of reopening the package.

The exhaustive warning-strict, coverage, and compatibility workflow is an
optional owner-requested diagnostic, not a completion requirement. Do not close
a P0 issue or describe its scoped outcome as complete until every applicable
fast, artifact, security, and live-evidence row is green with dated receipts,
the installed identity matches the tested source, and the current matrix
records the same state. Human-owned approval steps enter
`waiting_for_operator` and are not retried unattended.
