---
title: "Admit only exact content-free Codex host notices"
status: accepted
category: decisions
created: 2026-07-31
updated: 2026-07-31
tags: [codex, security, evidence, diagnostics, canary]
related:
  - docs/roadmap/issue-AR-208-preserve-codex-host-notices-in-product-evidence.md
  - docs/roadmap/issue-AR-207-persist-preflight-delegation-failure-diagnostics.md
  - docs/decisions/0116-bind-product-trials-to-exact-workspace-proof.md
  - docs/decisions/0119-separate-native-trust-modes-from-activation-proof.md
  - docs/worklog/2026-07-31-fb797f9-codex-host-notice-classification.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0125
type: decision
deciders: [maintainers]
---

# ADR-0125: Admit only exact content-free Codex host notices

## Context

Codex 0.146 serializes several non-critical startup notices as completed JSONL
items whose item type is `error`. Treating every such item as product work or a
runtime error makes a clean specialist lifecycle fail even when the host exits
successfully. Ignoring all `error` items would create the opposite and more
dangerous failure: real hook, configuration, reroute, deprecation, or host
errors could disappear from activation and product proof.

The first repair recognized two Codex-owned messages by their complete text and
projected only semantic types and a count. The activation contract retained
those fields, but the product collaboration projection silently omitted them.
The combined behavior is a durable security, evidence, and operating boundary.

## Decision

Treat every Codex JSONL `error` item as unexpected and fatal by default. Admit a
host notice only when its complete message exactly equals one entry in a fixed
source-controlled mapping. Prefixes, suffixes, regular expressions,
case-folding, fuzzy matching, and message-shape inference do not establish a
match.

Map each accepted message to one fixed content-free notice type. Persist only a
canonical unique list of those allowlisted types and the total occurrence count;
never persist the original message. Validate the same shape at every activation
and product projection boundary. The type list must contain only fixed allowed
values in canonical order, and the non-boolean count must be non-negative,
bounded by the Codex rollout line ceiling, and consistent with the number of
unique types. Any missing, malformed, unknown, duplicate, inconsistent, or
unbounded value fails the projection closed.

The supported hook-trust bypass remains evidence of `bypassed`, never
`trusted`. Adding or changing an admitted message requires a dedicated issue,
focused near-match regression, and review of this decision boundary.

## Consequences

- Known Codex host notices no longer masquerade as parent product tools or
  unexplained runtime errors.
- Activation and product reports preserve the same traceable content-free
  notice facts.
- A changed Codex spelling fails closed until it is reviewed explicitly.
- Raw host text cannot leak through the persisted proof surface.
- Exact matching carries maintenance cost when Codex changes wording, but that
  cost is visible and safer than heuristic error suppression.

## Alternatives

- **Ignore every completed `error` item when Codex exits zero.** Rejected
  because exit success does not prove every emitted error is harmless.
- **Match warning prefixes or regular expressions.** Rejected because a nearby
  real failure could be admitted by an overbroad expression.
- **Keep notices only in activation evidence.** Rejected because a product
  report would then conceal host conditions observed during its own execution.
- **Persist the complete message for later diagnosis.** Rejected because fixed
  semantic types are sufficient and keep the evidence boundary content-free.
