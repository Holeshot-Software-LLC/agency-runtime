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

The receiving package ran the required complete corpus with the unchanged
command, 15000 ms cold gate, and one-call fast budget:

```text
.\.venv\Scripts\agency.exe eval upstream-selection --all --platform windows --confirm-live-inference "RUN MATCHED UPSTREAM SELECTION EVAL" --json
```

The process completed in 405.9 seconds with no stderr. It returned exit status
1 because the benchmark was not valid and not every Agency case passed; the
malformed arm was preserved as an error rather than scored as an upstream
loss. The corpus fingerprint remained
`sha256:7358cb9422cef681dc7d85323160652029792916c2ea74d81514df6cfebbba38`,
the roster fingerprint remained
`sha256:c80b7422124f5935d3956ec48d6d0fffca15e7c23ebd155475998c7418e4f795`,
and the allowed-agent fingerprint was
`sha256:88d310bad3716357bf49a74c53a873236cf9c549b878c3c190b4affebead7765`.
Every arm again recorded provider `codex-subscription`, requested and actual
model `gpt-5.6-luna`, receipt source `cli.explicit_model_argument`, one call,
and applied inference.

Aggregate Agency evidence was 17/19 passing, precision 0.887097, recall
0.948276, F1 0.916667, 18/19 complete typed coverage, p50 8823.892 ms,
p95/max 18068.738 ms, and zero forbidden, ineligible, or conflict selections.
Upstream was 6/19 passing, precision 0.683333, recall 0.706897, F1 0.694915,
10/19 complete typed coverage, p50 11600.629 ms, p95/max 21919.303 ms, and
zero scored safety selections. The comparison was invalid because the
TypeScript upstream arm returned an unknown disabled shadow. Agency also had
two non-safety failures: active incident response abstained on selection
margin, and the exact LSP team exceeded the unchanged latency gate.

The exact compact projection follows with the same notation as the preceding
complete run:

```text
python-production-change | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=9755.918 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=11600.629 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[python-implementation-required,failure-path-testing-required,independent-review-required,distinct-specialist-contexts] | fairness=[]
typescript-production-change | helpful=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=7738.165 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=12683.191 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[typescript-production-change:arm_error]
backend-service-change | helpful=[backend-service-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[backend-service-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.888889 ms=10192.612 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[backend-service-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=10183.961 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[production-backend-implementation,integration-test-coverage,independent-code-review] | fairness=[]
installed-cross-platform-release | helpful=[software-test-engineer,code-reviewer,cross-platform-release-verifier] | A=accepted/pass selected=[cross-platform-installer-engineer,software-test-engineer,code-reviewer,test-results-analyzer,cross-platform-release-verifier] f1=0.75 ms=6324.213 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[agents-orchestrator,cross-platform-installer-engineer,software-test-engineer,cross-platform-release-verifier,application-integration-verifier,code-reviewer] f1=0.666667 ms=16005.143 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[matched-cross-platform-installation-scope,matched-installed-artifact-verification-scope,matched-testing-and-review-requirements,separate-contexts-for-specialists,selected-only-allowed-agent-ids] | fairness=[]
application-integration | helpful=[software-test-engineer,code-reviewer,application-integration-verifier] | A=accepted/pass selected=[minimal-change-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.75 ms=6626.439 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[backend-service-engineer,software-test-engineer,application-integration-verifier] f1=0.666667 ms=11419.098 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer;art:review-report] rc=[implementation-testing-and-independent-verification-required,specialists-separated-into-distinct-contexts,all-selected-agent-ids-are-allowed-and-eligible,no-disabled-semantic-winner-present] | fairness=[]
application-observability | helpful=[application-observability-engineer,software-test-engineer,code-reviewer] | A=accepted/pass selected=[application-observability-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=0.857143 ms=9285.387 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[application-observability-engineer,software-test-engineer,code-reviewer] f1=1 ms=9787.391 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[request-explicitly-requires-production-observability,request-explicitly-requires-failure-telemetry,request-explicitly-requires-tests,request-explicitly-requires-independent-review] | fairness=[]
documentation-change | helpful=[technical-writer,code-reviewer] | A=accepted/pass selected=[technical-writer,code-reviewer] f1=1 ms=6721.226 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[technical-writer,code-reviewer] f1=1 ms=11712.096 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[documentation-rewrite-matched-to-technical-writer,independent-technical-review-matched-to-code-reviewer,separate-contexts-preserve-review-independence] | fairness=[]
selection-safety-review | helpful=[selection-safety-critic] | A=accepted/pass selected=[selection-safety-critic] f1=1 ms=5631.764 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[agents-orchestrator,selection-safety-critic] f1=0.666667 ms=10507.585 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[selection-plan-not-explicitly-supplied,use-independent-selection-safety-review,resident-coordination-required] | fairness=[]
repository-security-patch-review | helpful=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] | A=accepted/pass selected=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] f1=1 ms=8823.892 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[codebase-archaeologist,code-reviewer,application-security-engineer] f1=0.333333 ms=11636.711 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:ai-generated-code-security-auditor,codebase-onboarding-engineer] rc=[matched-specialists-to-code-path-correctness-and-exploitability,all-selected-agent-ids-are-allowed-and-enabled,separate-contexts-preserve-independent-reviews,no-file-change-authority-required] | fairness=[]
runtime-routing-integration-failure | helpful=[application-integration-verifier,selection-safety-critic,test-results-analyzer] | A=accepted/pass selected=[codebase-onboarding-engineer,application-integration-verifier,test-results-analyzer,selection-safety-critic] f1=0.857143 ms=10889.201 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[agents-orchestrator,multi-agent-systems-architect,codebase-archaeologist,application-integration-verifier,selection-safety-critic] f1=0.5 ms=13739.649 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer] rc=[exact-agent-id-enforcement,distinct-specialist-contexts,routing-forensics,live-integration-validation,independent-staffing-audit] | fairness=[]
active-incident-containment | helpful=[incident-responder,incident-response-commander] | A=abstained/fail selected=[] f1=0 ms=11840.03 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:incident-responder;art:analysis,plan;life:discovery,planning] rc=[selection_margin_too_low] | U=accepted/fail selected=[incident-response-commander,incident-responder,secrets-credential-hygiene-engineer,threat-detection-engineer] f1=0.666667 ms=15092.892 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[active-security-incident,credential-theft-response,forensic-evidence-preservation,reversible-recovery,defensive-only-no-offensive-probing] | fairness=[]
lsp-incremental-index | helpful=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/fail selected=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=18068.738 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[lsp-index-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=9195.203 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[exact-agent-id-match,lsp-specialization-for-indexing,failure-path-test-coverage,independent-code-review,distinct-specialist-contexts] | fairness=[]
disabled-lsp-winner | helpful=[lsp-index-engineer] | A=abstained/pass selected=[] f1=0 ms=9816.041 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[selection_margin_too_low,selection_confidence_too_low] | U=accepted/pass selected=[codebase-archaeologist,test-automation-engineer] f1=0 ms=12686.964 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[best-semantic-specialist-disabled,use-evidence-grounded-codebase-diagnosis,add-reproducible-regression-tests,keep-specialists-in-distinct-isolated-contexts] | fairness=[]
incidental-finance-language | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=8685.038 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=11101.066 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[python-implementation-fit,failure-path-testing-required,independent-review-required,financial-analysis-explicitly-excluded] | fairness=[]
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=accepted/pass selected=[application-observability-engineer,python-application-engineer,typescript-application-engineer,software-test-engineer,accessibility-auditor,code-reviewer,application-integration-verifier,test-results-analyzer,cross-platform-release-verifier] f1=1 ms=10774.263 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[product-manager,software-architect,backend-service-engineer,frontend-developer,software-test-engineer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-installer-engineer,cross-platform-release-verifier] f1=0.526316 ms=21919.303 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,python-application-engineer,test-results-analyzer,typescript-application-engineer;art:review-report] rc=[production-python-api,typescript-dashboard,failure-path-testing,accessibility-review,observability,independent-integration-verification,windows-linux-release-evidence,separate-specialist-contexts] | fairness=[]
brand-and-whimsy-separated | helpful=[brand-guardian,whimsy-injector,accessibility-auditor] | A=accepted/pass selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=10991.567 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=11743.04 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:review-report;life:review] rc=[brand-governance-matched-to-brand-guardian,playful-details-matched-to-whimsy-injector,independent-accessibility-audit-required,separate-isolated-work-units,all-selected-agent-ids-allowed] | fairness=[]
accounts-payable-cfo-separated | helpful=[accounts-payable-agent,chief-financial-officer] | A=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=8492.108 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=8776.816 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:review-report] rc=[domain-fit-accounts-payable-exceptions,independent-cfo-review-requested,separate-contexts-enforced,all-selected-agents-allowed-and-enabled] | fairness=[]
postgres-write-query-analysis | helpful=[database-optimizer] | A=accepted/pass selected=[database-optimizer] f1=1 ms=4808.838 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[database-optimizer] f1=1 ms=8863.894 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[exact-domain-fit,analysis-only,no-documentation,no-application-code-change,measured-query-plan-evidence] | fairness=[]
clinical-legal-boundary-review | helpful=[clinical-evidence-agent,legal-document-review] | A=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=7748.636 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=11454.46 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[clinical-evidence-specialist-selected,legal-document-review-specialist-selected,independent-context-isolation-applied,no-diagnosis-requested,no-medical-billing-requested,no-compliance-certification-requested] | fairness=[]
```

The bounded follow-up showed model-shape and latency variance rather than a
stable deterministic defect. In a two-case matched rerun,
`active-incident-containment` recovered with `incident-responder`, F1 0.666667,
7348.709 ms, complete coverage, and zero safety violations. The same command's
LSP arm abstained in 8190.092 ms with
`lifecycle_owner_missing_from_required`. A subsequent instrumented one-call
diagnostic produced a valid four-unit plan and exact LSP team with a recorded
11002 ms provider latency. The next matched LSP-only rerun then passed with
`lsp-index-engineer`, `software-test-engineer`, `code-reviewer`, and
`test-results-analyzer`, F1 1.000000, 8028.102 ms, complete coverage, zero
safety violations, and a valid matched benchmark. No product or policy code
was changed because neither full-run Agency failure repeated consistently and
there was no governed general semantic defect to justify weakening or tuning
the deterministic contract.

At that checkpoint, another complete corpus remained required. That complete
run could not establish that every Agency arm passed together, and the
TypeScript upstream provider-contract failure prevented comparative
interpretation in all cases.

The next recovery package ran the required complete corpus again with the same
command, unchanged 15000 ms cold gate, and unchanged one-call fast budget. The
first process result exceeded the calling tool's transient output envelope and
was deliberately excluded because its complete JSON was not recoverable. The
immediately repeated command captured stdout and stderr separately outside the
repository. It completed in 426.748 seconds, emitted no stderr, produced a
complete machine-readable report, and returned exit status 1 because three
Agency cases failed and two upstream arms were invalid.

The complete report retained corpus fingerprint
`sha256:7358cb9422cef681dc7d85323160652029792916c2ea74d81514df6cfebbba38`,
roster fingerprint
`sha256:c80b7422124f5935d3956ec48d6d0fffca15e7c23ebd155475998c7418e4f795`,
and allowed-agent fingerprint
`sha256:88d310bad3716357bf49a74c53a873236cf9c549b878c3c190b4affebead7765`.
Every arm recorded provider `codex-subscription`, requested and actual model
`gpt-5.6-luna`, receipt source `cli.explicit_model_argument`, one call,
applied inference, and the unchanged 15000 ms latency budget.

Aggregate Agency evidence was 16/19 passing, precision 0.879310, recall
0.879310, F1 0.879310, 17/19 complete typed coverage, p50 8137.664 ms,
p95/max 12490.811 ms, and zero forbidden, ineligible, or conflict selections.
Upstream was 5/19 passing, precision 0.760870, recall 0.603448, F1 0.673077,
8/19 complete typed coverage, p50 12226.497 ms, p95/max 23117.197 ms, and zero
scored safety selections. The benchmark was invalid because the TypeScript
upstream arm returned an invalid assignment row and the broad application
upstream arm returned an unknown disabled shadow. Neither malformed arm is
interpreted as an upstream loss.

The three Agency failures were fail-closed or incomplete-team outcomes, not
unsafe substitutions: `selection-safety-review` abstained on confidence and
margin; `broad-python-typescript-application` omitted
`accessibility-auditor`; and `brand-and-whimsy-separated` abstained on
independent assurance. The exact compact projection follows:

