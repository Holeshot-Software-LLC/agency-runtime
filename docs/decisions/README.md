---
title: Decision registry
status: active
category: decisions
created: 2026-07-10
updated: 2026-08-24
tags: [architecture, adr, governance]
related:
  - docs/roadmap/README.md
  - docs/RELEASE_CHECKLIST.md
supersedes: []
superseded_by: null
---

# Decision registry

This is the single canonical registry for durable architectural, product, and operational decisions in Agency Runtime. All records share one sequence. A decision is not renumbered when its scope or weight changes.

Status meanings:

- **Proposed**: under active consideration.
- **Accepted**: governs the current system.
- **Superseded**: replaced by a newer decision; follow the recorded link.
- **Deprecated**: still present but discouraged and scheduled for removal.
- **Rejected**: considered and deliberately not adopted.

## Superseding chains

- ADR-0007 Enforce a Six-Line Response Evidence Header → ADR-0045 Use Turn-Scoped Specialist Activation with Immutable Session History
- ADR-0002 Resolve Models from Post-Request Logs → ADR-0003 Treat Response Telemetry as Model Truth
- ADR-0004 Cut Over Through a Host-Specific Compatibility Shim → ADR-0005 Keep a Portable Core with Thin Host Adapters
- ADR-0009 Generate One Python Hook Scaffold for Every Host → ADR-0024 Package Each Host Integration in Its Native Format
- ADR-0020 Keep a Partial Companion Policy in Code → ADR-0021 Load a Full Companion Policy with Explicit Precedence
- ADR-0022 Omit Preflight Context for Trivial Messages → ADR-0023 Load Default Companions Even for Trivial Messages
- ADR-0016 Centralize Finalization and Correlate Evidence by Session → ADR-0045 Use Turn-Scoped Specialist Activation with Immutable Session History
- ADR-0023 Load Default Companions Even for Trivial Messages → ADR-0045 Use Turn-Scoped Specialist Activation with Immutable Session History
- ADR-0043 Prime Bounded Stdin Before Resuming Windows Children → ADR-0044 Preclose Bounded Windows Child Stdin and Own One Suspension → ADR-0073 Own Subprocess Trees Atomically Across Windows and Linux
- ADR-0008 Use Ordered Provider Fallback Ending in Deterministic Scoring → ADR-0067 Require Configured Inference for Every Specialist-Selection Decision
- ADR-0054 Use Unit-Aware Specialist Assignment and Event-Driven DAG Scheduling → ADR-0068 Select Compatible Specialist Closures per Work Unit
- ADR-0062 Isolate Directive Specialists and Route Each Work Unit Before Hydration → ADR-0069 Enforce Specialist Conflicts Before Prompt Composition
- ADR-0063 Import External Rosters Through Declared Manifests into Quarantine → ADR-0066 Package the Audited Upstream Roster and Synchronize Quarantined Deltas
- ADR-0080 Plan before recruiting from the whole workforce → ADR-0083 Use capability-indexed recall and bounded inference
- ADR-0058 Broker restricted Windows host controls through the authenticated dashboard → ADR-0090 Model-facing control paths are read-only
- ADR-0059 Broker restricted Windows agent controls through narrow dashboard operations → ADR-0090 Model-facing control paths are read-only
- ADR-0061 Validate brokered control transition receipts against deterministic CAS semantics → ADR-0090 Model-facing control paths are read-only
- ADR-0090 Model-facing control paths are read-only → ADR-0096 Require genuine operator presence for persistent controls → ADR-0110 Remove Agency-owned Windows Hello and use harness-native trust → ADR-0111 Install the applicable suite by default → ADR-0117 Unify owner CLI and dashboard control authority
- ADR-0087 Inference decides from a relevance shortlist → ADR-0088 Deterministic typed-recall is the offline floor → ADR-0118 Require inference-owned specialist staffing
- ADR-0030 Gate routing changes with versioned quantitative evaluation → ADR-0121 Gate deterministic recall without selection authority
- ADR-0077 Prove Codex hook activation behaviorally without bypassing trust → ADR-0119 Separate native trust modes from activation proof → ADR-0173 Complete production-container installation with managed activation
- ADR-0071 Bound native delegation correction to one evidence-checked pass → ADR-0120 Construct evidence headers before first publication
- ADR-0065 Keep a compact resident manager kernel at the parent boundary → ADR-0122 Use one Agency-native resident steward
- ADR-0127 Bind opaque Codex children through exact plan labels → ADR-0128 Persist exact Codex plan authority and serialize opaque launches
- ADR-0124 Grade product trials against the inferred unit graph → ADR-0133 Treat product specialist loads as turn-scoped
- ADR-0165 Keep LiteLLM inference profiles model-agnostic → ADR-0166 Delegate exact schema translation to LiteLLM

