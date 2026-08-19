---
title: "Pin child-judge providers per canary harness"
status: accepted
category: decisions
created: 2026-08-19
updated: 2026-08-19
tags: [canary, inference, providers, hosts, security, evidence]
related:
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0158-collect-child-canary-proof-inside-disposable-host-profiles.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
  - docs/roadmap/AR-119-vision-loop-status.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/THREAT_MODEL.md
  - agency_runtime/core/canary_judge_provider.py
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/native_child_staffing.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0160
type: decision
deciders: [lkrammes]
---

# ADR-0160: Pin child-judge providers per canary harness

## Context

The AR-119 138-character control was replayed over the same digest-verified
71-agent universe. `codex-subscription` staffed it, while two applied
`claude-subscription` draws deliberately selected nobody at the same 0.75
confidence as the Claude canary's own decline. The child judge was therefore
changing with transport availability: an unconstrained provider chain used
Codex first in the owner profile but fell through to Claude inside the
disposable Claude profile.

The seal still requires a canary-only repair. Changing general child staffing
would alter real turns without evidence or authorization. Re-pinning the
global provider list before every host run would also make a multi-harness
series stateful and easy to misattribute.

## Decision

Agency configuration owns a persistent
`canary.child_judge_provider_by_host` map. Each live Agency canary resolves its
active host to one exact named CLI provider or supported inference profile and
narrows the child judge's provider tuple to that entry only. There is no
provider fallback. The disposable host environment carries the same requested
identity; a missing or ambiguous name, unsupported or unavailable adapter,
unsafe credential endpoint, or config/environment mismatch fails before judge
inference.

The pin applies only while `AGENCY_CANARY_MODE=1`. Ordinary parent and child
staffing continue to use the configured provider chain unchanged. Both the
initial child-judge call and the one funded abstention-repair call receive the
same narrowed configuration.

Canary preparation records the requested provider, and the routing decision
continues to record the provider that actually answered. Proof output projects
both identities independently; matching is observed rather than inferred from
the host driving the session.

For a CLI transport different from the host, the backend copies only that
transport's bounded authentication file into a second owner-private directory
inside the same disposable profile and sets the transport's explicit home.
The directory dies with the profile. No ambient host credential path is
treated as proof of the answering provider.

A map entry may instead name one existing Anthropic-compatible inference
profile. Agency materializes that profile as the canary's sole provider without
adding it to `config.providers`, so the ordinary provider chain is unchanged.
The endpoint must satisfy the existing HTTPS-or-literal-loopback credential
rule and the profile must resolve its configured credential. A name appearing
in both provider and profile namespaces is ambiguous and fails closed.

The map accepts every supported harness key so one owner profile can retain
the intended policy while switching harnesses. The current ZCode/GLM route can
reuse the owner's existing `zcode-recruiter` Anthropic-compatible profile as a
canary-only judge. Historical Store receipts show that profile family answered
ZCode workforce calls, but they predate this candidate and are not canary or
matrix proof. ZCode still has no safe noninteractive canary backend, so the
profile path is locally executable code rather than installed/live evidence.

No provider values are shipped by default and this change does not mutate the
owner's installed configuration. The evidence-backed AR-119 value for a
passing Claude control is currently `claude -> codex-subscription`; choosing
`claude -> claude-subscription` is the explicit falsification path and is
expected to decline unless new measurement reopens the finding.

## Consequences

- A host switch no longer requires reordering or editing the global provider
  chain once the owner has populated the per-harness map.
- Canary results are reproducible against one provider identity and cannot
  silently fall through to a different subscription.
- Cross-provider canaries carry two isolated credential homes but expose
  neither credential in Store or proof output.
- A named inference profile is projected only into the canary's one-provider
  tuple; it does not enter or reorder ordinary `config.providers`.
- General child staffing behavior, the canary work unit, the Rule-9 contract,
  and every AR-119 matrix cell remain unchanged.
- A configured ZCode/GLM profile pin does not manufacture native ZCode proof;
  the missing safe backend keeps installed/live claims closed.

## Alternatives

- **Pin one global provider for every harness.** Rejected because it prevents
  stable host-specific policy and requires operator mutation between runs.
- **Pair every harness with its same-brand provider automatically.** Rejected
  because the measured Claude provider currently declines the exact unit that
  the Codex provider staffs; brand affinity is not staffing evidence.
- **Leave the ordered chain unconstrained.** Rejected because transport
  availability then changes the judge and can reverse a staffing decision.
- **Apply the map to all child staffing.** Rejected because it changes real
  turn behavior outside the authorized canary mitigation.

## Provenance

The provider-conditional measurement and falsification rule are recorded at
the end of `AR-119-vision-loop-status.md`. This decision authorizes only the
local canary mechanism. It provides no installed or live proof and moves no
matrix cell; ADR-0156 remains the proof authority.
