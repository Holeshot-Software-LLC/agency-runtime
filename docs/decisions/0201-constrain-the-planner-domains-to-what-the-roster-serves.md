---
title: "Constrain the planner's domains to what the roster serves under the unit's authority"
status: accepted
category: decisions
created: 2026-09-03
updated: 2026-09-03
tags: [workforce, planner, staffing, recruiter, roster, inference]
related:
  - docs/roadmap/issue-AR-384-staff-decisions-die-on-uncoverable-typed-requirements.md
  - docs/roadmap/issue-AR-386-strict-critic-vetoes-verifier-accepted-install-turns.md
  - docs/roadmap/issue-AR-374-host-capability-vocabulary-gap.md
  - docs/roadmap/issue-AR-383-inferred-subject-context-fails-its-own-projection.md
  - docs/decisions/0198-waive-the-typed-requirements-the-roster-declares-but-cannot-serve.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0201
type: decision
deciders: [owner]
---

# ADR-0201: Constrain the planner's domains to what the roster serves under the unit's authority

## Status

**Accepted 2026-09-03.** Item 1 of the AR-383 capsule's next package: AR-384's
option 2 in the bounded form the eleven-turn measurement justified. ADR-0198
chose option 1 and recorded option 2 as not chosen; this record adopts the
part of it that option 1 provably cannot reach, and leaves the rest recorded
below as not done.

## Context

ADR-0198 waives the typed requirements the roster declares but cannot serve
for a unit, and after it the install path completed on two of eleven fresh
wordings under strict mode. Every remaining recruiter-side loss traced to one
token, `domain:platform`: three `staff_without_safe_team` rejections on the
`domain` axis (turns 202, 205 and 207 of the AR-384 measurement) and the
wrong-neighbour vetoes in which `api-platform-engineer` was selected on an
install plan (turns 205 and 208 of the AR-386 measurement). The captured
plans show why. The planner names `platform` and `desktop` to say *this
machine*: `[desktop, platform]` on plan units in turns 201, 203 and 206,
`[platform]` alone in turn 208, `[platform, operations]` in 202 and 205.

Two facts about the roster made those names fatal.

1. **`platform` was a homonym inside the roster as well.** The contract
   projector promoted two upstream categories to the one domain: `infrastructure`
   (three modify-authority cards: `devops-automator`, `infrastructure-maintainer`,
   `network-engineer`) and `platform-engineering` (one plan-authority card,
   `api-platform-engineer`, whose work is API gateways, versioning and SDK
   compatibility). Under plan authority `platform` was therefore served by
   exactly one contract, the API card. ADR-0198 waives only tokens *no*
   eligible contract covers, so the token stayed mandatory, the conjunctive
   sufficiency rule demanded the API card on every plan-authority install unit
   that named `platform`, the recruiter was rejected for leaving it out and the
   critic vetoed the team when the repair put it in.
2. **The planner saw the vocabulary, not what is staffable.** `planning_taxonomy`
   carried the union of every declared domain and nothing about which of them
   any worker can be staffed on under a unit's authority. Eligibility needs at
   least one shared domain, so a plan unit naming only `desktop` and `platform`
   had no eligible worker at all before the recruiter spoke, and the recruiter's
   only honest answers were a wrong neighbour or a hiring gap for a specialty
   the roster has under another authority.

On the installed 291-contract roster, plan authority serves 24 of the 30
declared domains; `desktop`, `cms`, `codebase-discovery`, `customer-operations`,
`frontend` and `machine-learning` are unserved under it, and `platform` joins
them once the API card leaves the domain. The per-kind served view costs 13 ms
to compute over the whole roster.

## Decision

1. **`platform` means infrastructure.** `platform-engineering` is no longer
   promoted to `platform` in `_CATEGORY_DOMAINS`; `api-platform-engineer`
   keeps `software-engineering` and `backend`, which `api-design` already gave
   it. A plan-authority unit naming `platform` now has no eligible coverer, so
   ADR-0198 waives the token and records it instead of forcing the API card.
   An installed store receives the change through the packaged-contract
   reconciliation that `agency install` runs: one re-projection of 280
   inspected contracts.