```text
python-production-change | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=6939.257 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=12138.394 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[python-application-engineer-is-the-best-fit-for-python-application-implementation,software-test-engineer-is-the-best-fit-for-failure-path-test-code,code-reviewer-provides-an-independent-review,separate-isolated-contexts-used-for-each-specialist] | fairness=[]
typescript-production-change | helpful=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=8791.921 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=19853.079 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream assignment row is invalid] | fairness=[typescript-production-change:arm_error]
backend-service-change | helpful=[backend-service-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[backend-service-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.888889 ms=7171.835 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[backend-service-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=15806.277 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[production-backend-endpoint-requires-service-implementation,integration-tests-require-independent-test-specialist,code-review-requires-independent-reviewer,separate-contexts-preserved-for-specialists] | fairness=[]
installed-cross-platform-release | helpful=[software-test-engineer,code-reviewer,cross-platform-release-verifier] | A=accepted/pass selected=[cross-platform-installer-engineer,software-test-engineer,code-reviewer,test-results-analyzer,cross-platform-release-verifier] f1=0.75 ms=6358.147 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[cross-platform-installer-engineer,software-test-engineer,application-integration-verifier,cross-platform-release-verifier,code-reviewer] f1=0.75 ms=15606.375 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[matched-cross-platform-installer-specialist,matched-test-implementation-specialist,matched-installed-app-integration-verifier,matched-cross-platform-release-verifier,matched-independent-code-reviewer,separate-isolated-contexts-for-specialists] | fairness=[]
application-integration | helpful=[software-test-engineer,code-reviewer,application-integration-verifier] | A=accepted/pass selected=[minimal-change-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.75 ms=6913.898 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[backend-service-engineer,software-test-engineer,application-integration-verifier] f1=0.666667 ms=17081.105 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer;art:review-report] rc=[bounded-implementation-agent-selected-for-app-integration,dedicated-test-agent-selected-for-test-code,independent-integration-verifier-selected-for-complete-running-application,distinct-contexts-preserved-for-specialists] | fairness=[]
application-observability | helpful=[application-observability-engineer,software-test-engineer,code-reviewer] | A=accepted/pass selected=[application-observability-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=0.857143 ms=10843.954 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[application-observability-engineer,software-test-engineer,application-integration-verifier] f1=0.666667 ms=15431.67 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer;art:review-report] rc=[implementation-specialist-selected-for-production-observability,failure-path-test-specialist-selected,independent-integration-review-selected,separate-contexts-preserved] | fairness=[]
documentation-change | helpful=[technical-writer,code-reviewer] | A=accepted/pass selected=[technical-writer,code-reviewer] f1=1 ms=7180.192 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[technical-writer,codebase-archaeologist] f1=0.5 ms=10959.507 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer;art:documentation] rc=[documentation-rewrite-matched-to-technical-writer,independent-accuracy-review-matched-to-codebase-archaeologist,separate-contexts-preserve-review-independence] | fairness=[]
selection-safety-review | helpful=[selection-safety-critic] | A=abstained/fail selected=[] f1=0 ms=6710.165 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:selection-safety-critic;art:review-report;life:review] rc=[selection_confidence_too_low,selection_margin_too_low] | U=accepted/pass selected=[selection-safety-critic] f1=1 ms=7541.658 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[selection-safety-critic-is-exact-fit,request-is-selection-composition-audit,no-disabled-semantic-winner-identified] | fairness=[]
repository-security-patch-review | helpful=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] | A=accepted/pass selected=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] f1=1 ms=7688.927 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[codebase-onboarding-engineer,code-reviewer,application-security-engineer] f1=0.666667 ms=12226.497 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:ai-generated-code-security-auditor] rc=[read-only-review,separate-specialist-contexts,independent-correctness-and-security-reviews] | fairness=[]
runtime-routing-integration-failure | helpful=[application-integration-verifier,selection-safety-critic,test-results-analyzer] | A=accepted/pass selected=[codebase-onboarding-engineer,application-integration-verifier,test-results-analyzer,selection-safety-critic] f1=0.857143 ms=12490.811 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[agents-orchestrator,multi-agent-systems-architect,application-integration-verifier,selection-safety-critic] f1=0.571429 ms=14867.248 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer] rc=[resident-coordination-required,routing-and-delegation-evidence-needed,live-installed-integration-verification-needed,independent-staffing-audit-needed,separate-context-isolation-enforced] | fairness=[]
active-incident-containment | helpful=[incident-responder,incident-response-commander] | A=accepted/pass selected=[incident-responder] f1=0.666667 ms=6524.141 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[incident-response-commander,incident-responder,secrets-credential-hygiene-engineer,threat-detection-engineer] f1=0.666667 ms=16529.37 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:analysis] rc=[active-incident,forensic-evidence-preservation,reversible-recovery,credential-response,defensive-only-scope,offensive-probing-excluded] | fairness=[]
lsp-incremental-index | helpful=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=9333.394 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[lsp-index-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=11886.789 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[exact-agent-id-match,lsp-specialist-for-indexing,dedicated-failure-path-test-author,independent-reviewer,separate-contexts-for-specialists] | fairness=[]
disabled-lsp-winner | helpful=[lsp-index-engineer] | A=abstained/pass selected=[] f1=0 ms=12376.476 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[no_safe_sufficient_team,recruiter_abstained,selection_margin_too_low] | U=accepted/pass selected=[codebase-archaeologist] f1=0 ms=11459.5 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[best-specialist-disabled,use-independent-read-only-codepath-diagnosis,safest-next-step-is-evidence-gathering-before-modification] | fairness=[]
incidental-finance-language | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=8545.729 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=10906.749 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[python-specialist-for-parser-implementation,dedicated-test-specialist-for-failure-path-coverage,independent-code-review-required,financial-analysis-explicitly-excluded] | fairness=[]
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=accepted/fail selected=[application-observability-engineer,python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer,cross-platform-release-verifier] f1=0.941176 ms=9941.431 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor] rc=[] | U=error/fail selected=[] f1=0 ms=23117.197 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor,application-integration-verifier,application-observability-engineer,code-reviewer,cross-platform-release-verifier,python-application-engineer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[broad-python-typescript-application:arm_error]
brand-and-whimsy-separated | helpful=[brand-guardian,whimsy-injector,accessibility-auditor] | A=abstained/fail selected=[] f1=0 ms=10250.804 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor,brand-guardian,whimsy-injector;art:implementation-change,plan,review-report;life:implementation,planning,review] rc=[no_safe_sufficient_team,recruiter_abstained,independent_assurance_missing] | U=accepted/fail selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=15742.387 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:plan,review-report;life:review] rc=[brand-governance-matched-to-brand-guardian,playful-interface-matched-to-whimsy-injector,whimsy-injector-requires-accessibility-auditor,separate-isolated-work-units,independent-accessibility-audit] | fairness=[]
accounts-payable-cfo-separated | helpful=[accounts-payable-agent,chief-financial-officer] | A=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=8137.664 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=9971.209 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[domain-fit,separate-contexts-resolve-conflict,independent-review-requested] | fairness=[]
postgres-write-query-analysis | helpful=[database-optimizer] | A=accepted/pass selected=[database-optimizer] f1=1 ms=5481.716 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[database-optimizer] f1=1 ms=9597.543 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[exact-domain-match,read-only-analysis-scope,no-documentation-or-code-change] | fairness=[]
clinical-legal-boundary-review | helpful=[clinical-evidence-agent,legal-document-review] | A=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=10887.396 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=11176.882 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[clinical-evidence-agent-is-the-semantic-winner-for-supplied-clinical-trial-evidence,legal-document-review-is-the-semantic-winner-for-independent-legal-document-review,separate-contexts-preserve-specialist-independence,diagnosis-billing-and-compliance-certification-are-out-of-scope] | fairness=[]
```

An immediate matched rerun limited to those three Agency failures completed in
88.469 seconds with no stderr. All three Agency arms passed with F1 1.000000,
3/3 complete typed coverage, p50 10891.965 ms, p95/max 14836.692 ms, and zero
forbidden, ineligible, or conflict selections:

```text
selection-safety-review: selected selection-safety-critic; F1 1.000000;
  5965.867 ms
broad-python-typescript-application: selected the exact nine helpful workers;
  F1 1.000000; 14836.692 ms
brand-and-whimsy-separated: selected brand-guardian, whimsy-injector, and
  accessibility-auditor; F1 1.000000; 10891.965 ms
```

That bounded benchmark remained invalid because the selection-safety upstream
arm returned an unknown disabled shadow and the broad-application upstream arm
returned an invalid assignment row. The Agency failures did not repeat, so no
product or policy code changed and there is still no governed general semantic
defect that would justify weakening or tuning the deterministic contract. A
further complete corpus remains required to show all 19 Agency arms passing
together and to determine whether malformed upstream provider arms remain the
only comparison blocker.

The next recovery package kept the same command, 15000 ms cold gate, one-call
fast budget, Windows platform, codex-subscription provider, requested and
actual gpt-5.6-luna model, and low reasoning effort. It captured every stdout
and stderr stream outside the repository before parsing. Two complete corpora,
two bounded matched reruns, and four cold Agency-only diagnostics changed no
product or policy code.

The first complete process finished in 439.456 seconds, emitted no stderr,
returned exit status 1, and produced 1,186,753 bytes of valid JSON with stdout
SHA-256
0e1d10188f0b8f147c7620f7fd8e1403daf7a91afef2e11dfedf7d1af47ff65e.
The corpus, roster, and allowed-agent fingerprints were unchanged. Every arm
recorded the configured provider, requested and actual model, explicit-model
receipt source, one call, and applied inference.

Agency passed 16/19, with precision, recall, and F1 all 0.862069, 16/19
complete typed coverage, p50 8877.847 ms, p95/max 14861.832 ms, and zero
forbidden, ineligible, or conflict selections. Upstream passed 5/19, with
precision 0.717391, recall 0.568966, F1 0.634615, 9/19 complete typed
coverage, p50 13961.214 ms, p95/max 25875.952 ms, and zero scored safety
selections. The benchmark was invalid because the application-integration and
LSP upstream arms returned unknown disabled shadows and the broad-application
upstream arm returned an invalid assignment row.

The three Agency failures were fail-closed confidence or margin abstentions:
application observability, active incident containment, and clinical/legal
boundary review. The exact compact projection follows:

