---
title: "AR-252: Record host-evidenced, independently verified outcomes for automatic promotion"
status: open
category: roadmap
created: 2026-08-05
updated: 2026-08-20
tags: [workforce, promotion, evidence, native-child, outcomes, critical-path]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-242-autonomous-promotion-review-window.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
  - docs/roadmap/issue-AR-260-accept-verified-launch-bindings-in-outcome-canary.md
  - docs/roadmap/AR-119-9685a16d-accepted-outcome-evidence.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0157-automatically-promote-host-verified-contractors.md
  - docs/decisions/0161-pin-accepted-outcome-parent-recruiter-separately.md
  - agency_runtime/core/accepted_outcome_canary_contract.py
  - agency_runtime/core/outcome_canary.py
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/child_delivery_evidence.py
  - agency_runtime/core/store/workforce.py
  - agency_runtime/core/store/native_child.py
  - agency_runtime/core/workforce/promotion.py
supersedes: []
superseded_by: null
type: issue
epic: workforce
issue_id: AR-252
priority: p0
tracker_url: null
depends_on: [AR-180, AR-242, AR-255]
blocks: [AR-119, AR-253, AR-260]
---

# AR-252: Record host-evidenced, independently verified outcomes for automatic promotion

## Problem

The automatic contractor-to-employee policy is implemented, but its live
evidence path is dormant. Native child termination records an `assignment`
outcome without independent acceptance evidence, so production work cannot
satisfy `promotion_readiness` or trigger `_auto_promote_if_ready`.

The former proposal depended on retired Job B plan rows, assurance units, and
consumed activation receipts. Restoring that transport would contradict the
current host-spawned, just-in-time architecture.

## Current state

AR-242 set the three-success and seven-day review-window policy. Store code can
validate acceptance evidence and perform automatic promotion atomically. The
private Claude collector now pairs exactly two host-artifact delivery
capabilities. An explicit isolated Claude canary mode drives that exact serial
pair and reports content-free provider, card, delivery, and Store-result
evidence. PR #301 installed that path from exact main `5a1d863c`; its first live
draw failed closed before child staffing because both `claude-haiku` parent
planner responses violated the structured response contract. Agency-authored
assignment rows alone remain insufficient proof.

The accepted-outcome v2 contract now enforces the 2026-08-18 joint-verdict
ruling at its input and persisted-manifest boundaries. The semantic decision is
identified by the verifier host artifact's digest and bounded record position;
the collector-owned binding separately names the producer artifact digest and
verifier child. Either half missing, misattributed, or edited after recording is
refused. The owner authorized exactly two consumptions only inside the atomic
producer/verifier transaction on 2026-08-20; no public or general-purpose
capability widening followed.

## Approach

Build an outcome envelope from artifacts the native host wrote. Those artifacts
prove the producer/verifier children, delivered card hashes, artifact digest,
and correlation; they do not prove semantic correctness. A distinct governed
verifier selected by inference establishes semantic acceptance through its
verdict bound to that exact artifact. Store receipts remain a derived audit
index, not the delivery authority.

Evaluate promotion in the same transaction that persists the validated
acceptance. Keep the existing three-success threshold and per-contractor review
window. Do not depend on Job B, model-authored headers, Agency-only lifecycle
rows, or a shared producer/verifier identity.

## Dependencies

- AR-255 must establish inference-owned card choice and host-authored delivery
  proof before an outcome can be attributed to a specialist.
- AR-242 supplies the existing threshold and review-window implementation; its
  unchecked acceptance record is reconciled under AR-256.

## Acceptance

- [x] A host-backed producer artifact plus a distinct, inference-selected
      verifier's host-backed artifact and bound accepted verdict records exactly
      one acceptance event.
- [x] Missing, ambiguous, replayed, Agency-only, shared-identity, or rejected
      evidence records no acceptance and reports a bounded reason.
- [x] Three distinct accepted outcomes automatically promote an eligible
      contractor after its review window with `actor="promotion-policy"` and
      the exact evidence manifest; no operator action is required.
- [x] Replay and concurrent finalization cannot duplicate an outcome or
      promotion.
