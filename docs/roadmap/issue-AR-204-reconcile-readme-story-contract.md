---
title: "AR-204: Reconcile the README story contract"
status: in_progress
category: roadmap
created: 2026-07-30
updated: 2026-07-30
tags: [product, dashboard, cli, inference, activation, evidence, automation]
related:
  - README.md
  - docs/decisions/0117-unify-owner-control-authority.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0119-separate-native-trust-modes-from-activation-proof.md
  - docs/decisions/0120-construct-first-pass-evidence-headers.md
  - docs/decisions/0121-gate-deterministic-recall-without-selection-authority.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
  - docs/roadmap/issue-AR-196-authorize-prepared-dashboard-service-repair.md
  - docs/roadmap/issue-AR-197-remove-agency-owned-windows-hello.md
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/THREAT_MODEL.md
  - docs/worklog/README.md
supersedes:
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
  - docs/roadmap/issue-AR-196-authorize-prepared-dashboard-service-repair.md
superseded_by: null
type: issue
epic: product
issue_id: AR-204
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/189
depends_on: []
blocks: []
---

# AR-204: Reconcile the README story contract

## Problem

The README's short product story and several later security, routing, and live-
proof changes no longer describe one executable system. The default installer
includes the dashboard but production disables its controls; owner CLI commands
enter a verifier whose implementation was intentionally removed; `dashboard
service open` can repair a service but is classified as a presence-gated
mutation; deterministic staffing remains available despite the inference-first
claim; native hook trust is sometimes treated as activation; and response or
dashboard surfaces can look healthy without underlying execution evidence.

These contradictions have repeatedly moved the live demo boundary instead of
letting one stable README story reach proof.

## Current state

The underlying configuration writers, dashboard mutation handlers, lifecycle
transactions, inference receipts, specialist activation records, and product
trial evaluator already exist. Blanket production gates and stale governing
records prevent those pieces from forming the advertised product. The exact
installed build `5e3fab622b75f257e0ab4b74f1cc2c6d43b1d748` proves the dashboard
service is healthy and the Codex plugin is registered, but it does not prove an
authenticated rendered dashboard, a successful prompt route, specialist
injection, delegation, or workspace write.

## Approach

1. Establish one authority model: normal owner CLI commands and the
   owner-authenticated dashboard are equivalent local configuration/control
   surfaces. Hook, MCP, and broker credentials remain read-only. Exact
   confirmation, revision/CAS, dry-run, ownership, and rollback checks remain
   safety controls; they do not pretend to prove a human is present.
2. Keep the dashboard an optional component that bare `agency install` selects
   by default. `--no-dashboard` opts out. `dashboard service open` may install,
   repair, or start an owned service before opening it.
3. Require a valid inference decision for every substantive specialist-
   selection turn. Deterministic code may classify, recall, filter, and verify,
   but may not choose, rank, recommend, or hire a specialist when inference is
   unavailable or invalid.
4. Separate native host registration, trust mode, hook start, route,
   specialist injection, delegation, and finalization as distinct evidence
   stages. Support both attended native trust and an explicit autonomous mode
   for isolated/container installations without claiming bypassed hooks are
   trusted.
5. Make a missing, malformed, corrected, or evidence-mismatched response header
   a loud terminal product failure. The header is a projection of Store
   evidence, never independent proof of execution.
6. Require dashboard proof to authenticate, render the packaged application,
   read configuration, perform a reversible owner configuration mutation, and
   restore the prior value. HTTP reachability alone is service health only.
7. Keep tests as the shared runtime backbone and add host-adapter contract tests
   plus bounded live canaries for the remaining harness-specific behavior.

## Dependencies

ADR-0117 owns local owner authority and default-suite semantics. ADR-0118 owns
inference-only staffing. ADR-0119 owns attended and autonomous native trust
modes and separates trust from activation evidence. AR-119 retains the complete
workforce implementation, while AR-203 retains exact Codex workspace and live
product proof.

## Implementation evidence

