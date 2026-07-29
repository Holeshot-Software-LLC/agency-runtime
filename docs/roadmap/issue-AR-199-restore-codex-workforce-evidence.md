---
title: "AR-199: Restore Codex workforce selection and evidence"
status: in_progress
category: roadmap
created: 2026-07-28
updated: 2026-07-29
tags: [codex, routing, workforce, receipts, resident-managers, regression]
related:
  - docs/decisions/0003-response-telemetry-is-model-truth.md
  - docs/decisions/0065-keep-compact-resident-manager-kernel.md
  - docs/decisions/0077-prove-codex-activation-behaviorally.md
  - docs/decisions/0081-compile-contractors-from-governed-structured-contracts.md
  - docs/decisions/0083-use-capability-indexed-recall-and-bounded-inference.md
  - docs/decisions/0112-stage-preflight-workforce-evidence-until-ready.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-195-separate-codex-canary-parent-and-child-goals.md
  - docs/roadmap/handoffs/issue-AR-199.md
supersedes: []
superseded_by: null
type: issue
epic: routing
issue_id: AR-199
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/161
depends_on: []
blocks: []
---

# AR-199: Restore Codex workforce selection and evidence

## Problem

The exact merged default installation loads Agency's Codex plugin, but the
first trusted production task exposed a broken end-to-end workforce contract.
The resident-manager binding is present while model-authored headers can report
`loaded: none`; nontrivial inferred work can abstain with no specialist; model
provider attempts are not persisted; contractor hiring is unavailable; and the
activation canary rejects its own native child goal.

## Current state

Exact installed revision `34e3180e465c175b07e1b0ae3c0b14106c36cca2`
successfully registers Codex and ZCode. The merged repair slices now
commit workforce receipts and deferred hires atomically, preserve Codex's
encrypted spawn input, inject the exact specialist context at child start, bind
generated contractors to their causing unit, and keep parent, planner, and
specialist model scopes distinct.

A fresh USB-diagnostic task proved that inference is running: two provider
attempts were recorded against `codex-subscription/gpt-5.6-luna`. The active
roster still produced zero eligible workers, and governed hiring declined with
`contract_invalid:ValueError`. The parent Codex task was configured by the
owner as Sol High; Luna was only Agency's independently configured workforce
planner. The existing `Actual Model selected` projection therefore conflated
three distinct identities: parent task, workforce inference, and specialist
execution.

Source reproduction isolated the hiring failure. The hiring JSON schema accepts
natural-language artifacts and safety boundaries, while the workforce contract
requires exact normalized artifact, lifecycle, capability, tool, host, and
platform identifiers. A generated contractor could therefore be valid prose
but fail its own causing work unit or current host.

The first source-level isolated canary after PR 162 proved the remaining route
regression exactly: its predecessor planned two units and selected nobody,
whereas trace `019fae5a-4815-7a82-a65e-66db8e35f203` used
`codex_activation_canary_contract`, selected `code-reviewer`, emitted one unit,
spawned once, and waited once. The child started and completed, but Codex's
spawn result left the issued activation grant unconsumed and the specialist-load
receipt absent. Exact-installed reruns after PRs 163 and 164 disproved both the
mapping-only and optional-nickname diagnoses: this configured Codex v0.146
surface emitted exactly `{"task_name":"/root/unit_05d45f7553"}`. The live
ordering instead records and delivers the real child at SubagentStart while the
grant remains deferred to PostToolUse. After moving consumption to
SubagentStart, traces through `019faeca-406f-7d20-b2e7-6b1741b5a8af` proved
that PostToolUse does not resolve the original callback identity. Store-backed
trace `019faef8-f76b-7740-9558-462e99f4abeb` then isolated the live ordering:
parent PostToolUse records the synthetic task lineage before child
SubagentStart consumes the exact grant against the real UUID. The final Store
contains the correct activation, but no later edge promoted the already-created
compact delegation, so finalization correctly stopped at `continue`.
Source-live trace `019faf17-be08-75a1-a074-8425eff20a71` then proved that
promotion repair end to end: one `code-reviewer` was selected, activated,
loaded, spawned, waited, and linked through the real child UUID with a valid
header and zero unexpected tools. The remaining rejection moved one boundary
later: Codex supplied the successful child's final assistant message, but the
outcome-free SubagentStop projection left the worker exit code unset and the
delegation at `delegated`, so finalization remained `continue`.
Source-live trace `019faf33-3766-7112-ab70-823e05dd598a` proves the terminal
repair: the exact delegation is `completed`, the linked worker ended with exit
code zero, and the earlier temporal hook diagnostic is absent. Finalization
still returned `continue`, but the continuation receipt discarded the
verifier's missing-field codes, so that last policy mismatch was not traceable.
Trace `019faf3e-5eb6-7a92-9423-cb5b083fa285` then made the mismatch exact:
the parent response retained every pre-execution header field except the stable
`Skills loaded` value. Codex received `continue: false`, which terminates a Stop
hook, instead of `decision: "block"`, which creates the documented corrective
continuation prompt. The model therefore never received the authoritative
post-child header rewrite.
Trace `019faf49-67bc-7953-8ff2-64f33173ae79` proves that correction path live:
Codex recorded one bounded `continue`, emitted the rewritten header, committed
one authoritative `accept`, and closed the run as `completed`. The activation
canary still reported failure only because its topology checker required
exactly one finalization row and treated the legitimate correction-plus-accept
pair as an incomplete graph.
Source-live trace `019faf50-d5d7-7bf2-8c88-e1dfd791a4fe` passes the corrected
canary with no unmet prerequisites. It proves exactly one route, plan, grant,
consumption, native child, specialist load, completed delegation, bounded
correction, authoritative accept, and completed run. Its isolated profile does
not mutate the persistent current-profile attestation.

