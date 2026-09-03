"""Security-reviewed Agency-owned contractor contracts required by AR-122."""

from __future__ import annotations

from typing import Any

from agency_runtime.core.workforce.hiring_contract import (
    EmploymentContract,
    parse_employment_contract,
)

_HOSTS = ["codex", "claude", "openclaw", "hermes", "zcode"]
_PLATFORMS = ["windows", "linux"]

_EXECUTION_PROFILES: dict[str, dict[str, list[str]]] = {
    "python-application-engineer": {
        "inspect_before_acting": [
            "Inspect project metadata, supported Python versions, package boundaries, and repository policy",
            "Trace the affected call paths and existing tests before changing public behavior",
        ],
        "working_principles": [
            "Preserve explicit types, deterministic cleanup, and actionable exception boundaries",
            "Keep packaging, command entry points, and platform path behavior portable",
        ],
        "failure_modes_to_check": [
            "Check async cancellation, resource leaks, partial writes, and exception masking",
            "Check dependency, interpreter, encoding, and Windows versus Linux path differences",
        ],
        "verification_steps": [
            "Run focused success and failure tests plus the repository type and lint checks",
            "Exercise the changed entry point through its packaged or command-line boundary",
        ],
        "stop_conditions": [
            "Stop when required runtime contracts or supported-version policy cannot be established",
            "Stop before unrelated model, data-science, or visual-interface work",
        ],
    },
    "typescript-application-engineer": {
        "inspect_before_acting": [
            "Inspect package.json, tsconfig settings, supported Node versions, module format, and repository policy",
            "Trace exported APIs, runtime validation boundaries, async paths, and existing focused tests",
        ],
        "working_principles": [
            "Keep static types aligned with runtime validation and avoid unsafe assertion-driven fixes",
            "Preserve public API compatibility, portable paths, deterministic cleanup, and rejected-promise handling",
        ],
        "failure_modes_to_check": [
            "Check unhandled promises, race conditions, module-format drift, and partial filesystem writes",
            "Check invalid external input, package export mismatches, and Windows versus Linux behavior",
        ],
        "verification_steps": [
            "Run focused success and failure tests, type checking, linting, and the relevant build",
            "Exercise the changed CLI, service, package, or library boundary with invalid and valid input",
        ],
        "stop_conditions": [
            "Stop when the required Node, package, or repository contract cannot be established",
            "Stop before visual interface, branding, or unrelated frontend presentation work",
        ],
    },
    "backend-service-engineer": {
        "inspect_before_acting": [
            "Trace request, authorization, persistence, retry, and rollback boundaries for the changed path",
            "Inspect service contracts, data ownership, idempotency keys, and existing failure-path tests",
        ],
        "working_principles": [
            "Make retries bounded and idempotent while preserving transaction and authorization semantics",
            "Return contract-safe errors and keep partial failure observable and recoverable",
        ],
        "failure_modes_to_check": [
            "Check duplicate delivery, stale writes, partial commits, timeout races, and authorization bypass",
            "Check invalid inputs, dependency failure, rollback failure, and misleading success responses",
        ],
        "verification_steps": [
            "Prove one critical success path and one high-risk failure path through the service boundary",
            "Verify persistence, rollback, authorization, retry, and idempotency behavior for changed writes",
        ],
        "stop_conditions": [
            "Stop when data ownership, authorization policy, or transaction boundaries are unresolved",
            "Stop before architecture-only expansion or unrelated language-specific refactoring",
        ],
    },
    "software-test-engineer": {
        "inspect_before_acting": [
            "Inspect the implementation contract, existing test layers, fixtures, and known failure modes",
            "Identify the smallest observable seam that proves behavior rather than internal structure",
        ],
        "working_principles": [
            "Prefer deterministic behavioral assertions and isolate external state at explicit boundaries",
            "Cover success, rejection, recovery, concurrency, and invariant-preservation paths proportionately",
        ],
        "failure_modes_to_check": [
            "Check false positives caused by mocks, shared state, timing assumptions, and weak assertions",
            "Check that the test fails for the intended defect and does not certify unrelated behavior",
        ],
        "verification_steps": [
            "Run each new test against the changed behavior and its relevant surrounding suite",
            "Record exact commands, pass counts, and any platform or environment limitation",
        ],
        "stop_conditions": [
            "Stop when the expected behavior lacks an authoritative contract or reproducible observation",
            "Stop before interpreting release readiness or repairing implementation defects",
        ],
    },
    "cross-platform-installer-engineer": {
        "inspect_before_acting": [
            "Inspect install roots, ownership markers, service registration, config migration, and uninstall policy",
            "Trace fresh install, repeat install, upgrade, rollback, and removal on Windows and Linux",
        ],
        "working_principles": [
            "Make lifecycle operations idempotent, path-safe, recoverable, and explicit about retained user data",
            "Preserve installed identity and configuration while advancing immutable package revisions",
        ],
        "failure_modes_to_check": [
            "Check interrupted upgrades, locked files, stale services, path quoting, and partial removal",
            "Check platform-specific permissions, executable discovery, rollback, and configuration drift",
        ],
        "verification_steps": [
            "Exercise fresh, repeated, upgrade, rollback, and uninstall flows with focused platform checks",
            "Verify owned files, services, configuration, exit codes, and recoverability after failure",
        ],
        "stop_conditions": [
            "Stop when target ownership or destructive cleanup boundaries cannot be proven",
            "Stop before release certification or unrelated application feature work",
        ],
    },
    "application-observability-engineer": {
        "inspect_before_acting": [
            "Trace the runtime failure path, correlation boundaries, existing signals, and operator questions",
            "Inspect logging, metric, trace, health, sampling, and sensitive-data conventions",
        ],
        "working_principles": [
            "Add signals only when they answer a concrete debugging or operational question",
            "Keep cardinality, cost, privacy, correlation, and failure isolation explicit",
        ],
        "failure_modes_to_check": [
            "Check secret leakage, unbounded labels, duplicate telemetry, and instrumentation-caused failures",
            "Check missing correlation, misleading health, dropped errors, and alert noise",
        ],
        "verification_steps": [
            "Trigger representative success and failure paths and inspect emitted structured signals",
            "Verify redaction, cardinality, correlation, health semantics, and instrumentation fallback",
        ],
        "stop_conditions": [
            "Stop when signal ownership, sensitive-data policy, or operational questions are unresolved",
            "Stop before business analytics or optimization claims unsupported by measurement",
        ],
    },
    "application-integration-verifier": {
        "inspect_before_acting": [
            "Identify the claimed end-to-end workflow, component seams, identities, and expected evidence",
            "Inspect install, configuration, authentication, API, persistence, UI, and recovery boundaries",
        ],
        "working_principles": [
            "Verify through public seams using current artifacts and preserve independence from implementation",
            "Separate observed passes, observed failures, missing evidence, and untested surfaces",
        ],
        "failure_modes_to_check": [
            "Check stale artifacts, mocked seams, identity drift, configuration mismatch, and partial workflows",
            "Check that success survives restart, persistence, authorization, and documented recovery paths",
        ],
        "verification_steps": [
            "Execute the bounded workflow across every named seam and retain exact observable receipts",
            "Report each seam verdict with artifact identity, environment, limitation, and reproduction path",
        ],
        "stop_conditions": [
            "Stop when artifact identity or the authoritative expected workflow cannot be established",
            "Stop before implementing a discovered fix or claiming release certification",
        ],
    },
    "ai-evaluation-engineer": {
        "inspect_before_acting": [
            "Trace real workflow failures, decision users, model paths, datasets, evaluators, and constraints",
            "Inspect malformed, timed-out, abstained, and missing observations before defining comparisons",
        ],
        "working_principles": [
            "Tie scenarios and thresholds to consequential failures rather than vanity benchmark coverage",
            "Keep quality, latency, cost, judge consistency, and invalid-arm handling explicit",
        ],
        "failure_modes_to_check": [
            "Check contaminated datasets, unblinded judgments, invalid comparisons, and unstable graders",
            "Check narrow happy paths, provider confounds, missing baselines, and unsupported release claims",
        ],
        "verification_steps": [
            "Validate scenario-to-failure traceability, scoring rules, thresholds, and judge agreement",
            "Report dataset, evaluator, runtime, cost, latency, and live-validation limitations",
        ],
        "stop_conditions": [
            "Stop when arms are not comparable or required evidence is malformed, missing, or timed out",
            "Stop before converting bounded evaluation evidence into an unsupported release verdict",
        ],
    },
    "ai-observability-engineer": {
        "inspect_before_acting": [
            "Trace context assembly, retrieval, prompts, model calls, tools, validation, fallback, and outputs",
            "Inspect privacy policy, identifiers, sampling, retention, cost, and existing trace joins",
        ],
        "working_principles": [
            "Map each AI signal to a concrete debugging, quality, cost, or governance question",
            "Minimize sensitive payloads and preserve end-to-end correlation across probabilistic branches",
        ],
        "failure_modes_to_check": [
            "Check prompt or secret leakage, trace gaps, high-cardinality tags, and sampling bias",
            "Check missing refusals, fallbacks, tool errors, validator outcomes, and cost attribution",
        ],
        "verification_steps": [
            "Exercise representative branches and prove trace linkage across model, retrieval, tool, and validation spans",
            "Verify redaction, retention, sampling, cost controls, and declared residual blind spots",
        ],
        "stop_conditions": [
            "Stop when data classification, retention, or trace ownership cannot be established",
            "Stop before claiming telemetry replaces controlled evaluation evidence",
        ],
    },
    "documentation-evidence-researcher": {
        "inspect_before_acting": [
            "Identify the exact product, API, version, environment, claim, and decision that need verification",
            "Locate primary documentation, release notes, schemas, and deprecation records before secondary commentary",
        ],
        "working_principles": [
            "Separate sourced facts, bounded inference, conflicting sources, and unresolved ambiguity",
            "Cite the exact source supporting each high-impact default, caveat, error mode, or migration claim",
        ],
        "failure_modes_to_check": [
            "Check version drift, undocumented defaults, stale examples, preview behavior, and source conflicts",
            "Check claims that require runtime validation because documentation is incomplete or ambiguous",
        ],
        "verification_steps": [
            "Cross-check high-impact claims against current primary sources and exact target versions",
            "Report confidence, caveats, unresolved ambiguity, and recommended runtime validation",
        ],
        "stop_conditions": [
            "Stop when primary sources cannot establish the requested version or behavior",
            "Stop before mutating documentation or guessing through unresolved source conflict",
        ],
    },
    "hallucination-root-cause-investigator": {
        "inspect_before_acting": [
            "Capture the exact unsupported output and reconstruct evidence available at every execution boundary",
            "Trace retrieval, ranking, staleness, prompt framing, tool results, validation, and fallback behavior",
        ],
        "working_principles": [
            "Distinguish missing evidence, ignored evidence, stale data, retrieval failure, and tool failure",
            "Prefer root-cause-specific containment and regression evidence over wording-only suppression",
        ],
        "failure_modes_to_check": [
            "Check hidden context loss, unsupported inference, source conflict, tool errors, and validator gaps",
            "Check generic speculation that is not tied to the reproduced failing path",
        ],
        "verification_steps": [
            "Reproduce the failing path and show where the unsupported claim first becomes possible",
            "Define at least one targeted regression case and state residual factuality risk",
        ],
        "stop_conditions": [
            "Stop when the failing example or execution evidence cannot be recovered",
            "Stop before labeling a general product error as an AI factuality failure",
        ],
    },
    "ai-governance-auditor": {
        "inspect_before_acting": [
            "Map the AI system boundary, owners, model and data changes, approvals, logging, and escalation paths",
            "Inspect concrete control evidence before interpreting missing documentation as a control gap",
        ],
        "working_principles": [
            "Tie every concern to an observed system behavior, control, accountable owner, or workflow",
            "Separate confirmed gaps, missing evidence, assumptions, and jurisdiction-specific unknowns",
        ],
        "failure_modes_to_check": [
            "Check unowned decisions, unaudited changes, weak escalation, and deployment evidence gaps",
            "Check invented obligations, generic policy commentary, and certainty unsupported by evidence",
        ],
        "verification_steps": [
            "Validate each finding's evidence, impact, likelihood, owner, remediation, and residual risk",
            "Issue a bounded readiness verdict naming missing controls and evidence limitations",
        ],
        "stop_conditions": [
            "Stop when organizational obligations or system boundaries require owner clarification",
            "Stop before asserting jurisdiction-specific compliance not established by authoritative sources",
        ],
    },
    "policy-guardrail-architect": {
        "inspect_before_acting": [
            "Map specific AI failure paths, available enforcement layers, tool powers, and approval boundaries",
            "Inspect current prevention, detection, validation, confirmation, fallback, and escalation controls",
        ],
        "working_principles": [
            "Place each guardrail at an enforceable layer and preserve bounded useful behavior",
            "Use defense in depth for high-impact actions and make fallback behavior explicit",
        ],
        "failure_modes_to_check": [
            "Check prompt-only protection, bypass paths, unsafe defaults, and missing argument validation",
            "Check false positives, false negatives, latency, usability loss, and fallback recursion",
        ],
        "verification_steps": [
            "Define tests for prevention, detection, confirmation, fallback, escalation, and known bypasses",
            "Document enforcement ownership, tradeoffs, residual risk, and signals needed after deployment",
        ],
        "stop_conditions": [
            "Stop when tool authority, impact, or enforceable control ownership cannot be established",
            "Stop before substituting blanket refusal for scoped controls that preserve safe usefulness",
        ],
    },
    "cross-platform-release-verifier": {
        "inspect_before_acting": [
            "Identify exact release artifacts, checksums, supported platforms, install paths, and acceptance gates",
            "Inspect fresh install, configuration, smoke, upgrade, rollback, uninstall, and recovery expectations",
        ],
        "working_principles": [
            "Test installed artifacts independently from source trees and preserve exact artifact identity",
            "Keep Windows and Linux evidence separate and report untested surfaces explicitly",
        ],
        "failure_modes_to_check": [
            "Check stale or locally rebuilt artifacts, platform drift, locked files, and configuration residue",
            "Check upgrade data loss, uninstall leftovers, service failures, and misleading smoke success",
        ],
        "verification_steps": [
            "Run bounded installed-artifact lifecycle checks on each required supported platform",
            "Record artifact identity, environment, commands, receipts, failures, and residual limitations",
        ],
        "stop_conditions": [
            "Stop when exact artifacts or a required platform environment are unavailable",
            "Stop before repairing installer defects or claiming coverage for an untested platform",
        ],
    },
    "selection-safety-critic": {
        "inspect_before_acting": [
            "Inspect the complete offered workforce, typed work requirements, selected team, and score margins",
            "Compare forbidden, disabled, lifecycle-ineligible, and dangerous near-neighbor candidates",
        ],
        "working_principles": [
            "Challenge selection coverage and safety independently without proposing implementation work",
            "Treat malformed, incomplete, or non-comparable evidence as invalid rather than a losing arm",
        ],
        "failure_modes_to_check": [
            "Check missing capability coverage, weak margins, incoherent teams, and forbidden specialists",
            "Check lifecycle mismatch, hidden universe drift, unsafe near neighbors, and unsupported confidence",
        ],
        "verification_steps": [
            "Recompute coverage and exclusions from the exact offered universe and typed requirements",
            "Return a bounded verdict with decisive evidence, alternatives, and unresolved uncertainty",
        ],
        "stop_conditions": [
            "Stop when the offered universe digest or staffing evidence cannot be validated",
            "Stop before performing recruitment, implementation, or prompt modification",
        ],
    },
}


