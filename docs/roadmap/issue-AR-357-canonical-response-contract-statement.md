---
title: "AR-357: State the response contract once per turn instead of via superseding snapshots"
status: open
category: roadmap
created: 2026-09-01
updated: 2026-09-01
tags: [finalization, header-contract, hooks, claude]
related:
  - docs/roadmap/issue-AR-344-codex-fail-open-stop-terminal-exit.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-357
priority: p2
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/427
depends_on: []
blocks: []
---

# AR-357: State the response contract once per turn instead of via superseding snapshots

## Problem

What a parent must emit to finalize a turn arrives as a stream of
superseding per-tool-observation header snapshots plus an implicit
finalization contract, and the two can drift within one turn. Measured
2026-09-01 on the claude host: a substantive final response that
followed the latest snapshot verbatim was withheld with
`response_invalid, missing: ["evidence_verification"]` (16:12:05Z,
trace `9ff53c55-…`), while adjacent turns using the same pattern were
accepted — the operator lost the turn's summary and the model cannot
tell which requirement it missed.

## Current state

Failure receipt captured; not yet root-caused. The turn-scoped
expectation lives in N superseding snapshots; the finalization
verifier's actual requirement set is not stated anywhere the model can
read it.

Second measured case (2026-09-01 evening, same session): a turn in
which no header snapshot was delivered at all — the model reused the
latest prior-turn snapshot verbatim, and the final response was
withheld with "did not satisfy the exact current-turn evidence header
contract. The turn is terminal; no correction was requested or
accepted." The operator lost that turn's summary and re-asked the
question. This adds the no-snapshot-delivered shape to the defect: the
contract can demand a snapshot the turn never provided.

## Approach

Investigate the claude-adapter verifier first (the miss may be
adapter-side rather than contract-side). Then deliver one canonical
statement of the finalization requirements per turn — in the same
delivery as the kernel or as the single authoritative snapshot — and
make later snapshots strictly additive observations, never a second
contract. A rejected response's `missing` list should name
requirements the model was actually told about.

## Dependencies

- The AR-344 answers (terminal-lifecycle vs bound-response conflation)
  as prior art on this surface.

## Acceptance

- [ ] The finalization requirements for a turn are stated once,
      canonically, in-context; snapshots no longer carry divergent
      expectations.
- [ ] The 2026-09-01 withheld-response case is root-caused and covered
      by a regression test.
- [ ] A rejection's `missing` list only names requirements that were
      delivered to the model in that turn.