Commit `ffec102` removes the retired shared presence dispatcher and parser
metadata, restores prepared roster rollback to normal owner authority while
retaining its exact Store/generation/revision revalidation, and keeps model-
facing native controls read-only under an explicit `owner_control_required`
result. The obsolete AR-143 and AR-196 contracts are now marked `wont_do` and
superseded by this issue rather than left as apparently active requirements.

Focused verification passed 708 tests with one platform skip across owner CLI,
parser, install/uninstall, Codex activation-shape, prepared transaction,
dashboard-service recovery, host-control, security-turn, native-installer,
upgrade, and release-contract boundaries. Ruff, formatting, metadata, policy,
documentation, worklog-currentness, and staged whitespace checks passed.

Commit `c8c8020` restores the owner dashboard surface end to end. The owner
bearer now reaches the existing confirmation- and revision-bound mutation
handlers; the broker bearer receives `403 owner control required` before its
bounded request body can reach a handler. The packaged client again exposes
configuration, maintenance, master, host, roster, workforce, and hiring
controls while retaining current request correlation, lifecycle cancellation,
bounded collections, activation disclosure, and stale-Store interlocks.

The complete dashboard client suite passed 110 tests, including exact request
bodies for all eight mutation endpoints. The dashboard authentication and
server suite passed 145 tests with three platform skips. The restored HTML is
byte-identical to the last owner-capable pre-regression Git blob, so no
display-truncated or hand-reconstructed shell content remains.

Commit `e1451ea` makes inference the sole production staffing authority.
Missing provider configuration, unavailable inference, and invalid inference
now produce explicit failure states with no selected, recommended, delegated,
or hired specialist. Online planning preserves the model-authored plan without
local enrichment; unit assignment requires exact inference-authored unit
claims; child routing clears unproven specialist identities; and legacy judge
paths can no longer restore confidence, token, or local-ranking fallbacks.
Historical durable unit plans remain replayable only when their recorded unit
and specialist identities still correlate to the same request and roster.

The final focused package passed 368 tests with one intentional skip. The
decision-conformance evaluation passed its baseline and killed all 26 curated
regressions with zero survivors and zero invalid mutations, including attempts
to restore offline staffing, deterministic plan enrichment, unavailable unit
assignment, and unconfigured-child specialist retention. Ruff, format, and
diff-integrity checks passed on the exact committed tree.

The activation source candidate now exposes one explicit autonomous install
transaction over the normal default-suite path. It uses Codex's supported hook-
trust bypass only for the exact canary invocation, records that invocation as
`autonomous_bypass`/`bypassed`, never mutates persistent trust, and cannot report
runtime readiness without the same behavioral proof required in attended mode.
Product-host evidence is bound to the exact activation rollout and workspace-
write sentinel. The former deterministic canary specialist fixture is removed:
normal workforce inference must select the worker and persist provider receipts
before the adapter may narrow that same worker to the fixed read-only diagnostic
goal. Missing or invalid inference fails visibly with no selected specialist.

Commit `03dba75` contains the reviewed activation package. Its expanded bounded
activation/product/preflight spine passed 287 warning-strict tests with one
intentional platform skip. Review caught and repaired three additional fail-
closed defects before commit: requested bypass was no longer mistaken for an
invoked bypass; the read-only activation canary no longer enters gap hiring;
and modern durable plan equality plus the bounded inferred binding now survive
exact replay. The last complete local decision-conformance run passed its
baseline and killed all 29 then-defined mutations with zero survivors and zero
invalid mutations. Four review-added mutations are manifest-tested; their
complete 33-mutation execution is the first post-checkpoint gate.

The first-pass response package supersedes the former one-correction policy
with ADR-0120. Native Codex now receives exact initial, updated, and final
Store-backed header snapshots before publication. Hermes and OpenClaw direct
the model through `agency.finalize` once before the natural final response and
accept only the exact committed result. The first invalid natural response
closes as `response_invalid` or `delegation_declined`; production no longer
claims a continuation receipt, OpenClaw never requests `action: revise`, and
Hermes exposes only a bounded safe failure response for an unverified draft.