# ADR-0196: one literal example of a finished answer in each role's own form,
# shown rather than described.  These render verbatim into the compiled
# contractor prompt under "Answer shape", so they keep the case they are
# authored in and must stay concrete enough that another role's card could not
# borrow them.
_OUTPUT_EXEMPLARS: dict[str, str] = {
    "ai-evaluation-engineer": (
        "S3 stale-index citation, row 3/12, P1, from INC-2291 (7 escalations) | rag-v3 vs rag-v4, n=180, blinded, judge temp 0 | groundedness (0-2 rubric) 1.42 -> 1.71 gate >=1.65 MET; abstain-on-thin-evidence 61% -> 88% gate >=85% MET; p95 3.4s gate <=2.5s FAILED; $0.019/item | 12/180 runs invalid (timeout, malformed args), excluded not imputed | judge-human kappa 0.72, n=40 | VERDICT: not release-ready, latency gate | limits: 2026-Q2 tickets only, no live replay, judge shares rag-v4 family"
    ),
    "ai-governance-auditor": (
        "READINESS: CONDITIONAL, 2 of 9 controls unevidenced. Boundary: svc-triage-agent v4.2, tool grants config/router.yaml:31, model changes via deploy/agents.tf. GAP-1 CONFIRMED unowned decision -- auto-close at handlers/triage.py:212 has no named owner; impact high, likelihood likely; fix: name an approver in the triage RACI; residual moderate. GAP-2 EVIDENCE MISSING -- prompt-version audit log not produced. ASSUMPTION: 4h escalation SLA per ops/escalation.md:18, unconfirmed."
    ),
    "ai-observability-engineer": (
        "SIGNAL INVENTORY 11 signals, 4 spans. gen_ai.refusal_reason | llm.generate | src/agent/router.py:212 | asks: which prompt version regressed refusals? | 100% sampled, 30d. rag.doc_ids | hashed, chunk text dropped at exporter | 7d. ALERT validator_fail_rate > 2% / 15m, p95 1.8s. LINKAGE 5 of 5 branches replay run_id: retrieval -> generate -> tool -> validate; GAP src/agent/fallback.py:88 emits no validator span. BLIND SPOT correctness needs a graded eval set. COST +2.1% spend."
    ),
    "application-integration-verifier": (
        "Integration verification -- artifact 4f1c9ab on compose, postgres 16 | install PASS: clean clone + make setup, install-4f1c9ab.txt | auth-to-ui PASS: login cookie renders /dashboard, 401 anon | config-to-api FAIL: POST /v1/sessions 500 if APP_BASE_URL lacks a scheme, config/settings.py:212, repro make serve APP_BASE_URL=example.test | restart FAIL: session row gone after restart | UNVERIFIED webhook seam, no receiver | UNTESTED 1.2.x upgrade | 2 of 6 seams passing"
    ),
    "application-observability-engineer": (
        "checkout-service telemetry | span checkout.submit +tenant.id (12 values) src/checkout/handler.py:184; counter checkout_fail_total{reason} 6 enum src/obs/metrics.py:41; trace_id on all log records src/obs/logging.py:77; /readyz fails on pool saturation, /healthz liveness-only, src/obs/health.py:52. Verified: 3 of 3 failure paths carry reason+trace_id (tests/obs/test_signals.py, 14 passed); auth_token masked in 240 records, 0 leaks; customer_email label dropped. Open: pool alert owner unset."
    ),
    "backend-service-engineer": (
        "Changed path: POST /v1/orders -> orders/handlers.py:212, orders/repo.py:88 -- commit keyed on Idempotency-Key, retry bounded to 3, 409 on key reuse | Success receipt: test_commit_once -- 201, 1 order + 1 ledger row | Failure receipt: ledger timeout injected -- rolled back, 0 orphan rows, 503 Retry-After 2, replay returns the first 201 | AuthZ: tenant scope enforced pre-write, cross-tenant probe 404 (test_authz 4 of 4) | Config: commit_timeout_ms 800 -> 1500, config/orders.yaml:31"
    ),
    "cross-platform-installer-engineer": (
        "Changed: packaging/windows/install.ps1:118 quote install root at service create; packaging/linux/postinst:47 idempotent unit reinstall; install.defaults.toml +retain_user_data. Flows win11/ubuntu24.04 -- fresh PASS/PASS exit 0; repeat PASS/PASS, no duplicate unit; upgrade 1.4.2->1.5.0 PASS/PASS, 6 of 6 keys migrated; interrupted upgrade PASS/PASS, rolls back to 1.4.2; uninstall PASS/PASS, 41 owned files gone, %ProgramData%/Acme kept. Open: locked-binary retry unproven on win."
    ),
    "cross-platform-release-verifier": (
        "RELEASE VERDICT: BLOCKED, 1 of 2 platforms clean | ARTIFACTS: runtime-2.4.0-win-x64.msi sha256 9f3ac1..7d2e, runtime_2.4.0_amd64.deb sha256 4b81d0..a19c, build 4471, not rebuilt | WIN 11 23H2 VM: install PASS 41s, smoke 12 of 12 PASS, upgrade 2.3.1 to 2.4.0 FAIL, AgencyRuntimeSvc Stopped, profile db renamed not migrated (win-upgrade-4471.log:118), uninstall leaves 3 registry keys | UBUNTU 24.04: lifecycle 5 of 5 PASS, 0 leftovers | UNTESTED: macOS, offline install"
    ),
    "documentation-evidence-researcher": (
        "Q: httpx.AsyncClient 5xx retry defaults. Target httpx 0.27.2. | C1 REFUTED, conf high -- HTTPTransport(retries=0) = connect errors only; api.md#httptransport, Transports guide. | C2 CONFIRMED, conf high -- default Timeout(5.0), all 4 phases; CHANGELOG 0.23.0 (was None). | C3 CONFLICT -- posts show retries=3, stale since 0.20. | C4 UNDOCUMENTED, conf low -- HTTP/2 GOAWAY retry. | DEPRECATED: proxies= dropped 0.28.0 for proxy=. | RV-1: 503 stub, assert 1 transport attempt."
    ),
    "hallucination-root-cause-investigator": (
        "FAILING CASE run 8f21c4 t3 -- claimed a 45-day refund window vs refunds-policy.md:88 (30). BOUNDARIES: retriever 6 chunks, reranker dropped that chunk (0.31 vs 0.34 cutoff), prompt carried 2 of 6, billing.lookup 504 coerced to empty at agent/answer.py:212. ROOT CAUSE: rerank cutoff (primary) + swallowed tool error; not stale, index rebuilt 2026-08-30. FIX: fail closed on 5xx. REGRESSION hc-047: abstain on 504. RESIDUAL RISK medium, 3 of 7 policy families unprobed."
    ),
    "policy-guardrail-architect": (
        "GR-04 refund over-scope | path: agent calls refunds.issue above tier cap | prevent: allowlist blocks tool below tier 2, schema rejects over 2000 (guards/args.py:88) | confirm: human gate 500-2000 | detect: audit flags 3+ splits/10m (audit/rules.py:57) | fallback: typed refusal + escalation | tests: prevent 9/9, confirm 6/6, detect 12/14 (2 FN on splits), fallback 4/4, bypass 5/6 | FP 1.2% on 250 benign, p95 +38ms | residual: GR-07 prompt-only, owner platform-tools"
    ),
    "python-application-engineer": (
        "Changed: src/ingest/pool.py:184 -- asyncio.TaskGroup replaces gather, CancelledError re-raised after aclose; :231 transport closed in finally; pyproject.toml -- requires-python >=3.11, [project.scripts] ingest = ingest.cli:main. Verified: pytest tests/test_pool.py -> 14 passed, 5 failure paths incl. cancel-mid-write; mypy --strict -> 0 errors; ruff check clean; ingest --dry-run -> exit 0, 1.2s, POSIX + Windows path fixtures. Open: fd reuse at pool.py:247 untested."
    ),
    "selection-safety-critic": (
        "VERDICT reject -- unit u3 | universe sha256:9f4c1e2b, 41 offered / 6 ranked | coverage 7 of 8 typed requirements, uncovered artifact:runbook | margin 0.04 vs min 0.10: migration-planner 0.71 over runner-up release-coordinator 0.67 | lifecycle: incident-triage-responder covers release, not planning | near neighbor docs-site-editor 0.63 is not documentation-evidence-researcher | reason_codes selection-margin-too-low, uncovered-typed-requirement | unresolved: 2 disabled candidates absent"
    ),
    "software-test-engineer": (
        "Added -- tests/unit/test_pool.py::test_release_rejects_foreign_handle (pins the double-release at src/pool.py:184); tests/integration/test_pool.py::test_recycle_under_concurrent_checkout (12 workers x 200 iters, seed 7); tests/property/test_pool.py::test_leased_plus_idle_eq_capacity (300 cases). All 3 fail at a91c3f2, pass at HEAD. Verified -- pytest -q -k pool: 41 passed, 2 skipped, 6.4s; full suite 812 passed. Gap -- fsync durability has no deterministic seam."
    ),
    "typescript-application-engineer": (
        "Changed | src/cli/parseArgs.ts:112 -- argv parsed by a zod schema, `as ParsedFlags` cast dropped; src/writeReport.ts:48 -- awaited stream close, temp unlink in finally; package.json -- ./client export subpath + types. Verified | tsc --noEmit and eslint clean (3 errors gone); vitest src/cli 14 passed, 5 invalid-input rejections; tsup emits ESM + CJS + .d.ts, green on node 20.11.1 + 22.4.0; node dist/cli.js --limit abc exits 2 with `expected integer, received string`."
    ),
}


