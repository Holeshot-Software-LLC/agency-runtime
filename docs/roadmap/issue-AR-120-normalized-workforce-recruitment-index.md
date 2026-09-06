---
title: "AR-120: Normalize and audit the complete workforce recruitment index"
status: open
category: roadmap
created: 2026-07-21
updated: 2026-09-05
tags: [roster, taxonomy, audit, ingestion]
related:
  - docs/roadmap/handoffs/issue-AR-120.md
  - docs/roadmap/AR-404-oldest-first-reconciliation-20260905.md
  - docs/roadmap/issue-AR-86-govern-complete-upstream-roster-lifecycle.md
  - docs/decisions/0066-package-audited-roster-and-sync-quarantined-deltas.md
  - docs/decisions/0083-use-capability-indexed-recall-and-bounded-inference.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/decisions/0080-plan-before-recruiting-from-the-whole-workforce.md
supersedes: []
superseded_by: null
type: issue
epic: routing
issue_id: AR-120
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/133
depends_on: []
blocks: [AR-121, AR-122, AR-125]
---

# AR-120: Normalize and audit the complete workforce recruitment index

## Problem

The roster's rich prompt metadata is not a normalized recruitment ontology, so
near-neighbor roles, stacks, lifecycle phases, tools, and composition rules are
too easy to confuse.

## Current state

**2026-09-05 oldest-first disposition: retain open, partially implemented.**
The normalized index is not missing wholesale. At reviewed main `8b8b594e`,
the following boundaries already exist; do not rebuild them from this old plan.

| Original requirement | Current source/test evidence | Remaining limitation |
|---|---|---|
| Complete normalized worker contracts | `core/workforce/contract.py` projects bounded immutable schema-2 contracts; `core/roster/workforce.py` checks complete current-version lineage, hashes and identity atomically. `tests/test_workforce_contract.py` covers all 265 bundled agents; `tests/test_workforce_lifecycle.py` covers worker/lineage bootstrap and contractor history. | Structural/source evidence is not a new independent semantic review of every worker. |
| Typed relationships | `CompositionContract` distinguishes same-context conflicts, selection exclusivity, requirements and complements; the legacy conflicts field is only a compatibility input. The contract regression verifies conflicts do not become exclusivity. | Existing typed behavior is present; no reason to restore overloaded conflict semantics. |
| Independent prompt/projection checking | Source-bound quarantine/audit/activation authority exists under AR-86. `tests/test_roster_activation_authority.py` rejects tampered or unproven activation. | The separately applied enrichment overlay is slug-keyed; the manual enricher reads metadata, not every full prompt plus an independently recorded review of its resulting projection. Existing audit provenance alone does not prove this universal criterion. |
| Ingestion refresh of contracts/confusion groups/evaluations | The workflow imports deltas into quarantine and uploads review evidence; active versions stay protected. | The job does not run its commented enrichment step or regenerate/publish confusion-group and evaluation artifacts. Its schedule is weekly, not nightly. |

Paths beginning `core/` in this table are under `agency_runtime/`. Fresh focused
contract/lifecycle/overlay/snapshot/audit/activation/adapter package: **219
passed in 15.34s**. The first invocation named a nonexistent test file and ran
no tests; the corrected command above used seven existing modules. No provider
call, upstream fetch, scheduled workflow dispatch or active-roster change ran.

The September 1 owner-approved discoverability addition also remains unmet:
there is no checked-in description-quality/routing-reachability baseline or
regression gate for it. Tests that validate contract shapes and source hashes
must not be relabeled as that gate. All four original acceptance boxes remain
unchanged; no isolated completion verdict is claimed.

### Historical index assessment

All approved prompt bodies have audit provenance, but categories and tool terms
are highly fragmented and `conflicts_with` overloads several distinct meanings.

## Approach

### Remaining bounded plan

1. Preserve the existing contract projector, typed relationships, immutable
   snapshots and quarantine approval boundaries. ADR-0118 governs staffing;
   the old ADR-0080 deterministic-selection design is not revived by index work.
2. Add source/version-bound projection-review evidence and changed-source
   invalidation for enrichment, with separate producer/reviewer identities.
   Do not present structural validation as independent semantic judgment.
3. Add a reviewed, versioned description-quality and routing-reachability
   baseline for the existing owner-approved scope. Regressions must be visible;
   a deliberate baseline change must explain any reduced reachability. This
   offline quality gate must not become a deterministic runtime staffer.
4. Extend the existing **scheduled, non-activating** delta-review path to
   produce proposed contract, confusion-group and evaluation artifacts with
   source identity and review evidence. Preserve approved active versions;
   missing inference/review evidence leaves proposals quarantined. Prove this
   in disposable local fixtures before any separately authorized hosted run.

The daily-to-weekly change was deliberate in `30ab92f9`; this cleanup does not
restore nightly hosted spending or auto-activation. The original nightly
wording below is retained as history, not proof that the missing artifact
refresh is implemented. AR-120 still owns these gaps; no duplicate ticket or
unowned successor is created. Under AR-404, merge this disposition and inspect
AR-125 next while retaining #133 open for the implementation packages above.

### Original proposal and owner-approved addition

Build and version a compact contract for every worker, audit each projection
against its source prompt, normalize vocabularies and typed relationships, and
maintain independent confusion groups and ingestion evaluations.

Scope note (2026-09-01, owner-approved lift): pair the index with a
monotone-decreasing discoverability baseline (pattern from ruflo's
ADR-112 tool-description audit) — every card description meets minimum
guidance/length/uniqueness rules, and a card's routing reachability may
only shrink through a deliberate baseline change, never silently.

## Dependencies

The existing audited roster and quarantine pipeline remain authoritative for
prompt provenance and activation approval.

## Acceptance

- [ ] Every governed worker has a complete normalized recruitment contract.
- [ ] Typed relationships replace overloaded conflict semantics.
- [ ] Every projection is independently checked against its prompt body.
- [ ] Nightly ingestion updates contracts, confusion groups, and evaluations safely.

## AR-256 status correction (2026-08-12)

Reopened because the nightly ingestion criterion remains unimplemented and no
successor owns it. The other index work does not make that gate complete.
