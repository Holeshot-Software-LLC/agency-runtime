---
title: "Prove Codex hook activation behaviorally without bypassing trust"
status: accepted
category: decisions
created: 2026-07-20
updated: 2026-07-20
tags: [codex, installation, hooks, trust, canary, security]
related:
  - docs/roadmap/issue-AR-114-guided-codex-hook-activation.md
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

The user approves all Agency hook events through Codex's `/hooks` interface.
Agency never writes the Codex trust store. The resumable
`agency install --agent codex --verify-activation` phase starts a bounded,
read-only, ephemeral Codex execution in the normal user profile. It retains the
canary's tool, app, web, output, timeout, and evidence limits but deliberately
omits `--dangerously-bypass-hook-trust`.

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

## Alternatives

- **Write Codex's trust state during installation.** Rejected because it bypasses
  informed consent and depends on undocumented private storage.
- **Use the dangerous bypass in the normal profile.** Rejected because it proves
  only that hooks run when security enforcement is disabled.
- **Treat registration as readiness.** Rejected because the observed installation
  produced no routing evidence or response header in a normal turn.
- **Require only a manual assertion.** Rejected because it cannot detect partial,
  changed, or ineffective hook approval.
