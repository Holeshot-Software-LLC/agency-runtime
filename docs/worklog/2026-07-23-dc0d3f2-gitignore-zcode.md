---
title: "Ignore local .zcode editor session state"
status: active
category: worklog
created: 2026-07-23
updated: 2026-07-23
tags: [worklog, tooling, green-main]
related:
  - docs/roadmap/issue-AR-117-parallelize-pr-verification.md
supersedes: []
superseded_by: null
type: worklog
commit: dc0d3f2
short: dc0d3f2
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-117-parallelize-pr-verification.md
---

# Worklog detail: chore(gitignore): ignore local .zcode editor session state

## Purpose

`scripts/verify_docs.py` lists tracked plus untracked-not-ignored
Markdown via `git ls-files --cached --others --exclude-standard` and then
requires YAML front matter on each. The editor-local `.zcode/plans/*.md`
plan-tracking files emitted into the worktree during interactive sessions
were untracked but not ignored, so they surfaced as
missing-front-matter documentation errors and blocked the static
documentation gate on otherwise clean trees.

## Approach

Add `.zcode/` to `.gitignore` alongside the existing editor/tooling-local
entries (`/.codex/`, `.codegraph/`, `.chunkhound/`, `.graphify/`,
`graphify-out/`). This is the same category of state and was the only
such directory not yet ignored.

## Challenges encountered

None beyond confirming that `verify_docs.py` uses
`--exclude-standard`, so a `.gitignore` entry is sufficient and no
scanner code change is required.

## Decisions and alternatives

- Ignoring the directory (not the specific file) was chosen because the
  plan-tracking path is per-session and varies; a directory entry is
  stable.
- Rejected: teaching `verify_docs.py` to hard-code `.zcode`. That would
  duplicate gitignore intent and is unnecessary because
  `--exclude-standard` already honors ignored paths.

## Verification

- `git check-ignore .zcode` -> ignored.
- `python scripts/verify_docs.py` -> the `.zcode/plans/*.md`
  missing-front-matter error no longer appears (the only remaining
  errors are the expected worklog-index staleness for commits not yet
  recorded, resolved by the accompanying ledger commit).

## Follow-ups

None. This is a self-contained hygiene fix.
