---
title: "AR-364: Audit two external review cards into the governed roster"
status: in_progress
category: roadmap
created: 2026-09-01
updated: 2026-09-02
tags: [roster, audit, specialists, review]
related:
  - docs/roadmap/issue-AR-120-normalized-workforce-recruitment-index.md
  - docs/roadmap/issue-AR-336-requalify-the-recruiter-route-for-ordinary-tasks.md
  - docs/roster-audit/batch-ecc-review-review.md
  - THIRD_PARTY_NOTICES.md
supersedes: []
superseded_by: null
type: issue
epic: roster-governance
issue_id: AR-364
priority: p3
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/437
depends_on: []
blocks: []
---

# AR-364: Audit two external review cards into the governed roster

## Problem

The roster has no specialist for two review dimensions with measured
misses in this repo's own history: silent failures (the AR-344/345/346
fail-open family was exactly swallowed-error/dangerous-fallback
defects) and type design (AR-343/AR-351 were representable-illegal-
state defects). Owner reviewed external catalogs 2026-09-01 and
approved auditing in two cards from affaan-m/ECC.

## Current state

Candidate source cards identified: `agents/silent-failure-hunter.md`
and `agents/type-design-analyzer.md` in affaan-m/ECC. Both are small,
read-only review personas with concrete finding rubrics; neither
overlaps an existing card in the index.

## Approach

Run both through the standard contractor audit pipeline exactly like
the existing governed imports: pin source URL + SHA-256 provenance, strip
host-specific boilerplate (their "Prompt Defense Baseline" blocks),
derive authority/context-mode/task-types/capabilities/anti-use
sections, record known audit constraints, and land them as governed
contracts. No shortcut path: if a card fails audit, record why and do
not add it.

## Dependencies

- None; uses the existing audit pipeline.

## Implementation (2026-09-02)

Path A from the owner review: the audit pipeline itself learned a second
source instead of the cards being hand-copied into the primary catalog.

- `docs/roster-audit/audit-manifest.json` is schema 3. A `sources` map names
  every audited checkout (the primary catalog with the `divisions`
  inventory, `ecc` with an `explicit` inventory: only the audited files plus
  `LICENSE` are read, at the pinned revision, from Git blobs rather than the
  working tree). Each audit contract carries `source`; the primary is the
  default.
- `scripts/build_bundled_roster.py` accepts `--source <id>=<path>`
  repeatedly, validates every checkout (origin, revision, license, tracked
  paths), packages one `LICENSE.<id>.txt` per source, and writes
  `source_repository` on every manifest entry so provenance never blurs
  between catalogs. The governed prompt's provenance line uses that
  repository (`agency_runtime/core/roster/semantic_projection.py`).
- `agency_runtime/core/roster/bundled.py` validates `sources` at load,
  resolves each entry's source by repository, and refuses a manifest whose
  primary block does not repeat unchanged under `sources`.
- Batch `docs/roster-audit/batch-ecc-review.json` with its review
  (`batch-ecc-review-review.md`): both cards approved as `review` authority,
  `direct_safe`, no required tools, distinct independence groups. The
  upstream "Prompt Defense Baseline" block and the model/tool pins were
  dropped and recorded as findings on each contract.
- Routing evidence: two curated retrieval probes
  (`agency_runtime/core/evals/full_roster_cases.py`,
  `silent-failure-review` and `type-design-review`) rank each card first
  for its request shape; `tests/test_ecc_review_cards.py` pins the
  provenance, the probes, and that `agent_authority_mismatch` blocks either
  card from a `modify` unit while a `review-report` unit staffs it.
- Third-party notice: `THIRD_PARTY_NOTICES.md` gained the ECC section
  (MIT, Copyright (c) 2026 Affaan Mustafa, revision `ca185ef5`).

Findings attacked while rebuilding (the first rebuild since the roster was
packaged):

- The pinned `division_manifest_sha256` was the CRLF hash of a Windows
  checkout, so an LF checkout could never reproduce the bundle. The builder
  now hashes the Git blob at the pinned revision and the pin was re-set to
  the blob hash (`15136bcf…`); the ECC blobs are read the same way.
- A rebuild published a bundle without `scope_qualifiers.json`, the
  human-curated ADR-0087 enrichment overlay that lives beside the generated
  files. The builder now carries the sidecar overlay forward byte-for-byte
  and `--check` covers it.
- `git ls-files` over a non-catalog repository exceeds the builder's Git
  output bound, so explicit-inventory sources check only the audited paths.
- Roster size 263 -> 265 (280 workers with shadows); the AR-227 recruiter
  index pin moved 264,087 -> 266,264 bytes (+0.82%) with its justification.

## Acceptance

- [x] Both cards exist as governed contracts with pinned provenance
      (source URL + SHA-256 + audit revision) or a recorded audit
      rejection. Evidence: `docs/roster-audit/batch-ecc-review.json`
      (content hashes `e5e2094c…`, `753908aa…`, revision `ca185ef5`, audit
      revision 2) packaged into `agency_runtime/core/roster/data/` with
      `source_repository` on both entries.
- [x] Routing evidence shows each card is reachable by inference for a
      matching request shape (a silent-failure review ask and a type
      design review ask). Evidence: the curated probes above rank each card
      first (`tests/test_full_roster_eval.py`, 9/9 curated cases).
- [x] Neither card can be selected for implementation-authority work
      (review authority only). Evidence:
      `tests/test_ecc_review_cards.py::test_cards_cannot_staff_implementation_authority_work`.