~~~text
python-production-change | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=7488.938 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=12140.48 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[selected-python-implementation-specialist,selected-failure-path-test-specialist,selected-independent-reviewer,kept-specialists-in-distinct-contexts] | fairness=[]
typescript-production-change | helpful=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=7430.24 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[typescript-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=12999.572 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[typescriptimplementationmatchedbytypescript-application-engineer,testcoveragematchedbysoftware-test-engineer,independentcodereviewmatchedbycode-reviewer,specialistskeptinseparatecontexts] | fairness=[]
backend-service-change | helpful=[backend-service-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[backend-service-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.888889 ms=8394.949 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[backend-architect,backend-service-engineer,software-test-engineer,code-reviewer] f1=0.75 ms=14180.981 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[backend-service-implementation,integration-test-coverage,independent-code-review,architecture-supports-production-readiness] | fairness=[]
installed-cross-platform-release | helpful=[software-test-engineer,code-reviewer,cross-platform-release-verifier] | A=accepted/pass selected=[cross-platform-installer-engineer,software-test-engineer,code-reviewer,test-results-analyzer,cross-platform-release-verifier] f1=0.75 ms=6371.943 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[agents-orchestrator,cross-platform-installer-engineer,software-test-engineer,cross-platform-release-verifier,application-integration-verifier,code-reviewer] f1=0.666667 ms=15477.12 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[matchedcross-platformpackaging,matchedindependentinstalled-releaseverification,matchedtestimplementation,matchedintegrationverification,matchedcode-review,keptspecialistsinseparatecontexts] | fairness=[]
application-integration | helpful=[software-test-engineer,code-reviewer,application-integration-verifier] | A=accepted/pass selected=[minimal-change-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.75 ms=7639.494 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=16201.881 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-integration-verifier,code-reviewer,software-test-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[application-integration:arm_error]
application-observability | helpful=[application-observability-engineer,software-test-engineer,code-reviewer] | A=abstained/fail selected=[] f1=0 ms=10088.399 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-observability-engineer,code-reviewer,software-test-engineer;art:implementation-change,review-report,test-code;life:implementation,review,testing] rc=[selection_confidence_too_low] | U=accepted/fail selected=[application-observability-engineer,software-test-engineer,application-integration-verifier] f1=0.666667 ms=11512.471 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer] rc=[matched-capabilities,complementary-specialists,separate-contexts,independent-review] | fairness=[]
documentation-change | helpful=[technical-writer,code-reviewer] | A=accepted/pass selected=[technical-writer,code-reviewer] f1=1 ms=6361.758 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[technical-writer,code-reviewer] f1=1 ms=11182.205 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:documentation] rc=[documentation-rewrite-routed-to-technical-writer,independent-technical-accuracy-review-routed-to-code-reviewer,separate-contexts-preserve-review-independence] | fairness=[]
selection-safety-review | helpful=[selection-safety-critic] | A=accepted/pass selected=[selection-safety-critic] f1=1 ms=5519.42 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[agents-orchestrator,selection-safety-critic] f1=0.666667 ms=9569.021 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[direct-match-selection-audit,resident-routing-required,independent-safety-review,separate-specialist-contexts] | fairness=[]
repository-security-patch-review | helpful=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] | A=accepted/pass selected=[codebase-onboarding-engineer,finops-engineer,code-reviewer,ai-generated-code-security-auditor,senior-secops-engineer] f1=0.75 ms=9150.484 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[codebase-onboarding-engineer,code-reviewer,application-security-engineer] f1=0.666667 ms=15616.652 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:ai-generated-code-security-auditor] rc=[read-only-review-request,separate-independent-review-contexts,no-file-changes-authorized,all-selected-agents-are-allowed-enabled-and-eligible] | fairness=[]
runtime-routing-integration-failure | helpful=[application-integration-verifier,selection-safety-critic,test-results-analyzer] | A=accepted/pass selected=[codebase-onboarding-engineer,application-integration-verifier,test-results-analyzer,selection-safety-critic] f1=0.857143 ms=7741.133 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[multi-agent-systems-architect,codebase-archaeologist,application-integration-verifier,test-automation-engineer,selection-safety-critic] f1=0.5 ms=17150.891 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer] rc=[diagnostic-requestrequiresroutinganddelegationanalysis,localintegrationtestingrequiresinstalled-appseamverification,independentstaffingauditrequiresselection-safety-critic,separatespecialistsintodistinctcontexts,noenabledsemanticwinnerwasdisabled] | fairness=[]
active-incident-containment | helpful=[incident-responder,incident-response-commander] | A=abstained/fail selected=[] f1=0 ms=9031.797 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:incident-responder;art:analysis,plan;life:discovery,planning] rc=[selection_margin_too_low] | U=accepted/fail selected=[incident-responder,secrets-credential-hygiene-engineer,threat-detection-engineer] f1=0.4 ms=15709.431 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:analysis;life:discovery] rc=[active-security-incident,forensic-evidence-preservation,reversible-recovery,defensive-only-scope,avoid-conflict-with-incident-response-commander] | fairness=[]
lsp-incremental-index | helpful=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=7624.577 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=13961.214 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,lsp-index-engineer,software-test-engineer,test-results-analyzer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[lsp-incremental-index:arm_error]
disabled-lsp-winner | helpful=[lsp-index-engineer] | A=abstained/pass selected=[] f1=0 ms=9230.822 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[no_safe_sufficient_team,recruiter_abstained,selection_margin_too_low] | U=accepted/pass selected=[codebase-archaeologist] f1=0 ms=11796.031 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[best-semantic-match-disabled,read-only-evidence-first,async-state-and-semantic-drift-diagnosis,safest-next-step-is-bounded-repository-audit-before-modification] | fairness=[]
incidental-finance-language | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=9854.454 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=16402.736 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[python-implementation,failure-path-test-coverage,independent-code-review,financial-analysis-explicitly-excluded] | fairness=[]
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=accepted/pass selected=[application-observability-engineer,python-application-engineer,typescript-application-engineer,software-test-engineer,accessibility-auditor,cross-platform-release-verifier,test-results-analyzer,code-reviewer,application-integration-verifier] f1=1 ms=14861.832 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=25875.952 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor,application-integration-verifier,application-observability-engineer,code-reviewer,cross-platform-release-verifier,python-application-engineer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[provider_response_contract_invalid,upstream assignment row is invalid] | fairness=[broad-python-typescript-application:arm_error]
brand-and-whimsy-separated | helpful=[brand-guardian,whimsy-injector,accessibility-auditor] | A=accepted/pass selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=10705.641 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=17469.005 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:review-report;life:review] rc=[brand-governance-routed-to-brand-guardian,playful-details-routed-to-whimsy-injector,accessibility-audit-required-by-whimsy-injector,specialists-isolated-in-distinct-contexts] | fairness=[]
accounts-payable-cfo-separated | helpful=[accounts-payable-agent,chief-financial-officer] | A=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=10660.601 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=11332.036 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[exact-agent-id-match,domain-specialization-match,separate-context-required-for-independent-review,same-context-conflict-avoided] | fairness=[]
postgres-write-query-analysis | helpful=[database-optimizer] | A=accepted/pass selected=[database-optimizer] f1=1 ms=8942.165 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[database-optimizer] f1=1 ms=12047.067 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[semantic-match-database-query-performance,read-only-measured-findings,no-documentation-or-implementation-artifact,single-specialist-sufficient] | fairness=[]
clinical-legal-boundary-review | helpful=[clinical-evidence-agent,legal-document-review] | A=abstained/fail selected=[] f1=0 ms=8877.847 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:clinical-evidence-agent,legal-document-review;art:analysis,review-report;life:discovery,review] rc=[selection_confidence_too_low] | U=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=10545.059 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[clinical-evidence-agent7is7the7exact7semantic7match7for7source-grounded7clinical7evidence7review,legal-document-review7is7the7exact7semantic7match7for7reviewing7supplied7legal7documents,separate7isolated7contexts7preserve7independent7specialist7reviews] | fairness=[]
~~~

The immediate three-case matched rerun finished in 69.568 seconds with no
stderr. Active incident containment and clinical/legal review passed, but
application observability repeated the same confidence abstention. Four
subsequent cold Agency-only one-call diagnostics all produced valid plans,
exact staffing, complete coverage, and zero safety defects in 8061.570,
10516.236, 14547.327, and 8318.659 ms. A final matched observability-only run
then passed in 7971.287 ms with the required observability, testing, and review
workers plus test-results-analyzer. Its benchmark was valid and the command
returned status 0. These diagnostics established configured-model plan-shape
variance rather than a repeatable governed semantic defect.

The second complete process then finished in 416.771 seconds, emitted no
stderr, returned exit status 1, and produced 1,195,404 bytes of valid JSON with
stdout SHA-256
974f5302b982a3d94667a980e0da902d975da7425e246f90dede3fb664a4219c.
The provider, model, receipt, call-count, inference, corpus, roster, and
allowed-agent bindings remained unchanged.

Agency passed 15/19, with precision 0.883333, recall 0.913793, F1 0.898305,
17/19 complete typed coverage, p50 8349.636 ms, p95/max 15216.664 ms, and zero
forbidden, ineligible, or conflict selections. Upstream passed 4/19, with
precision 0.711864, recall 0.724138, F1 0.717949, 8/19 complete typed coverage,
p50 12477.245 ms, p95/max 21762.725 ms, and zero scored safety selections. The
benchmark was invalid because the application-integration upstream arm
returned an unknown disabled shadow.

The four Agency failures were selection-safety confidence and margin
abstention, active-incident independent-assurance and margin abstention, the
exact broad-application team exceeding the unchanged gate by 216.664 ms, and
clinical/legal selection omitting legal-document-review. The exact compact
projection follows:

~~~text
python-production-change | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=8112.317 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=10845.72 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[narrow-python-implementation,failure-path-tests-required,independent-review-required,separate-contexts-for-specialists] | fairness=[]
typescript-production-change | helpful=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=8481.043 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[typescript-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=12377.902 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[typescript-implementation,automated-tests,independent-review] | fairness=[]
backend-service-change | helpful=[backend-service-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[backend-service-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.888889 ms=6693.325 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[backend-architect,backend-service-engineer,software-test-engineer,code-reviewer] f1=0.75 ms=13127.023 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[production-backend-service,integration-testing,independent-code-review,separate-specialist-contexts] | fairness=[]
installed-cross-platform-release | helpful=[software-test-engineer,code-reviewer,cross-platform-release-verifier] | A=accepted/pass selected=[cross-platform-installer-engineer,software-test-engineer,code-reviewer,test-results-analyzer,cross-platform-release-verifier] f1=0.75 ms=5701.621 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[agents-orchestrator,desktop-app-engineer,cross-platform-installer-engineer,software-test-engineer,cross-platform-release-verifier,code-reviewer] f1=0.666667 ms=18155.275 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[cross-platform-packaging,installed-release-verification,implementation-testing-review,distinct-isolated-specialist-contexts] | fairness=[]
application-integration | helpful=[software-test-engineer,code-reviewer,application-integration-verifier] | A=accepted/pass selected=[minimal-change-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.75 ms=6978.49 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=12270.818 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-integration-verifier,code-reviewer,software-test-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[application-integration:arm_error]
application-observability | helpful=[application-observability-engineer,software-test-engineer,code-reviewer] | A=accepted/pass selected=[application-observability-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=0.857143 ms=7810.004 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[application-observability-engineer,software-test-engineer,application-integration-verifier,code-reviewer] f1=0.857143 ms=16849.817 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[production-observability-requires-runtime-telemetry-and-failure-diagnostics,failure-telemetry-requires-executable-failure-path-tests,integration-verification-covers-cross-component-seams,independent-review-requires-a-separate-review-context,all-selected-agent-ids-are-present-in-allowed-agent-ids,no-selected-agent-is-disabled] | fairness=[]
documentation-change | helpful=[technical-writer,code-reviewer] | A=accepted/pass selected=[technical-writer,code-reviewer] f1=1 ms=11049.137 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[technical-writer,codebase-archaeologist] f1=0.5 ms=12477.245 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer;art:documentation] rc=[documentation-implementation-routed-to-technical-writer,independent-accuracy-review-routed-to-codebase-archaeologist,separate-contexts-enforced] | fairness=[]
selection-safety-review | helpful=[selection-safety-critic] | A=abstained/fail selected=[] f1=0 ms=5863.323 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:selection-safety-critic;art:review-report;life:review] rc=[selection_confidence_too_low,selection_margin_too_low] | U=accepted/pass selected=[selection-safety-critic] f1=1 ms=8228.686 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[direct-specialist-match,selection-safety-critic-explicitly-covers-workforce-selection-and-composition,review-report-required,isolated-context-required] | fairness=[]
repository-security-patch-review | helpful=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] | A=accepted/pass selected=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] f1=1 ms=8349.636 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[codebase-archaeologist,code-reviewer,application-security-engineer] f1=0.333333 ms=14265.802 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:ai-generated-code-security-auditor,codebase-onboarding-engineer] rc=[security-patch-needs-code-path-tracing,independent-correctness-review-required,independent-exploitability-review-required,separate-contexts-preserve-review-independence] | fairness=[]
runtime-routing-integration-failure | helpful=[application-integration-verifier,selection-safety-critic,test-results-analyzer] | A=accepted/pass selected=[codebase-onboarding-engineer,application-integration-verifier,test-results-analyzer,selection-safety-critic] f1=0.857143 ms=8774.084 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[multi-agent-systems-architect,application-integration-verifier,selection-safety-critic] f1=0.666667 ms=13367.787 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer] rc=[request-is-a-routing-and-integration-diagnosis,separate-contexts-required-for-independent-specialists,selected-agents-have-explicit-scope-and-tool-fit,no-disabled-semantic-winner-identified-in-supplied-roster] | fairness=[]
active-incident-containment | helpful=[incident-responder,incident-response-commander] | A=abstained/fail selected=[] f1=0 ms=8233.863 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:incident-responder;art:analysis,plan;life:discovery,planning] rc=[independent_assurance_missing,selection_margin_too_low] | U=accepted/fail selected=[incident-response-commander,incident-responder,secrets-credential-hygiene-engineer,threat-detection-engineer,data-privacy-officer] f1=0.571429 ms=18067.603 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:analysis] rc=[defensive-incident-response,forensic-preservation,reversible-recovery,no-offensive-probing,no-disabled-semantic-winner] | fairness=[]
lsp-incremental-index | helpful=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=9104.544 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[lsp-index-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=14617.921 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[exactagentidsfromallowedroster,lsp-specialistselectedforincremental-indexingimplementation,dedicatedfailure-pathtestengineerselected,independentcodereviewselected,specialistskeptindistinctcontexts] | fairness=[]
disabled-lsp-winner | helpful=[lsp-index-engineer] | A=abstained/pass selected=[] f1=0 ms=8602.899 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[no_safe_sufficient_team,recruiter_abstained] | U=accepted/pass selected=[agents-orchestrator,codebase-archaeologist] f1=0 ms=11553.804 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[best-specialist-disabled,use-read-only-cross-era-drift-audit,safest-next-step-is-reproduce-and-trace-cancellation-lifecycle-before-any-code-change] | fairness=[]
incidental-finance-language | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=11796.732 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=10821.602 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[python-parser-implementation-matched-to-python-application-engineer,failure-path-testing-matched-to-software-test-engineer,independent-review-matched-to-code-reviewer,separate-contexts-required-for-specialists,financial-analysis-explicitly-excluded] | fairness=[]
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=accepted/fail selected=[application-observability-engineer,python-application-engineer,typescript-application-engineer,software-test-engineer,accessibility-auditor,code-reviewer,application-integration-verifier,test-results-analyzer,cross-platform-release-verifier] f1=1 ms=15216.664 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[backend-architect,backend-service-engineer,typescript-application-engineer,software-test-engineer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-installer-engineer,cross-platform-release-verifier] f1=0.666667 ms=21762.725 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,python-application-engineer,test-results-analyzer;art:review-report;life:review] rc=[exact-agent-id-enforcement,separate-context-required-for-specialists,production-api-and-dashboard-scope,failure-path-testing-required,accessibility-review-required,observability-required,independent-integration-verification-required,cross-platform-release-evidence-required] | fairness=[]
brand-and-whimsy-separated | helpful=[brand-guardian,whimsy-injector,accessibility-auditor] | A=accepted/pass selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=8578.833 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=17900.875 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:plan,review-report;life:planning,review] rc=[brand-governance-matched-to-brand-guardian,playful-interface-details-matched-to-whimsy-injector,independent-accessibility-audit-matched-to-accessibility-auditor,isolated-work-unit-preserved,required-whimsy-accessibility-dependency-satisfied] | fairness=[]
accounts-payable-cfo-separated | helpful=[accounts-payable-agent,chief-financial-officer] | A=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=7264.067 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=8494.458 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:review-report] rc=[specialized-fit,independent-review-required,same-context-conflict-avoided] | fairness=[]
postgres-write-query-analysis | helpful=[database-optimizer] | A=accepted/pass selected=[database-optimizer] f1=1 ms=6943.451 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[database-optimizer] f1=1 ms=8010.779 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[direct-match-database-query-performance,read-only-analysis-scope,measured-query-plan-findings] | fairness=[]
clinical-legal-boundary-review | helpful=[clinical-evidence-agent,legal-document-review] | A=accepted/fail selected=[clinical-evidence-agent] f1=0.666667 ms=8656.413 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:legal-document-review] rc=[] | U=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=9201.499 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[clinical-evidence-agent-is-direct-domain-match,legal-document-review-is-direct-document-review-match,separate-contexts-preserve-independence,both-agent-ids-are-allowed-and-eligible] | fairness=[]
~~~

