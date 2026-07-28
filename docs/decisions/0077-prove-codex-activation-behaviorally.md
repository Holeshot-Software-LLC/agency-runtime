---
title: "Prove Codex hook activation behaviorally without bypassing trust"
status: accepted
category: decisions
created: 2026-07-20
updated: 2026-07-28
tags: [codex, installation, hooks, trust, canary, security]
related:
  - docs/roadmap/issue-AR-114-guided-codex-hook-activation.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/issue-AR-185-bind-codex-activation-verification.md
  - docs/roadmap/issue-AR-192-fail-fast-on-codex-hook-trust-drift.md
  - docs/decisions/0036-capability-bound-host-canary-attestations.md
  - docs/decisions/0076-bind-isolated-canaries-to-explicit-agency-modes.md
  - README.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0077
type: decision
deciders: [maintainers]
---

# ADR-0077: Prove Codex hook activation behaviorally without bypassing trust

## Context

Codex command hooks require explicit user trust. Agency can install and enable
its native plugin, but registration does not prove that a normal user session
will execute preflight or finalization. The existing isolated canary passes
Codex's explicit trust-bypass flag inside a disposable profile, which proves the
packaged integration but cannot establish real-profile readiness.

Codex exposes the current hook inventory and trust classification through its
read-only app-server `hooks/list` method, but it does not expose a supported
non-interactive trust-grant API. Writing private host state would cross a
security boundary and couple Agency to an undocumented implementation detail.

## Decision

Treat Codex registration and activation as separate installation phases. A
registered and enabled plugin without current-profile evidence has maturity
`activation-required`, and the top-level install remains incomplete.

After installation or refresh, the user closes Codex terminal TUIs that loaded
the prior plugin and approves all Agency hook events through a fresh terminal
TUI's startup review or `/hooks` interface. Codex Desktop's similarly named
`/hooks` screen may manage connector setup and is not equivalent. Agency never
writes the Codex trust store or reproduces its private trust hashes.

Before the resumable `agency install --agent codex --verify-activation` phase
starts any model-backed execution, it calls `hooks/list` through the selected
Codex executable in the exact canary working directory. The bounded, read-only
inspection selects only `agency-preflight@agency-runtime`, requires the
canonical eight events exactly once, and requires every event to be enabled and
`trusted`. Missing, duplicate, unexpected, disabled, untrusted, modified,
malformed, timed-out, or unavailable evidence fails closed with a sanitized
report and no model invocation. Command strings, source paths, unrelated hooks,
and raw app-server output do not enter the report.

Only after that preflight passes does verification start one bounded Codex
execution in the normal user profile. It retains the canary's tool, app, web,
output, timeout, and evidence limits but deliberately omits
`--dangerously-bypass-hook-trust`.

The verifier measures the installed hook and one native child lifecycle; it is
not a workforce-planner quality evaluation. Its exact current-profile child is
therefore recognized only by the two restricted canary environment markers, a
native-contract-verified Codex receipt, and the complete canonical prompt plus
one 32-character lowercase hexadecimal nonce. That closed form projects one
read-only, no-tool `code-reviewer` assignment without provider inference,
caching, session reuse, roster mutation, or gap hiring. The specialist must
already be active and retain its reviewed authority, review task type, and
direct-safe context contract. Any neighboring request or contract drift fails
closed or remains on ordinary inference-governed routing.

Only a successful current-profile invocation with a valid Agency header and
correlated routing and finalization evidence creates the durable attestation
that promotes installation, status, doctor, and dashboard maturity to
`runtime-verified`. The attestation remains bound to the host, platform,
installed bundle, install identifier, and plugin version.

## Consequences

- Installation cannot appear complete when normal Codex turns will skip Agency.
- Hook approval remains an informed user security decision.
- The same install command provides a resumable activation and verification path.
- A changed plugin, host, platform, or install identity invalidates readiness.
- Automation can stage Codex non-interactively but cannot claim readiness without
  an independently established current-profile attestation.
- Verification performs one explicit Codex model invocation only after the
  read-only trust preflight passes; unsettled trust fails before consuming the
  user's configured provider quota.
- Activation evidence is deterministic with respect to one diagnostic unit and
  does not measure or imply semantic workforce-planner quality.

## Alternatives

- **Write Codex's trust state during installation.** Rejected because it bypasses
  informed consent and depends on undocumented private storage.
- **Use the dangerous bypass in the normal profile.** Rejected because it proves
  only that hooks run when security enforcement is disabled.
- **Treat registration as readiness.** Rejected because the observed installation
  produced no routing evidence or response header in a normal turn.
- **Require only a manual assertion.** Rejected because it cannot detect partial,
  changed, or ineffective hook approval.
- **Infer trust failure from a model-backed canary with no hook evidence.**
  Rejected because it spends time and provider quota before checking the
  authoritative host state.
