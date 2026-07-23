---
title: "AR-119: Implement inference-first real-time workforce and contractor lifecycle"
status: in_progress
category: roadmap
created: 2026-07-21
updated: 2026-07-23
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

The successor package ran the complete 19-case corpus twice and then reran only
the failing boundaries. It fixed four general deterministic gaps without
changing the 15000 ms budget or one-call fast mode:

- read-only test-result evidence now remains in the `testing` lifecycle;
- request-grounded PostgreSQL query-performance and runtime-routing evidence can
  disambiguate otherwise generic analysis units without opening broad request
  token leakage;
- a secondary `research` domain remains a method inside a named subject domain,
  while routine software diagnosis no longer gains incident-only
  `investigation` coverage; actual incident signals preserve it; and
- downstream independent assurance binds to every local implementation unit,
  not only to a test unit that may omit a separate cross-cutting implementation.

The second full run used corpus fingerprint
`sha256:7358cb9422cef681dc7d85323160652029792916c2ea74d81514df6cfebbba38`
and roster fingerprint
`sha256:c80b7422124f5935d3956ec48d6d0fffca15e7c23ebd155475998c7418e4f795`.
Every arm recorded provider `codex-subscription`, requested and actual model
`gpt-5.6-luna`, receipt source `cli.explicit_model_argument`, one call, and
applied inference. Aggregate Agency evidence was 16/19 passing, precision
0.911111, recall 0.706897, F1 0.796117, 16/19 complete typed coverage, p50
7771.016 ms, p95/max 14041.516 ms, and zero forbidden, ineligible, or conflict
selections. Upstream was 7/19 passing, precision 0.756098, recall 0.534483, F1
0.626263, 9/19 complete typed coverage, p50 13060.875 ms, p95/max 19081.378 ms,
and zero scored safety selections. The benchmark was invalid because four
upstream arms returned malformed assignment or disabled-shadow contracts.

The exact compact projection follows. `A` and `U` identify Agency and upstream;
`safety=f/i/c` means forbidden/ineligible/conflict counts; `disabled` shows
reported/required shadows; and `missing` groups required workers, artifacts,
and lifecycles. A malformed arm is retained as `error/fail`, never reinterpreted
as a comparative loss.

