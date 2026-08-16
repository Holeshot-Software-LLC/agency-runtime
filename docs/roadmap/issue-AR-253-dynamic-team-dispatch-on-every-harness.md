---
title: "AR-253: Prove staffing latency, rate, and cross-host parity"
status: open
category: roadmap
created: 2026-08-05
updated: 2026-08-16
tags: [workforce, staffing, latency, harnesses, eval, host-evidence]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0132-fund-one-repair-per-workforce-inference-stage.md
  - docs/decisions/0153-adopt-per-stage-inference-profile-routes.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0157-automatically-promote-host-verified-contractors.md
  - agency_runtime/core/workforce/staffing_verifier.py
  - agency_runtime/adapters/hooks.py
supersedes: []
superseded_by: null
type: issue
epic: workforce
issue_id: AR-253
priority: p0
tracker_url: null
depends_on: [AR-180, AR-252, AR-255]
blocks: [AR-119]
---

# AR-253: Prove staffing latency, rate, and cross-host parity

## Problem

The prior issue described per-plan-row Job B dispatch, which has been retired.
The live remaining product contract is narrower and harder: measure whether
inference staffs host-spawned children, how long the decision and delivery take,
whether every supported host writes proof of multiple delivered cards, and
whether accepted outcomes drive the same automatic-promotion behavior.

Current computed routing is far outside the pinned 15,000 ms cold budget: the
AR-119 evidence reports roughly 2.4 provider calls per decision, p50 88.3 s,
and p95 195.9 s. Claude has three positive prior-candidate Rule-4 artifacts;
Codex has prior-candidate negative observations across TUI, Desktop, and exec
and a current source negative. Neither host has exact-candidate installed/live
proof; ZCode, Hermes, and OpenClaw are unproven.

## Where the latency actually is (measured 2026-08-14, `9e29aabe`)

The budget overrun is **the recruiter stage**, not process overhead. Measured on
one live Windows workstation against the real `claude-subscription` CLI
transport:

| what | measured |
|---|---|
| `claude -p` process cost under the transport's own isolated environment | 8.3 s warm, 9.2 s cold |
| planner call, end to end | 15.9 s |
| recruiter call, end to end | 59.3 s and 94.0 s |
| one accepted in-path turn (hook surface, 5 specialists, confidence 1.0) | 106.3 s |

Subtracting the ~9 s process floor, the planner spends ~7 s on inference and the
recruiter **50-85 s**, so the recruiter is roughly 7-12x the planner and owns the
overrun. A fresh isolated home costs no more than a reused one (9.2 s vs 8.3 s),
so pooling or warming the transport's home directory is not the lever.

Two measurement traps were found in the process, both of which inflate numbers
that look like product latency:

1. **A direct `claude` CLI run while a Claude session is open stalls exactly
   60 s** on `~/.claude.json` lock contention — the debug log says
   `Lock acquisition took longer than expected - another Claude instance may be
   running`. The same invocation costs 83-95 s with the lock and 8-9 s without.
   **Agency's transport is not affected**: `_isolated_invocation_environment` in
   `agency_runtime/core/cli_transport.py` redirects `HOME`/`USERPROFILE`/
   `APPDATA` to a private directory while keeping `CLAUDE_CONFIG_DIR` real, which
   preserves authentication and sidesteps the lock. Do not attribute this 60 s to
   Agency.
2. `agency route` from the CLI runs on an unproven surface and rejects 251 of 282
   candidates as `execution_host_unproven`, so its latency and its
   `staff_without_safe_team` failures are both artifacts. Measure staffing from
   `routing_decisions` rows produced by the hook path.

The earlier p50 88.3 s / p95 195.9 s figures are therefore plausible as real
inference cost rather than startup overhead, and the remeasurement should target
the recruiter prompt — 282 candidates per call — before anything else.

## Current state

`agency evidence latency` exposes overall and decision-source distributions,
but there is no fixed staffing-rate harness that joins selection, host spawn,
card delivery, and per-stage latency. Existing Agency Store rows cannot stand
in for host-written delivery proof.