## Approach

The implementation preserves the atomic preflight boundary while giving
workforce routing governed Store reads. It projects bounded provider receipts
and validated workforce changes as pending evidence, hydrates pending
specialists through a nonpersistent view, and commits the allowed evidence only
inside the winning ready CAS. It also recognizes Codex's opaque persisted spawn
message only for the package-owned canary goal after exact parent, task-label,
and assignment correlation; ordinary child goals retain exact equality.

The follow-up preserves Codex's opaque tool input unchanged. It stages the
native-hook grant at `PreToolUse`, retrieves one unambiguous prompt only after
the exact child lifecycle is persisted, injects that prompt through
`SubagentStart`, and consumes the grant at `PostToolUse` using exact tool-call
and lifecycle evidence. Rollout parsing now accepts the observed
`agent_message` delivery shape and rejects task-complete records with a decrypt
error or no final child message. Live proof showed that the exact delivery must
also be the complete `SubagentStart` context: prefix or suffix guidance changes
the strict original-task or prompt-body hash boundary.

The current follow-up binds every validated employment contract to the exact
typed causing work unit before criticism and persistence. It also aligns the
provider JSON schema with the parser, keeps natural-language artifact prose out
of typed routing identifiers, accepts explicit negative safety boundaries, and
passes the current host into deterministic eligibility. Header model text now
labels matching provider receipts as workforce inference and explicitly states
that the parent model is host-selected and not observable to Agency; it never
promotes Luna into the parent or specialist slot.

The isolated canary backend now marks its existing evidence Store before the
nonce-bound request. The PostToolUse boundary accepts Codex's native mapping
shape as well as its JSON-string shape. For v0.146 spawn results it permits only
`task_name` and the documented optional `nickname`, discards the nickname before
binding, and retains the rooted task label, exact task-name, exact projected-key,
persisted child-lifecycle, and one-use activation checks.

The current follow-up consumes the opaque canary's exact native-hook grant at
SubagentStart, after the real child UUID lifecycle is persisted and before the
specialist context is returned. Exact tool-use, unit, specialist version, prompt
hash, prompt body, worker, and native-run identities must all match. PostToolUse
then reconciles the already-consumed lineage idempotently.

Source-live trace `019faea3-4ea3-73a1-86c7-73443e519dc8` proves that repair:
one activation consumption and one specialist load now bind the real Codex
child UUID. The remaining verifier failure is limited to Codex's exact
`--dangerously-bypass-hook-trust` notice being counted as an unexpected tool.
The parser now excludes only that fixed host notice and rejects all other error
items.

PostToolUse resolves the planned unit from Codex's bounded rooted response and
reconciles a missing host callback only when the Store already contains exactly
one consumed native-hook activation for that task label, selected specialist
version/hash, and real `codex-agent:<UUID>` child.
It validates Codex's bounded rooted response before replacing the synthetic
task projection; unconsumed, ambiguous, mismatched, or synthetic lineage still
fails closed. A focused callback-ID rewrite regression joins the complete
activation suite, which passes 19 tests.

