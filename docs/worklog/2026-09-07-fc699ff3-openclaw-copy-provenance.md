---
title: "AR-270 closed installed-copy provenance source checkpoint"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [openclaw, uninstall, provenance]
related:
  - docs/roadmap/issue-AR-270-bind-openclaw-installed-copy-provenance.md
  - docs/roadmap/acceptance/evidence/AR-270-openclaw-copy-provenance-20260907.md
  - docs/decisions/0108-retire-only-owned-host-integrations.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: fc699ff392f75c345064077b039d8fc15615dcf2
short: fc699ff3
date: 2026-09-07
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/752
related_issues:
  - docs/roadmap/issue-AR-270-bind-openclaw-installed-copy-provenance.md
---

# Worklog detail: fix(openclaw): bind complete installed-copy provenance for AR-270

## Purpose

Implement the existing ADR-0108 provenance contract for OpenClaw's separate
installed copy and Agency-owned source. This is an in-progress source package,
not an acceptance verdict or completed native uninstall demonstration.

## Approach

Validate complete managed-source/copy-root/entry coherence, optional exposed
version agreement, exact identity, and absence of conflicting path aliases.
Handle the historical flat report and the current single-plugin inspect envelope.
Retain the joined record in native-state hashing without changing managed-tree
ownership, operator authority, replanning, gateway checks or keep-files behavior.
An authorized read-only native inspect and versioned local schema inspection
established the current shape without loading plugin runtime or changing state.

## Challenges encountered

First independent review identified a High false-absence gap in generic
first-truthy identity extraction. OpenClaw-specific extraction now retains any
exact Agency identity and explicitly refuses conflicting identity aliases at
inventory and inspect admission. Twelve full planner cases and one extraction
case were added to the original thirty-two unrun regressions. The initial High
review is retained; corrected-delta review is pending at this checkpoint.

Static Ruff initially rejected one test's complexity; related cases were grouped
and the final source/test check passed. Initial docs validation correctly required
removing AR-270 from the pre-tracker exception after authorized tracker creation,
and reported the known missing prior merge row. This ledger records that row and
this source commit. No historical proof box was promoted to newly verified.

## Decisions and alternatives

No new ADR or authority policy. A one-alias path relaxation was rejected: partial,
unsafe or conflicting native receipts must remain closed. The native copy stays
host-owned; the unchanged native command retains copied files. Optional schema
versions are checked when exposed, not newly required as universal fields.

## Verification

Scoped Ruff lint and formatting checks and git diff check passed. Metadata check
covered 1274 Markdown documents. Forty-five regression cases were written but
not executed under the owner's explicit code-first/no-tests direction. No CI,
provider call, isolated acceptance, uninstall, disable or owner mutation ran.

## Follow-ups

Normal merge `a9073fe6` integrates published main `cb9e9a50` (PR #748) with no
AR-270 source/test conflict. The worklog append conflict retained both histories
and faithful annotations. Source bytes remain those in `fc699ff3`.

The final narrow independent recheck confirmed the High resolved with no
additional scoped finding and no runtime test execution. Both review passes
remain in the source evidence receipt. Proceed through normal PR publication.
Keep tracker #749 open/in_progress; runtime tests,
isolated acceptance and any mutating/native delivery remain pending under AR-270.

Review checkpoint `6e701219` records both reviews and the deferred gates. Fresh
static/docs checks passed for 1282 Markdown files; policy availability, worklog,
scoped Ruff lint/format and diff checks passed. Strict tracker parity reported
only parallel AR-412 missing locally, pending that separately authorized filing's
integration. This is a temporary publication coordination boundary, not an
AR-270 runtime test result.

Normal merge `9aba5133` integrates AR-280 publication ledger `a574b56d`, retaining
both worklog histories and unchanged AR-270 source/test bytes. The parent
explicitly coordinates the sole parallel AR-412 tracker mismatch through serial
publication; it is not permission to ignore any AR-270 mismatch.

Normal nonclosing PR [#752](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/752)
publishes this source candidate for serial review/merge. The issue remains open;
no accepted-completion or installed native behavior is implied by publication.
