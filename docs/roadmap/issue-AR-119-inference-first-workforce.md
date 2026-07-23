---
title: "AR-119: Implement inference-first real-time workforce and contractor lifecycle"
status: in_progress
category: roadmap
created: 2026-07-21
updated: 2026-07-22
tags: [routing, workforce, contractors, delegation, participation, evaluation, performance]
related:
  - docs/decisions/0080-plan-before-recruiting-from-the-whole-workforce.md
  - docs/decisions/0081-compile-contractors-from-governed-structured-contracts.md
  - docs/decisions/0082-schedule-assurance-by-artifact-lifecycle.md
  - docs/decisions/0083-use-capability-indexed-recall-and-bounded-inference.md
supersedes: []
superseded_by: null
type: issue
epic: routing
issue_id: AR-119
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
depends_on: [AR-115, AR-116, AR-118]
blocks: []
---

# AR-119: Implement inference-first real-time workforce and contractor lifecycle

## Problem

Agency can route audited specialists, but it does not yet prove that every new
intent and every native work unit is performed with the best compatible
specialist rather than an untyped generic worker. Recruitment metadata, typed
planning, exact-version activation, native delegation, contractor hiring,
latency, and outcome evidence are not yet one coherent system. Complete
one-shot applications are an important downstream stress test, but they are not
the primary definition of Agency success.

## Current state

