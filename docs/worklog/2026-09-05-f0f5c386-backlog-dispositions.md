---
title: "First evidence-led backlog dispositions"
status: active
category: worklog
created: 2026-09-05
updated: 2026-09-05
tags: [backlog, review, supersession]
related:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/AR-404-backlog-dispositions-20260905.md
  - docs/decisions/0219-retire-removed-helper-release-obligations.md
supersedes: []
superseded_by: null
type: worklog
commit: f0f5c386e705dae51e9ac912139692caf53821f5
short: f0f5c386
date: 2026-09-05
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/676
related_issues:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/issue-AR-405-make-directory-identity-regressions-portable.md
---

# Worklog detail: First evidence-led backlog dispositions

## Purpose

Turn the owner's backlog-cleanup request into a bounded semantic review, not a
mass closure or a second implementation of obsolete requirements.

## Approach

Retire AR-132/167/169/267 with explicit successors and original criteria intact.
ADR-0219 reconciles the removed-helper release decisions while retaining the
current paired artifact topology. AR-160 gets an active no-helper checklist and
keeps its old checklist as history. AR-285 gets builder evidence for isolated
verification; no builder-written judgments or fresh native install claims.

## Challenges encountered

All-checked candidates were not necessarily complete: AR-267 names a replaced
release line, AR-337 excludes ZCode, and AR-336 has later scope outside its
checklist. Seven-file triage also found two existing Windows-attribute fixtures
failing on Linux (AR-405, #675). Tests required the existing build-system pins in
the isolated environment. Codex install found current files but still requires
attended hook trust; no trust or OpenClaw restart was bypassed.

## Decisions and alternatives

The supersession record implements prior owner decisions, not new hiring,
packaging or authority policy. In particular it does not remove the Windows
wheel, current release proof, operator approval or historical failed receipts.
Graphify had no repository index; source, canonical decisions and tests supplied
the evidence directly. No implementation agents were delegated.

## Verification

Before this checkpoint: 181 focused installer/registration tests pass, Ruff and
format pass, 138 UI tests pass, metadata/policy/docs checks pass. The wider
focused release run retains 443 passed, two skipped, two failed as AR-405.
Final delivery checkpoint 1d9dea1c: 1004 fast-spine passed/three skipped;
207 focused docs/acceptance/tracker/distribution-verifier tests passed; routing
and all 182 conformance mutations passed with source unchanged. Isolated Codex
verification satisfied three AR-285 criteria and reported two absent; the
Claude attempt produced no judgment because executable namespace trust failed.
The two missing criteria remain unchecked/open. No exhaustive workflow or native
service interruption was requested. PR #676 carries the batch.

## Follow-ups

AR-285 needs trusted-runner wiring citations and a successful changed-precondition
dry-run receipt, not a repeated successful classifier test. AR-404's reviewed
disposition table supplies the next bounded packages and explicitly unreviewed
remainder; AR-405 is not hidden by a green documentation gate.