## Architecture and integrations

| ID | Decision | Status |
|---|---|---|
| [ADR-0004](0004-host-specific-compatibility-shim.md) | Cut over through a host-specific compatibility shim | Superseded |
| [ADR-0005](0005-portable-core-thin-host-adapters.md) | Keep a portable core with thin host adapters | Accepted |
| [ADR-0009](0009-uniform-generated-python-hooks.md) | Generate one Python hook scaffold for every host | Superseded |
| [ADR-0010](0010-one-command-install-and-reversible-toggle.md) | Provide one-command install and a reversible host toggle | Accepted |
| [ADR-0024](0024-native-host-packages-and-minimal-bridges.md) | Package each host integration in its native format | Accepted |
| [ADR-0028](0028-host-support-maturity-and-reversible-install.md) | Separate host contract coverage from live support maturity | Accepted |
| [ADR-0049](0049-openclaw-final-only-full-payload-delivery.md) | Require final-only full-payload delivery on OpenClaw | Accepted |
| [ADR-0050](0050-isolate-installed-python-module-resolution.md) | Isolate installed Python module resolution from host workspaces | Accepted |
| [ADR-0108](0108-retire-only-owned-host-integrations.md) | Retire only ownership-proven host integrations | Accepted |
| [ADR-0155](0155-defer-agent-plugins-conformance-to-client-adoption.md) | Defer Agent Plugins conformance to client adoption | Accepted |
| [ADR-0169](0169-deliver-openclaw-native-errors-through-exact-terminal-evidence.md) | Deliver OpenClaw native errors through exact terminal evidence | Accepted |
| [ADR-0170](0170-authorize-finalized-openclaw-child-announcements.md) | Authorize finalized OpenClaw child announcements | Accepted |

## Routing, policy, and providers