The audited roster, turn-scoped activation, resident managers, native-child
receipts, provider evidence, CLI, and dashboard provide a strong base. The
complete contract and completion gates are authoritative in tracker issue
[#132](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132).
AR-120 through AR-125 divide implementation into independently verifiable
slices without narrowing that umbrella contract.

## Approach

Plan typed work before naming agents; resolve the required controlled
capabilities against an immutable versioned projection of the entire workforce;
verify staffing deterministically; and give the native host exact specialist
recipes without replacing its scheduler. A high-margin complete local result
needs no recruiter call. Balanced and strict modes may ask inference to resolve
an ambiguous bounded shortlist, but the model cannot nominate outside the
runtime-supplied cards or override eligibility and composition policy. Every
accepted Agency work unit must prove that the performing parent or child
consumed its exact-version activation receipt. Parent plans are reused by
children so native fan-out does not multiply inference calls.

Treat routing speed as a product contract: the common path uses one compact
intent-planning call followed by local whole-roster recall, warm continuations
reuse cache entries bound to every input and policy version, and child
activation uses no inference for already-planned work. Candidate and recruiter
caches use the same complete identity discipline. Measure Agency-on overhead
separately from host execution and fail the release gate when the configured
latency budget is exceeded. Subscription-backed Codex inference exposes the
account-visible model and its supported reasoning effort in both CLI and
dashboard configuration, allowing the planner to use a deliberately fast,
bounded setting rather than an accidental host default.

Hire only independently verified gaps. Contractor quarantine is an automated
in-turn admission pipeline, not a mandatory human queue: compile a structured
contract through a fixed prompt template, run duplicate, conflict, prompt
integrity, authority, tool, and independent critic checks, then admit a passing
worker as a least-privileged probationary contractor for the exact causing work
unit. Promotion remains operator-controlled by default. A bad projection for an
existing employee is repaired instead of creating a duplicate contractor.
Before first activation, a contractor must pass the same contract compilation,
capability indexing, audit, version, conflict, eligibility, activation, and
receipt path as an employee. Probation restricts authority and reuse; it never
bypasses workforce governance.

Prove value with paired Agency-on and Agency-off trials using the same ask,
host, model, configuration, and evaluator. An Agency-on trial without accepted
specialist activation evidence is invalid participation evidence, regardless of
the delivered artifact. Product-level one-shot trials remain downstream tests
of whether better participation translates into complete applications.

Pin the source-visible upstream Agency Agents revision and run a held-out
matched comparison corpus. Inference is a defining mechanism, but release
claims require measured improvement over that baseline in useful specialist
precision and recall, typed coverage, conflict safety, activation completion,
latency, and independently graded outcomes. Merely making an inference call is
not evidence that Agency is better.

## Dependencies

AR-115 establishes trustworthy live selection, AR-116 bounds native-child
routing and provider choice, and AR-118 reconciles activation evidence.

## Execution checkpoint

### Proven locally in the current slice

- All four supported native hosts receive host-correct delegation guidance:
  Codex `spawn_agent`, Claude `Agent`, Hermes `delegate_task`, and OpenClaw
  `sessions_spawn`.
- An isolated route cannot claim an Agency specialist when no exact typed unit
  plan exists. It abstains, preserves diagnostic candidates, and leaves the
  native host free to use an untyped fallback without counting it as Agency
  participation.
- Exact planned agents must be available before an isolated work unit can be
  activated, and legacy receipt replay remains compatible with the stricter
  work-unit schema.
- Parent plans and exact one-use native-child activation paths remain covered
  across Codex, Claude, Hermes, and OpenClaw.
- A matched selection benchmark now executes Agency and the exact pinned
  upstream Agency Agents orchestrator prompt through the same configured
  provider and requested model, with the same request, complete visible roster,
  explicit eligible-worker set, alternating arm order, and one shared scorer.
  The upstream prompt and MIT license are packaged and hash-verified at revision
  `ee5e758c10b412cf905f8984a02c5c016315e1ec`.
- The selection-safety corpus now has 19 labeled scenarios. Every scenario
  declares helpful and forbidden workers and the corpus covers dangerous or
  incompatible choices, disabled semantic winners, weak incidental lexical
  matches, broad multi-agent work, typed context conflicts, and latency.
- Malformed responses, provider/model mismatches, unavailable model receipts,
  non-inferred arms, and unequal call counts invalidate the comparison instead
  of creating artificial Agency lift. The report always keeps superiority and
  release-claim eligibility false for this bounded selection-only evidence.
- A live canary exposed and fixed one general compact-plan compiler defect:
  model outcomes may contain 512 characters, while locally derived acceptance
  evidence is bounded to 128. Evidence is now artifact-specific and bounded
  without using scenario-specific exceptions.

Current focused evidence on Windows:

```text
5 new cross-host and abstention cases passed
82 unit-aware delegation, native-child hook, and child-routing cases passed
55 matched-selection, compact-intent, selection-safety, upstream-architecture,
and CLI contract cases passed
ruff check passed for the touched routing slice
ruff format --check passed for the touched routing slice
git diff --check passed
```

Current configured-provider canary on Windows, using `codex-subscription` and
requested/actual model `gpt-5.6-luna`:

```text
agency eval upstream-selection --case active-incident-containment ...
benchmark failed truthfully
Agency helpful F1: 0.000
upstream helpful F1: 0.667
Agency forbidden/ineligible/conflict selections: 0/0/0
Agency cold latency: 11459.837 ms (10000 ms predeclared budget)
```

The valid Agency planner receipt produced two security planning units, but
deterministic staffing abstained with `no_safe_sufficient_team` and
`recruiter_abstained`: the planner required `operations`, `investigation`, and
`risk-analysis`, while the audited incident contracts do not currently cover
the complete requirement set. This is the next measured contract/routing gap;
it must not be relabeled as success or hidden by loosening the scorer.

### Still required before AR-119 can close

- Complete and pass the implemented matched held-out selection benchmark
  against the pinned source-visible upstream Agency Agents baseline. Reconcile
  the measured incident contract/planner capability mismatch, rerun its canary,
  then run all 19 scenarios and fix every unsafe or clearly inferior Agency
  result. Dangerous, forbidden, incompatible, disabled, and weak incidental
  matches remain explicit regressions, not aggregate-score noise.
- Complete the whole-roster multi-agent and conflict corpus, contractor
  duplicate/admission/promotion lifecycle, and CLI/dashboard operator flows.
- Prove cold, warm, cache-invalidation, and large native-fan-out latency bounds.
- Run paired Agency-on/off outcome trials with accepted activation evidence.
- Run the full local quality, coverage, documentation, packaging, Windows, and
  Linux matrix; then perform the deferred hosted checks once at the end.
- Create the final PR, merge it, reinstall the merged artifact, and run live
  canaries on Codex, Claude, OpenClaw, and Hermes before closing issue #132.

### Next bounded work package

Continue the matched selection package without advancing to contractor
lifecycle work. First reconcile the measured `active-incident-containment`
capability mismatch through governed, general roster-contract or planning
semantics; do not add a scenario-specific route or weaken required coverage.
Rerun that configured-provider canary until Agency produces a safe sufficient
team within a justified predeclared latency budget. Then execute all 19 matched
scenarios, retain exact provider/model receipts and parity bindings, and fix
every unsafe or clearly inferior Agency selection before advancing. Do not
claim Agency is better unless later untouched-corpus and completed-outcome
evidence satisfies the explicitly deferred release gates.

### Handoff constraints

- Continue on `codex/ar-115-live-routing-trust`; do not reset, discard, or
  silently rewrite the accumulated AR-119 work.
- Keep tracker issue #132 open and do not claim the north-star goal complete.
- Do not push or trigger hosted GitHub Actions during intermediate packages;
  the user requested one consolidated hosted verification near the end.
- After each bounded package, update this checkpoint, create local recovery and
  ledger commits, and apply the autonomous context handoff rule in `AGENTS.md`.

## Acceptance

- [ ] AR-120 through AR-125 are complete and tracker-evidenced.
- [ ] Every new intent is planned or explicitly classified as a continuation, and every Agency-assigned native child consumes the exact specialist recipe and one-use activation receipt.
- [ ] No generic native child is counted as Agency participation; recommendation without activation is rejected as incomplete evidence.
- [ ] Broad intent, ambiguity, adversarial, disabled-worker, conflict, and multi-agent corpora exercise the entire audited workforce rather than a single security-review case.
- [ ] Every employee and contractor has validated capability IDs in the same versioned contract and recruiter index, and bounded recruiter output cannot escape its supplied candidate cards.
- [ ] Parent routing is bounded, cached for continuations, reused by children, and passes explicit cold, warm, and fan-out latency budgets.
- [ ] Plan, candidate, recruiter, and parent-unit caches use complete versioned identities and invalidate on request, host, roster, contract, policy, provider, model, taxonomy, or schema changes as applicable.
- [ ] A genuine roster gap passes automated quarantine and uses a least-privileged probationary contractor in the causing turn; malicious or incoherent candidates are rejected without blocking safe host fallback.
- [ ] Paired Agency-on/off trials prove specialist participation and a better independently graded outcome for the same host and model.
- [ ] A pinned held-out comparison materially beats the source-visible upstream Agency Agents routing baseline without any forbidden or incompatible selection regression.
- [ ] Every completion gate in tracker issue #132 has direct current evidence.
- [ ] The final hosted matrix, installed artifacts, four host contracts, and live canaries pass.
- [ ] The merged and reinstalled artifact is verified before this item closes.
