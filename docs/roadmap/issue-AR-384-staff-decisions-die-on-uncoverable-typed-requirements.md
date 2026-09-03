---
title: "AR-384: The recruiter is told to staff units the roster cannot cover, then rejected for staffing them"
status: in_progress
category: roadmap
created: 2026-09-03
updated: 2026-09-03
tags: [workforce, recruiter, staffing, inference, planner, receipts]
related:
  - docs/decisions/0198-waive-the-typed-requirements-the-roster-declares-but-cannot-serve.md
  - docs/roadmap/issue-AR-373-recruiter-evidence-vocabulary.md
  - docs/roadmap/issue-AR-374-host-capability-vocabulary-gap.md
  - docs/roadmap/issue-AR-370-staffing-asks-the-wrong-question.md
  - docs/roadmap/issue-AR-383-inferred-subject-context-fails-its-own-projection.md
  - docs/roadmap/issue-AR-385-structured-reply-budget-truncates-nominations-silently.md
  - docs/roadmap/issue-AR-386-strict-critic-vetoes-verifier-accepted-install-turns.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-384
priority: p1
tracker_url: null
depends_on: []
blocks: []
---

# AR-384: The recruiter is told to staff units the roster cannot cover, then rejected for staffing them

## Problem

`staff_without_safe_team` is the dominant recruiter contract failure on this
installation, and in the captured instance no response the recruiter could
have given would have validated.

Measured on the 2026-09-03 forty-five-turn preflight smoke (receipts recorded
13:50 to 16:25 UTC, `preflight_failure_receipts.provider_attempts`):

| | count |
|---|---|
| recruiter attempts rejected `provider_response_contract_invalid` | 48 |
| of those, carrying `staff_without_safe_team` | **31** (16 first attempts, 15 repair attempts) |
| carrying `invalid_candidate` | 9 |
| carrying no failure record at all | 8 (AR-385) |
| per-unit `staff_without_safe_team` entries | 44, of which **40** name the `domain` axis |
| of those 44, `top_ranked_ineligibility` empty | 36 |

The empty ineligibility field means the recruiter's top candidate was
executable. These are not eligibility failures. They are the deterministic
coverage search finding no team, and the repair attempt failing the same way.

## Captured payload

Captured live 2026-09-03 through `run_preflight` with a real store, a proven
`codex` capability receipt, the credential sourced, and fresh wording so the
gateway cache could not replay. Both the exact HTTP request and the raw reply
were recorded by hooking the structured provider in-process. The recruiter
route was served by `anthropic/MiniMax-M3`, the gateway's first deployment.

Request: `Put this editor on my machine: <helix editor repository>`. The
planner produced three units. The second:

    unit-install-operation: artifact plan, lifecycle planning,
    domains [desktop, operations], required_capabilities [planning, operations],
    authority plan

`typed_recall`, built by `_typed_shortlists`
(`core/workforce/inference.py:1542-1608`), told the recruiter in the same
document:

    requirements: [artifact:plan, lifecycle:planning, domain:desktop,
                   domain:operations, capability:planning,
                   capability:operations, authority:plan]
    uncovered_requirements: [domain:desktop]

`uncovered_requirements` is computed over every enabled, executable, typed
contract in the roster (line 1595). It said, before the recruiter spoke, that
no eligible contract covers `domain:desktop` for this unit. The only contract
declaring that domain, `desktop-app-engineer`, carries `modify` authority and
is ineligible for a `plan` unit. `capability:operations` was covered by exactly
two candidates in the recall block, `incident-responder` and
`incident-response-commander`.

The recruiter did what the system prompt asks. It ranked `operations-manager`
required at 0.84 with `sre-site-reliability-engineer`,
`desktop-app-engineer` and `it-service-manager` acceptable, every row with
valid hyphenated evidence, and returned `staff`. The runtime rejected it:

    unit-install-operation=staff_without_safe_team:domain
      ~operations-manager~sre-site-reliability-engineer
      ~desktop-app-engineer~it-service-manager!1:3:4

The repair feedback then handed the model a `safe_team_contract` whose
`ranked_candidates` listed `desktop-app-engineer` as `excluded` (it is
ineligible) and asked it to "add or reclassify a faithful required/acceptable
complement that covers the exact missing requirement". No such candidate
exists. The model marked `desktop-app-engineer` forbidden, citing Agency's own
ineligibility code `agent_authority_mismatch`, and was rejected again for the
underscore (AR-373). The turn ended `inference_invalid`.

