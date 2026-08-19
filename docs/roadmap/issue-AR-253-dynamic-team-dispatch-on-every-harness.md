---
title: "AR-253: Prove staffing latency, rate, and cross-host parity"
status: open
category: roadmap
created: 2026-08-05
updated: 2026-08-18
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
  - docs/decisions/0160-pin-child-judge-providers-per-canary-harness.md
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

## 2026-08-19 child-judge provider policy

ADR-0160 now makes canary child-judge choice a persistent per-harness map,
instead of an ambient consequence of provider order and transport
availability. It is canary-only, uses one provider with no fallback, and
records both the requested and actual answering provider. This implements the
owner's desire to switch harnesses without re-pinning global configuration.

Codex and Claude remain the supported structured CLI judge transports. The
canary pin can now also resolve one existing supported Anthropic-compatible
inference profile, so ZCode may use its configured GLM profile without adding
that profile to or reordering the ordinary provider chain. Historical ZCode
Store receipts confirm GLM profile execution before this candidate; they are
not current canary proof. ZCode still needs a safe noninteractive native canary
backend. No parity or matrix claim follows from profile resolution or the
config shape.

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

### All three canary prerequisites reduce to this one fault

The `530f6df6c4b6` run also looked like an isolated-profile plugin failure —
`isolated_plugin` came back `registered/enabled/loaded/invoked: None` with only
`load_requested: true`. It is not a plugin fault. `profile_is_proven` requires,
for Claude, `load_requested is True and plugin_invoked`, and
`plugin_invoked = bool(evidence["correlated_trace_ids"])`, where
`correlated = route_traces & final_traces`. The run recorded **zero** routing
decisions, so that intersection is empty and every derived plugin field projects
`None`.

Agency was demonstrably live inside the disposable profile: it opened run
`8eb4f96b`, ran the planner (`claude-haiku`, `structured_response_applied`), ran
the recruiter twice (`claude-sonnet`), wrote one finalization and one preflight
failure receipt with complete provider attempts. **An earlier reading of this run
as "Agency may not have been active in the canary profile" is retracted.**

So the three unmet prerequisites are one fault with three faces: no routing
decision means the profile cannot be proven, the parent turn fails preflight so
no Agency header is emitted, and no staffing decision means no cards and
`delivery_marker_absent`. **The ranking-to-selection gap is therefore on the Rule 4
critical path directly** — it is not a parallel AR-253 latency concern, it is the
single thing standing between this machine and its first Installed/Live cell.

### The ranked set does not cover the unit; the roster does (2026-08-16)

The `470ebf3b421a` canary answered the question `top_ranked_ineligibility` was
built for, by being **absent**. Both rejected recruiter attempts on
`unit-python-strip-regression-risk-analysis` ranked `code-reviewer` first and
carried no ineligibility reason, so the top-ranked candidate was executable.
Eligibility is not what empties the team.

`selected` is not the model's answer. `_minimum_team_with_required` computes it
by searching combinations of the ranked, executable candidates for one whose
union of `_coverage(unit, contract)` contains every entry of
`_requirements(unit)`, and returns `()` when no combination within
`max_selected_per_unit` does. Coverage is conjunctive across six axes.

So `staff_without_safe_team` means **the ranked candidates jointly miss at least
one required axis**, while `_uncoverable_requirement_axis` asks whether *the
whole 283-contract roster* could cover it and therefore reports nothing. The
axis field answers a different question than the failure asks, which is why it
has been empty on every live failure.

## The Claude canary reported a deadline as a host refusal (2026-08-16)

The first run against `76dd96b2cc50` came back `status: "failed"`,
`exit_code: 124`, `timed_out: false`, with five unmet prerequisites headed by
"host invocation did not complete successfully". Read literally that says the
host ran and refused, which is a recruiter question. It is not what happened.

`run_bounded_text_capture` sets `returncode = 124, timed_out = True` on
`subprocess.TimeoutExpired`. `codex_canary_record` carries both through —
`status: "timed_out"`, `failure_reason: "codex_exec_timed_out"`.
`claude_canary_record` read neither: it derived status solely from
`_process_succeeded`, so a Claude timeout published a **false** `timed_out`
beside the timeout's own exit code. The two backends disagreed about how to
report the same event.

The store settles what actually happened. Run `5667202f` opened at 18:26:28 and
the report sampled at 18:28:25 — 117 seconds, against the CLI's undeclared
120-second default. Zero routing decisions, zero preflight failures, zero
receipts: Agency's SessionStart hook opened the run and the deadline arrived
before the parent turn reached staffing.

Fixed by giving `claude_canary_record` the Codex idiom, with
`claude_exec_timed_out` added to `CANARY_INVOCATION_FAILURE_REASONS` and a
regression test asserting the three fields together. This is the same shape as
the `ranked_agent_ids` depth break: an evidence field that reads as a definite
negative when the real answer is "not measured". **A canary that cannot
distinguish its own deadline from a host refusal cannot be trusted to report a
staffing failure**, and this one nearly sent a fourth diagnosis after the wrong
cause.