- [x] Migrate promotion validation and readiness from retired work-unit and
      consumed-activation-receipt identities to the host child, card hash,
      artifact digest, verifier decision, and verdict identities above.
- [ ] Live evidence proves the path through at least Claude and Codex before
      AR-119 can close.
- [ ] AR-253 proves the same accepted-outcome and automatic-promotion behavior
      on ZCode, Hermes, and OpenClaw; an unavailable supported host remains
      unproven and blocks AR-119.

## What the checked boxes do and do not mean

The five checked items cover the deciding rule, recorder, readiness migration,
and the locally simulated pairing path. Synthetic Claude transcripts now cross
the same private artifact verifier and sealed exactly-two transaction used by
the pending live path; direct envelope tests still exercise the host-free core.

They are not live proof. No real host has yet produced an accepted envelope;
the collector cases use synthetic host-shaped transcripts in an allocator-owned
temporary namespace. The remaining two acceptance items are exactly that gap.

The current accepted envelope is `agency.accepted-outcome.v2`. It deliberately
refuses the former flat v1 verdict rather than silently treating collector-added
artifact binding as verifier-authored semantics. No production collector ever
emitted a v1 row, so there is no live acceptance history to migrate. The
2026-08-20 affected acceptance, delivery, promotion, lifecycle, and dashboard
checkpoint is **339 passed**, with Ruff check, Ruff format check, and
`git diff --check` green.

The remaining Claude step is now a bounded preflight repair: reproduce and fix
the parent planner's `provider_response_contract_invalid` result locally, then
publish/install a repaired exact-main candidate and run the explicitly
confirmed live mode. Any further push, PR, merge, installation, or provider
draw requires fresh owner approval.

## Measured before building the collector (2026-08-14, `9e29aabe`)

Three constraints found by reading the seam, and any collector design has to
answer all three. They are recorded here so the next attempt does not discover
them halfway through a build.

1. **Agency cannot summon the verifier.** Rule 5 gives spawning to the native
   harness alone, and `agency_runtime/core/evals/spawn_authority.py` proves at
   the source that worker origin is confined to the host boundaries. So a
   "distinct governed verifier selected by inference" is not something Agency
   arranges — it exists only when the *host* independently spawns a second child
   and Agency staffs it. The collector can recognise verification; it cannot
   cause it. An acceptance rate below 100% is therefore the expected steady
   state, not a defect, and the promotion policy has to tolerate that.

2. **The verified-delivery capability is one-use and canary-only.**
   `_consume_verified_host_child_delivery` pops its identity on read, and the
   sole production consumer is `agency_runtime/core/canary_proof.py`, which
   collects inside a disposable host profile under ADR-0158. Nothing today holds
   two such capabilities at once, which is exactly what one envelope needs.
   Widening the seal is a threat-model change, not a refactor.

3. **No child carries a producer/verifier role, and completion is not
   acceptance.** `record_native_assignment_outcome` maps a native child's exit
   to `passed`/`failed`; ADR-0157 rejects counting child exits precisely because
   completion is not semantic acceptance. Nothing records that one child's work
   was the subject of another child's judgement, so the correlation the envelope
   needs — verdict bound to the producer's artifact digest — has no producer in
   the runtime yet.

## A fourth constraint, found by reading the rule against the seam (2026-08-14)

The three above were found by reading the collector. This one falls out of the
acceptance rule itself and is the sharpest of the four.

At the time of this measurement, v1 took `artifact_digest` from
`producer["artifact_digest"]`, and `_host_child_delivery_projection` set that
field from `evidence.artifact_digest` — the SHA-256 of the bounded trusted read
window of **the producer child's own transcript**. It was not a digest of any
work product. The former flat verdict then had to match it exactly
(`verdict_artifact_mismatch`). V2 retires that ambiguous shape in favor of the
explicit semantic and binding halves below.

So the thing a verifier must bind its verdict to is the hash of a file it cannot
read: the producer's transcript lives in the host's namespace, and the verifier
child has no access to it. **No verifier can compute or even quote that digest
unaided.** Only the collector — Agency, after reading the producer artifact —
can supply it.

