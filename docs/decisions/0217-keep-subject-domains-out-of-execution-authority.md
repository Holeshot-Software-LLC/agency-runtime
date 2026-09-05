---
title: "Keep subject domains out of execution authority"
status: accepted
category: decisions
created: 2026-09-05
updated: 2026-09-05
tags: [staffing, reliability]
related:
  - docs/roadmap/issue-AR-402-separate-subject-domains-from-execution-eligibility.md
  - docs/decisions/0198-waive-the-typed-requirements-the-roster-declares-but-cannot-serve.md
  - docs/decisions/0201-constrain-the-planner-domains-to-what-the-roster-serves.md
  - docs/decisions/0213-the-verifier-judges-safety-retrieval-judges-fit.md
  - docs/worklog/README.md
supersedes: 
  - docs/decisions/0201-constrain-the-planner-domains-to-what-the-roster-serves.md
  - docs/decisions/0213-the-verifier-judges-safety-retrieval-judges-fit.md
superseded_by: null
id: ADR-0217
type: decision
deciders: [owner]
---

# ADR-0217: Keep subject domains out of execution authority

## Context

The independent review reproduced a backend implementation unit restricted to
Roblox's systems scripter in the supplied 293-worker snapshot. The packaged
282-worker roster reproduces it. API platform and backend architects have audited
planning authority; recalling either cannot make it an implementer. ADR-0213's
retrieval-only explanation was incomplete.

Category-derived domain labels are not complete, mutually exclusive work
contracts. Eligibility and conjunctive coverage made them unintended staffing
authority. ADR-0201 propagated this assumption into a planner veto.

## Decision

Keep domains on units, contracts, planner taxonomy and recruiter cards. Domain
overlap still informs bounded candidate recall. It is not an eligibility veto,
mandatory team-coverage token or planner retry trigger. Recruit faithful fit from
actual outcomes, scope and exclusions; inference may declare a genuine gap.

Retain audited authority, capabilities, artifacts, lifecycle, tools, platforms,
explicit stack declarations, not-for exclusions, composition and independent
review. Never upgrade a planner to modification authority to solve an example.
An explicitly requested domain-derived capability remains a capability
requirement; the domain label alone does not request it.

Read historical domain-axis receipts unchanged. ADR-0198's waiver mechanics still
apply to actual execution requirements; its domain examples remain historical.

## Consequences

Implementation: `47ab9fce`, `e9d8ecea` and `af366dd8`, indexed in the worklog registry.

General software implementers are not excluded solely for lacking the backend
category. No worker is deterministically selected. An inapt model nomination is
still possible and live quality must be measured separately. Representative
package-roster tests cover backend, frontend, operations, review and five hosts.
domains_by_artifact_kind describes supply, not impossibility.

## Alternatives

Reclassifying planners invents authority. A backend-only alias leaves the same
incomplete-taxonomy failure for the next subject. Lowering confidence or removing
independent review does not fix eligibility.