The bounded finalization spine passed 378 warning-strict tests with five
platform skips, followed by a 144-test post-format regression. Ruff, formatting,
metadata, policy availability, documentation validation, and whitespace checks
passed. Four new curated mutations cover restoration of a Codex continuation
prompt, removal of the initial Codex snapshot, restoration of OpenClaw model
revision, and Hermes post-generation repair. The complete isolated evaluator
passed its 29-node baseline and killed all 37 curated mutations in 323 seconds,
with zero survivors, zero invalid results, and the source checkout unchanged.

The packaged source dashboard passed its bounded owner round trip against an
owner-private disposable configuration and Store. The browser consumed the
one-time fragment token, removed it from the visible URL, rendered the Signal
Observatory as `Authenticated` and `Online`, and exposed the same resolved
configuration path and retention value as the CLI. An unauthenticated
`/api/config` request returned `401`; the owner bearer returned `200`. The UI
changed retention from 37 to 38, the CLI independently read 38, and the UI then
restored 37. The configuration SHA-256 moved from
`d527e0901ce83b85a110d476d82045458768e92686c0dee4ac8583230311e944` to
`1bf901a9f9b746b4f4f647ecd33b31c7b045d6511ae58d6caabd5d3d8f42a0de`
and returned exactly to the original hash after restoration. The isolated
server was stopped and its token expired. This proves the source candidate's
dashboard boundary; the exact merged installation still owns the final product
trial.

The named fast spine then exposed a remaining inference-authority defect rather
than accepting a false green report: the legacy route preserved
`inference_unavailable` but merged a deterministic policy companion into
`selected_ids`. The route now suppresses every specialist identity projection
on terminal inference failure while retaining only action classification for
diagnosis. Its focused 26-test routing suite passes, and the new curated
mutation proves restoring the deterministic merge fails the exact regression.

ADR-0121 supersedes the obsolete offline-selection interpretation of the
routing gate. Report/corpus v1.4 measures the exact production candidate-union
recall path under `deterministic_candidate_recall_only`; it does not claim a
selected team. The standalone command passes all gates across 37 routing, 30
policy, and 22 delegation cases: required candidate and case recall are 1.0,
top-1 relevance is 1.0, forbidden-candidate rate is 0, and abstention accuracy
is 1.0. Its production cache-path fixture is explicitly labelled synthetic
inference evidence rather than hidden deterministic selection.

## Acceptance

- [x] Owner CLI configuration/control commands dispatch without the retired
  Agency-owned human-presence verifier.
- [x] The owner dashboard exposes the same supported configuration and runtime
  controls as the CLI, while broker, hook, and MCP identities cannot mutate.
- [x] `agency dashboard service open` can ensure an owned default-installed
  service is healthy and open it without an unavailable-presence error.
- [x] Bare install selects the supported dashboard by default and
  `--no-dashboard` remains a complete opt-out.
- [x] A substantive turn without a valid inference provider decision fails
  visibly and selects, recommends, delegates, and hires no specialist.
- [x] Deterministic recall and validation cannot become an online or offline
  specialist decider.
- [x] Attended and explicit autonomous native-install modes are both covered by
  the shared adapter contract; trust status is never reported as activation.
- [ ] Current Codex carries the exact activation contract into hook processes
  and proves hook start, route, exact specialist injection, and native child
  lifecycle separately.
- [x] Missing, malformed, corrected, or evidence-mismatched headers cannot be
  accepted as a successful turn; success requires correction count zero.
- [x] Dashboard success proves automatic token authentication, packaged render,
  configuration read, one reversible owner write, and exact restoration.
- [x] README, troubleshooting, threat model, roadmap, decisions, and tests state
  the same contract without stale operator-presence or offline-selection text.
- [ ] The named fast verification spine passes before the live demo resumes.
- [ ] One exact installed build completes the README product trial with a real
  inferred specialist team, actual delegation where planned, a workspace
  artifact, and zero response corrections.