```text
python-production-change | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=7624.325 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=11055.147 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[python-bug-matched-to-python-application-engineer,failure-path-testing-matched-to-software-test-engineer,independent-review-matched-to-code-reviewer,separate-contexts-for-specialists] | fairness=[]
typescript-production-change | helpful=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=5925 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[typescript-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=14382.854 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[typescript-specialist-selected,testing-complement-selected,independent-review-required,distinct-isolated-contexts] | fairness=[]
backend-service-change | helpful=[backend-service-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[backend-service-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.888889 ms=7333.505 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[backend-architect,backend-service-engineer,software-test-engineer,code-reviewer] f1=0.75 ms=14446.971 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[production-backend-endpoint,integration-test-coverage,independent-code-review,separate-specialist-contexts] | fairness=[]
installed-cross-platform-release | helpful=[software-test-engineer,code-reviewer,cross-platform-release-verifier] | A=abstained/fail selected=[] f1=0 ms=6417.142 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,cross-platform-release-verifier,software-test-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[required_agents_missing,no_safe_sufficient_team,recruiter_abstained] | U=accepted/pass selected=[cross-platform-installer-engineer,software-test-engineer,code-reviewer,cross-platform-release-verifier,application-integration-verifier] f1=0.75 ms=13087.141 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[matched-cross-platform-installation-scope,matched-test-and-review-requirements,matched-independent-installed-release-verification,matched-application-integration-verification] | fairness=[]
application-integration | helpful=[software-test-engineer,code-reviewer,application-integration-verifier] | A=accepted/pass selected=[minimal-change-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.75 ms=6812.271 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=17339.289 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-integration-verifier,code-reviewer,software-test-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream assignment row is invalid] | fairness=[application-integration:arm_error]
application-observability | helpful=[application-observability-engineer,software-test-engineer,code-reviewer] | A=accepted/pass selected=[application-observability-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=0.857143 ms=10116.352 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[application-observability-engineer,software-test-engineer,code-reviewer] f1=1 ms=14493.853 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[exact-observability-implementation-match,explicit-failure-telemetry-scope,explicit-test-requirement,independent-review-required,distinct-contexts-for-specialists] | fairness=[]
documentation-change | helpful=[technical-writer,code-reviewer] | A=accepted/pass selected=[technical-writer,code-reviewer] f1=1 ms=6703.82 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[technical-writer,codebase-archaeologist] f1=0.5 ms=9739.535 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer] rc=[documentation-authority-match,independent-technical-accuracy-review,isolated-contexts-preserved] | fairness=[]
selection-safety-review | helpful=[selection-safety-critic] | A=accepted/pass selected=[selection-safety-critic] f1=1 ms=10918.087 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[selection-safety-critic] f1=1 ms=8255.228 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[exact-specialist-match,selection-safety-review,no-disabled-semantic-winner] | fairness=[]
repository-security-patch-review | helpful=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] | A=accepted/pass selected=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] f1=1 ms=6687.622 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[codebase-onboarding-engineer,code-reviewer,application-security-engineer] f1=0.666667 ms=13060.875 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:ai-generated-code-security-auditor] rc=[security-code-review-request,read-only-review-scope,independent-specialist-contexts,no-disabled-semantic-winner] | fairness=[]
runtime-routing-integration-failure | helpful=[application-integration-verifier,selection-safety-critic,test-results-analyzer] | A=abstained/fail selected=[] f1=0 ms=9146.914 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-integration-verifier,selection-safety-critic,test-results-analyzer;art:review-report,test-evidence;life:review,testing] rc=[selection_confidence_too_low,selection_margin_too_low] | U=error/fail selected=[] f1=0 ms=15966.046 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-integration-verifier,selection-safety-critic,test-results-analyzer;art:review-report,test-evidence;life:review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[runtime-routing-integration-failure:arm_error]
active-incident-containment | helpful=[incident-responder,incident-response-commander] | A=accepted/pass selected=[incident-responder] f1=0.666667 ms=7771.016 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[incident-responder,secrets-credential-hygiene-engineer,threat-detection-engineer,data-privacy-officer] f1=0.333333 ms=11958.244 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:analysis;life:discovery] rc=[active-incident-requires-defensive-incident-response,preserve-forensic-evidence-before-eradication,credential-specific-revocation-and-rotation-needed,reversible-recovery-and-rollback-required,offensive-probing-excluded-by-request] | fairness=[]
lsp-incremental-index | helpful=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=9542.7 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=14499.449 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,lsp-index-engineer,software-test-engineer,test-results-analyzer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[lsp-incremental-index:arm_error]
disabled-lsp-winner | helpful=[lsp-index-engineer] | A=abstained/pass selected=[] f1=0 ms=8329.327 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[no_safe_sufficient_team,recruiter_abstained,selection_margin_too_low] | U=accepted/pass selected=[codebase-archaeologist,software-test-engineer] f1=0 ms=12528.449 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[best-semantic-match-disabled,use-independent-read-only-diagnosis,separate-specialist-contexts,safest-next-step-is-reproduce-and-preserve-failure-before-changing-index-state] | fairness=[]
incidental-finance-language | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=8674.915 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=11249.357 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[bounded-python-implementation,failure-path-testing-required,independent-review-required,financial-analysis-explicitly-out-of-scope,separate-contexts-for-specialists] | fairness=[]
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=abstained/fail selected=[] f1=0 ms=14041.516 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor,application-integration-verifier,application-observability-engineer,code-reviewer,cross-platform-release-verifier,python-application-engineer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[independent_assurance_missing] | U=error/fail selected=[] f1=0 ms=19081.378 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor,application-integration-verifier,application-observability-engineer,code-reviewer,cross-platform-release-verifier,python-application-engineer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[broad-python-typescript-application:arm_error]
brand-and-whimsy-separated | helpful=[brand-guardian,whimsy-injector,accessibility-auditor] | A=accepted/pass selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=8465.469 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=16462.402 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:review-report;life:review] rc=[brand-governance-routed-to-brand-guardian,playful-details-routed-to-whimsy-injector,independent-accessibility-audit-routed-to-accessibility-auditor,separate-contexts-enforced,whimsy-accessibility-dependency-satisfied] | fairness=[]
accounts-payable-cfo-separated | helpful=[accounts-payable-agent,chief-financial-officer] | A=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=7954.985 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=7510.741 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[exact-agent-match,segregation-of-duties,separate-context-required,enabled-and-eligible] | fairness=[]
postgres-write-query-analysis | helpful=[database-optimizer] | A=accepted/pass selected=[database-optimizer] f1=1 ms=5982.156 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[database-optimizer] f1=1 ms=8435.034 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[best-fit-database-query-plan-analysis,read-only-measured-findings,no-documentation-or-code-change-required] | fairness=[]
clinical-legal-boundary-review | helpful=[clinical-evidence-agent,legal-document-review] | A=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=7361.917 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=9783.745 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[clinical-evidence-agent-selected-for-source-grounded-clinical-evidence-summary,legal-document-review-selected-for-independent-review-of-legal-document-use,separate-contexts-required-for-independent-specialist-reviews] | fairness=[]
```

The three Agency failures in that full run were fail-closed planner-shape or
assurance outcomes, not unsafe substitutions. After the general fixes above, a
matched bounded rerun passed all three Agency arms with zero safety violations:

```text
installed-cross-platform-release: selected cross-platform-installer-engineer,
  software-test-engineer, code-reviewer, test-results-analyzer, and
  cross-platform-release-verifier; F1 0.750000; 5538.265 ms
runtime-routing-integration-failure: selected codebase-onboarding-engineer,
  application-integration-verifier, test-results-analyzer, and
  selection-safety-critic; F1 0.857143; 10834.705 ms
broad-python-typescript-application: selected the exact nine helpful workers;
  F1 1.000000; 14758.804 ms
```

That bounded benchmark was still invalid because the runtime upstream arm
returned `provider_response_contract_invalid` with an unknown disabled shadow.
No superiority claim is made. A new complete 19-case run from this recovery
checkpoint is required to determine whether every Agency arm now passes in one
corpus and whether provider-arm validity remains the only blocker.

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
lifecycle work. Start with one complete 19-case run from this recovery commit,
using the unchanged 15000 ms cold budget and one-call fast setting. Retain exact
provider/model receipts, parity bindings, per-case selections, safety counts,
disabled disclosures, reason codes, and every malformed or timed-out arm. If an
Agency arm fails, use only bounded case reruns and governed general semantics
before another complete run; do not weaken typed coverage, add a scenario
route, reinterpret a malformed arm as evidence, or tune latency after seeing
the corpus. If every Agency arm is safe and passing but the benchmark is
invalid only because upstream provider arms are malformed or timed out, record
that exact blocker instead of weakening the parser or fairness gates. Do not
claim Agency is better: untouched-corpus statistics, exact activation, and
blinded completed-outcome trials remain explicitly deferred release gates.

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
