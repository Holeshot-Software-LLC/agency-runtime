---
title: "Bind contractor risk to validated authority"
status: accepted
category: decisions
created: 2026-08-01
updated: 2026-08-01
tags: [contractors, hiring, risk, authority, autonomy]
related:
  - docs/roadmap/issue-AR-219-preserve-exact-multi-unit-product-execution-evidence.md
  - docs/roadmap/handoffs/issue-AR-207.md
  - docs/decisions/0081-compile-contractors-from-governed-structured-contracts.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - agency_runtime/core/workforce/hiring.py
  - agency_runtime/core/workforce/hiring_contract.py
  - tests/test_workforce_dynamic_hiring.py
  - tests/test_workforce_hiring_contract.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0134
type: decision
deciders: [maintainers]
---

# ADR-0134: Bind contractor risk to validated authority

## Context

Exact build `386afca` passed autonomous Codex activation, then its one product
trial failed atomically while filling an inference-declared workforce gap. The
hiring analyst and critic completed, but contractor compilation returned
`high_risk_human_approval_required`; no route, specialist, delegation, header,
or workspace write committed.

The employment-contract model supplied an `external_mutation` Boolean even
though the verified work unit already distinguished `read_only`,
`workspace_write`, and `external_write`. The risk classifier also searched
free-form requirements by substring, so an explicit prohibition such as
`no credential access` could be interpreted as granted credential authority.
Both behaviors conflate bounded local implementation with the external or
high-stakes actions that actually need operator approval.

## Decision

Inference continues to design the role, scope, evidence, and specialist team.
Deterministic enforcement owns only the validated authority boundary:

1. The verified work unit is authoritative for contractor mutation scope.
   Contractor compilation binds `external_mutation=true` exactly when the unit
   is `external_write`; `read_only` and `workspace_write` bind it to false,
   regardless of the model-authored descriptive Boolean.
2. High-risk text markers remain runtime-derived. A marker grants a risk class
   only when at least one occurrence is positively asserted. A narrowly
   recognized explicit prohibition such as `no`, `without`, `never`, or
   `must not` does not grant that authority. Ambiguous text, a later positive
   assertion, or language that removes a restriction remains high risk.
3. Genuine external mutation and positively asserted legal, medical,
   financial, destructive, approval, credential, or offensive-security
   authority continue to require explicit human approval. Autonomous mode does
   not approve or bypass those cases.
4. A rejected high-risk hire emits the generic approval reason plus one
   allowlisted, content-free reason for each derived risk class. Prompts,
   candidate prose, and model responses remain absent from failure receipts.

The work-unit binding caps authority; it does not grant a tool, credential,
network path, external side effect, or filesystem scope. Host and workspace
sandboxes remain independently enforced.

## Consequences

- An inference-designed specialist can be hired autonomously for ordinary work
  inside an already authorized repository or isolated product workspace.
- A model cannot suppress approval for an `external_write` unit by returning a
  false Boolean, and cannot expand a workspace unit into external authority by
  returning a true Boolean.
- Safety requirements can explicitly prohibit credentials or external actions
  without creating the authority they deny.
- If approval is still required, the durable receipt identifies the bounded
  risk class needed for the next decision without retaining private text.
- Inference remains the only source of specialist design and staffing; local
  code enforces authority and rejects unsafe output but does not select a role.

## Alternatives

- **Automatically approve high-risk hires in autonomous mode.** Rejected
  because unattended installation is not authority for legal, credential,
  destructive, external, or other high-stakes action.
- **Trust the model-authored external-mutation Boolean.** Rejected because the
  validated plan already owns that boundary and untrusted text may overstate or
  understate it.
- **Treat every marker substring as granted authority.** Rejected because a
  prohibition would become the capability it is intended to deny.
- **Require human approval for every workspace-writing specialist.** Rejected
  because repository-local implementation is already bounded by user and host
  authority and is not an external side effect.