## Approach

Add `agency eval staffing` over a versioned ask set. Report valid-decision,
staffed-child, multi-card host-proven-delivery, accepted-outcome, promotion, and
failure rates plus provider, validation, delivery, and end-to-end latency.
Preserve the one-call fast path and reuse one inference-owned parent decision
for children; optimize prompts, stage routing, cache identity, and bounded
repair without weakening ADR-0118 or evidence gates.

"One staffing call" means one successful recruiter/staffing decision after any
separate intent-planning stage; it does not silently supersede ADR-0132's bounded
planner and recruiter repair allowances. Report all stage attempts and latency.

Prove Claude and Codex locally, then ZCode, Hermes, and OpenClaw on installed
hosts. Unavailable hosts remain explicitly unproven.

## Dependencies

- AR-255 owns inference and evidence authority.
- AR-180 owns the Codex live canary after that authority is repaired.
- AR-252 owns the accepted-outcome and automatic-promotion implementation that
  this issue proves across every host.
- AR-125 owns the separate matched Agency-on/off value claim.

## Acceptance

- [ ] `agency eval staffing` emits a machine-readable manifest with fixed asks,
      candidate identity, stage timings, decision validity, selected cards, and
      host-artifact correlation.
- [ ] The configured path uses no more than one successful recruiter/staffing
      decision per turn and meets the unchanged 15,000 ms cold budget.
- [ ] At least 95% of valid selection-requiring fixed-set asks are staffed and delivered; invalid,
      timed-out, or malformed provider arms are reported, never scored as
      staffing losses.
- [ ] On Claude, Codex, ZCode, Hermes, and OpenClaw, at least one host-spawned
      child has a current host-written proof of two or more compatible,
      inference-selected cards before first speech. One child with one card is
      not Rule-4 completion.
- [ ] Every supported host independently admits at least one host-evidenced
      producer outcome plus a distinct inference-selected verifier's bound
      verdict into the same normalized accepted-outcome contract.
- [ ] The host-agnostic promotion core has no host-specific branch and promotes
      an eligible contractor after any three distinct normalized accepted
      outcomes, including a mixed-host case, with no operator action.
- [ ] An unavailable supported host remains visibly unproven and cannot satisfy
      this issue or AR-119 closure.
- [ ] Optimization introduces no deterministic specialist choice, evidence
      downgrade, conversational hard block, or unsupported superiority claim.

## The recruiter rejection is a plan defect wearing a recruiter's name (2026-08-15)

> **RETRACTED the same day by the live canary.** This section's conclusion is
> wrong for the canary's unit: the plan is fully coverable and the fault is the
> recruiter's ranking. Its mechanics — conjunctive coverage, and why a repair
> aimed at the recruiter cannot fix a plan — remain correct and are why the
> domain boundary still belongs where it was put. See "The canary refuted the
> plan-defect diagnosis" below.

With the runtime repaired, the live Claude canary reaches routing and dies at
`workforce_inference_failed` / `inference_invalid`. The receipt now explains
itself: both recruiter attempts on sonnet were rejected
`provider_response_contract_invalid` with one identical validation failure,
`staff_without_safe_team` on `unit-python-strip-regression-review`, and
`eligibility_reason_codes` empty.

`staff_without_safe_team` fires in `_validate_nomination_decisions` when the
recruiter decided `staff` but `proposal_row.selected` came back empty — that is,
no team within `max_selected_per_unit` (4 here) covers `_requirements(unit)`.
Coverage is conjunctive across six axes: `artifact`, `lifecycle`, `domain`,
`stack`, `capability`, `authority`. **If any one axis is uncoverable by the
whole roster, no ranking the recruiter could return would help.**

Measured offline against the live 283-contract roster, no inference involved:

- A realistic review unit (`review-report` / `review` / `software-engineering` /
  `python` / `review` / `review`) **is** staffable.