The immediate matched rerun of those four Agency failures finished in 108.526
seconds with no stderr. Every Agency arm passed, complete typed coverage was
4/4, precision was 1.000000, recall was 0.928571, F1 was 0.962963, p50 was
9903.703 ms, p95/max was 14055.499 ms, and forbidden, ineligible, and conflict
counts were all zero:

~~~text
selection-safety-review | helpful=[selection-safety-critic] | A=accepted/pass selected=[selection-safety-critic] f1=1 ms=6535.964 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[selection-safety-critic,multi-agent-systems-architect] f1=0.666667 ms=12486.564 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[selection-safety-critic-is-the-semantic-primary-for-workforce-selection-audits,multi-agent-systems-architect-provides-independent-composition-and-conflict-analysis,separate-isolated-contexts-preserve-specialist-independence] | fairness=[]
active-incident-containment | helpful=[incident-responder,incident-response-commander] | A=accepted/pass selected=[incident-responder] f1=0.666667 ms=7133.951 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[incident-responder,secrets-credential-hygiene-engineer,threat-detection-engineer] f1=0.4 ms=16844.956 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:analysis;life:discovery] rc=[active-security-incident,forensic-preservation-required,reversible-recovery-required,offensive-probing-excluded,separate-specialist-contexts] | fairness=[]
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=accepted/pass selected=[python-application-engineer,typescript-application-engineer,application-observability-engineer,software-test-engineer,accessibility-auditor,code-reviewer,application-integration-verifier,test-results-analyzer,cross-platform-release-verifier] f1=1 ms=14055.499 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=27879.49 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor,application-integration-verifier,application-observability-engineer,code-reviewer,cross-platform-release-verifier,python-application-engineer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[provider_response_contract_invalid,upstream assignment row is invalid] | fairness=[broad-python-typescript-application:arm_error]
clinical-legal-boundary-review | helpful=[clinical-evidence-agent,legal-document-review] | A=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=12673.456 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=9703.6 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[domain-match-clinical-evidence,domain-match-legal-document-review,separate-contexts-for-independent-specialists,no-diagnosis-or-billing-agent-selected] | fairness=[]
~~~

That bounded benchmark was invalid only because the broad-application upstream
arm returned an invalid assignment row. None of the complete-run Agency
failures repeated in its immediate bounded rerun, and the broad-application
latency returned below the unchanged gate. No governed general semantic defect
was established, so changing planner normalization, staffing thresholds,
typed coverage, response parsing, the latency gate, or the one-call budget
would tune policy to variable model output.

The receiving matched-selection package ran one further complete corpus from
checkpoint `dbc1742` with the unchanged 15000 ms cold gate, one-call fast
budget, Windows platform, `codex-subscription` provider, requested and actual
`gpt-5.6-luna` model, and low reasoning effort. Stdout and stderr were
captured separately outside the repository before parsing. The process finished
in 444.622 seconds, returned exit status 1, emitted 1,187,735 bytes of valid
JSON on stdout with SHA-256
`cb51a957743c0afeb91bb2a305b28f746bf6b8a2ad772cab7e64eb41b6fefbf4`,
and emitted zero stderr bytes with the empty-stream SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
The stream byte counts and hashes were verified again before the JSON was
parsed.

The corpus fingerprint remained
`sha256:7358cb9422cef681dc7d85323160652029792916c2ea74d81514df6cfebbba38`,
the base-roster fingerprint remained
`sha256:c80b7422124f5935d3956ec48d6d0fffca15e7c23ebd155475998c7418e4f795`,
and the allowed-agent fingerprint remained
`sha256:88d310bad3716357bf49a74c53a873236cf9c549b878c3c190b4affebead7765`.
Every arm recorded provider `codex-subscription`, requested and actual model
`gpt-5.6-luna`, receipt source `cli.explicit_model_argument`, one call,
applied inference, and the unchanged latency budget.

Agency passed 18/19, with precision 0.898305, recall 0.913793, F1 0.905983,
18/19 complete typed coverage, p50 8648.505 ms, p95/max 12484.032 ms, and zero
forbidden, ineligible, or conflict selections. Descriptive upstream aggregates
were 4/19 passing, precision 0.767442, recall 0.568966, F1 0.653465, 7/19
complete typed coverage, p50 12366.851 ms, p95/max 20954.238 ms, and zero scored
safety selections. The benchmark was invalid because the Python, TypeScript,
application-integration, and runtime-routing upstream arms returned unknown
disabled shadows, while the backend upstream arm returned an invalid assignment
row. Those malformed arms are retained as errors below and are not interpreted
as upstream losses.

The sole Agency failure was a fail-closed
`runtime-routing-integration-failure` confidence abstention. It selected no
worker, remained under the unchanged latency gate at 12484.032 ms, and produced
no forbidden, ineligible, or conflicting selection. The exact compact
projection follows:

~~~text
python-production-change | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=7706.434 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=11321.307 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,python-application-engineer,software-test-engineer,test-results-analyzer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[python-production-change:arm_error]
typescript-production-change | helpful=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=7296.867 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=18480.441 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[typescript-production-change:arm_error]
backend-service-change | helpful=[backend-service-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[backend-service-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.888889 ms=7649.318 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=16010.209 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:backend-service-engineer,code-reviewer,software-test-engineer,test-results-analyzer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream assignment row is invalid] | fairness=[backend-service-change:arm_error]
installed-cross-platform-release | helpful=[software-test-engineer,code-reviewer,cross-platform-release-verifier] | A=accepted/pass selected=[cross-platform-installer-engineer,software-test-engineer,code-reviewer,test-results-analyzer,cross-platform-release-verifier] f1=0.75 ms=5430.844 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[cross-platform-installer-engineer,software-test-engineer,application-integration-verifier,cross-platform-release-verifier,code-reviewer] f1=0.75 ms=16506.519 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[direct-match-cross-platform-packaging,independent-test-and-integration-evidence,release-verification-required,separate-contexts-for-specialists] | fairness=[]
application-integration | helpful=[software-test-engineer,code-reviewer,application-integration-verifier] | A=accepted/pass selected=[minimal-change-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.75 ms=7184.359 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=17868.715 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-integration-verifier,code-reviewer,software-test-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[application-integration:arm_error]
application-observability | helpful=[application-observability-engineer,software-test-engineer,code-reviewer] | A=accepted/pass selected=[application-observability-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=0.857143 ms=9116.245 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[sre-site-reliability-engineer,application-observability-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=18804.988 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[production-observability,failure-telemetry,failure-path-testing,independent-review,separate-specialist-contexts] | fairness=[]
documentation-change | helpful=[technical-writer,code-reviewer] | A=accepted/pass selected=[technical-writer,code-reviewer] f1=1 ms=12028.276 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[technical-writer,codebase-archaeologist] f1=0.5 ms=10703.04 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer;art:documentation] rc=[documentation-rewrite-matched-to-technical-writer,independent-technical-accuracy-review-matched-to-codebase-archaeologist,separate-contexts-preserve-review-independence] | fairness=[]
selection-safety-review | helpful=[selection-safety-critic] | A=accepted/pass selected=[selection-safety-critic] f1=1 ms=7309.422 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[agents-orchestrator,selection-safety-critic] f1=0.666667 ms=10666.447 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[exact-agent-id-allowlist-match,selection-safety-critic-is-direct-semantic-match,separate-isolated-contexts-enforced,no-conflict-pair-selected] | fairness=[]
repository-security-patch-review | helpful=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] | A=accepted/pass selected=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] f1=1 ms=9512.577 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[codebase-onboarding-engineer,code-reviewer,application-security-engineer] f1=0.666667 ms=11799.151 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:ai-generated-code-security-auditor] rc=[read-only-review-request,separate-independent-contexts,code-path-mapping-required,correctness-review-required,exploitability-audit-required] | fairness=[]
runtime-routing-integration-failure | helpful=[application-integration-verifier,selection-safety-critic,test-results-analyzer] | A=abstained/fail selected=[] f1=0 ms=12484.032 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-integration-verifier,selection-safety-critic,test-results-analyzer;art:review-report,test-evidence;life:review,testing] rc=[selection_confidence_too_low] | U=error/fail selected=[] f1=0 ms=20954.238 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-integration-verifier,selection-safety-critic,test-results-analyzer;art:review-report,test-evidence;life:review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[runtime-routing-integration-failure:arm_error]
active-incident-containment | helpful=[incident-responder,incident-response-commander] | A=accepted/pass selected=[incident-responder] f1=0.666667 ms=7465.333 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[incident-response-commander,incident-responder] f1=1 ms=11043.222 safety=f0/i0/c0 disabled=[]/required=[] missing=[life:planning] rc=[active-security-incident,forensic-evidence-preservation,reversible-recovery-planning,no-offensive-probing,distinct-contexts-for-specialists] | fairness=[]
lsp-incremental-index | helpful=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=9367.997 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[lsp-index-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=16338.324 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[exact-agent-id-match,implementation-specialist-selected,failure-path-test-specialist-selected,independent-review-specialist-selected,separate-contexts-for-specialists] | fairness=[]
disabled-lsp-winner | helpful=[lsp-index-engineer] | A=abstained/pass selected=[] f1=0 ms=8648.505 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[no_safe_sufficient_team,recruiter_abstained,selection_margin_too_low] | U=accepted/pass selected=[codebase-archaeologist] f1=0 ms=12398.581 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[best-specialist-disabled,fallback-to-enabled-semantic-neighbor,read-only-diagnosis-before-implementation,preserve-cancellation-and-symbol-lineage-evidence] | fairness=[]
incidental-finance-language | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=11735.513 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=12235.973 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[python-implementation-selected-for-parser-change,dedicated-failure-path-test-specialist-selected,independent-code-review-required,financial-analysis-excluded-by-request,distinct-contexts-enforced] | fairness=[]
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=accepted/pass selected=[python-application-engineer,typescript-application-engineer,application-observability-engineer,software-test-engineer,accessibility-auditor,code-reviewer,application-integration-verifier,test-results-analyzer,cross-platform-release-verifier] f1=1 ms=11178.567 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[agents-orchestrator,backend-architect,python-application-engineer,typescript-application-engineer,software-test-engineer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-installer-engineer,cross-platform-release-verifier] f1=0.736842 ms=20505.454 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,test-results-analyzer;art:review-report] rc=[multi-phase-production-engineering,distinct-context-specialists,implementation-and-testing-complementarity,independent-integration-verification,cross-platform-release-evidence] | fairness=[]
brand-and-whimsy-separated | helpful=[brand-guardian,whimsy-injector,accessibility-auditor] | A=accepted/pass selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=10027.487 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=11908.501 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:review-report;life:review] rc=[brand-governance-matched-to-brand-guardian,playful-interface-matched-to-whimsy-injector,accessibility-audit-is-independent,required-context-isolation-honored,all-selected-agents-enabled-and-allowed] | fairness=[]
accounts-payable-cfo-separated | helpful=[accounts-payable-agent,chief-financial-officer] | A=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=7617.68 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=12366.851 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:review-report] rc=[exact-agent-id-match,allowed-agent-id,eligible-worker,specialized-capability-match,separate-contexts-required-by-conflict-policy] | fairness=[]
postgres-write-query-analysis | helpful=[database-optimizer] | A=accepted/pass selected=[database-optimizer] f1=1 ms=8589.698 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[database-optimizer] f1=1 ms=9745.939 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[database-optimizer-is-the-exact-semantic-fit,analysis-only-output-request,no-documentation-or-implementation-assignment,performance-benchmarker-not-selected-authorized-load-test-environment-and-traffic-budget-are-not-supplied] | fairness=[]
clinical-legal-boundary-review | helpful=[clinical-evidence-agent,legal-document-review] | A=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=10395.268 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=12114.716 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[clinical-evidence-summary07requires07clinical-evidence-agent,legal-document-use07requires07independent07legal-document-review,separate07specialists07assigned07distinct07contexts,no07disabled07semantic07winner07identified] | fairness=[]

