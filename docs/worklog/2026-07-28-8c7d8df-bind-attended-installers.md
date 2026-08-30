---
title: "Worklog detail: Bind attended installers to their owning environment"
status: active
category: worklog
created: 2026-07-28
updated: 2026-07-28
tags: [updates, uv, pip, security, powershell]
related:
  - README.md
  - docs/roadmap/issue-AR-190-make-upgrade-plans-runnable-in-uv-tools.md
  - docs/decisions/0107-resolve-updates-immutably-and-keep-application-attended.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 8c7d8df44aa35d4bb7ab7698abaf0f7b2a93e47b
short: 8c7d8df
date: 2026-07-28
pr: null
related_issues:
  - docs/roadmap/issue-AR-190-make-upgrade-plans-runnable-in-uv-tools.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
---

# Worklog detail: Bind attended installers to their owning environment

## Purpose

Make the immutable attended upgrade plan runnable from Agency Runtime's normal
uv-tool installation without adding pip to that environment or printing a
command that mutates a different tool environment.

## Approach

The planner now binds the running package, interpreter, installer, and refresh
command to one private non-repository environment. A canonical uv receipt,
stable Agency entrypoint identity, safe uv launcher, default tool directory,
and default executable directory must all agree before a uv command is emitted.
Target-changing uv/XDG overrides fail closed. Non-uv environments use pip only
after an isolated bounded capability probe; both pip application and Codex
refresh use Python isolated mode. Windows command text now uses inert
PowerShell literals, while POSIX uv entrypoint symlinks must resolve into the
exact tool prefix. Unavailable plans return a failing CLI exit code.

## Challenges encountered

The first patch checked pip before uv ownership, trusted receipt-shaped lines
outside the uv tool table, and did not prove that either installer was usable.
Independent hostile reviews then found nested-repository executable discovery,
uv target redirection, pip configuration inheritance, POSIX symlink behavior,
PowerShell quoting, and renamed-tool-environment mismatches. Each boundary was
made explicit and covered by focused regression tests before commit.

## Decisions and alternatives

Agency continues to print attended commands rather than self-update. uv exposes
tool-root selection through environment variables rather than an install flag,
so the planner accepts only the proven default target with no target-changing
override and requires unchanged execution in the same owner-controlled
environment. Shell wrappers that mutate environment state and injecting pip
into uv-owned tool environments were rejected.

## Verification

- 65 focused update/CLI tests passed in 2.68 seconds on Windows; one POSIX-only
  symlink test was intentionally skipped.
- Targeted Ruff lint/format and `git diff --check` passed.
- Metadata, policy, and documentation checks passed for 488 Markdown files.
- Two independent read-only rereviews reported no remaining scoped blocker.
- A bounded live probe against this host's uv 0.10.9 environment selected the
  exact tool, prefix, bin directory, Agency entrypoint, and refresh interpreter,
  and rendered valid PowerShell commands.

## Follow-ups

Install this exact commit, run the attended Codex refresh and fresh activation
canary, then record exact success or failure under AR-190 and AR-119. Tracker
creation remains pending explicit outward-write authorization.