- Sweeping every roster-declared value one axis at a time: **0 of 8 lifecycles,
  0 of 8 artifact kinds and 0 of 4 authorities are unstaffable.** The typed
  space is healthy.
- A single off-vocabulary value is fatal and permanent: `lifecycle:verification`,
  `artifact:code-review`, `domain:code-review` each leave exactly that
  requirement uncoverable.

So the question is what the planner is allowed to emit. Two gaps, and only two:

1. **`lifecycle_phase: coordination` is enum-legal and declared by zero
   contracts.** `_LIFECYCLES` carries nine values, the roster declares eight;
   `coordination` is the orphan. Any unit planned in that phase is structurally
   unstaffable. (`_ARTIFACTS` has no such gap — enum and roster match exactly.)
2. **`domains` is an unvalidated free identifier.** `_parse_unit` enum-checks
   artifact, lifecycle, authority, mutation and parallelization, but domains go
   through `_items(..., identifiers=True)` with no allowed set. The planner is
   *shown* the roster's 30 domains by `_known_intent_vocabulary` and merely
   asked to use them, so an invented domain parses cleanly and is uncoverable.

Both explain the observed behaviour exactly: deterministic per plan, identical
on retry, and nondeterministic across runs because the planner picks differently
each time. **The retry cannot help, because the repair prompt is addressed to
the recruiter and the plan is what is wrong.** That also explains why the canary
"passed this stage" on one run and failed on the next with no code change.

Three candidate fixes, which differ in what they do to evidence and should not
be chosen casually:

- **Validate domains at plan parse.** An invented domain becomes an invalid
  plan with a planner-targeted repair, instead of surfacing as a recruiter
  failure two stages later. Narrowest, and it puts the error where the fault is.
- **Give uncoverable axes the stack wildcard.** `_coverage` already treats an
  axis no contract declares as neither proven nor disproven for stacks. Applying
  that to domain and lifecycle would absorb both gaps, but it weakens the
  sufficiency proof the verifier exists to make.
- **Route the repair by fault.** Send structural failures back to the planner
  and semantic ones to the recruiter. Most correct, largest change.

Whichever lands, the receipt should also name **which requirement axis was
uncoverable**, not just the unit. The axis names are a closed six-value
vocabulary, so this costs no evidence bounding, and without it every future
occurrence needs the same offline reconstruction this one did.

## Domains are validated at the plan boundary (2026-08-15)

The first option shipped. `parse_work_unit_plan` now takes an optional
`allowed_domains` vocabulary, and `compile_intent_plan` — the one boundary that
knows the live roster — supplies it. An unknown domain is refused there, by
name, and `_invoke_stage` sends the failure back to the **planner** under the
planner's own system prompt with the offending value in the feedback. The
recruiter never sees the unstaffable unit.

Two corrections to the diagnosis above, both found while building the fix:

1. **An unknown domain is not always a defect.** `_validate_nomination_decisions`
   only rejects `staff` decisions; a recruiter that answers `gap` is valid, and
   that gap is what drives hiring. `test_open_ended_pool_can_declare_gap_without_
   inventing_a_roster_candidate` plans `domains: ["quantum-build-systems"]` with
   `novel_capability: "quantum-build-evaluation"` precisely so the recruiter can
   declare `inference-declared-gap`. A blanket refusal would have closed the
   rule-6 contractor path. The shipped rule therefore refuses an unknown domain
   **only when the unit declares no novel capability** — novelty is the
   contract's existing signal for work the workforce genuinely lacks, and a unit
   that claims none has invented a narrower synonym for work already covered.
2. **`lifecycle_phase: coordination` cannot be the live cause.** The compact
   planner never chooses a lifecycle: `_unit_document` derives it from the
   artifact through `_ARTIFACT_FACTS`, whose nine entries yield only discovery,
   design, documentation, implementation, planning, review and testing. The
   orphan enum value is unreachable from the synchronous path, so **domains were
   the only planner-chosen axis that could go off-vocabulary.**

