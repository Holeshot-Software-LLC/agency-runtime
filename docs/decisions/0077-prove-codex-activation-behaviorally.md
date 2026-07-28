---
title: "Prove Codex hook activation behaviorally without bypassing trust"
status: accepted
category: decisions
created: 2026-07-20
updated: 2026-07-27
tags: [codex, installation, hooks, trust, canary, security]
related:
  - docs/roadmap/issue-AR-114-guided-codex-hook-activation.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/issue-AR-185-bind-codex-activation-verification.md
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

Codex does not expose a stable installer API for granting or reading hook trust.
Writing private host state would cross a security boundary and couple Agency to
an undocumented implementation detail.

## Decision

Treat Codex registration and activation as separate installation phases. A
registered and enabled plugin without current-profile evidence has maturity
`activation-required`, and the top-level install remains incomplete.

The user approves all Agency hook events through the Codex terminal TUI's
startup hook review or `/hooks` interface. Codex Desktop's similarly named
`/hooks` screen may manage connector setup and is not equivalent. Agency never
writes the Codex trust store or reproduces its private trust hashes. The resumable
`agency install --agent codex --verify-activation` phase starts a bounded,
read-only, ephemeral Codex execution in the normal user profile. It retains the
canary's tool, app, web, output, timeout, and evidence limits but deliberately
omits `--dangerously-bypass-hook-trust`.

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
- Verification performs one explicit Codex model invocation and can consume the
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