2. **The planner sees the served view.** `planning_taxonomy.domains_by_artifact_kind`
   lists, for each artifact kind, the known domains on which some enabled
   worker passes the verifier's own eligibility for a probe unit of that kind
   on this host: authority with its read-only special cases, host, platform,
   the tools the kind derives, enablement and contract binding. The probe names
   no domain, stack or capability, so those axes never narrow it, and a worker
   that passes contributes every domain it declares. The planner system prompt
   states the rule and the homonym: `host_context.platform` already says where
   the work runs, a domain names the specialist who owns the work, and an
   installation or setup plan is operations work.
3. **A unit none of whose domains is served is rejected for planner repair.**
   `plan_policy_violations` emits `plan_unit_domains_unserved` when no domain
   of a unit appears in the served list for its artifact kind, and the
   existing planner repair loop carries guidance naming the served view. The
   rule is the weak form on purpose: one served domain suffices, because
   ADR-0198 waives and records the rest, and the captured helix shape
   (`desktop` beside `operations` on a plan unit) stays the accepted path.
   Three exemptions keep it honest. A kind whose served list is empty proves
   nothing, not that nothing is possible, and defers to the staffing gate
   exactly as AR-374's tools rule does. A unit whose domains are all chosen by
   the compiler itself (`quality-assurance` on test artifacts, the `security`,
   `software-engineering` and `workforce-governance` aliases) is never the
   planner's fault. A unit naming a domain outside the known vocabulary is a
   declared `novel_capability` unit, the open-ended pool's way to reach the
   recruiter and declare a hiring gap, and replanning it would take that gap
   away. The rule is topology-independent: an explicit indivisible unit is
   held to it.

Not done, by design: renaming the `platform` domain (under modify authority
its three infrastructure cards are the right neighbours for an install, and
turn 209 was accepted on them); the strong form of the rule, which would
erase ADR-0198's advisory gaps and the hiring signal they carry; a prose
glossary of domain meanings for the planner; and enriching `operations` onto
implementers, which is roster work.

## Consequences

- Offline replay of the eleven captured planner replies against the
  reconciled roster: turns 201, 203, 206 and 208 are now rejected for planner
  repair on exactly the plan unit that named only the machine; the other
  seven compile unchanged because their plan units carry `operations`.
- `api-platform-engineer` is no longer eligible for a plan unit whose domains
  lie within `platform`, `desktop` and `operations`, so it cannot be forced
  onto an install plan or selected there. The recruiter index shrinks by the
  eleven bytes of its `platform` token; the size pin records why.
- One planner repair call is spent when the first plan is unserved. Under
  `workforce.mode: strict` the budget is five calls, and the subject stage,
  the planner, the recruiter, one recruiter repair and the critic already use
  all five, so a turn that needs both a planner repair and a recruiter repair
  ends `workforce_call_budget_exhausted` before the critic. The served view in
  the prompt exists to make the first plan right; the repair rate is measured
  live and recorded in the issue. `strict_call_budget` is operator
  configuration.
- The planner prompt grows by one list per artifact kind. The planner cache
  identity includes the prompt, so a roster change that alters the served
  view is a cache miss, as it should be; the subject stage's vocabulary is
  unchanged and still caches.
- The `desktop` homonym survives under modify authority: a plan to install
  command-line tools staffed on the desktop-application implementer (turn
  305) is served by the letter and remains a matter for the recruiter's
  judgment and the critic. `operations` is served by no modify-authority
  card, so an implementation unit naming it carries a waived
  `roster_coverage_gap`, unchanged from ADR-0198.

## Alternatives

- **The strong rule: every domain must be served.** Rejected. It would reject
  the accepted helix shape, spend a repair on every waived token, and remove
  the `roster_coverage_gap` advisories that tell hiring a specialty is
  missing under this authority.
- **Rename `platform` to `infrastructure`.** Removes the collision with
  `host_context.platform` but not the lone plan-authority coverer, and touches
  receipts, evidence and every test that spells the domain. Deferred; the
  vocabulary fix above is the part the measurement needed.
- **Teach the planner the roster's meaning of `platform` in prose only.**
  Non-deterministic, and the API card would have stayed the served coverer,
  so ADR-0198 would have kept the token mandatory.
- **Key the served view by authority instead of artifact kind.** The planner
  authors `artifact_kind` and never `authority`; keying by what it writes
  keeps the repair guidance actionable, as AR-374 did for tools.
- **Substitute a served domain at compile time.** The compiler cannot know
  which specialist owns the work, and ADR-0118 leaves planning to inference.
