---
title: "AR-181 smoke reconciliation recovery capsule"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [handoff, smoke, testing, performance, windows]
related:
  - docs/roadmap/issue-AR-181-bound-all-host-smoke-launcher-preparation.md
  - docs/roadmap/acceptance/evidence/AR-181-smoke-reconciliation-20260907.md
  - docs/decisions/0026-explicit-test-home-boundaries.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-181
branch: codex/ar181-smoke-reconciliation
evidence_commit: 24eede12fc80c24e7f1dd72f32514cdf591ab2a9
minimum_ledger_commit: 8ca6e240b507b11254944e0af76d32eb0e820555
hard_checkpoint_percent: 50
tracker_url: null
---

# AR-181 smoke reconciliation recovery capsule

## checkpoint

This records-only package follows AR-180 PR #730/main24eede12; its merge
ledger is the metadata checkpoint. AR-407's exact artifact receipt is now on
main. Normal PR/merge publication retains AR-181 in_progress with its explicit
Windows timing hold. No runtime changes or acceptance verdicts are introduced.

## completed-evidence

- Original implementation `c625bc76` prepares one attested launcher lazily and
  reuses it across selected generated hosts; failure is invocation-local.
- Both original parent source and current source share one explicit temporary
  home/Store with host-specific bundle paths. ADR-0026 requires isolation from
  the operator home, not one distinct home per host. Original criterion 2 is
  explicitly corrected to this existing contract; original wording is retained
  in the receipt and is not marked satisfied.
- Focused Linux checks: 37 passed, two Windows-labelled cases deselected in
  6.59 seconds. Actual existing installed aggregate CLI: eight pass, zero fail,
  zero skip, 4.25 seconds; all five generated host contracts ran.
- One in-memory failure probe: one preparation, zero generated calls, three
  typed host failures, no skip. This is not a committed new test.
- AR-407's separately built exact wheel passed packaged smoke and aggregate
  smoke (eight pass, zero fail/skip, 5.09 seconds). Its receipt owns the build
  commit, wheel/sdist digests and fresh-environment commands.

## exact-blocker

`waiting_for_operator` for the explicit native Windows timing criterion: the
owner reserved Windows work for a Windows machine. Linux timing is not that
proof. Criterion 2 is explicitly reconciled to existing ADR-0026; no runtime
behavior or authority changed. No verifier verdict exists in this package and
AR-181 remains `in_progress`.

## same-task-continuity

Use the portable receipt rather than re-running completed Linux checks. After
the smallest durable publication checkpoint, continue non-Windows backlog work
in the same task. The cumulative 50-percent telemetry rule does not require an
empty commit, a fresh canary, a new task, or waiting for context to rise.

## next-bounded-work-package

Publish this reconciled record and continue AR-183/184 Linux producer evidence.
Before future completion, have the owner capture the exact-wheel
native Windows aggregate result against the under-two-minute criterion. Do not
dispatch or retry that Windows work unattended on this Linux machine.

## verification

The evidence receipt contains the executed focused command and installed
aggregate command/output projection. For these documentation-only changes:

```bash
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
git diff --check
```

No new runtime test or model call is required merely to publish this receipt.
AR-407's linked evidence is present in this publication's main ancestry.

## constraints

- Preserve the original criterion-2 wording as provenance; the canonical
  replacement is explicit. No invented `satisfied` verdict or `done` flip.
- No native Windows timing claim from Linux; historical Windows 43.9 seconds
  stays historical, and installed 4.25 seconds is not fresh-wheel 5.09 seconds.
- Generated-host contracts are not native model-turn, header, injection, trust,
  or activation proof. No operator-profile hash audit is claimed.
- No runtime edits, new policy, provider call, native registration or real-host
  uninstall. Parent publishes the documented reconciliation and ledger.