| ID | Decision | Status |
|---|---|---|
| [ADR-0001](0001-layered-specialist-routing.md) | Use a layered specialist-routing pipeline | Accepted |
| [ADR-0006](0006-config-first-redacted-configuration.md) | Make configuration the primary source of runtime truth | Accepted |
| [ADR-0008](0008-ordered-provider-fallback.md) | Use ordered provider fallback ending in deterministic scoring | Superseded |
| [ADR-0020](0020-partial-companion-policy-in-code.md) | Keep a partial companion policy in code | Superseded |
| [ADR-0021](0021-full-companion-policy-with-precedence.md) | Load a full companion policy with explicit precedence | Accepted |
| [ADR-0022](0022-omit-preflight-for-trivial-messages.md) | Omit preflight context for trivial messages | Superseded |
| [ADR-0023](0023-default-companions-for-trivial-messages.md) | Load default companions even for trivial messages | Superseded |
| [ADR-0030](0030-versioned-quantitative-evaluation-gates.md) | Gate routing changes with versioned quantitative evaluation | Superseded |
| [ADR-0033](0033-explicit-companion-route-availability.md) | Classify every companion route against explicit availability | Accepted |
| [ADR-0035](0035-authoritative-bounded-provider-chain.md) | Use an authoritative bounded provider chain with allowlisted CLI transports | Accepted |
| [ADR-0054](0054-unit-aware-assignment-and-event-driven-dag.md) | Use unit-aware specialist assignment and event-driven DAG scheduling | Superseded |
| [ADR-0062](0062-isolate-directives-and-route-units-first.md) | Isolate directive specialists and route each work unit before hydration | Superseded |
| [ADR-0064](0064-classify-turn-intent-from-durable-state.md) | Classify turn intent from durable state before selecting expertise | Accepted |
| [ADR-0067](0067-require-configured-inference-for-selection.md) | Require configured inference for every specialist-selection decision | Accepted |
| [ADR-0068](0068-select-compatible-specialist-closures-per-unit.md) | Select compatible specialist closures per work unit | Accepted |
| [ADR-0069](0069-enforce-conflicts-before-prompt-composition.md) | Enforce specialist conflicts before prompt composition | Accepted |
| [ADR-0070](0070-run-child-specific-agency-activation.md) | Run child-specific Agency activation through native host lifecycles | Accepted |
| [ADR-0071](0071-bound-native-delegation-correction.md) | Bound native delegation correction to one evidence-checked pass | Superseded |
| [ADR-0072](0072-compare-task-outcomes-with-paired-trials.md) | Compare task outcomes with evidence-labelled paired trials | Accepted |
| [ADR-0078](0078-present-human-routing-evidence-and-abstain-on-noise.md) | Present human routing evidence and abstain on weak heuristic noise | Accepted |
| [ADR-0079](0079-route-native-children-once-and-bound-unplanned-reroutes.md) | Route native children once and bound unplanned reroutes | Accepted |
| [ADR-0080](0080-plan-before-recruiting-from-the-whole-workforce.md) | Plan before recruiting from the whole workforce | Superseded |
| [ADR-0083](0083-use-capability-indexed-recall-and-bounded-inference.md) | Use capability-indexed recall and bounded inference | Accepted |
| [ADR-0094](0094-durable-native-child-correlation.md) | Correlate native children durably and fail Agency-planned work closed | Accepted |
| [ADR-0112](0112-stage-preflight-workforce-evidence-until-ready.md) | Stage preflight workforce evidence until ready | Accepted |
| [ADR-0114](0114-fund-one-default-workforce-semantic-repair.md) | Fund one default workforce semantic repair | Superseded |
| [ADR-0115](0115-aggregate-bounded-recruiter-repair-failures.md) | Aggregate bounded recruiter repair failures | Accepted |
| [ADR-0118](0118-require-inference-owned-staffing.md) | Require inference-owned specialist staffing | Accepted |
| [ADR-0121](0121-gate-deterministic-recall-without-selection-authority.md) | Gate deterministic recall without selection authority | Accepted |
| [ADR-0129](0129-repair-verifier-rejected-recruiter-proposals-once.md) | Repair verifier-rejected recruiter proposals once | Accepted |
| [ADR-0130](0130-repair-critic-rejected-contractor-proposals-once.md) | Repair critic-rejected contractor proposals once | Accepted |
| [ADR-0131](0131-bind-verifier-evidence-into-contractor-critiques.md) | Bind verifier evidence into contractor critiques | Accepted |
| [ADR-0132](0132-fund-one-repair-per-workforce-inference-stage.md) | Fund one repair per workforce inference stage | Accepted |
| [ADR-0122](0122-use-one-agency-native-resident-steward.md) | Use one Agency-native resident steward | Accepted |
| [ADR-0123](0123-use-general-preflight-ceiling-for-persistent-parents.md) | Use the general preflight ceiling for persistent native parents | Accepted |
| [ADR-0161](0161-pin-accepted-outcome-parent-recruiter-separately.md) | Pin the accepted-outcome parent recruiter separately | Accepted |
| [ADR-0163](0163-resolve-contextual-turns-from-transcript-free-subjects.md) | Resolve contextual turns from transcript-free same-session subjects | Accepted |
| [ADR-0164](0164-use-dense-embeddings-only-for-workforce-recall.md) | Use learned embeddings only for additive workforce recall | Accepted |
| [ADR-0171](0171-separate-native-and-structured-reranker-transports.md) | Separate native and structured reranker transports | Accepted |

## Evidence and observability