That does not make the envelope unbuildable, but it fixes the verdict's shape:
the *semantic* half (accept or reject) must come from the verifier child's own
host-written output, while the *binding* half (which artifact, which verifier)
is assembled by Agency around it. A verdict is therefore a joint object, and the
design has to say so out loud rather than let a reader assume the verifier
authored the whole thing. Whether that division is acceptable evidence, or
whether the rule should bind to a digest of the produced work instead, is an
open decision and not one to settle inside a collector build.

## Delegated ruling: the verdict is a joint object (2026-08-18, loop session)

Recorded under the vision-completion loop brief §5, which directs this
session to settle the fourth constraint's open decision before any
collector build, per this issue's own requirement.

**Ruling.** The acceptance verdict is a joint object with its division
named in the envelope, never implied:

- The **semantic half** — accept or reject, and any qualifying findings —
  must originate in the verifier child's own host-written output. Agency
  never composes, paraphrases, or completes it.
- The **binding half** — which producer artifact digest, which verifier
  identity, which cards — is assembled by the collector, because only the
  collector can read both host artifacts; no verifier child can compute or
  quote the producer's transcript digest unaided.
- The envelope must carry the division explicitly (semantic fields
  attributed to the verifier's artifact by digest and record position;
  binding fields attributed to the collector), so a reader cannot assume
  the verifier authored the whole verdict.

**Why this division rather than a produced-work digest.** The producer's
transcript digest is the only host-sealed identity of produced work that
exists today (`evidence.artifact_digest`); a produced-work digest would
require every child to emit a separable work artifact, which no host
contract guarantees, and much child work *is* its transcript content.
Binding to the transcript therefore preserves ADR-0156's authority chain —
both halves originate in host-written artifacts and Agency only assembles.

**What this ruling does not do.** It does not widen the one-use,
canary-only verified-delivery capability (constraint 2); holding two such
capabilities at once remains a threat-model change that is not taken here
and is not delegated. It does not close the open alternative: binding to a
digest of the produced work remains available as a future *tightening*
under a new owner confirmation, not a rollback of collected envelopes.

**Falsification.** If the owner rules the joint division inadequate as
acceptance evidence, every collected envelope remains auditable by its
named halves and re-derivable under the replacement rule; nothing in the
envelope shape hides which author supplied which field. If a host contract
later guarantees separable work artifacts, the produced-work binding
supersedes this ruling for new envelopes.

## V2 attribution boundary implemented (2026-08-20)

`evaluate_acceptance` and `accepted_outcome_manifest` now require and recheck
both named halves. The semantic half carries exact authority
`verifier-host-artifact`, the verifier artifact digest, a bounded non-boolean
record index, and the verifier's decision. The binding half carries exact
authority `collector`, the producer artifact digest, and verifier child ID.
The verifier artifact digest and semantic record position also participate in
the replay identity, so two records in one verifier transcript cannot collapse
silently. The stored manifest preserves every attribution field and stops
counting if any one is edited.

The owner authorized exactly two consumptions within one atomic pairing
transaction on 2026-08-20. That ruling does not authorize a public multi-use
capability, ordinary-turn outcome recording, installation, or a provider call.

## Exactly-two pairing collector implemented (2026-08-20)

`_collect_private_host_accepted_outcome` requires exactly two artifacts from one
fresh isolated Claude invocation. Each artifact must independently pass the v6
Store decision and host-delivery verifier. Exact launch markers bind a shared
128-bit pair ID and producer/verifier roles; the producer must carry exactly one
contractor card and in-window host-written output, while the verifier must write
one exact semantic JSON line in its own artifact. Missing, extra, mismatched,
ambiguous, stale, or rejected evidence lands on a closed refusal reason.

The collector mints pair-scoped sealed capabilities together. The ordinary
single consumer rejects them, and a shared lock permits only the exact two-member
transaction to call `record_accepted_outcome`; both identities disappear after
a validated terminal Store result and are discarded on every failure path. The
Store result is re-bound to the locally evaluated envelope, exact worker, replay
key, and producer digest. Synthetic tests prove recording, policy promotion,
rejection, ambiguity, pair mismatch, exact-two cardinality, output presence,
single-consumer refusal, replay, and non-public authority. No live or matrix
claim follows from this checkpoint.

