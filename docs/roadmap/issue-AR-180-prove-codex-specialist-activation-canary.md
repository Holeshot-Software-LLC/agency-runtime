---
title: "AR-180: Prove Codex specialist activation in the live canary"
status: open
category: roadmap
created: 2026-07-27
updated: 2026-08-13
tags: [codex, canary, activation, delegation, production-readiness]
related:
  - docs/roadmap/issue-AR-195-separate-codex-canary-parent-and-child-goals.md
  - docs/roadmap/issue-AR-114-guided-codex-hook-activation.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
  - docs/roadmap/issue-AR-182-bind-codex-hook-trust-inventory.md
  - docs/roadmap/issue-AR-185-bind-codex-activation-verification.md
  - docs/roadmap/issue-AR-191-support-codex-v2-hook-identity.md
  - docs/roadmap/issue-AR-192-fail-fast-on-codex-hook-trust-drift.md
  - docs/decisions/0077-prove-codex-activation-behaviorally.md
  - docs/decisions/0104-refresh-existing-codex-through-an-exact-attended-transaction.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0119-separate-native-trust-modes-from-activation-proof.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0158-collect-child-canary-proof-inside-disposable-host-profiles.md
  - docs/decisions/0159-authenticate-codex-plaintext-spawns-from-host-transcripts.md
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
depends_on: [AR-143, AR-182, AR-185, AR-191, AR-192, AR-195, AR-255]
blocks: [AR-119, AR-252, AR-253]
---

# AR-180: Prove Codex specialist activation in the live canary

> **RESTATED 2026-08-12.** The historical canary narrative below records useful
> Codex trust and lifecycle investigations, but its Job B work units, one-use
> grants, Store-only load proof, and response header are not current success
> authority. AR-255 builds inference-owned staffing and sealed host-artifact
> proof. The exact-host preflight below found that Codex 0.147 has a conditional
> host-marked plaintext assignment path, while the current Sol/TUI call remained
> encrypted and the hook payload omitted that marker. AR-180 authenticates and
> uses the supported path, then exact-installs and live-proves one real child on
> TUI, Desktop, and exec. Only the Approach and Acceptance sections as amended
> below govern closure.

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
and whitespace checks. Exact ledger candidate `1a58e5e` then produced a
7,528,969-byte Windows wheel with SHA-256 `e6a94cd9...e43bf5` and an
18,402,728-byte source archive with SHA-256 `7d7d003e...a2209`. Strict Twine and
independent exact-commit verification passed. A fresh Python 3.13 wheel install
passed dependency checks, all eight packaged smoke checks in 43.6 seconds, the
installed activation/native-only option assertions, and every offline routing
gate in 15.1 seconds. The first build attempt correctly rejected the mutable
workspace virtual-environment ACL; the accepted build used an owner-private
release interpreter. Installed checkpoint `194d697` remains untouched and does
not contain this correction. No activation or production `GO` is claimed until
exact candidate `1a58e5e` receives attended refresh and hook trust, then passes
one fresh current-profile canary.

One bounded isolated-profile attempt from the exact wheel was retained as
negative evidence, not retried. Isolated mode intentionally remained on ordinary
semantic planning and selected two units, `finops-engineer` and `code-reviewer`,
for trace `019fa6c9-1e2d-7021-acdd-5a4b08113f85`. The exact-one-child verifier
rejected the invocation with no accepted collaboration, no activation evidence,
no header, and no attestation, then closed its sole active run. The content-free
12,614-byte report has SHA-256
`65981b64cb441e550bcc949ed5dfbdd37c8c7a3201c062091d3215a36c1fae95`.
This does not contradict or exercise the persisted-parent correction: the
nonce-bound deterministic fixture is admitted only by the current-profile
existing-Store verification contract. It confirms that isolated semantic
planning cannot substitute for the final attended proof.

The next trusted current-profile run then routed one exact `code-reviewer` unit
and spawned one child, but the child received only generic identity context and
spawned a grandchild. Primary-source inspection of Codex 0.145 isolated the
boundary: MultiAgentV2's `collaboration.spawn_agent` reaches command hooks as
`collaborationspawn_agent`, while the installed Agency matcher accepted only
`spawn_agent`. AR-191 owns the exact alias, parent-trace, and truthful canary-
projection corrections. Its live-envelope regressions pass; a fresh install
and one bounded current-profile canary remain before activation can be claimed.

AR-191 then landed as exact pushed pair `380f899`/`9a5b37c` and was installed
as Codex plugin `0.1.0+codex.9e970ea1b470`. Two bounded current-profile attempts
produced no Agency Store rows and no activation attestation. A fresh read-only
Codex app-server `hooks/list` inspection in both the repository and private
canary working directories reported the exact eight Agency hooks enabled but
with `trustStatus=modified`. The trusted hashes belonged to definitions held
by a Codex TUI opened before the refresh, so working-directory trust was not the
cause. Codex correctly declined to execute changed commands. AR-192 owns the
Agency-side defect: verification must detect that settled trust state before a
model call. One fresh-TUI approval, an authoritative 8/8 trusted inspection,
and one bounded live canary remain before activation can be claimed.

