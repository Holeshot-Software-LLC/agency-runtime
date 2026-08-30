---
title: "Worklog detail: Preserve setup activation degradation"
status: active
category: worklog
created: 2026-08-25
updated: 2026-08-25
tags: [setup, install, codex, activation, reliability]
related:
  - docs/roadmap/issue-AR-292-classify-setup-activation-pending.md
  - docs/roadmap/issue-AR-290-end-to-end-guided-setup.md
  - docs/roadmap/issue-AR-291-isolate-smoke-runtime-pointers.md
  - agency_runtime/cli/setup_commands.py
  - agency_runtime/cli/install_commands.py
  - README.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: af2f872fc73340f9f11beb2a201cf8ddc8f68632
short: af2f872f
date: 2026-08-25
pr: null
related_issues:
  - docs/roadmap/issue-AR-292-classify-setup-activation-pending.md
  - docs/roadmap/issue-AR-290-end-to-end-guided-setup.md
---

# Worklog detail: Preserve setup activation degradation

## Purpose

Let the guided setup journey distinguish a successful Codex registration that
still needs owner-attended hook trust from a hard installation failure. Keep
standalone `agency install` strict and ensure setup never hides a failed host,
dashboard, activation verification, or runtime projection.

## Approach

Add an internal setup-only install request bit rather than a public installer
flag. The installer returns degraded exit 2 only when every selected mutation
is `ok`, no runtime drift remains, and the sole incomplete result exactly
matches registered Codex with attended `activation_required` state and the
canonical trust surface and resume command. Setup labels that result
`activation-pending`, continues through doctor and deterministic smoke, and
preserves degradation from any accepted stage in its final exit code.

## Challenges encountered

The strict installer intentionally reduces both incomplete activation and hard
mutation failure to nonzero for standalone use, so the setup orchestrator could
not safely reinterpret exit 1 by itself. The bounded solution performs the
distinction where the structured host, dashboard, activation, and drift facts
still exist, while making the relaxed exit available only to the internal setup
namespace.

Installed AR-291 recovery removed the earlier foreign-package drift and made
this independent classification issue observable. The initial regression run
failed in the five expected locations before implementation.

## Decisions and alternatives

Changing public `agency install` completion semantics was rejected because
current-profile activation remains part of its strict contract. Treating any
`ok` but incomplete host as degraded was rejected because it would mask staged-
but-unregistered adapters. Post-hoc setup inference from doctor output was also
rejected because healthy prior state could conceal a failed current mutation.

## Verification

- All 58 focused setup and install-command tests passed with warnings as errors.
- The broader setup, install, native installer, doctor, parser, and dashboard-
  service regression group passed all 299 tests with warnings as errors.
- Explicit negative coverage keeps dashboard failure, failed host mutation,
  staged/unregistered host, activation verification failure, and runtime drift
  at exit 1.
- Full Ruff lint and format checks passed across 693 files.
- Metadata, policy availability, worklog, and documentation checks passed for
  815 Markdown files; `git diff --check` passed.

## Follow-ups

Install this exact checkpoint and repeat the real guided setup. Codex trust and
fresh-session activation verification remain attended operator actions. Tracker
creation, push, PR, tag, and release remain separately unauthorized.
