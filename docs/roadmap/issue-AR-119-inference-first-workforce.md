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
- The measured incident gap is reconciled through governed roster and planning
  semantics rather than a scenario route. Audited incident-response contracts
  now cover their actual planning, operations, investigation, and risk-analysis
  responsibilities; read-only plans and reviews may use those declared
  capabilities without gaining mutation authority.
- General plan compilation now removes ungrounded stacks and capabilities,
  separates method capabilities from subject domains, ignores prohibited
  mutation language when classifying requested work, normalizes safe
  topological ordering, and keeps integration, release, accessibility, and
  workforce-governance assurance distinct. A domain accidentally repeated in
  the capability array is removed only when that exact governed domain is
  already declared; every other unknown capability still fails closed.
- Lifecycle ownership, minimum-team composition, disabled-winner disclosure,
  independent assurance, and stackless cross-cutting specialists are enforced
  locally across incident response, language-server indexing, installation,
  observability, accessibility, finance, database analysis, clinical evidence,
  legal review, brand, and playful-design boundaries. An applied inference
  plan remains truthfully recorded as inferred when deterministic staffing
  subsequently makes an allowed fail-closed abstention.
- Before corpus expansion, the global cold selection budget was predeclared as
  15000 ms. That value covers valid observed configured-provider calls and was
  not adjusted per case; the one-call fast budget remains unchanged.

Current focused evidence on Windows:

```text
257 compact-intent, inference, staffing, matched-selection, selection-safety,
upstream-architecture, CLI, contract, and bundled-roster cases passed
targeted compiler and policy regressions passed
focused ruff check and ruff format --check passed during implementation
git diff --check passed
```

Current configured-provider evidence on Windows uses `codex-subscription`,
requested/actual model `gpt-5.6-luna`, low reasoning effort, and one planner
call per Agency arm. Valid bounded runs produced:

```text
active-incident-containment: Agency F1 0.667, upstream F1 0.400,
  Agency latency 11272 ms, Agency forbidden/ineligible/conflict 0/0/0
runtime-routing-integration-failure: Agency F1 0.857, upstream F1 0.571,
  Agency latency 10524.381 ms, Agency forbidden/ineligible/conflict 0/0/0
lsp-incremental-index: Agency F1 1.000, upstream F1 0.857,
  Agency latency 14041.717 ms, Agency forbidden/ineligible/conflict 0/0/0
postgres-write-query-analysis: Agency F1 1.000, upstream F1 1.000,
  Agency latency 5469.497 ms, Agency forbidden/ineligible/conflict 0/0/0
clinical-legal-boundary-review: Agency F1 1.000, upstream F1 1.000,
  Agency latency 8519.167 ms, Agency forbidden/ineligible/conflict 0/0/0
disabled-lsp-winner: valid safe abstention on both arms, required disabled
  shadow disclosed, Agency latency 7938.386 ms, no unsafe substitute
```

Additional bounded runs produced exact Agency teams for incidental-finance,
composition, and broad Python/TypeScript application cases. The broad case's
Agency arm selected the exact nine helpful workers at 11212.181 ms after the
compiler normalization, but its paired upstream response was malformed, so the
benchmark remained invalid rather than manufacturing comparative lift. Other
observed invalid runs included upstream timeouts or malformed assignment and
disabled-shadow rows and, before the final normalization, an Agency planner
placing `accessibility` in both domain and capability dimensions. Malformed or
timed-out arms remain invalid. The full 19-case corpus was deliberately not
started after context telemetry crossed the mandatory handoff threshold.

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
lifecycle work. From this recovery commit, rerun a small boundary subset if
needed and then execute all 19 matched scenarios with the unchanged 15000 ms
cold budget and one-call fast setting. Retain exact provider/model receipts,
parity bindings, per-case Agency selections, safety counts, and every malformed
or timed-out arm. Fix any remaining unsafe or clearly inferior Agency result
through governed general semantics; do not weaken typed coverage, add a
scenario route, reinterpret a malformed arm as evidence, or tune latency after
seeing the corpus. A valid full corpus is the next gate. Do not claim Agency is
better: untouched-corpus statistics, exact activation, and blinded completed-
outcome trials remain explicitly deferred release gates.

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