~~~

The immediate matched runtime-routing confirmation captured both streams
outside the repository and finished in 25.214 seconds. It returned exit status
0, emitted 711,681 stdout bytes with SHA-256
`c0d79bf920872433acb6d0110677368d974fdc7819be287ea7a1249875cddaee`,
and emitted zero stderr bytes with SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
The bounded corpus fingerprint was
`sha256:45ace89b8e46871a53a1cc2bfbabfebb907b1616f63f00a190a5a96b0bb677ba`;
the base-roster and allowed-agent fingerprints were unchanged. Both arms
recorded the same provider, requested and actual model, receipt source,
one-call count, applied inference, and 15000 ms latency budget as the complete
run.
The bounded benchmark was valid. Agency passed with complete typed coverage,
precision 0.750000, recall 1.000000, F1 0.857143, 12799.429 ms latency, and
zero forbidden, ineligible, or conflict selections:

~~~text
runtime-routing-integration-failure | helpful=[application-integration-verifier,selection-safety-critic,test-results-analyzer] | A=accepted/pass selected=[codebase-onboarding-engineer,selection-safety-critic,application-integration-verifier,test-results-analyzer] f1=0.857143 ms=12799.429 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[agents-orchestrator,multi-agent-systems-architect,application-integration-verifier,selection-safety-critic] f1=0.571429 ms=11321.225 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer] rc=[resident-routing-required,separate-isolated-contexts,live-integration-evidence-requested,independent-staffing-audit-requested] | fairness=[]

~~~

The complete-run Agency abstention did not repeat in its immediate matched
confirmation. No governed general semantic defect was established, so no
product or policy code changed. Changing planner normalization, staffing
thresholds, typed coverage, response parsing, the latency gate, or the one-call
budget would tune policy to variable model output. No comparative superiority
claim is made.

The next matched-selection recovery package started from checkpoint
`97896f0` with the unchanged 15000 ms cold gate, one-call fast budget,
Windows platform, `codex-subscription` provider, requested and actual
`gpt-5.6-luna` model, and low reasoning effort. Stdout and stderr were
captured as separate raw byte streams outside the repository before parsing.
The complete process finished in 506.068 seconds, returned exit status 1,
emitted 1,188,204 stdout bytes with SHA-256
`24cba48946d8f8e48767da0958e1277544811c200a4674382f7c629b232dd265`,
and emitted zero stderr bytes with the empty-stream SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

The corpus fingerprint remained
`sha256:7358cb9422cef681dc7d85323160652029792916c2ea74d81514df6cfebbba38`,
the base-roster fingerprint remained
`sha256:c80b7422124f5935d3956ec48d6d0fffca15e7c23ebd155475998c7418e4f795`,
and the allowed-agent fingerprint remained
`sha256:88d310bad3716357bf49a74c53a873236cf9c549b878c3c190b4affebead7765`.
Every arm recorded provider `codex-subscription`, requested and actual model
`gpt-5.6-luna`, receipt source `cli.explicit_model_argument`, one call,
applied inference, and the unchanged latency budget.

Agency passed 16/19, with precision 0.887097, recall 0.948276, F1 0.916667,
18/19 complete typed coverage, p50 10651.201 ms, p95/max 21550.432 ms, and
zero forbidden, ineligible, or conflict selections. Descriptive upstream
aggregates were 4/19 passing, precision 0.717391, recall 0.568966, F1
0.634615, 8/19 complete typed coverage, p50 16039.879 ms, p95/max 21438.083
ms, and zero scored safety selections. The benchmark was invalid because the
TypeScript, backend, active-incident, and LSP upstream arms returned unknown
disabled shadows. Those malformed arms are retained as errors and are not
interpreted as upstream losses.

The three Agency failures were non-safety outcomes. Application integration
selected its complete typed team but exceeded the unchanged gate at 18467.060
ms. Active incident containment failed closed on independent assurance and
selection margin at 11822.331 ms. Clinical/legal review selected its exact
two-worker team but exceeded the unchanged gate at 21550.432 ms. The exact
compact projection follows:

~~~text
python-production-change | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=8305.368 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=12375.773 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[python-implementation-match,failure-path-testing-match,independent-code-review-match,separate-contexts-for-specialists] | fairness=[]
typescript-production-change | helpful=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=7691.552 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=16039.879 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[typescript-production-change:arm_error]
backend-service-change | helpful=[backend-service-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[backend-service-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.888889 ms=10651.201 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=18209.11 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:backend-service-engineer,code-reviewer,software-test-engineer,test-results-analyzer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[backend-service-change:arm_error]
installed-cross-platform-release | helpful=[software-test-engineer,code-reviewer,cross-platform-release-verifier] | A=accepted/pass selected=[cross-platform-installer-engineer,software-test-engineer,code-reviewer,test-results-analyzer,cross-platform-release-verifier] f1=0.75 ms=13857.52 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[cross-platform-installer-engineer,software-test-engineer,cross-platform-release-verifier,code-reviewer,devops-automator] f1=0.75 ms=18342.136 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[selectedspecialistswhosecapabilitiesdirectlymatchcross-platformpackagingtestingreviewandinstalled-releaseverification,keptisolated-onlyspecialistsinseparatecontextvalues,includedindependentreleaseverificationafterimplementationandtesting] | fairness=[]
application-integration | helpful=[software-test-engineer,code-reviewer,application-integration-verifier] | A=accepted/fail selected=[minimal-change-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.75 ms=18467.06 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[agents-orchestrator,backend-service-engineer,software-test-engineer,application-integration-verifier] f1=0.571429 ms=18241.787 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer;art:review-report] rc=[implementation-plus-test-plus-independent-verification,separate-contexts-for-specialists,all-selected-agent-ids-are-allowed-and-eligible] | fairness=[]
application-observability | helpful=[application-observability-engineer,software-test-engineer,code-reviewer] | A=accepted/pass selected=[application-observability-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=0.857143 ms=7984.205 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[application-observability-engineer,software-test-engineer,application-integration-verifier,code-reviewer] f1=0.857143 ms=17972.045 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[implementation-role-matched-to-runtime-telemetry,failure-path-testing-required,independent-integration-verification-required,independent-code-review-required] | fairness=[]
documentation-change | helpful=[technical-writer,code-reviewer] | A=accepted/pass selected=[technical-writer,code-reviewer] f1=1 ms=9005.033 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[technical-writer,codebase-archaeologist] f1=0.5 ms=12237.773 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer;art:documentation] rc=[documentation-rewrite,independent-technical-accuracy-review,separate-contexts-for-independent-specialists] | fairness=[]
selection-safety-review | helpful=[selection-safety-critic] | A=accepted/pass selected=[selection-safety-critic] f1=1 ms=7762.857 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[selection-safety-critic] f1=1 ms=9392.07 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[direct17semantic17match,review-only17assignment17preserves17independence,isolated17context17required17by17agent17contract] | fairness=[]
repository-security-patch-review | helpful=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] | A=accepted/pass selected=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] f1=1 ms=9202.241 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[code-reviewer,application-security-engineer] f1=0.4 ms=11287.935 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:ai-generated-code-security-auditor,codebase-onboarding-engineer;life:discovery] rc=[repository-security-patch-review,read-only-review-no-implementation,independent-correctness-and-exploitability-specialists,distinct-isolated-contexts] | fairness=[]
runtime-routing-integration-failure | helpful=[application-integration-verifier,selection-safety-critic,test-results-analyzer] | A=accepted/pass selected=[codebase-onboarding-engineer,application-integration-verifier,test-results-analyzer,selection-safety-critic] f1=0.857143 ms=10432.255 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[multi-agent-systems-architect,application-integration-verifier,selection-safety-critic] f1=0.666667 ms=16256.619 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer] rc=[exact-agent-id-match,scope-aligned-routing-diagnosis,scope-aligned-live-integration-testing,independent-staffing-review,isolated-contexts-for-separate-specialists] | fairness=[]
active-incident-containment | helpful=[incident-responder,incident-response-commander] | A=abstained/fail selected=[] f1=0 ms=11822.331 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:incident-responder;art:analysis,plan;life:discovery,planning] rc=[independent_assurance_missing,selection_margin_too_low] | U=error/fail selected=[] f1=0 ms=11692.991 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:incident-responder;art:analysis,plan;life:discovery,planning] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[active-incident-containment:arm_error]
lsp-incremental-index | helpful=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=10336.74 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=20358.674 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,lsp-index-engineer,software-test-engineer,test-results-analyzer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[lsp-incremental-index:arm_error]
disabled-lsp-winner | helpful=[lsp-index-engineer] | A=abstained/pass selected=[] f1=0 ms=10926.735 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[selection_margin_too_low] | U=accepted/pass selected=[codebase-archaeologist] f1=0 ms=10162.237 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[best-specialist-disabled,use-enabled-nearest-semantic-neighbor,preserve-read-only-diagnosis-before-code-changes,separate-context-for-specialist-analysis] | fairness=[]
incidental-finance-language | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=9224.556 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=16305.014 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[python-implementation-required,failure-path-testing-required,independent-review-required,financial-analysis-explicitly-excluded] | fairness=[]
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=accepted/pass selected=[application-observability-engineer,python-application-engineer,typescript-application-engineer,software-test-engineer,accessibility-auditor,code-reviewer,application-integration-verifier,test-results-analyzer,cross-platform-release-verifier] f1=1 ms=14410.031 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[agents-orchestrator,backend-architect,python-application-engineer,frontend-developer,software-test-engineer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-installer-engineer,cross-platform-release-verifier] f1=0.631579 ms=21438.083 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,test-results-analyzer,typescript-application-engineer;art:review-report;life:review] rc=[production-python-api,typescript-dashboard,failure-path-testing,accessibility-review,observability,independent-integration-verification,windows-linux-release-evidence,separate-specialist-contexts] | fairness=[]
brand-and-whimsy-separated | helpful=[brand-guardian,whimsy-injector,accessibility-auditor] | A=accepted/pass selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=11424.975 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=15515.67 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:review-report;life:review] rc=[selected-brand-governance-specialist,selected-playful-interface-specialist,selected-independent-accessibility-auditor,separate-isolated-work-unit-boundary-preserved,distinct-contexts-preserved] | fairness=[]
accounts-payable-cfo-separated | helpful=[accounts-payable-agent,chief-financial-officer] | A=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=12809.363 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=11182.952 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[domain-specialized-match,independent-review-required,separate-context-required] | fairness=[]
postgres-write-query-analysis | helpful=[database-optimizer] | A=accepted/pass selected=[database-optimizer] f1=1 ms=13296.94 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[database-optimizer] f1=1 ms=17539.301 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[domain-match-database-query-optimization,analysis-only-scope,measured-query-plan-findings-required,no-documentation,no-application-code-changes] | fairness=[]
clinical-legal-boundary-review | helpful=[clinical-evidence-agent,legal-document-review] | A=accepted/fail selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=21550.432 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=10172.602 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[clinical-evidence-agent-is-the-semantic-winner-for-source-grounded-clinical-trial-evidence-review,legal-document-review-is-the-semantic-winner-for-independent-review-of-supplied-legal-document-use,separate-isolated-contexts-preserve-specialist-independence,no-diagnosis-medical-billing-or-compliance-certification-requested] | fairness=[]

