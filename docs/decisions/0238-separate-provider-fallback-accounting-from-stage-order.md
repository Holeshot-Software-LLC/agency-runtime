---
title: "Separate provider fallback accounting from inference-stage order"
status: accepted
category: decisions
created: 2026-09-08
updated: 2026-09-08
tags: [receipts, telemetry, inference, compatibility]
related:
  - docs/roadmap/issue-AR-284-disambiguate-provider-fallback-receipts.md
  - docs/decisions/0047-reconcile-litellm-model-and-router-evidence.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0238
type: decision
deciders: []
---

# ADR-0238: Separate provider fallback accounting from inference-stage order

## Context

The atomic-ready, direct-workforce and committed-hiring receipt writers used
flattened list order as `attempted_fallbacks`. Independent planner, recruiter
and critic stages therefore appeared to fall back even on one profile. Their
list also includes semantic repairs and pre-request refusals. Neither list
order, configured provider-slot order nor provider-name changes establish how
many prior provider entries actually made calls.

## Decision

Stamp content-free `metadata_version: 1` at each covered structured
workforce/hiring provider-chain invocation boundary. Keep these concepts
separate in existing durable attempt JSON:

| Field | Meaning |
|---|---|
| `stage` | Existing closed inference-stage identity. |
| `ordinal` | One-based position in that projected attempt list; not a fallback count. |
| `provider_chain_index` | Zero-based configured entry slot in this chain invocation. |
| `provider_call_attempted` | True for a dispatch, false for a known pre-request refusal, null when the transport does not say. |
| `provider_fallback_count` | Number of earlier distinct entries in this same chain known to have dispatched; null when this call or a prior entry is unknown, or this entry was not attempted. |

Each stage/chain starts its own accounting. Semantic retries within an entry
do not increment the fallback count. A complete structured answer proves a
dispatch even if semantic validation rejects it. A named transport failure
uses its explicit `call_attempted` fact. A legacy bare `None` does not prove
dispatch; spending budget alone cannot establish that fact. Unknown prior
entries keep a later count unknown. A subsequent known dispatch of that same
entry resolves whether the entry ever dispatched; a later refusal does not.

All three covered wrapper writers persist only the strictly validated stamped
count into `model_receipts.attempted_fallbacks`; absent or malformed accounting
means SQL NULL, never a fabricated zero or flattened ordinal. The existing
column is already nullable; there is no schema migration. Preserve explicit
None only on generic wrapper ingress. Omitted legacy defaults and host or
authoritative LiteLLM callback normalization retain their existing behavior.
Callback counts describe that callback's provider/router scope, not an inferred
whole-turn workforce total.

Optional companion metadata is emitted only when version, closed stage, exact
types, bounds and internal relationships validate. Old JSON projections remain
fixed points; no field is backfilled into historical receipts. Historical
wrapper SQL integers without the companion metadata retain their original
bytes and ambiguous legacy meaning. Consumers must not relabel them as proven
fallback counts merely because a newer runtime can read them. SQL NULL means
unknown; a current non-null wrapper claim needs its versioned companion.

## Consequences

- Single-profile multi-stage staffing records zero known fallbacks per stage,
  while true dispatched provider-chain progression records its own count.
- Refusals, repairs and unavailable dispatch telemetry remain distinguishable.
- Existing SQLite readers retain unknown as null without schema changes.
- Uninstrumented/legacy attempt producers yield unknown wrapper counts until
  they provide the same explicit metadata; absence is not proof of zero calls.
- New metadata is bounded diagnostic evidence, not provider/model authority,
  staffing permission, a new fallback policy or a changed retry/call budget.
- Historical raw SQL alone remains insufficient to disambiguate old wrapper
  values. No repair rewrites historical observations.

## Alternatives

- Count flattened attempts or changes in provider names: rejected because
  stages, repairs and configured route changes are not provider fallbacks.
- Equate configured slot with actual fallback count: rejected because earlier
  entries may be refused without dispatch.
- Turn unknown into zero: rejected because absence would become false proof.
- Add new SQL columns and migrate old counts: unnecessary for this bounded
  repair; the column accepts NULL and existing companion JSON carries the
  separate stage, ordinal and provenance. Old counts cannot be recovered by
  migration without evidence that was never recorded.