The canary projects one allowlisted, content-free PostToolUse reconciliation
rejection code through bounded run metadata, with hook stderr retained only as
a best-effort secondary source. That diagnostic identified
`reference_activation_cardinality_mismatch` before SubagentStart consumption.
The attachment transaction now recognizes only Agency's exact Codex synthetic
task lineage, one consumed native-hook grant, and one matching real
`codex-agent:<UUID>` lifecycle row. It atomically replaces the synthetic
delegation lineage, links the activation receipt, and binds the worker row to
the work unit. If SubagentStart wins first, the existing PostToolUse reconcile
path remains authoritative; every ambiguous or lookalike shape still fails
closed. The complete activation file passes 20 tests, including the observed
PostToolUse-before-SubagentStart order.

Codex's documented SubagentStop contract and current native source make a
non-empty `last_assistant_message` the successful child-turn completion edge.
The hook now records `ok` only for that exact signal and never persists the
message; empty stops remain outcome-free. The expected parent-PostToolUse
activation gap is no longer emitted as a canary rejection because
SubagentStart owns its later exact attachment.

Continuation claims now retain the verifier's bounded missing-field codes while
continuing to store only a response hash. The earlier Store promotion helper
also resolves the Codex task-label utility lazily, preserving a clean
fresh-process import order between Store and the public delegation package.

Codex Stop corrections now use `decision: "block"` and a bounded `reason`;
terminal retry exhaustion continues to use `continue: false`. This restores one
model correction pass without reopening a terminal response or changing
ZCode's stricter always-block compatibility rule. Optional child identity is
also initialized before every PostToolUse branch, preventing non-spawn tool
events from reading an unbound local.

The Codex activation proof now accepts either a direct authoritative accept or
exactly one content-free correction followed by the authoritative accept. It
still rejects more than one correction, a correction without missing fields,
duplicate response hashes, nonterminal accepts, and every extra activation,
delegation, child, load, route, trace, or plan row.

Header parser and formatter documentation no longer repeats a manually
maintained line count. The user-facing Stop correction derives its line count
from `HEADER_FIELDS`, and a native-hook regression pins the exact seven-line
diagnostic.

The zero-correction acceptance contract supersedes the canary's former
correction-plus-accept allowance. Stop correction remains a fail-closed runtime
backstop, but it cannot satisfy activation proof.

The named fast production spine passes 651 tests with 6 skips, the dashboard
suite passes 109 tests, and the routing evaluation passes every gate. A fresh
ordinary Codex turn also rendered both resident managers and proposed
`codebase-onboarding-engineer`, `minimal-change-engineer`, `code-reviewer`, and
`test-results-analyzer`. That is selection evidence, not completed delegation:
an intervening selection-explanation request superseded the launchable plan,
and a reduced-context preflight on only the latest conversational sentence
truthfully abstained. Exact-installed launch and model-receipt proof therefore
remain open.

PR 165 merged the repair as `816db5b29a78faf8a09bd16eeecc987a15d3bc6c`.
That exact revision was installed and refreshed into Codex. Isolated-profile
trace `019faf64-5aee-78e0-a5ab-657f782a6175` then passed with one
`code-reviewer` route, grant, consumption, real child UUID, specialist load,
completed delegation, worker exit zero, spawn, wait, and accepted finalization;
the header was valid and no hook diagnostic or unmet prerequisite remained.
The refreshed normal profile remains `hook_trust_status: unverified` and
`restart_required: true`, so this is autonomous isolated-profile proof rather
than attended current-profile activation or provider/model-receipt proof.

Two subsequent ordinary Codex tasks exposed a first-pass header regression.
The Conveyor status answer took 165 seconds before emitting
`Agency/Agencies loaded: none`, then spent 11 seconds on one Stop correction;
the dashboard telemetry answer took 264 seconds before the same invalid value
and 19 seconds on its correction. Both persisted rollouts completed after one
correction rather than an unbounded retry, but each duplicated the answer and
failed first-pass acceptance. The preflight template had authoritative resident
binding evidence while still presenting `none` as a valid loaded value. It now
renders the exact resident pair, forbids replacing it with `none`, and requires
the evidence header in substantive progress updates. Focused cross-host,
context-ceiling, preflight, and hook coverage passes 156 tests. The named fast
spine then passes 651 tests with 6 skips, the dashboard passes 109 tests, and
the routing evaluation, Ruff, formatting, and documentation gates all pass.

