---
title: "Worklog detail: Install the applicable suite by default"
status: active
category: worklog
created: 2026-07-28
updated: 2026-07-28
tags: [installation, host-integrations, dashboard, windows, security]
related:
  - docs/worklog/README.md
  - docs/roadmap/issue-AR-197-remove-agency-owned-windows-hello.md
  - docs/roadmap/issue-AR-198-install-applicable-suite-by-default.md
  - docs/roadmap/handoffs/issue-AR-198.md
  - docs/decisions/0111-install-the-applicable-suite-by-default.md
supersedes: []
superseded_by: null
type: worklog
commit: f5ca172eb1195358188e7594ef13a8bedc7f986c
short: f5ca172
date: 2026-07-28
pr: null
related_issues:
  - docs/roadmap/issue-AR-197-remove-agency-owned-windows-hello.md
  - docs/roadmap/issue-AR-198-install-applicable-suite-by-default.md
---

# Worklog detail: Install the applicable suite by default

## Purpose

Make the shortest installer command install the useful applicable product:
core Agency state, every detected supported harness, and the dashboard unless
the operator explicitly opts out.

## Approach

Made an omitted host selector trigger OS-aware automatic discovery while
retaining `--all` as an explicit alias and `--agent` as a narrowing selector.
Host transactions now continue independently, dashboard preflight and install
run independently from host work, and JSON distinguishes partial completion.
Removed Agency-owned Windows Hello and routed exact harness refresh through
harness-native lifecycle and trust. Roster rollback and owned host uninstall
remain unavailable. Release verification retains a generic executable and
disguised-PE prohibition.

## Challenges encountered

The first write-free default-install demo discovered Codex and a valid
config-native ZCode integration, but the aggregate reported incomplete because
an obsolete `--all` rule required every host plan to contain an executable.
The rule was removed and regression coverage now accepts successful
config-native plans without weakening per-plan validity.

## Decisions and alternatives

[ADR-0111](../decisions/0111-install-the-applicable-suite-by-default.md)
supersedes the earlier dashboard opt-in choice. Aborting all host work on a
dashboard failure and fabricating integrations for absent harnesses were both
rejected.

## Verification

- 358 focused installer and retired-authority tests passed.
- 324 focused release packaging and canonicalization tests passed.
- A later focused installer rerun passed 116 tests after the ZCode regression
  fix.
- Documentation validation passed for 507 Markdown files.
- Ruff check and format checks passed; staged diff whitespace passed.
- Write-free `agency install --dry-run --json` detected Codex and ZCode, planned
  the dashboard, and returned `ok=true`, `complete=true`.

## Follow-ups

- Run the named fast production spine and dashboard UI suite in the same task.
- Create the same-repository AR-197 and AR-198 tracker items only after explicit
  outward-write authorization.
- Run a fresh Codex-native trust and activation canary in its separately scoped
  package; no live install or service mutation ran here.
