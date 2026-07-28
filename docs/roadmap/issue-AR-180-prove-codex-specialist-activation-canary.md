---
title: "AR-180: Prove Codex specialist activation in the live canary"
status: open
category: roadmap
created: 2026-07-27
updated: 2026-07-27
tags: [codex, canary, activation, delegation, production-readiness]
related:
  - docs/roadmap/issue-AR-114-guided-codex-hook-activation.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
  - docs/roadmap/issue-AR-182-bind-codex-hook-trust-inventory.md
  - docs/roadmap/issue-AR-185-bind-codex-activation-verification.md
  - docs/decisions/0077-prove-codex-activation-behaviorally.md
  - docs/decisions/0104-refresh-existing-codex-through-an-exact-attended-transaction.md
  - agency_runtime/core/canary.py
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/canary_proof.py
  - agency_runtime/core/store/evidence.py
  - agency_runtime/dashboard/dashboard-render.js
  - tests/test_host_canary.py
  - tests/test_codex_activation_canary.py
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-180
priority: p0
tracker_url: null
depends_on: [AR-143, AR-182, AR-185]
blocks: [AR-119]
---

# AR-180: Prove Codex specialist activation in the live canary

## Problem

The current-profile Codex canary requires exactly one `code-reviewer` child
activation. Prompt wording alone cannot guarantee that topology: one attended
probe stayed in the parent and another semantic-planner pass split the tiny
diagnostic into two units. Both behaviors are valid for ordinary scheduling but
make activation verification depend on planner variance instead of the
installed hook and native-child lifecycle it is intended to measure.

## Current state

The proof contract and hook-to-Store chain are complete. Strict proof binds the
Codex JSONL tool call, immutable `native_hook` receipt provenance, one-use
activation consumption, child lifecycle, delegation, model receipt, exact
header, current install identity, and the dedicated
`agency.codex-activation-canary.v1` contract. Schema v38 migrates legacy rows to
manual provenance and rejects impossible origin/tool-ID pairs.

The hook remains advisory to Codex scheduling: it injects or rejects only a
positively identified Agency-owned planned call. Ambiguous and unmatched native
calls return no hook decision. A current-profile recheck clears the older
success immediately before invocation, so a failure or timeout cannot leave a
stale readiness claim. Isolated and tokenless diagnostics never persist this
attestation. The dashboard now labels the record as the last successful proof,
neutralizes it when host inspection expires, and exposes no canary action.

Focused proof, provenance, migration, output-durability, dashboard API, and all
106 dashboard UI tests pass locally. Exact checkpoint `af892ae` was built from
a clean private worktree into a 7,465,173-byte Windows wheel and 18,136,468-byte
sdist; independent Windows artifact verification and a fresh Python 3.13 wheel
install passed. The attended existing-install refresh then verified Windows
operator presence, backed up the previous tree, and registered enabled plugin
`0.1.0+codex.92db70112a1a`, bundle `e0c19b9d...ea387`, install ID
`fe76121b-9911-497d-b853-685d39b0e830`.

The attended refresh to plugin `0.1.0+codex.34b430f3606d`, bundle
`829cb612...6300f8f9`, install ID
`60b089c2-7a55-47af-97ba-5daabb835421` passed Windows owner presence, and the
user then approved all eight hooks in the Codex terminal TUI. A direct bounded
current-profile canary proved hook routing, one deterministic `code-reviewer`
unit, a valid Agency header, and finalization. It nevertheless produced zero
native collaboration calls, leaving the delegation at `suggested` and failing
the exact activation graph.

The exact receipt exposed a canary-contract mismatch rather than another trust
failure: the canary user prompt said not to split the unit but did not explicitly
request a sub-agent. Current Codex delegation policy therefore kept the work in
the parent despite the injected one-row Agency plan.

Exact checkpoint `c71ce0a` then built and independently verified as a Windows
wheel/source pair, passed a fresh-wheel installed smoke, refreshed Codex through
an attended transaction, and received renewed eight-hook trust. Its 60-second
current-profile attempt reached routing but the revised prose caused the live
inference planner to create two units (`codebase-onboarding-engineer` and
`code-reviewer`). The proof contract correctly refused that topology. The next
candidate preserves the previously proven indivisible-unit opening and adds one
narrow directive to delegate that complete unit to exactly one sub-agent without
subdivision; it removes the extra parent-execution sentence that was interpreted
as a second planning concern.

A routing-only probe of that next wording at checkpoint `5a26dbe` still produced
two units. The candidate therefore stops treating prose as a topology control.
Only the exact existing-Store canary environment, a native-contract-verified
Codex receipt, and the canonical prompt plus a 32-character lowercase-hex nonce
admit a deterministic fixture. It selects the already-active `code-reviewer`,
requires review-only authority, a review task type, direct-safe context, and no
tools, and produces one selected-only read-only assignment. It does not invoke
the semantic planner, provider, gap hiring, roster mutation, cache, or session
reuse. Ordinary requests remain inference-governed. The route survives durable
preflight replay and records distinct fixture provenance for debugging. Focused
warning-strict canary and activation tests pass; an exact artifact refresh and
live current-profile proof are the remaining gates. Tracker creation remains
pending authorization.

