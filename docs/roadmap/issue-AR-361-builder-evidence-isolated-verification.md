---
title: "AR-361: Split acceptance into builder evidence and isolated single-check verification"
status: in_progress
category: roadmap
created: 2026-09-01
updated: 2026-09-02
tags: [acceptance, evidence, verification, process]
related:
  - docs/roadmap/AR-256-done-acceptance-reconciliation.md
  - docs/roadmap/issue-AR-235-autonomous-gap-hiring-with-isolated-security-review.md
supersedes: []
superseded_by: null
type: issue
epic: product
issue_id: AR-361
priority: p2
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/434
depends_on: []
blocks: []
---

# AR-361: Split acceptance into builder evidence and isolated single-check verification

## Problem

Acceptance boxes are graded by whoever did the work. The gates only
check that boxes are checked, so "done" can drift from reality until a
manual reconciliation: the 2026-08-30 pass found nine done-docs whose
acceptance did not hold and forced eight tracker reopens (AR-256
records the disposition). Self-grading is the root gap.

## Current state

`verify_docs` refuses done flips with unchecked boxes — a syntactic
guard only. Nothing separates who cites evidence from who judges it,
and no isolated context re-derives a verdict from the evidence.

## Approach

Adopt the two-phase pattern (lifted from LobeHub's acceptance-evidence
tool and verify-agent, owner-approved 2026-09-01), on our existing
isolated-worker machinery:

1. **Builder evidence phase**: after work completes, the builder cites
   concrete evidence per acceptance criterion — command output, file
   paths, receipt ids — and is explicitly forbidden from judging or
   inventing; missing evidence is stated plainly.
2. **Isolated verification phase**: a verifier with a deliberately
   minimal toolset (verdict writeback plus injected read-only
   investigation tools) judges exactly one criterion per run and must
   submit its verdict through the tool to be recorded.

Start with roadmap-doc acceptance (the measured failure), leaving room
to extend to workforce completion criteria later.

## Implementation (2026-09-02)

- Record format and gate: `docs/roadmap/acceptance/README.md` documents the
  per-issue record (`docs/roadmap/acceptance/issue-AR-NN.md`, front matter
  `type: acceptance-verification`, `candidate_commit` pending-or-frozen,
  `evidence_cutoff`, matching `tracker_url`) with its two strict tables.
  `scripts/verify_docs.py::validate_acceptance_verification` runs on every
  gate pass: a `done` issue outside the frozen pre-verification history must
  have exactly one record whose every column-0 criterion carries builder rows
  (closed kinds `command-output`/`file`/`receipt`/`tracker`/`test`/`absent`,
  sources resolved with `git show <candidate>:<path>` and line ranges or
  headings checked) and one `satisfied` verdict bound to the sha256 of the
  candidate, criterion text, and builder rows; `absent`, `contradicted`, a
  missing row, a duplicated verifier run id, a digest mismatch, or a pending
  candidate blocks the flip. Nested checkbox sub-items are rejected for done
  issues so criterion indexes stay stable. Spoofed tables (fenced,
  commented, indented) are invisible.
- Frozen history: `docs/roadmap/pre-verification-history.txt` lists every
  issue already `done`/`wont_do` at the branch point (`9558e806`, newest
  AR-346); `scripts/roadmap_history.py` pins the set by digest
  (`PRE_VERIFICATION_HISTORY_SHA256`) and caps it at
  `PRE_VERIFICATION_MAX_ID = 346`, so the list can only shrink and every
  later done flip needs a record — including the four flips already on main
  from the same day (AR-352, AR-356, AR-360, AR-363), whose records land with
  this change.
- Isolated verifier: `scripts/verify_acceptance.py --issue AR-NN
  --criterion N | --all [--provider claude|codex] [--dry-run]` builds a
  prompt holding exactly one criterion, its own builder rows, and bounded
  excerpts of the cited sources at the candidate, and calls
  `invoke_cli_structured` with a JSON verdict schema. On `claude` the
  candidate tree is exported to a private temporary directory and the CLI
  runs in safe mode with only `Read`, `Grep`, `Glob` (`--restricted
  --add-dir <snapshot>`, no session, no MCP, `dontAsk`); on `codex` the
  existing read-only shell-free sandbox judges the inlined excerpts. The
  verdict is written as the criterion's one `## Verification` row with a
  fresh run id and the recomputed digest; an unavailable verifier or an
  answer outside the closed vocabulary records nothing and exits 2.
- `agency_runtime/core/cli_transport.py::invoke_cli_structured` gained
  bounded `tools`, `max_turns`, and `read_only_roots` options (only the three
  read-only tools, existing absolute directories, codex refuses tools); every
  existing caller stays tool-free and byte-identical. `scripts/docs_metadata.py`
  classifies the new directory.
- Tests: `tests/test_verify_docs_schema.py` (record schema, criteria parsing,
  builder-row and verdict validation, digest binding, duplicate run ids,
  nested criteria, grandfather list semantics, spoofing corpus) and
  `tests/test_verify_acceptance.py` (runner on a committed fixture repository
  with a fake invoker: satisfied recorded, unavailable verifier records
  nothing, absent evidence recorded without a model call, pending candidate
  refused, dry run prints the single-criterion prompt and writes nothing).
- Dogfood: this issue's own record is written after the implementation
  commit exists on `main` (a commit cannot cite its own SHA), so the done
  flip follows in the next docs change; the four already-merged issues were
  verified criterion by criterion through the codex transport.
- First measured behaviour of the gate (2026-09-02, 13 criteria): the
  isolated verifier returned `absent` for seven criteria on the first pass
  and `contradicted` for one on the second. Every objection traced back to a
  criterion whose text named evidence its builder rows did not show (a hash
  literal no test pins, a receipt assertion one flaky test does not make, a
  pytest command offered as evidence, tests named but not cited). The fixes
  were more builder rows and corrected criterion wording, never an edited
  verdict — the digest binding would have exposed that. One criterion
  flipped `satisfied` → `absent` between two runs over identical rows, so a
  verdict is a recorded judgement, not a proof; the run id and reason stay
  in the record for exactly that reason.

## Dependencies

- None; uses existing isolated_only worker plumbing.

## Acceptance

- [ ] A done flip requires per-criterion builder evidence records, not
      just checked boxes.
- [ ] Each criterion's verdict comes from an isolated single-check
      verifier run, recorded with the evidence it judged.
- [ ] A criterion with absent or contradicted evidence fails verification
      and blocks the done flip, covered by regression tests.