The first response in the already-open owner task still entered one Stop
correction. Its hook path names removed bundle `0.1.0+codex.3082f29f362e`,
while the only installed bundle is `0.1.0+codex.1b65d565506c`; that process is
therefore stale and cannot prove or disprove the installed repair. The
correction also exposed a separate current-source defect: the validator
requires seven fields but called them an exact six-line header. The diagnostic
now derives `7` from the authoritative field tuple instead of carrying a stale
hard-coded count.

The follow-up passes 66 focused header and native-hook tests. The named fast
production spine passes 651 tests with 6 skips, the dashboard passes all 109
tests, the routing evaluation passes every gate, and documentation, Ruff,
formatting, and diff checks pass. A sandboxed Node worker first returned
`spawn EPERM`; the canonical command passed outside that process boundary.
Any live proof with a correction count above zero remains `NO-GO`, even when
the bounded Stop backstop repairs the response.

Exact merge `85069f3b992b88b2a0d43e37a1f75f2d96045aa1` produced Codex bundle
`0.1.0+codex.1366cdece66b`. Isolated trace
`019fafb3-8200-7163-83b0-e2405c783a4c` proved one complete
`code-reviewer` activation chain, but its first response omitted six header
fields and required one correction 16 seconds later. The legacy canary called
that pass; the owner acceptance contract calls it `NO-GO`.

The bounded repair injects a Store-derived seven-line header snapshot after a
successful Codex wait, immediately before final response generation. Canary
proof now requires exactly one authoritative finalization, reports
`correction_count`, and exposes the validated header fields without response
body content. The directly affected hook and canary suites pass 148 tests.

Exact merge `aa0d94974cf89b0b21c6dfc47fa3798c95f24aa3` produced Codex bundle
`0.1.0+codex.fc83b66da46d`. Isolated trace
`019fafc4-f1d8-76a1-ae07-16381ce00267` is the first zero-correction live GO:
it records exactly one accepted finalization, `correction_count: 0`, one
selected and loaded `code-reviewer`, one completed delegation, worker exit
zero, and exactly one spawn plus one wait. The accepted header reports both
resident managers and the specialist. Its model field truthfully says the
parent is host-selected and unobservable and that no specialist launch-model
receipt exists; ordinary multi-unit selection and authoritative model-receipt
proof therefore remain separate open packages.

The exact-installed deterministic detector recognizes the bounded ordinary
probe as four independent high-confidence units and marks it delegable. Local
workforce reads confirm enabled matches including `codebase-onboarding-engineer`,
`code-reviewer`, `test-results-analyzer`, `reality-checker`, and
`model-qa-specialist`. That is a local precheck, not an authoritative plan:
the configured planner is external `codex-subscription/gpt-5.6-luna`, and this
package does not infer egress authorization. The launch-model receipt and
persistent-profile trust steps remain explicit `NO-GO` or waiting boundaries.

Ordinary trace `019faf9a-625a-7a23-ba2d-2679a4401eb5` is a current failure:
its inferred three-unit local-page plan selected nobody, attempted hiring, and
needed one Stop correction. A local replay of the same typed unit shape exposed
the deterministic cause: generic software discovery ranked `finops-engineer`,
generic page implementation did not own a frontend anchor, and implementation
review ranked `accessibility-auditor`, ending in `selection_margin_too_low`.
Commit `196dedc` binds those units to `codebase-onboarding-engineer`,
`frontend-developer`, and `code-reviewer`. The replay now accepts all three
assignments, and the focused selection-safety suite passes 24 tests with one
platform skip. This is source proof; exact-installed ordinary proof remains.

The same trace falsely reported `eligible_count: 0` because workforce routing
does not use legacy retrieval and the receipt treated its unavailable count as
authoritative. Commit `c02a10a` carries the explicit eligible-catalog count into
the durable projection while preserving the distinct retrieval count. The
focused receipt and selector suites pass all 71 tests.

The post-repair fast production checkpoint is green. The named Python spine
passes 652 tests with 6 skips, the dashboard suite passes all 109 tests, the
routing evaluation returns `passed: true`, and the documentation, Ruff, format,
and diff gates pass. This closes source verification without substituting for
the still-required exact-installed ordinary provider and delegation trace.

PR 171 merged those repairs as exact commit
`fbed63abaf739d6a863113a221c09c8cfababc40`, now installed as build
`0.1.0+gfbed63abaf73` with Codex bundle `0.1.0+codex.ae2086569c9e`.
Isolated trace `019fb039-193d-79c2-b771-5cdd2ad86065` passes the complete
activation chain with one loaded and completed `code-reviewer`, one native
spawn and wait, one accepted finalization, a valid first-pass header, and zero
corrections. Current-profile inspection separately reports all eight hooks as
modified and stops before model invocation, so attended trust is still open.