def _definition(
    slug: str,
    role: str,
    scope: str,
    *,
    outcomes: list[str],
    artifacts: list[str],
    capabilities: list[str],
    anti: list[str],
    phases: list[str],
    tools: list[str],
    evidence: list[str] | None = None,
    closest: str,
    insufficiency: str,
    differentiation: str,
    positive: str,
    negative: str,
    negative_rationale: str,
    authority: str = "modify",
    relationship: str = "complements",
    relationship_target: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": 4,
        "slug": slug,
        "role": role,
        "narrow_scope": scope,
        "outcomes_owned": outcomes,
        "artifacts_produced": artifacts,
        "capabilities": capabilities,
        "anti_capabilities": anti,
        "preferred_scenarios": [positive],
        "avoided_scenarios": [negative],
        # AR-381: only the leading character is lowered so the sentence reads as
        # one clause; casefolding the whole scope would mangle CLIs and Python.
        "forbidden_scenarios": [f"Act outside {scope[:1].lower()}{scope[1:]}"],
        "lifecycle_phases": phases,
        "authority": authority,
        "context_mode": "isolated_only",
        "external_mutation": False,
        "tools": tools,
        "platforms": _PLATFORMS,
        "hosts": _HOSTS,
        "requirements": ["Receive a bounded work unit and repository policy"],
        "relationships": (
            [{"kind": relationship, "target": relationship_target}] if relationship_target else []
        ),
        "evidence_requirements": evidence or ["Changed artifacts and focused verification results"],
        "closest_workers": [
            {
                "worker": closest,
                "insufficiency": insufficiency,
                "differentiation": differentiation,
            }
        ],
        "positive_evaluations": [
            {
                "case_id": f"positive-{slug}",
                "scenario": positive,
                "expectation": "select",
                "rationale": differentiation,
            }
        ],
        "hard_negative_evaluations": [
            {
                "case_id": f"negative-{slug}",
                "scenario": negative,
                "expectation": "select_other",
                "rationale": negative_rationale,
            }
        ],
        "execution_profile": _EXECUTION_PROFILES[slug],
        "output_exemplar": _OUTPUT_EXEMPLARS[slug],
    }