Exact `main` candidate `194d697` is installed as plugin
`0.1.0+codex.edc73d72c476`, bundle `5f7913...`, install ID
`44d37728-83b5-4377-b1f5-a8a9a403ccf3`. The first post-install approval used
stale definitions retained by an already-open Codex process: Codex's own
`hooks/list` reported all eight current entries as `modified`, so the verifier
correctly produced no Store evidence. After a fresh Codex process and renewed
approval, `hooks/list` reported all eight entries enabled and `trusted`. A
zero-token, invalid-model `codex exec` probe without the trust bypass then
persisted exactly one accepted `codex_activation_canary_contract` route, one
`code-reviewer` unit, and a ready preflight before the expected model rejection.
The exact live activation graph remains the next and only current gate.

The bounded live attempt at 02:47 UTC then proved the trusted hooks and the
deterministic route again: trace `019fa69e-79a0-7991-a0a0-f2a97db803e5`
contained exactly one accepted `code-reviewer` unit. It produced no activation
receipt, consumption, worker run, specialist load, or model receipt, and the
verifier correctly closed the run as `canary_failed`. A same-binary controlled
comparison isolated the host failure. The prior `--ephemeral` form took about
73.5 seconds and returned `collab spawn failed: no thread with id`; the same
request without `--ephemeral` completed in about 13.5 seconds and its persisted
parent and child rollouts proved one `spawn_agent`, one `wait_agent`, one
parent-child edge, and child completion. Codex exec JSONL omitted the successful
V2 spawn and emitted a wait with no receivers, so stdout alone cannot establish
the exact native topology.

The source candidate removes `--ephemeral` only from the activation path,
forces `multi_agent_v2`, and requires `fork_turns="none"`. Its verifier reads a
fixed-depth, owner-private, size- and event-bounded parent/child rollout pair,
requires stable identity and exact cardinality/order, rejects nested child
activity, retains only content-free identities and hashes, and reconciles the
lossy stdout projection before the existing Store proof runs. Persisted rollout
proof is an explicit activation-only backend mode: deferred product trials keep
their custom ephemeral response contract, while native-only canaries remain
ephemeral with delegation disabled and matching no-tool developer instructions.
The current focused package passes 156 warning-strict tests, plus lint, format,
and whitespace checks. Installed checkpoint `194d697` does not contain this
correction. No activation or production `GO` is claimed until an exact refreshed
candidate receives attended hook trust and passes one fresh current-profile
canary.

## Approach

Define a deterministic, time-bounded Codex activation probe whose requested
work has one safe isolated unit and one eligible specialist. Recognize only the
closed diagnostic form described above and bypass variable planning without
granting authority or changing ordinary routing. Prove first that
the non-interactive Codex surface exposes the required native delegation tool.
The user-level probe must explicitly request exactly one sub-agent for the
whole unit so the canary remains compatible with Codex's native delegation
policy; indivisibility constrains fanout rather than prohibiting delegation.
Then require exactly one child launch, exact work-unit correlation, pre-LLM
specialist delivery, one-use activation consumption, child completion, parent
finalization, and a valid response header. Reject absent tools, topology drift,
extra children, timeouts, unconsumed grants, parent-only prompt loading, and
uncorrelated evidence. Keep shell, filesystem writes, external services, and
hook-trust bypass disabled.

## Dependencies

ADR-0077 owns behavioral activation proof. ADR-0104 supplies the exact installed
candidate. The host must expose a non-interactive native-child surface that the
canary can invoke safely; if it does not, activation needs a different attended
probe instead of weakening the evidence gate.

## Acceptance

- [x] The canary request deterministically produces exactly one bounded work unit
  and one expected specialist without semantic-plan fanout.
- [ ] Current-profile Codex exposes and invokes the supported native child tool
  without hook-trust bypass, shell access, file writes, or external services.
- [ ] PreToolUse, SubagentStart, PostToolUse, SubagentStop, and Stop evidence is
  correlated to one session, trace, work unit, child, and install identity.
- [ ] The expected specialist prompt is delivered only to the child and its
  one-use activation grant is consumed exactly once.
- [ ] Child completion and parent finalization are accepted, the Agency header
  is valid, and the installation-bound current-profile attestation persists.
- [x] Missing tools, extra delegation, timeout, drift, replay, or incomplete
  evidence fails and closes only the exact canary run.
- [x] Focused tests cover positive, unavailable-tool, timeout, and correlation-
  failure paths before another live attempt.