The first exact-installed ordinary product trace,
`019fb03e-5ad6-7b70-8d22-bc8c7ee0d028`, is a bounded `NO-GO`. It persisted two
successful Luna wrapper receipts and found 53 eligible workers, but its
nine-unit plan selected nobody because the `architecture-record` / `design`
unit had no eligible governed owner. Commit `b8c0a8d` fixes the contract bridge:
architecture-category workers compile as architects and the unit anchors to
`software-architect`. The focused contract and selection suites pass 50 tests
with one platform skip. The named Python spine passes 653 tests with 6 skips,
the dashboard passes all 109 tests, the 39-gate routing evaluation reports
`passed: true`, and documentation and Ruff gates pass. Exact-installed rerun
remains pending.

## Dependencies

AR-119 owns inference-first planning, staffing, and governed hiring. AR-195 and
ADR-0077 own the exact Codex activation canary. ADR-0003 and ADR-0065 govern
model truth and resident-manager visibility.

## Acceptance

- [ ] Every enabled Codex parent turn with a valid resident binding reports
  `agents-orchestrator, chief-of-staff` on its first generated response, even
  when no specialist is selected, without requiring Stop correction.
- [x] Configured workforce provider attempts are committed as current-turn
  model receipts without leaving evidence behind after a failed preflight.
- [x] Same-task gap hiring can use the governed Store without bypassing the
  ready-CAS or creating partial workforce state.
- [ ] A nontrivial four-unit request against the active workforce produces a
  verified unit-agent plan or a complete truthful gap/hiring outcome; it does
  not silently collapse to a generic no-match result.
- [x] Focused Codex activation tests launch exactly one goal-bound specialist,
  waits exactly once, and persists a complete attestation.
- [x] Focused tests cover header reconciliation, atomic receipt persistence,
  hiring availability, and exact canary goal binding.
- [x] The current hiring and model-scope follow-up passes 177 broadened focused
  tests with one expected xfail; all 601 Python files pass Ruff.
- [x] Source-level isolated canary routing selects exactly `code-reviewer`,
  produces one read-only unit, spawns once, and waits once without a trust
  prompt; focused activation and receipt verification passes 68 tests with two
  platform skips.
- [x] Source-live Codex canary passes the complete correction-plus-accept
  activation graph with no unmet prerequisites.
- [x] Both Codex callback orders bind the consumed specialist, real child UUID,
  compact delegation, and worker-run receipt to the same exact work unit.
- [x] A successful Codex SubagentStop closes the exact worker and delegation;
  an empty stop remains outcome-free and cannot fabricate success.
- [x] A rejected native finalization retains bounded missing-field diagnostics
  without persisting the response or specialist content.
- [x] Codex corrective Stop responses use the current documented continuation
  shape while terminal outcomes remain non-looping.
- [x] The named fast Python, dashboard, documentation, lint, and routing
  evaluation gates pass locally.
- [x] The exact merged revision passes the isolated-profile Codex activation
  canary with one complete real-child evidence chain and no trust prompt.
- [x] Preflight pins the authoritative resident pair in final and substantive
  status headers while preserving every host context ceiling.
- [x] Header correction diagnostics identify the authoritative seven-line
  contract without a stale hard-coded field count.
- [x] Codex activation proof rejects every correction count above zero and
  projects the count explicitly.
- [x] Exact-installed isolated trace
  `019fafc4-f1d8-76a1-ae07-16381ce00267` completes one real-child specialist
  chain with exactly one accepted finalization and zero corrections.
- [x] The exact-installed detector recognizes the ordinary proof prompt as four
  independent high-confidence units and local workforce reads find relevant
  enabled employees without invoking the external planner.
- [x] The persisted ordinary three-unit local-page shape deterministically
  staffs `codebase-onboarding-engineer`, `frontend-developer`, and
  `code-reviewer` without a margin abstention.
- [x] Workforce receipts report the explicit eligible catalog independently of
  the unused legacy retrieval count.
- [x] Exact merge `fbed63a` passes an isolated-profile activation trace with one
  completed specialist chain, a valid first-pass header, and zero corrections.
- [ ] A fresh exact-installed Codex task visibly reports both resident managers,
  at least one accepted specialist for an explicit bounded work unit, and an
  authoritative provider/model receipt.