| ID | Decision | Status |
|---|---|---|
| [ADR-0002](0002-model-attribution-from-post-request-logs.md) | Resolve models from post-request logs | Superseded |
| [ADR-0003](0003-response-telemetry-is-model-truth.md) | Treat response telemetry as model truth | Accepted |
| [ADR-0007](0007-six-line-evidence-header.md) | Enforce a six-line response evidence header | Superseded |
| [ADR-0011](0011-explicit-delegation-evidence-lifecycle.md) | Model delegation as an explicit evidence lifecycle | Accepted |
| [ADR-0015](0015-versioned-selection-explain-receipts.md) | Publish versioned selection-explain receipts | Accepted |
| [ADR-0016](0016-central-finalization-and-session-correlation.md) | Centralize finalization and correlate evidence by session | Superseded |
| [ADR-0027](0027-authoritative-runtime-evidence-traces.md) | Derive runtime claims from authoritative correlated evidence | Accepted |
| [ADR-0045](0045-turn-scoped-specialist-activation.md) | Use turn-scoped specialist activation with immutable session history | Accepted |
| [ADR-0047](0047-reconcile-litellm-model-and-router-evidence.md) | Reconcile LiteLLM actual-model and router evidence separately | Accepted |
| [ADR-0065](0065-keep-compact-resident-manager-kernel.md) | Keep a compact resident manager kernel at the parent boundary | Superseded |
| [ADR-0093](0093-atomic-finalization-evidence-batches.md) | Commit one finalization evidence batch atomically | Accepted |
| [ADR-0120](0120-construct-first-pass-evidence-headers.md) | Construct evidence headers before first publication | Accepted |
| [ADR-0156](0156-host-artifacts-prove-native-child-delivery.md) | Use host-authored artifacts as native-child delivery proof | Accepted |
| [ADR-0158](0158-collect-child-canary-proof-inside-disposable-host-profiles.md) | Collect child-canary proof inside disposable host profiles | Accepted |
| [ADR-0159](0159-authenticate-codex-plaintext-spawns-from-host-transcripts.md) | Authenticate Codex plaintext spawns from host transcripts | Accepted |
| [ADR-0160](0160-pin-child-judge-providers-per-canary-harness.md) | Pin child-judge providers per canary harness | Accepted |
| [ADR-0167](0167-authorize-openclaw-native-skill-reads-from-inventory.md) | Authorize OpenClaw native skill reads from inventory | Accepted |
| [ADR-0168](0168-refresh-openclaw-headers-through-awaited-tool-results.md) | Refresh OpenClaw headers through awaited tool results | Accepted |
| [ADR-0174](0174-admit-local-ollama-canary-child-judges.md) | Admit local Ollama canary child judges | Accepted |

## State and roster governance

| ID | Decision | Status |
|---|---|---|
| [ADR-0012](0012-canonical-sqlite-audit-store.md) | Use SQLite as the canonical audit store with explicit retention | Accepted |
| [ADR-0013](0013-approval-gated-roster-activation.md) | Gate roster activation through quarantine and approval | Accepted |
| [ADR-0046](0046-config-backed-agent-activation-policy.md) | Separate reversible agent availability from governed roster state | Accepted |
| [ADR-0048](0048-preserve-legacy-tombstones-without-inventing-session-identity.md) | Preserve legacy tombstones without inventing session identity | Accepted |
| [ADR-0063](0063-import-external-rosters-through-declared-manifests.md) | Import external rosters through declared manifests into quarantine | Superseded |
| [ADR-0066](0066-package-audited-roster-and-sync-quarantined-deltas.md) | Package the audited upstream roster and synchronize quarantined deltas | Accepted |
| [ADR-0081](0081-compile-contractors-from-governed-structured-contracts.md) | Compile contractors from governed structured contracts | Accepted |
| [ADR-0134](0134-bind-contractor-risk-to-validated-authority.md) | Bind contractor risk to validated authority | Accepted |
| [ADR-0157](0157-automatically-promote-host-verified-contractors.md) | Automatically promote contractors from host-evidenced, independently verified outcomes | Accepted |
| [ADR-0162](0162-compile-structured-contractor-execution-guidance.md) | Compile structured contractor execution guidance | Accepted |

## Operations and engineering