Open, and deliberately not guessed at: whether 120 seconds was ever sufficient.
The `530f6df6c4b6` and `470ebf3b421a` runs completed inside it, so either the
cold isolated profile got slower or something in the parent turn now hangs. The
re-run carries an explicit `--timeout` and answers that from evidence.

**Answered by the re-run.** At `--timeout 420` the same canary completed
cleanly: `exit_code 0`, `status: completed`, `timed_out: false`, three unmet
prerequisites rather than five. The default was simply too short for a cold
isolated profile on this machine, and nothing hangs. Use an explicit
`--timeout` for Claude isolated-profile runs.

## The axis was scoped to the ranked set and is still absent (2026-08-16)

The `76dd96b2cc50` canary is the first run carrying the ranked-set scoping, and
it **refutes the conclusion that shipped with it**. Both recruiter attempts on
`unit-python-text-normalization-strip-review` were rejected
`provider_response_contract_invalid` / `staff_without_safe_team`, both ranked
`code-reviewer` first, and both carry **no `requirement_axis` and no
`top_ranked_ineligibility`**:

- attempt 1: `code-reviewer`, `application-security-engineer`,
  `senior-secops-engineer`, `ai-generated-code-security-auditor`
- attempt 2: the same four plus `test-results-analyzer`,
  `codebase-onboarding-engineer`

The scoping is confirmed present in the running projection (`scope = [item for
item in contracts if item.agent_id in ranked_ids]` at
`site-packages/agency_runtime/core/workforce/inference.py:1409`), so this is not
a stale-launcher artifact. And `typed_staffing_coverage` /
`typed_staffing_requirements` are literally `_coverage` / `_requirements` — the
axis field and the verifier compute the same union over the same fields. So
**the ranked set does cover every requirement, and the team search still
returned nothing.** The prior section's conclusion — that the conjunctive
requirement set applied to the ranked candidates is what empties the team — does
not survive its own first measurement and is retracted.

### What the search actually scores

`_minimum_team_with_required` is called with the **executable** ranked ids:

~~~python
executable = [
    (agent_id, score) for agent_id, score in semantic
    if agent_id not in forbidden_ids and not _eligibility(unit, roster[agent_id], context)
]
selected = _minimum_team_with_required(
    unit, tuple(a for a, _s in executable), roster, required_ids,
    active_budget.max_selected_per_unit,
)
~~~

The axis was scored over **all** ranked contracts. An axis covered only by an
ineligible ranked candidate therefore read as covered while being unavailable to
any team. Fixed: `_failure_axis` filters the ranked scope through
`typed_staffing_ineligibility` before scoring, and widens back to the full
ranked set when nothing survives, so an entirely unrunnable ranking still
reports through `top_ranked_ineligibility` instead of inventing an axis.

The dedicated regression test owed from the previous change now exists, and it
records the non-obvious part: `_eligibility` already gates domain, capability
and authority, so a candidate missing one of those is never executable and the
two scopes agree. **Artifact and lifecycle are coverage-only** — they are the
axes where the scopes can disagree, and where the field was silently wrong.

### The three branches that remain, and the numbers that separate them

If the executable-scoped axis also comes back absent, the executable ranked set
covers everything and `()` came from one of three remaining paths in
`_minimum_team_with_required`:

1. `len(required_ids) > max_selected_per_unit` (4 here, unset in `agency.yaml`).
   Attempt 2 ranked six candidates, so this is reachable; attempt 1 ranked four,
   so it is not, and one mechanism must explain both.
2. Budget starvation — `required_ids` is smaller than the cap but leaves too few
   slots for the complements that would finish coverage, so the combination loop
   `range(1, min(maximum - len(ordered_required), len(remaining)) + 1)` is empty
   or too short.
3. `required_ids` not a subset of the executable ids. `_semantic_classes`
   already demotes ineligible model-required picks into `forbidden`, so this
   should be unreachable — which makes it worth proving rather than assuming.

Three integers separate all three: `len(required)`, `len(ranked_executable)` and
`max_selected_per_unit`. `UnitRecruitment` already carries the first two at the
failure site. That is the next instrument, and unlike the axis it needs a
projection change, so it is written down here rather than added in haste — the
`ranked_agent_ids` depth break came from exactly that kind of hurry.

## The staffing failure is intermittent, and the next run staffed (2026-08-16)

The `33ac14fcdac4` canary **succeeded at parent staffing**. Routing `6f383f65`
was `accepted` from `computed`, selecting `code-reviewer` and
`senior-secops-engineer` out of 284 candidates, with both cards written to
`specialists_loaded` and the receipt correlated. Zero preflight failures.

The only code difference from the run that failed twenty-five minutes earlier is
`_failure_axis`, which computes an evidence string and cannot affect selection.
So **`staff_without_safe_team` is intermittent, not a deterministic mechanism**,
and every diagnosis on this issue that treated it as one — including the three
already retracted — was reading run-to-run variance as structure.

The two runs are not repeated trials of the same input. The planner synthesises
the units, and it produced `unit-python-text-normalization-strip-review` on the
failing run and a single unit on the succeeding one. Unit synthesis varies, the
requirement set varies with it, and the team search varies with that. That is
the most economical account of every observation so far: absent axis, absent
ineligibility, `code-reviewer` ranked first, and an empty team.