A second captured turn had the same shape one unit earlier:
`unit-review-throttle-security` (review-report, domains `[security, backend]`,
review authority) carried `uncovered_requirements: [domain:backend]`. Three
contracts declare `backend`; none has review authority. Two of the twenty-three
captured units were unstaffable before the recruiter answered, and both turns
died.

## Mechanism

1. `_requirements` (`core/workforce/staffing_verifier.py:415-425`) emits one
   token per axis value. `_minimum_team_with_required` (lines 525-551) accepts
   a team only when the union of its typed coverage contains **every** token.
   `_validate_nomination_decisions` (`core/workforce/inference.py:2554-2605`)
   turns an empty team under a `staff` decision into
   `staff_without_safe_team`. Sufficiency is conjunctive across all six axes,
   as the module's own docstring says: one uncovered axis defeats every team.
2. The escape hatch is gone. `_coverage` (lines 427-466) treats a contract
   with no typed fields as covering everything, with a comment explaining that
   this is what keeps "the recruiter's faithful-match decision" from being
   "hard-rejected by a typed-data gate that has no data to evaluate". The
   installed roster now has **0 untyped contracts of 291** (3 declare stacks).
   Every candidate is typed, so every candidate is judged, and the gate has
   data on every axis.
3. The planner chooses tokens from the roster's vocabulary, not from what the
   roster can cover. `_known_intent_vocabulary` (lines 1449-1465) shows it the
   union of declared domains and capabilities, and the planner system prompt
   tells it to reuse them. It has no view of which domain, capability,
   artifact and authority combinations any eligible contract satisfies. On
   this roster:

   | token | contracts that cover it |
   |---|---|
   | `domain:desktop` | 1 (modify authority only) |
   | `domain:backend` | 3 (plan and modify; no review) |
   | `capability:operations` | 6 of 291 |
   | `capability:threat-modeling` | 4 |
   | `capability:coordination` | 4 |
   | `artifact:test-code` | 3 |

   `capability:operations` is scarce because `_operations_rule`
   (`staffing_verifier.py:224`) admits only contracts with a `coordination` or
   `release` lifecycle phase or an explicit `operations` capability id. A plan
   unit for installing software names `operations` every time.
4. The prompt and the validator contradict each other. `_RECRUITER_SYSTEM`
   (`inference.py:298`) says `uncovered_requirements` "never mandates a gap on
   its own"; lines 306-308 say "imperfect typed coverage is recorded honestly
   on the receipt, never a reason to leave good candidates unstaffed". Line
   317 then asks the model to verify full typed coverage before returning
   `staff`. The validator enforces only the last sentence. For a unit with a
   roster-wide uncovered token the only accepted answer is `gap`, which the
   prompt discourages and which sends a coverable specialty to hiring.

So the answer to "is the model, the schema or the validator wrong" for this
class is: the contract between the planner's vocabulary and the verifier's
sufficiency rule is wrong. The model followed its instructions, the transport
schema was satisfied, and the validator applied its rule exactly.

## Current state

Filed from the AR-383 investigation. The prior-session receipts show the same
shape on every install-flavoured prompt (`unit-install-plan`,
`unit-install-execution`, `unit-zed-install-operation`: `domain` axis, one
required candidate, two or three executable, no team), and AR-373's own
captured example, a `plan` unit carrying `domain:platform` with
`devops-automator` required at 0.85, fits it as well.

**Implemented on branch `claude/ar384-coverage-gaps` (2026-09-03)** per
[ADR-0198](../decisions/0198-waive-the-typed-requirements-the-roster-declares-but-cannot-serve.md).
`typed_staffing_coverage_gaps` splits a unit's uncovered tokens into `waived`
(declared by some enabled typed contract, covered by none eligibly) and
unknown (declared by nobody). The team search drops waived tokens and the
verifier records each as `roster_coverage_gap` with the token as detail;
unknown tokens stay mandatory. `typed_recall` rows carry
`waived_requirements`, the prompts and repair contract say which tokens are
waived, and `_operations_rule` reads the `operations` domain.

Two findings changed the shape of option 1 during implementation:

1. Waiving `domain:desktop` alone left the captured helix reply rejected on
   `capability:operations`: its only eligible coverer was
   `incident-response-commander`, which the recruiter had not ranked, because
   `_operations_rule` never read the audited `operations` domain that
   `operations-manager`, `sre-site-reliability-engineer` and
   `it-service-manager` declare.
2. A blanket waiver broke
   `test_named_regulated_assurance_requires_explicit_contract_coverage`: a
   named specialty nobody declares must stay a hiring gap.

