---
title: "AR-29: Reconcile LiteLLM model and router evidence"
status: done
category: roadmap
created: 2026-07-15
updated: 2026-07-16
tags: [litellm, models, receipts, observability, dashboard]
related:
  - docs/decisions/0003-response-telemetry-is-model-truth.md
  - docs/decisions/0047-reconcile-litellm-model-and-router-evidence.md
  - docs/roadmap/issue-AR-64-reject-unproven-litellm-router-alias-echoes.md
  - docs/roadmap/issue-AR-78-preserve-litellm-router-when-model-is-unavailable.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: observability
issue_id: AR-29
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/30"
depends_on: []
blocks: [AR-64, AR-78]
---

# AR-29: Reconcile LiteLLM model and router evidence

## Problem

LiteLLM requests may name a router group or alias rather than the deployment
that handled the request. The callback previously preferred the response model
when present, but otherwise could promote an opaque `model_id` or the requested
alias into the Actual Model header. It also did not consume LiteLLM's standard
logging payload, so the router group and routed provider model were not
reconciled consistently across SDK and Proxy callbacks.

## Current state

The runtime stores requested model, model group, provider, and resolved model as
separate fields. Existing callback payload compatibility and bounded metadata
handling are strong, but the trust order does not match current LiteLLM
telemetry and the dashboard does not put the alias, router, and actual model
side by side.

The model-call success/failure callback also closed the correlated Agency turn.
That confused completion of one provider request with completion of the agent
turn and could make the later Stop/finalization callback appear to reuse a
terminal correlation. A later low-fidelity host receipt could then replace a
stronger reconciled LiteLLM receipt merely because it was inserted later.

## Approach

Read the StandardLoggingPayload defensively in both mapping and attribute form.
Keep `model_group` as the LiteLLM router identity. Reconcile the actual model
from successful provider response telemetry first, then
`hidden_params.litellm_model_name`, then a bounded allowlist of deployment
metadata. Retain `model_id` only as opaque operational metadata and never infer
actual execution from the requested alias. Persist failure as unavailable,
render the router explicitly in the Agency header, and expose the separated
fields in dashboard receipt evidence.
Treat model callbacks as receipt events only: finalization or Stop exclusively
owns Agency-turn closure. Select completion receipts by deterministic evidence
quality and authority, using ingestion order only among equal-quality evidence.
Enforce that authority at the Store ingress: only the dedicated LiteLLM callback
path can persist a trusted LiteLLM source, while public and generic callers are
downgraded and every persisted field is normalized, bounded, and safe for
operator surfaces.

## Dependencies

This refines ADR-0003's response-telemetry rule and uses the canonical model
receipt store and six-line evidence header.

## Acceptance

- [x] SDK and Proxy StandardLoggingPayload shapes preserve `model_group` as the router name.
- [x] Genuine provider-reported `response.model` wins when telemetry disagrees;
      an exact requested/router-alias echo yields to distinct routed deployment evidence.
- [x] Standard hidden routed model is the next authoritative fallback.
- [x] Only bounded allowlisted deployment metadata can provide a final fallback.
- [x] Requested aliases and opaque model IDs never become actual-model evidence.
- [x] Failed calls remain unavailable even when success-shaped metadata exists.
- [x] Missing and older LiteLLM payloads degrade to bounded unavailable evidence.
- [x] Agency headers name the reconciled provider/model and LiteLLM router explicitly.
- [x] Dashboard receipts show requested model, router group, actual provider, and actual model separately.
- [x] Model-call callbacks leave the Agency turn active until Stop/finalization owns closure.
- [x] Later unavailable generic receipts cannot mask a concrete reconciled LiteLLM receipt.
- [x] Public source impersonation cannot outrank authentic LiteLLM callback evidence.
- [x] Store ingress bounds counts and fields and rejects unsafe provider metadata.
- [x] Full repository validation and tracker synchronization pass.
