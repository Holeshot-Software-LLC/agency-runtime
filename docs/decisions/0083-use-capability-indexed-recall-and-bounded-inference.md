---
title: "Use capability-indexed recall and bounded inference"
status: accepted
category: decisions
created: 2026-07-22
updated: 2026-07-22
tags: [routing, inference, capabilities, caching, evaluation]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-120-normalized-workforce-recruitment-index.md
  - docs/roadmap/issue-AR-121-inference-planning-and-staffing.md
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
supersedes: [docs/decisions/0080-plan-before-recruiting-from-the-whole-workforce.md]
superseded_by: null
id: ADR-0083
type: decision
deciders: [maintainers]
---

# ADR-0083: Use capability-indexed recall and bounded inference

## Context

Asking one model to inspect the complete workforce while also planning and
staffing a request creates large prompts, long synchronous waits, and weak
separation between semantic judgment and policy authority. Keyword-only
routing is fast but misses decisive intent, near-neighbor distinctions, and
complementary teams. Agency must make inference useful without making every
turn slower or allowing a model to activate an unsafe worker.

## Decision

Maintain a controlled, versioned capability vocabulary in every employee and
contractor contract. Use one compact inference call to translate a new intent
into typed work units and required capability IDs without naming workers. Run
recall across the complete local contract index, apply hard eligibility and
composition rules, and accept a complete high-confidence, high-margin team
deterministically.

Fast mode abstains when that local result is ambiguous. Balanced and strict
modes may ask a recruiter model to resolve the ambiguity, but only over bounded
typed shortlists and exact contract cards produced by whole-roster recall. The
model cannot nominate an ID outside those cards or override deterministic
staffing verification. Strict mode adds an independent veto-only critic.

Cache the immutable roster projection, intent plan, candidate set, recruiter
result, and parent-unit assignment only under identities that include every
input and governing version relevant to that layer. A contractor must pass the
same compiled contract, capability index, audit, version, conflict, activation,
and receipt path as an employee before its first probationary use.

Pin the source-visible upstream Agency Agents revision and gate superiority
claims on held-out matched comparisons. Inference is a mechanism; measurable
selection safety, specialist coverage, latency, activation, and outcome lift
are the product evidence.

## Consequences

The common inferred route becomes one small model call plus local indexed work,
while hard cases retain semantic recruitment. Selection remains explainable and
safe because inference proposes intent or ordering but never grants authority.
The system must maintain capability metadata, complete cache identities,
shortlist-recall tests, adversarial recruiter tests, and a reproducible upstream
baseline. Taxonomy or contract changes invalidate more cached evidence, which is
intentional.

## Alternatives

Sending the full roster to every recruiter call was rejected because latency
and context size grow with the workforce. Pure keyword or embedding selection
was rejected because retrieval similarity is not sufficient staffing evidence.
Allowing a recruiter to discover arbitrary IDs outside its cards was rejected
because it bypasses recall provenance and prompt bounds. Treating contractors
as a faster, weaker contract type was rejected because it would turn gaps into
a governance bypass.