The compiler still normalizes first and refuses only what normalization could
not place, so the planner's vocabulary is not narrowed. Measured against the
live 283-contract roster for the canary's own ask:

| planner domain | normalizes to | in roster | coverable | at the boundary |
|---|---|---|---|---|
| `software-engineering` | `software-engineering` | yes | yes | accepted |
| `code-review` | `software-engineering` | yes | yes | accepted |
| `regression-testing` | `quality-assurance` | yes | yes | accepted |
| `python-development` | `software-engineering` | yes | yes | accepted |
| `code-quality` | `quality-assurance` | yes | yes | accepted |
| `text-normalization` | *(unchanged)* | no | **no** | refused |
| `text-processing` | *(unchanged)* | no | **no** | refused |
| `string-handling` | *(unchanged)* | no | **no** | refused |

Three of eight plausible domains for one ordinary review request leak through
normalization verbatim, are coverable by no team of four, and previously reached
the recruiter as an unwinnable `staff_without_safe_team`. Five are rescued and
still accepted.

**What this is not.** The canary's actual plan is unrecoverable: `routing_intent`
and `routing_cache` are empty, the workforce cache is in-process, and
`preflight_failure_receipts.provider_attempts` deliberately records attempt
metadata without response content. So the exact domain that killed the live run
is unknown, and this fix is proven by mechanism against the real roster, not by
replaying the failure. **The next live Claude canary is the test.** If it fails
the same way with a plan whose domains are all roster-declared, the fault is
elsewhere and this section is wrong.

## The receipt names the uncoverable axis (2026-08-15)

Nothing in the stored evidence distinguished a domain gap from a lifecycle or
authority gap, which is why the diagnosis needed offline reconstruction and why
its second gap turned out to be unreachable. `staff_without_safe_team` now
carries the axis.

`_uncoverable_requirement_axis` asks the one question the receipt could not
answer: is there a requirement **no contract in the roster covers**? The axis
names come from `REQUIREMENT_AXES` in `staffing_verifier.py`, beside the
`_requirements` function that produces them, so the vocabulary is not restated
per consumer. It is a closed six-value set carrying no request content, so it
crosses the content-free receipt boundary; `project_nomination_failures` emits
it as `requirement_axis` and fails closed on anything outside the vocabulary.

**The axis is a fault classifier, not decoration.** Present, it says the plan or
the roster is at fault and no ranking the recruiter could return would help.
Absent, it says the roster could have covered every axis and the ranking is at
fault — which is the recruiter's own mistake and is exactly what its bounded
repair is for. This morning's investigation spent a day on a question that is
now one field.

Naming the axis also makes the funded repair recoverable rather than doomed.
When an axis is uncoverable, the repair prompt now says so and states the only
honest answer — declare gap — instead of asking for a faithful ranking that
cannot exist. `test_recruiter_repair_declares_gap_when_typed_recall_proves_
uncovered_requirements` already covered a roster that cannot supply
`capability:automation`; the recruiter reached the same gap by inference, and
now it is told.

Editing the `staff_without_safe_team` line required updating the matching
`before` snippet in `core/evals/decision_conformance.py`, which stores literal
source text for the mutation proof. That coupling is invisible from the edit
site and belongs on the list of duplicated facts this codebase keeps.

## The canary refuted the plan-defect diagnosis (2026-08-15)

The runtime was republished as `0e42ee679dfc` carrying the domain refusal, and
the live Claude canary was run against it. It failed **identically to before
the fix**: `staff_without_safe_team` on `unit-python-strip-regression-review`,
on both funded recruiter attempts. The falsification condition written into the
section above fired, so that diagnosis is retracted.

The axis field settled it in one read, which is what it was built for. It is
**absent** on that failure, and the installed launcher's own projection emits
`requirement_axis` when one exists, so the absence means what it says: no
requirement axis is uncoverable.

Verified offline against the live 283-contract roster, no inference spent:

- The unit needs six things — `artifact:review-report`, `lifecycle:review`,
  `domain:software-engineering`, `stack:python`, `capability:review`,
  `authority:review`. **The whole roster covers all six.**
- Filtered to a claude/windows execution context, **10 of 283 contracts are
  eligible — and each of the ten covers the unit essentially single-handed.**
- `code-reviewer`, the specialist the canary expects, appears exactly once, is
  enabled, is eligible, and covers all six alone.
- The typed shortlist the recruiter receives carries 24 candidates,
  `uncovered_requirements: []`, and 10 marked `execution_eligible`.

Simulating the deterministic team build from candidate rankings reproduces the
failure exactly:

| ranking supplied | resulting team |
|---|---|
| only `python-cli-architecture-specialist` (in shortlist, `eligible=False`) | `()` → `staff_without_safe_team` |
| `code-reviewer` | `('code-reviewer',)` |
| ineligible first, `code-reviewer` second | `('code-reviewer',)` |

**The failure requires a ranking containing no eligible candidate at all.** One
eligible name anywhere in it rescues the team. So this is a recruiter ranking
fault, and `staff_without_safe_team` is actively misleading here: it asserts no
safe team exists while ten do. The funded repair then tells the recruiter to
"rank at least one semantically faithful candidate", which it believes it
already did — which is why the retry reproduces rather than recovers.

`python-cli-architecture-specialist` is the obvious lure: it sits in the same
shortlist, it is the aptest-sounding name for reviewing a one-line Python
change, and it is ineligible. Ordering cannot warn against it, because ADR-0118
forbids a local preference — candidates are ordered by coverage count then
identity, never by fit.

**What shipped now is evidence only, deliberately.** The failure records the
agent ids the recruiter actually ranked, projected as `ranked_agent_ids`
alongside the unit and the axis. Recruiter behaviour is unchanged, so the next
canary run either shows a ranking with no eligible candidate — confirming the
mechanism from evidence instead of reconstruction — or shows something else and
refutes this too. The remaining fix, once confirmed, is a distinct reason code
for "ranked only ineligible candidates" and a repair that names the eligible
subset rather than restating an instruction the recruiter already believes it
followed.

## The recruiter ranks the right specialist first and still declines (2026-08-16)

`ranked_agent_ids` fired live for the first time in the `530f6df6c4b6` canary,
and it settles the question the offline simulation could not. Both recruiter
attempts on `unit-review-textorm-strip-regression` were rejected
`provider_response_contract_invalid` carrying `staff_without_safe_team`, and both
ranked the sufficient specialist **first**:

- attempt 1: `code-reviewer`, `application-security-engineer`,
  `senior-secops-engineer`, `codebase-onboarding-engineer`
- attempt 2: `code-reviewer`, `application-security-engineer`,
  `senior-secops-engineer`, `ai-generated-code-security-auditor`,
  `codebase-onboarding-engineer`

`requirement_axis` is absent from both, so the roster covers every requirement
and this is not a coverage gap. `code-reviewer` is eligible and covers the unit
alone. **So the recruiter is not ranking only ineligible candidates — it ranks
the correct candidate at position one and then does not select it.** The fault
is between ranking and selection, in what the recruiter puts in the team, not in
what it was shown or how the plan was compiled. Every earlier diagnosis on this
issue that blamed the ranking order is superseded by this evidence.

The same receipt is the first host proof that the flat `ranked_agent_ids`
projection stores and reads correctly at the reader's `maximum_depth=4` bound;
the nested form it replaced had blocked the preceding canary attempt outright.

Not advanced by this run: the canary completed (`exit 0`, no timeout) but failed
with three unmet prerequisites — isolated-profile plugin registration and
enablement unproven, final response header unproven, and `delivery_marker_absent`.
The parent turn died at routing, so the AR-255 child-staffing repairs shipped the
same day — the capability receipt and the abstention reason — were never reached
and remain unexercised on a host.