This does not retire the instrument. Intermittent means the budget branches in
"The three branches that remain" are still the place to look, and it raises the
bar for reading any single run: **a green staffing run no longer proves the
failure is fixed, and a red one no longer proves a mechanism.** Failure rate
across repeated runs is now the measurement, not the content of one receipt.

Recruiter latency on the accepted row was **124,165 ms**, consistent with the
50-85 s and 124.0 s already recorded here. The overrun is unchanged.

## Both canary records now answer a protocol error the same way (2026-08-16)

Two tests asserted contradictory contracts for the same case — a host that exits
0 whose stdout cannot be projected. `test_complexity_refactors.py` demanded
`exit_code == 1`; `test_canary_coverage_complete.py` demanded `exit_code == 0`
plus a typed `failure_reason`. The first had been **red on main** and neither
file was in the gate spine, so nothing failed.

`canary_proof.py` settles which is right:

~~~python
process_ok = result.get("status") == "completed" and result.get("exit_code") == 0
~~~

`status` already fails a protocol error closed, so the synthesised `exit_code=1`
in `claude_canary_record` bought no safety and misreported what the host did.
`exit_code` is a fact about the process; `status` is the verdict. Claude now
matches Codex: the real returncode, `status: "failed"`, and a typed reason —
`claude_result_projection_unavailable` when the payload will not parse,
`claude_output_projection_unavailable` when it parses without a result. Dropping
the synthesised code without those two reasons would have *lost* the diagnostic
it was crudely standing in for.

### The spine was a fourth copy of a list nobody could see drift

`tests/test_canary_coverage_complete.py` and `tests/test_complexity_refactors.py`
are now in the production spine. Adding them meant editing the spine in **four
hand-kept places**: `scripts/run_local_gates.py`, `.github/workflows/ci.yml`,
`AGENTS.md`, and a pinned expectation inside `test_release_packaging.py`.

They had already drifted. **`AGENTS.md` was missing `test_storage_file_trust.py`
and `test_upstream_selection_eval.py`**, so the documented spine and the enforced
one were different suites, and had been for long enough that nobody noticed.

Fixed the way this repository already fixes it one assertion further down, where
the matrix-evidence list is derived rather than copied: `test_release_packaging`
now imports `PRODUCTION_SPINE` and checks both `ci.yml` and the `AGENTS.md`
Validation block against it. One source, two derived checks, and a doc that can
no longer quietly disagree with the gate. Verified with a drop-one control:
removing a single entry from the doc block makes the comparison fail.

Two further silent-empty paths in the same function deserve receipts:
`required_ids` not being a subset of the ranked ids, and `len(required_ids)`
exceeding `max_selected_per_unit`.

**The bounded fix is to compute the uncoverable axis over the ranked set rather
than the roster.** That names the axis the ranking actually missed, which is
also the one thing a bounded repair could act on — it can tell the recruiter to
add a candidate covering that axis instead of re-ranking blind. It is an
evidence and repair change, not an architecture change, and it targets the live
Rule 4 blocker directly.

This also re-aims the planner-scope finding. The binding constraint is the unit's
conjunctive six-axis requirement set — still a planner invention — but it binds
through coverage, not through eligibility, so direction B must make *coverage*
requirements advisory to have any effect.

## Overnight 2026-08-18 receipts: the defect is stage-roving and load-shaped

Sampled across the vision-loop session's own turns and two serialized
canary series on runtime `cc478bc88258…` (all ids in the store):

- Recruiter `staff_without_safe_team` (decision "staff", ranked list,
  empty selection): 23:50:24Z, 00:10Z, 00:32Z, 01:32Z — four draws.
- Planner `provider_no_valid_response`: 00:03Z, 00:47Z, 02:11Z (`aa12fb29`),
  02:47Z (`a7999a88`), ~04:30Z (series 2 run 3) — five draws.
- Planner `provider_response_contract_invalid` double-rejection: 01:12Z.
- Child-stage `native_child_inference_failure` (empty selection, judge
  never answered): 03:50:34Z (`f1cb84be`) — matching the 2026-08-17
  policy-series run 2 shape.
- Against, same window: accepted/applied draws at 01:47:41Z (child judge
  STAFFED a live harness child — `native-child-3507ad14…`), 01:52Z,
  02:15Z, 02:35Z, 02:58:49Z (four-card parent accept, 109 s), 03:06:38Z
  (two-card accept, resumed turn), 03:50:10Z (canary parent accept,
  code-reviewer selected AND loaded, 127.8 s).

Reading: the failure roves across planner, recruiter, and child stages,
interleaved with clean draws minutes apart on identical code — a
provider/load phenomenon, not a runtime or prompt defect; the owner
flagged account-level model-limit pressure the same night. Receipts filed
per the loop brief §7.4; no provider chase attempted. Two consecutive
provider-killed series (02:02Z, 03:40Z) stand; a third at ≥08:05Z decides
`blocked-on-provider`.