| ID | Decision | Status |
|---|---|---|
| [ADR-0014](0014-generated-analysis-indexes-stay-local.md) | Keep generated analysis indexes out of version control | Accepted |
| [ADR-0017](0017-sanitized-server-error-boundary.md) | Sanitize errors at the server boundary | Accepted |
| [ADR-0018](0018-signature-aware-delegation-compatibility.md) | Adapt delegate signatures without masking execution errors | Accepted |
| [ADR-0019](0019-bounded-machine-readable-cli-delegation.md) | Make CLI delegation bounded and machine-readable | Accepted |
| [ADR-0026](0026-explicit-test-home-boundaries.md) | Require explicit home boundaries for generated-plugin tests | Accepted |
| [ADR-0029](0029-secure-local-dashboard-and-bounded-observability.md) | Keep the operations dashboard local and observability bounded | Accepted |
| [ADR-0031](0031-optional-user-dashboard-service-and-shared-configuration.md) | Use an optional user-scoped dashboard service with one typed configuration boundary | Accepted |
| [ADR-0172](0172-compose-first-run-setup-from-guarded-owner-operations.md) | Compose first-run setup from guarded owner operations | Accepted |
| [ADR-0173](0173-complete-production-container-installation-with-managed-activation.md) | Complete production-container installation with managed activation | Accepted |
| [ADR-0032](0032-adaptive-authenticated-dashboard-polling.md) | Use adaptive authenticated polling and source-owned signal visualizations | Accepted |
| [ADR-0034](0034-persistent-soft-host-control.md) | Separate immediate host control from native plugin lifecycle | Accepted |
| [ADR-0036](0036-capability-bound-host-canary-attestations.md) | Bind live host canary attestations to capability and installation identity | Accepted |
| [ADR-0037](0037-layered-pinned-supply-chain-gates.md) | Use layered pinned supply-chain gates | Accepted |
| [ADR-0038](0038-refuse-executable-git-configuration-during-delegation.md) | Refuse executable Git configuration during delegated mutations | Accepted |
| [ADR-0039](0039-fail-before-dacl-mutation-under-restricted-windows-tokens.md) | Fail before DACL mutation under restricted Windows tokens | Accepted |
| [ADR-0040](0040-preserve-environment-owned-python-launchers.md) | Preserve environment-owned Python launchers | Accepted |
| [ADR-0041](0041-bounded-asynchronous-overload-responses.md) | Use bounded asynchronous overload responses | Accepted |
| [ADR-0042](0042-local-only-bounded-work-file-inference.md) | Keep automatic work-file inference local and bounded | Accepted |
| [ADR-0043](0043-prime-stdin-before-windows-child-resume.md) | Prime bounded stdin before resuming Windows children | Superseded |
| [ADR-0044](0044-preclose-bounded-windows-child-stdin.md) | Preclose bounded Windows child stdin and own one suspension | Superseded |
| [ADR-0051](0051-bind-dashboard-runtime-publication-to-validated-filesystem-identities.md) | Bind dashboard runtime publication to validated filesystem identities | Accepted |
| [ADR-0052](0052-require-trusted-parents-for-sqlite-store-paths.md) | Require trusted parents for SQLite Store paths | Accepted |
| [ADR-0053](0053-durable-fail-enabled-master-control.md) | Use a durable fail-enabled master control before every host boundary | Accepted |
| [ADR-0055](0055-freeze-executable-identity-before-launch.md) | Freeze every launch-critical executable identity before process creation | Accepted |
| [ADR-0056](0056-capability-bound-restricted-windows-scratch.md) | Use capability-bound ephemeral scratch for restricted Windows hosts | Accepted |
| [ADR-0057](0057-generation-checked-host-control-mutations.md) | Require generation-checked atomic host-control mutations | Accepted |
| [ADR-0058](0058-broker-restricted-windows-host-controls.md) | Broker restricted Windows host controls through the authenticated dashboard | Superseded |
| [ADR-0059](0059-broker-restricted-windows-agent-controls.md) | Broker restricted Windows agent controls through narrow dashboard operations | Superseded |
| [ADR-0060](0060-restricted-windows-cli-read-and-fail-safe.md) | Broker restricted CLI reads narrowly and fail unsafe operations before execution | Accepted |
| [ADR-0061](0061-validate-brokered-control-transition-receipts.md) | Validate brokered control transition receipts against deterministic CAS semantics | Superseded |
| [ADR-0073](0073-own-subprocess-trees-atomically.md) | Own subprocess trees atomically across Windows and Linux | Accepted |
| [ADR-0074](0074-build-byte-deterministic-release-artifacts.md) | Build byte-deterministic release artifacts from canonical Git blobs | Accepted |
| [ADR-0075](0075-preserve-config-trust-under-wsl-systemd.md) | Preserve configuration trust while adapting systemd hardening on WSL | Accepted |
| [ADR-0076](0076-bind-isolated-canaries-to-explicit-agency-modes.md) | Bind isolated canaries to explicit Agency modes | Accepted |
| [ADR-0077](0077-prove-codex-activation-behaviorally.md) | Prove Codex hook activation behaviorally without bypassing trust | Superseded |
| [ADR-0082](0082-schedule-assurance-by-artifact-lifecycle.md) | Schedule assurance by artifact lifecycle | Accepted |
| [ADR-0090](0090-model-facing-control-paths-are-read-only.md) | Model-facing control paths are read-only | Superseded |
| [ADR-0091](0091-least-privilege-subprocess-environments.md) | Build every subprocess environment from least privilege | Accepted |
| [ADR-0092](0092-do-not-cache-positive-filesystem-trust.md) | Do not cache positive filesystem trust without complete authority identity | Accepted |
| [ADR-0095](0095-complete-paginated-dashboard-collections.md) | Dashboard collection views expose complete paginated truth | Accepted |
| [ADR-0096](0096-require-operator-presence-for-persistent-controls.md) | Require genuine operator presence for persistent controls | Superseded |
| [ADR-0097](0097-gate-expensive-ci-fanout-behind-quality-contracts.md) | Gate expensive CI fanout behind same-revision quality contracts | Accepted |
| [ADR-0098](0098-pair-portable-and-win-amd64-wheels.md) | Pair portable and win_amd64 wheels for native delivery | Accepted |
| [ADR-0099](0099-separate-reproducible-unsigned-builds-from-signed-delivery.md) | Separate reproducible unsigned builds from signed delivery | Accepted |
| [ADR-0100](0100-short-circuit-trusted-docs-only-pull-requests.md) | Short-circuit trusted documentation-only pull requests | Accepted |
| [ADR-0101](0101-run-exhaustive-python-verification-on-demand.md) | Run exhaustive Python verification on demand | Superseded |
| [ADR-0102](0102-defer-one-shot-application-evaluation.md) | Defer complete-application evaluation without weakening live release evidence | Accepted |
| [ADR-0103](0103-bind-named-regulated-assurance-to-typed-staffing.md) | Bind named regulated assurance to typed staffing requirements | Accepted |
| [ADR-0104](0104-refresh-existing-codex-through-an-exact-attended-transaction.md) | Refresh existing Codex through an exact attended transaction | Accepted |
| [ADR-0105](0105-bound-delivery-to-live-demo-checkpoints.md) | Bound delivery to live demo checkpoints | Accepted |
| [ADR-0106](0106-isolate-native-host-lifecycle-working-directories.md) | Isolate native host lifecycle working directories | Accepted |
| [ADR-0107](0107-resolve-updates-immutably-and-keep-application-attended.md) | Resolve updates immutably and keep application attended | Accepted |
| [ADR-0109](0109-prepare-dashboard-service-repair-before-operator-presence.md) | Prepare dashboard-service repair before operator presence | Superseded |
| [ADR-0110](0110-remove-agency-owned-windows-hello.md) | Remove Agency-owned Windows Hello and use harness-native trust | Superseded |
| [ADR-0111](0111-install-the-applicable-suite-by-default.md) | Install the applicable suite by default | Superseded |
| [ADR-0113](0113-prove-decision-conformance-with-isolated-mutations.md) | Prove decision conformance with isolated curated mutations | Accepted |
| [ADR-0116](0116-bind-product-trials-to-exact-workspace-proof.md) | Bind product trials to exact isolated workspace proof | Accepted |
| [ADR-0117](0117-unify-owner-control-authority.md) | Unify owner CLI and dashboard control authority | Accepted |
| [ADR-0119](0119-separate-native-trust-modes-from-activation-proof.md) | Separate native trust modes from activation proof | Superseded |
| [ADR-0124](0124-grade-product-trials-against-the-inferred-unit-graph.md) | Grade product trials against the inferred unit graph | Superseded |
| [ADR-0125](0125-admit-only-exact-content-free-codex-host-notices.md) | Admit only exact content-free Codex host notices | Accepted |
| [ADR-0126](0126-authorize-exact-product-delegation-at-the-codex-developer-boundary.md) | Authorize exact product delegation at the Codex developer boundary | Superseded |
| [ADR-0127](0127-bind-opaque-codex-children-through-exact-plan-labels.md) | Bind opaque Codex children through exact plan labels | Superseded |
| [ADR-0128](0128-persist-exact-codex-plan-authority-and-serialize-launches.md) | Persist exact Codex plan authority and serialize opaque launches | Accepted |
| [ADR-0133](0133-treat-product-specialist-loads-as-turn-scoped.md) | Treat product specialist loads as turn-scoped | Accepted |
| [ADR-0135](0135-require-explicit-codex-child-execution-turns.md) | Require explicit Codex child execution turns | Superseded |
| [ADR-0136](0136-bind-opaque-codex-execution-by-ciphertext-identity.md) | Bind opaque Codex execution by ciphertext identity | Superseded |
| [ADR-0137](0137-reconcile-codex-followup-completion-at-parent-stop.md) | Reconcile Codex follow-up completion at parent Stop | Superseded |
| [ADR-0138](0138-request-automatic-codex-delegation-through-managed-global-guidance.md) | Request automatic Codex delegation through managed global guidance | Accepted |
| [ADR-0139](0139-make-codex-execution-turns-self-contained.md) | Make Codex execution turns self-contained | Superseded |
| [ADR-0140](0140-use-codex-stable-multi-agent-feature.md) | Use the Codex stable multi-agent feature | Superseded |
| [ADR-0141](0141-admit-writer-proof-only-through-agency-plans.md) | Admit writer proof only through Agency plans | Accepted |
| [ADR-0142](0142-require-terminal-product-child-before-next-unit.md) | Require terminal product child before the next unit | Superseded |
| [ADR-0143](0143-execute-codex-specialists-in-the-initial-spawn-turn.md) | Execute Codex specialists in the initial spawn turn | Superseded |
| [ADR-0144](0144-claim-codex-spawn-execution-at-the-first-complete-callback.md) | Claim Codex spawn execution at the first complete callback | Accepted |
| [ADR-0145](0145-place-exact-codex-execution-after-specialist-expertise.md) | Place exact Codex execution after specialist expertise | Accepted |
| [ADR-0146](0146-preserve-content-free-codex-child-tool-outcomes.md) | Preserve content-free Codex child tool outcomes | Accepted |
| [ADR-0147](0147-persist-codex-child-tool-evidence-on-worker-receipts.md) | Persist Codex child tool evidence on worker receipts | Accepted |
| [ADR-0148](0148-classify-nested-codex-exec-tools-without-content.md) | Classify nested Codex exec tools without content | Accepted |
| [ADR-0149](0149-classify-codex-wrapper-failures-without-content.md) | Classify Codex wrapper failures without content | Accepted |
| [ADR-0150](0150-correlate-codex-wrapper-tools-with-outcomes.md) | Correlate Codex wrapper tools with outcomes | Accepted |
| [ADR-0151](0151-route-codex-product-approvals-to-auto-review.md) | Route Codex product approvals to automatic review | Accepted |
| [ADR-0152](0152-fail-open-with-honest-header-when-no-specialist.md) | Fail open with an honest header when no specialist is selected | Accepted |
| [ADR-0153](0153-adopt-per-stage-inference-profile-routes.md) | Adopt per-stage inference profile routes | Accepted |
| [ADR-0154](0154-plain-text-cli-cards-over-rich-dependency.md) | Plain-text CLI cards over a rich dependency | Accepted |
| [ADR-0165](0165-keep-litellm-inference-profiles-model-agnostic.md) | Keep LiteLLM inference profiles model-agnostic | Superseded |
| [ADR-0166](0166-delegate-exact-schema-translation-to-litellm.md) | Delegate exact schema translation to LiteLLM | Accepted |

