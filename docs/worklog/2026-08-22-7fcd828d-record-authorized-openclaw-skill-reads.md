---
title: "Record authorized OpenClaw native skill reads"
status: active
category: worklog
created: 2026-08-22
updated: 2026-08-22
tags: [openclaw, skills, evidence, security]
related:
  - docs/decisions/0165-authorize-openclaw-native-skill-reads-from-inventory.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-273-model-agnostic-structured-inference-profiles.md
  - docs/roadmap/issue-AR-274-record-openclaw-native-skill-reads.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 7fcd828d2a20d85562bee73cbea9f538985107ac
short: 7fcd828d
date: 2026-08-22
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-273-model-agnostic-structured-inference-profiles.md
  - docs/roadmap/issue-AR-274-record-openclaw-native-skill-reads.md
---

# Worklog detail: Record authorized OpenClaw native skill reads

## Purpose

OpenClaw `2026.7.1-2` loads a native skill by reading its `SKILL.md`, but the
generated Agency bridge discarded the path and the generic adapter recognized
only `skill_view`. A real Weather read therefore produced neither a
`skills_loaded` Store row nor a skill name in the authoritative header. This
commit makes the supported native event observable without treating arbitrary
file reads as skill evidence.

## Approach

The generated OpenClaw payload allowlist now retains only the bounded `path`
field needed by the observed native event. The OpenClaw adapter accepts only an
absolute, non-traversal `SKILL.md` candidate with a bounded skill key, then
runs fixed argv `openclaw skills info <key> --json` through the repository's
owned, bounded native-command helper and OpenClaw-only least-privilege
environment. It normalizes the read to canonical `skill_view` only when name,
key, file path, base directory, eligibility, model visibility, and every
disable/block flag match exactly. Canonical Store failure detection remains the
last gate, so a failed native read records nothing.

## Challenges encountered

The expected-red run produced the two intended failures: missing projected
`path` and no adapter skill row. The first post-repair run then exposed a
traversal-shaped path that was ultimately rejected by inventory mismatch but
still launched the inventory command. A stricter lexical prefilter now rejects
`.` and `..` path components before any subprocess. The new continuation
worktree also lacked a local Ruff executable; the unchanged retry was avoided
and the already-installed Ruff binary from the clean predecessor worktree ran
the checks without a download.

## Decisions and alternatives

Plain suffix matching, recording every OpenClaw `read`, trusting model prose,
and weakening Agency's existing filesystem/executable trust checks were
rejected because each could manufacture skill evidence. Requiring a nonexistent
OpenClaw `skill_view` tool was also rejected: the audited host version exposes
native `read` plus an authoritative `skills info --json` inventory. The repair
uses that inventory as authorization while keeping Store/final-header checks
unchanged.

## Verification

- Expected-red: 2 exact failures in `/tmp/ar274-openclaw-native-skill-read-red.xml`.
- Focused green: 22 passed, 1 skipped in `/tmp/ar274-openclaw-native-skill-read-green-v3.xml`.
- Affected warning-strict slice: 453 passed, 1 skipped in `/tmp/ar274-openclaw-skill-read-affected-slice.xml`.
- Installed inventory helper smoke returned only `weather`.
- Focused Ruff lint/format, documentation validation, metadata, policy/worklog, and `git diff --check` passed.

## Follow-ups

- [AR-274](../roadmap/issue-AR-274-record-openclaw-native-skill-reads.md): reinstall Agency only into OpenClaw and prove a genuinely different skill in a fresh session.
- [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md): run the distinct substantive OpenClaw work unit after skill evidence passes; do not move a Rule-4 matrix cell.