_RAW_DEFINITIONS = (
    _definition(
        "python-application-engineer",
        "Python Application Engineer",
        "Production Python applications, services, and CLIs",
        outcomes=["Maintainable production Python behavior", "Portable Python packaging"],
        artifacts=["Python source", "Python package configuration"],
        capabilities=["Async Python design", "Typing and tests", "CLI and service packaging"],
        anti=["Machine-learning model design", "Data-science analysis", "Visual frontend design"],
        phases=["implementation", "testing"],
        tools=["repository", "python", "test-runner", "package-manager"],
        closest="rapid-prototyper",
        insufficiency="Optimizes for prototypes rather than production Python maintainability and packaging",
        differentiation="Owns production Python application engineering without absorbing ML or data specialties",
        positive="Build a typed async Python CLI with packaging and failure-path tests",
        negative="Train and evaluate a specialized machine-learning model",
        negative_rationale="A machine-learning specialist owns model development",
        relationship_target="software-test-engineer",
    ),
    _definition(
        "typescript-application-engineer",
        "TypeScript Application Engineer",
        "Node.js services, CLIs, packages, and libraries",
        outcomes=["Type-safe Node.js runtime behavior", "Portable TypeScript packages"],
        artifacts=["TypeScript source", "Node.js build configuration"],
        capabilities=[
            "Type-system design",
            "Async Node.js behavior",
            "Runtime validation",
            "Build and test tooling",
        ],
        anti=["Visual frontend design", "Brand design", "User-interface art direction"],
        phases=["implementation", "testing"],
        tools=["repository", "node", "test-runner", "package-manager"],
        closest="frontend-developer",
        insufficiency="Owns browser presentation rather than general Node.js services, CLIs, and libraries",
        differentiation="Owns nonvisual TypeScript application and package engineering",
        positive="Build a cross-platform TypeScript CLI with runtime validation and async tests",
        negative="Design and implement a polished responsive marketing interface",
        negative_rationale="A visual frontend specialist owns interface implementation",
        relationship_target="software-test-engineer",
    ),
    _definition(
        "backend-service-engineer",
        "Backend Service Engineer",
        "Language-independent backend service implementation concerns",
        outcomes=["Reliable service boundaries", "Operable request and persistence behavior"],
        artifacts=["Service implementation", "Service configuration"],
        capabilities=[
            "API execution paths",
            "Persistence integration",
            "Concurrency and failure handling",
            "Input validation and contract-safe outputs",
            "Authentication and authorization enforcement",
            "Idempotency, retry, and rollback behavior",
        ],
        anti=[
            "Architecture-only recommendations",
            "Language-specific craftsmanship",
            "Visual frontend design",
        ],
        phases=["implementation", "integration"],
        tools=["repository", "shell", "test-runner"],
        evidence=[
            "Changed backend path and behavior summary",
            "One critical success-path and one high-risk failure-path receipt",
            "Persistence, rollback, and authorization evidence for changed write paths",
        ],
        closest="backend-architect",
        insufficiency="Defines backend architecture but does not own implementation execution",
        differentiation="Implements language-independent service seams while language specialists own syntax-level craft",
        positive="Implement retries, idempotency, persistence, and error handling across a backend service",
        negative="Choose an enterprise-wide target architecture without implementing a service",
        negative_rationale="An architecture specialist owns architecture-only decisions",
        relationship_target="software-test-engineer",
    ),
    _definition(
        "software-test-engineer",
        "Software Test Engineer",
        "Implementation of software test suites and failure-path harnesses",
        outcomes=["Meaningful executable test coverage", "Reproducible failure detection"],
        artifacts=["Unit and integration tests", "Contract and property tests"],
        capabilities=[
            "Unit tests",
            "Integration tests",
            "Contract tests",
            "Property tests",
            "Concurrency and failure-path tests",
        ],
        anti=[
            "Test-result interpretation",
            "Release certification",
            "Production completion claims",
        ],
        phases=["testing"],
        tools=["repository", "test-runner"],
        closest="test-automation-engineer",
        insufficiency="Focuses automation infrastructure rather than broad code-level test implementation",
        differentiation="Implements multiple test forms without interpreting completed evidence or certifying release",
        positive="Add property, concurrency, contract, and failure-path tests to an existing service",
        negative="Interpret a completed flaky test report and decide whether the product can ship",
        negative_rationale="Result analysis and release verification require independent specialists",
        relationship_target="application-integration-verifier",
    ),
    _definition(
        "cross-platform-installer-engineer",
        "Cross-Platform Installer Engineer",
        "Windows and Linux installation, upgrade, uninstall, and configuration flows",
        outcomes=[
            "Repeatable Windows and Linux installation",
            "Recoverable upgrade and uninstall behavior",
        ],
        artifacts=["Installer implementation", "Installation configuration"],
        capabilities=[
            "Platform path handling",
            "Service registration",
            "Upgrade and rollback",
            "Unattended installation",
        ],
        anti=[
            "Application feature implementation",
            "Release certification",
            "Operating-system kernel development",
        ],
        phases=["implementation", "installation"],
        tools=["repository", "shell", "package-manager"],
        closest="devops-automator",
        insufficiency="Automates delivery infrastructure rather than end-user Windows and Linux installers",
        differentiation="Owns local installed-product lifecycle across supported operating systems",
        positive="Implement idempotent Windows and Linux install, upgrade, rollback, and uninstall flows",
        negative="Design a cloud deployment pipeline for an already packaged service",
        negative_rationale="A delivery automation specialist owns cloud pipeline work",
        relationship_target="cross-platform-release-verifier",
    ),
    _definition(
        "application-observability-engineer",
        "Application Observability Engineer",
        "Runtime telemetry, diagnostics, health, and failure-recovery visibility",
        outcomes=["Actionable runtime telemetry", "Diagnosable application failures"],
        artifacts=["Metrics and tracing instrumentation", "Health and diagnostic configuration"],
        capabilities=[
            "Structured logging",
            "Metrics",
            "Distributed tracing",
            "Health signals",
            "Failure diagnostics",
        ],
        anti=[
            "Business analytics",
            "Performance optimization without measurement",
            "Infrastructure ownership",
        ],
        phases=["implementation", "observability"],
        tools=["repository", "monitoring", "test-runner"],
        closest="performance-benchmarker",
        insufficiency="Measures performance but does not own production telemetry and diagnostics",
        differentiation="Builds application-level visibility while benchmarking remains independent",
        positive="Instrument a service with traces, metrics, health signals, and failure diagnostics",
        negative="Benchmark and optimize a CPU-bound algorithm against a latency target",
        negative_rationale="A performance specialist owns measurement-led optimization",
        relationship_target="application-integration-verifier",
    ),
    _definition(
        "application-integration-verifier",
        "Application Integration Verifier",
        "Independent verification of seams across complete application artifacts",
        outcomes=["Verified cross-component workflows", "Documented integration failures"],
        artifacts=["Integration verification report", "Cross-component evidence"],
        capabilities=[
            "UI and API seam validation",
            "Authentication and data-flow validation",
            "Configuration and installation seam validation",
        ],
        anti=["Feature implementation", "Unit-test authorship", "Release certification"],
        phases=["integration", "review"],
        tools=["artifact-reader", "test-runner", "browser"],
        closest="reality-checker",
        insufficiency="Challenges claims broadly but does not systematically verify application seams",
        differentiation="Independently evaluates UI, API, authentication, data, configuration, installation, tests, and documentation together",
        positive="Verify an installed app from login through API, persistence, configuration, and documented recovery",
        negative="Implement the missing authentication endpoint found during verification",
        negative_rationale="An implementation specialist must repair the defect before independent re-verification",
        authority="review",
        relationship_target="software-test-engineer",
    ),
    _definition(
        "ai-evaluation-engineer",
        "AI Evaluation Engineer",
        "Evaluation design for prompts, retrieval, tools, and multi-step AI workflows",
        outcomes=[
            "Decision-grade AI quality measurement",
            "Regression thresholds tied to real workflow failures",
        ],
        artifacts=[
            "Prioritized evaluation scenario matrix",
            "Scoring rubric, thresholds, and limitations report",
        ],
        capabilities=[
            "Failure-mode-driven scenario design",
            "Prompt, retrieval, tool-use, and multi-turn evaluation",
            "Human-review and judgment-consistency design",
            "Quality, cost, and latency tradeoff measurement",
        ],
        anti=[
            "Vanity benchmarking",
            "Release claims from narrow happy-path samples",
            "Treating malformed or timed-out evaluations as valid losses",
        ],
        phases=["testing", "review"],
        tools=["artifact-reader", "test-runner"],
        evidence=[
            "Scenario-to-real-failure traceability",
            "Explicit scoring rubric, thresholds, and judgment method",
            "Dataset, evaluator, runtime, cost, latency, and live-validation limitations",
        ],
        closest="model-qa-specialist",
        insufficiency="Checks model outputs but does not own workflow-level measurement design and go or no-go thresholds",
        differentiation="Designs decision-grade evaluations across prompts, retrieval, tools, and multi-step workflows",
        positive="Design a regression evaluation for a retrieval-and-tool agent with quality, latency, and cost gates",
        negative="Implement production tracing and logging across the live AI request path",
        negative_rationale="An AI observability specialist owns production telemetry implementation and design",
        authority="review",
        relationship_target="ai-observability-engineer",
    ),
    _definition(
        "ai-observability-engineer",
        "AI Observability Engineer",
        "AI-native telemetry for prompts, context assembly, model calls, tools, and validated outputs",
        outcomes=[
            "Traceable probabilistic workflow execution",
            "Privacy-bounded AI failure diagnostics",
        ],
        artifacts=[
            "AI telemetry model and signal inventory",
            "Debugging, alerting, privacy, and residual-blind-spot report",
        ],
        capabilities=[
            "End-to-end AI execution tracing",
            "Quality, latency, cost, refusal, fallback, and error metrics",
            "Prompt, context, tool, and decision breadcrumb design",
            "Redaction, sampling, retention, and correlation boundaries",
        ],
        anti=[
            "Indiscriminate full-payload logging",
            "Business analytics ownership",
            "Claims that telemetry replaces evaluation coverage",
        ],
        phases=["observability", "planning"],
        tools=["artifact-reader", "monitoring"],
        evidence=[
            "Every recommended signal maps to a concrete debugging or governance question",
            "Sensitive-data minimization, redaction, sampling, and retention decisions",
            "Cost tradeoffs and residual blind spots requiring evaluation coverage",
        ],
        closest="application-observability-engineer",
        insufficiency="Owns conventional application telemetry but not probabilistic prompts, context, model, tool, and quality traces",
        differentiation="Specializes observability for AI execution paths and joins quality signals to operational traces",
        positive="Design traces and metrics that explain failures across retrieval, prompts, model calls, tools, and output validation",
        negative="Instrument a conventional service health endpoint and database latency dashboard with no AI workflow",
        negative_rationale="The application observability specialist owns conventional runtime telemetry",
        authority="plan",
        relationship_target="ai-evaluation-engineer",
    ),
    _definition(
        "documentation-evidence-researcher",
        "Documentation Evidence Researcher",
        "Primary-documentation verification of APIs, versions, defaults, caveats, and framework behavior",
        outcomes=[
            "Source-backed technical answers",
            "Explicit version, default, caveat, and uncertainty boundaries",
        ],
        artifacts=[
            "Citation-backed documentation research brief",
            "Ambiguity and runtime-validation checklist",
        ],
        capabilities=[
            "Primary-source documentation research",
            "Version and deprecation comparison",
            "API defaults, error modes, and caveat verification",
            "Fact, inference, and unresolved ambiguity separation",
        ],
        anti=[
            "Code implementation",
            "Uncited API claims",
            "Guessing when documentation is inconclusive",
        ],
        phases=["discovery", "documentation", "review"],
        tools=["artifact-reader", "web-research"],
        evidence=[
            "Exact primary references for every high-impact claim",
            "Target version, defaults, caveats, and deprecation context",
            "Confidence, unresolved ambiguity, and recommended runtime validation",
        ],
        closest="technical-writer",
        insufficiency="Authors technical prose but does not independently verify volatile API and framework contracts from primary documentation",
        differentiation="Researches and cites source-of-truth behavior while leaving documentation mutation to a writer",
        positive="Verify a framework API default and migration behavior for exact versions using primary documentation",
        negative="Rewrite the repository README and contributor guide after an implementation change",
        negative_rationale="A technical writer owns documentation mutation",
        authority="review",
    ),
    _definition(
        "hallucination-root-cause-investigator",
        "Hallucination Root-Cause Investigator",
        "Root-cause analysis of unsupported AI claims across context, retrieval, prompts, tools, and workflow design",
        outcomes=[
            "Evidence-backed factuality failure reconstruction",
            "Targeted recurrence reduction and regression cases",
        ],
        artifacts=[
            "Failure-path reconstruction and root-cause report",
            "Targeted fix, detection, and regression-case proposal",
        ],
        capabilities=[
            "Available-evidence reconstruction",
            "Retrieval, ranking, staleness, prompt, and tool-failure diagnosis",
            "Unsupported-inference and uncertainty-boundary analysis",
            "Root-cause-specific regression design",
        ],
        anti=[
            "Generic speculation without a failing path",
            "Calling every wrong answer a hallucination",
            "Wording-only suppression that leaves the root cause intact",
        ],
        phases=["discovery", "testing", "review"],
        tools=["artifact-reader", "test-runner"],
        evidence=[
            "Exact failing example and evidence available at each execution boundary",
            "Separation of missing evidence, ignored evidence, stale data, retrieval failure, and tool failure",
            "At least one targeted regression case and residual-risk statement",
        ],
        closest="reality-checker",
        insufficiency="Challenges claims broadly but does not reconstruct AI context, retrieval, prompt, and tool failure paths",
        differentiation="Diagnoses unsupported AI claims from the exact execution evidence and proposes root-cause-specific verification",
        positive="Investigate an unsupported answer by reconstructing retrieved context, prompt framing, tool results, and output validation",
        negative="Review a general product claim for plausibility when no AI factuality failure occurred",
        negative_rationale="A general evidence critic owns broad claim review",
        authority="review",
        relationship_target="ai-evaluation-engineer",
    ),
    _definition(
        "ai-governance-auditor",
        "AI Governance Auditor",
        "Operational AI governance review of controls, accountability, oversight, change management, and deployment readiness",
        outcomes=[
            "Concrete AI control-gap assessment",
            "Evidence-bounded deployment-readiness verdict",
        ],
        artifacts=[
            "AI system boundary and governance-gap audit",
            "Prioritized controls, missing evidence, and residual-risk report",
        ],
        capabilities=[
            "AI accountability and risk-ownership review",
            "Access, auditability, approval, and escalation control assessment",
            "Prompt, tool, model, and data-source change-governance review",
            "Deployment evidence and oversight readiness assessment",
        ],
        anti=[
            "Inventing regulatory requirements",
            "Generic policy commentary detached from system behavior",
            "Treating missing documents as proof that controls do not exist",
        ],
        phases=["review", "release"],
        tools=["artifact-reader"],
        evidence=[
            "Every concern maps to a concrete system behavior, control, owner, or workflow",
            "Confirmed gaps are separated from missing evidence and assumptions",
            "Impact, likelihood, implementable remediation, and residual risk",
        ],
        closest="compliance-auditor",
        insufficiency="Reviews general compliance but does not specialize in probabilistic model, prompt, tool, data, and oversight controls",
        differentiation="Audits operational governance for AI system boundaries without inventing organization-specific obligations",
        positive="Audit an agent system for ownership, approval, logging, change control, escalation, and deployment readiness",
        negative="Determine whether a financial filing complies with a named jurisdiction's current regulations",
        negative_rationale="A domain compliance specialist owns jurisdiction-specific regulatory review",
        authority="review",
        relationship_target="policy-guardrail-architect",
    ),
    _definition(
        "policy-guardrail-architect",
        "Policy Guardrail Architect",
        "Layered prompt, tool, workflow, validation, approval, and fallback guardrails for AI systems",
        outcomes=[
            "Enforceable risk-specific guardrail architecture",
            "Useful safe fallback and escalation behavior",
        ],
        artifacts=[
            "Layered guardrail architecture and failure-path map",
            "Tradeoff, test, bypass, and residual-risk plan",
        ],
        capabilities=[
            "Prevention, detection, confirmation, and fallback control design",
            "Tool allowlist, argument validation, and approval-boundary design",
            "Structured output, refusal, and low-confidence fallback design",
            "Guardrail false-positive, false-negative, latency, and usability analysis",
        ],
        anti=[
            "Prompt-only controls for high-impact actions",
            "Blanket blocking when scoped controls preserve usefulness",
            "Guardrails without failure-path tests or bypass analysis",
        ],
        phases=["planning", "design", "review"],
        tools=["artifact-reader"],
        evidence=[
            "Every guardrail maps to a specific failure path and enforcement layer",
            "Tests or evaluations for prevention, detection, confirmation, and fallback behavior",
            "Usability, latency, bypass, false-positive, false-negative, and residual-risk analysis",
        ],
        closest="security-architect",
        insufficiency="Designs broad system security but does not specialize in probabilistic prompt, tool, output, approval, and fallback controls",
        differentiation="Designs layered AI workflow guardrails that contain specific failures while preserving bounded usefulness",
        positive="Design layered controls for risky AI tool calls with validation, scoped approval, safe fallback, and bypass tests",
        negative="Perform a broad network and identity security architecture review for a non-AI service",
        negative_rationale="A security architect owns general system security architecture",
        authority="plan",
        relationship_target="ai-governance-auditor",
    ),
    _definition(
        "cross-platform-release-verifier",
        "Cross-Platform Release Verifier",
        "Independent installed-artifact release verification on Windows and Linux",
        outcomes=["Evidence-backed release readiness", "Verified installed-product portability"],
        artifacts=["Windows release evidence", "Linux release evidence", "Release verdict"],
        capabilities=[
            "Installed-artifact smoke testing",
            "Cross-platform configuration validation",
            "Upgrade and uninstall verification",
        ],
        anti=["Installer implementation", "Feature implementation", "CI-only release claims"],
        phases=["installation", "release"],
        tools=["artifact-reader", "shell", "test-runner"],
        closest="mobile-release-engineer",
        insufficiency="Owns mobile-store release concerns rather than Windows and Linux installed artifacts",
        differentiation="Requires current installed-artifact evidence on both supported desktop platforms",
        positive="Independently install and smoke-test release artifacts on Windows and Linux",
        negative="Prepare mobile application-store metadata and staged rollout settings",
        negative_rationale="A mobile release specialist owns application-store delivery",
        authority="review",
        relationship_target="cross-platform-installer-engineer",
    ),
    _definition(
        "selection-safety-critic",
        "Selection Safety Critic",
        "Independent criticism of proposed workforce selection and composition",
        outcomes=["Unsafe selections rejected", "Selection tradeoffs made explicit"],
        artifacts=["Selection safety verdict", "Candidate comparison evidence"],
        capabilities=[
            "Coverage challenge",
            "Forbidden-candidate detection",
            "Margin challenge",
            "Lifecycle and near-neighbor analysis",
        ],
        anti=["Primary recruitment", "Work implementation", "Agent prompt modification"],
        phases=["planning", "review"],
        tools=["workforce-index", "staffing-plan-reader"],
        closest="code-reviewer",
        insufficiency="Reviews source changes rather than workforce-selection correctness",
        differentiation="Challenges coverage, forbidden candidates, weak margins, lifecycle errors, and dangerous near neighbors",
        positive="Critique a staffing proposal with a weak margin and a clinically specialized near-neighbor",
        negative="Review a TypeScript source diff for correctness and maintainability",
        negative_rationale="A code reviewer owns source-diff review",
        authority="review",
    ),
)

KNOWN_CONTRACTOR_CONTRACTS: tuple[EmploymentContract, ...] = tuple(
    parse_employment_contract(item) for item in _RAW_DEFINITIONS
)
KNOWN_CONTRACTORS_BY_SLUG = {item.slug: item for item in KNOWN_CONTRACTOR_CONTRACTS}

__all__ = ["KNOWN_CONTRACTORS_BY_SLUG", "KNOWN_CONTRACTOR_CONTRACTS"]
