---
title: "AR-119: Implement inference-first real-time workforce and contractor lifecycle"
status: in_progress
category: roadmap
created: 2026-07-21
updated: 2026-08-20
tags: [routing, workforce, contractors, delegation, participation, evaluation, performance, multi-harness]
related:
  - docs/decisions/0080-plan-before-recruiting-from-the-whole-workforce.md
  - docs/decisions/0081-compile-contractors-from-governed-structured-contracts.md
  - docs/decisions/0082-schedule-assurance-by-artifact-lifecycle.md
  - docs/decisions/0083-use-capability-indexed-recall-and-bounded-inference.md
  - docs/decisions/0084-bounded-recovery-capsules-and-idempotent-task-dispatch.md
  - docs/decisions/0085-continue-in-task-after-context-checkpoints.md
  - docs/decisions/0086-use-checkpoint-only-context-telemetry.md
  - docs/decisions/0088-deterministic-typed-recall-offline-floor.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0157-automatically-promote-host-verified-contractors.md
  - docs/decisions/0158-collect-child-canary-proof-inside-disposable-host-profiles.md
  - docs/decisions/0159-authenticate-codex-plaintext-spawns-from-host-transcripts.md
  - docs/decisions/0160-pin-child-judge-providers-per-canary-harness.md
  - docs/decisions/0161-pin-accepted-outcome-parent-recruiter-separately.md
  - docs/roadmap/AR-119-founding-vision.md
  - docs/roadmap/AR-119-rule-host-evidence-matrix.md
  - docs/roadmap/AR-119-acceptance-evidence.md
  - docs/roadmap/AR-119-39ff6dca-recruiter-diagnostic-evidence.md
  - docs/decisions/0102-defer-one-shot-application-evaluation.md
  - docs/decisions/0103-bind-named-regulated-assurance-to-typed-staffing.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/issue-AR-178-evaluate-one-shot-applications-post-production.md
  - docs/roadmap/issue-AR-179-fail-named-regulated-assurance-gaps-closed.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/issue-AR-185-bind-codex-activation-verification.md
  - docs/roadmap/issue-AR-190-make-upgrade-plans-runnable-in-uv-tools.md
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
  - docs/roadmap/issue-AR-256-canonical-nine-rule-completion-contract.md
  - docs/roadmap/issue-AR-200-diagnosable-decision-conformance.md
  - docs/roadmap/issue-AR-126-bounded-idempotent-context-handoffs.md
  - docs/roadmap/issue-AR-170-fail-dashboard-response-correlation-closed.md
  - docs/roadmap/issue-AR-171-redact-dashboard-lifecycle-reasons.md
  - docs/roadmap/issue-AR-172-make-roster-pages-snapshot-consistent.md
  - docs/roadmap/issue-AR-173-correlate-route-lab-observations.md
  - docs/roadmap/issue-AR-174-short-circuit-docs-only-ci.md
  - docs/roadmap/issue-AR-175-retire-dashboard-control-fallback.md
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
  - docs/analysis/2026-07-26-production-readiness-review.md
supersedes: []
superseded_by: null
type: issue
epic: routing
issue_id: AR-119
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
depends_on: [AR-115, AR-116, AR-118, AR-125, AR-179, AR-180, AR-185, AR-190, AR-228, AR-252, AR-253, AR-255, AR-256]
blocks: [AR-178, AR-200, AR-201]
---

# AR-119: Implement inference-first real-time workforce and contractor lifecycle

## Problem

> **RESTATED 2026-08-12.** The section explicitly titled "Historical execution
> record" is retained as provenance and is no longer the contract. This issue
> was written around
> "every native work unit is performed by the best compatible specialist" and
> closed on five per-host *product trials* — Agency authoring a multi-unit plan,
> staffing a team against it, executing it, and being graded on the result.
> That direction is retired: AR-214, AR-219, AR-220 and AR-221 are closed as
> superseded, Job B is deleted, and `unit_agent_plan` and the isolated delivery
> mode went with it (`40c608dc`, `d9f6e6be`). **Do not restore the work-unit
> execution framing from the history below.**

**What is actually wanted: prove the nine vision rules on every supported host,
using evidence the host itself wrote.**

Implementation and simulation coverage exist for much of the vision, but they
are not completion evidence. The
[canonical rule/host matrix](AR-119-rule-host-evidence-matrix.md) is the sole
current completion projection. It records selection authority, installed and
live state, proof authority, exact artifacts, and limitations separately so a
contract test or Store row cannot silently become a green host claim.

Rule 4 — harness-spawned children receive specialist cards, plural — was first
observed on a prior Claude candidate on 2026-08-11. Three host-authored child
artifacts contain exact card identities before the child first spoke. None is
bound to the matrix's exact candidate, so Claude's current installed/live layers
remain unproven. Codex now has a repaired conditional plaintext source path;
exact CLI `0.147.0` in-file and authentic one-record TUI cross-file ancestry pass
source, simulation, and independent review. A separate sealed v3 profile now
does the same for observed Desktop `0.147.0-alpha.6.6` root/depth-one/depth-two
V2 ancestry. Exec depth-two/deeper remains unsupported, and prior-candidate live
negatives do not establish exact-candidate installed/live state:

| host | children provably staffed | blocker |
|---|---|---|
| claude | **0 exact-candidate proofs** (3 prior-candidate, 6 legacy) | exact-candidate install/live canary is absent; Rule 1 and parity remain negative |
| codex | **0 exact-candidate proofs** (prior-candidate negatives, 11 legacy) | CLI and Desktop-alpha source/simulation are proven; exec depth-two/deeper remains unsupported and the exact-candidate install/live canary is absent |
| zcode | not measured | host emits no `SubagentStart`/`SubagentStop` |
| openclaw | not measured | not installed on the development box |
| hermes | not measured | not installed on the development box |

Codex is the sharp case: the host demonstrably spawns children — eleven legacy
artifacts prove it — and no prior-candidate measured child carried a card. The
current adapter leaves encrypted calls untouched and conditionally staffs only
an authenticated marked call. Exact CLI `0.147.0` source/simulation covers the
authentic 11/11 one-record TUI census; the separate Desktop-alpha profile covers
the authentic 52/52 V2 census. Exact-candidate installed/live state remains
unproven. ZCode, Hermes, and OpenClaw are not waived.
Hermes and OpenClaw also have a current source-level Rule-8 negative because
their bridge failure paths withhold the host response when Agency is
unavailable.

## Current state

On 2026-08-19 the owner chose ADR-0160's Option A mechanism: persist one
canary-only child-judge provider pin per harness, constrain both judge calls to
that one provider with no fallback, and leave ordinary child staffing
unchanged. The approved isolated install now maps Claude and Codex to
`codex-subscription` and ZCode to the existing `zcode-recruiter` GLM profile;
the ordinary chain is unchanged. A Claude draw produced a verified pre-speech
host artifact for `minimal-change-engineer`, with requested and answering
`codex-subscription` recorded on Store decision `native-child-7624e16e…`.
Commit `14de2f74` repairs the report's parent/child correlation and provider
projection; 134 affected tests pass. The repaired runtime is installed across
all three hosts at digest `51b3202a2acb…`. Two bounded refreshed Claude draws
stopped at parent preflight and therefore neither measured nor contradicted the
earlier child route.

The first attended ZCode 3.8.1 call closed provider attribution but exposed a
prompt-hydration defect after `zcode-recruiter` answered. AR-135 traced that to
28 of 72 eligible cards using a supported prefixed Store hash while v6 evidence
requires the bare digest. Exact Store lookup is now preserved and only the
delivered proof identity is canonicalized.

The installed recheck on runtime `f24664b87f3b…` closes that scoped defect.
Native-child decision `native-child-aa6e5296…` requested and was answered by
the canary-only `zcode-recruiter` profile (`GLM-5.2`), selected
`python-application-engineer`, and bound its v6 envelope to Agent call
`call_1f2255f…`. ZCode's own child metadata and transcript bind that call to
`agent_07b6377b…`; record zero contains the complete card before first child
speech and matches the immutable Store body. Fourteen mechanical checks pass.
This completes Option A from the owner-scoped Claude/Codex/ZCode perspective:
Claude has its attributed pin, Codex parent remains operational with its
upstream child-proof exception, and ZCode has attributed GLM staffing plus
host-written delivery. It does not publish the unpushed commits, change
ordinary staffing, re-promote a retracted Rule, move a matrix cell, or complete
Rule 9 or AR-119.

PR #301 subsequently merged the sealed accepted-outcome path to exact main
`5a1d863c` and installed it for Claude. Its first live producer/verifier draw
failed closed before staffing: both `claude-haiku` parent planner responses were
rejected as `provider_response_contract_invalid`, leaving zero routing
decisions, worker runs, or delivery verifications. The host process itself
completed and wrote two candidate child artifacts, but neither could carry an
Agency v6 delivery marker after the failed preflight. No outcome, promotion, or
matrix movement followed. The next Claude package is therefore a deterministic
isolated-parent preflight repair, not another unmodified provider draw.

The owner separately confirmed the current Codex boundary on 2026-08-19.
Codex parent operation is working: a live request-scoped parent turn identifies
`host=codex`, carries Agency preflight inference, loads the selected specialist
capsule, and projects the required response header. The unresolved Codex issue
is narrower: Agency cannot read the host's opaque native-child collaboration to
prove which cards reached a spawned child. That limitation blocks Codex Rule 4
Installed/Live evidence; it does not make Codex parent routing or header
delivery unavailable. The current phase therefore treats Codex parent behavior
as operational while leaving Codex child delivery, Rule 4, and Rule 9 open.

The audited roster, inference receipts, request-scoped cards, resident managers,
native lifecycle telemetry, CLI, and dashboard provide a strong base. Runtime
candidate `211563c7` retains the repaired Rule-1 source/simulation state: native
child staffing preserves one complete inference-selected team or proceeds
unstaffed. Its sealed in-lifetime Claude collector advances Claude Rule 4 only
through Implementation and Simulation. Its sealed Codex v3 attestor separately
proves Rule-4 Implementation and Simulation for unchanged exact CLI `0.147.0`
profiles plus the exact Desktop `0.147.0-alpha.6.6` profile. No exact-candidate
Installed or Live layer is proven, and no top-level matrix cell is green.
Candidate `211563c7` safely rejects observed unmarked calls, seals every required
canonical prefix, file, profile, currentness check, and causal edge, bounds
aggregate external ancestry to 64 MiB, and rolls final-validation failure back
before commit. Exec depth-two/deeper remains unsupported.

Tracker issue [#132](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132)
mirrors the umbrella state. Repository-local AR-119, AR-256, and their evidence
records provide durable history. The founding vision defines the rules, the
rule/host matrix owns completion status, and the active capsule owns recovery.
AR-120 through AR-125 divide implementation into independently verifiable
slices without narrowing that umbrella contract.

Fresh-task recovery uses the bounded
[AR-119 active recovery capsule](handoffs/issue-AR-119.md). The capsule is the
current bootstrap projection; this issue remains the complete historical
record and dependency map, not a second completion projection.

### Owner-scoped completion sequence — 2026-08-19

The owner set the immediate development milestone to Claude, Codex, and ZCode.
OpenClaw and Hermes are deferred for this session and will be resumed on the
owner's OpenClaw box after the three-host slice is solid. This scheduling choice
is not a host waiver: the five-host Rule-9 contract and every unproven matrix
cell remain unchanged.

The completion sequence for the review brief is:

1. **Land Option A without changing real turns.** Review and publish ADR-0160's
   canary-only per-harness pin after renewed push/PR approval. Preserve the
   control unit, no-fallback provider identity, requested-versus-actual receipt,
   and ordinary-turn noninterference.
2. **Close the Claude canary slice.** Configure the evidence-backed
   `claude -> codex-subscription` pin, install only after approval, and collect
   one fresh host-authored artifact. `claude -> claude-subscription` remains the
   expected-to-decline falsification path, not the passing configuration.
3. **Close the available Codex parent slice honestly.** Retain current parent
   routing/header evidence and the exact pin contracts. Do not rerun the
   byte-identical child canary expecting variation. Keep native-child delivery
   proof explicitly waiting on the upstream Codex collaboration capability.
4. **Make ZCode/GLM attributable and host-proven.** Use the existing isolated
   `zcode-recruiter` profile through the canary-only resolver. Source tests
   prove the documented ZCode Agent `PreToolUse` event reaches child staffing
   and profile pins need no CLI credential home. The current host is hook-only,
   has no launchable CLI here, and emits no child lifecycle events, so collect
   provider attribution through an attended installed ZCode Agent call; do not
   build or credit a synthetic backend. The profile cannot enter ordinary
   staffing. A subscription, prior receipt, or parent-model label alone remains
   insufficient.
5. **Declare only the bounded Option-A milestone complete.** Claude must have
   its fresh proof; Codex parent must remain operational with the child-proof
   exception named; an attended ZCode/GLM call must be executable and
   attributable. OpenClaw and Hermes remain scheduled next, and no Rule-9 or
   matrix claim follows from this three-host milestone.
6. **Finish the primary-tool proof package.** Once Claude Rule 4 is green,
   complete AR-252's independently verified accepted-outcome and automatic
   promotion path. Formalize Claude Rule 8 only if the owner authorizes the
   candidate advance to `f7b84c8a40fa` and the required R2/R3/R7 re-anchoring.
7. **Resume the deferred hosts and final parity.** Move to the OpenClaw box for
   real OpenClaw evidence, then scope and execute Hermes. Re-run the required
   exact-candidate proof set and close Rule 9 only after Rules 1–8 are proven on
   all five hosts.

### Completion plan for the 19 August review artifact

This checkpoint refresh maps every remaining item in the supplied “Nine Rules,
Five Tools” review to an executable package and an explicit admission gate.
Estimates remain the review's engineer-day ranges until a package is scoped on
its real host.

1. **Freeze the vendor-selection fix — complete for this phase.** Preserve the
   canary-only map (`claude/codex -> codex-subscription`,
   `zcode -> zcode-recruiter`), no fallback, requested/actual attribution, and
   unchanged ordinary staffing. Do not re-measure Claude, Codex, or ZCode merely
   for variation. Publication still requires a clean rollup and renewed push/PR
   authorization.
2. **Close the primary-tool delivery package — 2–4 days, medium confidence.**
   On Claude, reconcile the existing host artifact and immutable verification
   with the one-use capability seal, then complete AR-252's independently
   verified accepted outcome and automatic-promotion path on one exact installed
   candidate. The exit is current host-written evidence plus the named matrix
   authority; until then R1/R4/R5/R6 stay retracted.
3. **Make the Rule-8 owner decision — 1–2 days after approval, medium-high
   confidence.** Evidence already exists at run `e9715480` / trace `2a77824c`.
   Lucas must choose whether to advance `candidate_commit` to `f7b84c8a40fa`.
   If approved, re-anchor R2/R3/R7 at that candidate and only then formalize R8;
   if declined, leave the current matrix unchanged and record the deferral.
4. **Treat Codex child proof as an external dependency — weeks if solvable, low
   confidence.** Keep Codex parent routing and headers supported. Resume Rule-4
   work only when upstream exposes readable collaboration/child artifacts or an
   owner-approved proof strategy meets ADR-0156 without weakening the bar.
   Monitoring the open vendor issues is not a passing result.
5. **Scope and execute OpenClaw on the owner's box — estimate after discovery.**
   After renewed install/live authorization, establish a clean exact candidate,
   verify native registration and real host artifacts, then run Rules 1–8 through
   their named acceptance authorities. Record reachability, gaps, and an effort
   estimate before promising a date; no synthetic bridge substitutes for the
   real box.
6. **Scope Hermes after OpenClaw — currently unestimated.** Establish an actual
   supported host path, install and rollback contract, child-delivery evidence
   surface, and focused acceptance suite before scheduling live matrix work.
   Hermes remains exempt from this session, not waived from five-host parity.
7. **Close Rule 9 last.** On one verified-clean rollup, reconcile Rules 1–8 at
   all four evidence layers for Claude, Codex, ZCode, OpenClaw, and Hermes; run
   the fixed matched parity/value corpus and local release gates; then obtain the
   named authority for every matrix movement. Rule 9 is arithmetic over those
   accepted cells, never an independent implementation shortcut.

Near-term commitment therefore remains the review's **4–7 engineer-day primary
tool package**, subject to the Rule-8 owner choice. Five-tool completion gets no
date until Codex exposes a proof surface and the OpenClaw/Hermes discovery
packages return estimates.

Push, PR, merge, install, live canary, tracker, and hosted verification actions
remain approval-gated. The sequence above is a plan, not evidence that any
unrun stage has passed.

The independent production-readiness review is now captured in
[the 2026-07-26 audit report](../analysis/2026-07-26-production-readiness-review.md).
Its reproduced remediation queue is AR-128 through AR-143. Those items are
required corrective slices of this production push; the earlier untracked
2026-07-25 working draft is not governing evidence.

## Approach

Inference reads the current intent and is the only authority that chooses one
or more compatible specialist cards or declares a contractor gap. The cards
load into the current caller. Agency never creates an execution plan or decides
to spawn; if the native host independently starts a child, Agency may deliver
the exact inference-chosen cards, and only the host's own artifact containing
their hashes before first speech proves delivery.

> **ADR-0118 governs the current approach and supersedes the ADR-0088 offline
> amendment.** Every substantive specialist or contractor choice requires a
> validated inference decision. Deterministic code may recall candidates and
> enforce hard eligibility, compatibility, budgets, and evidence correlation;
> it may never select, rank, replace, or invent the team. No valid inference
> means Agency supplies no specialist card or contractor and emits an
> honest diagnostic; the native host remains free to proceed unstaffed.
> Conflicting historical wording below is provenance, not an authorized
> fallback.

The current closure path requires the same behavior on Codex, Claude Code,
ZCode, Hermes, and OpenClaw; multi-card Rule-4 proof on each host; Rule-8
fail-open publication when Agency is unavailable; and automatic contractor
promotion after three independently accepted successes and the seven-day review
window. The unchanged cold staffing control is 15,000 ms. AR-125 may establish
value only from a valid matched Agency-on/off corpus; malformed or timed-out
arms are invalid rather than upstream losses.

### Historical approach record (superseded)

The remainder of this Approach section records the earlier Job B, planned-child,
work-unit, deterministic-floor, activation-receipt, and operator-promotion
design. It is preserved for provenance only. It grants no current fallback,
host waiver, delivery proof, or execution authority.

A high-margin complete local result needs no recruiter call. Balanced and strict
modes may ask inference to resolve an ambiguous bounded shortlist, but the model
cannot nominate outside the runtime-supplied cards or override eligibility and
composition policy. Every accepted Agency work unit must prove that the
performing parent or child consumed its exact-version activation receipt. Parent
plans are reused by children so native fan-out does not multiply inference calls.

> **Superseded current-contract note (2026-08-12).** The paragraph immediately
> above is historical Job B/offline-floor behavior. Under ADR-0118 and the
> restatement, there is no deterministic specialist choice, parent dispatch
> plan, Agency work unit, or one-use activation receipt. The native host owns
> spawning; Agency may only deliver cards chosen by valid inference, or deliver
> none and let the host proceed unstaffed with an honest diagnostic.

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

> **Superseded promotion note (2026-08-12).** Operator-controlled promotion is
> historical. ADR-0157 makes the default three-success/seven-day automatic path
> part of AR-119; AR-252 must supply and live-prove its host-backed acceptance
> evidence before the umbrella closes.

Prove value with paired Agency-on and Agency-off trials using the same ask,
host, model, configuration, and evaluator. An Agency-on trial without accepted
specialist activation evidence is invalid participation evidence, regardless of
the delivered artifact. AR-178 retains product-level one-shot trials as
non-blocking post-production research into complete application delivery.

Pin the source-visible upstream Agency Agents revision and run a held-out
matched comparison corpus. Inference is a defining mechanism, but release
claims require measured improvement over that baseline in useful specialist
precision and recall, typed coverage, conflict safety, activation completion,
latency, and independently graded outcomes. Merely making an inference call is
not evidence that Agency is better.

## Dependencies

AR-115 establishes trustworthy live selection, AR-116 bounds native-child
routing and provider choice, and AR-118 reconciles activation evidence.

## Historical execution record (superseded)

The following checkpoint narrative is the faithful chronological record of the
retired work-unit, Job B, deterministic-floor, planned-child, and product-trial
program. It is not the current implementation plan, acceptance checklist, or
host-proof authority. Resume only from the active recovery capsule, and score
completion only from the canonical rule/host matrix.

### Proven locally in the current slice

- Wave 2 source work now covers atomic finalization, schema-37 native-child
  scope, exact ZCode integration, coherent/paginated dashboard state,
  content-free cross-layer observations, truthful hiring projection,
  revision-aware retrieval, lightweight CLI startup, compatibility wrappers,
  and fail-closed operator-presence enforcement.
- Independent split evidence is 110 authority tests, 167 native-hook/ZCode
  tests, 147 transaction/observability/protocol tests with 8 skips, 134
  dashboard server tests with 3 skips, 82 browser interaction tests, and 101
  distribution/release tests. One five-minute combined arm timed out without a
  result and is excluded; its exact components passed in isolation.
- Production remains blocked by AR-143 because no genuine OS-backed
  operator-presence verifier exists. The current source cannot be freshly
  installed through a model-executed CLI without bypassing that security
  boundary, so the earlier install is not promoted as current-source evidence.
- Wave 1 security/protocol/schema/hiring/release corrections pass a combined
  785-test Python checkpoint suite with 9 skips and the 97-test dashboard
  interaction suite. Full Ruff, format, and diff checks are clean.
- Canonical safe gaps now hire in stable order with cumulative task/daily
  limits and durable plural outcomes; installed configured-provider dogfood is
  still required before this umbrella item can claim contractor execution.
- The second security pass reproduced model-callable owner-dashboard mutations
  and a forged native activation-marker bypass. AR-143 and AR-136 keep those
  production gates explicitly open.

- All five supported hosts receive host-correct guidance: Codex `spawn_agent`,
  Claude `Agent`, Hermes `delegate_task`, OpenClaw `sessions_spawn`, and ZCode's
  main-session Agency activation. ZCode native-child self-routing remains
  host-limited because ZCode emits no child lifecycle events.
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

The next matched-selection recovery package started from checkpoint `b48cb89`
with the unchanged 15000 ms cold gate, one-call fast budget, Windows platform,
`codex-subscription` provider, requested and actual `gpt-5.6-luna` model, and
low reasoning effort. Stdout and stderr were captured as separate raw byte
streams outside the repository before parsing. The complete process finished
in 433.173 seconds, returned exit status 1, emitted 1,188,929 stdout bytes with
SHA-256
`7952a82098d1f97c8fc23899db016fb4da80feffaf9d76e18aa957ebd2005305`,
and emitted zero stderr bytes with the empty-stream SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
The byte counts and hashes were independently reverified before the JSON was
parsed.

The corpus fingerprint remained
`sha256:7358cb9422cef681dc7d85323160652029792916c2ea74d81514df6cfebbba38`,
the base-roster fingerprint remained
`sha256:c80b7422124f5935d3956ec48d6d0fffca15e7c23ebd155475998c7418e4f795`,
and the allowed-agent fingerprint remained
`sha256:88d310bad3716357bf49a74c53a873236cf9c549b878c3c190b4affebead7765`.
All 38 arms recorded provider `codex-subscription`, requested and actual model
`gpt-5.6-luna`, receipt source `cli.explicit_model_argument`, one call,
applied inference, and the unchanged 15000 ms latency budget.

Agency passed 16/19, with precision 0.912281, recall 0.896552, F1 0.904348,
17/19 complete typed coverage, p50 8331.847 ms, p95/max 19631.949 ms, and
zero forbidden, ineligible, or conflict selections. Descriptive upstream
aggregates were 5/19 passing, precision 0.745098, recall 0.655172, F1
0.697248, 7/19 complete typed coverage, p50 12677.413 ms, p95/max 18894.658
ms, and zero scored safety selections. The benchmark was invalid because the
application-integration and runtime-routing upstream arms returned unknown
disabled shadows. Those malformed arms remain errors below and are not
interpreted as upstream losses.

The three Agency failures were non-safety outcomes. Installed cross-platform
release failed closed without selecting a team at 8213.130 ms. Active incident
containment failed closed on selection margin at 8534.211 ms. Clinical/legal
review selected its exact two-worker team but exceeded the unchanged gate at
19631.949 ms. The exact compact projection follows:

~~~text
python-production-change | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=7882.35 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=17500.266 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[python-implementation-specialist-selected,failure-path-testing-specialist-selected,independent-code-review-selected,distinct-contexts-for-specialists,narrow-bug-does-not-require-architecture-phase] | fairness=[]
typescript-production-change | helpful=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=7297.508 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[typescript-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=13174.272 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[typescript-implementation,executable-tests,independent-review,separate-specialist-contexts] | fairness=[]
backend-service-change | helpful=[backend-service-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[backend-service-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.888889 ms=7788.123 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[backend-architect,backend-service-engineer,software-test-engineer,code-reviewer] f1=0.75 ms=15243.988 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[production-backend-endpoint,integration-testing-required,independent-code-review,separate-specialist-contexts] | fairness=[]
installed-cross-platform-release | helpful=[software-test-engineer,code-reviewer,cross-platform-release-verifier] | A=abstained/fail selected=[] f1=0 ms=8213.13 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,cross-platform-release-verifier,software-test-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[required_agents_missing,no_safe_sufficient_team,recruiter_abstained] | U=accepted/pass selected=[cross-platform-installer-engineer,software-test-engineer,cross-platform-release-verifier,application-integration-verifier,code-reviewer] f1=0.75 ms=12181.409 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[cross-platform-installation-required,automated-testing-required,independent-installed-release-verification-required,application-integration-verification-required,independent-code-review-required] | fairness=[]
application-integration | helpful=[software-test-engineer,code-reviewer,application-integration-verifier] | A=accepted/pass selected=[minimal-change-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.75 ms=11035.185 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=12596.299 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-integration-verifier,code-reviewer,software-test-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[application-integration:arm_error]
application-observability | helpful=[application-observability-engineer,software-test-engineer,code-reviewer] | A=accepted/pass selected=[application-observability-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=0.857143 ms=12676.815 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[application-observability-engineer,software-test-engineer,application-integration-verifier] f1=0.666667 ms=12533.822 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer] rc=[direct-scope-match,implementation-testing-review-coverage,independent-context-isolation,no-disabled-semantic-winner] | fairness=[]
documentation-change | helpful=[technical-writer,code-reviewer] | A=accepted/pass selected=[technical-writer,code-reviewer] f1=1 ms=6489.577 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[technical-writer,codebase-archaeologist] f1=0.5 ms=15914.145 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer;art:documentation] rc=[documentation-implementation-plus-independent-accuracy-review,separate-contexts-required-for-independent-specialists] | fairness=[]
selection-safety-review | helpful=[selection-safety-critic] | A=accepted/pass selected=[selection-safety-critic] f1=1 ms=5332.877 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[selection-safety-critic] f1=1 ms=10354.506 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[exact-specialist-match,review-only-scope,no-composition-conflict,no-disabled-semantic-winner] | fairness=[]
repository-security-patch-review | helpful=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] | A=accepted/pass selected=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] f1=1 ms=8331.847 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[codebase-archaeologist,code-reviewer,application-security-engineer] f1=0.333333 ms=18894.658 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:ai-generated-code-security-auditor,codebase-onboarding-engineer] rc=[matched-read-only-repository-mapping,independent-correctness-review,independent-security-exploitability-review,no-file-changes-authorized,distinct-contexts-for-specialists] | fairness=[]
runtime-routing-integration-failure | helpful=[application-integration-verifier,selection-safety-critic,test-results-analyzer] | A=accepted/pass selected=[codebase-onboarding-engineer,application-integration-verifier,test-results-analyzer,selection-safety-critic] f1=0.857143 ms=10200.01 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=16264.012 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-integration-verifier,selection-safety-critic,test-results-analyzer;art:review-report,test-evidence;life:review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[runtime-routing-integration-failure:arm_error]
active-incident-containment | helpful=[incident-responder,incident-response-commander] | A=abstained/fail selected=[] f1=0 ms=8534.211 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:incident-responder;art:analysis,plan;life:discovery,planning] rc=[selection_margin_too_low] | U=accepted/fail selected=[incident-responder,secrets-credential-hygiene-engineer,threat-detection-engineer] f1=0.4 ms=13878.99 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:analysis;life:discovery] rc=[active-credential-theft-incident,forensic-evidence-preservation,reversible-recovery-planning,offensive-probing-excluded,same-context-specialists-separated] | fairness=[]
lsp-incremental-index | helpful=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=8134.141 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[lsp-index-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=13408.973 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[exact-specialist-match,implementation-testing-review-coverage,independent-contexts,all-selected-agents-enabled] | fairness=[]
disabled-lsp-winner | helpful=[lsp-index-engineer] | A=abstained/pass selected=[] f1=0 ms=9671.766 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[no_safe_sufficient_team,recruiter_abstained] | U=accepted/fail selected=[codebase-archaeologist] f1=0 ms=10130.548 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[art:analysis] rc=[best-semantic-match-disabled,use-enabled-nearest-neighbor-for-read-only-diagnosis,safest-next-step-is-preserve-reproduction-evidence-and-have-fallback-reviewer-trace-cancellation-lifetimes-and-symbol-generation] | fairness=[]
incidental-finance-language | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=9823.497 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=11862.965 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[bounded-python-implementation,failure-path-testing-required,independent-review-required,financial-analysis-excluded] | fairness=[]
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=accepted/pass selected=[python-application-engineer,typescript-application-engineer,application-observability-engineer,software-test-engineer,accessibility-auditor,cross-platform-release-verifier,test-results-analyzer,code-reviewer,application-integration-verifier] f1=1 ms=12293.496 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[backend-architect,python-application-engineer,frontend-developer,software-test-engineer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-installer-engineer,cross-platform-release-verifier] f1=0.666667 ms=17215.562 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,test-results-analyzer,typescript-application-engineer;art:review-report] rc=[multi-component-production-build,distinct-specialist-contexts,failure-path-testing-required,accessibility-review-required,observability-required,independent-integration-verification-required,cross-platform-release-evidence-required] | fairness=[]
brand-and-whimsy-separated | helpful=[brand-guardian,whimsy-injector,accessibility-auditor] | A=accepted/pass selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=9530.056 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=11963.266 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:review-report;life:review] rc=[exact-agent-id-match,brand-governance-specialist-selected,whimsy-injector-requires-accessibility-auditor,separate-contexts-for-isolated-specialists,independent-accessibility-audit] | fairness=[]
accounts-payable-cfo-separated | helpful=[accounts-payable-agent,chief-financial-officer] | A=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=7128.368 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=9847.059 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[domain-specialist-match,independent-review-required,separate-context-enforced] | fairness=[]
postgres-write-query-analysis | helpful=[database-optimizer] | A=accepted/pass selected=[database-optimizer] f1=1 ms=5281.645 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[database-optimizer] f1=1 ms=10085.619 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[database-query-performance,measured-execution-plan-findings,read-only-analysis,no-code-or-documentation-change] | fairness=[]
clinical-legal-boundary-review | helpful=[clinical-evidence-agent,legal-document-review] | A=accepted/fail selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=19631.949 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=12677.413 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[clinical-evidence-agent-is-best-match-for-supplied-clinical-trial-evidence-review,legal-document-review-is-best-match-for-independent-review-of-evidence-use-in-a-legal-document,separate-specialists-require-distinct-contexts,request-excludes-diagnosis-medical-billing-and-compliance-certification] | fairness=[]
~~~

The immediate matched rerun of those three Agency failures again captured both
streams outside the repository. It finished in 69.983 seconds, returned exit
status 1, emitted 764,337 stdout bytes with SHA-256
`80093329cdeec73b91d307a4b21c1334017b5ec5713cb1b43bd5e0c8f1ed10dc`,
and emitted zero stderr bytes with the empty-stream hash. Its bounded corpus
fingerprint was
`sha256:4826fdc7d5e13372906519cdfe35d69dc17e907feaf2bfc39c4753db4be4609b`;
the roster, allowed-agent, provider, model, receipt, call-count, inference, and
latency-budget bindings were unchanged.

The bounded benchmark was valid. Agency passed 2/3, with precision, recall,
and F1 of 0.714286, 2/3 complete typed coverage, p50 7888.950 ms, p95/max
13981.295 ms, and zero forbidden, ineligible, or conflict selections.
Installed release recovered with complete coverage at 6549.592 ms, and
clinical/legal recovered with its exact team at 7888.950 ms. Active incident
containment remained fail-closed on selection margin at 13981.295 ms.

~~~text
installed-cross-platform-release | helpful=[software-test-engineer,code-reviewer,cross-platform-release-verifier] | A=accepted/pass selected=[cross-platform-installer-engineer,software-test-engineer,code-reviewer,test-results-analyzer,cross-platform-release-verifier] f1=0.75 ms=6549.592 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[cross-platform-installer-engineer,software-test-engineer,cross-platform-release-verifier,application-integration-verifier,code-reviewer] f1=0.75 ms=14525.232 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[cross-platform-packaging,windows-linux-release,installed-artifact-verification,application-testing,independent-code-review,separate-isolated-contexts] | fairness=[]
active-incident-containment | helpful=[incident-responder,incident-response-commander] | A=abstained/fail selected=[] f1=0 ms=13981.295 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:incident-responder;art:analysis,plan;life:discovery,planning] rc=[selection_margin_too_low] | U=accepted/fail selected=[incident-response-commander,incident-responder,secrets-credential-hygiene-engineer,threat-detection-engineer] f1=0.666667 ms=15223.986 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:analysis] rc=[active-credential-theft-incident,forensic-evidence-preservation,reversible-recovery,defensive-only-scope,no-offensive-probing,distinct-isolated-contexts] | fairness=[]
clinical-legal-boundary-review | helpful=[clinical-evidence-agent,legal-document-review] | A=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=7888.95 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=10544.082 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[clinical-evidence-agent-is-enabled-and-exactly-matches-supplied-clinical-evidence-review,legal-document-review-is-enabled-and-matches-independent-legal-document-review,separatespecialistsintodistinctcontexts,requestdoesnotaskfordiagnosisbillingorcertaincompliancecertification] | fairness=[]
~~~

The immediate active-incident-only matched confirmation captured both streams
outside the repository and finished in 30.107 seconds. It returned exit status
0, emitted 709,309 stdout bytes with SHA-256
`959ec98c7ccaa5680e6b98ee38f2b08d7272ef6255e68490f3e15bb859f7994b`,
and emitted zero stderr bytes with the empty-stream hash. Its bounded corpus
fingerprint was
`sha256:753aa7e236953e0b8108e044c575b0c1bc2ab61bc674428e8810e37b20824810`;
all other parity bindings remained unchanged. The benchmark was valid and the
command passed. Agency selected `incident-responder`, achieved complete typed
coverage, precision 1.000000, recall 0.500000, F1 0.666667, and passed at
13155.609 ms with zero safety defects:

~~~text
active-incident-containment | helpful=[incident-responder,incident-response-commander] | A=accepted/pass selected=[incident-responder] f1=0.666667 ms=13155.609 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[incident-responder,secrets-credential-hygiene-engineer,threat-detection-engineer] f1=0.4 ms=15886.858 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:analysis;life:discovery] rc=[active-credential-theft-incident,forensic-preservation-required,reversible-recovery-planning,offensive-probing-excluded] | fairness=[]
~~~

All three complete-run Agency failures therefore passed under the same governed
controls in bounded confirmation. Installed release recovered with its complete
team, clinical/legal recovered below budget, and active incident containment
recovered on the second bounded confirmation. No governed general semantic
defect was established, so no product or policy code changed. Changing planner
normalization, staffing thresholds, typed coverage, response parsing, the
latency gate, or the one-call budget would tune policy to variable model output.
No comparative superiority claim is made.

The raw captures remain outside the repository at:

- `C:\Users\lucas\AppData\Local\Temp\agency-runtime-ar119-019f8e13-full-20260723-042744`
- `C:\Users\lucas\AppData\Local\Temp\agency-runtime-ar119-019f8e13-bounded-20260723-043610`
- `C:\Users\lucas\AppData\Local\Temp\agency-runtime-ar119-019f8e13-incident-20260723-043751`

The exact blocker remains unchanged: no single complete corpus has yet shown
all 19 Agency arms safe and passing together, and malformed upstream provider
arms continue to invalidate comparative interpretation. The next bounded
package remains in matched selection and starts with another complete corpus
under the unchanged controls. Contractor lifecycle, untouched-corpus
statistics, exact activation, superiority claims, and blinded completed-outcome
trials remain deferred.

The next matched-selection recovery package started from checkpoint `c248f3b`
with the unchanged 15000 ms cold gate, one-call fast budget, Windows platform,
`codex-subscription` provider, requested and actual `gpt-5.6-luna` model, and
low reasoning effort. Stdout and stderr were captured as separate raw byte
streams outside the repository before parsing. The complete process finished
in 430.356 seconds, returned exit status 1, emitted 1,175,519 stdout bytes with
SHA-256
`7ab25f6049444028c8526309bdb76592fff45894ebc02b25ae04e4275f7de67b`,
and emitted zero stderr bytes with the empty-stream SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
The byte counts, hashes, and complete JSON parse were independently reverified
before the report was interpreted.

The corpus fingerprint remained
`sha256:7358cb9422cef681dc7d85323160652029792916c2ea74d81514df6cfebbba38`,
the base-roster fingerprint remained
`sha256:c80b7422124f5935d3956ec48d6d0fffca15e7c23ebd155475998c7418e4f795`,
and the allowed-agent fingerprint remained
`sha256:88d310bad3716357bf49a74c53a873236cf9c549b878c3c190b4affebead7765`.
All 38 arms recorded provider `codex-subscription`, requested and actual model
`gpt-5.6-luna`, receipt source `cli.explicit_model_argument`, one call,
applied inference, and the unchanged 15000 ms latency budget.

Agency passed 16/19, with precision 0.865385, recall 0.775862, F1 0.818182,
16/19 complete typed coverage, p50 8714.009 ms, p95/max 13986.513 ms, and
zero forbidden, ineligible, or conflict selections. Descriptive upstream
aggregates were 4/19 passing, precision 0.718750, recall 0.396552, F1
0.511111, 7/19 complete typed coverage, p50 12953.483 ms, p95/max 21534.806
ms, and zero scored safety selections. The benchmark was invalid because the
TypeScript and backend upstream arms returned invalid assignment rows, while
the application-integration, runtime-routing, incidental-finance, and broad-
application upstream arms returned unknown disabled shadows. Those six
malformed arms remain errors below and are not interpreted as upstream losses.

The three Agency failures were fail-closed non-safety outcomes.
`selection-safety-review` abstained on selection margin at 5827.250 ms,
`active-incident-containment` abstained on selection margin at 10220.782 ms,
and the broad Python/TypeScript application abstained on selection confidence
at 11600.694 ms. None selected a forbidden, ineligible, or conflicting worker.
The exact compact projection follows:

~~~text
python-production-change | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=8714.009 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=9500.712 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[python-implementation,failure-path-testing,independent-review,distinct-specialist-contexts] | fairness=[]
typescript-production-change | helpful=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=9342.5 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=20438.14 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream assignment row is invalid] | fairness=[typescript-production-change:arm_error]
backend-service-change | helpful=[backend-service-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[backend-service-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.888889 ms=8006.759 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=16919.501 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:backend-service-engineer,code-reviewer,software-test-engineer,test-results-analyzer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream assignment row is invalid] | fairness=[backend-service-change:arm_error]
installed-cross-platform-release | helpful=[software-test-engineer,code-reviewer,cross-platform-release-verifier] | A=accepted/pass selected=[cross-platform-installer-engineer,software-test-engineer,code-reviewer,test-results-analyzer,cross-platform-release-verifier] f1=0.75 ms=6146.074 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[desktop-app-engineer,cross-platform-installer-engineer,software-test-engineer,cross-platform-release-verifier,application-integration-verifier] f1=0.5 ms=17080.333 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer;art:review-report;life:review] rc=[cross-platform-installation-and-release-verification-are-explicitly-covered,implementation-testing-and-independent-installed-artifact-verification-are-separated,isolated-only-specialists-use-distinct-contexts,no-disabled-semantic-winner-was-present-in-the-supplied-visible-roster] | fairness=[]
application-integration | helpful=[software-test-engineer,code-reviewer,application-integration-verifier] | A=accepted/pass selected=[minimal-change-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.75 ms=6874.299 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=13759.238 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-integration-verifier,code-reviewer,software-test-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[application-integration:arm_error]
application-observability | helpful=[application-observability-engineer,software-test-engineer,code-reviewer] | A=accepted/pass selected=[application-observability-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=0.857143 ms=11574.573 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[application-observability-engineer,software-test-engineer,code-reviewer] f1=1 ms=16899.676 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[scope-matched-specialists-selected,separate-contexts-for-specialists,implementation-testing-and-independent-review-covered] | fairness=[]
documentation-change | helpful=[technical-writer,code-reviewer] | A=accepted/pass selected=[technical-writer,code-reviewer] f1=1 ms=6790.882 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[technical-writer,codebase-archaeologist] f1=0.5 ms=13987.572 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer] rc=[documentation-rewrite-and-independent-accuracy-review,separate-context-specialists,exact-allowed-agent-ids-only] | fairness=[]
selection-safety-review | helpful=[selection-safety-critic] | A=abstained/fail selected=[] f1=0 ms=5827.25 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:selection-safety-critic;art:review-report;life:review] rc=[selection_margin_too_low] | U=accepted/pass selected=[selection-safety-critic] f1=1 ms=7904.456 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[direct-specialist-fit,selection-safety-review,no-composition-conflict] | fairness=[]
repository-security-patch-review | helpful=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] | A=accepted/pass selected=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] f1=1 ms=8858.867 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[codebase-archaeologist,code-reviewer,application-security-engineer] f1=0.333333 ms=11157.412 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:ai-generated-code-security-auditor,codebase-onboarding-engineer] rc=[matched-code-path-mapping,matched-independent-correctness-review,matched-security-exploitability-review,separate-contexts-for-independent-specialists] | fairness=[]
runtime-routing-integration-failure | helpful=[application-integration-verifier,selection-safety-critic,test-results-analyzer] | A=accepted/pass selected=[codebase-onboarding-engineer,selection-safety-critic,application-integration-verifier,test-results-analyzer] f1=0.857143 ms=10078.586 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=18218.799 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-integration-verifier,selection-safety-critic,test-results-analyzer;art:review-report,test-evidence;life:review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[runtime-routing-integration-failure:arm_error]
active-incident-containment | helpful=[incident-responder,incident-response-commander] | A=abstained/fail selected=[] f1=0 ms=10220.782 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:incident-responder;art:analysis,plan;life:discovery,planning] rc=[selection_margin_too_low] | U=accepted/fail selected=[incident-responder,secrets-credential-hygiene-engineer,threat-detection-engineer] f1=0.4 ms=12953.483 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:analysis;life:discovery] rc=[active-security-incident,credential-theft,forensic-evidence-preservation,reversible-recovery,defensive-only-no-offensive-probing,distinct-specialist-contexts] | fairness=[]
lsp-incremental-index | helpful=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=13986.513 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[lsp-index-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=12719.43 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[narrow-language-server-indexing-change,separate-implementation-testing-and-review-contexts,failure-path-testing-required,independent-review-required] | fairness=[]
disabled-lsp-winner | helpful=[lsp-index-engineer] | A=abstained/pass selected=[] f1=0 ms=7986.75 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[no_safe_sufficient_team,recruiter_abstained,selection_margin_too_low] | U=accepted/fail selected=[codebase-archaeologist] f1=0 ms=15448.654 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[art:analysis] rc=[best-specialist-disabled,select-evidence-ranked-near-neighbor,diagnosis-only-no-implementation-authority] | fairness=[]
incidental-finance-language | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=8650.09 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=10991.424 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,python-application-engineer,software-test-engineer,test-results-analyzer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[incidental-finance-language:arm_error]
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=abstained/fail selected=[] f1=0 ms=11600.694 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor,application-integration-verifier,application-observability-engineer,code-reviewer,cross-platform-release-verifier,python-application-engineer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[selection_confidence_too_low] | U=error/fail selected=[] f1=0 ms=21534.806 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor,application-integration-verifier,application-observability-engineer,code-reviewer,cross-platform-release-verifier,python-application-engineer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[broad-python-typescript-application:arm_error]
brand-and-whimsy-separated | helpful=[brand-guardian,whimsy-injector,accessibility-auditor] | A=accepted/pass selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=10828.408 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=10480.933 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:review-report;life:review] rc=[brand-governance-guidance,separate-playful-interface-work-unit,independent-accessibility-audit,isolated-contexts,all-selected-agents-enabled] | fairness=[]
accounts-payable-cfo-separated | helpful=[accounts-payable-agent,chief-financial-officer] | A=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=7686.658 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=8717.604 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[direct-domain-match,independent-review-required,same-context-conflict-enforced,both-agents-enabled-and-eligible] | fairness=[]
postgres-write-query-analysis | helpful=[database-optimizer] | A=accepted/pass selected=[database-optimizer] f1=1 ms=7785.938 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[database-optimizer] f1=1 ms=9088.645 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[database-performance-specialist-selected,measured-query-plan-findings-only,no-implementation-or-documentation] | fairness=[]
clinical-legal-boundary-review | helpful=[clinical-evidence-agent,legal-document-review] | A=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=9476.778 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=9890.037 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[clinical-evidence-agent-is-semantic-match-and-enabled,legal-document-review-is-semantic-match-and-enabled,separate-contexts-preserved-for-independent-specialists] | fairness=[]
~~~

The immediate matched rerun of those three Agency failures again captured both
streams outside the repository. It finished in 75.868 seconds, returned exit
status 1, emitted 764,550 stdout bytes with SHA-256
`e29d2cb4e9adf122e4fe6a082bfe142d6ce1a3754ab893965d5194d9f9aa0e5a`,
and emitted zero stderr bytes with the empty-stream hash. Its bounded corpus
fingerprint was
`sha256:a3a4613d8cd1f5723f0948faf43401c018d9f831319ef444648e8ff8ff2b9e94`;
the base-roster, allowed-agent, provider, model, receipt, call-count,
inference, and latency-budget bindings were unchanged for all six arms.

Agency passed all 3/3, with precision 1.000000, recall 0.916667, F1
0.956522, 3/3 complete typed coverage, p50 9034.259 ms, p95/max 13722.494
ms, and zero forbidden, ineligible, or conflict selections. Selection safety
recovered with its exact specialist, active incident containment recovered
with `incident-responder`, and the broad application recovered with its exact
nine-worker team. The benchmark remained invalid only because the broad-
application upstream arm returned unknown disabled shadows; that malformed arm
is retained as an error and is not interpreted as an upstream loss.

~~~text
selection-safety-review | helpful=[selection-safety-critic] | A=accepted/pass selected=[selection-safety-critic] f1=1 ms=5471.599 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[selection-safety-critic] f1=1 ms=11347.017 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[best-fit-specialist,request-explicitly-concerns-wrong-neighbor-and-unsafe-composition,independent-review-required] | fairness=[]
active-incident-containment | helpful=[incident-responder,incident-response-commander] | A=accepted/pass selected=[incident-responder] f1=0.666667 ms=9034.259 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[incident-responder,secrets-credential-hygiene-engineer] f1=0.5 ms=13764.827 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:analysis;life:discovery] rc=[active-security-incident,forensic-evidence-preservation,reversible-recovery-required,offensive-probing-excluded,separate-specialist-contexts] | fairness=[]
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=accepted/pass selected=[python-application-engineer,typescript-application-engineer,application-observability-engineer,software-test-engineer,accessibility-auditor,code-reviewer,application-integration-verifier,test-results-analyzer,cross-platform-release-verifier] f1=1 ms=13722.494 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=21389.39 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor,application-integration-verifier,application-observability-engineer,code-reviewer,cross-platform-release-verifier,python-application-engineer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[broad-python-typescript-application:arm_error]
~~~

All three complete-run Agency failures therefore passed under the same governed
controls in immediate bounded confirmation. No governed general semantic defect
was established, so no product or policy code changed. Changing planner
normalization, staffing thresholds, typed coverage, response parsing, the
latency gate, or the one-call budget would tune policy to variable model output.
No comparative superiority claim is made.

The raw captures for this package remain outside the repository at:

- `C:\Users\lucas\AppData\Local\Temp\agency-runtime-ar119-019f8e2a-full-20260723-045239`
- `C:\Users\lucas\AppData\Local\Temp\agency-runtime-ar119-019f8e2a-bounded-20260723-050157`

The exact blocker remains unchanged: no single complete corpus has yet shown
all 19 Agency arms safe and passing together, and malformed upstream provider
arms continue to invalidate comparative interpretation. The next bounded
package remains in matched selection and starts with another complete corpus
under the unchanged controls. Contractor lifecycle, untouched-corpus
statistics, exact activation, superiority claims, and blinded completed-outcome
trials remain deferred.

The next matched-selection recovery package started from checkpoint `251025d`
with the unchanged 15000 ms cold gate, one-call fast budget, Windows
platform, `codex-subscription` provider, requested and actual
`gpt-5.6-luna` model, and low reasoning effort. Stdout and stderr were
captured as separate raw byte streams outside the repository before parsing.
The complete process finished in 416.918 seconds, returned exit status 1,
emitted 1,177,003 stdout bytes with SHA-256
`75cefd31ccffd038ea3b8329c3107be52d3f91ec311377a31343e437620a98c5`,
and emitted zero stderr bytes with the empty-stream SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
The byte counts, hashes, and complete JSON parse were independently reverified
before the report was interpreted.

The corpus fingerprint remained
`sha256:7358cb9422cef681dc7d85323160652029792916c2ea74d81514df6cfebbba38`,
the base-roster fingerprint remained
`sha256:c80b7422124f5935d3956ec48d6d0fffca15e7c23ebd155475998c7418e4f795`,
and the allowed-agent fingerprint remained
`sha256:88d310bad3716357bf49a74c53a873236cf9c549b878c3c190b4affebead7765`.
All 38 arms recorded provider `codex-subscription`, requested and actual model
`gpt-5.6-luna`, receipt source `cli.explicit_model_argument`, one call,
applied inference, and the unchanged 15000 ms latency budget.

Agency passed 17/19, with precision 0.867925, recall 0.793103, F1 0.828829,
17/19 complete typed coverage, p50 8451.681 ms, p95/max 14232.686 ms, and
zero forbidden, ineligible, or conflict selections. Descriptive upstream
aggregates were 6/19 passing, precision 0.794118, recall 0.465517, F1
0.586957, 8/19 complete typed coverage, p50 11323.587 ms, p95/max
21595.293 ms, and zero scored safety selections. The benchmark was invalid
because the TypeScript, installed-release, application-integration, runtime-
routing, and broad-application upstream arms returned unknown disabled
shadows. Those five malformed arms remain errors below and are not
interpreted as upstream losses.

The two Agency failures were fail-closed non-safety outcomes.
`selection-safety-review` abstained on selection confidence and margin at
6550.418 ms, while the broad Python/TypeScript application abstained on
selection confidence at 14232.686 ms. Neither selected a forbidden,
ineligible, or conflicting worker. The exact compact projection follows:

~~~text
python-production-change | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=7988.656 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=10132.414 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[python-bug-requires-python-implementation-specialist,failure-path-tests-require-dedicated-test-engineer,independent-review-requires-separate-reviewer-context] | fairness=[]
typescript-production-change | helpful=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=8018.48 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=16862.4 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[typescript-production-change:arm_error]
backend-service-change | helpful=[backend-service-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[backend-service-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.888889 ms=8025.937 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[backend-service-engineer,software-test-engineer,application-integration-verifier,code-reviewer] f1=0.75 ms=13641.376 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer] rc=[production-backend-endpoint,integration-tests-required,independent-code-review-required,isolated-specialist-contexts] | fairness=[]
installed-cross-platform-release | helpful=[software-test-engineer,code-reviewer,cross-platform-release-verifier] | A=accepted/pass selected=[cross-platform-installer-engineer,software-test-engineer,code-reviewer,test-results-analyzer,cross-platform-release-verifier] f1=0.75 ms=6251.342 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=15497.668 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,cross-platform-release-verifier,software-test-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[installed-cross-platform-release:arm_error]
application-integration | helpful=[software-test-engineer,code-reviewer,application-integration-verifier] | A=accepted/pass selected=[minimal-change-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.75 ms=10413.102 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=19641.536 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-integration-verifier,code-reviewer,software-test-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[application-integration:arm_error]
application-observability | helpful=[application-observability-engineer,software-test-engineer,code-reviewer] | A=accepted/pass selected=[application-observability-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=0.857143 ms=8481.117 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[application-observability-engineer,software-test-engineer,application-integration-verifier,code-reviewer] f1=0.857143 ms=11318.323 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[production-observability,failure-telemetry,automated-failure-path-tests,independent-review] | fairness=[]
documentation-change | helpful=[technical-writer,code-reviewer] | A=accepted/pass selected=[technical-writer,code-reviewer] f1=1 ms=7390.978 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[technical-writer,codebase-archaeologist] f1=0.5 ms=11212.148 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer;art:documentation] rc=[documentation-rewrite-matched-technical-writer,independent-accuracy-review-matched-codebase-archaeologist,separate-contexts-preserve-review-independence] | fairness=[]
selection-safety-review | helpful=[selection-safety-critic] | A=abstained/fail selected=[] f1=0 ms=6550.418 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:selection-safety-critic;art:review-report;life:review] rc=[selection_confidence_too_low,selection_margin_too_low] | U=accepted/pass selected=[selection-safety-critic] f1=1 ms=10604.323 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[direct-specialist-match,selection-safety-review,independent-composition-audit] | fairness=[]
repository-security-patch-review | helpful=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] | A=accepted/pass selected=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] f1=1 ms=9636.304 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[codebase-archaeologist,code-reviewer,application-security-engineer] f1=0.333333 ms=15608.893 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:ai-generated-code-security-auditor,codebase-onboarding-engineer] rc=[read-only-review,separate-code-path-mapping,independent-correctness-review,independent-exploitability-audit,distinct-specialist-contexts] | fairness=[]
runtime-routing-integration-failure | helpful=[application-integration-verifier,selection-safety-critic,test-results-analyzer] | A=accepted/pass selected=[codebase-onboarding-engineer,application-integration-verifier,test-results-analyzer,selection-safety-critic] f1=0.857143 ms=8451.681 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=19407.045 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-integration-verifier,selection-safety-critic,test-results-analyzer;art:review-report,test-evidence;life:review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[runtime-routing-integration-failure:arm_error]
active-incident-containment | helpful=[incident-responder,incident-response-commander] | A=accepted/pass selected=[incident-responder] f1=0.666667 ms=8180.294 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[incident-responder,secrets-credential-hygiene-engineer] f1=0.5 ms=11089.2 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:analysis] rc=[active-credential-theft-incident,forensic-evidence-preservation-required,reversible-recovery-required,offensive-probing-excluded,separate-specialist-contexts] | fairness=[]
lsp-incremental-index | helpful=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=9848.593 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[lsp-index-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=9223.731 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[domain-match-lsp-indexing,implementation-and-testing-required,failure-path-test-specialist,independent-review-required,isolated-contexts-preserved] | fairness=[]
disabled-lsp-winner | helpful=[lsp-index-engineer] | A=abstained/pass selected=[] f1=0 ms=7972.727 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[no_safe_sufficient_team,recruiter_abstained] | U=accepted/pass selected=[codebase-archaeologist] f1=0 ms=11829.043 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[best-semantic-specialist-disabled,use-read-only-code-path-and-history-audit,safest-next-step-is-to-preserve-state-and-reproduce-before-modifying-indexing-or-cancellation-logic] | fairness=[]
incidental-finance-language | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=8972.551 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=11323.587 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[python-implementation-match,failure-path-testing-match,independent-code-review-match,financial-analysis-excluded] | fairness=[]
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=abstained/fail selected=[] f1=0 ms=14232.686 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor,application-integration-verifier,application-observability-engineer,code-reviewer,cross-platform-release-verifier,python-application-engineer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[selection_confidence_too_low] | U=error/fail selected=[] f1=0 ms=21595.293 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor,application-integration-verifier,application-observability-engineer,code-reviewer,cross-platform-release-verifier,python-application-engineer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[broad-python-typescript-application:arm_error]
brand-and-whimsy-separated | helpful=[brand-guardian,whimsy-injector,accessibility-auditor] | A=accepted/pass selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=10763.842 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=14196.962 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:review-report;life:review] rc=[brand-governance-matched-brand-guardian,playful-details-require-whimsy-injector,independent-accessibility-audit-required,separate-isolated-work-unit-maintained] | fairness=[]
accounts-payable-cfo-separated | helpful=[accounts-payable-agent,chief-financial-officer] | A=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=8505.458 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=8491.104 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[domain-match-accounts-payable,independent-cfo-review,separate-contexts,conflict-isolated-by-context] | fairness=[]
postgres-write-query-analysis | helpful=[database-optimizer] | A=accepted/pass selected=[database-optimizer] f1=1 ms=4806.097 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[database-optimizer] f1=1 ms=8578.761 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[exact-specialist-match,read-only-analysis,no-implementation-or-documentation-required] | fairness=[]
clinical-legal-boundary-review | helpful=[clinical-evidence-agent,legal-document-review] | A=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=8946.373 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=10963.585 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[exact-specialist-match,independent-review-required,separate-contexts-for-specialists] | fairness=[]
~~~

The immediate matched rerun of those two Agency failures again captured both
streams outside the repository. It finished in 58.523 seconds, returned exit
status 1, emitted 738,046 stdout bytes with SHA-256
`500841120ce6c2ddf7e7f178b760b722444cbead94d0583c41aacab9889da2ac`,
and emitted zero stderr bytes with the empty-stream hash. Its bounded corpus
fingerprint was
`sha256:dcdf6adea8b69d2ae4acfe4efa2204524d256d8ba5ce79c347722b9e1c6ae8b7`;
the base-roster, allowed-agent, provider, model, receipt, call-count,
inference, and latency-budget bindings were unchanged for all four arms.

Agency passed 1/2, with precision 1.000000, recall 0.900000, F1 0.947368,
1/2 complete typed coverage, p50 13978.311 ms, p95/max 16512.175 ms, and
zero forbidden, ineligible, or conflict selections. The broad application
recovered with its exact nine-worker team at 11444.447 ms. Selection safety
again failed closed on confidence and margin and exceeded the unchanged gate
at 16512.175 ms. The benchmark was invalid because the broad upstream arm
returned unknown disabled shadows; that malformed arm is retained as an error
and is not interpreted as an upstream loss.

~~~text
selection-safety-review | helpful=[selection-safety-critic] | A=abstained/fail selected=[] f1=0 ms=16512.175 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:selection-safety-critic;art:review-report;life:review] rc=[selection_confidence_too_low,selection_margin_too_low] | U=accepted/pass selected=[selection-safety-critic,agents-orchestrator] f1=0.666667 ms=12028.583 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[direct-capability-match,composition-safety-review,coordination-required] | fairness=[]
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=accepted/pass selected=[application-observability-engineer,python-application-engineer,typescript-application-engineer,software-test-engineer,accessibility-auditor,cross-platform-release-verifier,test-results-analyzer,code-reviewer,application-integration-verifier] f1=1 ms=11444.447 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=17258.651 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor,application-integration-verifier,application-observability-engineer,code-reviewer,cross-platform-release-verifier,python-application-engineer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[broad-python-typescript-application:arm_error]
~~~

The immediate selection-safety-only matched confirmation captured both streams
outside the repository and finished in 20.105 seconds. It returned exit
status 0, emitted 708,475 stdout bytes with SHA-256
`24d385312686dfd833bc92d124b8ca2bab70975c1687d7fd08c75372b1742a31`,
and emitted zero stderr bytes with the empty-stream hash. Its bounded corpus
fingerprint was
`sha256:a095de433fb2dbb6a9b36c0a6aacfa3a7ec1d2806a670b8fc0899b7157e78cda`;
the base-roster, allowed-agent, provider, model, receipt, call-count,
inference, and latency-budget bindings remained unchanged for both arms.
The benchmark was valid. Agency selected `selection-safety-critic`,
achieved complete typed coverage and precision, recall, and F1 of 1.000000,
passed at 7852.970 ms, and had zero safety defects:

~~~text
selection-safety-review | helpful=[selection-safety-critic] | A=accepted/pass selected=[selection-safety-critic] f1=1 ms=7852.97 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[agents-orchestrator,selection-safety-critic] f1=0.666667 ms=11211.489 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[selection-audit-requires-specialized-safety-critique,resident-coordination-required,separate-specialist-contexts-preserved] | fairness=[]
~~~

Both complete-run Agency failures therefore passed under the same governed
controls in bounded confirmation. The broad application recovered on the
first bounded rerun, and selection safety recovered on the second bounded
confirmation after one repeated confidence, margin, and latency failure. No
governed general semantic defect was established, so no product or policy code
changed. Changing planner normalization, staffing thresholds, typed coverage,
response parsing, the latency gate, or the one-call budget would tune policy
to variable model output. No comparative superiority claim is made.

The raw captures for this package remain outside the repository at:

- `C:\Users\lucas\AppData\Local\Temp\agency-runtime-ar119-019f8e3f-full-20260723-051622`
- `C:\Users\lucas\AppData\Local\Temp\agency-runtime-ar119-019f8e3f-bounded-20260723-052455`
- `C:\Users\lucas\AppData\Local\Temp\agency-runtime-ar119-019f8e3f-selection-safety-20260723-052641`

The exact blocker remains unchanged: no single complete corpus has yet shown
all 19 Agency arms safe and passing together, and malformed upstream provider
arms continue to invalidate comparative interpretation. The next bounded
package remains in matched selection and starts with another complete corpus
under the unchanged controls. Contractor lifecycle, untouched-corpus
statistics, exact activation, superiority claims, and blinded completed-outcome
trials remain deferred.

The next matched-selection recovery package started from checkpoint `f7800b8`
with the unchanged 15000 ms cold gate, one-call fast budget, Windows platform,
`codex-subscription` provider, requested and actual `gpt-5.6-luna` model, and
low reasoning effort. Stdout and stderr were captured as separate raw byte
streams outside the repository before parsing. The complete process finished
in 418.513 seconds, returned exit status 1, emitted 1,185,217 stdout bytes with
SHA-256
`f5c4514a32802bb532a22aa242656cc0cc81b0bba84ae4b33eca7d271e79d675`,
and emitted zero stderr bytes with the empty-stream SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
The byte counts, hashes, and complete JSON parse were independently reverified
before the report was interpreted.

The corpus fingerprint remained
`sha256:7358cb9422cef681dc7d85323160652029792916c2ea74d81514df6cfebbba38`,
the base-roster fingerprint remained
`sha256:c80b7422124f5935d3956ec48d6d0fffca15e7c23ebd155475998c7418e4f795`,
and the allowed-agent fingerprint remained
`sha256:88d310bad3716357bf49a74c53a873236cf9c549b878c3c190b4affebead7765`.
All 38 arms recorded provider `codex-subscription`, requested and actual model
`gpt-5.6-luna`, receipt source `cli.explicit_model_argument`, one call,
applied inference, and the unchanged 15000 ms latency budget.

Agency passed 18/19, with precision 0.887097, recall 0.948276, F1 0.916667,
18/19 complete typed coverage, p50 7954.096 ms, p95/max 11811.115 ms, and
zero forbidden, ineligible, or conflict selections. Descriptive upstream
aggregates were 4/19 passing, precision 0.731707, recall 0.517241, F1
0.606061, 9/19 complete typed coverage, p50 12356.945 ms, p95/max 23312.771
ms, and zero scored safety selections. The benchmark was invalid because the
Python and broad-application upstream arms returned unknown disabled shadows,
while the application-integration upstream arm returned an invalid assignment
row. Those three malformed arms remain errors below and are not interpreted as
upstream losses.

The sole Agency failure was a fail-closed non-safety outcome.
`selection-safety-review` abstained on selection confidence and margin at
5592.651 ms. It selected no forbidden, ineligible, or conflicting worker. The
exact compact projection follows:

~~~text
python-production-change | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=8007.472 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=17150.632 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,python-application-engineer,software-test-engineer,test-results-analyzer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[python-production-change:arm_error]
typescript-production-change | helpful=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=10990.443 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[typescript-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=10040.991 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[typescript-feature-matched-to-typescript-application-engineer,tests-required-and-matched-to-software-test-engineer,independent-review-required,separate-contexts-for-specialists] | fairness=[]
backend-service-change | helpful=[backend-service-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[backend-service-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.888889 ms=11725.731 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[backend-service-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=15122.738 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[backend-service-implementation,integration-test-coverage,independent-code-review,separate-specialist-contexts] | fairness=[]
installed-cross-platform-release | helpful=[software-test-engineer,code-reviewer,cross-platform-release-verifier] | A=accepted/pass selected=[cross-platform-installer-engineer,software-test-engineer,code-reviewer,test-results-analyzer,cross-platform-release-verifier] f1=0.75 ms=5499.349 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[cross-platform-installer-engineer,software-test-engineer,application-integration-verifier,cross-platform-release-verifier] f1=0.571429 ms=14765.32 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer;art:review-report;life:review] rc=[selected-exact-platform-packaging-specialist,selected-independent-test-specialist,selected-installed-application-integration-verifier,selected-independent-cross-platform-release-verifier,kept-specialists-in-distinct-contexts,all-selected-agent-ids-are-allowed-and-eligible] | fairness=[]
application-integration | helpful=[software-test-engineer,code-reviewer,application-integration-verifier] | A=accepted/pass selected=[minimal-change-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.75 ms=6486.161 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=19604.366 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-integration-verifier,code-reviewer,software-test-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream assignment row is invalid] | fairness=[application-integration:arm_error]
application-observability | helpful=[application-observability-engineer,software-test-engineer,code-reviewer] | A=accepted/pass selected=[application-observability-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=0.857143 ms=9118.116 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[application-observability-engineer,software-test-engineer,application-integration-verifier] f1=0.666667 ms=12356.945 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer] rc=[direct-scope-match,implementation-plus-testing-plus-independent-review,distinct-isolated-contexts,all-selected-agent-ids-allowed] | fairness=[]
documentation-change | helpful=[technical-writer,code-reviewer] | A=accepted/pass selected=[technical-writer,code-reviewer] f1=1 ms=6475.277 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[technical-writer,codebase-archaeologist] f1=0.5 ms=11100.288 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer] rc=[documentation-rewrite,repository-grounded-installation-guidance,independent-technical-accuracy-review,separate-specialist-contexts] | fairness=[]
selection-safety-review | helpful=[selection-safety-critic] | A=abstained/fail selected=[] f1=0 ms=5592.651 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:selection-safety-critic;art:review-report;life:review] rc=[selection_confidence_too_low,selection_margin_too_low] | U=accepted/pass selected=[selection-safety-critic] f1=1 ms=10860.177 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[exact-specialist-match,workforce-composition-audit,wrong-neighbor-analysis,unsafe-selection-review] | fairness=[]
repository-security-patch-review | helpful=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] | A=accepted/pass selected=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] f1=1 ms=11811.115 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[codebase-archaeologist,code-reviewer,application-security-engineer] f1=0.333333 ms=12171.396 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:ai-generated-code-security-auditor,codebase-onboarding-engineer] rc=[read-only-review,independent-specialist-contexts,security-exploitability-analysis,exact-allowed-agent-ids-only] | fairness=[]
runtime-routing-integration-failure | helpful=[application-integration-verifier,selection-safety-critic,test-results-analyzer] | A=accepted/pass selected=[codebase-onboarding-engineer,selection-safety-critic,application-integration-verifier,test-results-analyzer] f1=0.857143 ms=8200.571 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[agents-orchestrator,multi-agent-systems-architect,application-integration-verifier,selection-safety-critic] f1=0.571429 ms=16805.369 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer] rc=[request-spans-routing-diagnosis-local-integration-testing-and-independent-staffing-audit,separate-context-required-for-specialists,all-selected-agent-ids-are-allowed-and-eligible,no-semantic-winner-is-disabled] | fairness=[]
active-incident-containment | helpful=[incident-responder,incident-response-commander] | A=accepted/pass selected=[incident-responder] f1=0.666667 ms=7271.298 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[incident-responder,secrets-credential-hygiene-engineer] f1=0.5 ms=11631 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:analysis;life:discovery] rc=[active-credential-theft-incident,forensic-evidence-preservation,reversible-recovery-required,offensive-probing-excluded] | fairness=[]
lsp-incremental-index | helpful=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=9333.467 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[lsp-index-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=10750.01 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[domain-match-language-server-indexing,explicit-failure-path-testing-required,independent-review-required,separate-contexts-enforced] | fairness=[]
disabled-lsp-winner | helpful=[lsp-index-engineer] | A=abstained/pass selected=[] f1=0 ms=7206.323 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[no_safe_sufficient_team,recruiter_abstained] | U=accepted/pass selected=[codebase-archaeologist,test-automation-engineer] f1=0 ms=11140.274 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[best-semantic-specialist-disabled,use-read-only-code-path-tracing,isolate-regression-test-design,safest-next-step-is-diagnosis-and-reproduction-before-modification] | fairness=[]
incidental-finance-language | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=7954.096 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=11093.655 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[narrow-python-implementation,failure-path-test-coverage,independent-code-review,financial-analysis-excluded] | fairness=[]
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=accepted/pass selected=[python-application-engineer,typescript-application-engineer,application-observability-engineer,software-test-engineer,accessibility-auditor,code-reviewer,application-integration-verifier,test-results-analyzer,cross-platform-release-verifier] f1=1 ms=11295.021 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=23312.771 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor,application-integration-verifier,application-observability-engineer,code-reviewer,cross-platform-release-verifier,python-application-engineer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[broad-python-typescript-application:arm_error]
brand-and-whimsy-separated | helpful=[brand-guardian,whimsy-injector,accessibility-auditor] | A=accepted/pass selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=9731.383 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=14411.704 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:review-report;life:review] rc=[exact-agent-id-match,separate-isolated-work-units,independent-accessibility-audit,required-complement-satisfied] | fairness=[]
accounts-payable-cfo-separated | helpful=[accounts-payable-agent,chief-financial-officer] | A=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=7669.853 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=8355.202 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[direct-specialist-match,separate-context-required-by-request,same-context-conflict-avoided] | fairness=[]
postgres-write-query-analysis | helpful=[database-optimizer] | A=accepted/pass selected=[database-optimizer] f1=1 ms=5446.053 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[database-optimizer] f1=1 ms=15789.123 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[exact-agent-id-present,database-query-and-index-bottleneck-specialist,analysis-only-scope,no-code-or-documentation-change] | fairness=[]
clinical-legal-boundary-review | helpful=[clinical-evidence-agent,legal-document-review] | A=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=7423.87 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=12646.332 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[domain-match-clinical-evidence,domain-match-legal-document-review,separate-contexts-required-for-independent-specialist-reviews,no-diagnosis-no-billing-no-compliance-certification] | fairness=[]
~~~

The immediate selection-safety-only matched confirmation again captured both
streams before parsing. It finished in 16.348 seconds, returned exit status 0,
emitted 707,880 stdout bytes with SHA-256
`17420379d51854517788a8fd119b2031695033c5886dcba52e25908f6da89053`,
and emitted zero stderr bytes with the empty-stream hash. Its bounded corpus
fingerprint was
`sha256:a095de433fb2dbb6a9b36c0a6aacfa3a7ec1d2806a670b8fc0899b7157e78cda`;
the base-roster, allowed-agent, provider, model, receipt, call-count,
inference, and latency-budget bindings remained unchanged for both arms. The
benchmark was valid. Agency selected `selection-safety-critic`, achieved
complete typed coverage and precision, recall, and F1 of 1.000000, passed at
7523.085 ms, and had zero safety defects:

~~~text
selection-safety-review | helpful=[selection-safety-critic] | A=accepted/pass selected=[selection-safety-critic] f1=1 ms=7523.085 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[selection-safety-critic] f1=1 ms=7792.178 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[direct-specialist-match,selection-safety-review,composition-conflict-audit] | fairness=[]
~~~

The sole complete-run Agency failure therefore passed under the same governed
controls in its immediate bounded confirmation. No governed general semantic
defect was established, so no product or policy code changed. Changing planner
normalization, staffing thresholds, typed coverage, response parsing, the
latency gate, or the one-call budget would tune policy to variable model output.
No comparative superiority claim is made.

The raw captures for this package remain outside the repository at:

- `C:\Users\lucas\AppData\Local\Temp\agency-runtime-ar119-019f8e53-full-20260723-053711`
- `C:\Users\lucas\AppData\Local\Temp\agency-runtime-ar119-019f8e53-selection-safety-20260723-054541`

The exact blocker remains unchanged: no single complete corpus has yet shown
all 19 Agency arms safe and passing together, and malformed upstream provider
arms continue to invalidate comparative interpretation. The next bounded
package remains in matched selection and starts with another complete corpus
under the unchanged controls. Contractor lifecycle, untouched-corpus
statistics, exact activation, superiority claims, and blinded completed-outcome
trials remain deferred.

The next matched-selection recovery package started from checkpoint `528a830`
with the unchanged 15000 ms cold gate, one-call fast budget, Windows platform,
`codex-subscription` provider, requested and actual `gpt-5.6-luna` model, and
low reasoning effort. Stdout and stderr were captured as separate raw byte
streams outside the repository before parsing. The complete process finished
in 415.027 seconds, returned exit status 1, emitted 1,179,789 stdout bytes with
SHA-256
`a501c307ab88e8bf32fd2c484b7895341b2b66b6e1cb99f5cb7117908aa7574b`,
and emitted zero stderr bytes with the empty-stream SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
The byte counts, hashes, and complete 19-case JSON parse were independently
reverified before the report was interpreted.

The corpus fingerprint remained
`sha256:7358cb9422cef681dc7d85323160652029792916c2ea74d81514df6cfebbba38`,
the base-roster fingerprint remained
`sha256:c80b7422124f5935d3956ec48d6d0fffca15e7c23ebd155475998c7418e4f795`,
and the allowed-agent fingerprint remained
`sha256:88d310bad3716357bf49a74c53a873236cf9c549b878c3c190b4affebead7765`.
All 38 arms recorded provider `codex-subscription`, requested and actual model
`gpt-5.6-luna`, receipt source `cli.explicit_model_argument`, one call,
applied inference, and the unchanged 15000 ms latency budget.

Agency passed 17/19, with precision 0.887097, recall 0.948276, F1 0.916667,
18/19 complete typed coverage, p50 8302.183 ms, p95/max 15154.956 ms, and
zero forbidden, ineligible, or conflict selections. Descriptive upstream
aggregates were 3/19 passing, precision 0.718750, recall 0.396552, F1
0.511111, 7/19 complete typed coverage, p50 12999.298 ms, p95/max 20623.868
ms, and zero scored safety selections. The benchmark was invalid because the
Python, backend, installed-release, application-integration, and broad-
application upstream arms returned unknown disabled shadows, while the LSP
upstream arm returned an invalid assignment row. Those six malformed arms
remain errors below and are not interpreted as upstream losses.

The two Agency failures were non-safety outcomes. Runtime routing selected its
complete typed team but exceeded the unchanged gate by 154.956 ms at
15154.956 ms. Active incident containment failed closed on selection margin at
8209.393 ms. Neither selected a forbidden, ineligible, or conflicting worker.
The exact compact projection follows:

~~~text
python-production-change | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=8302.183 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=12999.298 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,python-application-engineer,software-test-engineer,test-results-analyzer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[python-production-change:arm_error]
typescript-production-change | helpful=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=7403.44 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[typescript-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=13138.732 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[typescript-feature,implementation-and-tests-requested,independent-review-requested,separate-contexts-for-specialists] | fairness=[]
backend-service-change | helpful=[backend-service-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[backend-service-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.888889 ms=7603.178 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=17377.756 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:backend-service-engineer,code-reviewer,software-test-engineer,test-results-analyzer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[backend-service-change:arm_error]
installed-cross-platform-release | helpful=[software-test-engineer,code-reviewer,cross-platform-release-verifier] | A=accepted/pass selected=[cross-platform-installer-engineer,software-test-engineer,code-reviewer,test-results-analyzer,cross-platform-release-verifier] f1=0.75 ms=6207.459 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=20623.868 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,cross-platform-release-verifier,software-test-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[installed-cross-platform-release:arm_error]
application-integration | helpful=[software-test-engineer,code-reviewer,application-integration-verifier] | A=accepted/pass selected=[minimal-change-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.75 ms=9723.612 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=16217.143 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-integration-verifier,code-reviewer,software-test-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[application-integration:arm_error]
application-observability | helpful=[application-observability-engineer,software-test-engineer,code-reviewer] | A=accepted/pass selected=[application-observability-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=0.857143 ms=10306.076 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[application-observability-engineer,software-test-engineer,code-reviewer] f1=1 ms=15295.054 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[direct-capability-match,production-observability,failure-telemetry,failure-path-testing,independent-review,distinct-specialist-contexts] | fairness=[]
documentation-change | helpful=[technical-writer,code-reviewer] | A=accepted/pass selected=[technical-writer,code-reviewer] f1=1 ms=6460.031 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[technical-writer,codebase-archaeologist] f1=0.5 ms=10392.605 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer] rc=[narrow-documentation-request,independent-review-required,separate-contexts-for-independent-specialists] | fairness=[]
selection-safety-review | helpful=[selection-safety-critic] | A=accepted/pass selected=[selection-safety-critic] f1=1 ms=5596.592 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[selection-safety-critic] f1=1 ms=10343.865 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[specialized-selection-safety-review,direct-match-to-request,no-composition-conflict] | fairness=[]
repository-security-patch-review | helpful=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] | A=accepted/pass selected=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] f1=1 ms=13776.169 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[codebase-archaeologist,code-reviewer,application-security-engineer] f1=0.333333 ms=11356.812 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:ai-generated-code-security-auditor,codebase-onboarding-engineer] rc=[read-only-review,separate-independent-contexts,security-correctness-and-code-path-coverage] | fairness=[]
runtime-routing-integration-failure | helpful=[application-integration-verifier,selection-safety-critic,test-results-analyzer] | A=accepted/fail selected=[codebase-onboarding-engineer,selection-safety-critic,application-integration-verifier,test-results-analyzer] f1=0.857143 ms=15154.956 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[agents-orchestrator,multi-agent-systems-architect,codebase-archaeologist,application-integration-verifier,selection-safety-critic] f1=0.5 ms=13975.306 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer] rc=[matched-routing-evidence-to-multi-agent-systems-architect,matched-installed-hook-forensics-to-codebase-archaeologist,matched-local-live-integration-testing-to-application-integration-verifier,matched-independent-staffing-audit-to-selection-safety-critic,separate-contexts-for-independent-specialists] | fairness=[]
active-incident-containment | helpful=[incident-responder,incident-response-commander] | A=abstained/fail selected=[] f1=0 ms=8209.393 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:incident-responder;art:analysis,plan;life:discovery,planning] rc=[selection_margin_too_low] | U=accepted/fail selected=[incident-responder,secrets-credential-hygiene-engineer] f1=0.5 ms=13001.042 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:analysis;life:discovery] rc=[active-incident-response,forensic-evidence-preservation,credential-theft-containment,reversible-recovery,no-offensive-probing,separate-specialist-contexts] | fairness=[]
lsp-incremental-index | helpful=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=8545.574 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=16763.136 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,lsp-index-engineer,software-test-engineer,test-results-analyzer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream assignment row is invalid] | fairness=[lsp-incremental-index:arm_error]
disabled-lsp-winner | helpful=[lsp-index-engineer] | A=abstained/pass selected=[] f1=0 ms=9159.915 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[required_agents_missing,no_safe_sufficient_team,recruiter_abstained,selection_margin_too_low] | U=accepted/pass selected=[codebase-archaeologist,software-architect] f1=0 ms=9851.201 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[best-specialist-disabled,use-independent-repository-diagnosis,separate-specialist-contexts,prefer-evidence-first-read-only-analysis,safest-next-step-is-scoped-reproduction-and-regression-plan] | fairness=[]
incidental-finance-language | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=7498.163 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=11980.725 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[python-implementation,failure-path-testing,independent-review,financial-analysis-explicitly-excluded] | fairness=[]
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=accepted/pass selected=[application-observability-engineer,python-application-engineer,typescript-application-engineer,software-test-engineer,accessibility-auditor,cross-platform-release-verifier,test-results-analyzer,code-reviewer,application-integration-verifier] f1=1 ms=11680.375 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=14524.376 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor,application-integration-verifier,application-observability-engineer,code-reviewer,cross-platform-release-verifier,python-application-engineer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[broad-python-typescript-application:arm_error]
brand-and-whimsy-separated | helpful=[brand-guardian,whimsy-injector,accessibility-auditor] | A=accepted/pass selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=8903.382 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=11215.005 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:review-report;life:review] rc=[brand-governance-matched-to-brand-guardian,playful-interface-matched-to-whimsy-injector,accessibility-audit-matched-to-accessibility-auditor,separate-isolated-contexts-required,whimsy-brand-conflict-avoided,independent-accessibility-audit-selected] | fairness=[]
accounts-payable-cfo-separated | helpful=[accounts-payable-agent,chief-financial-officer] | A=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=8398.544 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=9133.735 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:review-report] rc=[exact-agent-id-match,domain-fit-accounts-payable-exceptions,domain-fit-cash-impact-finance-review,independent-context-required-by-request,conflict-isolation-accounts-payable-agent-vs-chief-financial-officer] | fairness=[]
postgres-write-query-analysis | helpful=[database-optimizer] | A=accepted/pass selected=[database-optimizer] f1=1 ms=5358.055 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[database-optimizer] f1=1 ms=9725.05 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[matched-measured-database-workload,analysis-only-request,no-documentation-or-application-code-change] | fairness=[]
clinical-legal-boundary-review | helpful=[clinical-evidence-agent,legal-document-review] | A=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=8180.893 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=8471.584 safety=f0/i0/c0 disabled=[]/required=[] missing=[life:discovery] rc=[clinical-evidence-review,independent-legal-document-review,separate-isolated-contexts] | fairness=[]
~~~

The immediate two-case matched rerun captured both streams before parsing. It
finished in 45.067 seconds, returned exit status 1, emitted 735,464 stdout
bytes with SHA-256
`3d514a00f4f040c8d0d5af9ccde9e5ff22a0f4cc2f4e9d14db2f8910818593a9`,
and emitted zero stderr bytes with the empty-stream hash. Its bounded corpus
fingerprint was
`sha256:70f66aed59a201c4fea4425dd8ce8bf6148411aa7ad605236340e443e34f0163`;
the base-roster, allowed-agent, provider, model, receipt, call-count,
inference, and latency-budget bindings were unchanged for all four arms.

The bounded benchmark was valid, but both Agency arms remained fail-closed.
Runtime routing abstained on selection confidence at 9390.006 ms, and active
incident containment abstained on selection margin at 8529.749 ms. Agency had
0/2 complete typed coverage, p50 8959.877 ms, p95/max 9390.006 ms, and zero
forbidden, ineligible, or conflict selections:

~~~text
runtime-routing-integration-failure | helpful=[application-integration-verifier,selection-safety-critic,test-results-analyzer] | A=abstained/fail selected=[] f1=0 ms=9390.006 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-integration-verifier,selection-safety-critic,test-results-analyzer;art:review-report,test-evidence;life:review,testing] rc=[selection_confidence_too_low] | U=accepted/fail selected=[agents-orchestrator,codebase-archaeologist,application-integration-verifier,multi-agent-systems-architect,selection-safety-critic] f1=0.5 ms=14711.393 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer] rc=[resident-coordination-required,routing-evidence-needs-independent-code-audit,live-local-integration-testing-required,multi-agent-routing-architecture-is-in-scope,independent-selection-safety-review-required] | fairness=[]
active-incident-containment | helpful=[incident-responder,incident-response-commander] | A=abstained/fail selected=[] f1=0 ms=8529.749 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:incident-responder;art:analysis,plan;life:discovery,planning] rc=[selection_margin_too_low] | U=accepted/fail selected=[incident-responder,incident-response-commander,secrets-credential-hygiene-engineer] f1=0.8 ms=11302.51 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:analysis;life:discovery] rc=[active-security-incident,credential-theft,forensic-preservation,reversible-recovery,no-offensive-probing] | fairness=[]
~~~

The second two-case matched confirmation again captured both streams before
parsing. It finished in 53.879 seconds, returned exit status 1, emitted 735,862
stdout bytes with SHA-256
`fa1f7d8ac0bb00a5ab2a27f05caa91aa9dc52108a5cc2ef79a11977f51136c7e`,
and emitted zero stderr bytes with the empty-stream hash. It retained the same
bounded corpus fingerprint and every other parity binding remained unchanged.

Agency passed both cases, with precision 0.800000, recall 0.800000, F1
0.800000, 2/2 complete typed coverage, p50 8657.542 ms, p95/max 10140.279
ms, and zero forbidden, ineligible, or conflict selections. Runtime routing
recovered with its complete team at 10140.279 ms, and active incident
containment recovered with `incident-responder` at 7174.805 ms. The benchmark
was invalid only because the runtime-routing upstream arm returned unknown
disabled shadows; that malformed arm remains an error and is not interpreted
as an upstream loss:

~~~text
runtime-routing-integration-failure | helpful=[application-integration-verifier,selection-safety-critic,test-results-analyzer] | A=accepted/pass selected=[codebase-onboarding-engineer,application-integration-verifier,test-results-analyzer,selection-safety-critic] f1=0.857143 ms=10140.279 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=21281.595 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-integration-verifier,selection-safety-critic,test-results-analyzer;art:review-report,test-evidence;life:review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[runtime-routing-integration-failure:arm_error]
active-incident-containment | helpful=[incident-responder,incident-response-commander] | A=accepted/pass selected=[incident-responder] f1=0.666667 ms=7174.805 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[incident-response-commander,incident-responder,secrets-credential-hygiene-engineer,threat-detection-engineer] f1=0.666667 ms=14172.494 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:analysis] rc=[active-security-incident,evidence-preservation-required,reversible-recovery-required,defensive-only-scope,avoid-offensive-probing,distinct-specialist-contexts] | fairness=[]
~~~

Both complete-run Agency failures therefore passed under the same governed
controls in bounded confirmation. Runtime routing restored its complete team
below budget, and active incident containment recovered on the second bounded
confirmation. No governed general semantic defect was established, so no
product or policy code changed. Changing planner normalization, staffing
thresholds, typed coverage, response parsing, the latency gate, or the one-call
budget would tune policy to variable model output. No comparative superiority
claim is made.

The raw captures for this package remain outside the repository at:

- `C:\Users\lucas\AppData\Local\Temp\agency-runtime-ar119-019f8e64-full-20260723-055553`
- `C:\Users\lucas\AppData\Local\Temp\agency-runtime-ar119-019f8e64-bounded-20260723-060408`
- `C:\Users\lucas\AppData\Local\Temp\agency-runtime-ar119-019f8e64-confirmation-20260723-060551`

The next matched-selection recovery package started from checkpoint `77c3a74`
with the unchanged 15000 ms cold gate, one-call fast budget, Windows platform,
`codex-subscription` provider, requested `gpt-5.6-luna` model, and low
reasoning effort. Stdout and stderr were captured as separate raw byte streams
outside the repository before parsing. The complete process finished in
399.725 seconds, returned exit status 1, emitted 1,179,646 stdout bytes with
SHA-256
`d35bce3afa366b5cfd9b38d93023a4389f5029e747cc781c998944b8b3b3cbf9`,
and emitted zero stderr bytes with the empty-stream SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
The byte counts, hashes, and complete 19-case JSON parse were independently
reverified before the report was interpreted.

The corpus fingerprint remained
`sha256:7358cb9422cef681dc7d85323160652029792916c2ea74d81514df6cfebbba38`,
the base-roster fingerprint remained
`sha256:c80b7422124f5935d3956ec48d6d0fffca15e7c23ebd155475998c7418e4f795`,
and the allowed-agent fingerprint remained
`sha256:88d310bad3716357bf49a74c53a873236cf9c549b878c3c190b4affebead7765`.
All 38 arms retained the configured provider, requested model, one-call count,
and unchanged latency budget. All 19 Agency arms and 17 upstream arms also
recorded actual model `gpt-5.6-luna`, receipt source
`cli.explicit_model_argument`, and applied inference. The active-incident and
LSP upstream arms instead returned `provider_no_valid_response` and
truthfully recorded no actual model, an unavailable model receipt, and no
applied inference.

Agency passed 16/19, with precision, recall, and F1 of 0.879310, 17/19
complete typed coverage, p50 7939.273 ms, p95/max 12491.359 ms, and zero
forbidden, ineligible, or conflict selections. Descriptive upstream aggregates
were 3/19 passing, precision 0.806452, recall 0.431034, F1 0.561798, 6/19
complete typed coverage, p50 11343.929 ms, p95/max 22268.039 ms, and zero
scored safety selections. The benchmark was invalid because the backend and
application-integration upstream arms returned invalid assignment rows, the
installed-release and broad-application upstream arms returned unknown
disabled shadows, and the active-incident and LSP upstream arms returned no
valid provider response. Those six invalid arms remain errors below and are
not interpreted as upstream losses.

The three Agency failures were non-safety outcomes.
`active-incident-containment` failed closed on independent assurance and
selection margin at 10651.813 ms. The broad Python/TypeScript application
selected eight of its nine helpful workers but omitted
`accessibility-auditor` at 9537.229 ms. `brand-and-whimsy-separated`
failed closed without a sufficient team at 8906.675 ms. None selected a
forbidden, ineligible, or conflicting worker. The exact compact projection
follows:

~~~text
python-production-change | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=12491.359 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=11343.929 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[python-application-engineer-is-the-best-fit-for-the-python-bug-fix,software-test-engineer-is-the-best-fit-for-failure-path-test-code,code-reviewer-provides-independent-review,separate-contexts-preserved] | fairness=[]
typescript-production-change | helpful=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=7414.037 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[typescript-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=11803.733 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[typescript-feature-needs-specialized-implementation,tests-required,independent-code-review-required,separate-contexts-for-specialists] | fairness=[]
backend-service-change | helpful=[backend-service-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[backend-service-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.888889 ms=7173.642 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=19143.063 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:backend-service-engineer,code-reviewer,software-test-engineer,test-results-analyzer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream assignment row is invalid] | fairness=[backend-service-change:arm_error]
installed-cross-platform-release | helpful=[software-test-engineer,code-reviewer,cross-platform-release-verifier] | A=accepted/pass selected=[cross-platform-installer-engineer,software-test-engineer,code-reviewer,test-results-analyzer,cross-platform-release-verifier] f1=0.75 ms=6796.543 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=18556.746 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,cross-platform-release-verifier,software-test-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[installed-cross-platform-release:arm_error]
application-integration | helpful=[software-test-engineer,code-reviewer,application-integration-verifier] | A=accepted/pass selected=[minimal-change-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.75 ms=6871.767 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=21974.157 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-integration-verifier,code-reviewer,software-test-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream assignment row is invalid] | fairness=[application-integration:arm_error]
application-observability | helpful=[application-observability-engineer,software-test-engineer,code-reviewer] | A=accepted/pass selected=[application-observability-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=0.857143 ms=7691.402 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[application-observability-engineer,software-test-engineer,application-integration-verifier] f1=0.666667 ms=13426.232 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer] rc=[production-observability-match,failure-telemetry-implementation,failure-path-test-coverage,independent-review-required] | fairness=[]
documentation-change | helpful=[technical-writer,code-reviewer] | A=accepted/pass selected=[technical-writer,code-reviewer] f1=1 ms=6621.451 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[technical-writer,code-reviewer] f1=1 ms=12805.318 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:documentation] rc=[documentation-implementation-and-independent-review-required,separate-contexts-enforced-for-independent-specialists,all-selected-agent-ids-present-in-allowed-agent-ids] | fairness=[]
selection-safety-review | helpful=[selection-safety-critic] | A=accepted/pass selected=[selection-safety-critic] f1=1 ms=11485.62 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[selection-safety-critic] f1=1 ms=11334.01 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[specialized-selection-audit-fit,independent-composition-safety-review,no-additional-specialist-needed,no-disabled-semantic-winner-observed] | fairness=[]
repository-security-patch-review | helpful=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] | A=accepted/pass selected=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] f1=1 ms=9339.823 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[codebase-onboarding-engineer,code-reviewer,application-security-engineer] f1=0.666667 ms=13286.058 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:ai-generated-code-security-auditor] rc=[exact-agent-ids-only,read-only-review-scope,independent-specialists-in-distinct-contexts,no-disabled-semantic-winner] | fairness=[]
runtime-routing-integration-failure | helpful=[application-integration-verifier,selection-safety-critic,test-results-analyzer] | A=accepted/pass selected=[codebase-onboarding-engineer,application-integration-verifier,test-results-analyzer,selection-safety-critic] f1=0.857143 ms=9834.239 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[agents-orchestrator,multi-agent-systems-architect,test-automation-engineer,selection-safety-critic] f1=0.285714 ms=10383.942 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-integration-verifier,test-results-analyzer] rc=[multi-workstream-diagnosis,routing-evidence-required,live-integration-testing-required,independent-staffing-audit-required,distinct-context-isolation] | fairness=[]
active-incident-containment | helpful=[incident-responder,incident-response-commander] | A=abstained/fail selected=[] f1=0 ms=10651.813 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:incident-responder;art:analysis,plan;life:discovery,planning] rc=[independent_assurance_missing,selection_margin_too_low] | U=error/fail selected=[] f1=0 ms=2726.425 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:incident-responder;art:analysis,plan;life:discovery,planning] rc=[provider_no_valid_response] | fairness=[active-incident-containment:arm_error,active-incident-containment:actual_model_unmatched,active-incident-containment:model_receipt_unavailable,active-incident-containment:inference_not_applied]
lsp-incremental-index | helpful=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=7488.341 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=2658.032 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,lsp-index-engineer,software-test-engineer,test-results-analyzer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_no_valid_response] | fairness=[lsp-incremental-index:arm_error,lsp-incremental-index:actual_model_unmatched,lsp-incremental-index:model_receipt_unavailable,lsp-incremental-index:inference_not_applied]
disabled-lsp-winner | helpful=[lsp-index-engineer] | A=abstained/pass selected=[] f1=0 ms=9074.603 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[selection_margin_too_low] | U=accepted/pass selected=[codebase-archaeologist] f1=0 ms=9765.76 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[best-semantic-specialist-disabled,do-not-select-disabled-agent,use-evidence-only-code-path-audit-as-safest-next-step,preserve-cancellation-and-index-consistency-boundaries] | fairness=[]
incidental-finance-language | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=7939.273 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=10822.743 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[narrow-python-implementation,failure-path-tests-explicitly-requested,independent-review-explicitly-requested,financial-analysis-excluded,separate-contexts-for-specialists] | fairness=[]
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=accepted/fail selected=[application-observability-engineer,python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer,cross-platform-release-verifier] f1=0.941176 ms=9537.229 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor] rc=[] | U=error/fail selected=[] f1=0 ms=22268.039 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor,application-integration-verifier,application-observability-engineer,code-reviewer,cross-platform-release-verifier,python-application-engineer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[broad-python-typescript-application:arm_error]
brand-and-whimsy-separated | helpful=[brand-guardian,whimsy-injector,accessibility-auditor] | A=abstained/fail selected=[] f1=0 ms=8906.675 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor,brand-guardian,whimsy-injector;art:implementation-change,plan,review-report;life:implementation,planning,review] rc=[no_safe_sufficient_team,recruiter_abstained] | U=accepted/fail selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=16025.154 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:review-report;life:review] rc=[brand-governance-matched-to-brand-guardian,playful-details-matched-to-whimsy-injector,accessibility-audit-required-by-whimsy-injector-and-kept-independent,separate-isolated-contexts-preserved,all-selected-agent-ids-are-allowed-and-eligible] | fairness=[]
accounts-payable-cfo-separated | helpful=[accounts-payable-agent,chief-financial-officer] | A=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=7552.171 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=10636.217 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:review-report] rc=[exact-domain-match,independent-review-required,separate-context-enforced] | fairness=[]
postgres-write-query-analysis | helpful=[database-optimizer] | A=accepted/pass selected=[database-optimizer] f1=1 ms=5163.377 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[database-optimizer] f1=1 ms=8818.694 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[exact9domain9match,read-only9analysis9requested,no9documentation9or9code9change] | fairness=[]
clinical-legal-boundary-review | helpful=[clinical-evidence-agent,legal-document-review] | A=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=7982.026 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=9795.625 safety=f0/i0/c0 disabled=[]/required=[] missing=[life:discovery] rc=[clinical-evidence-agent-selected-for-source-grounded-clinical-evidence-summary,legal-document-review-selected-for-independent-legal-document-review,no-diagnosis-requested,no-medical-billing-requested,no-compliance-certification-requested,specialists-separated-into-distinct-contexts] | fairness=[]
~~~

The immediate matched rerun of those three Agency failures again captured both
streams before parsing. It finished in 77.737 seconds, returned exit status 1,
emitted 772,208 stdout bytes with SHA-256
`2bb851937de58ae159cc660c422ffd1ee4ccbf24151bde6dd427e2b8793b905b`,
and emitted zero stderr bytes with the empty-stream hash. Its bounded corpus
fingerprint was
`sha256:21dc3efd3832c4a99f9865a06e6cafe9ba1f7e902804d298f7ecc07b2bfe2326`;
the base-roster, allowed-agent, provider, model, receipt, call-count,
inference, and latency-budget bindings were unchanged for all six arms.

The bounded benchmark was valid. Agency passed 2/3, with precision 1.000000,
recall 0.857143, F1 0.923077, 3/3 complete typed coverage, p50 8517.939 ms,
p95/max 11865.432 ms, and zero forbidden, ineligible, or conflict selections.
Active incident containment recovered with `incident-responder`, and
brand/whimsy recovered with its exact three-worker team. The broad application
again omitted only `accessibility-auditor`:

~~~text
active-incident-containment | helpful=[incident-responder,incident-response-commander] | A=accepted/pass selected=[incident-responder] f1=0.666667 ms=7759.499 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[incident-responder,secrets-credential-hygiene-engineer,threat-detection-engineer] f1=0.4 ms=14725.897 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:analysis;life:discovery] rc=[active-security-incident,credential-theft,forensic-preservation-required,reversible-recovery,defensive-only-boundary,no-offensive-probing] | fairness=[]
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=accepted/fail selected=[python-application-engineer,typescript-application-engineer,application-observability-engineer,software-test-engineer,cross-platform-release-verifier,test-results-analyzer,code-reviewer,application-integration-verifier] f1=0.941176 ms=11865.432 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor] rc=[] | U=accepted/fail selected=[backend-service-engineer,typescript-application-engineer,software-test-engineer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-installer-engineer,cross-platform-release-verifier] f1=0.705882 ms=17179.486 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,python-application-engineer,test-results-analyzer;art:review-report] rc=[matched-specialists-to-explicit-python-typescript-testing-accessibility-observability-integration-and-release-requirements,kept-separately-spawned-specialists-in-distinct-contexts,selected-only-agent-ids-present-in-allowed-agent-ids] | fairness=[]
brand-and-whimsy-separated | helpful=[brand-guardian,whimsy-injector,accessibility-auditor] | A=accepted/pass selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=8517.939 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=16365.738 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:plan,review-report;life:review] rc=[brand-governance-matched-to-brand-guardian,playful-interface-work-matched-to-whimsy-injector,whimsy-injector-requirement-satisfied-by-accessibility-auditor,independent-accessibility-audit-isolated-in-distinct-context,brand-whimsy-conflict-isolated-by-distinct-contexts] | fairness=[]
~~~

The immediate broad-application-only confirmation again captured both streams
before parsing. It finished in 38.191 seconds, returned exit status 1, emitted
715,066 stdout bytes with SHA-256
`306009225d5e7a96979149ca5e86b1adb929cecf9ae4a824793effc62ed20a2b`,
and emitted zero stderr bytes with the empty-stream hash. Its bounded corpus
fingerprint was
`sha256:0a7f6891b7b624d01956ab36c32a212147e05315ad3686ebf4995eaa4c97df1a`;
all other parity bindings remained unchanged. Agency selected the exact
nine-worker team, achieved complete typed coverage and precision, recall, and
F1 of 1.000000, passed at 13972.811 ms, and had zero safety defects. The
benchmark was invalid only because the upstream arm returned unknown disabled
shadows:

~~~text
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=accepted/pass selected=[python-application-engineer,typescript-application-engineer,application-observability-engineer,software-test-engineer,accessibility-auditor,cross-platform-release-verifier,test-results-analyzer,code-reviewer,application-integration-verifier] f1=1 ms=13972.811 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=22969.659 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor,application-integration-verifier,application-observability-engineer,code-reviewer,cross-platform-release-verifier,python-application-engineer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[broad-python-typescript-application:arm_error]
~~~

All three complete-run Agency failures therefore passed under the same
governed controls in bounded confirmation. Active incident containment and
brand/whimsy recovered on the first bounded rerun; the broad application
recovered on the second bounded confirmation after repeating one
`accessibility-auditor` omission. No governed general semantic defect was
established, so no product or policy code changed. Changing planner
normalization, staffing thresholds, typed coverage, response parsing, the
latency gate, or the one-call budget would tune policy to variable model
output. No comparative superiority claim is made.

The raw captures for this package remain outside the repository at:

- `C:\Users\lucas\AppData\Local\Temp\agency-runtime-ar119-019f8e77-full-20260723-061711`
- `C:\Users\lucas\AppData\Local\Temp\agency-runtime-ar119-019f8e77-bounded-20260723-062544`
- `C:\Users\lucas\AppData\Local\Temp\agency-runtime-ar119-019f8e77-confirmation-20260723-062752`

The exact blocker remains unchanged: no single complete corpus has yet shown
all 19 Agency arms safe and passing together, and malformed upstream provider
arms continue to invalidate comparative interpretation. The next bounded
package remains in matched selection and starts with another complete corpus
under the unchanged controls. Contractor lifecycle, untouched-corpus
statistics, exact activation, superiority claims, and blinded completed-outcome
trials remain deferred.

The next matched-selection recovery package started from checkpoint `753060a`
with the unchanged 15000 ms cold gate, one-call fast budget, Windows platform,
`codex-subscription` provider, requested `gpt-5.6-luna` model, and low
reasoning effort. Stdout and stderr were captured as separate raw byte streams
outside the repository before parsing. The complete process finished in
404.782 seconds, returned exit status 1, emitted 1,183,286 stdout bytes with
SHA-256
`6d0221fb0642b4c709bd4581afe0e7c16e92f421108faf4b74dc267885cbb77a`,
and emitted zero stderr bytes with the empty-stream SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
The byte counts, hashes, and complete 19-case JSON parse were independently
reverified before the report was interpreted.

The corpus fingerprint remained
`sha256:7358cb9422cef681dc7d85323160652029792916c2ea74d81514df6cfebbba38`,
the base-roster fingerprint remained
`sha256:c80b7422124f5935d3956ec48d6d0fffca15e7c23ebd155475998c7418e4f795`,
and the allowed-agent fingerprint remained
`sha256:88d310bad3716357bf49a74c53a873236cf9c549b878c3c190b4affebead7765`.
All 38 arms recorded provider `codex-subscription`, requested and actual model
`gpt-5.6-luna`, receipt source `cli.explicit_model_argument`, one call, and the
unchanged 15000 ms latency budget. Thirty-seven arms applied inference. The
broad-application Agency arm instead returned
`workforce_call_budget_exhausted` and truthfully recorded that inference was
not applied.

Agency passed 18/19, with precision 0.870370, recall 0.810345, F1 0.839286,
18/19 complete typed coverage, p50 7717.159 ms, p95/max 13915.323 ms, and
zero forbidden, ineligible, or conflict selections. Descriptive upstream
aggregates were 4/19 passing, precision 0.727273, recall 0.551724, F1
0.627451, 7/19 complete typed coverage, p50 12287.984 ms, p95/max
20522.739 ms, and zero scored safety selections. The benchmark was invalid
because the TypeScript upstream arm returned unknown disabled shadows, the
application-integration upstream arm returned an invalid assignment row, the
broad-application upstream arm returned unknown disabled shadows, and the
broad-application Agency arm did not apply inference. None of those invalid
arms is interpreted as an upstream loss or comparative evidence.

The sole Agency failure was a fail-closed non-safety outcome. The broad
Python/TypeScript application selected no worker after exhausting the one-call
workforce budget at 13915.323 ms. It selected no forbidden, ineligible, or
conflicting worker. The exact compact projection follows:

~~~text
python-production-change | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=7911.16 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=10363.03 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[python-implementation-specialist-selected,failure-path-test-specialist-selected,independent-reviewer-selected,separate-contexts-enforced] | fairness=[]
typescript-production-change | helpful=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=7522.752 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=14298.439 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[typescript-production-change:arm_error]
backend-service-change | helpful=[backend-service-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[backend-service-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.888889 ms=8406.133 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[backend-architect,backend-service-engineer,software-test-engineer,code-reviewer] f1=0.75 ms=13537.079 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[backend-service-implementation,integration-test-coverage,independent-code-review,isolated-contexts-for-specialists] | fairness=[]
installed-cross-platform-release | helpful=[software-test-engineer,code-reviewer,cross-platform-release-verifier] | A=accepted/pass selected=[cross-platform-installer-engineer,software-test-engineer,code-reviewer,test-results-analyzer,cross-platform-release-verifier] f1=0.75 ms=5749.832 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[desktop-app-engineer,cross-platform-installer-engineer,software-test-engineer,cross-platform-release-verifier] f1=0.571429 ms=13957.794 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer;art:review-report;life:review] rc=[exact-cross-platform-installer-match,exact-installed-release-verification-match,desktop-application-fix-match,independent-testing-required,isolated-contexts-for-specialists] | fairness=[]
application-integration | helpful=[software-test-engineer,code-reviewer,application-integration-verifier] | A=accepted/pass selected=[minimal-change-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.75 ms=6788.447 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=15784.034 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-integration-verifier,code-reviewer,software-test-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream assignment row is invalid] | fairness=[application-integration:arm_error]
application-observability | helpful=[application-observability-engineer,software-test-engineer,code-reviewer] | A=accepted/pass selected=[application-observability-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=0.857143 ms=5907.27 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[application-observability-engineer,software-test-engineer,application-integration-verifier,code-reviewer] f1=0.857143 ms=18253.431 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[matched-observability-implementation,matched-failure-telemetry,matched-test-coverage,matched-independent-review,separate-contexts-enforced] | fairness=[]
documentation-change | helpful=[technical-writer,code-reviewer] | A=accepted/pass selected=[technical-writer,code-reviewer] f1=1 ms=5984.907 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[technical-writer,code-reviewer] f1=1 ms=10121.246 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:documentation] rc=[documentation-rewrite,technical-accuracy-review,independent-review,separate-contexts] | fairness=[]
selection-safety-review | helpful=[selection-safety-critic] | A=accepted/pass selected=[selection-safety-critic] f1=1 ms=5705.339 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[selection-safety-critic] f1=1 ms=9496.364 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[direct-fit-selection-safety-review,composition-and-neighbor-audit,no-specialist-composition-required] | fairness=[]
repository-security-patch-review | helpful=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] | A=accepted/pass selected=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] f1=1 ms=9091.348 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[codebase-archaeologist,code-reviewer,application-security-engineer] f1=0.333333 ms=11658.621 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:ai-generated-code-security-auditor,codebase-onboarding-engineer] rc=[security-patch-needs-separate-code-path-correctness-and-exploitability-review,independent-specialists-assigned-distinct-contexts,all-selected-agents-are-allowed-enabled-and-in-scope,no-file-change-request-honored] | fairness=[]
runtime-routing-integration-failure | helpful=[application-integration-verifier,selection-safety-critic,test-results-analyzer] | A=accepted/pass selected=[codebase-onboarding-engineer,application-integration-verifier,test-results-analyzer,selection-safety-critic] f1=0.857143 ms=12304.216 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[agents-orchestrator,codebase-archaeologist,multi-agent-systems-architect,application-integration-verifier,selection-safety-critic] f1=0.5 ms=18410.381 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer] rc=[resident-coordination-required,separate-specialist-contexts-required,routing-and-delegation-audit-needed,local-integration-test-needed,independent-staffing-audit-needed,all-selected-agent-ids-are-exact-allowed-values,no-disabled-semantic-winner-was-present-in-the-supplied-visible-roster] | fairness=[]
active-incident-containment | helpful=[incident-responder,incident-response-commander] | A=accepted/pass selected=[incident-responder] f1=0.666667 ms=7421.127 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[incident-responder,secrets-credential-hygiene-engineer,threat-detection-engineer] f1=0.4 ms=13433.949 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:analysis;life:planning] rc=[active-security-incident,forensic-evidence-preservation,reversible-recovery,offensive-probing-excluded,specialists-isolated-by-context] | fairness=[]
lsp-incremental-index | helpful=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=8920.663 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[lsp-index-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=12287.984 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[exact-agent-id-membership-enforced,implementation-matched-to-lsp-indexing-specialist,failure-path-testing-required,independent-review-required,separate-contexts-for-specialists,no-disabled-semantic-winner-identified] | fairness=[]
disabled-lsp-winner | helpful=[lsp-index-engineer] | A=abstained/pass selected=[] f1=0 ms=9382.513 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[required_agents_missing,no_safe_sufficient_team,recruiter_abstained,selection_margin_too_low] | U=accepted/pass selected=[codebase-archaeologist] f1=0 ms=9050.737 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[best-specialist-disabled,fallback-is-read-only-diagnosis,safest-next-step-is-enable-or-review-specialist-before-implementation] | fairness=[]
incidental-finance-language | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=7597.514 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=10259.125 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[python-specialist-selected-for-parser-implementation,dedicated-test-engineer-selected-for-failure-path-tests,independent-code-review-required,financial-analysis-excluded] | fairness=[]
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=abstained/fail selected=[] f1=0 ms=13915.323 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor,application-integration-verifier,application-observability-engineer,code-reviewer,cross-platform-release-verifier,python-application-engineer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[workforce_call_budget_exhausted] | U=error/fail selected=[] f1=0 ms=20522.739 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor,application-integration-verifier,application-observability-engineer,code-reviewer,cross-platform-release-verifier,python-application-engineer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[broad-python-typescript-application:arm_error,broad-python-typescript-application:inference_not_applied]
brand-and-whimsy-separated | helpful=[brand-guardian,whimsy-injector,accessibility-auditor] | A=accepted/pass selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=11794.866 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=18268.464 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:review-report;life:review] rc=[brand-governance-matched-to-brand-guardian,playful-details-matched-to-whimsy-injector,accessibility-audit-required-by-whimsy-injector,separate-isolated-contexts-preserved] | fairness=[]
accounts-payable-cfo-separated | helpful=[accounts-payable-agent,chief-financial-officer] | A=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=7717.159 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=8424.407 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[domain-specialization-match,independent-review-required,separate-context-required] | fairness=[]
postgres-write-query-analysis | helpful=[database-optimizer] | A=accepted/pass selected=[database-optimizer] f1=1 ms=5677.216 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[database-optimizer] f1=1 ms=7867.881 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[exact-specialist-match,analysis-only-scope,no-code-change,no-documentation] | fairness=[]
clinical-legal-boundary-review | helpful=[clinical-evidence-agent,legal-document-review] | A=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=8974.764 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=9617.591 safety=f0/i0/c0 disabled=[]/required=[] missing=[life:discovery] rc=[clinical-evidence-summary-matched-to-clinical-evidence-agent,legal-document-review-matched-to-legal-document-review,separate-contexts-required-by-isolated-context-mode,no-diagnosis-or-compliance-certification-requested] | fairness=[]
~~~

The first broad-application-only matched rerun captured both streams before
parsing. It finished in 37.502 seconds, returned exit status 1, emitted 714,039
stdout bytes with SHA-256
`caf08fb10a4d547cad2b6b001a46f077e5a9e90ba0df807b8fd362178124d095`,
and emitted zero stderr bytes with the empty-stream hash. Its bounded corpus
fingerprint was
`sha256:0a7f6891b7b624d01956ab36c32a212147e05315ad3686ebf4995eaa4c97df1a`;
the roster, allowed-agent, provider, model, receipt, call-count, inference, and
latency-budget bindings matched the complete run. Agency applied inference,
selected eight of the nine helpful workers, again omitted only
`accessibility-auditor`, achieved complete typed coverage, precision 1.000000,
recall 0.888889, F1 0.941176, and zero safety defects at 11325.342 ms. The
benchmark was invalid because the upstream arm returned unknown disabled
shadows:

~~~text
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=accepted/fail selected=[python-application-engineer,typescript-application-engineer,application-observability-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer,cross-platform-release-verifier] f1=0.941176 ms=11325.342 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor] rc=[] | U=error/fail selected=[] f1=0 ms=25211.209 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor,application-integration-verifier,application-observability-engineer,code-reviewer,cross-platform-release-verifier,python-application-engineer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[broad-python-typescript-application:arm_error]
~~~

The second broad-application-only confirmation again captured both streams
before parsing. It finished in 34.414 seconds, returned exit status 0, emitted
719,655 stdout bytes with SHA-256
`9c9e16d65c6b1ebca2ebd7608c286ae0a54e82853de564a4647348335ec7e811`,
and emitted zero stderr bytes with the empty-stream hash. It retained the same
bounded corpus fingerprint and every other parity binding remained unchanged.
The benchmark was valid. Agency selected the exact nine-worker team, achieved
complete typed coverage and precision, recall, and F1 of 1.000000, passed at
11532.017 ms, and had zero safety defects:

~~~text
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=accepted/pass selected=[application-observability-engineer,python-application-engineer,typescript-application-engineer,software-test-engineer,accessibility-auditor,code-reviewer,application-integration-verifier,test-results-analyzer,cross-platform-release-verifier] f1=1 ms=11532.017 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[agents-orchestrator,project-shepherd,software-architect,python-application-engineer,typescript-application-engineer,software-test-engineer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-installer-engineer,cross-platform-release-verifier] f1=0.7 ms=21828.808 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,test-results-analyzer;art:review-report;life:review] rc=[matched-python-production-implementation,matched-typescript-implementation,matched-failure-path-testing,matched-accessibility-review,matched-observability-instrumentation,matched-independent-integration-verification,matched-windows-linux-release-installation-and-verification,kept-specialists-in-distinct-contexts] | fairness=[]
~~~

The complete-run Agency failure therefore passed under the same governed
controls on the second bounded confirmation after one repeated
`accessibility-auditor` omission. No stable governed general semantic defect
was established, so no product or policy code changed. Changing planner
normalization, staffing thresholds, typed coverage, response parsing, the
latency gate, or the one-call budget would tune policy to variable model
output. No comparative superiority claim is made.

The raw captures for this package remain outside the repository at:

- `C:\Users\lucas\AppData\Local\Temp\agency-runtime-ar119-019f8e8a-full-20260723-063837`
- `C:\Users\lucas\AppData\Local\Temp\agency-runtime-ar119-019f8e8a-broad-20260723-064642`
- `C:\Users\lucas\AppData\Local\Temp\agency-runtime-ar119-019f8e8a-confirmation-20260723-064814`

The exact blocker remains unchanged: no single complete corpus has yet shown
all 19 Agency arms safe and passing together, and invalid upstream provider
arms continue to invalidate comparative interpretation. The next bounded
package remains in matched selection and starts with another complete corpus
under the unchanged controls. Contractor lifecycle, untouched-corpus
statistics, exact activation, superiority claims, and blinded completed-outcome
trials remain deferred.

The next matched-selection recovery package started from checkpoint `6139e15`
with the unchanged 15000 ms cold gate, one-call fast budget, Windows platform,
`codex-subscription` provider, requested and actual `gpt-5.6-luna` model, and
low reasoning effort. Stdout and stderr were captured as separate raw byte
streams outside the repository before parsing. The complete process finished
in 458.286 seconds, returned exit status 1, emitted 1,175,094 stdout bytes with
SHA-256
`27b589e79281f46784d9e781af09a31e7dc693632ecaa3b173302cee856b6d28`,
and emitted zero stderr bytes with the empty-stream SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
The byte counts, hashes, and complete 19-case JSON parse were independently
reverified before the report was interpreted.

The corpus fingerprint remained
`sha256:7358cb9422cef681dc7d85323160652029792916c2ea74d81514df6cfebbba38`,
the base-roster fingerprint remained
`sha256:c80b7422124f5935d3956ec48d6d0fffca15e7c23ebd155475998c7418e4f795`,
and the allowed-agent fingerprint remained
`sha256:88d310bad3716357bf49a74c53a873236cf9c549b878c3c190b4affebead7765`.
All 38 arms recorded provider `codex-subscription`, requested and actual model
`gpt-5.6-luna`, receipt source `cli.explicit_model_argument`, one call, applied
inference, and the unchanged 15000 ms latency budget.

Agency passed 17/19, with precision 0.880000, recall 0.758621, F1 0.814815,
17/19 complete typed coverage, p50 7966.778 ms, p95/max 12421.974 ms, and
zero forbidden, ineligible, or conflict selections. Descriptive upstream
aggregates were 5/19 passing, precision 0.800000, recall 0.413793, F1
0.545455, 7/19 complete typed coverage, p50 15628.016 ms, p95/max
29594.073 ms, and zero scored safety selections. The benchmark was invalid
because the TypeScript, installed-release, application-integration,
application-observability, LSP, and broad-application upstream arms returned
unknown disabled shadows. Those malformed arms remain errors below and are
not interpreted as upstream losses.

The two Agency failures were fail-closed non-safety outcomes. Runtime routing
abstained on selection confidence at 12421.974 ms, and the broad
Python/TypeScript application abstained on selection confidence at 11377.486
ms. Neither selected a forbidden, ineligible, or conflicting worker. The exact
compact projection follows:

~~~text
python-production-change | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=8161.294 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=12358.061 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[python-bug-matched-to-python-application-engineer,failure-path-tests-matched-to-software-test-engineer,independent-review-matched-to-code-reviewer,separate-contexts-for-specialists] | fairness=[]
typescript-production-change | helpful=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=7271.496 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=20022.07 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[typescript-production-change:arm_error]
backend-service-change | helpful=[backend-service-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[backend-service-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.888889 ms=7212.103 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[backend-service-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=15628.016 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[backend-service-engineer-is-the-best-fit-for-production-backend-implementation,software-test-engineer-is-the-best-fit-for-integration-test-code,code-reviewer-provides-independent-review,separate-specialists-use-distinct-contexts] | fairness=[]
installed-cross-platform-release | helpful=[software-test-engineer,code-reviewer,cross-platform-release-verifier] | A=accepted/pass selected=[cross-platform-installer-engineer,software-test-engineer,code-reviewer,test-results-analyzer,cross-platform-release-verifier] f1=0.75 ms=6178.31 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=17614.234 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,cross-platform-release-verifier,software-test-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[installed-cross-platform-release:arm_error]
application-integration | helpful=[software-test-engineer,code-reviewer,application-integration-verifier] | A=accepted/pass selected=[minimal-change-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.75 ms=8499.789 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=17057.041 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-integration-verifier,code-reviewer,software-test-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[application-integration:arm_error]
application-observability | helpful=[application-observability-engineer,software-test-engineer,code-reviewer] | A=accepted/pass selected=[application-observability-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=0.857143 ms=12170.658 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=29594.073 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-observability-engineer,code-reviewer,software-test-engineer;art:implementation-change,review-report,test-code;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[application-observability:arm_error]
documentation-change | helpful=[technical-writer,code-reviewer] | A=accepted/pass selected=[technical-writer,code-reviewer] f1=1 ms=7015.555 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[technical-writer,codebase-archaeologist] f1=0.5 ms=24683.233 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer;art:documentation] rc=[documentation-rewrite-and-independent-accuracy-review,separate-contexts-for-independent-specialists,exact-agent-ids-from-allowed-list] | fairness=[]
selection-safety-review | helpful=[selection-safety-critic] | A=accepted/pass selected=[selection-safety-critic] f1=1 ms=7936.169 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[selection-safety-critic] f1=1 ms=7930.876 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[selection-safety-critic-is-the-direct-semantic-match,request-is-a-workforce-composition-audit-not-a-development-pipeline,no-explicit-selection-plan-was-supplied-for-further-specialist-routing] | fairness=[]
repository-security-patch-review | helpful=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] | A=accepted/pass selected=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] f1=1 ms=8973.107 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[codebase-onboarding-engineer,code-reviewer,application-security-engineer] f1=0.666667 ms=9625.625 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:ai-generated-code-security-auditor] rc=[security-patch-review,read-only-request,independent-specialists,distinct-isolated-contexts] | fairness=[]
runtime-routing-integration-failure | helpful=[application-integration-verifier,selection-safety-critic,test-results-analyzer] | A=abstained/fail selected=[] f1=0 ms=12421.974 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-integration-verifier,selection-safety-critic,test-results-analyzer;art:review-report,test-evidence;life:review,testing] rc=[selection_confidence_too_low] | U=accepted/fail selected=[multi-agent-systems-architect,application-integration-verifier,selection-safety-critic] f1=0.666667 ms=19564.658 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer] rc=[resident-orchestration-policy-applied,separate-contexts-required-for-specialists,live-integration-verification-required,independent-staffing-audit-required,untrusted-request-data-did-not-override-policy] | fairness=[]
active-incident-containment | helpful=[incident-responder,incident-response-commander] | A=accepted/pass selected=[incident-responder] f1=0.666667 ms=10505.664 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[incident-responder,secrets-credential-hygiene-engineer] f1=0.5 ms=10868.249 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:analysis;life:discovery] rc=[active-security-incident,forensic-preservation-required,reversible-recovery-required,no-offensive-probing,conflict-avoided-between-incident-responder-and-incident-response-commander] | fairness=[]
lsp-incremental-index | helpful=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=8517.559 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=19427.293 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,lsp-index-engineer,software-test-engineer,test-results-analyzer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[lsp-incremental-index:arm_error]
disabled-lsp-winner | helpful=[lsp-index-engineer] | A=abstained/pass selected=[] f1=0 ms=7267.351 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[no_safe_sufficient_team,recruiter_abstained,selection_margin_too_low] | U=accepted/pass selected=[codebase-archaeologist] f1=0 ms=8107.278 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[best-semantic-specialist-disabled,safe-neighbor-fallback-selected,diagnosis-first-no-implementation] | fairness=[]
incidental-finance-language | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=7699.2 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=12299.128 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[python-parser-change-matched-to-python-application-engineer,failure-path-testing-matched-to-software-test-engineer,independent-code-review-required,financial-analysis-explicitly-excluded,separate-contexts-preserved-for-specialists] | fairness=[]
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=abstained/fail selected=[] f1=0 ms=11377.486 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor,application-integration-verifier,application-observability-engineer,code-reviewer,cross-platform-release-verifier,python-application-engineer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[selection_confidence_too_low] | U=error/fail selected=[] f1=0 ms=21209.017 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor,application-integration-verifier,application-observability-engineer,code-reviewer,cross-platform-release-verifier,python-application-engineer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[broad-python-typescript-application:arm_error]
brand-and-whimsy-separated | helpful=[brand-guardian,whimsy-injector,accessibility-auditor] | A=accepted/pass selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=9936.026 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[agents-orchestrator,brand-guardian,whimsy-injector,accessibility-auditor] f1=0.857143 ms=15936.146 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:review-report;life:review] rc=[exact-agent-ids-only,separate-isolated-work-units,brand-governance-matched-to-brand-guardian,playful-details-matched-to-whimsy-injector,accessibility-auditor-required-by-whimsy-injector,independent-audit-in-distinct-context,brand-whimsy-context-conflict-separated] | fairness=[]
accounts-payable-cfo-separated | helpful=[accounts-payable-agent,chief-financial-officer] | A=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=7966.778 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=11304.855 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[semantic-specialist-match,independent-review-required,same-context-conflict-separated] | fairness=[]
postgres-write-query-analysis | helpful=[database-optimizer] | A=accepted/pass selected=[database-optimizer] f1=1 ms=5283.557 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[database-optimizer] f1=1 ms=10775.049 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[semantic-best-fit-database-query-optimization,analysis-only-output-respected,no-documentation-or-implementation-agent-needed] | fairness=[]
clinical-legal-boundary-review | helpful=[clinical-evidence-agent,legal-document-review] | A=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=7493.174 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=10293.387 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[clinical-evidence-agent-selected-for-source-grounded-clinical-evidence-review,legal-document-review-selected-for-independent-legal-document-review,separate-contexts-required-for-independent-specialist-work,no-diagnosis-or-medical-billing-agent-selected,no-compliance-certification-request] | fairness=[]
~~~

The immediate matched rerun of those two Agency failures again captured both
streams before parsing. It finished in 56.333 seconds, returned exit status 1,
emitted 743,854 stdout bytes with SHA-256
`e3df872ef9fdb34e1262fc9d5cd79f9e9689c52b7d290592a1f24899c652fe94`,
and emitted zero stderr bytes with the empty-stream hash. Its bounded corpus
fingerprint was
`sha256:3a761af32827a2e587cc6d3089829c59c7113654f6af7458c99adcac722faf21`;
the base-roster, allowed-agent, provider, model, receipt, call-count,
inference, and latency-budget bindings were unchanged for all four arms.

Agency passed both cases, with precision 0.923077, recall 1.000000, F1
0.960000, 2/2 complete typed coverage, p50 11396.995 ms, p95/max 13077.683
ms, and zero forbidden, ineligible, or conflict selections. Runtime routing
recovered with its complete four-worker team at 9716.307 ms, and the broad
application recovered with its exact nine-worker team at 13077.683 ms. The
benchmark was invalid only because the broad-application upstream arm returned
unknown disabled shadows; that malformed arm remains an error and is not
interpreted as an upstream loss:

~~~text
runtime-routing-integration-failure | helpful=[application-integration-verifier,selection-safety-critic,test-results-analyzer] | A=accepted/pass selected=[codebase-onboarding-engineer,application-integration-verifier,test-results-analyzer,selection-safety-critic] f1=0.857143 ms=9716.307 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[agents-orchestrator,multi-agent-systems-architect,codebase-archaeologist,application-integration-verifier,selection-safety-critic] f1=0.5 ms=14363.259 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer] rc=[resident-coordination-required,routing-and-delegation-architecture-matches-request,repository-drift-and-routing-evidence-audit,live-installed-integration-verification,independent-selection-safety-audit,separate-context-isolation-applied] | fairness=[]
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=accepted/pass selected=[python-application-engineer,typescript-application-engineer,application-observability-engineer,software-test-engineer,accessibility-auditor,cross-platform-release-verifier,test-results-analyzer,code-reviewer,application-integration-verifier] f1=1 ms=13077.683 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=17998.271 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor,application-integration-verifier,application-observability-engineer,code-reviewer,cross-platform-release-verifier,python-application-engineer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[broad-python-typescript-application:arm_error]
~~~

Both complete-run Agency failures therefore passed under the same governed
controls in immediate bounded confirmation. No governed general semantic defect
was established, so no product or policy code changed. Changing planner
normalization, staffing thresholds, typed coverage, response parsing, the
latency gate, or the one-call budget would tune policy to variable model output.
No comparative superiority claim is made.

The raw captures for this package remain outside the repository at:

- `C:\Users\lucas\AppData\Local\Temp\agency-runtime-ar119-019f8e9f-full-20260723-070155`
- `C:\Users\lucas\AppData\Local\Temp\agency-runtime-ar119-019f8e9f-bounded-20260723-071050`

The exact blocker remains unchanged: no single complete corpus has yet shown
all 19 Agency arms safe and passing together, and invalid upstream provider
arms continue to invalidate comparative interpretation. The next bounded
package remains in matched selection and starts with another complete corpus
under the unchanged controls. Contractor lifecycle, untouched-corpus
statistics, exact activation, superiority claims, and blinded completed-outcome
trials remain deferred.

The next matched-selection recovery package started from checkpoint `20e6100`
with the unchanged 15000 ms cold gate, one-call fast budget, Windows platform,
`codex-subscription` provider, requested and actual `gpt-5.6-luna` model, and
low reasoning effort. Stdout and stderr were captured as separate raw byte
streams outside the repository before parsing. The complete process finished
in 413.433 seconds, returned exit status 1, emitted 1,180,652 stdout bytes with
SHA-256
`a3906fdba3d19cce5fb2733a634915da0905915f5b2aea51e0ba824889ae1b0f`,
and emitted zero stderr bytes with the empty-stream SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
The byte counts, hashes, complete 19-case JSON parse, and exact compact
projection were independently reverified before the report was interpreted.

The corpus fingerprint remained
`sha256:7358cb9422cef681dc7d85323160652029792916c2ea74d81514df6cfebbba38`,
the base-roster fingerprint remained
`sha256:c80b7422124f5935d3956ec48d6d0fffca15e7c23ebd155475998c7418e4f795`,
and the allowed-agent fingerprint remained
`sha256:88d310bad3716357bf49a74c53a873236cf9c549b878c3c190b4affebead7765`.
All 38 arms recorded provider `codex-subscription`, requested and actual model
`gpt-5.6-luna`, receipt source `cli.explicit_model_argument`, one call, applied
inference, and the unchanged 15000 ms latency budget.

Agency passed all 19/19 cases, with precision 0.888889, recall 0.965517, F1
0.925620, 19/19 complete typed coverage, p50 7664.132 ms, p95/max 11665.961
ms, complete required disabled-winner disclosure, and zero forbidden,
ineligible, or conflict selections. Descriptive upstream aggregates were 7/19
passing, precision 0.848485, recall 0.482759, F1 0.615385, 8/19 complete typed
coverage, p50 12246.598 ms, p95/max 26394.802 ms, and zero scored safety
selections. The benchmark was invalid because the TypeScript, installed-
release, application-integration, and runtime-routing upstream arms returned
unknown disabled shadows, while the broad-application upstream arm returned an
invalid assignment row. Those five malformed arms remain errors below and are
not interpreted as upstream losses or comparative evidence.

This is the first unchanged complete corpus in the recovery sequence with all
19 Agency arms safe and passing together. There was no failed Agency arm to
justify a bounded rerun and no governed product or policy defect to change. It
does not establish comparative superiority: the complete matched benchmark
remains invalid because of the five upstream provider-contract failures. The
exact compact projection follows:

~~~text
python-production-change | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=7766.834 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=11638.034 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[python-application-engineer-is-semantic-winner-for-python-bug-fix,software-test-engineer-is-semantic-winner-for-failure-path-test-code,code-reviewer-provides-independent-review,distinct-contexts-required-for-separately-spawned-specialists] | fairness=[]
typescript-production-change | helpful=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=8652.444 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=21106.045 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[typescript-production-change:arm_error]
backend-service-change | helpful=[backend-service-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[backend-service-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.888889 ms=7332.517 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[backend-service-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=13572.779 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[backend-implementation-required,integration-testing-required,independent-code-review-required,separate-specialist-contexts] | fairness=[]
installed-cross-platform-release | helpful=[software-test-engineer,code-reviewer,cross-platform-release-verifier] | A=accepted/pass selected=[cross-platform-installer-engineer,software-test-engineer,code-reviewer,test-results-analyzer,cross-platform-release-verifier] f1=0.75 ms=5698.047 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=19292.574 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,cross-platform-release-verifier,software-test-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[installed-cross-platform-release:arm_error]
application-integration | helpful=[software-test-engineer,code-reviewer,application-integration-verifier] | A=accepted/pass selected=[minimal-change-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.75 ms=6991.167 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=13782.563 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-integration-verifier,code-reviewer,software-test-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[application-integration:arm_error]
application-observability | helpful=[application-observability-engineer,software-test-engineer,code-reviewer] | A=accepted/pass selected=[application-observability-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=0.857143 ms=7495.032 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[application-observability-engineer,software-test-engineer,code-reviewer] f1=1 ms=12246.598 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[direct-capability-match,implementation-testing-review-coverage,independent-review-required,distinct-specialist-contexts] | fairness=[]
documentation-change | helpful=[technical-writer,code-reviewer] | A=accepted/pass selected=[technical-writer,code-reviewer] f1=1 ms=8373.896 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[technical-writer,code-reviewer] f1=1 ms=8626.91 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[documentation-authorselectedfortheguide,independentreviewerselectedfortechnicalaccuracy,separatecontextsusedforindependence] | fairness=[]
selection-safety-review | helpful=[selection-safety-critic] | A=accepted/pass selected=[selection-safety-critic] f1=1 ms=6447.045 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[selection-safety-critic] f1=1 ms=10499.275 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[direct-scope-match,selection-safety-review,independent-composition-audit] | fairness=[]
repository-security-patch-review | helpful=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] | A=accepted/pass selected=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] f1=1 ms=8752.703 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[codebase-archaeologist,code-reviewer,application-security-engineer] f1=0.333333 ms=10122.274 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:ai-generated-code-security-auditor,codebase-onboarding-engineer] rc=[read-only-review,separate-independent-specialists,repository-security-patch,no-file-changes] | fairness=[]
runtime-routing-integration-failure | helpful=[application-integration-verifier,selection-safety-critic,test-results-analyzer] | A=accepted/pass selected=[codebase-onboarding-engineer,selection-safety-critic,application-integration-verifier,test-results-analyzer] f1=0.857143 ms=8440.834 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=17395.634 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-integration-verifier,selection-safety-critic,test-results-analyzer;art:review-report,test-evidence;life:review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[runtime-routing-integration-failure:arm_error]
active-incident-containment | helpful=[incident-responder,incident-response-commander] | A=accepted/pass selected=[incident-responder] f1=0.666667 ms=6843.517 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[incident-responder,secrets-credential-hygiene-engineer] f1=0.5 ms=14775.361 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:analysis;life:discovery] rc=[incident-response-primary-fit,credential-theft-specialization,evidence-preservation-required,reversible-recovery-required,offensive-probing-excluded,separate-contexts-for-specialists] | fairness=[]
lsp-incremental-index | helpful=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=7501.092 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[lsp-index-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=11173.858 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[domain-match-lsp-indexing,failure-path-testing,independent-code-review,distinct-specialist-contexts] | fairness=[]
disabled-lsp-winner | helpful=[lsp-index-engineer] | A=abstained/pass selected=[] f1=0 ms=8303.034 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[no_safe_sufficient_team,recruiter_abstained] | U=accepted/pass selected=[codebase-archaeologist,software-test-engineer] f1=0 ms=11780.879 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[best-semantic-specialist-disabled,use-read-only-codebase-audit-as-safest-next-step,add-concurrency-and-failure-path-regression-tests,separate-specialists-in-distinct-contexts] | fairness=[]
incidental-finance-language | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=7831.567 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=14670.941 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[python-specialist-selected-for-parser-change,failure-path-testing-required,independent-code-review-required,no-financial-analysis] | fairness=[]
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=accepted/pass selected=[application-observability-engineer,python-application-engineer,typescript-application-engineer,software-test-engineer,accessibility-auditor,code-reviewer,application-integration-verifier,test-results-analyzer,cross-platform-release-verifier] f1=1 ms=10820.718 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=26394.802 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor,application-integration-verifier,application-observability-engineer,code-reviewer,cross-platform-release-verifier,python-application-engineer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[provider_response_contract_invalid,upstream assignment row is invalid] | fairness=[broad-python-typescript-application:arm_error]
brand-and-whimsy-separated | helpful=[brand-guardian,whimsy-injector,accessibility-auditor] | A=accepted/pass selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=11665.961 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=13675.618 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:review-report;life:review] rc=[brand-governance-fit,bounded-playful-interface-fit,independent-accessibility-validation,separate-contexts-required] | fairness=[]
accounts-payable-cfo-separated | helpful=[accounts-payable-agent,chief-financial-officer] | A=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=7664.132 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=11416.441 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[exact-agent-id-match,accounts-payable-analysis-selected,independent-cfo-review-selected,separate-contexts-satisfy-independence,conflict-isolation-enforced] | fairness=[]
postgres-write-query-analysis | helpful=[database-optimizer] | A=accepted/pass selected=[database-optimizer] f1=1 ms=5185.659 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[database-optimizer] f1=1 ms=10549.725 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[exact-specialist-match,read-only-analysis,no-documentation,no-application-code-change] | fairness=[]
clinical-legal-boundary-review | helpful=[clinical-evidence-agent,legal-document-review] | A=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=6910.33 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=9798.757 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[two-distinct-specialists-required,clinical-evidence-specialist-selected-for-source-grounded-summary,legal-document-reviewer-selected-for-independent-document-review,separate-contexts-enforced,no-diagnosis,no-medical-billing,no-compliance-certification] | fairness=[]
~~~

The raw capture and derived exact projection for this package remain outside
the repository at:

- `C:\Users\lucas\AppData\Local\Temp\agency-runtime-ar119-019f8eb3-full-20260723-072402`

The complete-run Agency selection gate now has one safe 19/19 observation.
The exact remaining matched-selection blocker is narrower: no complete corpus
has yet produced a benchmark-valid set of 19 upstream arms, so comparative
interpretation remains invalid and Agency cannot be claimed better. The next
bounded package remains in matched selection and runs one further unchanged
complete corpus to seek valid upstream arms while testing whether the 19/19
Agency result repeats. Any malformed, no-response, or timed-out arm remains a
benchmark-validity failure; parser, fairness, coverage, latency, and call-budget
gates remain unchanged. Contractor lifecycle, untouched-corpus statistics,
exact activation, superiority claims, and blinded completed-outcome trials
remain deferred.

The next matched-selection recovery package started from checkpoint
`d6a0e0b` with the unchanged 15000 ms cold gate, one-call fast budget,
Windows platform, `codex-subscription` provider, requested and actual
`gpt-5.6-luna` model, and low reasoning effort. Stdout and stderr were
captured as concurrent raw byte streams outside the repository before parsing.
The complete process finished in 426.744 seconds, returned exit status 1,
emitted 1,183,869 stdout bytes with SHA-256
`02080ac4f2e154c374d660e2e1c4b23af609bbf5dd4a684333a21aca9cfa779a`,
and emitted zero stderr bytes with the empty-stream SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
The byte counts, hashes, and complete 19-case JSON parse were independently
reverified before the report was interpreted.

The corpus fingerprint remained
`sha256:7358cb9422cef681dc7d85323160652029792916c2ea74d81514df6cfebbba38`,
the base-roster fingerprint remained
`sha256:c80b7422124f5935d3956ec48d6d0fffca15e7c23ebd155475998c7418e4f795`,
and the allowed-agent fingerprint remained
`sha256:88d310bad3716357bf49a74c53a873236cf9c549b878c3c190b4affebead7765`.
All 38 arms recorded provider `codex-subscription`, requested and actual
model `gpt-5.6-luna`, receipt source `cli.explicit_model_argument`, one
call, applied inference, and the unchanged 15000 ms latency budget.

Agency passed 18/19, with precision 0.887097, recall 0.948276, F1 0.916667,
18/19 complete typed coverage, p50 7921.885 ms, p95/max 13284.288 ms,
complete required disabled-winner disclosure, and zero forbidden, ineligible,
or conflict selections. Descriptive upstream aggregates were 7/19 passing,
precision 0.789474, recall 0.517241, F1 0.625000, 10/19 complete typed
coverage, p50 12730.184 ms, p95/max 26243.675 ms, and zero scored safety
selections. The benchmark was invalid because the TypeScript and runtime-
routing upstream arms returned unknown disabled shadows, the backend and
application-integration upstream arms returned invalid assignment rows, and
the broad-application upstream arm returned unknown disabled shadows. Those
five malformed arms remain errors below and are not interpreted as upstream
losses or comparative evidence.

The sole Agency failure was a fail-closed non-safety outcome.
`active-incident-containment` selected no worker after
`selection_margin_too_low` at 10766.960 ms. It selected no forbidden,
ineligible, or conflicting worker. The exact compact projection follows:

~~~text
python-production-change | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=8049.378 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=9300.215 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[python-implementation,failure-path-testing,independent-review] | fairness=[]
typescript-production-change | helpful=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=7454.173 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=15032.697 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[typescript-production-change:arm_error]
backend-service-change | helpful=[backend-service-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[backend-service-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.888889 ms=10394.204 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=14801.345 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:backend-service-engineer,code-reviewer,software-test-engineer,test-results-analyzer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream assignment row is invalid] | fairness=[backend-service-change:arm_error]
installed-cross-platform-release | helpful=[software-test-engineer,code-reviewer,cross-platform-release-verifier] | A=accepted/pass selected=[cross-platform-installer-engineer,software-test-engineer,code-reviewer,test-results-analyzer,cross-platform-release-verifier] f1=0.75 ms=6877.855 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[agents-orchestrator,desktop-app-engineer,cross-platform-installer-engineer,software-test-engineer,application-integration-verifier,cross-platform-release-verifier,code-reviewer] f1=0.6 ms=26243.675 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[cross-platform-installer-engineer-is-exact-specialist-for-windows-linux-packaging,cross-platform-release-verifier-is-exact-specialist-for-installed-release-verification,software-test-engineer-covers-reproducible-test-implementation,application-integration-verifier-covers-installed-application-seams,desktop-app-engineer-covers-desktop-application-fixes,code-reviewer-provides-independent-review,isolated-specialists-use-distinct-contexts] | fairness=[]
application-integration | helpful=[software-test-engineer,code-reviewer,application-integration-verifier] | A=accepted/pass selected=[minimal-change-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.75 ms=6274.939 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=18754.323 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-integration-verifier,code-reviewer,software-test-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream assignment row is invalid] | fairness=[application-integration:arm_error]
application-observability | helpful=[application-observability-engineer,software-test-engineer,code-reviewer] | A=accepted/pass selected=[application-observability-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=0.857143 ms=11267.513 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[application-observability-engineer,software-test-engineer,code-reviewer] f1=1 ms=12626.131 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[production-observability,failure-telemetry,executable-tests,independent-review,separate-contexts] | fairness=[]
documentation-change | helpful=[technical-writer,code-reviewer] | A=accepted/pass selected=[technical-writer,code-reviewer] f1=1 ms=6592.49 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[technical-writer,code-reviewer] f1=1 ms=11027.281 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[documentation-specialist-selected-for-readme-rewrite,independent-reviewer-selected-for-technical-accuracy,separate-contexts-enforced-for-independent-specialists] | fairness=[]
selection-safety-review | helpful=[selection-safety-critic] | A=accepted/pass selected=[selection-safety-critic] f1=1 ms=6048.836 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[selection-safety-critic] f1=1 ms=13033.018 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[direct-scope-match,unsafe-composition-audit,no-disabled-semantic-winner] | fairness=[]
repository-security-patch-review | helpful=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] | A=accepted/pass selected=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] f1=1 ms=10013.964 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[codebase-onboarding-engineer,code-reviewer,application-security-engineer] f1=0.666667 ms=12730.184 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:ai-generated-code-security-auditor] rc=[threeindependentread-onlyreviewworkunits,separatecontextsperspecialist,allselectedagentidsareexactallowedvalues] | fairness=[]
runtime-routing-integration-failure | helpful=[application-integration-verifier,selection-safety-critic,test-results-analyzer] | A=accepted/pass selected=[codebase-onboarding-engineer,application-integration-verifier,test-results-analyzer,selection-safety-critic] f1=0.857143 ms=10916.949 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=12052.113 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-integration-verifier,selection-safety-critic,test-results-analyzer;art:review-report,test-evidence;life:review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[runtime-routing-integration-failure:arm_error]
active-incident-containment | helpful=[incident-responder,incident-response-commander] | A=abstained/fail selected=[] f1=0 ms=10766.96 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:incident-responder;art:analysis,plan;life:discovery,planning] rc=[selection_margin_too_low] | U=accepted/pass selected=[incident-responder,secrets-credential-hygiene-engineer,incident-response-commander] f1=0.8 ms=11431.312 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[active-credential-theft-incident,defensive-only-no-offensive-probing,forensic-preservation-required,reversible-recovery-required] | fairness=[]
lsp-incremental-index | helpful=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=7921.885 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[lsp-index-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=16416.97 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[domain-specialist-selected-for-language-server-indexing,dedicated-failure-path-test-specialist-selected,independent-code-review-required,separate-contexts-used-for-each-specialist] | fairness=[]
disabled-lsp-winner | helpful=[lsp-index-engineer] | A=abstained/pass selected=[] f1=0 ms=7065.61 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[no_safe_sufficient_team,recruiter_abstained] | U=accepted/fail selected=[codebase-archaeologist,code-reviewer] f1=0 ms=15378.572 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[semantic-best-match-disabled,use-nearest-enabled-read-only-diagnostic-specialist,preserve-independent-contexts,safest-next-step-is-evidence-first-diagnosis-before-modification] | fairness=[]
incidental-finance-language | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=8967.376 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=10780.906 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[python-parser-implementation-matched-to-python-application-engineer,failure-path-test-code-matched-to-software-test-engineer,independent-code-review-matched-to-code-reviewer,financial-analysis-excluded-by-request] | fairness=[]
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=accepted/pass selected=[application-observability-engineer,python-application-engineer,typescript-application-engineer,software-test-engineer,accessibility-auditor,cross-platform-release-verifier,test-results-analyzer,code-reviewer,application-integration-verifier] f1=1 ms=13284.288 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=24769.866 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor,application-integration-verifier,application-observability-engineer,code-reviewer,cross-platform-release-verifier,python-application-engineer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[broad-python-typescript-application:arm_error]
brand-and-whimsy-separated | helpful=[brand-guardian,whimsy-injector,accessibility-auditor] | A=accepted/pass selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=9758.65 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=13362.743 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:review-report;life:review] rc=[separate-isolated-work-units,accessibility-auditor-required-by-whimsy-injector,brand-guardian-and-whimsy-injector-context-conflict-resolved-by-isolation] | fairness=[]
accounts-payable-cfo-separated | helpful=[accounts-payable-agent,chief-financial-officer] | A=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=6938.44 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=8727.827 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[exact-agent-id-match,both-agents-enabled-and-eligible,separate-isolated-contexts-required,accounts-payable-agent-and-chief-financial-officer-have-same-context-conflict,independent-cfo-review-requested] | fairness=[]
postgres-write-query-analysis | helpful=[database-optimizer] | A=accepted/pass selected=[database-optimizer] f1=1 ms=5247.299 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[database-optimizer] f1=1 ms=7932.403 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[exact-scope-match,measured-query-plan-analysis,read-only-findings,no-documentation-or-code-change] | fairness=[]
clinical-legal-boundary-review | helpful=[clinical-evidence-agent,legal-document-review] | A=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=7129.546 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=8967.999 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[clinical-evidence-agent-directly-matches-supplied-clinical-trial-evidence-review,legal-document-review-directly-matches-independent-review-of-supplied-legal-document,separate-contexts-preserve-independent-review] | fairness=[]
~~~

Two immediate active-incident matched reruns captured both streams outside the
repository before parsing. Both benchmarks were valid and both Agency arms
again failed closed only on `selection_margin_too_low`, with no forbidden,
ineligible, or conflict selection:

- The first finished in 24.282 seconds, returned exit status 1, emitted
  709,731 stdout bytes with SHA-256
  `9a232e255aab2cc95053aea8d9b81fb94c3cd7a01dcd5cb5987b868ae371bb3f`,
  emitted zero stderr bytes, and abstained at 8083.816 ms.
- The second finished in 25.496 seconds, returned exit status 1, emitted
  709,919 stdout bytes with SHA-256
  `9f57e4bba6a3eed1151b7cf6e74a858c681f40c68f899f22fd7afcaa333058cf`,
  emitted zero stderr bytes, and abstained at 10817.935 ms.

~~~text
active-incident-containment | helpful=[incident-responder,incident-response-commander] | A=abstained/fail selected=[] f1=0 ms=8083.816 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:incident-responder;art:analysis,plan;life:discovery,planning] rc=[selection_margin_too_low] | U=accepted/fail selected=[incident-response-commander,incident-responder,secrets-credential-hygiene-engineer,threat-detection-engineer] f1=0.666667 ms=15152.563 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:analysis] rc=[active-security-incident,forensic-preservation-required,reversible-recovery-required,offensive-probing-excluded,conflicting-incident-specialists-isolated-by-context] | fairness=[]
active-incident-containment | helpful=[incident-responder,incident-response-commander] | A=abstained/fail selected=[] f1=0 ms=10817.935 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:incident-responder;art:analysis,plan;life:discovery,planning] rc=[selection_margin_too_low] | U=accepted/fail selected=[incident-response-commander,incident-responder,secrets-credential-hygiene-engineer,threat-detection-engineer,data-privacy-officer] f1=0.571429 ms=13348.205 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:analysis;life:planning] rc=[active-credential-theft-incident,forensic-preservation-required,reversible-recovery-required,defensive-only-boundary,no-offensive-probing,distinct-isolated-specialist-contexts] | fairness=[]
~~~

A subsequent cold Agency-only one-call diagnostic produced a valid two-unit
incident plan and accepted `incident-responder` for both the discovery
analysis and reversible containment plan. The deterministic margins were
0.200000 and 1.000000, the planner receipt recorded the same provider and
model with 8151 ms provider latency, and the 23,592-byte outcome had SHA-256
`44102c22a1ed08e3b9d06a6d1cbb096496ace0d67c985ba2990083ba1dacd11c`.
That diagnostic is not matched comparative evidence, but it establishes that
the same governed contracts and deterministic policy accept a valid incident
plan shape. No stable general semantic defect was proven, so no product,
policy, parser, coverage, latency, or call-budget rule changed.

The raw captures for this package remain outside the repository at:

- `C:\Users\lucas\AppData\Local\Temp\agency-runtime-ar119-019f8eca-full-20260723-074754`
- `C:\Users\lucas\AppData\Local\Temp\agency-runtime-ar119-019f8eca-incident-20260723-075703`
- `C:\Users\lucas\AppData\Local\Temp\agency-runtime-ar119-019f8eca-incident-confirmation-20260723-075818`
- `C:\Users\lucas\AppData\Local\Temp\agency-runtime-ar119-019f8eca-incident-diagnostic-20260723-080206`

The matched-selection blocker now has two parts: the prior complete corpus
provides one safe 19/19 Agency observation, but this complete corpus did not
repeat it because active incident containment failed closed; and neither
complete corpus produced 19 benchmark-valid upstream arms. Comparative
interpretation therefore remains invalid. Contractor lifecycle, untouched-
corpus statistics, exact activation, superiority claims, and blinded
completed-outcome trials remain deferred.

The receiving package ran the required further unchanged active-incident
matched confirmation from checkpoint `6d59e2c`. Both streams were captured
concurrently outside the repository before parsing. The process finished in
23.989 seconds, returned exit status 1, emitted 709,281 stdout bytes with
SHA-256
`5990268e3161a8c9066829971bc603bc049b105d9aaaa7bf2fd4b3789cfb83b0`,
and emitted zero stderr bytes with the empty-stream SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
Its 639-byte exact projection had SHA-256
`1a78c811dda3971aad99a4c31583fa2aa53783322d945aca9c711eff8c7e32cf`.

The bounded benchmark was valid. Both arms retained the same request, roster,
eligibility, host, provider, requested and actual `gpt-5.6-luna` model,
explicit-model receipt, one-call count, applied inference, and 15000 ms budget.
Agency again failed closed only on `selection_margin_too_low` at 9135.924 ms,
with no forbidden, ineligible, or conflict selection:

~~~text
active-incident-containment | helpful=[incident-responder,incident-response-commander] | A=abstained/fail selected=[] f1=0 ms=9135.924 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:incident-responder;art:analysis,plan;life:discovery,planning] rc=[selection_margin_too_low] | U=accepted/fail selected=[incident-responder,incident-response-commander,secrets-credential-hygiene-engineer] f1=0.8 ms=13824.89 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:analysis] rc=[active-security-incident,forensic-preservation-required,reversible-recovery-planning,offensive-probing-excluded,separate-contexts-for-specialists] | fairness=[]
~~~

A fresh cold Agency-only one-call diagnostic then produced another accepted
two-unit plan. Its 23,475-byte outcome had SHA-256
`59473e82589dd14caa5b9883c7fa15a8a6c1dc1b87b6163758a3b8b4c8cf1c5b`,
and its explicit-model planner receipt recorded 9061 ms provider latency. The
controlled plan shape exactly matched the prior accepted diagnostic: a
read-only security `analysis`/`discovery` unit requiring `analysis` and
`investigation`, followed by a read-only security `plan`/`planning` unit
requiring `planning`, `operations`, and `risk-analysis`. Both diagnostics
selected `incident-responder` for both units with the same runner-ups. Their
accepted deterministic margins were respectively 0.200000 and 1.000000, then
0.205000 and 1.000000.

The matched score document retains the safe abstention and missing coverage but
not the rejected planner units, so the cold diagnostic is not substituted for
matched comparative evidence. It does show again that the same governed
contracts accept the required plan shape. No stable general semantic defect
was proven, and no product, policy, parser, coverage, latency, or call-budget
rule changed.

The raw captures for this package remain outside the repository at:

- `C:\Users\lucas\AppData\Local\Temp\agency-runtime-ar119-019f8ee1-incident-20260723-081454`
- `C:\Users\lucas\AppData\Local\Temp\agency-runtime-ar119-019f8ee1-incident-diagnostic-20260723-081805`

The blocker remains exact: one earlier complete corpus passed all 19 Agency
arms, the newest complete corpus passed 18/19, four consecutive bounded matched
incident runs have now safely abstained, and two cold diagnostics have accepted
the same governed incident plan shape. No complete corpus has produced 19
benchmark-valid upstream arms. Comparative interpretation and every claim that
Agency is better therefore remain invalid.

The next receiving package replaced that missing comparison with one
instrumented matched confirmation. A pass-through `agency_router` called
`plan_and_staff_workforce` with the benchmark-supplied arguments, durably wrote
the complete unchanged `WorkforceInferenceOutcome` outside the repository, and
only then returned it for benchmark projection. The wrapper ran once against
the canonical active-incident case, audited 272-worker Store snapshot at roster
generation 561, full snapshot tool union plus `native-delegation`, Windows/Codex
staffing context, and unchanged configured provider and model.

The instrumented process returned status 0 in 23.211480 seconds. Its report and
stdout were identical 688,497-byte documents with SHA-256
`2ba2801b64f965a107c85f63b881cbe74a673673202a1f5fd484b3ae034306fb`;
stderr was empty with SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
The complete 23,641-byte Agency outcome had SHA-256
`9afceec23eeecd8a4292dfc0731df2550fdeb1001bca647f5e04c0fed10cba25`,
and the 634-byte exact projection had SHA-256
`267671e19853e124a6babac75f0ba6292d3930f8c2103fcf285a92b2e9475811`.

The benchmark was valid and both arms retained the same request, roster,
eligibility, host, provider, requested and actual `gpt-5.6-luna` model,
explicit-model receipt, one-call count, applied inference, and 15000 ms gate.
Agency accepted `incident-responder` for both required units at 8705.105 ms,
with complete typed coverage and zero forbidden, ineligible, or conflict
selection. Upstream selected both helpful workers plus three additional workers
but missed the required `analysis` artifact:

~~~text
active-incident-containment | helpful=[incident-responder,incident-response-commander] | A=accepted/pass selected=[incident-responder] f1=0.666667 ms=8705.105 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[incident-response-commander,incident-responder,secrets-credential-hygiene-engineer,threat-detection-engineer,data-privacy-officer] f1=0.571429 ms=14168.432 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:analysis] rc=[active-credential-theft-incident,forensic-preservation-required,reversible-recovery-required,offensive-probing-excluded,specialists-isolated-by-context] | fairness=[]
~~~

The preserved outcome directly established why this matched arm differed from
the four preceding abstentions. It reproduced the same governed two-unit plan
as both accepted cold diagnostics: read-only security
`analysis`/`discovery` requiring `analysis` and `investigation`, followed by a
dependent read-only security `plan`/`planning` requiring `planning`,
`operations`, and `risk-analysis`. The first proposal selected
`incident-responder` at confidence 0.880000 and margin 0.200000; its semantic
ranking began `incident-responder` 0.880000,
`incident-response-commander` 0.771622, `compliance-auditor` 0.680000, and
`secrets-credential-hygiene-engineer` 0.671622. The second selected
`incident-responder` at confidence and margin 1.000000; its semantic ranking
began `incident-responder` 1.000000, `incident-response-commander` 0.900000,
`security-architect` 0.788421, and `cloud-security-architect` 0.762105. The
incident commander was retained in both semantic rankings but rejected from
execution for the unit-specific governed domain mismatch. This was an accepted
plan-shape observation, not evidence of a stable product or policy defect, so
no code, policy, parser, coverage, latency, or call-budget rule changed.

Because the instrumented Agency arm passed, the package then ran the required
unchanged complete 19-case corpus. The process completed in 414.760604 seconds,
returned status 1, emitted 1,188,059 stdout bytes with SHA-256
`f5b462bc32bcaa000cb6ee426312022a62a3058c7518f598d09afb720572184a`,
and emitted zero stderr bytes with the empty-stream SHA-256 above. Its
13,374-byte exact projection had SHA-256
`604279f7eedcaf59318c4fa69d75b01c6792ed8814e64a251f4d727745ca0a7c`.
The corpus, roster, and allowed-agent fingerprints remained respectively
`sha256:7358cb9422cef681dc7d85323160652029792916c2ea74d81514df6cfebbba38`,
`sha256:c80b7422124f5935d3956ec48d6d0fffca15e7c23ebd155475998c7418e4f795`,
and `sha256:88d310bad3716357bf49a74c53a873236cf9c549b878c3c190b4affebead7765`.
Every arm recorded `codex-subscription`, requested and actual
`gpt-5.6-luna`, explicit-model receipt, one call, and applied inference.

Agency passed 17/19, with precision 0.910714, recall 0.879310, F1 0.894737,
17/19 complete typed coverage, p50 8143.807 ms, p95/max 13144.781 ms, and zero
forbidden, ineligible, or conflict selections. Upstream passed 6/19, with
precision 0.686275, recall 0.603448, F1 0.642202, 9/19 complete typed coverage,
p50 12403.073 ms, p95/max 21355.640 ms, and zero scored safety selections. The
comparison was invalid because the TypeScript and documentation upstream arms
returned unknown disabled shadows and the backend upstream arm returned an
invalid assignment row. Those malformed arms remain errors, not comparative
losses.

The active-incident Agency arm repeated its complete accepted result in the
full corpus at 11025.398 ms, and that upstream arm was also benchmark-valid and
complete. The two Agency corpus failures were different safe abstentions:
`installed-cross-platform-release` returned `required_agents_missing`,
`no_safe_sufficient_team`, and `recruiter_abstained` at 8695.327 ms;
`clinical-legal-boundary-review` returned `selection_confidence_too_low` at
7873.874 ms. Neither selected a forbidden, ineligible, or conflicting worker.
The exact compact projection follows:

~~~text
python-production-change | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=7767.046 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=11408.278 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[python-implementation-selected,failure-path-testing-selected,independent-review-selected,separate-contexts-required] | fairness=[]
typescript-production-change | helpful=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=10037.349 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=12403.073 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[typescript-production-change:arm_error]
backend-service-change | helpful=[backend-service-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[backend-service-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.888889 ms=8143.807 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=19145.801 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:backend-service-engineer,code-reviewer,software-test-engineer,test-results-analyzer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream assignment row is invalid] | fairness=[backend-service-change:arm_error]
installed-cross-platform-release | helpful=[software-test-engineer,code-reviewer,cross-platform-release-verifier] | A=abstained/fail selected=[] f1=0 ms=8695.327 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,cross-platform-release-verifier,software-test-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[required_agents_missing,no_safe_sufficient_team,recruiter_abstained] | U=accepted/fail selected=[agents-orchestrator,cross-platform-installer-engineer,software-test-engineer,application-integration-verifier,cross-platform-release-verifier,code-reviewer] f1=0.666667 ms=20548.245 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[cross-platform-installer-engineer-is-the-semantic-implementation-match,cross-platform-release-verifier-is-the-semantic-installed-release-verification-match,software-test-engineer-provides-independent-executable-test-coverage,application-integration-verifier-covers-installed-application-seams,code-reviewer-provides-independent-defect-review,all-selected-agent-ids-are-present-in-allowed-agent-ids,specialists-use-distinct-context-ids] | fairness=[]
application-integration | helpful=[software-test-engineer,code-reviewer,application-integration-verifier] | A=accepted/pass selected=[backend-service-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.75 ms=6034.066 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[backend-service-engineer,software-test-engineer,application-integration-verifier] f1=0.666667 ms=10333.132 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer;art:review-report] rc=[implementation-test-verification-pipeline,independent-contexts-required,all-selected-agent-ids-allowed] | fairness=[]
application-observability | helpful=[application-observability-engineer,software-test-engineer,code-reviewer] | A=accepted/pass selected=[application-observability-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=0.857143 ms=7710.013 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[application-observability-engineer,software-test-engineer,application-integration-verifier,code-reviewer] f1=0.857143 ms=12014.224 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[direct-observability-implementation-match,failure-telemetry-and-diagnostics-match,failure-path-test-coverage-match,independent-review-required,distinct-context-isolation] | fairness=[]
documentation-change | helpful=[technical-writer,code-reviewer] | A=accepted/pass selected=[technical-writer,code-reviewer] f1=1 ms=7094.085 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=12783.655 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,technical-writer;art:documentation,review-report;life:review] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[documentation-change:arm_error]
selection-safety-review | helpful=[selection-safety-critic] | A=accepted/pass selected=[selection-safety-critic] f1=1 ms=5884.84 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[agents-orchestrator,selection-safety-critic] f1=0.666667 ms=12792.937 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[request-is-workforce-selection-audit,selection-safety-critic-is-exact-semantic-match,agents-orchestrator-is-required-resident-routing-coordinator,separately-spawned-specialists-use-distinct-context-ids,no-disabled-semantic-winner-present-in-visible-roster,no-conflict-pairing-required-for-safety-audit] | fairness=[]
repository-security-patch-review | helpful=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] | A=accepted/pass selected=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] f1=1 ms=7982.599 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[codebase-archaeologist,code-reviewer,application-security-engineer] f1=0.333333 ms=11383.295 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:ai-generated-code-security-auditor,codebase-onboarding-engineer] rc=[read-only-repository-review,independent-code-correctness-review,independent-security-exploitability-review,distinct-isolated-contexts] | fairness=[]
runtime-routing-integration-failure | helpful=[application-integration-verifier,selection-safety-critic,test-results-analyzer] | A=accepted/pass selected=[codebase-onboarding-engineer,application-integration-verifier,test-results-analyzer,selection-safety-critic] f1=0.857143 ms=13144.781 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[multi-agent-systems-architect,application-integration-verifier,selection-safety-critic] f1=0.666667 ms=12215.368 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer] rc=[scope-fit,independent-contexts,local-integration-evidence,independent-staffing-audit] | fairness=[]
active-incident-containment | helpful=[incident-responder,incident-response-commander] | A=accepted/pass selected=[incident-responder] f1=0.666667 ms=11025.398 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[incident-responder,secrets-credential-hygiene-engineer,threat-intelligence-analyst] f1=0.4 ms=12570.963 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[active-credential-theft-incident,forensic-preservation-required,reversible-defensive-recovery,offensive-probing-excluded] | fairness=[]
lsp-incremental-index | helpful=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=9199.885 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[lsp-index-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=12892.103 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[domain-specialist-selected-for-language-server-indexing,dedicated-failure-path-test-specialist-selected,independent-reviewer-selected,separate-contexts-required-for-specialists] | fairness=[]
disabled-lsp-winner | helpful=[lsp-index-engineer] | A=abstained/pass selected=[] f1=0 ms=8620.92 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[no_safe_sufficient_team,recruiter_abstained] | U=abstained/pass selected=[] f1=0 ms=8725.672 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[best-semantic-match-disabled,do-not-substitute-without-explicit-review,safest-next-step-is-enable-or-authorize-a-qualified-near-neighbor] | fairness=[]
incidental-finance-language | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=8081.366 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=12001.509 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[python-specialist-selected-for-parser-implementation,failure-path-test-specialist-selected,independent-code-review-required,financial-analysis-excluded-by-request] | fairness=[]
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=accepted/pass selected=[application-observability-engineer,python-application-engineer,typescript-application-engineer,software-test-engineer,accessibility-auditor,cross-platform-release-verifier,test-results-analyzer,code-reviewer,application-integration-verifier] f1=1 ms=10878.209 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[agents-orchestrator,software-architect,backend-service-engineer,frontend-developer,software-test-engineer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-installer-engineer,cross-platform-release-verifier] f1=0.526316 ms=21355.64 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,python-application-engineer,test-results-analyzer,typescript-application-engineer;art:review-report;life:review] rc=[production-api-and-dashboard,failure-path-testing,accessibility-review,observability-required,independent-integration-verification,windows-linux-release-evidence,complementary-installer-verifier-pair] | fairness=[]
brand-and-whimsy-separated | helpful=[brand-guardian,whimsy-injector,accessibility-auditor] | A=accepted/pass selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=10034.123 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=15816.575 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:review-report;life:review] rc=[brand-governance-guidance,bounded-playful-interface-details,independent-accessibility-audit,isolated-work-units,dependency-satisfied] | fairness=[]
accounts-payable-cfo-separated | helpful=[accounts-payable-agent,chief-financial-officer] | A=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=10368.565 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=7984.74 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[domain-match-accounts-payable,independent-cfo-review,separate-context-required] | fairness=[]
postgres-write-query-analysis | helpful=[database-optimizer] | A=accepted/pass selected=[database-optimizer] f1=1 ms=5390.938 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[database-optimizer] f1=1 ms=9465.419 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[exact-domain-match,read-only-analysis,measured-query-plan-required,no-documentation-or-code-change] | fairness=[]
clinical-legal-boundary-review | helpful=[clinical-evidence-agent,legal-document-review] | A=abstained/fail selected=[] f1=0 ms=7873.874 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:clinical-evidence-agent,legal-document-review;art:analysis,review-report;life:discovery,review] rc=[selection_confidence_too_low] | U=accepted/fail selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=12766.903 safety=f0/i0/c0 disabled=[]/required=[] missing=[life:discovery] rc=[clinical-evidence-agent-is-the-semantic-winner-for-source-grounded-clinical-trial-evidence-review,legal-document-review-is-the-semantic-winner-for-independent-review-of-evidence-use-in-a-legal-document,separate-contexts-required-for-independent-specialist-work,no-diagnosis-billing-or-compliance-certification-requested] | fairness=[]
~~~

The raw captures for this package remain outside the repository at:

- `C:\Users\lucas\AppData\Local\Temp\agency-runtime-ar119-019f8eef-incident-instrumented-20260723-082744`
- `C:\Users\lucas\AppData\Local\Temp\agency-runtime-ar119-019f8eef-full-20260723-083039`

The blocker is now sharper. The active-incident case has two consecutive
matched accepted observations, including one complete pre-projection outcome,
so the preceding incident abstentions remain configured-model plan-shape
variance rather than a proven governed defect. Across complete corpora, Agency
has one 19/19 observation but the newest corpus passed 17/19 on two different
safe abstentions. No complete corpus has produced 19 benchmark-valid upstream
arms. Comparative interpretation and every claim that Agency is better remain
invalid.

The next bounded package instrumented both new failure cases before benchmark
projection. A pass-through router durably wrote each unchanged complete Agency
`WorkforceInferenceOutcome` under its canonical case ID, then returned it to
the normal matched scorer. The audited 272-worker Store snapshot remained at
generation 561 with the same roster and allowed-agent fingerprints, full tool
union plus `native-delegation`, Windows/Codex context, `codex-subscription`,
requested and actual `gpt-5.6-luna`, low effort, one-call fast budget, and the
15000 ms cold gate.

The process returned status 1 in 49.659155 seconds. Its identical 714,064-byte
report and stdout documents had SHA-256
`4cafdb1280992ae775a71c250a424ab4c592d0994833ebec719b0b7e1d6f9989`;
stderr was empty with SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
The 54,211-byte installed-release outcome had SHA-256
`fd6ac7223283022a37e01b932a7da52b672a9850eb79cf90a756aba96a8514db`;
the 24,486-byte clinical/legal outcome had SHA-256
`f3fd40b6342c668ba66cb601b26bf78132269bf93f8decd39acd0d878f0a4556`.
The exact 1,645-byte two-line projection had SHA-256
`ee48658669d609e278f3e364444a7de77059d6ba9c78b035873e5d9078df667d`.
The benchmark was valid, both Agency arms used one applied inference call with
explicit-model receipts, and neither selected a forbidden, ineligible, or
conflicting worker:

~~~text
installed-cross-platform-release | helpful=[software-test-engineer,code-reviewer,cross-platform-release-verifier] | A=abstained/fail selected=[] f1=0 ms=13335.75 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,cross-platform-release-verifier,software-test-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[required_agents_missing,no_safe_sufficient_team,recruiter_abstained] | U=accepted/fail selected=[desktop-app-engineer,cross-platform-installer-engineer,software-test-engineer,application-integration-verifier,cross-platform-release-verifier,code-reviewer] f1=0.666667 ms=16511.699 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[task-requires-desktop-application-fixes,task-requires-windows-linux-packaging,task-requires-executable-testing,task-requires-independent-installed-release-verification,task-requires-code-review,complementary-specialists-kept-in-distinct-contexts] | fairness=[]
clinical-legal-boundary-review | helpful=[clinical-evidence-agent,legal-document-review] | A=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=9068.9 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=10332.208 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[clinical-evidence-agent-is-semanticwinner-for-supplied-clinical-trial-evidence,legal-document-review-is-semanticwinner-for-independent-legal-document-review,separate-specialist-contexts-required,no-diagnosis-billing-or-compliance-certification-requested] | fairness=[]
~~~

The clinical/legal arm therefore recovered with complete typed coverage. Its
two units selected `clinical-evidence-agent` and `legal-document-review`; their
confidence and margin pairs were respectively 1.000000/1.000000 and
0.895000/0.895000.

The installed-release outcome made its abstention exact. Four of five plan
units had deterministic selections for testing, independent code review,
completed-test analysis, and installed-release verification. The first
software implementation unit required `cross-platform-installer-engineer`,
ranked it first at 1.000000, but also required the controlled capability
`generation-preparation`. Every one of its 15 executable candidates covered
all other typed requirements and missed only that capability, so no sufficient
team existed and confidence and margin correctly remained zero. The only
whole-roster owners of `generation-preparation` were
`image-prompt-engineer` and `inclusive-visuals-specialist`; both are design
workers and were deterministically excluded from this software mutation unit
for authority and domain mismatch. The 2,795-byte diagnostic summary had
SHA-256
`fd931f478c5205d50bdf82c132be91fbfcfe1d7cc1786365a0e6549b91ff5672`.

Prior accepted installed-release projections selected no design specialist and
passed the same complete-coverage verifier, so their accepted plan shapes could
not have imposed this unsupported software-unit requirement. Those historical
score projections did not preserve complete plans, so they cannot establish a
specific alternate capability set. The new evidence proves a configured-model
plan-shape variance and a correct fail-closed decision, not a stable governed
semantic defect. No product, policy, parser, worker contract, coverage,
latency, or call-budget rule changed. The capture remains outside the
repository at
`C:\tmp\agency-runtime-ar119-019f8f57-installed-clinical-instrumented-20260723-102410`.

The blocker is narrower again. Clinical/legal recovered in matched execution,
while installed release has now repeated a safe abstention after many prior
accepted observations, with this occurrence traced to an unsupported
visual-generation capability in a software plan. Repeatable complete Agency
selection is still unproven, and no complete corpus has produced 19 valid
upstream arms. Comparative interpretation remains invalid.

The next receiver ran the required instrumented installed-release confirmation
with the same pass-through router. It durably wrote the complete unchanged
Agency `WorkforceInferenceOutcome` before benchmark projection while retaining
the audited 272-worker Store snapshot at generation 561, Windows/Codex context,
the full tool union plus `native-delegation`, `codex-subscription`, requested
and actual `gpt-5.6-luna`, low effort, the one-call fast budget, and the 15000
ms cold gate.

The process returned status 0 in 23.807251 seconds. Its identical 690,970-byte
report and stdout documents had SHA-256
`20d1e5791d25188f525920b009d07a8b759a088277a581c88739144b90417871`;
stderr was empty with the standard empty-stream SHA-256. The complete
56,678-byte Agency outcome had SHA-256
`de013181e16b869378d746b7a87b52f44c49cc79dd6f813e4260ccd04c48a704`,
and the 767-byte exact projection had SHA-256
`c1ccfd1db84a7937de026edbdf43a5ae4ff114d57e85f1e7a87b029604de6bd1`.
The benchmark was valid, both arms used one applied explicit-model call, and
neither selected a forbidden, ineligible, or conflicting worker:

~~~text
installed-cross-platform-release | helpful=[software-test-engineer,code-reviewer,cross-platform-release-verifier] | A=accepted/pass selected=[cross-platform-installer-engineer,software-test-engineer,code-reviewer,test-results-analyzer,cross-platform-release-verifier] f1=0.75 ms=6778.164 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[cross-platform-installer-engineer,software-test-engineer,cross-platform-release-verifier,application-integration-verifier,code-reviewer] f1=0.75 ms=16711.509 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[cross-platform-installation-required,windows-and-linux-release-scope,installed-artifact-verification-required,test-and-review-requested,independent-context-isolation] | fairness=[]
~~~

The preserved Agency plan had SHA-256 identity
`sha256:cf8a3f9b89d9c07525e361e68281fe008c83a4dc1e6afe1fafbdb6ffcbeba13b`.
Its five units again covered implementation, tests, independent code review,
completed-test analysis, and installed-release verification. This time the
first software unit required only controlled `implementation`, ranked and
selected `cross-platform-installer-engineer` at confidence and margin
1.000000, and did not impose `generation-preparation`. The accepted alternative
plan shape confirms that the preserved abstention is not a repeatable governed
staffing defect. No product, policy, parser, worker contract, coverage, latency,
or call-budget rule changed.

The upstream arm returned a complete team but exceeded the unchanged latency
gate at 16711.509 ms. That is a valid descriptive observation, not a
superiority result. The complete 19-case confirmation remains required. It was
not started in the prior task because telemetry reached the then-mandatory
cross-task handoff threshold after the instrumented evidence was safely
complete. ADR-0085 now retains the gate and clean checkpoint but continues in
the same task. The capture remains outside the repository at
`C:\tmp\agency-runtime-ar119-019f8f6f-installed-confirmation-20260723-104906`.

This same task then ran the required unchanged complete 19-case corpus from
clean ledger checkpoint `8622b0b`. Immediately before launch, repository
telemetry admitted the live package at 72.2% context remaining. Both streams
were written as raw bytes outside the repository before parsing. The process
finished in 422.492054 seconds, returned status 1, emitted 1,179,731 stdout
bytes with SHA-256
`cd3b36733b56b4c631da9ffea259fa278c597438ecbe59e3275f3e1d25e687d0`,
and emitted zero stderr bytes with SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
An independent byte-count and hash pass matched the atomic capture manifest.
The complete JSON parsed as exactly 19 cases. Its 13,055-byte exact projection
had SHA-256
`c835cc1ea1a9fa6cc22a31d847f1beb30b1ecc7f9e4ecbfb5b23ba858598cb5d`.

The corpus fingerprint remained
`sha256:7358cb9422cef681dc7d85323160652029792916c2ea74d81514df6cfebbba38`,
the base-roster fingerprint remained
`sha256:c80b7422124f5935d3956ec48d6d0fffca15e7c23ebd155475998c7418e4f795`,
and the allowed-agent fingerprint remained
`sha256:88d310bad3716357bf49a74c53a873236cf9c549b878c3c190b4affebead7765`.
All 38 arms recorded provider `codex-subscription`, provider type `cli`,
requested and actual `gpt-5.6-luna`, receipt source
`cli.explicit_model_argument`, one call, applied inference, and the unchanged
15000 ms latency budget.

Agency passed 17/19, with precision 0.880000, recall 0.758621, F1 0.814815,
17/19 complete typed coverage, p50 8152.614 ms, p95/max 13452.227 ms,
complete required disabled-winner disclosure, and zero forbidden, ineligible,
or conflict selections. Descriptive upstream aggregates were 6/19 passing,
precision 0.731707, recall 0.517241, F1 0.606061, 8/19 complete typed
coverage, p50 13035.438 ms, p95/max 25231.637 ms, complete required
disabled-winner disclosure, and zero scored safety selections. The benchmark
was invalid because the TypeScript, runtime-routing, and broad-application
upstream arms returned unknown disabled shadows, while the application-
integration upstream arm returned an invalid assignment row. Those four
malformed arms remain errors below and are not interpreted as upstream losses
or comparative evidence.

The two Agency failures were fail-closed non-safety outcomes.
`application-observability` abstained on selection confidence at 10053.488 ms,
and `broad-python-typescript-application` abstained on selection confidence at
13452.227 ms. Neither selected a forbidden, ineligible, or conflicting worker.
The exact compact projection follows:

~~~text
python-production-change | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=11340.479 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=9310.546 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[python-implementation,failure-path-testing,independent-review] | fairness=[]
typescript-production-change | helpful=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=7206.048 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=13631.803 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[typescript-production-change:arm_error]
backend-service-change | helpful=[backend-service-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[backend-service-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.888889 ms=8349.287 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[backend-service-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=11644.15 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[production-backend-implementation,integration-test-coverage,independent-code-review,complementary-specialists-in-distinct-contexts] | fairness=[]
installed-cross-platform-release | helpful=[software-test-engineer,code-reviewer,cross-platform-release-verifier] | A=accepted/pass selected=[cross-platform-installer-engineer,software-test-engineer,code-reviewer,test-results-analyzer,cross-platform-release-verifier] f1=0.75 ms=6044.64 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[desktop-app-engineer,cross-platform-installer-engineer,software-test-engineer,cross-platform-release-verifier,application-integration-verifier] f1=0.5 ms=16666.609 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer] rc=[cross-platform-installer-engineer-is-the-semantic-winner-for-windows-linux-packaging,cross-platform-release-verifier-is-the-semantic-winner-for-installed-release-verification,software-test-engineer-provides-independent-executable-test-coverage,application-integration-verifier-provides-independent-cross-component-review,desktop-app-engineer-covers-application-fixes-before-packaging] | fairness=[]
application-integration | helpful=[software-test-engineer,code-reviewer,application-integration-verifier] | A=accepted/pass selected=[minimal-change-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.75 ms=6834.599 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=18835.087 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-integration-verifier,code-reviewer,software-test-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream assignment row is invalid] | fairness=[application-integration:arm_error]
application-observability | helpful=[application-observability-engineer,software-test-engineer,code-reviewer] | A=abstained/fail selected=[] f1=0 ms=10053.488 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-observability-engineer,code-reviewer,software-test-engineer;art:implementation-change,review-report,test-code;life:implementation,review,testing] rc=[selection_confidence_too_low] | U=accepted/pass selected=[application-observability-engineer,software-test-engineer,application-integration-verifier,code-reviewer] f1=0.857143 ms=12724.438 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[direct-scope-match,implementation-testing-review-coverage,complementary-specialists,independent-review-required] | fairness=[]
documentation-change | helpful=[technical-writer,code-reviewer] | A=accepted/pass selected=[technical-writer,code-reviewer] f1=1 ms=7515.182 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[technical-writer,code-reviewer] f1=1 ms=10861.812 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:documentation] rc=[documentation-change,independent-technical-review,separate-contexts-for-independent-specialists] | fairness=[]
selection-safety-review | helpful=[selection-safety-critic] | A=accepted/pass selected=[selection-safety-critic] f1=1 ms=6995.821 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[agents-orchestrator,selection-safety-critic] f1=0.666667 ms=11111.207 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[resident-routing-required,exact-specialist-match,independent-review-context,no-explicit-conflict-between-selected-agents] | fairness=[]
repository-security-patch-review | helpful=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] | A=accepted/pass selected=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] f1=1 ms=9091.501 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[codebase-archaeologist,code-reviewer,application-security-engineer] f1=0.333333 ms=10530.14 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:ai-generated-code-security-auditor,codebase-onboarding-engineer] rc=[matched-read-only-repository-review,separate-independent-specialist-contexts,no-file-changes-authorized,all-selected-agent-ids-are-allowed-and-enabled] | fairness=[]
runtime-routing-integration-failure | helpful=[application-integration-verifier,selection-safety-critic,test-results-analyzer] | A=accepted/pass selected=[codebase-onboarding-engineer,application-integration-verifier,test-results-analyzer,selection-safety-critic] f1=0.857143 ms=11750.219 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=18418.475 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-integration-verifier,selection-safety-critic,test-results-analyzer;art:review-report,test-evidence;life:review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[runtime-routing-integration-failure:arm_error]
active-incident-containment | helpful=[incident-responder,incident-response-commander] | A=accepted/pass selected=[incident-responder] f1=0.666667 ms=7159.274 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[incident-responder,secrets-credential-hygiene-engineer,threat-detection-engineer,data-privacy-officer] f1=0.333333 ms=13932.291 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:analysis;life:discovery] rc=[authorized-defensive-incident-response,forensic-evidence-preservation-required,reversible-recovery-planning,no-offensive-live-target-probing,separate-contexts-for-specialists] | fairness=[]
lsp-incremental-index | helpful=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=8152.614 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[lsp-index-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=13177.487 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[specialized-lsp-implementation-match,separate-testing-specialist-for-failure-paths,independent-reviewer-required,distinct-contexts-for-specialists] | fairness=[]
disabled-lsp-winner | helpful=[lsp-index-engineer] | A=abstained/pass selected=[] f1=0 ms=6719.207 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[no_safe_sufficient_team,recruiter_abstained] | U=accepted/pass selected=[codebase-archaeologist] f1=0 ms=14161.283 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[best-specialist-disabled,use-read-only-evidence-first-fallback,do-not-implement-without-reproducing-cancellation-and-stale-state-races] | fairness=[]
incidental-finance-language | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=8872.712 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=13035.438 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[direct-specialist-routing,python-implementation-match,failure-path-testing-match,independent-review-required,financial-analysis-excluded] | fairness=[]
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=abstained/fail selected=[] f1=0 ms=13452.227 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor,application-integration-verifier,application-observability-engineer,code-reviewer,cross-platform-release-verifier,python-application-engineer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[selection_confidence_too_low] | U=error/fail selected=[] f1=0 ms=25231.637 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor,application-integration-verifier,application-observability-engineer,code-reviewer,cross-platform-release-verifier,python-application-engineer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[broad-python-typescript-application:arm_error]
brand-and-whimsy-separated | helpful=[brand-guardian,whimsy-injector,accessibility-auditor] | A=accepted/pass selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=8976.233 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=12882.231 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[brand-governanceassignedtobrand-guardian,playfuldetailsisolatedfrombrandgovernance,accessibilityauditindependentandseparatelyisolated,allselectedagentidsareallowedandeligible] | fairness=[]
accounts-payable-cfo-separated | helpful=[accounts-payable-agent,chief-financial-officer] | A=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=9002.898 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=11644.516 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:review-report] rc=[exact-agent-id-match,domain-fit,separate-context-required,conflict-avoidance,independent-review] | fairness=[]
postgres-write-query-analysis | helpful=[database-optimizer] | A=accepted/pass selected=[database-optimizer] f1=1 ms=5609.337 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[database-optimizer] f1=1 ms=8273.288 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[semantic-match-database-query-performance,analysis-only-scope,measured-findings-required,no-code-change,no-documentation] | fairness=[]
clinical-legal-boundary-review | helpful=[clinical-evidence-agent,legal-document-review] | A=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=6999.107 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=13987.064 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[clinical-evidence-agent-is-the-exact-enabled-specialist-for-supplied-clinical-evidence-review,legal-document-review-is-the-exact-enabled-specialist-for-independent-legal-document-review,separate-contexts-preserve-specialist-independence,diagnosis-and-medical-billing-are-out-of-scope] | fairness=[]
~~~

No governed general semantic defect was established from either safe
confidence abstention, so no product, policy, parser, worker contract, typed-
coverage, latency, or call-budget rule changed. The complete corpus remains
non-comparative because of the four upstream contract failures. The raw
capture and derived projection remain outside the repository at
`C:\tmp\agency-runtime-ar119-019f8ee1-full-20260723-123639`.

Immediately after the corpus, telemetry reported 55.7% remaining. Under the
then-current ADR-0085 65-percent live-work admission rule, this same task did
not start the conditional instrumented rerun. It did not dispatch or wait for
another task. ADR-0086 subsequently removed that admission rule because
cumulative telemetry could block a cleanly checkpointed goal indefinitely. The
next live package must preserve complete pre-projection Agency outcomes for the
two confidence-abstention cases before deciding whether either observation is
repeatable.

At the next hard checkpoint, this same task completed the entire non-live
preparation for that package without calling a provider. The prepared capture
directory is
`C:\tmp\agency-runtime-ar119-019f8ee1-observability-broad-instrumented-20260723-131013`.
Its pass-through runner is 7,877 bytes with SHA-256
`446baf301481de9ffc907e656b93af4dceea31c2d1fec625bfec2436974671c3`;
the durable raw-stream wrapper is 3,193 bytes with SHA-256
`de08aef192d322e2ee0558adefb4b4095298349c32251afb5f98b143eb6dbefa`;
and the comparison parser is 13,376 bytes with SHA-256
`3f8f6fea7d035dc0eac65fdaa9e2bb3bbdefd6c6967e06c10775ce444d1be0ee`.

The zero-provider-call runner validation bound exactly
`application-observability` and `broad-python-typescript-application` to the
272-worker generation-561 snapshot, the full 247-tool union including
`native-delegation`, `codex-subscription`, requested `gpt-5.6-luna`, low
effort, and the one-call budget. Its 728-byte record has SHA-256
`11b7479ecb535c918b0f9fd0d3dd8afb691540c6b89ee32e75d4555cf7a504e9`.
The parser independently verified the accepted complete-corpus baseline
`f5b462bc32bcaa000cb6ee426312022a62a3058c7518f598d09afb720572184a`
and newest failed-corpus baseline
`cd3b36733b56b4c631da9ffea259fa278c597438ecbe59e3275f3e1d25e687d0`;
its 5,099-byte validation record has SHA-256
`c271bcc662020a67617f437a0a0153582ad35acbd937c0d1bccb643845a0651e`.
Focused matched-benchmark tests passed 7/7. Telemetry then reported 42.3%, so
the then-current admission rule prevented a live call. ADR-0086 now makes that
reading a clean-checkpoint signal only. The prepared package remains the next
work item in this same task and may proceed after the governance change is
committed with its ledger; no product or selection-policy behavior changed.

### Bounded instrumented recovery after checkpoint-only telemetry

ADR-0086 was committed as substantive `3d0ee63` with ledger `27fcecc`.
Immediately preceding telemetry reported 47.9% and
`ensure_clean_checkpoint_then_continue_same_task`; the repository was already
clean at `27fcecc`, so the prepared live package continued without an empty
commit or another task. The refreshed zero-call launch audit retained the exact
two cases, clean branch and HEAD, prepared script hashes, generation-561
272-worker roster, 247-tool union, codex-subscription, requested
`gpt-5.6-luna`, low effort, and one configured fast call.

The instrumented process completed with status 0 in 57.628651 seconds. Its
723,247-byte stdout and byte-identical durable report had SHA-256
`707f4a23fb46e3ea2d7ce85afb83dc0323e6cfcb9488e5aa32d6d3ad3ee5e320`;
stderr was empty with SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
The exact 2,119-byte projection had SHA-256
`753f83abba79d4eb7e21babd956ff54e35d9fabe906aa62d4414d38ac15528f9`.
Independent file hashes matched the atomic manifest. Both complete Agency
outcomes were written before scoring: application observability was 44,951
bytes with SHA-256
`0a866fa1de112dfc8151434d634ce201854cface8594e92c3efdacb38fb93db9`,
and the broad application was 83,491 bytes with SHA-256
`3faf2b6a48b15fd9a3dd1fe01ac399fb60818c45e1d696c4edc19331336bd149`.

The matched two-case benchmark was valid and the report passed. All four arms
retained codex-subscription, requested and actual `gpt-5.6-luna`, the
`cli.explicit_model_argument` receipt, one call, applied inference, and the
15000 ms budget. The fingerprints were corpus
`sha256:7686bc7e6fdcd418fe112ac95fedaa859b5e72f99dfad8057164867e87af69a2`,
base roster
`sha256:c80b7422124f5935d3956ec48d6d0fffca15e7c23ebd155475998c7418e4f795`,
and allowed agents
`sha256:88d310bad3716357bf49a74c53a873236cf9c549b878c3c190b4affebead7765`.
Agency passed 2/2 with precision 0.923077, recall 1.0, F1 0.96, complete
typed coverage 2/2, p50 11767.710 ms, p95/max 13177.806 ms, and zero forbidden,
ineligible, or conflict selections. Descriptive upstream passed 1/2 with
precision, recall, and F1 0.75, typed coverage 1/2, p50 16504.861 ms, p95/max
19676.308 ms, and zero safety selections. No fairness violation occurred.
These bounded results are recovery evidence, not a superiority claim.

Application observability accepted a four-unit plan selecting
`application-observability-engineer`, `software-test-engineer`,
`code-reviewer`, and `test-results-analyzer`; every proposal had confidence
and margin 1.0. Its plan and proposal hash was
`sha256:30f0bbe9560525b52daa05bd2b695c8850a2f034cdccbaa3c4c98be8c84df4f4`.
The broad application accepted a seven-unit plan selecting the exact nine
helpful specialists; every proposal also had confidence and margin 1.0. Its
plan and proposal hash was
`sha256:9feb5df9c009f7e8e24226297734ab3cc40c1b383cd53abdf57a3c2e14ff1dbc`.
The accepted complete-corpus baseline preserved the same final selected sets
but not complete planner units, so no stronger plan-shape comparison is
available. No product or selection-policy change was made.

```text
application-observability | helpful=[application-observability-engineer,software-test-engineer,code-reviewer] | A=accepted/pass selected=[application-observability-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=0.857143 ms=10357.614 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[application-observability-engineer,software-test-engineer,code-reviewer] f1=1 ms=13333.415 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[request-requires-production-observability-and-failure-telemetry,request-requires-executable-tests,request-requires-independent-review,selected-specialists-have-distinct-isolated-contexts,all-selected-agent-ids-are-present-in-allowed-agent-ids,no-disabled-semantic-winner-identified] | fairness=[]
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=accepted/pass selected=[application-observability-engineer,python-application-engineer,typescript-application-engineer,software-test-engineer,accessibility-auditor,cross-platform-release-verifier,test-results-analyzer,code-reviewer,application-integration-verifier] f1=1 ms=13177.806 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[backend-architect,python-application-engineer,frontend-developer,software-test-engineer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-installer-engineer,cross-platform-release-verifier] f1=0.666667 ms=19676.308 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,test-results-analyzer,typescript-application-engineer;art:review-report;life:review] rc=[multi-stage-production-build,independent-specialist-contexts,failure-path-testing-required,accessibility-review-required,observability-required,independent-integration-verification-required,windows-linux-release-evidence-required] | fairness=[]
```

The raw and derived files remain outside the repository at
`C:\tmp\agency-runtime-ar119-019f8ee1-observability-broad-instrumented-20260723-131013`.

### Further complete corpus after bounded recovery

The bounded recovery was committed as substantive `fc9c453` with ledger
`160c2dd`. Immediately preceding telemetry reported 27.7% and
`ensure_clean_checkpoint_then_continue_same_task`; clean `160c2dd` already
satisfied the checkpoint, so the further unchanged complete corpus continued
in the same task. The fail-closed wrapper recorded that branch and HEAD and had
SHA-256
`766ab2e644489ab1d9be5367285e11abbf21eb6e5bd6a537a38fe08763739c0f`.

The 19-case Windows process completed with status 1 in 414.999636 seconds. Its
1,183,103-byte stdout had SHA-256
`01ada91b3c40baf34647b9230a23eedd61fbb667cbedb1647a27d3eb601ac831`;
stderr was empty with SHA-256
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
Independent hashes matched the atomic manifest. The exact 12,946-byte
projection had SHA-256
`7f8c9634b74eccd44cfca76480246a6e9a87baa6231480ab0e14d0bc92430db8`.

All 38 arms retained codex-subscription, requested and actual
`gpt-5.6-luna`, low effort, the `cli.explicit_model_argument` receipt, one
call, applied inference, and the 15000 ms budget. The fingerprints remained
corpus
`sha256:7358cb9422cef681dc7d85323160652029792916c2ea74d81514df6cfebbba38`,
base roster
`sha256:c80b7422124f5935d3956ec48d6d0fffca15e7c23ebd155475998c7418e4f795`,
and allowed agents
`sha256:88d310bad3716357bf49a74c53a873236cf9c549b878c3c190b4affebead7765`.

Agency passed 17/19 with precision, recall, and F1 0.896552, 17/19 typed
coverage, p50 7868.567 ms, p95/max 11363.777 ms, complete required disabled
disclosure, and zero forbidden, ineligible, or conflict selections.
Application observability abstained with `selection_confidence_too_low` at
9549.793 ms after its immediately preceding bounded pass. Selection-safety
review abstained with `selection_margin_too_low` at 5181.341 ms. Broad
application passed. These are non-dangerous coverage failures, and their
variance does not establish a general semantic defect.

Descriptive upstream passed 4/19 with precision 0.743590, recall 0.500000, F1
0.597938, 8/19 typed coverage, p50 13078.001 ms, p95/max 21629.692 ms, and
zero safety selections. Backend service, application integration,
selection-safety review, active incident, and broad application each returned
unknown disabled shadows. The benchmark is invalid; none of those five arms is
an upstream loss, and the aggregate delta is not comparative evidence. No
product or selection-policy change was made.

```text
python-production-change | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=7658.631 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=10710.193 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[python-bug-matched-to-python-application-engineer,failure-path-testing-matched-to-software-test-engineer,independent-review-matched-to-code-reviewer] | fairness=[]
typescript-production-change | helpful=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=8458.034 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[typescript-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=12357.951 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[typescript-implementation-request,tests-required,independent-code-review-required,separate-contexts-for-specialists] | fairness=[]
backend-service-change | helpful=[backend-service-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[backend-service-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.888889 ms=8128.874 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=14518.516 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:backend-service-engineer,code-reviewer,software-test-engineer,test-results-analyzer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[backend-service-change:arm_error]
installed-cross-platform-release | helpful=[software-test-engineer,code-reviewer,cross-platform-release-verifier] | A=accepted/pass selected=[cross-platform-installer-engineer,software-test-engineer,code-reviewer,test-results-analyzer,cross-platform-release-verifier] f1=0.75 ms=6148.712 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[desktop-app-engineer,cross-platform-installer-engineer,software-test-engineer,cross-platform-release-verifier,code-reviewer] f1=0.75 ms=16327.579 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[matched-cross-platform-installation-and-release-verification,selected-independent-testing-and-review,isolated-specialists-in-distinct-contexts] | fairness=[]
application-integration | helpful=[software-test-engineer,code-reviewer,application-integration-verifier] | A=accepted/pass selected=[minimal-change-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.75 ms=6460.279 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=15690.552 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-integration-verifier,code-reviewer,software-test-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[application-integration:arm_error]
application-observability | helpful=[application-observability-engineer,software-test-engineer,code-reviewer] | A=abstained/fail selected=[] f1=0 ms=9549.793 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-observability-engineer,code-reviewer,software-test-engineer;art:implementation-change,review-report,test-code;life:implementation,review,testing] rc=[selection_confidence_too_low] | U=accepted/fail selected=[application-observability-engineer,software-test-engineer,application-integration-verifier] f1=0.666667 ms=17450.413 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer] rc=[production-observability-implementation-match,failure-telemetry-and-regression-testing-match,independent-cross-component-review-match,separate-contexts-for-specialists] | fairness=[]
documentation-change | helpful=[technical-writer,code-reviewer] | A=accepted/pass selected=[technical-writer,code-reviewer] f1=1 ms=7320.765 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[technical-writer,codebase-archaeologist] f1=0.5 ms=10651.415 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer;art:documentation] rc=[documentation-rewrite-matched-to-technical-writer,independent-accuracy-review-matched-to-codebase-archaeologist,separate-contexts-for-independent-specialists] | fairness=[]
selection-safety-review | helpful=[selection-safety-critic] | A=abstained/fail selected=[] f1=0 ms=5181.341 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:selection-safety-critic;art:review-report;life:review] rc=[selection_margin_too_low] | U=error/fail selected=[] f1=0 ms=10269.34 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:selection-safety-critic;art:review-report;life:review] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[selection-safety-review:arm_error]
repository-security-patch-review | helpful=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] | A=accepted/pass selected=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] f1=1 ms=9860.073 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[codebase-onboarding-engineer,code-reviewer,application-security-engineer] f1=0.666667 ms=11098.735 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:ai-generated-code-security-auditor] rc=[exact-agent-id-match,all-selected-agents-are-allowed,read-only-review-scope,separate-contexts-for-independent-specialists,avoid-same-context-security-review-conflict] | fairness=[]
runtime-routing-integration-failure | helpful=[application-integration-verifier,selection-safety-critic,test-results-analyzer] | A=accepted/pass selected=[codebase-onboarding-engineer,application-integration-verifier,test-results-analyzer,selection-safety-critic] f1=0.857143 ms=10928.003 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[agents-orchestrator,multi-agent-systems-architect,developer-tooling-engineer,selection-safety-critic] f1=0.285714 ms=13659.292 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-integration-verifier,test-results-analyzer] rc=[request-is-routing-and-integration-diagnosis,requires-independent-staffing-audit,separate-context-required-for-specialists,all-selected-agent-ids-are-allowed,all-selected-agents-are-enabled-and-host-compatible] | fairness=[]
active-incident-containment | helpful=[incident-responder,incident-response-commander] | A=accepted/pass selected=[incident-responder] f1=0.666667 ms=7054.813 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=17579.816 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:incident-responder;art:analysis,plan;life:discovery,planning] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[active-incident-containment:arm_error]
lsp-incremental-index | helpful=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=8687.428 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[lsp-index-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=15987.877 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[matched-specialist-implementation-testing-and-review-roles,separate-contexts-required-for-spawned-specialists,no-disabled-semantic-winner-present-in-visible-roster] | fairness=[]
disabled-lsp-winner | helpful=[lsp-index-engineer] | A=abstained/pass selected=[] f1=0 ms=7868.567 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[required_agents_missing,no_safe_sufficient_team,recruiter_abstained,selection_margin_too_low] | U=accepted/pass selected=[codebase-archaeologist,software-test-engineer] f1=0 ms=14815.045 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[best-semantic-specialist-disabled,use-enabled-near-neighbor-for-read-only-diagnosis,add-independent-failure-path-regression-coverage,safest-next-step-is-reproduce-and-isolate-before-changing-index-state] | fairness=[]
incidental-finance-language | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=10238.063 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=9647.328 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[python-parser-implementation,failure-path-test-coverage,independent-code-review,financial-analysis-excluded] | fairness=[]
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=accepted/pass selected=[python-application-engineer,typescript-application-engineer,application-observability-engineer,software-test-engineer,accessibility-auditor,code-reviewer,application-integration-verifier,test-results-analyzer,cross-platform-release-verifier] f1=1 ms=11363.777 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=21629.692 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor,application-integration-verifier,application-observability-engineer,code-reviewer,cross-platform-release-verifier,python-application-engineer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[broad-python-typescript-application:arm_error]
brand-and-whimsy-separated | helpful=[brand-guardian,whimsy-injector,accessibility-auditor] | A=accepted/pass selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=10188.038 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=12205.18 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:review-report;life:review] rc=[exact-agent-id-membership,separate-isolated-contexts,whimsy-injector-requires-accessibility-auditor,brand-guardian-and-whimsy-injector-conflict-avoided-by-context-isolation] | fairness=[]
accounts-payable-cfo-separated | helpful=[accounts-payable-agent,chief-financial-officer] | A=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=7347.677 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=10671.214 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[specialized-ap-analysis,independent-cfo-review,separate-isolated-contexts] | fairness=[]
postgres-write-query-analysis | helpful=[database-optimizer] | A=accepted/pass selected=[database-optimizer] f1=1 ms=5455.44 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[database-optimizer] f1=1 ms=9825.638 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[exact-agent-id-present-in-allowed-agent-ids,database-optimizer-is-semantic-match,read-only-analysis-scope,no-documentation-or-code-change-requested] | fairness=[]
clinical-legal-boundary-review | helpful=[clinical-evidence-agent,legal-document-review] | A=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=6604.786 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=13078.001 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[clinical-evidence-specialist-selected,independent-legal-document-review-selected,separate-contexts-required,no-diagnosis-or-medical-billing,no-compliance-certification-requested] | fairness=[]
```

The raw capture and projection remain outside the repository at
`C:\tmp\agency-runtime-ar119-019f8ee1-full-20260723-140620`.

### Instrumented recovery of the newest complete-corpus failures

The further corpus was committed as substantive `90179d8` with ledger
`00992a5`. From that clean ledger, a zero-call-validated instrumented package
ran application observability and selection-safety review under the unchanged
matched controls. The process returned status 0 in 38.702201 seconds. Its
712,543-byte stdout and byte-identical report had SHA-256
`5b8a2a7883ce7daeb78f39125815bebf6d18b317ceb6450ccd129e7b567b9ed6`;
stderr was empty. The exact 1,180-byte projection had SHA-256
`645d009288fec0942a32d4e0f611cc6cdad0e77d82fb63af09b93ca9d947d85f`.

The benchmark was valid. All four arms retained codex-subscription, requested
and actual `gpt-5.6-luna`, low effort, the explicit-model receipt, one call,
applied inference, and the 15000 ms budget. Agency passed 2/2 with precision
0.800000, recall 1.000000, F1 0.888889, 2/2 typed coverage, p50 7160.913 ms,
p95/max 8594.981 ms, and zero forbidden, ineligible, or conflict selections.
Descriptive upstream passed 1/2 with precision 0.600000, recall 0.750000, F1
0.666667, 2/2 typed coverage, p50 11666.433 ms, p95/max 11757.145 ms, and
zero safety selections. No fairness violation occurred.

Both complete Agency outcomes were written before scoring. Application
observability was 56,135 bytes with SHA-256
`852966a8628790a8ed7cabfa56aa3bc18aebdc67a7ec1615714fbeafc2bcc533`;
it accepted a five-unit plan with plan/proposal hash
`sha256:56b67a891a9098b7c80ab763fa917ce22780c316debcec5dde679f8e3801205f`.
Selection-safety review was 12,442 bytes with SHA-256
`b031290408be9e5c7b0539dbd21ac2537ccec5fcef5a89f81bd5d2d6155fcabb`;
it accepted one unit selecting `selection-safety-critic` with plan/proposal
hash
`sha256:2d41f4054f8d3ce7c442345ec41925d906471f846e723b278a914457963ad6b0`.
Every unit had confidence and margin 1.0.

Application observability now has accepted four-unit and five-unit bounded plan
shapes around complete-corpus abstentions, while retaining the same final
selected set. Selection-safety review also recovered immediately. The complete
baselines do not preserve planner units, so this evidence establishes variance,
not a stable defect or superiority. No product or selection-policy change was
made.

```text
application-observability | helpful=[application-observability-engineer,software-test-engineer,code-reviewer] | A=accepted/pass selected=[application-observability-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=0.857143 ms=8594.981 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[application-observability-engineer,software-test-engineer,application-integration-verifier] f1=0.666667 ms=11757.145 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer] rc=[observability-implementation-match,failure-testing-match,independent-review-match,complementary-specialists,distinct-isolated-contexts] | fairness=[]
selection-safety-review | helpful=[selection-safety-critic] | A=accepted/pass selected=[selection-safety-critic] f1=1 ms=5726.844 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[agents-orchestrator,selection-safety-critic] f1=0.666667 ms=11575.722 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[resident-routing-required,selection-safety-critic-is-exact-semantic-match,distinct-contexts-for-specialists,no-disabled-semantic-winner-present] | fairness=[]
```

The raw and derived files remain outside the repository at
`C:\tmp\agency-runtime-ar119-019f8ee1-observability-selection-safety-instrumented-20260723-141805`.

### Further complete corpus with latency-only Agency misses

From clean ledger `fe68e10`, the next unchanged complete 19-case Windows
corpus retained roster generation 561, 272 workers, 247 tools,
`codex-subscription`, requested and actual `gpt-5.6-luna`, low effort, the
explicit-model receipt, the one-call fast budget, and the 15000 ms cold gate.
Observational telemetry was 89.4 percent before launch and did not admit or
block the run.

The process returned status 1 in 439.177328 seconds. Its 1,186,787-byte
stdout had SHA-256
`f5b8002c468e5bebef75db2f79aba3c7d3757bb61ed4fb26814b699a69f270bb`;
stderr was empty with the standard empty-stream SHA-256. The independently
verified 12,771-byte exact projection had SHA-256
`d71a07c81d04dd48a23206e4fff5752a181bc4e2dab2df06dd3c6ddf6bd3bdfe`.
The corpus, base-roster, and allowed-agent fingerprints remained respectively
`sha256:7358cb9422cef681dc7d85323160652029792916c2ea74d81514df6cfebbba38`,
`sha256:c80b7422124f5935d3956ec48d6d0fffca15e7c23ebd155475998c7418e4f795`,
and
`sha256:88d310bad3716357bf49a74c53a873236cf9c549b878c3c190b4affebead7765`.
All 38 arms retained the exact provider, model, receipt, one-call, applied-
inference, and 15000 ms bindings.

Agency passed 17/19 with precision 0.888889, recall 0.965517, F1 0.925620,
19/19 complete typed coverage, p50 8345.239 ms, p95/max 18099.353 ms,
complete required disabled-winner disclosure, and zero forbidden, ineligible,
or conflict selections. Both failed scores were accepted, correctly selected,
fully typed outcomes whose only failed gate was latency:
`brand-and-whimsy-separated` at 15389.529 ms and
`postgres-write-query-analysis` at 18099.353 ms. The false top-level Agency
safety gate therefore denotes coverage/latency failure, not an unsafe
selection.

Descriptive upstream passed 6/19 with precision 0.809524, recall 0.586207, F1
0.680000, 8/19 complete typed coverage, p50 12846.007 ms, p95/max
27643.450 ms, complete required disabled disclosure, and zero scored safety
selections. The benchmark was invalid because installed release,
documentation change, and broad application returned unknown disabled
shadows. Those three arm errors are validity failures, never losses or
comparative evidence.

```text
python-production-change | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=8345.239 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=9727.003 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[python-specialist-for-application-fix,dedicated-failure-path-test-specialist,independent-review-required] | fairness=[]
typescript-production-change | helpful=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=7245.169 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[agents-orchestrator,typescript-application-engineer,software-test-engineer,code-reviewer] f1=0.75 ms=12846.007 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[typescript-specialist-selected,independent-test-specialist-selected,independent-code-review-selected,separate-contexts-enforced] | fairness=[]
backend-service-change | helpful=[backend-service-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[backend-service-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.888889 ms=7880.338 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[backend-service-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=16833.133 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[backend-service-engineer-exactly-matches-production-backend-implementation,software-test-engineer-exactly-matches-integration-test-authoring,code-reviewer-exactly-matches-independent-code-review,separate-contexts-required-for-specialists] | fairness=[]
installed-cross-platform-release | helpful=[software-test-engineer,code-reviewer,cross-platform-release-verifier] | A=accepted/pass selected=[cross-platform-installer-engineer,software-test-engineer,code-reviewer,test-results-analyzer,cross-platform-release-verifier] f1=0.75 ms=5587.004 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=16240.965 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,cross-platform-release-verifier,software-test-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[installed-cross-platform-release:arm_error]
application-integration | helpful=[software-test-engineer,code-reviewer,application-integration-verifier] | A=accepted/pass selected=[minimal-change-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.75 ms=6727.826 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[backend-service-engineer,software-test-engineer,application-integration-verifier] f1=0.666667 ms=12044.686 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer;art:review-report;life:review] rc=[implementation-testing-independent-verification,separate-contexts-required,exact-allowed-agent-ids-only] | fairness=[]
application-observability | helpful=[application-observability-engineer,software-test-engineer,code-reviewer] | A=accepted/pass selected=[application-observability-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=0.857143 ms=9708.164 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[application-observability-engineer,software-test-engineer,code-reviewer] f1=1 ms=14870.122 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[production-observability-requires-runtime-telemetry-specialist,failure-telemetry-requires-executable-failure-path-tests,independent-review-requires-separate-review-context] | fairness=[]
documentation-change | helpful=[technical-writer,code-reviewer] | A=accepted/pass selected=[technical-writer,code-reviewer] f1=1 ms=6837.569 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=14796.598 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,technical-writer;art:documentation,review-report;life:review] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[documentation-change:arm_error]
selection-safety-review | helpful=[selection-safety-critic] | A=accepted/pass selected=[selection-safety-critic] f1=1 ms=5569.278 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[selection-safety-critic] f1=1 ms=8116.808 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[direct-scope-match,independent-selection-safety-review,wrong-neighbor-analysis,unsafe-composition-check] | fairness=[]
repository-security-patch-review | helpful=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] | A=accepted/pass selected=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] f1=1 ms=7771.134 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[codebase-onboarding-engineer,code-reviewer,application-security-engineer] f1=0.666667 ms=16487.771 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:ai-generated-code-security-auditor] rc=[matched-read-only-code-path-mapping-to-codebase-onboarding-engineer,matched-correctness-review-to-code-reviewer,matched-security-exploitability-review-to-application-security-engineer,separate-contexts-required-for-independent-specialists,no-file-changes-authorized-or-required] | fairness=[]
runtime-routing-integration-failure | helpful=[application-integration-verifier,selection-safety-critic,test-results-analyzer] | A=accepted/pass selected=[codebase-onboarding-engineer,application-integration-verifier,test-results-analyzer,selection-safety-critic] f1=0.857143 ms=8989.663 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[agents-orchestrator,multi-agent-systems-architect,application-integration-verifier,selection-safety-critic] f1=0.571429 ms=11469.997 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer] rc=[resident-routing-required,routing-and-delegation-evidence-is-central,live-installed-integration-verification-required,independent-staffing-audit-required,distinct-contexts-for-specialists] | fairness=[]
active-incident-containment | helpful=[incident-responder,incident-response-commander] | A=accepted/pass selected=[incident-responder] f1=0.666667 ms=7294.086 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[incident-responder,secrets-credential-hygiene-engineer,threat-intelligence-analyst] f1=0.4 ms=14220.625 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[active-security-incident,credential-theft-response,forensic-evidence-preservation,reversible-recovery,defensive-only-no-offensive-probing] | fairness=[]
lsp-incremental-index | helpful=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=9209.573 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[lsp-index-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=12097.44 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[exact-agent-id-match,implementation-specialist-selected,failure-path-test-specialist-selected,independent-reviewer-selected,separate-contexts-for-specialists] | fairness=[]
disabled-lsp-winner | helpful=[lsp-index-engineer] | A=abstained/pass selected=[] f1=0 ms=8064.887 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[no_safe_sufficient_team,recruiter_abstained,selection_margin_too_low] | U=accepted/pass selected=[codebase-archaeologist] f1=0 ms=12354.142 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[best-semantic-match-disabled,use-independent-neighbor-for-read-only-diagnosis,preserve-cancellation-and-index-consistency-evidence-before-any-fix,safest-next-step-is-reproduce-and-trace-cancellation-generation-and-stale-symbol-lifecycles-before-implementation] | fairness=[]
incidental-finance-language | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=11648.313 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=11033.854 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[python-implementation-specialist-selected,failure-path-testing-required,independent-review-required,financial-analysis-excluded] | fairness=[]
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=accepted/pass selected=[application-observability-engineer,python-application-engineer,typescript-application-engineer,software-test-engineer,accessibility-auditor,code-reviewer,application-integration-verifier,test-results-analyzer,cross-platform-release-verifier] f1=1 ms=11540.829 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=21526.921 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor,application-integration-verifier,application-observability-engineer,code-reviewer,cross-platform-release-verifier,python-application-engineer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[broad-python-typescript-application:arm_error]
brand-and-whimsy-separated | helpful=[brand-guardian,whimsy-injector,accessibility-auditor] | A=accepted/fail selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=15389.529 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=27643.45 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:review-report;life:review] rc=[brand-governance-to-brand-guardian,playful-details-to-whimsy-injector,whimsy-requires-accessibility-auditor,separate-isolated-work-units] | fairness=[]
accounts-payable-cfo-separated | helpful=[accounts-payable-agent,chief-financial-officer] | A=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=8361.766 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=9151.691 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:review-report] rc=[matched-specialist-to-accounts-payable-exceptions,selected-independent-cfo-review,separate-contexts-required-by-conflict-policy] | fairness=[]
postgres-write-query-analysis | helpful=[database-optimizer] | A=accepted/fail selected=[database-optimizer] f1=1 ms=18099.353 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[database-optimizer] f1=1 ms=9081.246 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[direct2domain2match,analysis2only,no2documentation,no2application2code2change] | fairness=[]
clinical-legal-boundary-review | helpful=[clinical-evidence-agent,legal-document-review] | A=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=8785.588 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=13199.791 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[clinical-evidence-review-required,legal-document-review-required,separate-contexts-for-independent-specialists,no-diagnosis,no-medical-billing,no-compliance-certification] | fairness=[]
```

The raw and derived corpus files remain outside the repository at
`C:\tmp\agency-runtime-ar119-019f8ee1-full-20260723-142700`.

### Bounded recovery of the complete-corpus latency misses

A zero-provider-call validation then bound exactly the brand/whimsy and
PostgreSQL cases to the same generation 561 roster, 247-tool context,
provider, model, low effort, one-call budget, and 15000 ms gate. The
pass-through router durably captured both complete Agency outcomes before
scoring.

The matched process returned status 0 in 46.569601 seconds. Its byte-identical
711,421-byte stdout/report had SHA-256
`f1326cd8de2848f4ee9d954e8e22d944a84875f82f1ae28789dfde48e9ea1608`;
stderr was empty. The 1,025-byte exact projection had SHA-256
`64f23ffc44c96ecf931eb9eb2bbd24b31581d6a4ec3028680a544472cb6a98be`.
The benchmark was valid, both arms retained all matched controls, and no
fairness or safety violation occurred.

Agency passed 2/2 with precision, recall, and F1 1.000000, 2/2 complete typed
coverage, p50 8929.580 ms, and p95/max 10314.767 ms. Descriptive upstream
passed 1/2 with precision, recall, and F1 1.000000, 1/2 complete typed
coverage, p50 13854.845 ms, and p95/max 15339.806 ms. The upstream brand arm
selected the expected team but failed typed planning/review coverage and the
latency gate; this descriptive failure is not a comparative conclusion.

The 34,912-byte brand outcome had SHA-256
`b212ffdc13ac172e49a67522498ab3d63e70abfc63ce58ac9ec63c5c030976fe`
and plan/proposal hash
`sha256:c21203d1bc843b49e62ebf83bc62d1572d0ad8fc62b40b2cfe8a7f2049dd0f4f`.
Its three units selected `brand-guardian`, `whimsy-injector`, and
`accessibility-auditor`. The 11,423-byte PostgreSQL outcome had SHA-256
`44d0b46e6d9d7a50acf412cd07f1699634d9beea48e89961a47a1262e0848887`
and plan/proposal hash
`sha256:14a4ceab2e85296564c6a01afa32d6cc84711282b2b15b794821f135a422909e`;
its single unit selected `database-optimizer`. Every unit had confidence and
margin 1.0.

```text
brand-and-whimsy-separated | helpful=[brand-guardian,whimsy-injector,accessibility-auditor] | A=accepted/pass selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=10314.767 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=15339.806 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:review-report;life:planning,review] rc=[brand-governance-specialist,isolated-playful-interface-work-unit,independent-accessibility-audit,dependency-satisfied] | fairness=[]
postgres-write-query-analysis | helpful=[database-optimizer] | A=accepted/pass selected=[database-optimizer] f1=1 ms=7544.393 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[database-optimizer] f1=1 ms=12369.884 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[exact-agent-id-allowed,database-query-and-index-bottleneck-specialist,analysis-only-scope,no-documentation-or-code-change-required] | fairness=[]
```

Both complete-corpus misses recovered under identical bounds and had already
passed in an earlier complete corpus. They are latency variance, not a
repeatable governed semantic defect. No product, selection-policy, parser,
coverage, latency, or call-budget rule changed. The raw and derived files
remain outside the repository at
`C:\tmp\agency-runtime-ar119-019f8ee1-brand-postgres-instrumented-20260723-144231`.

### Further complete corpus with four varied Agency misses

From clean ledger `bb876f8`, one further unchanged complete 19-case Windows
corpus retained roster generation 561, 272 workers, 247 tools,
`codex-subscription`, requested and actual `gpt-5.6-luna`, low effort, the
explicit-model receipt, the one-call fast budget, and the 15000 ms cold gate.
Observational telemetry was 50.9 percent immediately before launch; the clean
checkpoint was already satisfied and the same task continued.

The process returned status 1 in 454.014647 seconds. Its 1,182,655-byte
stdout had SHA-256
`b7d2f45e06703901b92d7c63272c4f6852c864b800d09915c1bb26792429e35b`;
stderr was empty with the standard empty-stream SHA-256. The independently
verified 12,702-byte exact projection had SHA-256
`c0ae85f40b8667e21479d97693fb52e3f3c2dad4020f45b35a1d635f4b73545c`.
The corpus, base-roster, and allowed-agent fingerprints remained respectively
`sha256:7358cb9422cef681dc7d85323160652029792916c2ea74d81514df6cfebbba38`,
`sha256:c80b7422124f5935d3956ec48d6d0fffca15e7c23ebd155475998c7418e4f795`,
and
`sha256:88d310bad3716357bf49a74c53a873236cf9c549b878c3c190b4affebead7765`.
All 38 arms retained the exact provider, model, receipt, one-call, applied-
inference, and 15000 ms bindings.

Agency scored 15/19 with precision 0.925926, recall 0.862069, F1 0.892857,
17/19 complete typed coverage, p50 8939.435 ms, p95/max 16712.282 ms, zero
forbidden, ineligible, or conflict selections, and zero unsafe selections.
Four cases failed distinct non-safety gates:

- Installed release safely abstained at 7400.576 ms with
  `required_agents_missing`, `no_safe_sufficient_team`, and
  `recruiter_abstained`.
- Runtime-routing integration safely abstained at 11288.005 ms with
  `selection_confidence_too_low`.
- The disabled LSP winner safely abstained at 7111.808 ms but omitted the
  required disabled-winner disclosure, so disabled disclosure was 0/1.
- Broad application accepted the complete expected nine-agent team but
  exceeded the fixed latency gate at 16712.282 ms.

Descriptive upstream scored 4/19 with precision 0.794872, recall 0.534483, F1
0.639175, 5/19 complete typed coverage, p50 14325.921 ms, p95/max 26469.788
ms, complete required disabled disclosure, and zero scored safety selections.
The benchmark was invalid: repository security and broad application returned
unknown disabled shadows, while runtime routing and incremental LSP returned
invalid assignment rows. These four errors are validity failures, never
losses or comparative evidence.

```text
python-production-change | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=10144.178 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=11346.399 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[python-bug-matched-to-python-application-engineer,failure-path-testing-matched-to-software-test-engineer,independent-review-matched-to-code-reviewer,separate-contexts-preserved-for-specialists] | fairness=[]
typescript-production-change | helpful=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=7516.944 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[typescript-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=10583.967 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[typescript-feature-implementation,dedicated-test-coverage,independent-code-review] | fairness=[]
backend-service-change | helpful=[backend-service-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[backend-service-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.888889 ms=8939.435 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[backend-service-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=15243.769 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[backend-implementation-selected,integration-test-specialist-selected,independent-code-review-selected,separate-contexts-enforced] | fairness=[]
installed-cross-platform-release | helpful=[software-test-engineer,code-reviewer,cross-platform-release-verifier] | A=abstained/fail selected=[] f1=0 ms=7400.576 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,cross-platform-release-verifier,software-test-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[required_agents_missing,no_safe_sufficient_team,recruiter_abstained] | U=accepted/pass selected=[cross-platform-installer-engineer,software-test-engineer,cross-platform-release-verifier,application-integration-verifier,code-reviewer] f1=0.75 ms=13735.753 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[cross-platform-packaging,windows-linux-installation,installed-release-verification,integration-testing,independent-code-review,distinct-specialist-contexts] | fairness=[]
application-integration | helpful=[software-test-engineer,code-reviewer,application-integration-verifier] | A=accepted/pass selected=[minimal-change-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.75 ms=7505.015 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[agents-orchestrator,backend-service-engineer,software-test-engineer,application-integration-verifier] f1=0.571429 ms=15959.21 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer;art:review-report;life:review] rc=[exact-agent-id-match,implementation-testing-verification-decomposition,complementary-test-engineer,independent-integration-verification,isolated-specialist-contexts] | fairness=[]
application-observability | helpful=[application-observability-engineer,software-test-engineer,code-reviewer] | A=accepted/pass selected=[application-observability-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=0.857143 ms=10836.709 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[application-observability-engineer,software-test-engineer,code-reviewer] f1=1 ms=16897.28 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[production-observability-requires-runtime-telemetry-and-failure-diagnostics,failure-telemetry-requires-executable-failure-path-tests,independent-review-required,separate-contexts-preserved-for-specialists] | fairness=[]
documentation-change | helpful=[technical-writer,code-reviewer] | A=accepted/pass selected=[technical-writer,code-reviewer] f1=1 ms=6582.012 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[technical-writer,codebase-archaeologist] f1=0.5 ms=9786.189 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer;art:documentation] rc=[documentation-rewrite-selected,independent-technical-accuracy-review-selected,separate-contexts-for-independent-specialists,all-selected-agent-ids-are-allowed] | fairness=[]
selection-safety-review | helpful=[selection-safety-critic] | A=accepted/pass selected=[selection-safety-critic] f1=1 ms=5915.837 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[agents-orchestrator,selection-safety-critic] f1=0.666667 ms=9597.599 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[resident-coordination-required,selection-safety-critic-is-direct-semantic-fit,separate-specialist-contexts,no-composition-conflict-between-selected-agents] | fairness=[]
repository-security-patch-review | helpful=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] | A=accepted/pass selected=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] f1=1 ms=11152.619 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=10677.625 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:ai-generated-code-security-auditor,code-reviewer,codebase-onboarding-engineer;art:review-report;life:discovery,review] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[repository-security-patch-review:arm_error]
runtime-routing-integration-failure | helpful=[application-integration-verifier,selection-safety-critic,test-results-analyzer] | A=abstained/fail selected=[] f1=0 ms=11288.005 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-integration-verifier,selection-safety-critic,test-results-analyzer;art:review-report,test-evidence;life:review,testing] rc=[selection_confidence_too_low] | U=error/fail selected=[] f1=0 ms=18806.977 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-integration-verifier,selection-safety-critic,test-results-analyzer;art:review-report,test-evidence;life:review,testing] rc=[provider_response_contract_invalid,upstream assignment row is invalid] | fairness=[runtime-routing-integration-failure:arm_error]
active-incident-containment | helpful=[incident-responder,incident-response-commander] | A=accepted/pass selected=[incident-responder] f1=0.666667 ms=7432.182 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[incident-responder,secrets-credential-hygiene-engineer,threat-detection-engineer] f1=0.4 ms=17209.961 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:analysis;life:discovery] rc=[active-security-incident,forensic-preservation-required,reversible-recovery-required,offensive-probing-excluded] | fairness=[]
lsp-incremental-index | helpful=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=10975.368 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=21504.332 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,lsp-index-engineer,software-test-engineer,test-results-analyzer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream assignment row is invalid] | fairness=[lsp-incremental-index:arm_error]
disabled-lsp-winner | helpful=[lsp-index-engineer] | A=abstained/fail selected=[] f1=0 ms=7111.808 safety=f0/i0/c0 disabled=[]/required=[lsp-index-engineer] missing=[disabled:lsp-index-engineer] rc=[no_safe_sufficient_team,recruiter_abstained] | U=abstained/pass selected=[] f1=0 ms=14325.921 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[best-fit-specialist-disabled,no-safe-equivalent-substitution,safest-next-step-enable-or-manually-review-lsp-index-engineer] | fairness=[]
incidental-finance-language | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=10151.442 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=13002.977 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[python-implementation,failure-path-testing,independent-review,financial-analysis-excluded] | fairness=[]
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=accepted/fail selected=[python-application-engineer,typescript-application-engineer,application-observability-engineer,software-test-engineer,accessibility-auditor,cross-platform-release-verifier,test-results-analyzer,code-reviewer,application-integration-verifier] f1=1 ms=16712.282 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=26469.788 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor,application-integration-verifier,application-observability-engineer,code-reviewer,cross-platform-release-verifier,python-application-engineer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[broad-python-typescript-application:arm_error]
brand-and-whimsy-separated | helpful=[brand-guardian,whimsy-injector,accessibility-auditor] | A=accepted/pass selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=9032.966 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=16628.256 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:review-report;life:review] rc=[exact-agent-id-match,brand-governance-routed-to-brand-guardian,playful-interface-routed-to-whimsy-injector,whimsy-injector-requirement-satisfied-by-accessibility-auditor,separate-isolated-contexts,independent-accessibility-review] | fairness=[]
accounts-payable-cfo-separated | helpful=[accounts-payable-agent,chief-financial-officer] | A=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=11542.004 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=9055.325 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:review-report] rc=[domain-specialization-match,explicit-independent-review,separate-contexts-required,selection-conflict-isolation] | fairness=[]
postgres-write-query-analysis | helpful=[database-optimizer] | A=accepted/pass selected=[database-optimizer] f1=1 ms=5119.819 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[database-optimizer] f1=1 ms=8660.985 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[direct-specialist-match,read-only-analysis-scope,no-documentation-or-code-change-required] | fairness=[]
clinical-legal-boundary-review | helpful=[clinical-evidence-agent,legal-document-review] | A=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=7421.446 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=19344.609 safety=f0/i0/c0 disabled=[]/required=[] missing=[life:discovery] rc=[domain-specialization,independent-review-required,no-diagnosis,no-billing-coding,no-compliance-certification] | fairness=[]
```

The raw and derived files remain outside the repository at
`C:\tmp\agency-runtime-ar119-019f8ee1-full-20260723-145700`.

### Instrumented recovery of the four varied misses

The complete corpus was committed as substantive `6049510` with ledger
`7b91cf8`. From that clean checkpoint, a zero-provider-call validation bound
exactly installed release, runtime routing, disabled LSP, and broad application
to the unchanged generation 561 roster, 247-tool context, provider, model, low
effort, one-call budget, and 15000 ms gate. The parser validated those cases
against the preserved 19/19 Agency corpus and the newest four-failure corpus
before launch. The pass-through router durably captured every complete Agency
outcome before scoring.

The process returned status 1 in 109.988309 seconds because the benchmark was
invalid. Its byte-identical 768,427-byte stdout/report had SHA-256
`2bc25b57ea7b5d86b36d8ef38bba1c2d6d510a88358b62a28814ed892181ac93`;
stderr was empty. The 3,350-byte exact projection had SHA-256
`fb72cf528a86e079cee3b46e8cb60debaf803fa740826b845f006d6b2e239a50`,
and the 249,364-byte plan-shape analysis had SHA-256
`fcf4c426211e497891e2058c39cceb4bdaa086166f1225d4699723f42f6427d9a2`.

Agency passed 4/4 with precision 0.833333, recall 0.937500, F1 0.882353, 4/4
complete typed coverage, complete required disabled disclosure, p50 8848.103
ms, p95/max 14074.396 ms, and zero forbidden, ineligible, conflict, or unsafe
selections. Installed release accepted the complete five-agent team at
6962.794 ms; runtime routing accepted its complete four-agent team at
9656.861 ms; disabled LSP safely abstained with the required disabled-winner
disclosure at 8039.345 ms; and broad application accepted the complete
nine-agent team at 14074.396 ms.

Descriptive upstream passed 1/4 with precision 0.166667, recall 0.062500, F1
0.090909, 2/4 typed coverage, complete required disabled disclosure, p50
17544.041 ms, p95/max 24837.778 ms, and zero safety selections. Installed
release returned unknown disabled shadows and broad application returned an
invalid assignment row. Those two errors make the bounded benchmark invalid;
they are not losses or comparative evidence.

```text
installed-cross-platform-release | helpful=[software-test-engineer,code-reviewer,cross-platform-release-verifier] | A=accepted/pass selected=[cross-platform-installer-engineer,software-test-engineer,code-reviewer,test-results-analyzer,cross-platform-release-verifier] f1=0.75 ms=6962.794 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=17323.525 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,cross-platform-release-verifier,software-test-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[installed-cross-platform-release:arm_error]
runtime-routing-integration-failure | helpful=[application-integration-verifier,selection-safety-critic,test-results-analyzer] | A=accepted/pass selected=[codebase-onboarding-engineer,application-integration-verifier,test-results-analyzer,selection-safety-critic] f1=0.857143 ms=9656.861 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[agents-orchestrator,multi-agent-systems-architect,codebase-archaeologist,test-automation-engineer,selection-safety-critic] f1=0.25 ms=17764.556 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-integration-verifier,test-results-analyzer] rc=[resident-coordination-required,routing-and-delegation-architecture-match,repository-drift-audit-match,local-integration-testing-match,independent-staffing-audit-match] | fairness=[]
disabled-lsp-winner | helpful=[lsp-index-engineer] | A=abstained/pass selected=[] f1=0 ms=8039.345 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[no_safe_sufficient_team,recruiter_abstained,selection_margin_too_low] | U=accepted/pass selected=[codebase-archaeologist] f1=0 ms=10150.842 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[best-semantic-specialist-disabled,safe-neighbor-selected-for-read-only-diagnosis,preserve-evidence-before-implementation] | fairness=[]
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=accepted/pass selected=[python-application-engineer,typescript-application-engineer,application-observability-engineer,software-test-engineer,accessibility-auditor,code-reviewer,application-integration-verifier,test-results-analyzer,cross-platform-release-verifier] f1=1 ms=14074.396 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=24837.778 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:accessibility-auditor,application-integration-verifier,application-observability-engineer,code-reviewer,cross-platform-release-verifier,python-application-engineer,software-test-engineer,test-results-analyzer,typescript-application-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[provider_response_contract_invalid,upstream assignment row is invalid] | fairness=[broad-python-typescript-application:arm_error]
```

The complete outcome hashes were:

- installed release: 56,613 bytes, SHA-256
  `b77c669e4776c3f332ffb0560510bd8ca57f0d4c07e97ca56eb69a80a93d44a6`,
  plan/proposal hash
  `sha256:05d22b3895ae1be53cc4b347dc2e6686f2ed8cda8c04cc8ad3a180726a84f781`;
- runtime routing: 35,368 bytes, SHA-256
  `3e8502cc9f4b9c3975370485ce6f461948b0f049632492e090fdd153c3231957`,
  plan/proposal hash
  `sha256:599ea558f8c0b6194bc3ca1378708b59b85ea9591a0f425fe11266f69e751e5d`;
- disabled LSP: 24,461 bytes, SHA-256
  `a72767fa6ece8df023155a84b2bedc36bc05adad5369155db6933140c7766422`,
  plan/proposal hash
  `sha256:bb8d36765397153e88274cc2ae4c2ebd85ac84f73d0a1eb2023ffcaa0dfcfe72`;
- broad application: 93,808 bytes, SHA-256
  `e609d1f39ef61f0455f96d0c938948b8520f31d09372f9b0d6288f18ea0eb326`,
  plan/proposal hash
  `sha256:c70a02ebb8f8df445988226ed0f71825b95fc07eb2f5db3b6f1dbafd719acdbe`.

The three accepted outcomes used complete governed teams; every accepted unit
had confidence and margin 1.0. The disabled case used a two-unit plan, exposed
`lsp-index-engineer` as the disabled semantic winner in both units, and safely
abstained when its second unit had no safe deterministic team. All four latest
complete-corpus failures therefore recovered under identical bounds. This is
variance, not a repeatable governed defect. No product, policy, parser,
coverage, latency, or call-budget rule changed, and no superiority claim is
made. The raw and derived files remain outside the repository at
`C:\tmp\agency-runtime-ar119-019f8ee1-four-failures-instrumented-20260723-151600`.

### Second complete 19/19 Agency corpus with one invalid upstream arm

The four-case recovery was committed as substantive `48e3022` with ledger
`3e34c6f`. From that clean checkpoint, one further unchanged complete 19-case
Windows corpus retained roster generation 561, 272 workers, 247 tools,
`codex-subscription`, requested and actual `gpt-5.6-luna`, low effort, the
explicit-model receipt, the one-call fast budget, and the 15000 ms cold gate.
Observational telemetry was 22.8 percent immediately before launch; the clean
checkpoint was already satisfied and the same task continued.

The process returned status 1 in 406.071759 seconds. Its 1,195,829-byte stdout
had SHA-256
`2e051f5aa2aa7b158a2ba799fde3ca9ff0e413a89fd587d0be740d090063b530`;
stderr was empty with the standard empty-stream SHA-256. The independently
verified 13,313-byte exact projection had SHA-256
`bab3fbf0c735603439914d284afc5a044d154b6e56f27715ef8dbdefbc6400c6`.
The corpus, base-roster, and allowed-agent fingerprints remained respectively
`sha256:7358cb9422cef681dc7d85323160652029792916c2ea74d81514df6cfebbba38`,
`sha256:c80b7422124f5935d3956ec48d6d0fffca15e7c23ebd155475998c7418e4f795`,
and
`sha256:88d310bad3716357bf49a74c53a873236cf9c549b878c3c190b4affebead7765`.
All 38 arms retained the exact provider, model, receipt, one-call, applied-
inference, and 15000 ms bindings.

Agency passed all 19/19 cases with precision 0.888889, recall 0.965517, F1
0.925620, 19/19 complete typed coverage, complete required disabled-winner
disclosure, p50 7948.958 ms, p95/max 12942.243 ms, and zero forbidden,
ineligible, conflict, or unsafe selections. This is the second complete 19/19
Agency observation in the recovery sequence. It supports repeatability under
the fixed controls but does not establish comparative superiority.

Descriptive upstream scored 4/19 with precision 0.727273, recall 0.689655, F1
0.707965, 6/19 complete typed coverage, complete required disabled disclosure,
p50 12062.573 ms, p95/max 23146.736 ms, and zero scored safety selections.
Exactly one arm made the benchmark invalid: application observability returned
unknown disabled shadows. That provider-contract error is a validity failure,
never an upstream loss. No Agency failure required bounded confirmation, and
no product or policy change was made.

```text
python-production-change | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=7481.589 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=11155.853 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[python-application-engineer-selected-for-python-application-fix,software-test-engineer-selected-for-failure-path-test-code,code-reviewer-selected-for-independent-review,separate-contexts-required-for-specialist-independence] | fairness=[]
typescript-production-change | helpful=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=6509.839 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[typescript-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=12062.573 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[typescript-application-engineer-selected-for-typescript-implementation,software-test-engineer-selected-for-executable-test-coverage,code-reviewer-selected-for-independent-code-review,separate-contexts-enforced] | fairness=[]
backend-service-change | helpful=[backend-service-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[backend-service-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.888889 ms=7948.958 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[backend-service-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=12202.694 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[backend-service-engineer-is-the-semantic-match-for-production-backend-endpoint-implementation,software-test-engineer-is-the-semantic-match-for-integration-test-code,code-reviewer-is-the-semantic-match-for-independent-code-review,separate-specialists-use-distinct-contexts] | fairness=[]
installed-cross-platform-release | helpful=[software-test-engineer,code-reviewer,cross-platform-release-verifier] | A=accepted/pass selected=[cross-platform-installer-engineer,software-test-engineer,code-reviewer,test-results-analyzer,cross-platform-release-verifier] f1=0.75 ms=6288.571 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[cross-platform-installer-engineer,desktop-app-engineer,software-test-engineer,application-integration-verifier,cross-platform-release-verifier,code-reviewer] f1=0.666667 ms=18501.408 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[selected-specialists-for-cross-platform-packaging,selected-independent-testing-and-installed-release-verification,selected-code-reviewer-for-final-defect-review] | fairness=[]
application-integration | helpful=[software-test-engineer,code-reviewer,application-integration-verifier] | A=accepted/pass selected=[minimal-change-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.75 ms=6604.231 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[backend-service-engineer,software-test-engineer,application-integration-verifier] f1=0.666667 ms=15528.125 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer;art:review-report;life:review] rc=[exact2agent2ids2selected2from2allowed2agent2ids,implementation2testing2and2independent2verification2are2separated,specialists2use2distinct2isolated2contexts,no2disabled2semantic2winner2was2present] | fairness=[]
application-observability | helpful=[application-observability-engineer,software-test-engineer,code-reviewer] | A=accepted/pass selected=[application-observability-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=0.857143 ms=8670.298 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=11573.384 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-observability-engineer,code-reviewer,software-test-engineer;art:implementation-change,review-report,test-code;life:implementation,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[application-observability:arm_error]
documentation-change | helpful=[technical-writer,code-reviewer] | A=accepted/pass selected=[technical-writer,code-reviewer] f1=1 ms=6794.01 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[technical-writer,code-reviewer] f1=1 ms=10463.669 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:documentation] rc=[documentation-rewrite-and-independent-technical-review,separate-contexts-for-independent-specialists] | fairness=[]
selection-safety-review | helpful=[selection-safety-critic] | A=accepted/pass selected=[selection-safety-critic] f1=1 ms=5989.6 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[selection-safety-critic] f1=1 ms=9367.656 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[exact-domain-match,independent-selection-safety-review,no-explicit-plan-candidates-supplied] | fairness=[]
repository-security-patch-review | helpful=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] | A=accepted/pass selected=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] f1=1 ms=10559.407 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[codebase-archaeologist,code-reviewer,application-security-engineer] f1=0.333333 ms=13334.753 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:ai-generated-code-security-auditor,codebase-onboarding-engineer] rc=[read-only-review-request,separate-code-path-mapping,independent-correctness-review,independent-exploitability-audit,isolated-contexts-for-specialists] | fairness=[]
runtime-routing-integration-failure | helpful=[application-integration-verifier,selection-safety-critic,test-results-analyzer] | A=accepted/pass selected=[codebase-onboarding-engineer,application-integration-verifier,test-results-analyzer,selection-safety-critic] f1=0.857143 ms=9034.871 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[multi-agent-systems-architect,test-automation-engineer,selection-safety-critic,codebase-archaeologist] f1=0.285714 ms=18131.354 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-integration-verifier,test-results-analyzer;art:test-evidence] rc=[request-is-routing-and-orchestration-diagnosis,live-local-integration-testing-required,independent-staffing-audit-required,isolated-specialist-contexts] | fairness=[]
active-incident-containment | helpful=[incident-responder,incident-response-commander] | A=accepted/pass selected=[incident-responder] f1=0.666667 ms=7675.382 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[incident-responder,secrets-credential-hygiene-engineer,threat-detection-engineer] f1=0.4 ms=11843.158 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:analysis;life:discovery] rc=[active-incident-routing,forensic-preservation-required,reversible-recovery-required,offensive-probing-excluded,separate-specialist-contexts] | fairness=[]
lsp-incremental-index | helpful=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=10487.372 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[lsp-index-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=12850.573 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[matched-specialized-lsp-implementation-to-indexing-scope,matched-failure-path-test-specialist,matched-independent-code-reviewer,separate-contexts-required-for-specialists] | fairness=[]
disabled-lsp-winner | helpful=[lsp-index-engineer] | A=abstained/pass selected=[] f1=0 ms=8822.19 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[no_safe_sufficient_team,recruiter_abstained,selection_margin_too_low] | U=accepted/pass selected=[codebase-archaeologist] f1=0 ms=11273.745 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[best-specialist-disabled,use-read-only-nearest-neighbor-diagnosis,preserve-independent-context,defer-implementation-until-lsp-specialist-is-enabled] | fairness=[]
incidental-finance-language | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=8314.762 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=13654.76 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[matched-python-implementation-to-python-application-engineer,matched-failure-path-testing-to-software-test-engineer,matched-independent-review-to-code-reviewer,excluded-finance-specialists-per-explicit-request] | fairness=[]
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=accepted/pass selected=[python-application-engineer,typescript-application-engineer,application-observability-engineer,software-test-engineer,accessibility-auditor,cross-platform-release-verifier,test-results-analyzer,code-reviewer,application-integration-verifier] f1=1 ms=12942.243 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[backend-architect,frontend-developer,python-application-engineer,software-test-engineer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-installer-engineer,cross-platform-release-verifier] f1=0.666667 ms=23146.736 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,test-results-analyzer,typescript-application-engineer;art:review-report] rc=[multi-component-production-build,backend-and-frontend-implementation,failure-path-testing-required,accessibility-review-required,observability-required,independent-integration-verification-required,cross-platform-release-evidence-required] | fairness=[]
brand-and-whimsy-separated | helpful=[brand-guardian,whimsy-injector,accessibility-auditor] | A=accepted/pass selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=9740.083 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=13567.303 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:review-report;life:review] rc=[separate-work-units-required,whimsy-injector-requirementsatisfied,independent-accessibility-audit-selected,brand-guardian-and-whimsy-injector-conflict-isolated-by-distinct-contexts] | fairness=[]
accounts-payable-cfo-separated | helpful=[accounts-payable-agent,chief-financial-officer] | A=accepted/pass selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=7931.45 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=9481.262 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:review-report] rc=[exact-agent-id-match,accounts-payable-specialist-selected,chief-financial-officer-selected,separate-contexts-required-by-conflict-policy,both-selected-agents-enabled] | fairness=[]
postgres-write-query-analysis | helpful=[database-optimizer] | A=accepted/pass selected=[database-optimizer] f1=1 ms=5227.271 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[database-optimizer] f1=1 ms=10492.361 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[exact-agent-id-allowed,semantic-fit-database-query-optimization,analysis-only-scope,no-code-or-documentation-change] | fairness=[]
clinical-legal-boundary-review | helpful=[clinical-evidence-agent,legal-document-review] | A=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=8619.059 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=9257.08 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[clinical-evidence-agent-selected-for-source-grounded-clinical-evidence-summary,legal-document-review-selected-for-independent-legal-document-review,separate-contexts-used-for-independent-specialist-work,no-diagnosis-medical-billing-or-compliance-certification-requested] | fairness=[]
```

The raw and derived files remain outside the repository at
`C:\tmp\agency-runtime-ar119-019f8ee1-full-20260723-152800`.

### Complete corpus after the second 19/19 observation

The second 19/19 corpus was committed as substantive `0dfe777` with ledger
`644aec1`. From that clean checkpoint, the next unchanged 19-case Windows
corpus retained the exact generation 561 roster, 247-tool context, provider,
requested and actual model, low effort, explicit-model receipt, one-call fast
budget, and 15000 ms gate.

The process returned status 1 in 441.588810 seconds. Its 1,189,496-byte stdout
had SHA-256
`c3d5276a257e3ec6fefd7a64ca1c24b1c852ae6ca12853a0c0d48864c7523707`;
stderr was empty. The 12,979-byte exact projection had SHA-256
`72ff44fb13c003221bb623fbeb2d487ad1a170759eb8ff3f9c8fc9dff111524e`.
Corpus, roster, and allowed-agent fingerprints remained unchanged, and all 38
arms retained the exact provider/model/receipt, one-call, applied-inference,
and 15000 ms bindings.

Agency scored 17/19 with precision 0.885246, recall 0.931034, F1 0.907563,
17/19 typed coverage, complete required disabled disclosure, p50 8122.589 ms,
p95/max 14466.738 ms, and zero forbidden, ineligible, conflict, or unsafe
selections. Active incident containment safely abstained on
`selection_margin_too_low` at 8122.589 ms. Accounts payable accepted only
`accounts-payable-agent` at 7509.934 ms and omitted the required independent
`chief-financial-officer` review.

Descriptive upstream scored 5/19 with precision 0.764706, recall 0.672414, F1
0.715596, 7/19 typed coverage, complete disabled disclosure, p50 12101.971 ms,
p95/max 22695.622 ms, and zero safety selections. Installed release,
selection-safety review, and runtime routing returned unknown disabled shadows,
so the benchmark is invalid and none of those arms is a loss.

```text
python-production-change | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=8784.13 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=11818.539 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[python-application-engineer-selected-for-python-implementation,software-test-engineer-selected-for-failure-path-test-code,code-reviewer-selected-for-independent-review,separate-contexts-preserved] | fairness=[]
typescript-production-change | helpful=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=7765.881 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[typescript-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=11834.891 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[typescript-feature-matched-to-typescript-application-engineer,tests-matched-to-software-test-engineer,independent-review-matched-to-code-reviewer,separate-contexts-preserved,all-selected-agent-ids-present-in-allowed-agent-ids] | fairness=[]
backend-service-change | helpful=[backend-service-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[backend-service-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.888889 ms=8072.417 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[backend-service-engineer,software-test-engineer,application-integration-verifier,code-reviewer] f1=0.75 ms=17373.039 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer] rc=[backend-implementation-match,integration-testing-match,independent-code-review-match,separate-contexts-for-specialists] | fairness=[]
installed-cross-platform-release | helpful=[software-test-engineer,code-reviewer,cross-platform-release-verifier] | A=accepted/pass selected=[cross-platform-installer-engineer,software-test-engineer,code-reviewer,test-results-analyzer,cross-platform-release-verifier] f1=0.75 ms=5881.575 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=18698.328 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,cross-platform-release-verifier,software-test-engineer;art:implementation-change,review-report,test-code,test-evidence;life:implementation,release,review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[installed-cross-platform-release:arm_error]
application-integration | helpful=[software-test-engineer,code-reviewer,application-integration-verifier] | A=accepted/pass selected=[minimal-change-engineer,software-test-engineer,code-reviewer,application-integration-verifier,test-results-analyzer] f1=0.75 ms=7115.206 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[backend-service-engineer,software-test-engineer,application-integration-verifier] f1=0.666667 ms=11192.358 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer;art:review-report;life:review] rc=[implementation-testing-verification-pipeline,distinct-contexts-for-specialists,independent-final-verification] | fairness=[]
application-observability | helpful=[application-observability-engineer,software-test-engineer,code-reviewer] | A=accepted/pass selected=[application-observability-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=0.857143 ms=12980.227 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[application-observability-engineer,software-test-engineer,application-integration-verifier,code-reviewer] f1=0.857143 ms=11438.232 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[production-observability-match,failure-telemetry-match,test-code-match,independent-review-match,separate-contexts-for-specialists] | fairness=[]
documentation-change | helpful=[technical-writer,code-reviewer] | A=accepted/pass selected=[technical-writer,code-reviewer] f1=1 ms=6998.609 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[technical-writer,code-reviewer] f1=1 ms=12101.971 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[documentation-and-independent-review,technical-writer-selected-for-repository-grounded-documentation,code-reviewer-selected-for-independent-accuracy-review,separate-contexts-for-independent-specialists] | fairness=[]
selection-safety-review | helpful=[selection-safety-critic] | A=accepted/pass selected=[selection-safety-critic] f1=1 ms=14466.738 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=12001.864 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:selection-safety-critic;art:review-report;life:review] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[selection-safety-review:arm_error]
repository-security-patch-review | helpful=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] | A=accepted/pass selected=[codebase-onboarding-engineer,code-reviewer,ai-generated-code-security-auditor] f1=1 ms=9518.378 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[codebase-onboarding-engineer,code-reviewer,senior-secops-engineer] f1=0.666667 ms=13850.922 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:ai-generated-code-security-auditor] rc=[matched-read-only-code-path-mapping,matched-independent-correctness-review,matched-defensive-security-exploitability-review,separate-contexts-for-independent-specialists] | fairness=[]
runtime-routing-integration-failure | helpful=[application-integration-verifier,selection-safety-critic,test-results-analyzer] | A=accepted/pass selected=[codebase-onboarding-engineer,application-integration-verifier,test-results-analyzer,selection-safety-critic] f1=0.857143 ms=10839.059 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=error/fail selected=[] f1=0 ms=19983.169 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:application-integration-verifier,selection-safety-critic,test-results-analyzer;art:review-report,test-evidence;life:review,testing] rc=[provider_response_contract_invalid,upstream disabled shadows contain unknown workers] | fairness=[runtime-routing-integration-failure:arm_error]
active-incident-containment | helpful=[incident-responder,incident-response-commander] | A=abstained/fail selected=[] f1=0 ms=8122.589 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:incident-responder;art:analysis,plan;life:discovery,planning] rc=[selection_margin_too_low] | U=accepted/fail selected=[incident-responder,secrets-credential-hygiene-engineer,threat-detection-engineer] f1=0.4 ms=14427.578 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:analysis] rc=[active-incident-routing,forensic-preservation-required,reversible-recovery-required,offensive-probing-excluded,specialists-isolated-by-context] | fairness=[]
lsp-incremental-index | helpful=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[lsp-index-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=8198.781 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[lsp-index-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=12210.699 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[exact-specialist-match,independent-review-required,isolated-contexts-required] | fairness=[]
disabled-lsp-winner | helpful=[lsp-index-engineer] | A=abstained/pass selected=[] f1=0 ms=12209.845 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[no_safe_sufficient_team,recruiter_abstained,selection_margin_too_low] | U=accepted/pass selected=[codebase-archaeologist,test-automation-engineer] f1=0 ms=11642.2 safety=f0/i0/c0 disabled=[lsp-index-engineer]/required=[lsp-index-engineer] missing=[] rc=[semantic-best-match-disabled,use-read-only-codepath-diagnosis-first,preserve-cancellation-and-stale-symbol-reproduction-before-implementation,separatespecialistsintodistinctcontexts] | fairness=[]
incidental-finance-language | helpful=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] | A=accepted/pass selected=[python-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer] f1=1 ms=7968.436 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[python-application-engineer,software-test-engineer,code-reviewer] f1=0.857143 ms=10697.081 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:test-results-analyzer;art:test-evidence] rc=[python-specialist-selected-for-parser-implementation,dedicated-test-engineer-selected-for-failure-path-tests,independent-code-review-selected,no-financial-analysis-agent-selected,separate-contexts-enforced] | fairness=[]
broad-python-typescript-application | helpful=[python-application-engineer,typescript-application-engineer,software-test-engineer,code-reviewer,test-results-analyzer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-release-verifier] | A=accepted/pass selected=[python-application-engineer,typescript-application-engineer,software-test-engineer,application-observability-engineer,accessibility-auditor,code-reviewer,application-integration-verifier,test-results-analyzer,cross-platform-release-verifier] f1=1 ms=12029.825 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[product-manager,backend-architect,python-application-engineer,frontend-developer,software-test-engineer,accessibility-auditor,application-observability-engineer,application-integration-verifier,cross-platform-installer-engineer,cross-platform-release-verifier] f1=0.631579 ms=22695.622 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:code-reviewer,test-results-analyzer,typescript-application-engineer;art:review-report;life:review] rc=[selected-specialists-by-requested-work-shape,kept-isolated-specialists-in-distinct-contexts,used-available-roster-equivalents-for-upstream-role-labels] | fairness=[]
brand-and-whimsy-separated | helpful=[brand-guardian,whimsy-injector,accessibility-auditor] | A=accepted/pass selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=14393.571 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/fail selected=[brand-guardian,whimsy-injector,accessibility-auditor] f1=1 ms=14477.815 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:review-report;life:review] rc=[brand-governance-matched-to-brand-guardian,playful-details-matched-to-whimsy-injector,independent-accessibility-audit-matched-to-accessibility-auditor,isolated-contexts-preserved-for-separate-specialists,same-context-brand-whimsy-conflict-avoided] | fairness=[]
accounts-payable-cfo-separated | helpful=[accounts-payable-agent,chief-financial-officer] | A=accepted/fail selected=[accounts-payable-agent] f1=0.666667 ms=7509.934 safety=f0/i0/c0 disabled=[]/required=[] missing=[req:chief-financial-officer;art:review-report;life:review] rc=[] | U=accepted/fail selected=[accounts-payable-agent,chief-financial-officer] f1=1 ms=18898.777 safety=f0/i0/c0 disabled=[]/required=[] missing=[art:review-report] rc=[specialized-match,independent-review-required,same-context-conflict-avoided] | fairness=[]
postgres-write-query-analysis | helpful=[database-optimizer] | A=accepted/pass selected=[database-optimizer] f1=1 ms=5485.166 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[database-optimizer] f1=1 ms=8881.861 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[exact10domain10match,read-only10analysis10scope,no10documentation10or10application10code10change] | fairness=[]
clinical-legal-boundary-review | helpful=[clinical-evidence-agent,legal-document-review] | A=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=6754.952 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[] | U=accepted/pass selected=[clinical-evidence-agent,legal-document-review] f1=1 ms=9959.489 safety=f0/i0/c0 disabled=[]/required=[] missing=[] rc=[clinical-evidence-specialist-selected,legal-document-review-specialist-selected,separate-contexts-required-for-independent-specialists,no-diagnosis-request,no-medical-billing-request,no-compliance-certification-request] | fairness=[]
```

The raw and derived files remain outside the repository at
`C:\tmp\agency-runtime-ar119-019f8ee1-full-20260723-154100`.

### Production-hardening checkpoint 2026-07-26

The local implementation sequence now includes governed AR-128 through AR-155
slices. Commit/ledger pair `6a3bdaa`/`871ec14` specifically repairs AR-149
through AR-155 and passes 168 focused Python tests with 3 skips, four
post-review regressions, and 101 dashboard UI tests. These local repairs do not
close tracker, current-artifact, installed-host, or hosted gates, and AR-143
still deliberately lacks a positive production operator-presence backend.

The earlier complete integrated Python run passed 7,522 tests with 61 skips and
1 expected failure. The first exact coverage arm then failed at 96.66 percent
with four test-contract failures. A later pre-final-trace checkpoint preserved
that failed history and passed the ordinary warning-strict suite with 7,604
tests, 61 skips, and 1 expected failure; its exact coverage arm passed at 97.08
percent against the unchanged 97 percent floor, and its separate three-test
performance arm passed. Later implementation commits mean a final current-head
aggregate rerun was required at that checkpoint. The later final validation
section records the current result without rewriting this historical evidence.

The final deep-review slice confirmed and repaired a high-severity nested
Windows conditional-ACE trust bypass, three medium SQLite currentness defects,
and one low malformed-HMAC availability defect. Measured stable operational
routing fell from 1,104.677 ms to 663.671 ms and the module version entrypoint
from about 647 ms to 112 ms without positive trust caching. Focused ACL,
schema, Store/workforce, routing, UI, packaging, supply-chain, and dependency
checks are locally green. These are source controls, not a fresh current-source
installation, hosted portability result, valid matched outcome corpus, or
production-readiness claim.

### Native and workflow trust checkpoint 2026-07-27

Commit/ledger pair `f64ba1e`/`7b9e2d0` is the clean recovery boundary for the
native and workflow trust package. AR-143 now has one genuine positive mutation:
exact roster rollback on Windows 11 x64 prepares and binds the complete Store,
revision, authority, and workforce transition; verifies an identity-pinned
app-owned Windows consent helper; then revalidates under `BEGIN IMMEDIATE`
before commit. Every other persistent mutation and unsupported platform remains
fail closed. The helper is reproducibly built and platform-honestly packaged,
but it is still an unsigned review artifact; publisher/legal/signing/timestamp
authority and an attended success-and-denial Windows Hello canary remain AR-161
release blockers.

The same pair repairs repository-ancestor `PATH` poisoning (AR-164), stale
signed remediation authority and paged-history truth (AR-163), ambiguous
dependency-review fallback (AR-165), and dashboard read-only/correlation/privacy
copy gaps (AR-166). It also pairs isolated CI sessions and collapses unavailable
CodeQL fanout without removing exact coverage, compatibility, Windows, artifact,
or language surfaces. A historical 119.12-runner-minute pull-request run now
models at approximately 13.63 to 22.85 raw minutes and 13 rather than 24 jobs;
that is a projection, not a saving claim, because GitHub Actions billing rejects
new hosted jobs before execution.

Current bounded evidence includes 1,102 combined security/release/integration
tests with one platform skip, 166 remediation/dashboard projection tests, 115
release/workflow contracts, 102 dashboard UI tests, 577-file Ruff lint/format,
425-document verification, strict offline workflow security, and independent
review with no remaining actionable severity finding in the integrated slice.
Clean cross-OS artifacts, fresh installed-package dogfood, real-browser UI QA,
the complete current-head corpus, and hosted measurements still follow this
checkpoint and are not implied by it.

### Final UI-to-Store and CI-budget checkpoint 2026-07-27

The current hard-checkpoint package completes the requested final layered pass
through AR-170 through AR-175. Browser request identity and protected headers,
worker and roster response identity, mandatory worker evidence, safe JavaScript
revisions, effective-roster Store/configuration continuity, atomic public roster
pages, control-envelope Store continuity, Route Lab observation correlation,
and reduced lifecycle-reason privacy now fail closed with focused regressions.
The unsupported multi-endpoint dashboard control fallback is removed.

The final security-delta reviewer classified zero Critical, High, or Medium
findings and six Low findings, all repaired, with no remaining actionable
finding in that reviewed delta. The broader traceability review separately
prioritized the response cross-binding and snapshot-currentness defects as
Medium because they crossed authoritative UI, HTTP, service, Store, and SQL
boundaries. Both classifications and the repairs are retained; neither is a
claim that the external release gates have passed.

Focused evidence is 105 browser interaction tests, 121 release-packaging
contracts, 176 dashboard/workforce/roster tests with 3 platform skips, 19
fail-closed CI-scope tests, Ruff, Bandit on modified Python, strict offline
workflow security, and clean diff checks. The ten shipped dashboard assets are
257,620 bytes, 5,547 bytes below the unchanged ceiling. AR-174 structurally
reduces an eligible documentation-only primary pull-request lane from 13 hosted
runner allocations to 5 while retaining Linux and Windows artifacts plus
parity. The exhaustive four-shard coverage corpus and six-version compatibility
corpus are now explicit `workflow_dispatch` integration gates: pull requests
and pushes require both jobs to be skipped, while a manual aggregate requires
both to succeed. This is local structural proof, not measured hosted time or
savings.

The first exact final warning-strict run then passed 8,010 tests with 61 skips
and 1 expected failure but exposed 11 stale full-gate contracts after 33:25.
AR-176 repairs ten test-isolation/fixture defects without weakening production
and one Low missing-Node diagnostic defect. All original failures pass together,
and the combined neighboring package passes 670 tests with 1 platform skip. The
exact second current-head run passes 8,021 tests with 61 skips and 1 expected
failure in 32:11. The separate uninstrumented performance arm passes 3 tests
with 8,080 deselected in 20.66 seconds. The dashboard UI gate passes all 105
tests at 98.72 percent line, 91.00 percent branch, and 97.97 percent function
coverage.

The current-head Python coverage attempt was stopped before completion and is
not a passing result. Exhaustive coverage and compatibility are now owner-
requested manual integration work and were not rerun. The production verdict
stays **NO-GO** because generic installation, signed/presence-authorized
delivery, installed-host canaries, and the external hosted, benchmark-outcome,
branch-protection, and tracker gates remain open.

### Fresh artifact and regulated-gap checkpoint 2026-07-27

Exact candidate `29da6eca` now has clean Windows and Linux producer pairs. The
portable and `win_amd64` wheels plus their byte-identical sdist pass strict
metadata and independent merged-set verification. Fresh Windows Python 3.10 and
Linux Python 3.12 wheel/sdist installs pass the packaged smoke contract; the
portable wheel contains no executable or PE payload. A freshly installed
Windows-wheel dashboard then authenticated, rendered every section, refreshed,
reported no browser warning/error, and truthfully disabled Route Lab without a
verified enabled host. No hosted runner was used. Earlier live routing
reproduced one P0 false-sufficient-team defect: a DO-178C avionics-assurance
request was accepted with generic onboarding, test-results, and code-review
workers.

After the authorized push to `origin/main` at `880a5ce`, the named fast
production spine passed 521 tests with 5 platform skips in 74.94 seconds, the
105-test UI suite passed, and every routing-evaluation gate passed. Automatic
CI and CodeQL were rejected before runner allocation by the account billing
gate; exhaustive integration was not dispatched. Current Codex inventory is
registered and enabled but has launcher drift and unverified hook trust. A
current-profile canary completed without an Agency header, specialist,
correlated route, receipt, or accepted finalization. Candidate reinstall then
failed closed on operator-presence unavailability before any persistent change.
AR-179 and ADR-0103 now preserve named high-assurance standards as typed
independent-review capabilities. Generic review cannot cover them; an explicit
governed contract can. The focused 57-test intent/staffing slice and 64-test
inference/safety/hiring slice pass. The post-checkpoint live route then
abstained in 45.359 seconds with zero selected agents and
`required_agents_missing`, `no_safe_sufficient_team`, and
`recruiter_abstained`; its uncovered unit produced a truthful
`hiring_store_unavailable` diagnostic. Both configured-provider calls were
applied with requested/actual `gpt-5.6-luna` receipts. No activation,
delegation, hire, or contractor execution is claimed.

### Attended existing-Codex refresh checkpoint 2026-07-27

ADR-0104 and commit pair `30d5fc0`/`6d55e29` add the exact positive
existing-install Codex refresh without enabling generic or missing-host
installation. The focused transaction/security/native slice passes 341 tests,
the named production spine passes 522 with 5 platform skips in 75.89 seconds,
all 105 dashboard UI tests pass, and every routing-evaluation gate passes.

The exact committed Windows wheel (`7d071c8c...593f0`) and sdist
(`3a81eddf...e316`) were built in a clean detached worktree with an owner-
private Python 3.13 environment and passed strict metadata plus independent
distribution verification. A fresh wheel venv saw the real existing Codex
integration. One hidden attended attempt timed out before mutation and returned
`partial=false`, `state_preserved=true`, and no recovery requirement. A visible
retry completed Windows Hello and the prepared transaction with exit zero.
Post-install status proves new install ID
`7761d792-3dc3-4c92-8084-5cd524c63103`, bundle
`0c3696e1...084f3`, retained backup `20260727T160533.282423Z`, and native
version `0.1.0+codex.a106953cb0c7` installed/enabled under exact policy.

This is installation and registration evidence only. After renewed trust for
the refreshed exact hook commands, a fresh process proved a valid Agency
header, routing, expected `code-reviewer` selection, four planned delegations,
and Stop finalization. It correctly rejected the turn because no isolated child
activation was recorded. A delegation-enabled diagnostic planned five units
but timed out after 240 seconds without child activation or finalization. AR-180
owns the now-reproduced activation-canary gap. No attestation was persisted.
Fresh missing-host bootstrap, signed delivery, the roster-rollback canary, four
other host canaries, and the manual exact-head release gate remain open.

### Bounded final-candidate preparation checkpoint 2026-07-27

Commit pair `c625bc7`/`09ee942` removes five repeated 821-file private-runtime
hash passes from `agency smoke --all`: source smoke now passes all eight checks
with no failures or skips in 43.9 seconds instead of exceeding a 122.4-second
outer ceiling. Commit pair `1676f6a`/`c3251cd` adds a bounded immutable
workforce-contract serialization cache and removes unrelated test setup. The
reproduced workforce and MCP hotspots fell from 5.45 and 4.08 seconds to 2.66
and 0.81 seconds; all 98 touched tests passed with one platform skip. Neither
change weakens a launch attestation, preflight, assertion, coverage floor, or
automatic/manual workflow boundary.

Commit pair `b95d78a`/`15dbe0f` reconciles seven already accepted audit items to
the roadmap's canonical `done` status while leaving tracker creation visibly
pending authorization. Exact head `15dbe0f` has not yet been rebuilt or
installed; the last exact `44f930b` Windows wheel/sdist passed strict metadata,
independent verification, fresh Python 3.13 install, and packaged smoke before
the smoke optimization was committed. The current source/mobile UI and all 106
UI tests are green, but final installed desktop/mobile QA remains required.

AR-141's bounded consolidation audit found four security- or protocol-sensitive
remaining families: link/same-object path primitives, persisted/external JSON
loading, cross-layer digest ownership, and native-child/workforce authority
projection. Broad line-count-only decomposition is explicitly excluded from
the production push; only those evidence-backed boundaries are candidates for
the next package.

### Persisted Codex activation checkpoint 2026-07-27

The latest trusted live canary again reached the deterministic one-unit
`code-reviewer` route but produced no native activation evidence. A bounded
same-binary control established that Codex V2 delegation with `--ephemeral`
cannot recover the parent history required by its default fork: it failed after
about 73.5 seconds with a missing-parent error. The non-ephemeral form completed
in about 13.5 seconds and persisted one exact spawn, wait, parent-child edge,
and child completion even though exec JSONL omitted the successful spawn.

AR-180 now owns a source correction that keeps the activation parent persisted,
forces V2, requests `fork_turns="none"`, and reconciles bounded owner-private
rollout identity with the existing Store proof without retaining prompt or
reasoning content. The shared backend enables that contract only for Agency
activation: deferred product trials retain their custom ephemeral response
contract, and native-only canaries are ephemeral, delegation-disabled, and
no-tool. The current focused package passes 156 warning-strict tests with lint
and formatting clean. Installed checkpoint `194d697` predates the correction;
exact ledger candidate `1a58e5e` now has a strict-Twine and independently
verified Windows wheel/source pair. A fresh Python 3.13 wheel install passed
dependency checks, all eight packaged smoke checks, the installed option split,
and every offline routing gate. The current install remains untouched; attended
refresh, renewed hook trust, and one fresh bounded live canary remain. No hosted
or exhaustive workflow was run or is required for this checkpoint.

One subsequent isolated-profile attempt from the exact wheel remained on the
ordinary planner and selected `finops-engineer` plus `code-reviewer`. The
exact-one-child verifier accepted no collaboration or activation, persisted no
attestation, and closed the sole failed run; report SHA-256 is
`65981b64...fae95`. It was not retried. Only the existing-Store current-profile
contract admits the deterministic fixture, so this negative isolated result is
not a substitute for the attended live gate.

That fixture description is retained as historical evidence only. ADR-0118 and
AR-204 now require every production activation canary to obtain a valid
inference decision and provider-attempt receipts before any specialist exists.
The closed activation adapter may narrow only the already inferred worker to
the package-owned read-only diagnostic goal needed for Codex replay; it cannot
select, add, rank, or substitute a worker. Missing or invalid inference fails
the canary visibly with no deterministic fallback.

### The routing cache has never hit once, and cannot — measured 2026-08-11

**Zero of 200 recorded decisions came from `cache` or `session`; every one is `computed`.** That is
not a tuning problem, it is structural:

- `_ROUTING_CACHE` (`selector/cache.py:22`, TTL 600 s) and `_SESSION_ROUTING`
  (`selector/stickiness.py:17`, max age 300 s, 0.6 similarity) are both module-level
  `OrderedDict`s living in **process memory**.
- Every hook event is installed as `type: command` launching `python.exe` — verified in the host's
  own `hooks.json`, all ten events. **A fresh process per event.**

So both caches are constructed empty, populated once, and destroyed microseconds later, on every
single turn. The only production caller of the routing cache cannot, even in principle, observe a
hit. `cache_put` runs faithfully every turn and nothing ever reads it back.

**And the test suite proves the cache works.** `evals/benchmarks.py:509` asserts
`cache_probe["cache_hit"] is True` and passes — because the benchmark warms and probes **in one
process**. The cache is verified in the one configuration that never occurs in production. Green
test, dead feature. A textbook instance of the rule that reachability is not evidence of purpose.

**Why this is worth fixing rather than deleting.** Session stickiness targets follow-up turns
within 300 s at 0.6 similarity — the ordinary shape of a conversation, i.e. the common case, not an
edge case. At the measured cost of a miss (~2.4 provider calls, floor 8 s each on claude and 26–33 s
on codex) a working cache removes most of the routing cost from continuation turns.

**BUILT `f1fd9064` — `routing_cache`.** Persists a decision across processes, keyed and expired the
same way. It stores **only fields already allowlisted for persistence** (`_ROUTING_DECISION_FIELDS`,
bounded at 16 KB): the live routing dict also carries work-unit text and unit descriptors the
decision projection deliberately drops, and a cache is not a reason to widen what the store retains.
The compatibility receipt is therefore absent **by construction**, which is the point — its absence
sends a reused entry through the ordinary reuse path, revalidating every selected id against the
live catalog and recomputing compatibility locally. A persisted receipt would let a later process
accept a selection without rechecking it, the one way this cache could change which specialists a
turn gets. Reuse stays advisory: a store failure costs a later turn latency, never the turn that
produced the decision. **One bug caught by its own test:** expiry first compared against
`DATETIME('NOW', …)`, which yields `2026-08-11 19:33:02` while rows are written as
`2026-08-11T19:33:02.999000+00:00` — `'T'` sorts above `' '`, so every row passed and nothing ever
expired. Now compares in the written format.

**The original shape of the fix:** back the cache with the store rather than process memory.
`routing_decisions` already persists `context_fingerprint` and `query_hash` per decision, so most of
the identity a cross-process lookup needs is already being written every turn — only the normalized
cache key is absent. Confirm invalidation still keys on roster, policy, config and host before
reusing anything.

### `inference: unknown` on a healthy box — found and fixed at install 2026-08-11

**Installing the latency and cache work flipped the status line from `operational` to `unknown`,
and the install was not the cause — it only made an existing defect visible.**
`dashboard_operational._SUCCESS_STATES` did not contain `"accepted"`, which is precisely what the
semantic router writes for a healthy turn: **every** routing row in the live store carries it
(`pipeline.py:922` gates acceptance on it, `workforce/inference.py:531` and
`staffing_verifier.py:127` read it as success, and `workforce/promotion.py:9` already lists it in
its own `_SUCCESS_OUTCOMES`). Two success vocabularies, disagreeing — the recurring two-sources
shape.

With `accepted` in neither the success nor the failure set, state fell through to `unknown`. The
panel therefore reported **`operational` only when the newest record was a preflight failure that
had inference applied**, and `unknown` when the newest record was a turn that routed correctly.
Exactly backwards: a successful turn downgraded the panel, and a failure upgraded it. The install
merely wrote a fresh accepted routing row, which pushed the older preflight receipt out of newest
position and exposed it.

**Why it survived.** The existing test reached `operational` through `"inferred"`
(`test_dashboard_operational.py:564`) — a status nothing in production persists. Synthetic value,
green test, broken panel; the same failure mode as the cache above, one section up.

**Fixed** — `accepted` added to the vocabulary, with a test that asserts the status the router
really writes and that fails without the fix. Live box now reads
`inference: operational; 2 provider entries; eligible-turn inference required`.

### What breaks when the model changes — audited 2026-08-11

Prompted by the luna→terra bump. **The bump did not cause the codex failure, and did not help.**
`provider_response_contract_invalid` appears against `gpt-5.6-luna` on 2026-08-01, 08-02 (twice) and
08-03, well before terra. `codex exec --model gpt-5.6-terra` answers normally, so the model resolves
— what fails is the planner's *response* contract (`workforce/inference.py:878`), which fires when
the parser rejects the returned document. One repair retry with validation feedback, then the turn
fails. That path is coupled to model **behaviour**, not to its name, so a swap can change how often
it trips but no rename will fix it.

**Two places are coupled to the model's name, both by string prefix:**

- `structured_provider.py:380` — `provider.model.casefold().startswith("gpt-5")` selects
  `max_completion_tokens` and drops `temperature`; otherwise `max_tokens`.
- `judge_protocol.py:381` — `model.lower().startswith("gpt-5")`, same swap.

**They are already out of step with what we ship.** `config_defaults.yaml:103` sets
`model: gpt5.6-luna` — no hyphen after `gpt` — so `"gpt5.6-luna".startswith("gpt-5")` is **False**,
while the operator config on this box says `gpt-5.6-terra` and is **True**. Two boxes naming the
same family differently get different request bodies. The default path survives only because it
points at a LiteLLM proxy that normalizes the parameters; a direct OpenAI-compatible endpoint would
be sent the wrong pair.

**And the test cannot catch it:** `test_roster_inference_adapter.py:960` exercises the branch with
`model="gpt-5.6"`, a spelling nothing ships, while `test_inference_profiles.py:614` separately pins
the real default as `gpt5.6-luna`. Both green, neither crossing. Third instance today of the same
failure mode — after the routing cache verified only in-process, and `_SUCCESS_STATES` verified
through a status nothing persists.

**What is safe.** Model names flow through the CLI transport untouched (`cli_transport.py:973`
passes `--model` straight through). `model_requirements` on specialists is descriptive metadata in
the semantic projection, never a code gate, so a new model cannot make specialists unselectable.
`detect.py:307-331` holds stale suggestions (`gpt-5.4`, `gpt-5.5`) but only as fallbacks when
discovery fails, and `_preferred_model` degrades rather than rejecting. Thinking level is a separate
profile field, never appended to a model name — the `-low`/`-medium`/`-high` suffixes in the litellm
defaults are proxy aliases, so a rename there needs matching aliases on the proxy, not code changes.

**The fix, when wanted:** replace both prefix tests with one capability predicate keyed off the
provider entry rather than a substring of its name, and give it a test fed from
`config_defaults.yaml` so a default we ship can never disagree with a branch we take.

### Selection does not track the domain of the work — measured 2026-08-11

Two turns nine minutes apart, on one box, settle this better than any argument.

| time | the actual work | `frontend-developer` staffed? |
|---|---|---|
| 21:07 / 21:08 | Python provider-config change; message said *"i have codex in a worktree doing the ui dashboard stuff, **you continue with that**"* | **yes** |
| 21:16 | *"analyze what needs to be added/removed from **dashboard**, come up with a plan"* | **no** — `incident-response-commander` instead |

**Those two 21:0x decisions are two of only three times `frontend-developer` has ever been selected
across 202 recorded decisions.** It fired on the turn that told Agency to stay off the dashboard,
and stayed silent on the turn that was entirely about the dashboard. Anti-correlated with the
domain, not merely imprecise about it.

**An earlier draft of this entry blamed attribution** — that a clause naming someone else's work
("codex is doing X") becomes staffable because the only message-level controls over decomposition,
`workforce/inference.py:73` and `:78`, ask *how many* work units there are and never *whose* they
are. That is real and still worth fixing, but it cannot be the whole story: attribution explains a
false positive on turn A and says nothing about the miss on turn B, where the work was
unambiguously this turn's. Recording the incomplete diagnosis here rather than quietly replacing it,
because the second observation is what disproved the first.

**Eligibility does not excuse turn B.** `frontend-developer` lists `analysis` among its task types
and carries `authority: modify`, so an analyze-and-plan task was well within its contract. It is
also the roster's only frontend specialist. `incident-response-commander` was selected instead:
`authority: plan`, task types including `planning` — a match on the verb *"come up with a plan"*
while being a production-incident specialist with no dashboard relevance. Its seven prior selections
all sit beside `sre-site-reliability-engineer`, `devops-automator`, `it-service-manager`; genuinely
incident-shaped contexts. Turn B is the odd one out.

**The distribution says the same thing at scale.** Across 202 accepted decisions, mean 2.4
specialists each:

- **39 distinct specialists have ever been selected**, out of ~282 offered as candidates. Roughly
  86% of the roster has never once been chosen.
- **`code-reviewer` appears in 72.3%** of all decisions. A specialist chosen for nearly three turns
  in four is not a decision, it is a default.
- The top ten account for **82% of all selections**: `code-reviewer`, `codebase-onboarding-engineer`,
  `software-test-engineer`, `test-results-analyzer`, `minimal-change-engineer`, `technical-writer`,
  `application-integration-verifier`, `python-application-engineer`, `software-architect`,
  `typescript-application-engineer`.

Every one of those is an *activity* — review it, onboard on it, test it, write it up. Almost none
is a *domain*. The selector looks like it is keyed on the shape of the activity a message describes
and largely blind to the subject matter, which explains both observations at once: turn A's
dashboard nouns reached an implementer because the actual work was under-specified by a
back-reference ("continue with that"), and turn B's "come up with a plan" reached a planning
specialist without the dashboard ever constraining which one.

**Lucas's read, and it matches the data:** inference should establish the request's *intent* first,
then staff against it — rather than mapping surface features straight onto specialists.

**Before building.** The store is content-free by design — `routing_decisions` keeps
`source_message_hash` and `query_hash`, never message text — so wording cannot be correlated with
selections after the fact. Any evaluation of an intent-first change needs a labelled corpus built
deliberately, or instrumentation captured at decision time under an explicit retention decision.
That constraint is itself a finding: **we cannot currently audit selection quality from the
evidence we keep.**

**BUILT `5cea1a4d` — `routing_intent`, on Lucas's explicit retention decision.** Retains the
planner's own work-unit text beside the specialists that decision produced; `agency evidence intent`
prints one against the other. Because this inverts the content-free posture every other routing
table holds, it is **off unless `selector.record_routing_intent` is set** — bounded per unit and in
total, stripped of control characters before the audit surface can print it back to a terminal,
purged with the rest of the runtime evidence, and unable to fail a turn. The first test asserts the
default writes nothing at all.

**CORRECTED, and the real cause is narrower — FIXED.** The claim below, that there is no
subject-matter dimension, was drawn from the *persisted* descriptor, which is a content-free replay
artifact. The **live** side has domains end to end: `WorkUnit.domains` is **required**
(`planning_contracts.py:285`), workers declare `domains` (`contract.py:103`), `staffing_verifier.py:349`
matches them by set intersection, and `comparison.py:80` weights them at 0.20.

The defect was **resolution, not absence**. `_DIVISION_DOMAINS` maps a division to one domain, and a
division says which part of the *business* a specialist belongs to, not which part of the *system*
they work on — so all 54 `engineering` workers carried the single domain `software-engineering`.
On the one dimension meant to separate them, `frontend-developer` and `code-reviewer` were
identical, across the division holding nearly all real work. That is why a frontend specialist was
never nominated for a frontend task.

**`_CATEGORY_DOMAINS` promotes categories the roster already declares** into domain identifiers.
Measured on the shipped roster: **21 distinct domain tuples across the 54 engineering specialists,
up from 1.** `frontend-developer` → `('software-engineering', 'frontend')`;
`incident-response-commander` → `('software-engineering', 'operations')`, which is precisely why it
should not have matched a dashboard planning unit. Strictly additive — contracts only gain domains,
and the verifier's check is a set intersection — so nothing staffable before became unstaffable, and
a test asserts it. Another test asserts every promoted category actually appears in the roster; it
caught `ui-engineering`, which had been lifted from a test fixture and exists nowhere in production.

**Cost, paid deliberately.** The recruiter index grew 263,616 → 264,087 bytes (+471, +0.18%) against
a 288 KB ceiling. AR-227's exact-size pin is a change detector, and it worked — it stopped the change
until someone justified it. It now carries that justification, plus a new assertion on **remaining
headroom**, so the next promotion is measured against the budget that actually constrains the index
rather than quietly consuming it. Note the index is a roster snapshot, not per-turn prompt content —
the model receives a bounded candidate subset — so this is a memory cost, not a latency one.

**The earlier, wider claim, kept for the record:** `project_workforce_unit_descriptors`
(`workforce/routing_projection.py:131`) defines the router's own representation of a work unit, and
its entire vocabulary is activity: `artifact_kind` ∈ {analysis, architecture-record, documentation,
implementation-change, plan, review-report, test-code, test-evidence}, `lifecycle_phase` ∈
{coordination, discovery, documentation, design, implementation, planning, release, review,
testing}, `authority` ∈ {advise, plan, modify, review}. **There is no subject-matter dimension at
all.** A work unit literally cannot express "this is about the dashboard". So selection is not
merely under-weighting domain — the intermediate representation it staffs from cannot carry domain,
which is exactly what the 72.3% `code-reviewer` rate and the 39-of-282 tail look like from the
outside. An intent-first change has to widen this vocabulary, not just reword a prompt.

**Four declarations of one field, again.** Adding `selector.record_routing_intent` required the
dataclass, the renderer, `configuration_schema`'s strict allowlist, **and**
`configuration_patch._SET_VALIDATORS`. Missing the fourth meant `agency config set
selector.record_routing_intent true` — the exact command the empty audit surface prints — failed
with "operation path is not supported" while `agency config get` happily returned it. A setting an
operator cannot reach is a setting that does not exist; there is now a test that reaches it through
the same entry point the documentation names.

### `agency config set` can brick every hook on the box — hit live 2026-08-11

**A config edit took the machine down for roughly an hour of turns.** Every turn failed its Stop
hook with "could not verify or persist the turn-scoped evidence contract" — a message naming
neither a field nor a file.

**The mechanism, and it is a product defect rather than a slip.** `agency config set` does not patch
the targeted path; it rewrites the **whole document through the current renderer**. A CLI newer than
the last install therefore stamps fields the installed projection has never heard of onto sections
the operator never touched. Both config validators are strict allowlists, so the projection raises
`providers.0: contains unsupported fields` — and because hooks parse config on **every event**, one
unrelated setting stops the entire box.

Concretely: setting an unrelated `selector` flag wrote `token_parameter: ''` onto both providers,
from the field added in `4d4c5741` hours earlier. The installed projection `bb45af11309a` predates
it. Setting the flag back to `false` changed nothing, because the rejected thing is the **key**, not
the value.

**Why nothing caught it.** Every check ran against source, where the field is legitimate and all
four declarations agree. The install-drift line already knew the CLI and the projection disagreed —
it prints on every `agency status` — and no config write consulted it. The one authority that could
answer "will the installed hooks accept this?" was never asked.

**GUARDED.** `installed_config_compatibility` runs the candidate past the installed projection
before the atomic replace, using the projection's own validator rather than a reimplementation of
its allowlist — a copy here would be one more thing to drift. It **fails open**: an unfindable or
unrunnable projection proves nothing and must never block an operator from editing config. It also
checks **only the file the hooks actually read**; a first cut probed every candidate and made four
unrelated configuration tests fail against whatever happened to be installed, inventing exactly the
machine-sensitive failure this repo keeps tripping over. The same command that broke the box now
refuses with the projection digest, the rejected path, and the remedy.

**FIXED `da6d66b6` — the cause, not just the damage.** The rewrite does not come from the renderer,
as first written here; it comes from `configuration_service.py:256`, `document = validate(document)`.
Validation is a **normalization**: each section validator builds a fresh dict with every field
materialized to its default, and that document was what reached disk. The write is now expressed
against the operator's own file, carrying only the paths an operation actually changed; the
normalized projection still drives change detection and state, so nothing else moves. Narrowing
returns `None` when it cannot place a change faithfully — a provider secret addresses a list
element, which a mapping walk cannot reach — and the caller then persists the normalized document
rather than silently dropping the edit, with the guard above covering that remaining case.

Verified live: `agency config set selector.min_confidence 0.85` now writes that key alone and leaves
both providers byte-for-byte unchanged. The same command before this change stamped
`token_parameter` onto both.

### The kill switch is immediate — verified 2026-08-11

Questioned during the incident, so it is worth recording as fact rather than belief. `agency off
--global` takes effect on the **next hook event**, not the next session: each hook is a fresh
process that re-reads `control.json` through `--runtime-control` before anything else, and
`adapters/hooks.py:2787` short-circuits to a true pass-through when disabled — explicitly so that a
malformed Stop envelope cannot reach the fail-closed completion policy while Agency is off. Nothing
caches the control state across events.

The CLI's "start a fresh host session" line is about *comparing* on/off behaviour: specialist cards
already injected into a live transcript remain as context. That is text in a conversation, not
enforcement. A turn already in flight can still fail; the next one is clean.

### CI on `main` is red, and has been — observed 2026-08-11

Merging #266 surfaced it: **`main` has failed CI on at least its last five commits**, current tip
included, on one gate — `92.64%` dashboard **function** coverage against a `93%` threshold. All 109
dashboard UI tests pass; only the threshold fails, and the numbers are byte-identical on `main` and
on the branch, which touched no JavaScript at all. Everything downstream (`security`,
`artifact-parity`, `performance`, `windows-portability-contract`) then reports `skipped`, so a
single 0.36-point shortfall reads as five failed gates.

The shortfall is concentrated: `app.js` at **60.47%** functions, against 94–100% everywhere else.
**This likely resolves itself through the re-scope below rather than through new tests** — uncovered
functions in a surface we are about to cut are the cheapest possible thing to delete, and writing
tests for them first would be work aimed at code that should not survive. Worth confirming which
`app.js` functions are uncovered before choosing; if any are load-bearing for the vision, they need
tests instead.

### Raised 2026-08-11 — two items the vision restatement implies

- **Re-scope the dashboard and the CLI to the vision; anything not part of it goes.** Lucas's call,
  made after the AR-119 restatement: both surfaces accumulated against the retired product-trial
  contract, so a large part of each is now answering questions the vision does not ask. Treat this
  as deletion work with an explicit keep-list derived from the vision, not as a refactor — the
  default for a surface with no vision justification is removal, not migration. Do this against
  [[agency-runtime-founding-vision]] rather than against reachability or usage counts; the code is
  full of dead bodies and traffic is not evidence of purpose.
  **CLI half DONE `c0e42931`** — keep-list with the rule behind each survivor in
  `docs/analysis/2026-08-11-cli-vision-keep-list.md`. Removed `agency delegate` (the last live
  surface of Job B: it picked a backend, spawned it, and waited — rule 5 says Agency never decides
  to spawn; the 2026-08-09 deletion took Job B out of the hook path and nothing in that pass walked
  the CLI), `agency run` (arbitrary command execution, no vision anchor, on a binary installed into
  five hosts), and `agency codex exec` (a per-host branch with no parity twin). Renamed
  `agency eval delegation` → `agency eval host-parity`: that suite never spawned anything, it
  proves all five adapters record identical evidence for the same turn, which is rule 9 and rule 5
  done correctly — the name read as the opposite of what it does. Golden parser manifest 109 → 106
  paths. **`core/delegation/` was left alone on purpose**: `run_bounded_process` is the installer's
  and canary's subprocess primitive, `suggested_delegations` is on the live hook path, and
  `lifecycle_git.run_git` belongs to the update service — the package name is a historical
  accident, not a statement of contents. The Job B machinery still exported from its `__init__`
  (`delegate_with_lifecycle`, `dispatch_work_units`, `provision_worktrees`, `DependencyGraph`,
  ~3,400 lines) is the natural next package, deferred only because `server/dashboard.py` imports
  `delegation.lifecycle` and Codex is in that file now. **Dashboard half still open (Codex).**
  Three parity gaps the re-scope surfaced but did not fix: `agency serve` is an HTTP control plane
  no host consumes; `agency smoke` overlaps `doctor` + `host-canary` + `evidence wiring`; and one
  **retracted**: `agency hook` accepting only `codex`, `claude`, `zcode` is not a rule 9 gap —
  hermes and openclaw reach Agency through `adapters.hermes.bridge` and
  `adapters.openclaw.node_bridge`, invoked by their own plugin systems, so the verb differs
  because the harness does while coverage does not. That claim was inferred from a parser
  `choices` list without checking for the capability by another route. The genuine gap it
  uncovered — parity tested per host but never *across* hosts — is closed by
  `tests/test_host_boundary_parity.py`, which also records that **ZCode has no `SubagentStart`**
  and reaches rule 4 through `PreToolUse` matched on `Agent`.
- **Where the latency goes, measured 2026-08-11 — and why the store cannot finish the answer.**
  A routing decision makes **~2.4 provider calls** (433 receipts across 196 traces). Per-call
  duration *is* measured — `StructuredProviderResult.latency_ms` at the provider layer, carried
  onto the workforce attempt (`inference.py:433`, populated at `:809`) — and then **discarded**:
  `_record_workforce_model_receipts` (`selector/pipeline.py:1116`) writes each receipt without
  `started_at`/`ended_at`, which `record_model_receipt` accepts and defaults to the record instant.
  Result: **427 of 433 receipts have `started_at == ended_at`**, and the stored decision blob keeps
  only the single total. The cost is unattributable by omission at one call site, not by design.
  **Direct floor measurement instead** (trivial one-word prompt, same processes the CLI transport
  spawns): `claude -p` **7.6 s / 8.0 s**; `codex exec` **33.1 s / 25.8 s**. At ~2 calls per
  decision that is ~16 s on claude and ~52–66 s on codex *before* Agency's much larger prompts —
  so provider round-trips plausibly dominate the 88 s, and **the codex transport costs 3–4× the
  claude one for the same role**. Note the provider chain prefers `codex-subscription`.
  **DONE `<pending>` — `model_receipts.latency_ms` now carries the per-call duration**, declared
  through a single-source `MODEL_RECEIPT_MIGRATED_COLUMNS` tuple used by both the migration and the
  startup staleness predicate, so an existing database is actually migrated rather than stamped
  current and left to fail at query time. A duration, not a reconstructed span: writing
  `ended_at - latency` into a timestamp column would sit a fabricated absolute time next to real
  ones. `agency evidence latency` now reports the provider/Agency split and calls-per-decision,
  read back from the receipts rather than modelled. **A `0` receipt means unreported, never a free
  call** — such decisions are counted as unattributable instead of being blamed on Agency, which is
  why all 200 existing decisions on this box report `cannot be split`. **Attribution begins at the
  next `agency install`**: the hooks execute the published projection, so the recording change only
  takes effect once it is published.
- **BUILT `3708c96d` — `agency evidence latency`.** Reports min/p50/p95/max overall and per decision
  source, exits 1 when p95 exceeds `--budget-ms` (default the pinned 15000 ms cold control), and
  excludes zero-latency decisions rather than counting them as fast turns — both writers store `0`
  when no provider call was spent, so including them reports Agency as cheap in proportion to how
  often it did nothing. First reading: **200 decisions, p50 38.5 s, p95 140.7 s**; the live
  `computed` path alone is **p50 88.3 s, p95 195.9 s, max 225 s** against a 15 s budget. The
  original finding follows.
- **There is no operator surface for Agency's own latency, and the recorded numbers are the reason
  it needs one.** `routing_decisions.latency_ms` is the only stored timing column (318 rows, sole
  timing column in the entire schema). Measured on this box: today's 4 accepted routing decisions
  ran **min 26.8 s, p50 32.6 s, p95 43.3 s**; all-time `computed` averages **47.8 s** with a
  **225 s** maximum. The pinned control elsewhere in this document is a **15000 ms cold** budget,
  so live parent-turn routing is running roughly 2–3× over it and nothing surfaces that to an
  operator. `agency eval routing` runs latency gates and the benchmarks compute p95, but neither
  answers "what is Agency costing my turns right now". A read-only surface over the column already
  being written is a small piece of work and should precede any latency tuning.

### AR-180 exact-host capability preflight — 2026-08-12

The current PATH-resolved Codex runtime is `0.147.0`; Codex Desktop package
`26.803.10989.0` carries runtime `0.147.0-alpha.6.6`. Tagged Codex 0.147 source
has a conditional plaintext collaboration path identified by host response-item
marker `encrypted_function_args: []`. The documented `PreToolUse` payload omits
that marker, however, and the exact active Sol/TUI spawn omitted it too: its
1,036-character `message` was ciphertext and reached the child as encrypted
content. This corrects the broad statement that Codex 0.147 has no plaintext
path while preserving that checkpoint's verdict: candidate `7e1b3603` could not
authenticate or use it. Candidate `e8b60f64` repairs and adversarially verifies
the exact-0.147 TUI/exec source boundary, but authentic one-record TUI forks,
Desktop alpha, unobserved exec depth-two/deeper ancestry, and every Installed/
Live layer remain unproven. No Agency canary, install, or trust change occurred.
ADR-0159 now governs the version-pinned transcript authorization; it does not
replace the host-authored child artifact required for Rule-4 proof.

### AR-180 cross-file ancestry checkpoint — 2026-08-13

Candidate `45b21cdc` and ledger `01730614` add the v2 exact-CLI-`0.147.0`
attestation for authentic one-record TUI forks. It resolves each declared
parent/root UUID through a unique canonical UTC-day plus-or-minus-one lookup,
validates file offsets independently, seals the complete external prefixes,
proves exact adjacent causal records at both depth-two edges, and applies one
64 MiB aggregate external-ancestry limit. The current authorization call still
requires `encrypted_function_args: []`; only ancestor causal calls may use the
ordinary exact schema or that schema plus the exact empty marker.

The authentic census resolved 11/11 chains: one depth-one sparse, seven depth-
one inherited, one depth-two sparse, and two depth-two inherited. The largest
sample sealed 48,678,898 external bytes and resolved in 3.809 seconds. The parent
passed 365 focused tests, the 673-test fast spine with 6 skips, and a scoped
19/19 mutation run with a green baseline and `source_unchanged=true`. The
independent reviewer passed 200 tests, killed the same 19/19 mutations, and
reported no finding at any severity. This advances only Codex Rule-4
Implementation and Simulation. For candidate `45b21cdc`, the 134-test dashboard
suite, routing evaluation, Ruff, format, and documentation/schema gates passed.
Its decision-conformance evaluator exited zero in 883.1 seconds: the baseline
passed in 169,548 ms, all 131/131 mutations were killed, zero survived or were
invalid, and `source_unchanged=true`. Desktop alpha, exec depth-two/deeper,
Installed, and Live remain unproven; no install, trust, or canary action occurred.

### AR-180 Desktop-alpha checkpoint — 2026-08-13

Candidate `211563c7` and ledger `ee8db873` add the sealed v3 Desktop profile,
pinned only to runtime `0.147.0-alpha.6.6`; the exact CLI `0.147.0` profiles are
unchanged. Desktop requires one exact root, while depth-one/depth-two V2 child
ancestry must match one of 13 atomic observed tuples. Eight tested but unobserved
cross-products, disabled guardians, greater depth, mixed profiles, and schema drift fail open
unstaffed. Canonical owner files, both depth-two edges, exact adjacent direct
event/output records, copied history, file/profile/currentness seals, and the
64 MiB aggregate external bound remain mandatory. Ancestor calls use the exact
ordinary schema or that schema plus `encrypted_function_args: []`; the current
authorization call still requires the exact empty marker.

Focused provenance/hook verification passed 288/288, focused plus the anchor
passed 289/289, and the named fast spine passed 673 with 6 skips. The scoped
Desktop baseline passed and killed 20/20 mutations with zero survived or invalid
and `source_unchanged=true`; an independent run reproduced those results and
reported no finding at any severity. A content-safe probe resolved 52/52
authentic V2 Desktop chains (47 depth one, 5 depth two), with maximum external
ancestry 32,650,955 bytes and maximum resolver time 2.765 seconds. All 65
observed Desktop calls were encrypted and unmarked, so no rewrite or child was
proved. Codex Rule-4 Implementation and Simulation remain proven; State,
Installed, and Live remain unproven. For `211563c7`, dashboard UI passed 134/134,
routing passed every threshold, and Ruff lint/format passed. The expanded
decision-conformance evaluator remains pending; the 131/131 result above remains
`45b21cdc` history.

### Option A exact-main parent checkpoint — 2026-08-20

PR #299 merged the ZCode authoritative-parent-header repair to main as
`f203dc66` with no hosted Actions run. ZCode alone was reinstalled from that
exact merge and passed its deterministic 4/4 source smoke. The bundled ZCode
0.16.3 CLI then completed one no-tools parent control: session
`sess_d4ac6d99-a8e6-4f43-ab81-c19902f23d86`, host trace
`d3f6efd5-9e14-4e34-81c6-bb2fae78d9d9`, Agency trace
`498d64b3-8643-4c38-8c0f-922e3837cf8d`.

ZCode's own model-I/O records provider `zai`, requested `glm-5.2`, actual
response model `glm-5.3`, one request, and zero tool calls. Agency's separate
workforce receipt records `claude-subscription/sonnet`; the response carried
the exact Store-backed five-line header and Stop finalized it
`accept/completed` with no missing fields, activation, or delegation rows.
This closes the parent-header repair and the owner-scoped three-host Option A
rollout. It is not plural-card Rule-4 proof, a candidate advance, or a matrix
promotion. The sequenced plan for every remaining item in the 19 August owner
review is in `AR-119-vision-loop-status.md` under
"CHECKPOINT PLAN: finish the 19 August review scope."

### Claude exactly-two outcome collector checkpoint — 2026-08-20

The owner authorized two verified-delivery consumptions only inside one atomic
producer/verifier pairing transaction. The private Claude collector now requires
exactly two independently Store-verified host artifacts, shared pair identity,
distinct roles, one contractor card plus producer output, and one verifier-
artifact semantic decision. Pair capabilities cannot enter the ordinary single
consumer and disappear together after the bounded Store result. The 339-test
affected acceptance/delivery/promotion/lifecycle/dashboard surface passes with
Ruff and diff checks green. This is source and synthetic-artifact evidence only:
no install, provider draw, live outcome, candidate advance, or matrix cell moved.

### Claude accepted-outcome canary source checkpoint — 2026-08-20

The isolated Claude backend now has one explicit `--accepted-outcome` mode with
an exact confirmation phrase. It asks the host for exactly two serial children,
collects both artifacts before private-home cleanup, and rejects a child-judge
provider mismatch before the atomic Store outcome call. Its content-free report
joins the configured pin to both providers that actually answered, exact cards,
artifact receipts, the Store result, and promotion status; model and child text
never enter the report. The complete local harness passes 14/14 in 14.4 minutes
(796 production-spine, 695 matrix-evidence, 134 dashboard), the separate full
decision-conformance run kills 151/151 mutations, and 46/46 focused tests pass.
A read-only source CLI smoke reached the new gate but sandboxed inventory was
not host-readiness evidence. No install, live draw, acceptance, promotion,
candidate advance, or matrix cell moved.

### Claude accepted-outcome parent-preflight repair candidate — 2026-08-20

The exact merged-main canary prompt measured 2,316 characters and did not
satisfy the existing indivisible-work-unit detector. The local canary-only
candidate explicitly makes the producer/verifier sequence one indivisible
parent work unit and forbids decomposition; the resulting 2,367-character
prompt satisfies that same production detector. It changes no provider, model
profile, ordinary-turn behavior, Store contract, or global configuration.

The exact prompt surface passes 11/11 tests, the widened canary/collector/
activation/inference surface passes 102/102, and the local fast harness passes
12/12 with Ruff, 161 workflow contracts, 151 mutation snippets, and 134
dashboard tests green. This is source-level repair evidence only. No provider
was called, no accepted outcome or promotion was written, the candidate did
not advance, and no matrix cell moved.

### Claude parent-preflight repair merged and installed — 2026-08-20

PR #302 merged exact repair head `c798562f` to main as `a102a932`.
The non-draft PR was cleanly mergeable with no check rollup; skip instructions
on both head and merge produced no hosted run. The exact head passed 12/12 fast
gates before push and again in the pre-push hook.

Claude-only install `4c6d8a17-902e-4de6-8b8a-15de14276eca` came from a
clean detached checkout of that merge and staged bundle `b0b5073ca7cb…`.
Readiness on Claude Code 2.1.226 is true with zero unmet prerequisites, current
launcher artifacts, and explicit child pin `codex-subscription`. This is
merged/install/readiness evidence only; no provider call, outcome, attestation,
promotion, candidate advance, or matrix cell occurred at this checkpoint.

### Claude planner repair passes; recruiter still fails — 2026-08-20

Exact-main pair `6e0eff1149894c830127417a1411f06d` ran once. Claude exited
0 without timeout or truncation, while the wrapper failed closed at
`delivery_marker_absent` and wrote no outcome, attestation, or promotion.
Store session `7c19bc88…`, trace `055d329f…`, run `2dbc72dd…`, and
failure `88840ca1…` prove the changed boundary.

The Haiku planner now applied one valid structured unit, live-proving the
indivisible-parent repair. The configured Sonnet recruiter then failed
`staff_without_safe_team` for `unit-parseport-impl` after ranking four
implementation candidates; its funded repair returned no valid response. The
trace contains no routing decision, applied model receipt, specialist load,
delegation, child scope, captured assignment, worker run, delivery verification,
finalization, attestation, skill, or worker-outcome row. Collector ordering
proves exactly two in-window Claude artifacts existed, but the first lacked v6
delivery because preflight never staffed. No child judge answered.

This is the already documented intermittent Claude/Sonnet recruiter behavior,
not a new planner, child-pin, Agent-topology, or outcome-recorder defect. The
authorized draw is consumed without retry. No rule, candidate, or matrix cell
moved.

### Accepted-outcome parent-recruiter pin candidate — 2026-08-20

The owner chose a canary-only `claude -> codex-subscription` parent-recruiter
pin instead of spending another draw on the unchanged Sonnet route. The local
candidate introduces a distinct typed map,
`canary.accepted_outcome_parent_recruiter_provider_by_host`, and projects it
only into the Claude accepted-outcome subprocess. Workforce routing consumes
the projection only for the primary recruiter route; planner, critic, ordinary
turn, activation-canary, and child-judge paths remain unchanged. Resolution is
exact, CLI-only, and no-fallback, with requested parent recruiter and child
judge identities reported separately.

This checkpoint has no owner-config mutation, install, live inference, outcome,
promotion, rule credit, candidate advance, or matrix movement. Publication,
owner-config update, exact-main installation, and one bounded draw remain fresh
authorization boundaries.

The local proof set is green: 137 bounded configuration/canary tests passed
with 4 skips and the unrelated historical fast-default assertion deselected;
152 host-canary/workforce-route tests, 182 child/activation/hook
noninterference tests, and the 797-test warning-strict production spine passed
(20 spine skips). All 12 fast gates passed in 1.2 minutes and documentation
validation passed for 713 files. The slow 14-gate harness and every outward or
live boundary remain unrun.

### Parent pin merged; draw exposes the recruiter output contract — 2026-08-20

PR #303 merged exact head `dbfe2b0d` as main `eff66c67` with skip
instructions and no hosted run. The exact-main install and owner config applied
the canary-only Claude parent-recruiter pin. Pair
`39ff6dca0e5885d132cefadecc3e1fdb` then proved the requested route actually
reached `codex-subscription` / `gpt-5.6-terra` twice; this is not a provider-
routing ambiguity.

Both recruiter results were rejected `staff_without_safe_team` for
`unit-parseport-impl-verified`. The first retained projection ranks
`typescript-application-engineer`, `minimal-change-engineer`,
`backend-service-engineer`, and `solidity-smart-contract-engineer` with no
axis or top-ranked ineligibility. The repair ranks the first two and leaves
`capability` uncovered. The run ended preflight before routing, child judging,
delivery, outcome, attestation, or promotion, and it was not retried.

The no-cost evidence package is
[`AR-119-39ff6dca-recruiter-diagnostic-evidence.md`](AR-119-39ff6dca-recruiter-diagnostic-evidence.md).
It records why the raw recruiter JSON and byte-exact dynamic prompt cannot be
recovered, while the immutable parent prompt and exact source contract can be
inspected. The source defect is an underspecified classification boundary:
`required` was not stated as a mandatory selected member, and the repair call
received no prior classification/count/coverage facts despite referring to a
prior response.

The local repair changes no provider route. It defines the three classification
semantics in prose and the machine response contract, sends only bounded
deterministic safe-team facts on the one funded repair, excludes declared-
forbidden candidates from the diagnostic axis, and adds three content-free
counts to future durable failure receipts. Deterministic code still never
selects, adds, reorders, or invents a team. Provider-free verification is green:
97 focused/conformance tests, the 797-test production spine with 20 skips, and
695 deterministic matrix regressions; all 14 local gates pass in 13.9 minutes.
Commits `e7e4e285` / `1dd70983` are local. No matrix cell moved and no further
live draw is authorized or needed before publication and exact-main review.

### Still required before AR-119 can close

- Preserve the local repairs across AR-128 through AR-176 while completing their
  remaining tracker, installed-host, attended-canary, signing, and hosted
  evidence. AR-143's exact Windows roster-rollback path is positive
  native proof only after the AR-161 signed-artifact and attended-canary gates;
  it is not general persistent-control or cross-platform authority.
- Complete a benchmark-valid run of the implemented matched held-out selection
  benchmark against the pinned source-visible upstream Agency Agents baseline.
  Two complete corpora have now established all 19 Agency arms safe and passing
  together within the unchanged coverage and latency gates, with intervening
  complete-corpus variance recovered in bounded confirmations. The newest
  corpus returned to 17/19 on active-incident margin and missing CFO review;
  confirm both unchanged before any defect claim. Obtain one complete corpus
  with 19 valid comparable upstream arms, and retain every malformed, no-
  response, or timed-out arm as a benchmark-validity failure.
  Dangerous, forbidden, incompatible, disabled, and weak incidental matches
  remain explicit regressions, not aggregate-score noise.
- Complete the whole-roster multi-agent and conflict corpus, contractor
  duplicate/admission/promotion lifecycle, and CLI/dashboard operator flows.
- Prove cold, warm, cache-invalidation, and large native-fan-out latency bounds.
- Run paired Agency-on/off outcome trials with accepted activation evidence.
- Keep exhaustive Python coverage and compatibility manual-only and run them
  only when the owner explicitly asks. Perform the deferred hosted checks once
  at the end; do not restore those corpora to automatic PR/push execution.
- Create the final PR, merge it, reinstall the merged artifact, and run live
  canaries on Codex, Claude, Hermes, OpenClaw, and ZCode before closing issue
  #132.

### Next bounded work package

Keep Option A frozen. The owner chose the local canary-only
`claude -> codex-subscription` parent-recruiter pin. Finish its local gates and
recovery pair, then obtain fresh authority for publication, owner-config update,
exact-main installation, and one bounded falsification draw; no general-turn
route change or unapproved retry is authorized.
Formal R8 credit remains a separate owner decision because it advances the
candidate and re-anchors R2/R3/R7. Codex child work waits for an upstream readable
started-child surface; do not burn repeated canaries. After ZCode plural-card
closure, move development to the owner's OpenClaw box; Hermes and final five-host
Rule 9 remain later authorized packages.

### Context checkpoint constraints

- Continue on `codex/ar119-claude-outcome-live-evidence` from the current local
  recovery checkpoint; do not reset, discard, or silently rewrite the
  accumulated AR-119 work.
- Keep tracker issue #132 open and do not claim the north-star goal complete.
- Do not push or trigger hosted GitHub Actions during intermediate packages;
  the user requested one consolidated hosted verification near the end.
- After each bounded package, update this checkpoint, create local recovery and
  ledger commits, and apply the same-task clean-checkpoint protocol in
  `AGENTS.md`. Telemetry never blocks live work and never creates, forks,
  dispatches, or waits for another task.

## Acceptance

Current acceptance is the
[founding nine-rule vision](AR-119-founding-vision.md) evaluated cell by cell in
the [canonical rule/host evidence matrix](AR-119-rule-host-evidence-matrix.md).
That matrix is the only current completion projection. A rule is not complete
from implementation, simulation, registration, an Agency Store row, or model
prose; it needs the proof authority named in its matrix cell for the exact
candidate.

- [ ] Rules 1 through 8 are `proven` on **Codex, Claude Code, ZCode, Hermes,
      and OpenClaw**, with no negative or unproven cell; Rule 9 is proven by
      that complete five-host set. An unavailable host stays unproven. There is
      no host waiver or not-applicable path while it remains supported.
- [ ] Rule 1: the exact inference decision is the only specialist or contractor
      choice and is joined to the delivered card hashes. Deterministic code may
      recall, hard-filter, validate, budget, and correlate, but never select,
      rank, replace, erase, or invent the staffing result.
- [ ] Rule 4: each native host independently starts a child whose host-authored
      artifact contains multiple compatible card hashes before first speech.
      Claude has three prior-candidate artifacts but is exact-candidate
      unproven. Codex has reviewed conditional host support and exact CLI
      `0.147.0` plus Desktop `0.147.0-alpha.6.6` compatibility, but exec-depth-
      two/deeper compatibility and exact-candidate installed/live proof remain
      open; ZCode, Hermes, and OpenClaw remain unproven.
- [ ] Rule 8: Agency unavailability supplies no card and never suppresses the
      host's natural response on any host. Only a verifier's definite negative
      and the malformed-`Stop` forgery boundary deliberately withhold.
- [ ] Rule 6: host-backed producer and independent-verifier artifacts feed the
      accepted-outcome path, and three successes after the seven-day review
      window automatically promote the contractor without operator action.
- [ ] The fixed 15,000 ms cold staffing control passes without weakening
      inference, host spawn, evidence, Rule-8, or promotion authority.
- [ ] AR-125 produces a valid matched Agency-on/off corpus before any value or
      superiority claim; malformed and timed-out arms remain invalid.
- [ ] The merged exact candidate, documentation/tracker records, installed
      artifacts, and release evidence agree before tracker issue #132 closes.

## Historical acceptance record (superseded)

Everything below this heading is retained verbatim as chronological evidence
for the former deterministic-floor, planned-child, activation-receipt, host-
limitation, and product-trial contracts. It grants no current fallback, host
waiver, acceptance credit, or proof authority. Current status is exclusively in
the matrix linked above.

- [x] Rules 1, 2, 3, 5, 6, 7 hold, each with a landed commit.
- [x] Rule 4 on **claude** — child `ad68a49ad2297ebd2`, three cards, `legacy=false`, `correlated=true`, envelope in record 0 (2026-08-11). **Re-proven the same day on the refreshed adapter** (`cae7ca576462`, installed 18:46Z) through a fresh headless `claude -p` session with Agency enabled before session start: child `a9c6ab358c1e5ebc6`, parent `91e03ac9-c1ec-40f1-b8a8-eaf6dc853c65`, `legacy=false`, `correlated=true`, cards `python-cli-architecture-specialist, agency-model-explainer, software-architect`. Provably staffed count 1 → 2. **Confirmed a third time in an attended interactive session** (not headless): child `a41e5c325024bb208`, `legacy=false`, `correlated=true`, same three cards, count 2 → 3. It required **no re-trust** after the republish, unlike codex — the two hosts do not gate hook execution the same way, which is worth remembering before reading a codex trust state as a general fact.
- [x] Rule 8 — Agency never withholds a turn because Agency is unavailable; the verifier's definite negative and the malformed-`Stop` forgery guard are deliberate and stay.
- [x] Rule 8 is auditable, not asserted: `agency evidence rejections` partitions closed runs into withheld versus Agency-was-blind and exits non-zero when anything was withheld.
- [ ] Rule 4 on **codex**: **MEASURED 2026-08-11 — negative, and the cause is now confirmed in the host's own artifacts rather than suspected.** A valid bench finally ran: install current, hook trust granted, Agency on before session start, codex `active`, exactly one child. Parent `019ff1e8-e0fe-7fe0-b8ba-57de219228c6`, child `019ff1e9-defe-77c2-8bd1-9d503f1670b6`. The child is real and correlatable — record 0 is `session_meta` carrying `payload.source.subagent.thread_spawn.parent_thread_id` = the parent. Agency's hooks fired (`SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`×2, `Stop`) and the parent turn recruited `agency-steward` + `codebase-onboarding-engineer` via inference. But `agency-native-child-jit` appears **0 times** across both artifacts, and `agency evidence children --host codex` is unchanged at 0 staffed / 11 legacy.
  **AR-209 is confirmed, and sharpened.** Parent record 16 is `function_call name=spawn_agent namespace=collaboration` with exactly three arguments — `task_name` (`find_cli_install_drift`, plaintext), `fork_turns` (`all`, plaintext), and `message`, which is a **396-char Fernet token** (`gAAAAA…`). Agency is not blind to the launch: `PreToolUse` fired and the call is visible. The defect is narrower than "Agency may be unable to correlate the launch" — Agency **sees** the spawn but the only argument that could carry a specialist card is encrypted, so there is nothing to rewrite. Any fix must come from the host surface, not from Agency.
  Two secondary findings from the same run: `SubagentStart`/`SubagentStop` did **not** fire for this spawn despite being among the eight trusted events; and the parent reported `delegated: none - executed worker has no validated Agency specialist`, which is the honest downstream consequence.
  **Cross-surface re-check, 2026-08-11 — the caveat is now closed for two of three surfaces by census, not by sampling.** All 1181 rollouts under `~/.codex/sessions` were scanned for `spawn_agent`: **274 calls, 274 with an encrypted `message`, 0 plaintext**, spanning 8 CLI versions (`0.144.0-alpha.4` → `0.147.0`) and every surface with any spawn history — `Codex Desktop/vscode` (the GUI: 159 spawns across 5 versions), `Codex Desktop/exec` (1), `Codex Desktop/subagent` (37 nested), `codex_exec/exec` (76 across 3 versions), `codex_exec/subagent` (1). The argument shape varies (`message,task_name`; `fork_turns,message,task_name`; `fork_turns,message,reasoning_effort,task_name`) but **no variant has ever exposed a plaintext context field**. This is not version-specific, surface-specific, or recent.
  **Independent confirmation from the same census:** `agency-native-child-jit` appears in only 5 of 1181 rollouts, and **all 5 are this bench document's own text being read** — 3 are shell-read `custom_tool_call_output`, 2 are `{"subagent":{"other":"guardian"}}` reviewer sessions quoting the transcript. Agency has never delivered a JIT envelope into any codex session on this box, on any surface.
  **TUI gap CLOSED 2026-08-11 by direct measurement — all three surfaces now agree.** An attended interactive `codex-tui` session with hook trust freshly granted and Agency on before session start spawned exactly one child: parent `019ff24f-5ebd-7af0-a456-5b33a566b151`, child `019ff250-6243-7261-a7bd-366714f530ad`, linked by `thread_spawn.parent_thread_id`. The spawn is `spawn_agent` / `collaboration` with the same three arguments and a **504-char encrypted `message`**; `agency-native-child-jit` appears **0** times; `agency evidence children --host codex` unchanged at 0 staffed / 11 legacy. TUI, GUI and exec are now measured and identical. Nothing about rule 4 on codex is unmeasured any more.
  **One new detail worth carrying into the fix design:** the parent set `task_name` to `codebase_onboarding_engineer` — it named the child after the specialist it had loaded. The intent to staff was present and the parent knew the slug; only the delivery channel was closed. `task_name` is also proof the host *does* expose plaintext arguments, so the ask upstream is concrete rather than speculative: an owner-supplied plaintext context field alongside the encrypted one. `task_name` itself is not a candidate — it is model-authored, unvalidated, and carries no prompt hash.
- [ ] *(superseded context for the line above)* The 2026-08-11 first attempt stopped before spawning a child, correctly, but on a false reading; the bench is now unblocked. The prescribed `agency install --agent codex --verify-activation` form is verification-only — `cmd_install` dispatches it before any install work — and the real shape, `agency install --agent codex --no-dashboard`, additionally requires global and codex runtime **on** as preconditions. Run in that order the refresh committed: plugin `352838f1948f` → `e6a092ee419a`, and the codex target's launcher record now binds the required projection `7013411cf205`. **The `runtime:` drift line in `agency status` is not evidence about codex** — the installed-runtime pointer is a single global file written only by the generic install path, so it still reports `5b17b2253b5d` and still names `--agent claude` after a fully successful codex install; read `~/.agency-runtime/marketplaces/codex/.agency-runtime-launcher.json` instead. What remains is hook trust on the new bundle, `--verify-activation`, and one child in a fresh session. Baseline re-measured after the install is unchanged at 0 staffed / 11 legacy. AR-209 remains the next suspect only if that valid bench reaches child launch and the encrypted `PreToolUse` payload blocks correlation.
- [x] **FIXED `8b92a5b9`** — the installed-runtime pointer is now per host (`current-<host>.json`), and the prepared Codex refresh records what it publishes. A named host never writes the shared file, so one host's install cannot answer for another's; the legacy shared pointer is still read but only for the host it actually named, so existing installations lose nothing. `runtime_staleness(host=…)` resolves that host's own record, `cli_install_drift_reports()` returns one report per stale host, and `agency status` prints a host-tagged line each (`status --json` gains `runtime_drift_hosts`, keeps `runtime_drift`). The source digest is computed lazily so a foreign recorded root is still decided by root alone and never digest-compared. Verified live: codex current and silent, claude correctly reported behind and correctly named. 6 new tests including the exact defect; `test_host_hooks.py` re-measured against a clean HEAD worktree at 9 failed / 82 passed before and after, identical names. The original diagnosis follows.
  Per-host installed-runtime pointer. `record_installed_runtime` is called only from `installer_orchestration.py:555`; `prepared_codex_install.py` publishes a runtime but never records one, and the pointer is single-valued, so a codex install cannot be represented without silencing genuine claude staleness. Measured 2026-08-11 — this is a bounded package, not a one-line fix.
- [x] **FIXED `2865493d`** — Codex hook-trust inspection can now launch its worker. It builds the argv from the published private projection (`persistent_python_executable()` + the projection's `_bootstrap.py`) instead of `sys.executable` + the checkout's bootstrap, so `freeze_process_argv` accepts it. The guard is unchanged — this satisfies it rather than relaxing it — and the inspector still publishes nothing: an absent projection reports the new distinct `worker_projection_unavailable` instead of `inspection_failed`, so an unlaunchable inspector can never again be misread as untrusted hooks. `isolated_python_argv` gained an opt-in `bootstrap_path` override to keep the argv shape defined once. Verified live on this box: `observed 0 → 8`, `missing 8 → 0`, error cleared; the reading became `modified` on all 8 (republishing the adapter changes the hook commands, so a prior trust grant no longer matches — a true finding, not an error). 3 tests pin it; 310 tests green across the touched suites. The original diagnosis follows.
  Codex hook-trust inspection cannot run from a checkout, so `--verify-activation` can never pass there. `inspect_codex_hook_trust` builds its worker argv from `sys.executable` and `agency_bootstrap_path()` and then freezes it; `_assert_executable_artifact_trusted` refuses both as cross-account writable, and the library flattens the `PermissionError` into `error=inspection_failed` with `observed=0 missing=8`. Reproduced directly 2026-08-11. **`inspection_failed` is not evidence about trust in either direction**, and the in-code comment at `codex_hook_trust.py:713-720` claiming `forbidden_roots=()` already fixed this is wrong — that argument only governs the repository-root check, not the ACL assertion. The launcher path picks a trusted interpreter via `persistent_python_executable()` (`sys._base_executable`); the inspector does not. Substituting it clears artifact 0 (verified) but not artifact 1, so the real fix runs the worker from the published `~/.agency-runtime/launchers/runtime-sha256-<digest>/` projection instead of the live checkout. Do not weaken the guard. This gates the activation *attestation*, not the rule-4 measurement.
- [ ] Rule 4 on **zcode**, or an explicit recorded finding that the host cannot support it (it emits no `SubagentStart`/`SubagentStop`).
- [ ] Rule 4 on **openclaw** and **hermes**, on a machine where they are installed.
- [ ] Rule 9: the rule-8 split behaves identically on all five hosts. Proven in code for openclaw; unverified live, because the Node-side consumer is external to this repo and the host is not installed here.
- [ ] `agency evidence children` reports zero uncorrelated staffed children on every host that has any.

---

*Retired product-trial gates, provenance only:*

- [ ] AR-120 through AR-125 are complete and tracker-evidenced.
- [ ] Every new intent is planned or explicitly classified as a continuation, and every Agency-assigned native child consumes the exact specialist recipe and one-use activation receipt.
- [ ] No generic native child is counted as Agency participation; recommendation without activation is rejected as incomplete evidence.
- [ ] Broad intent, ambiguity, adversarial, disabled-worker, conflict, and multi-agent corpora exercise the entire audited workforce rather than a single security-review case.
- [ ] Every employee and contractor has validated capability IDs in the same versioned contract and recruiter index, and bounded recruiter output cannot escape its supplied candidate cards.
- [ ] Without a configured provider, deterministic typed recall either forms a safe compatible team stamped `inference_mode="deterministic"` and `decision_source="deterministic"`, or abstains with no specialist; it never becomes the decider when inference is configured.
- [ ] Parent routing is bounded, cached for continuations, reused by children, and passes explicit cold, warm, and fan-out latency budgets.
- [ ] Plan, candidate, recruiter, and parent-unit caches use complete versioned identities and invalidate on request, host, roster, contract, policy, provider, model, taxonomy, or schema changes as applicable.
- [ ] A genuine roster gap passes automated quarantine and uses a least-privileged probationary contractor in the causing turn; malicious or incoherent candidates are rejected without blocking safe host fallback.
- [ ] Paired Agency-on/off trials prove specialist participation and a better independently graded outcome for the same host and model.
- [ ] A pinned held-out comparison materially beats the source-visible upstream Agency Agents routing baseline without any forbidden or incompatible selection regression.
- [ ] Every completion gate in tracker issue #132 has direct current evidence.
- [ ] The final hosted matrix, installed artifacts, and host contracts pass for all five supported hosts (codex, claude, zcode, hermes, openclaw).
- [ ] **codex**: One fresh exact-build product trial passes with zero corrections.
- [ ] **zcode**: One fresh exact-build product trial passes with zero corrections.
- [ ] **claude**: One fresh exact-build product trial passes with zero corrections.
- [ ] **hermes**: One fresh exact-build product trial passes with zero corrections.
- [ ] **openclaw**: One fresh exact-build product trial passes with zero corrections.
- [ ] The merged and reinstalled artifact is verified before this item closes.
