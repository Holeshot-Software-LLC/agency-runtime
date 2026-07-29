---
title: "Worklog detail: Bind hired specialists to live gaps"
status: active
category: worklog
created: 2026-07-29
updated: 2026-07-29
tags: [routing, workforce, hiring, codex, model-receipts]
related:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
  - docs/roadmap/handoffs/issue-AR-199.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: a05549f
short: a05549f
date: 2026-07-29
pr: null
related_issues:
  - docs/roadmap/issue-AR-199-restore-codex-workforce-evidence.md
---

# Worklog detail: Bind hired specialists to live gaps

## Purpose

Repair the live Codex path where workforce inference ran but the active roster
had no eligible specialist and the generated contractor failed its own typed
coverage contract. Keep the parent Codex model distinct from Agency's workforce
planner and any specialist execution receipt.

## Approach

The hiring schema now matches the parser's bounds, closed enums, case IDs, and
positive or negative evaluation expectations. After parsing, the runtime binds
the employment contract to the exact causing work unit and current host before
the independent critic and persistence step. Natural-language artifact and tool
descriptions remain contract evidence but are filtered out of normalized routing
identifiers.

The response header correlates the durable routing receipt with the current
model receipt. A matching receipt is labeled as workforce inference; the
host-selected parent model and specialist launch model are reported as separate
evidence scopes and are never inferred from that planner receipt.

## Challenges encountered

The live failure exposed two independent semantic mismatches. Schema-valid
contract prose could exceed parser limits or use values outside closed enums,
and valid human-readable artifacts such as `USB diagnostic report` were being
projected into a workforce field that accepts normalized identifiers only.
Explicit negative safety boundaries also matched the same lexical filter as a
permissive approval bypass.

## Decisions and alternatives

The runtime deterministically adds only the exact causing unit and current host
to the validated contract. It does not derive authority or broaden scope from
free text. Safety language beginning with `do not` or `never` may state an
approval boundary, while permissive `without approval` language remains
rejected.

The parent model is not copied from the Agency planner configuration. Codex
owns that host selection, and Agency reports it as unobservable until the host
provides an authoritative parent receipt.

## Verification

- 177 broadened hiring, workforce, preflight, Store, and header tests passed
  with one expected xfail.
- Ruff check and format passed all 601 Python files.
- Metadata, policy availability, worklog, documentation, and diff checks passed.
- Tracker issue 161 was created with the required `epic:routing` label.

## Follow-ups

Run the named fast production spine, merge the follow-up PR, exact-install the
merge, and capture a fresh USB-style Codex task with contractor, specialist,
delegation, and scoped model evidence.
