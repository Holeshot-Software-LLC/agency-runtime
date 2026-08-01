---
title: "AR-211: Bound immutable commit resolution responses"
status: in_progress
category: roadmap
created: 2026-07-31
updated: 2026-07-31
tags: [release, update, github, security, installation]
related:
  - docs/roadmap/issue-AR-188-add-immutable-update-discovery.md
  - docs/roadmap/issue-AR-190-make-upgrade-plans-runnable-in-uv-tools.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/decisions/0107-resolve-updates-immutably-and-keep-application-attended.md
  - docs/worklog/README.md
  - CHANGELOG.md
supersedes: []
superseded_by: null
type: issue
epic: release
issue_id: AR-211
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/206
depends_on: []
blocks: []
---

# AR-211: Bound immutable commit resolution responses

## Problem

The attended upgrade planner requests GitHub's complete commit projection even
though it consumes only `sha` and `html_url`. Merge commit `207b150` produces
more than the authenticated transport's 256 KiB response limit. The valid
authenticated response is therefore rejected, and the private repository's
anonymous HTTPS fallback returns 404, which the CLI misleadingly reports as an
unpublished ref. This blocks the README's canonical exact-install path.

## Current state

PR 204 merged and GitHub publishes `207b15066185bf67c7164792e87453fe29b089f7`
at `main`. The installed `584b949` planner rejects both that exact ref and a
refreshed main-channel lookup without mutating the environment. Invoking its
authenticated transport directly proves `GitHub CLI update response exceeded
its size limit`. The same commit request with `per_page=1` returns the exact
SHA in 6,635 UTF-8 bytes, well inside the unchanged bound. The repaired
candidate resolves `207b150` with `error: null`, `status: different_target`,
and `mutation_performed: false`; its editable checkout correctly refuses to
claim an installed-tool mutation command. Focused update and CLI tests pass 66
cases with one skip; Ruff, formatting, diff checks, and validation of 596
Markdown documents also pass. The exact local merge spine passes 639
warning-strict Python tests with six skips, 110 dashboard tests, and every
isolated routing gate; Ruff remains green across 604 files.

## Approach

1. Append GitHub's supported `per_page=1` query to every commit-resolution
   request while preserving ref normalization and exact SHA/URL validation.
2. Keep the existing total timeout, response-size, JSON-depth, node-count,
   origin, and immutable-target controls unchanged.
3. Add focused coverage for main, version, and full-SHA selectors so unused
   commit-file expansion cannot return.
4. Prove the candidate resolves `207b150` without mutation, then review, merge,
   bootstrap the exact repaired build, and prove the canonical installed-tool
   planner can emit an attended plan.

## Dependencies

ADR-0107 owns immutable resolution and attended external mutation. AR-204 owns
the integrated README story whose exact-install checkpoint exposed this defect.

## Acceptance

- [x] Main, version, and full-SHA commit requests limit unused file pagination
  without weakening exact identity validation.
- [x] Focused update-service, CLI-upgrade, formatting, documentation, and diff
  checks pass.
- [x] The candidate resolves merge commit `207b150` with
  `mutation_performed=false`; an editable checkout remains unable to claim an
  installed-tool mutation command.
- [ ] The repair is independently reviewed, merged, exact-installed, and the
  repaired installed planner resolves its own immutable merge commit.
