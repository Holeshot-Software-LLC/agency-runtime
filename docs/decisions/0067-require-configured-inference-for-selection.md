---
title: "Require configured inference for every specialist-selection decision"
status: accepted
category: decisions
created: 2026-07-18
updated: 2026-07-18
tags: [routing, inference, providers, degradation, litellm]
related:
  - docs/roadmap/issue-AR-84-bounded-semantic-agent-cards.md
  - docs/roadmap/issue-AR-85-state-aware-turn-classification.md
  - docs/decisions/0008-ordered-provider-fallback.md
  - docs/decisions/0035-authoritative-bounded-provider-chain.md
  - docs/decisions/0047-reconcile-litellm-model-and-router-evidence.md
  - docs/worklog/README.md
supersedes: [docs/decisions/0008-ordered-provider-fallback.md]
superseded_by: null
id: ADR-0067
type: decision
deciders: [maintainers]
---

# ADR-0067: Require configured inference for every specialist-selection decision

## Context

Deterministic retrieval is a useful no-provider mode and candidate generator,
but it cannot satisfy the configured semantic-routing contract if a high lexical
score is allowed to bypass the judge. Silent deterministic fallback also makes a
provider outage look like an inferred selection and defeats reliable comparison
of routing quality.

## Decision

Whenever state-aware classification sets `selection_required` and any inference
provider or key is configured, inference is mandatory. This includes
conversation, new intent, revision, and rerouted continuation. Pure
acknowledgements and exact deterministic runtime controls do not require
inference.

Apply hard security, host, tool, platform, permission, and activation filters
before inference. Build a bounded candidate union from lexical, semantic,
category, capability, diversity, and hard-negative retrieval over the entire
enabled roster. Send only structured bounded cards, never full specialist
prompts.

Try the configured provider chain in declared order and record every bounded
attempt. If every configured path fails, do not label the deterministic result
as inferred. Use only the resident managers or an explicitly configured degraded
policy, and expose the degraded state through receipts, doctor, CLI, dashboard,
and the final evidence boundary. With no configured inference, deterministic
routing remains an explicit supported mode.

Preserve requested alias, provider, authoritative actual model, and LiteLLM
router or model-group identity as separate fields. A router alias is never an
actual-model receipt.

## Consequences

- Configured inference cannot be bypassed by lexical confidence.
- Provider failure is visible and reproducible instead of silently changing the
  selection algorithm.
- No-key installations remain usable in an honestly labeled deterministic mode.
- Conversation can explicitly abstain after semantic consideration instead of
  being treated as a generic bypass.
- Provider health becomes part of release and operational evidence.

## Alternatives

- Keep deterministic token ranking after configured providers fail. Rejected
  because it silently violates the operator's inference requirement.
- Let a lexical-confidence threshold skip inference. Rejected because lexical
  overlap is not a semantic or compatibility proof.
- Require inference even when no provider is configured. Rejected because
  offline portability remains a supported, visibly deterministic mode.