## Documentation governance

| ID | Decision | Status |
|---|---|---|
| [ADR-0025](0025-self-contained-linked-documentation.md) | Keep a self-contained planning-to-evidence documentation chain | Accepted |
| [ADR-0084](0084-bounded-recovery-capsules-and-idempotent-task-dispatch.md) | Use bounded recovery capsules and persistent goal ownership | Superseded |
| [ADR-0085](0085-continue-in-task-after-context-checkpoints.md) | Continue in the current task after context checkpoints | Superseded |
| [ADR-0086](0086-use-checkpoint-only-context-telemetry.md) | Use checkpoint-only context telemetry | Accepted |
| [ADR-0087](0087-inference-decides-from-a-relevance-shortlist.md) | Inference decides specialist selection from a relevance shortlist | Accepted (offline-decline clause superseded by ADR-0088) |
| [ADR-0088](0088-deterministic-typed-recall-offline-floor.md) | Deterministic typed-recall is the offline floor | Superseded |
| [ADR-0089](0089-zcode-stop-rejections-use-decision-block.md) | ZCode Stop rejections use decision:block | Accepted |

## Maintenance rules

- Record the decision before or with the implementation that depends on it.
- Update this registry in the same change as a new decision record.
- Never edit an accepted record to hide a changed decision. Add a new record and wire supersedes and superseded_by in both directions.
- Keep decision links repository-local. External systems may be cited as evidence only when the repository does not depend on them for understanding the decision.