Offline replay of the captured helix recruiter reply (`raw/103-calls.json`
from the AR-383 capture) through the branch verifier against the installed
291-contract roster: nomination validation accepted, `unit-install-operation`
selected `operations-manager`, `verify_staffing` accepted with one
`roster_coverage_gap` for `domain:desktop`.

Live re-measurement, nine fresh install-flavoured wordings through
`run_preflight` on the branch runtime (evidence in
`docs/roadmap/acceptance/evidence/AR-384-evidence-20260903.txt`):

| outcome | turns |
|---|---|
| verifier accepted the install unit, `roster_coverage_gap` recorded, strict critic vetoed the turn | 4 (203, 204, 205, 209) |
| recruiter reply cut at the 2048-token budget, AR-385 | 4 first attempts (201, 204, 206, 209), 2 turns lost (201, 206) |
| evidence charset residue, AR-373 | 2 turns lost (202 repair, 208) |
| `staff_without_safe_team:domain` on a coverable token | 3 turns (202, 205, 207), all `domain:platform` |
| verifier rejected a staff decision on a waived token | 0 |

Turn 203 is the helix criterion: `unit-install-plan` (domains `desktop` and
`operations`, plan authority, the captured shape) selected `operations-manager`
with `roster_coverage_gap domain:desktop`, and the turn then died at the strict
critic (`wrong-neighbor-selection`, `missing-implementation-lifecycle-assurance`),
which is AR-386.

**Verification (2026-09-03).** The acceptance record is frozen at
`1711bcaa`; the isolated verifier found criteria 1 and 3 satisfied and
criterion 2 contradicted, because the criterion names `unit-install-operation`
literally while the fresh-wording turn's planner named the captured-shape unit
`unit-install-plan`. Under the AR-386 runtime turn 304 (`Get the helix text
editor working in my shell on this box`) staffed `operations-manager` on both
plan-authority install units of that shape and completed. Whether the
criterion should name the shape rather than the id is the owner's call.

**Residue, this issue's option 2.** The planner names `domain:platform` for
the operating system; the roster's `platform` domain means API platforms and
its only eligible coverer is `api-platform-engineer`. The token is coverable,
so it stays mandatory, the recruiter is pushed to rank a wrong neighbour, and
the critic then objects. Constraining the planner's vocabulary to what the
roster can serve is the remaining fix, and it is not small.

## Approach

**Decision, 2026-09-03: option 1, amended.** Roster-wide unserved tokens are
advisory; tokens no contract declares stay mandatory; the `operations`
capability also reads the `operations` domain. The reasoning, the alternatives
and the two departures from the option as filed are in
[ADR-0198](../decisions/0198-waive-the-typed-requirements-the-roster-declares-but-cannot-serve.md).
The options as filed follow.

1. **Make roster-wide uncovered requirements advisory.** When
   `_typed_shortlists` proves that no eligible contract covers a token, drop
   that token from the sufficiency check for that unit and record it on the
   receipt as an honest coverage gap. This is what the prompt already
   promises. Tokens some eligible contract does cover stay mandatory, so the
   conjunctive rule still catches a ranking that omits an available
   complement. Smallest change; touches `_validate_nomination_decisions` and
   the receipt.
2. **Constrain the planner to coverable combinations.** Show it, per domain
   and capability, the authorities and artifact kinds the roster can serve,
   and validate plans against that. Larger, and it moves the failure to the
   planner stage rather than removing it.
3. **Enrich the scarce tokens.** Give operational specialists the
   `operations` capability and desktop or backend domains where they apply.
   Roster work; it narrows the problem without closing it.

Not proposed: reinstating wildcard coverage, or weakening eligibility. Both
would let an unproven candidate through on an axis that carries a safety
property.

## Dependencies

- AR-386 owns the strict critic vetoes that now end every verifier-accepted
  install turn.
- AR-373 owns the evidence-vocabulary residue seen on the repair attempt.
- AR-385 owns the truncated first attempts that hide behind the same
  `provider_response_contract_invalid` code.
- AR-374 owns why so few candidates are executable in the first place; this
  issue is about units no executable candidate can cover.

## Acceptance

- [x] A `staff` decision whose ranked team covers every requirement some
      eligible contract can cover is accepted, and the receipt names the
      roster-wide uncovered tokens instead of rejecting the team.
- [x] The captured helix-install turn, re-run with fresh wording, staffs
      `unit-install-operation` with `operations-manager` selected. Evidenced
      at the verifier: the captured reply replays to an accepted decision, and
      live turn 203 reaches the same decision before the strict critic vetoes
      the turn (AR-386).
- [x] `staff_without_safe_team` on the `domain` axis no longer appears on any
      receipt whose `typed_recall.uncovered_requirements` names that same
      domain token.