~~~

The immediate matched rerun of those three Agency failures again captured both
streams outside the repository. It finished in 77.534 seconds, returned exit
status 1, emitted 759,414 stdout bytes with SHA-256
`fdb2b48c45a387a0f68380f112eac406dbceddb737356443165098b3613177e4`,
and emitted zero stderr bytes with SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
Its bounded corpus fingerprint was
`sha256:965427cc5b7e3084840f2bb9841b5efced27d501ee20de07490dffae7d059686`;
the base-roster and allowed-agent fingerprints were unchanged. Every arm kept
the same provider, requested and actual model, receipt source, one-call count,
applied inference, and latency budget.

Agency passed 2/3, with precision 0.666667, recall 0.571429, F1 0.615385, 2/3
complete typed coverage, p50 9935.039 ms, p95/max 10107.692 ms, and zero
forbidden, ineligible, or conflict selections. Application integration and
active incident containment both recovered safely below budget. Clinical/legal
review instead failed closed on selection confidence at 10107.692 ms. The
bounded benchmark was invalid because the application-integration upstream arm
returned an invalid assignment row; it is not interpreted as an upstream loss.

~~~text
application-integration | helpful=[software-test-engineer,code-reviewer,application-integration-verifier] | A=accepted/pass selected=[minimal-change-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.75 ms=9935.039 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=21220.692 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-integration-verifier,code-reviewer,software-test-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream assignment row is invalid] | fairness=[application-integration:arm_error]
active-incident-containment | helpful=[incident-responder,incident-response-commander] | A=accepted/pass selected=[incident-responder] f1=0.666667 ms=7678.819 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[incident-responder,secrets-credential-hygiene-engineer] f1=0.5 ms=18016.901 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:analysis;life:discovery] rc=[active-credential-theft-incident,forensic-evidence-preservation,reversible-recovery,no-offensive-probing,distinct-specialist-contexts] | fairness=[]
clinical-legal-boundary-review | helpful=[clinical-evidence-agent,legal-document-review] | A=abstained/fail selected=[] f1=0 ms=10107.692 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:clinical-evidence-agent,legal-document-review;art:analysis,review-report;life:discovery,review] rc=[selection_confidence_too_low] | U=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=9472.361 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[domain-fit,independent-review,separate-contexts,non-diagnostic,non-certification] | fairness=[]

~~~

The immediate clinical/legal-only matched confirmation captured both streams
outside the repository and finished in 19.399 seconds. It returned exit status
0, emitted 709,673 stdout bytes with SHA-256
`359cedbd5b254dfafa1d758582e5038d6fe599be7ac03a0e7c284c5ffa29edda`,
and emitted zero stderr bytes with SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
The bounded corpus fingerprint was
`sha256:cb2a4b912f8c4373dabc86a0c295ed3d9430b95dd52fd870cfe8bd7fb13e32a1`;
the base-roster and allowed-agent fingerprints were unchanged. The benchmark
was valid. Agency selected `clinical-evidence-agent` and
`legal-document-review`, achieved complete typed coverage, precision,
recall, and F1 of 1.000000, completed in 7810.931 ms, and had zero forbidden,
ineligible, or conflict selections.

~~~text
clinical-legal-boundary-review | helpful=[clinical-evidence-agent,legal-document-review] | A=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=7810.931 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=10581.155 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[clinical-evidence-agent-directlymatches-clinical-trial-evidence-review,legal-document-review-directlymatches-legal-document-review,separate-contexts-for-independent-specialists,excluded-diagnosis-billing-and-certification-scopes] | fairness=[]

~~~

Both complete-run latency failures recovered below the unchanged gate, the
active-incident abstention recovered, and the bounded clinical confidence
abstention passed immediately on its next matched confirmation. No governed
general semantic defect was established, so no product or policy code changed.
Changing planner normalization, staffing thresholds, typed coverage, response
parsing, the latency gate, or the one-call budget would tune policy to variable
model output. No comparative superiority claim is made.

The exact blocker remains that no single complete corpus has yet shown all 19
Agency arms passing together, while malformed upstream provider arms continue
to invalidate comparative interpretation. The next bounded package therefore
stays in matched selection and starts with one unchanged complete corpus. It
must preserve the same stream-capture, projection, receipt, fingerprint,
safety, disclosure, and malformed-arm discipline. Contractor lifecycle,
untouched-corpus statistics, activation proof, superiority claims, and blinded
completed-outcome trials remain deferred.

The next matched-selection recovery package started from checkpoint `46834c2`
with the unchanged 15000 ms cold gate, one-call fast budget, Windows platform,
`codex-subscription` provider, requested and actual `gpt-5.6-luna` model, and
low reasoning effort. Stdout and stderr were captured as separate byte streams
outside the repository before parsing. The complete process finished in
429.572 seconds, returned exit status 1, emitted 1,179,064 stdout bytes with
SHA-256
`0a0a8d2baf81f75e2fb57c7b52b37fb2949e7c1f5d6e30cc6404b84886289914`,
and emitted zero stderr bytes with the empty-stream SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

The corpus fingerprint remained
`sha256:7358cb9422cef681dc7d85323160652029792916c2ea74d81514df6cfebbba38`,
the base-roster fingerprint remained
`sha256:c80b7422124f5935d3956ec48d6d0fffca15e7c23ebd155475998c7418e4f795`,
and the allowed-agent fingerprint remained
`sha256:88d310bad3716357bf49a74c53a873236cf9c549b878c3c190b4affebead7765`.
All 38 arms recorded provider `codex-subscription`, requested and actual model
`gpt-5.6-luna`, receipt source `cli.explicit_model_argument`, one call,
applied inference, and the unchanged 15000 ms latency budget.

Agency passed 17/19, with precision 0.851852, recall 0.793103, F1 0.821429,
17/19 complete typed coverage, p50 8679.513 ms, p95/max 18182.802 ms, and zero
forbidden, ineligible, or conflict selections. Descriptive upstream aggregates
were 6/19 passing, precision 0.833333, recall 0.517241, F1 0.638298, 8/19
complete typed coverage, p50 12281.164 ms, p95/max 26486.971 ms, and zero
scored safety selections. The benchmark was invalid because the backend and
application-integration upstream arms returned invalid assignment rows, the
installed-release upstream arm returned unknown disabled shadows, and the
broad-application upstream arm returned another invalid assignment row. Those
four malformed arms remain errors below and are not interpreted as upstream
losses.

The two Agency failures were fail-closed non-safety outcomes. The broad
Python/TypeScript application abstained on selection confidence at 18182.802
ms. PostgreSQL query analysis abstained because the required lifecycle owner
was missing at 5276.058 ms. Neither selected a forbidden, ineligible, or
conflicting worker. The exact compact projection follows:

~~~text
python-production-change | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=8262.928 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=11465.137 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[python-bug-matched-to-python-application-engineer,failure-path-tests-matched-to-software-test-engineer,independent-review-matched-to-code-reviewer,separate-contexts-preserved] | fairness=[]
typescript-production-change | helpful=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=5458.943 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[typescript-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=11610.823 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[typescript-implementation-match,test-coverage-required,independent-review-required] | fairness=[]
backend-service-change | helpful=[backend-service-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[backend-service-engineer,software-test-engineer,application-integration-verifier,code-reviewer,test-results-analyzer] f1=0.888889 ms=10318.277 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=16617.998 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:backend-service-engineer,code-reviewer,software-test-engineer,test-results-analyzer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream assignment row is invalid] | fairness=[backend-service-change:arm_error]
installed-cross-platform-release | helpful=[software-test-engineer,code-reviewer,cross-platform-release-verifier] | A=accepted/pass selected=[cross-platform-installer-engineer,software-test-engineer,code-reviewer,test-results-analyzer,cross-platform-release-verifier] f1=0.75 ms=8953.667 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=15312.763 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,cross-platform-release-verifier,software-test-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[installed-cross-platform-release:arm_error]
application-integration | helpful=[software-test-engineer,code-reviewer,application-integration-verifier] | A=accepted/pass selected=[minimal-change-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.75 ms=8640.221 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=17618.665 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-integration-verifier,code-reviewer,software-test-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream assignment row is invalid] | fairness=[application-integration:arm_error]
application-observability | helpful=[application-observability-engineer,software-test-engineer,code-reviewer] | A=accepted/pass selected=[application-observability-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=0.857143 ms=8635.393 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[application-observability-engineer,software-test-engineer,code-reviewer] f1=1 ms=13464.156 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[selected-specialist-for-production-observability-implementation,selected-specialist-for-executable-failure-path-testing,selected-independent-reviewer,separate-contexts-for-separately-spawned-specialists] | fairness=[]
documentation-change | helpful=[technical-writer,code-reviewer] | A=accepted/pass selected=[technical-writer,code-reviewer] f1=1 ms=6384.656 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[technical-writer,code-reviewer] f1=1 ms=9439.413 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:documentation] rc=[technical-writer-selected-for-repository-documentation-rewrite,code-reviewer-selected-for-independent-accuracy-review,separate-contexts-preserved-for-independent-specialists] | fairness=[]
selection-safety-review | helpful=[selection-safety-critic] | A=accepted/pass selected=[selection-safety-critic] f1=1 ms=5566.646 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[agents-orchestrator,selection-safety-critic] f1=0.666667 ms=14080.569 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[selection-safety-critic-is-the-semantic-match-for-workforce-selection-audit,agents-orchestrator-provides-required-resident-routing-coordination,specialist-contexts-are-isolated-and-distinct] | fairness=[]
repository-security-patch-review | helpful=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] | A=accepted/pass selected=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor,senior-secops-engineer] f1=0.857143 ms=9029.215 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[codebase-archaeologist,code-reviewer,application-security-engineer] f1=0.333333 ms=11901.38 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:ai-generated-code-security-auditor,codebase-onboarding-engineer] rc=[matched-read-only-repository-review,separate-code-path-correctness-and-security-workstreams,all-selected-agent-ids-are-allowed-and-enabled,distinct-contexts-for-independent-specialists] | fairness=[]
runtime-routing-integration-failure | helpful=[application-integration-verifier,selection-safety-critic,test-results-analyzer] | A=accepted/pass selected=[codebase-onboarding-engineer,application-integration-verifier,test-results-analyzer,selection-safety-critic] f1=0.857143 ms=10263.132 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[multi-agent-systems-architect,application-integration-verifier,selection-safety-critic] f1=0.666667 ms=15201.504 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer] rc=[direct-qualified-specialists-selected,separate-contexts-for-specialists,no-disabled-semantic-winner-present] | fairness=[]
active-incident-containment | helpful=[incident-responder,incident-response-commander] | A=accepted/pass selected=[incident-responder] f1=0.666667 ms=9635.936 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[incident-responder,secrets-credential-hygiene-engineer] f1=0.5 ms=13483.344 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:analysis;life:discovery] rc=[active-security-incident,forensic-evidence-preservation,reversible-recovery-plan,defensive-scope-only] | fairness=[]
lsp-incremental-index | helpful=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=8069.746 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[lsp-index-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=12238.949 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[exact-domain-match,separate-testing-specialist,independent-review-required] | fairness=[]
disabled-lsp-winner | helpful=[lsp-index-engineer] | A=abstained/pass selected=[] f1=0 ms=9474.199 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[no_safe_sufficient_team,recruiter_abstained,selection_margin_too_low] | U=accepted/pass selected=[codebase-archaeologist] f1=0 ms=11165.112 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[best-semantic-match-disabled,fallback-selected-by-neighboring-capability,safest-next-step-is-read-only-evidence-based-diagnosis-before-any-indexer-mutation] | fairness=[]
incidental-finance-language | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=8152.997 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=15859.914 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[bounded-python-parser-implementation,failure-path-test-coverage-required,independent-review-required,financial-analysis-explicitly-out-of-scope] | fairness=[]
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=abstained/fail selected=[] f1=0 ms=18182.802 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor,application-integration-verifier,application-observability-engineer,code-reviewer,cross-platform-release-verifier,python-application-engineer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[selection_confidence_too_low] | U=error/fail selected=[] f1=0 ms=26486.971 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor,application-integration-verifier,application-observability-engineer,code-reviewer,cross-platform-release-verifier,python-application-engineer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[provider_response_contract_invalid,upstream assignment row is invalid] | fairness=[broad-python-typescript-application:arm_error]
brand-and-whimsy-separated | helpful=[brand-guardian,whimsy-injector,accessibility-auditor] | A=accepted/pass selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=9976.599 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=12281.164 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:review-report;life:review] rc=[specialist-match,required-dependency-selected,independent-context-isolation,brand-whimsy-conflict-avoided] | fairness=[]
accounts-payable-cfo-separated | helpful=[accounts-payable-agent,chief-financial-officer] | A=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=8679.513 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=10512.968 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[domain-fit-accounts-payable,domain-fit-chief-financial-officer,separate-contexts-preserve-independence,same-context-conflict-avoided] | fairness=[]
postgres-write-query-analysis | helpful=[database-optimizer] | A=abstained/fail selected=[] f1=0 ms=5276.058 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:database-optimizer;art:analysis;life:discovery] rc=[lifecycle_owner_missing_from_required] | U=accepted/pass selected=[database-optimizer] f1=1 ms=9309.46 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[exact-agent-id-present-in-allowed-agent-ids,semantic-match-database-query-optimization,analysis-only-output-request,no-documentation-or-implementation-required,isolated-context-required] | fairness=[]
clinical-legal-boundary-review | helpful=[clinical-evidence-agent,legal-document-review] | A=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=9252.998 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=11004.034 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[clinical-evidence-agent-is-semantic-match,legal-document-review-is-semantic-match,separate-contexts-required-for-independent-specialists] | fairness=[]
~~~