## Isolated Claude accepted-outcome canary wired (2026-08-20)

`host-canary claude --accepted-outcome` now has a distinct exact confirmation
phrase and a fixed work shape: one TypeScript producer followed serially by one
independent verifier in the same isolated Claude invocation. The backend raises
its bounded turn allowance only for this mode, collects both artifacts before
the private home is deleted, and never accepts an arbitrary callback or caller-
supplied envelope. The collector compares both immutable routing decisions'
actual applied provider against the configured child-judge pin before it can
reach `record_accepted_outcome`; a mismatch returns `provider_pin_mismatch` and
writes no acceptance row.

The operator report excludes parent, child, and model prose. It names the
requested pin, both actual answering providers, exact content-free card
revisions, host-artifact digests, pair identity, fresh Store result, and whether
promotion occurred. A replay is not a fresh canary pass. The widened local
canary/outcome/CLI regression surface passes 273/273 warning-strict; the final
focused surface passes 46/46 with Ruff lint/format green. The complete local
harness passes 14/14 in 14.4 minutes (796 production-spine, 695 matrix-evidence,
and 134 dashboard tests), and the separate decision-conformance evaluator kills
151/151 mutations from a green baseline. A read-only source CLI smoke reached
the new confirmation gate without `--execute`; its sandboxed host inventory was
not readiness evidence. No host call, provider draw, acceptance, promotion,
candidate advance, or matrix move occurred.

## First exact-main live draw stopped at parent preflight (2026-08-20)

PR #301 merged the canary at `5a1d863c` with no hosted run. Exact-main install
`3c0f9bb6-ca93-444b-a965-c10706e67b67` staged bundle `7a526cd548a9...`; Claude
Code 2.1.226 readiness was green. Pair `5a1be926bf1b0d1e86148b382f474f8d`
then ran once with the required confirmation and 420-second bound. Claude exited
0 without timeout or truncation, while the proof failed closed at
`delivery_marker_absent` and wrote no acceptance, attestation, or promotion.

The Store makes the earlier cause exact. Session `c6a4a7ea...`, trace
`2d918a99...`, and failure `61ec6d6d...` closed `preflight_failed` /
`workforce_inference_failed`. Both planner attempts used `claude-haiku` with
requested and actual `haiku`; both were rejected as
`provider_response_contract_invalid`. No routing decision, worker run, delivery
verification, or applied model receipt exists in the invocation window. The
two host artifacts therefore could not carry Agency v6 delivery markers. This
is a deterministic isolated-parent preflight repair target; it does not measure
the requested `codex-subscription` child judge and moves no matrix cell.

## Local indivisible-parent repair candidate (2026-08-20)

The exact 2,316-character merged-main canary prompt did not satisfy the
existing parent-planner indivisible-unit detector. The local canary-only
candidate now explicitly declares one indivisible work unit and forbids
splitting or decomposition; its 2,367-character prompt satisfies that same
production detector. It changes no provider, model profile, ordinary-turn
behavior, Store contract, or global configuration.

The exact prompt contract passes 11/11 tests, the widened canary/collector/
activation/inference surface passes 102/102, and Ruff plus all 12 fast local
gates are green. No live rerun followed, so this does not yet prove staffing,
accepted outcome recording, attestation, or promotion. Publication,
installation, and one bounded provider draw require fresh owner authority.

## Indivisible-parent repair merged and installed (2026-08-20)

PR #302 merged exact repair head `c798562f` as main `a102a932` with skip
instructions on both commits and no hosted run. The exact head passed the
12-gate fast harness twice locally, including the pre-push hook. Claude-only
install `4c6d8a17-902e-4de6-8b8a-15de14276eca` then staged bundle
`b0b5073ca7cb…` from a clean detached checkout of that merge.

Claude Code 2.1.226 readiness is true with zero unmet prerequisites, current
launcher artifacts, and explicit requested child pin `codex-subscription`.
No provider call or live canary had run at this checkpoint. The single
authorized 420-second falsification draw is next; merge, install, and readiness
alone prove no accepted outcome, attestation, or promotion.

