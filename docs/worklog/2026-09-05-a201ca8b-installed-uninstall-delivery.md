---
title: "Record merged uninstall build and five-host smoke"
status: active
category: worklog
created: 2026-09-05
updated: 2026-09-05
tags: [installation, smoke, delivery, backlog]
related:
  - docs/roadmap/issue-AR-271-accept-stopped-openclaw-uninstall-status.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/acceptance/evidence/AR-271-installed-delivery-20260905.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: a201ca8be34fc5f565b5dd487d83c45469ddfd22
short: a201ca8b
date: 2026-09-05
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/680
related_issues:
  - docs/roadmap/issue-AR-271-accept-stopped-openclaw-uninstall-status.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
---

# Worklog detail: Record merged uninstall build and five-host smoke

## Purpose

Complete the owner's push/main/install/smoke request for the accepted AR-405
and AR-271 fixes without confusing installed contracts with live host sessions.

## Approach

Merge through PR #678/#679, fast-forward main, then install the exact official
5434836e revision into a new owner-private non-editable environment. Back up the
existing launcher before changing its interpreter, retaining the old runtime.
Run the requested all-host integration refresh and deterministic smoke. Retain
the immutable build/projection identity and separately describe each native
host result in the linked evidence. Update AR-404's bounded recovery capsule
and current accounting without changing the historical inventory.

## Challenges encountered

Installation was partial: Codex needs attended hook trust and OpenClaw's gateway
is live. The installer restarted its managed dashboard and reported repairing
fourteen Claude package permissions under recorded consent; both are retained
as actual side effects. No OpenClaw lifecycle command or extra manual repair ran.
Claude readiness passed, but this shell lacks its configured LITELLM_API_KEY;
the presence-only check prevented a predictable failed live run. No credential
was created, printed or changed, and the prior build's live pass was not reused.

An initial documentation-test command used nonexistent test filenames and
collected no tests (exit 4). Repository file discovery corrected the invocation;
the actual three verifier test files then returned 104 passed in 0.69s.

## Decisions and alternatives

This is delivery evidence, not a new architectural decision. Preserve the
existing authority/trust gates and report partial installation. Runtime, tests
and tools are identical to the accepted candidate, so another unchanged slow
spine/conformance run would not add current-source coverage. The source package
already has focused, spine, UI, routing and mutation evidence.

## Verification

Installed version and out-of-checkout VCS metadata agree on full revision
5434836eec4efe70432e50ca3c732dc65c63e209; projection 1d617ca589a2.
Eight installed-source smoke checks passed, zero failures/skips, including all
five generated host contracts. Strict docs, metadata, policy availability,
worklog and tracker validation passed; tracker count 396 plus two PR-history
skips. Canonical counts: 240 done, 93 in_progress, 54 open, 11 wont_do.
No native Windows, exhaustive corpus, coverage shards, interpreter matrix or
workflow dispatch was run.

## Follow-ups

[AR-404](../roadmap/issue-AR-404-evidence-led-backlog-completion.md) remains
in_progress: 146 baseline records plus its coordinator remain unfinished.
Verify AR-298's implemented inspection work, then deliver the real AR-348/349
hiring-safety fixes and explicitly reconcile the scope contradictions. AR-285
retains its distinct historical proof gaps. Native operator/credential gates
remain recorded, not waived by a deterministic five-host smoke pass.
