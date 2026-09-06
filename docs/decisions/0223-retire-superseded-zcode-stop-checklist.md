---
title: "Retire the superseded ZCode Stop checklist, preserve the wire contract"
status: accepted
category: decisions
created: 2026-09-05
updated: 2026-09-05
tags: [backlog, zcode, evidence, supersession]
related:
  - docs/roadmap/issue-AR-127-zcode-stop-rejection-shape.md
  - docs/roadmap/issue-AR-135-complete-zcode-integration.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/AR-119-founding-vision.md
  - docs/decisions/0089-zcode-stop-rejections-use-decision-block.md
  - docs/decisions/0105-bound-delivery-to-live-demo-checkpoints.md
  - docs/decisions/0120-construct-first-pass-evidence-headers.md
  - agency_runtime/adapters/hooks.py
  - tests/test_host_hooks.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0223
type: decision
deciders: [maintainers]
---

# ADR-0223: Retire the superseded ZCode Stop checklist, preserve the wire contract

## Context

The owner's oldest-first reconciliation reaches AR-127 at main 79930464.
Its output-shape repair already exists in both HookBridge._reject_completion
and the malformed/oversized Stop boundary. ADR-0089 remains the valid native
wire contract: an actual ZCode rejection uses decision:block, not lifecycle
continue/stopReason fields. The original fix is recorded at d9ce781a / PR #150.

The rest of the old checklist is no longer the current product contract.
ADR-0120 removed continuation-claim/retry recovery in favor of terminal first
rejection and exact replay. Vision Rule 8 lets the host publish when Agency
cannot verify/persist its own evidence; that is not a negative finding about
the response. Malformed Stop envelopes still block. ADR-0105 made the full
warning-strict corpus optional, yet the August 12 reopening treats its missing
historical receipt as the only blocker. Reimplementing those old assumptions
would regress current behavior, not repair the shape bug.

## Decision

Retire AR-127 as wont_do/superseded by AR-135, not as accepted against its
original checklist and not as a new live ZCode success. Preserve that checklist,
the original report, the historical live-result claim and the reopening note.
Keep ADR-0089 accepted; this decision does not replace its valid wire shape.

AR-135 explicitly owns current ZCode Stop integration: real negative and
malformed-envelope rejections use decision:block, terminal replay is identical,
Agency-unavailable publication follows Rule 8, and current native/full-response
evidence must be distinguished from fixture or installed-contract tests.
The old turn-5 truncated-preview explanation is a hypothesis, not an established
cause; any still-relevant full-response/false-reject question stays with AR-135.
AR-119/125 retain the broader current five-host and comparative live evidence.

No code, test, schedule, header policy, founding rule or matrix cell changes.
Do not recreate response retries, block a host solely because Agency is blind,
weaken malformed-Stop rejection, or run the exhaustive suite merely to satisfy
the retired historical checklist. New live claims still need their own evidence.

## Consequences

One obsolete mapped record leaves the open queue without certifying its old
criteria. The working shape fix remains tested and its current product outcome
has an explicit existing owner. Tracker #151 is retired as not planned after
merge; AR-135 stays open pending its own reconciliation and acceptance.

## Alternatives

- Mark the old checklist satisfied: rejected because continuation and
  unavailable-verification behavior changed, and no fresh live result exists.
- Restore old retry/fail-closed behavior or require the historical full suite:
  rejected because it contradicts the current governing policies.
- Delete the record or wire-shape decision: rejected because the original fix
  and rationale remain useful, and the native rejection contract still applies.

## Verification basis

Current terminal/replay/ZCode boundary/Rule-8 and completion-policy checks:
37 passed in 3.37s at unchanged source 79930464. The wider hook/policy/turn
package is 133 passed and three failures in 41.91s, not a pass. Those already-
documented legacy delegate/retry assertions remain owned by AR-176, not hidden
or rewritten here. No fresh host trial or exhaustive corpus is claimed.