The immediate two-case matched rerun again captured both streams before
parsing. It finished in 60.727 seconds, returned exit status 1, emitted 738,536
stdout bytes with SHA-256
`9906dbd16c2cdee02bd73d97bfccce599d4205fd7f2b9e7e076d74a22fe9bee3`,
and emitted zero stderr bytes with SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
Its bounded corpus fingerprint was
`sha256:e761fa950399ca55e6b697e98eb62a0824dc2ecdd83f15e2b59c8a377de54e29`;
the roster, allowed-agent, provider, model, receipt, call-count, inference, and
latency-budget bindings were unchanged.

Agency had complete typed coverage and precision, recall, and F1 of 1.000000
for both cases, with zero safety defects. PostgreSQL recovered and passed in
5523.005 ms. The broad application selected the exact nine helpful workers but
missed the unchanged gate by 9.149 ms, so Agency passed 1/2; p50 was 10266.077
ms and p95/max was 15009.149 ms. The benchmark was invalid because the broad
upstream arm returned unknown disabled shadows.

~~~text
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=accepted/fail selected=[python-application-engineer,typescript-application-engineer,application-observability-engineer,software-test-engineer,accessibility-auditor,code-reviewer,application-integration-verifier,test-results-analyzer,cross-platform-release-verifier] f1=1 ms=15009.149 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=23472.542 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor,application-integration-verifier,application-observability-engineer,code-reviewer,cross-platform-release-verifier,python-application-engineer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[broad-python-typescript-application:arm_error]
postgres-write-query-analysis | helpful=[database-optimizer] | A=accepted/pass selected=[database-optimizer] f1=1 ms=5523.005 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[database-optimizer] f1=1 ms=15583.699 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[exact-domain-match,measured-query-plan-analysis,read-only-findings-only,no-documentation-or-code-change-required] | fairness=[]
~~~

The first broad-only confirmation finished in 39.152 seconds, returned exit
status 1, emitted 719,242 stdout bytes with SHA-256
`3a3dd400fb38c828bf1e1d620d3dac03be5ea7868b6cc170f7be3fb5e7223951`,
and emitted zero stderr bytes with the empty-stream hash. The bounded benchmark
was valid. Agency again selected the exact nine-worker team with complete typed
coverage and zero safety defects, but exceeded the unchanged gate at 15867.544
ms:

~~~text
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=accepted/fail selected=[application-observability-engineer,python-application-engineer,typescript-application-engineer,software-test-engineer,accessibility-auditor,application-integration-verifier,test-results-analyzer,cross-platform-release-verifier,code-reviewer] f1=1 ms=15867.544 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,frontend-developer,software-test-engineer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-installer-engineer,cross-platform-release-verifier] f1=0.705882 ms=22242.246 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,test-results-analyzer,typescript-application-engineer;art:review-report;life:review] rc=[production-python-api-matched-to-python-application-engineer,typescript-dashboard-matched-to-frontend-developer,failure-path-testing-matched-to-software-test-engineer,accessibility-review-matched-to-accessibility-auditor,observability-matched-to-application-observability-engineer,independent-integration-matched-to-application-integration-verifier,windows-linux-installation-matched-to-cross-platform-installer-engineer,windows-linux-release-evidence-matched-to-cross-platform-release-verifier] | fairness=[]
~~~

The second broad-only confirmation finished in 43.600 seconds, returned exit
status 1, emitted 713,485 stdout bytes with SHA-256
`6c66a6a5ec6fb78bd3177eaca8521699c5917c51ce52a3226d39cda5ac0a16e0`,
and emitted zero stderr bytes with the empty-stream hash. It retained the same
bounded corpus fingerprint
`sha256:0a7f6891b7b624d01956ab36c32a212147e05315ad3686ebf4995eaa4c97df1a`
as the first confirmation and all other parity bindings remained unchanged.
Agency selected the exact team, achieved complete typed coverage and
precision, recall, and F1 of 1.000000, and passed below budget in 10081.549 ms
with zero safety defects. The benchmark was invalid only because the upstream
arm returned an invalid assignment row:

~~~text
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=accepted/pass selected=[application-observability-engineer,python-application-engineer,typescript-application-engineer,software-test-engineer,accessibility-auditor,code-reviewer,application-integration-verifier,test-results-analyzer,cross-platform-release-verifier] f1=1 ms=10081.549 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=32475.623 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor,application-integration-verifier,application-observability-engineer,code-reviewer,cross-platform-release-verifier,python-application-engineer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[provider_response_contract_invalid,upstream assignment row is invalid] | fairness=[broad-python-typescript-application:arm_error]
~~~

Both complete-run Agency failures therefore passed under the same governed
controls in bounded confirmation. The broad application selected its exact
team in every bounded rerun, with cold latency moving from 15009.149 to
15867.544 to 10081.549 ms. That evidence establishes configured-provider
latency variance rather than a repeatable selection-semantic defect. No product
or policy code changed because changing planner normalization, staffing
thresholds, typed coverage, response parsing, the latency gate, or the one-call
budget would tune policy to variable model output. No comparative superiority
claim is made.

The exact blocker remains unchanged: no single complete corpus has yet shown
all 19 Agency arms safe and passing together, and malformed upstream provider
arms continue to invalidate comparative interpretation. The next bounded
package remains in matched selection and starts with another complete corpus
under the unchanged controls. Contractor lifecycle, untouched-corpus
statistics, exact activation, superiority claims, and blinded completed-outcome
trials remain deferred.

The next matched-selection recovery package started from checkpoint `624a0df`
with the unchanged 15000 ms cold gate, one-call fast budget, Windows platform,
`codex-subscription` provider, requested and actual `gpt-5.6-luna` model, and
low reasoning effort. Stdout and stderr were captured as separate raw byte
streams outside the repository before parsing. The complete process finished
in 457.161 seconds, returned exit status 1, emitted 1,185,651 stdout bytes with
SHA-256
`9fc0140ccc5cddd291ed6d67ea890d6c55d09b73b4dbee1ec6ad09946a40dc14`,
and emitted zero stderr bytes with the empty-stream SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

The corpus fingerprint remained
`sha256:7358cb9422cef681dc7d85323160652029792916c2ea74d81514df6cfebbba38`,
the base-roster fingerprint remained
`sha256:c80b7422124f5935d3956ec48d6d0fffca15e7c23ebd155475998c7418e4f795`,
and the allowed-agent fingerprint remained
`sha256:88d310bad3716357bf49a74c53a873236cf9c549b878c3c190b4affebead7765`.
All 38 arms recorded provider `codex-subscription`, requested and actual model
`gpt-5.6-luna`, receipt source `cli.explicit_model_argument`, one call, and the
unchanged 15000 ms latency budget. Every complete-run arm applied inference.

Agency passed 16/19, with precision 0.881356, recall 0.896552, F1 0.888889,
18/19 complete typed coverage, p50 8070.313 ms, p95/max 15204.514 ms, and zero
forbidden, ineligible, or conflict selections. Descriptive upstream aggregates
were 4/19 passing, precision 0.642857, recall 0.465517, F1 0.540000, 6/19
complete typed coverage, p50 12911.773 ms, p95/max 33796.038 ms, and zero
scored safety selections. The benchmark was invalid because the TypeScript and
broad-application upstream arms returned invalid assignment rows, while the
application-observability and incidental-finance upstream arms returned unknown
disabled shadows. Those four malformed arms remain errors below and are not
interpreted as upstream losses.

The three Agency failures were non-safety outcomes. Application observability
failed closed on selection confidence at 9951.087 ms. Runtime-routing
integration selected its complete typed team but exceeded the unchanged gate by
204.514 ms at 15204.514 ms. The broad application selected eight of its nine
helpful workers but omitted `accessibility-auditor` at 10507.357 ms. The exact
compact projection follows:

~~~text
python-production-change | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=10712.774 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=33796.038 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[python-application-engineer-selected-for-python-implementation,software-test-engineer-selected-for-failure-path-test-code,code-reviewer-selected-for-independent-review,specialists-isolated-in-distinct-contexts] | fairness=[]
typescript-production-change | helpful=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=5714.146 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=14219.977 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream assignment row is invalid] | fairness=[typescript-production-change:arm_error]
backend-service-change | helpful=[backend-service-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[backend-service-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.888889 ms=7503.227 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[backend-service-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=11930.793 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[backend-service-engineer-is-the-best-fit-implementation-agent,software-test-engineer-is-the-best-fit-integration-test-specialist,code-reviewer-provides-independent-review,separate-contexts-required-for-isolated-specialists] | fairness=[]
installed-cross-platform-release | helpful=[software-test-engineer,code-reviewer,cross-platform-release-verifier] | A=accepted/pass selected=[cross-platform-installer-engineer,software-test-engineer,code-reviewer,test-results-analyzer,cross-platform-release-verifier] f1=0.75 ms=7579.457 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[cross-platform-installer-engineer,software-test-engineer,application-integration-verifier,cross-platform-release-verifier] f1=0.571429 ms=17406.113 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer;art:review-report;life:review] rc=[cross-platform-packaging16and16installed-release16verification16are16the16dominant16task16needs,installer16and16release-verifier16are16declared16complements,testing16and16integration16verification16cover16the16requested16test16and16review16gates,separate16context16ids16preserve16specialist16independence] | fairness=[]
application-integration | helpful=[software-test-engineer,code-reviewer,application-integration-verifier] | A=accepted/pass selected=[minimal-change-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.75 ms=7878.928 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[agents-orchestrator,frontend-developer,software-test-engineer,application-integration-verifier] f1=0.571429 ms=19705.722 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer;art:review-report] rc=[request-requires-implementation,request-requires-test-code,request-requires-independent-end-to-end-verification,software-test-engineer-complements-application-integration-verifier,separate-contexts-for-specialists] | fairness=[]
application-observability | helpful=[application-observability-engineer,software-test-engineer,code-reviewer] | A=abstained/fail selected=[] f1=0 ms=9951.087 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-observability-engineer,code-reviewer,software-test-engineer;art:implementation-change,review-report,test-code;life:implementation,review,testing] rc=[selection_confidence_too_low] | U=error/fail selected=[] f1=0 ms=22008.53 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-observability-engineer,code-reviewer,software-test-engineer;art:implementation-change,review-report,test-code;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[application-observability:arm_error]
documentation-change | helpful=[technical-writer,code-reviewer] | A=accepted/pass selected=[technical-writer,code-reviewer] f1=1 ms=6101.959 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[technical-writer,codebase-archaeologist] f1=0.5 ms=11394.639 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer;art:documentation] rc=[documentation-implementation-and-independent-technical-review,distinct-contexts-for-independent-specialists,all-selected-agent-ids-allowed] | fairness=[]
selection-safety-review | helpful=[selection-safety-critic] | A=accepted/pass selected=[selection-safety-critic] f1=1 ms=6179.576 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[agents-orchestrator,selection-safety-critic] f1=0.666667 ms=10955.601 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[request-is-workforce-selection-audit,selection-safety-critic-is-exact-semantic-match,separate-isolated-contexts-required,no-disabled-semantic-winner-evidenced] | fairness=[]
repository-security-patch-review | helpful=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] | A=accepted/pass selected=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] f1=1 ms=8900.083 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[codebase-archaeologist,code-reviewer,application-security-engineer] f1=0.333333 ms=11462.716 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:ai-generated-code-security-auditor,codebase-onboarding-engineer] rc=[repository-security-patch-review,read-only-scope,independent-specialist-contexts,affected-path-mapping,correctness-review,exploitability-audit] | fairness=[]
runtime-routing-integration-failure | helpful=[application-integration-verifier,selection-safety-critic,test-results-analyzer] | A=accepted/fail selected=[codebase-onboarding-engineer,selection-safety-critic,application-integration-verifier,test-results-analyzer] f1=0.857143 ms=15204.514 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[agents-orchestrator,multi-agent-systems-architect,codebase-archaeologist,application-integration-verifier,selection-safety-critic] f1=0.5 ms=19417.562 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer] rc=[resident-routing-required,routing-and-delegation-analysis,installed-hook-code-audit,authorized-local-integration-verification,independent-selection-safety-review,distinct-isolated-specialist-contexts] | fairness=[]
active-incident-containment | helpful=[incident-responder,incident-response-commander] | A=accepted/pass selected=[incident-responder] f1=0.666667 ms=11209.839 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[incident-responder,secrets-credential-hygiene-engineer,threat-detection-engineer] f1=0.4 ms=13049.576 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:analysis;life:discovery] rc=[active-security-incident,forensic-evidence-preservation,reversible-recovery,defensive-only-scope,separate-specialist-contexts] | fairness=[]
lsp-incremental-index | helpful=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=8041.584 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[lsp-index-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=12303.682 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[exact-agent-id-match,lsp-specialist-selected-for-language-server-indexing,failure-path-test-specialist-selected,independent-review-context-separated] | fairness=[]
disabled-lsp-winner | helpful=[lsp-index-engineer] | A=abstained/pass selected=[] f1=0 ms=8070.313 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[required_agents_missing,no_safe_sufficient_team,recruiter_abstained,selection_margin_too_low] | U=accepted/pass selected=[codebase-archaeologist,test-results-analyzer] f1=0 ms=11235.6 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[best-specialist-disabled,safe-fallback-to-read-only-code-path-diagnosis,preserve-cancellation-and-index-consistency-semantics-before-implementation] | fairness=[]
incidental-finance-language | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=8302.387 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=12911.773 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,python-application-engineer,software-test-engineer,test-results-analyzer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[incidental-finance-language:arm_error]
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=accepted/fail selected=[application-observability-engineer,python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer,cross-platform-release-verifier] f1=0.941176 ms=10507.357 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor] rc=[] | U=error/fail selected=[] f1=0 ms=22463.254 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor,application-integration-verifier,application-observability-engineer,code-reviewer,cross-platform-release-verifier,python-application-engineer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[provider_response_contract_invalid,upstream assignment row is invalid] | fairness=[broad-python-typescript-application:arm_error]
brand-and-whimsy-separated | helpful=[brand-guardian,whimsy-injector,accessibility-auditor] | A=accepted/pass selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=13187.276 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=16279.374 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:review-report;life:review] rc=[brand-governance-matched-to-brand-guardian,playful-interface-work-isolated-in-separate-context,accessibility-audit-selected-independently,whimsy-injector-requires-accessibility-auditor] | fairness=[]
accounts-payable-cfo-separated | helpful=[accounts-payable-agent,chief-financial-officer] | A=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=7683.267 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=9227.583 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:review-report] rc=[specialized-match,independent-context-separation,same-context-conflict-avoided,exact-allowed-agent-ids] | fairness=[]
postgres-write-query-analysis | helpful=[database-optimizer] | A=accepted/pass selected=[database-optimizer] f1=1 ms=5281.224 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[database-optimizer] f1=1 ms=7719.877 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[database-query-performance,measured-execution-plan-findings-only,no-code-or-documentation-change] | fairness=[]
clinical-legal-boundary-review | helpful=[clinical-evidence-agent,legal-document-review] | A=accepted/pass selected=[healthcare-innovation-strategist,legal-document-review,clinical-evidence-agent] f1=0.8 ms=10135.285 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=9355.685 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[domain-match-clinical-evidence,domain-match-legal-document-review,independent-specialists-required,separate-contexts-for-specialists,no-diagnosis,no-medical-billing,no-compliance-certification] | fairness=[]
~~~

The immediate matched rerun of those three Agency failures again captured both
streams outside the repository. It finished in 85.899 seconds, returned exit
status 1, emitted 765,327 stdout bytes with SHA-256
`a11f96b07ca9114c590c1c42318a0a10eb0282791dc87735c1d123820be8d7e5`,
and emitted zero stderr bytes with SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
Its bounded corpus fingerprint was
`sha256:1e125ccdfeef60be2768243dce932ca16dab5c1ca56c5c77468a2184d440af34`;
the roster, allowed-agent, provider, model, receipt, call-count, and latency
bindings were unchanged.

Runtime routing recovered with complete typed coverage at 8344.524 ms. The
broad application selected its exact nine-worker team and recovered with
complete typed coverage at 12212.504 ms. Application observability remained
fail-closed at 9806.569 ms with `workforce_call_budget_exhausted`; that arm
truthfully recorded that staffing inference was not applied after the one-call
budget was exhausted. Agency therefore passed 2/3, with precision 0.923077,
recall 0.800000, F1 0.857143, 2/3 complete typed coverage, p50 9806.569 ms,
p95/max 12212.504 ms, and zero forbidden, ineligible, or conflict selections.
The benchmark was invalid because the observability Agency arm was non-inferred,
the observability upstream arm returned an invalid assignment row, and the
broad upstream arm returned another invalid assignment row. None is treated as
comparative evidence.

~~~text
application-observability | helpful=[application-observability-engineer,software-test-engineer,code-reviewer] | A=abstained/fail selected=[] f1=0 ms=9806.569 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-observability-engineer,code-reviewer,software-test-engineer;art:implementation-change,review-report,test-code;life:implementation,review,testing] rc=[workforce_call_budget_exhausted] | U=error/fail selected=[] f1=0 ms=16983.682 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-observability-engineer,code-reviewer,software-test-engineer;art:implementation-change,review-report,test-code;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream assignment row is invalid] | fairness=[application-observability:arm_error,application-observability:inference_not_applied]
runtime-routing-integration-failure | helpful=[application-integration-verifier,selection-safety-critic,test-results-analyzer] | A=accepted/pass selected=[codebase-onboarding-engineer,application-integration-verifier,test-results-analyzer,selection-safety-critic] f1=0.857143 ms=8344.524 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[multi-agent-systems-architect,application-integration-verifier,selection-safety-critic] f1=0.666667 ms=15663.56 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer] rc=[matched-routing-architecture-to-multi-agent-systems-architect,matched-live-integration-testing-to-application-integration-verifier,matched-independent-staffing-audit-to-selection-safety-critic,separate-contexts-required-for-independent-specialists] | fairness=[]
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=accepted/pass selected=[python-application-engineer,typescript-application-engineer,application-observability-engineer,software-test-engineer,accessibility-auditor,code-reviewer,application-integration-verifier,test-results-analyzer,cross-platform-release-verifier] f1=1 ms=12212.504 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=21744.929 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor,application-integration-verifier,application-observability-engineer,code-reviewer,cross-platform-release-verifier,python-application-engineer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[provider_response_contract_invalid,upstream assignment row is invalid] | fairness=[broad-python-typescript-application:arm_error]
~~~

The immediate observability-only matched confirmation captured both streams
outside the repository and finished in 22.685 seconds. It returned exit status
0, emitted 711,961 stdout bytes with SHA-256
`466a9ed105cf6ab12ba47ce85aef26e969a657011c4a78f96c6f3e496a0b3426`,
and emitted zero stderr bytes with the empty-stream hash. The bounded corpus
fingerprint was
`sha256:60d345ffad05b16064c57238d6101bd511a3d0f396c34eebac5bf6dc49c0ff50`;
all other parity bindings remained unchanged. The benchmark was valid. Agency
selected the required observability, test, and review workers plus
`test-results-analyzer`, achieved complete typed coverage, precision 0.750000,
recall 1.000000, F1 0.857143, and passed at 9885.533 ms with zero safety
defects:

~~~text
application-observability | helpful=[application-observability-engineer,software-test-engineer,code-reviewer] | A=accepted/pass selected=[application-observability-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=0.857143 ms=9885.533 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[application-observability-engineer,software-test-engineer,application-integration-verifier,code-reviewer] f1=0.857143 ms=11771.869 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[direct-semantic-fit,implementation-testing-review-coverage,independent-context-isolation,complementary-specialist-pairing] | fairness=[]
~~~

All three complete-run Agency failures therefore passed under the same governed
controls in bounded confirmation. Runtime routing recovered below budget, the
broad application restored its exact team, and observability recovered on the
second bounded confirmation. No governed general semantic defect was
established, so no product or policy code changed. Changing planner
normalization, staffing thresholds, typed coverage, response parsing, the
latency gate, or the one-call budget would tune policy to variable model output.
No comparative superiority claim is made.

The exact blocker remains unchanged: no single complete corpus has yet shown
all 19 Agency arms safe and passing together, and malformed upstream provider
arms continue to invalidate comparative interpretation. The next bounded
package remains in matched selection and starts with another complete corpus
under the unchanged controls. Contractor lifecycle, untouched-corpus
statistics, exact activation, superiority claims, and blinded completed-outcome
trials remain deferred.

### Still required before AR-119 can close

- Complete and pass the implemented matched held-out selection benchmark
  against the pinned source-visible upstream Agency Agents baseline. Obtain one
  complete corpus in which all 19 Agency arms are safe and passing, and retain
  every malformed or timed-out upstream arm as a benchmark-validity failure.
  Dangerous, forbidden, incompatible, disabled, and weak incidental matches
  remain explicit regressions, not aggregate-score noise.
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
lifecycle work. Start with one complete 19-case run from this handoff
checkpoint, using the unchanged 15000 ms cold budget and one-call fast setting:

```text
.\.venv\Scripts\agency.exe eval upstream-selection --all --platform windows --confirm-live-inference "RUN MATCHED UPSTREAM SELECTION EVAL" --json
```

Retain the same exact compact projection, provider/model receipts, parity
bindings, per-case selections, safety counts, disabled disclosures, reason
codes, and every malformed or timed-out arm. If an Agency arm fails, use only
bounded case reruns and governed general semantics before another complete
run; do not weaken typed coverage, add a scenario route, reinterpret a
malformed arm as evidence, raise the 15000 ms gate, or increase the one-call
fast budget. If every Agency arm is safe and passing but the benchmark is
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