ADR-0118, ADR-0119, and AR-204 supersede the deterministic-selection part of
that historical candidate. The current source sends every exact canary through
normal workforce inference and requires durable provider-attempt and inferred-
decision receipts. Only after inference selects exactly one eligible worker may
the activation adapter validate and narrow that same worker to the fixed,
package-owned, read-only diagnostic goal needed to recover Codex's encrypted
current-profile child message. It cannot add or substitute a worker; absent or
invalid inference closes the canary as `workforce_inference_failure`. Attended
trust and the explicit invocation-only autonomous bypass are now separate
adapters over the same behavioral proof.

### 2026-08-12 exact-host capability preflight

The read-only preflight identified two exact local runtimes. The PATH-resolved
TUI and exec installation reports Codex `0.147.0`; its Windows native binary has
SHA-256 `935A1911ED2556E4FFCEC995F4886AC2AC425863BA26FED264DF62E30272AD9D`.
Codex Desktop package `26.803.10989.0` uses runtime `0.147.0-alpha.6.6`; that
native binary has SHA-256
`592958896CBFFA154709618476FC9C9BF7FE73957E9A4FC12094C5051B6C69B3`.

The official `rust-v0.147.0` source includes merged upstream change `#35845`.
For `collaboration.spawn_agent`, `send_message`, and `followup_task`, the router
selects `DirectPlaintextMessage` only when the host response item carries
`encrypted_function_args: []`; otherwise delivery remains encrypted. The tagged
stream path records that response item before it queues the tool future. This is
a conditional host capability, not proof that every model or surface emits the
marker.

Current TUI parent `019ff8ee-eb1c-7de3-815d-3deea9eca028`, running Sol through
Codex `0.147.0`, emitted spawn call
`call_4fLyxjPXggCL0L9VWsSXDWr3` with a 1,036-character `gAAAAA...` message and
no `encrypted_function_args` field. The child received encrypted content. This
normal read-only preflight child is evidence that the exact active path is
opaque; it is not an Agency canary and advances no Installed or Live gate.

The documented `PreToolUse` payload supplies `transcript_path`, `turn_id`,
`tool_use_id`, and parsed `tool_input`, and it permits `updatedInput` rewrites.
It does not expose the plaintext marker or internal tool-call source, and the
documented transcript format is explicitly unstable. A plaintext-looking
`tool_input.message` therefore has no authority by itself. Candidate `966845cc`
implements a bounded exact-0.147 scanner, sealed exact-record attestation,
validator-time and output-time revalidation, and an atomic successful-launch
replay guard. Missing, ambiguous, completed, malformed, oversized, linked,
unmarked, or drifted evidence remains unstaffed. Its synthetic marked-host path
and the real current unmarked transcript both pass their expected controls.
This is source and simulation only: independent attack, exact installation, and
host child artifacts remain required before a live Rule-4 measurement.
ADR-0159 keeps rewrite authorization separate from delivery-proof authority.

## Approach

Define a time-bounded Codex activation probe whose requested work has one safe
isolated unit and a compatible multi-card team selected by configured inference.
Require the inferred decision and its provider receipts before narrowing those
same cards to the closed diagnostic execution boundary. Prove first that the
non-interactive Codex surface exposes the required native delegation tool.
The user-level probe must explicitly request exactly one sub-agent for the
whole unit so the canary remains compatible with Codex's native delegation
policy; indivisibility constrains fanout rather than prohibiting delegation.
Then require exactly one child launch and a host-written child artifact that
contains the exact inference-selected card hashes before first child speech.
Correlate parent, child, install, channel, and inference decision without Job B
work units or one-use grants. Reject absent tools, topology drift, extra
children, timeouts, parent-only prompt loading, replay, and uncorrelated or
Agency-only evidence. Keep shell, filesystem writes, and external services
disabled. Run the same proof through either attended native trust or the
explicit per-invocation autonomous bypass without conflating the two.

## Dependencies

ADR-0119 owns behavioral activation proof and its two explicit trust modes.
ADR-0118 requires inference-owned staffing. ADR-0104 supplies the exact
installed candidate, and AR-192 remains the attended-mode trust preflight.
The host must expose a non-interactive native-child surface that the canary can
invoke safely; if it does not, activation needs a different attended probe
instead of weakening the evidence gate.

## Acceptance

- [x] The historical bounded control proved configured inference could select
  exactly one expected specialist with provider and inferred-decision receipts;
  no deterministic fallback chose or substituted it.
- [x] A read-only exact-host preflight inventories the active TUI/exec and
      Desktop runtimes, distinguishes conditional host support from the active
      encrypted path, and advances no Installed or Live claim.
- [x] Exact-version source authentication binds the private rollout, session,
      turn, call, namespace, complete arguments, explicit empty marker, stable
      records, and one successful Store launch; unsupported paths fail open.
- [ ] Current-profile Codex exposes and invokes the supported native child tool
  through attended trust or the explicit autonomous bypass, without shell
  access, file writes, or external services.
- [ ] TUI, Desktop, and exec each produce a host-written child artifact bound to
      the exact parent, child, install, inference decision, and card hashes.
- [ ] The expected specialist cards appear before the child's first speech and
      only in the child context; Store rows and response prose cannot pass.
- [ ] At least one Codex child receives two or more compatible cards selected by
      the same valid inference decision; one child must not be confused with one
      card.
- [ ] Child completion and parent finalization are accepted and the
      installation-bound current-profile attestation persists.
- [x] Missing tools, extra delegation, timeout, drift, replay, or incomplete
  evidence fails and closes only the exact canary run.
- [x] Focused tests cover positive, unavailable-tool, timeout, and correlation-
  failure paths before another live attempt.