## Second exact-main draw advances to recruiter safety (2026-08-20)

Pair `6e0eff1149894c830127417a1411f06d` ran once from exact main. Claude
exited 0 without timeout or truncation; the wrapper failed at
`delivery_marker_absent` and persisted no attestation, accepted outcome, or
promotion. Session `7c19bc88…`, trace `055d329f…`, run `2dbc72dd…`,
and failure `88840ca1…` close `preflight_failed` /
`workforce_inference_failed`.

The repaired parent prompt reached a valid applied Haiku planner result. The
configured Sonnet recruiter then could not produce a safe selected team for
`unit-parseport-impl` from four ranked implementation candidates, and its
repair attempt returned no valid response. The trace has no route, applied
model receipt, specialist load, delegation, child scope, worker run, delivery
verification, finalization, or outcome event. Collector ordering proves exactly
two in-window host artifacts, but no v6 marker because Agency never staffed.
The requested `codex-subscription` child judge was not reached.

The planner repair is therefore live-proven at its intended boundary. The
remaining issue is the previously measured intermittent Claude/Sonnet recruiter
contract behavior, not accepted-outcome recording or promotion. No automatic
retry followed and no matrix cell moved.

## Parent recruiter isolated onto the chosen provider locally (2026-08-20)

The owner chose a canary-only `claude -> codex-subscription` parent-recruiter
pin. The local candidate now requires that role through the typed
`canary.accepted_outcome_parent_recruiter_provider_by_host` map, projects its
identity and CLI credentials only into the accepted-outcome subprocess, and
uses it only for the primary recruiter call and funded repair. The Haiku parent
planner, ordinary turns, activation canaries, and independently pinned child
judge retain their existing routes. Missing, ambiguous, unsupported, and
mismatched parent pins fail closed without fallback.

No owner config, install, provider, Store outcome, or promotion state changed.
The next proof boundary is an authorized publish/configure/install cycle and
one bounded draw from exact merged main; until then this is local source and
test evidence only and no matrix cell moves.

Verification passed 137 bounded configuration/canary tests (4 skips, one
unrelated historical fast-default assertion deselected), 152 host-canary and
workforce-route tests, 182 child/activation/hook noninterference tests, and the
797-test warning-strict production spine with 20 skips. The 12 fast gates passed
in 1.2 minutes and 713 Markdown files passed documentation validation. The slow
14-gate harness, hosted CI, install, owner-config mutation, and live inference
remain unrun.

## Collector diagnosis shipped ahead of the collector (2026-08-14)

`_collect_private_host_child_delivery` answered eighteen distinct conditions
with a bare `None`, so a Rule 4 canary reported only that delivery "was not
proven". It now returns `HostChildCollection` with a closed reason vocabulary,
the canary record carries `host_child_collection_reason`, and the operator-facing
failure line quotes it. On a live run the same afternoon that previously said
nothing, it says `delivery_marker_absent`.

This is not the envelope collector and does not check any box above. It is the
instrument the envelope collector will be built with — every stage it now names
is a stage the pairing collector has to pass through twice.

What the instrument then found was a break this issue caused. Raising
`SCHEMA_VERSION` from 45 to 46 here, and then running checkout-local CLI
commands against the real `~/.agency-runtime/agency.db`, migrated that store
past the pinned launcher every hook actually executes. Since
`2026-08-14T23:15:24Z` every Agency hook on the evidence workstation has raised
`RuntimeError: Agency Runtime database schema is newer than this runtime
(46 > 45)` and failed open, staffing nothing and recording nothing.

**So no producer proof was collectable on that machine for the rest of the day**,
and every zero-marker measurement taken after that timestamp describes the break
rather than the delivery path. The remedy is a reinstall so the launcher matches
the store; it needs owner authorization.

Two durable consequences for this issue. A schema bump is not a local change
when the store is shared with an installed runtime — **it disables staffing
everywhere until the launcher is refreshed**, which is worth sequencing
deliberately rather than discovering. And `agency doctor` reported the stored
version as a green tick throughout; it now compares that number against the
running runtime's own `SCHEMA_VERSION`, so this condition announces itself.
