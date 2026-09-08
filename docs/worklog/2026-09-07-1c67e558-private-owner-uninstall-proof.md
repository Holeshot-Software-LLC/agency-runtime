---
title: "Prove private owner-CLI host retirement"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [uninstall, evidence, owner-authority, backlog]
related:
  - docs/roadmap/issue-AR-189-add-owned-host-integration-uninstall.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/acceptance/evidence/AR-189-owner-cli-reconciliation-20260907.md
  - docs/decisions/0117-unify-owner-control-authority.md
  - tests/test_host_uninstall_live_boundary.py
supersedes: []
superseded_by: null
type: worklog
commit: 1c67e55844177ae266bf644e18e1f507bb56b960
short: 1c67e558
date: 2026-09-07
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/738
related_issues:
  - docs/roadmap/issue-AR-189-add-owned-host-integration-uninstall.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
---

# Worklog detail: test(uninstall): prove private owner-CLI retirement

## Purpose

Prove that the existing prepared owner-CLI uninstall transaction is reachable
without replacing its authority check, and reconcile AR-189's old presence
wording with accepted ADR-0117. Keep genuine native Windows evidence open.

## Approach

The new private ZCode regression invokes the real CLI parser and handlers for
install, write-free planning, wrong-digest refusal, exact apply and repeat
no-op. Explicit filesystem/launcher seams isolate the fixture; authority,
binding primitives, shared lifecycle locks, replanning, config removal,
retention and journaling remain production code. Seven Agency handlers become
zero, the complete bundle is retained unchanged, and owner configuration,
history and every logical SQLite row are preserved.

The portable receipt retains the original twelve criteria, exact private
operation/plan/journal identities and original source hashes. Only criteria
4/8/12 change obsolete presence terminology. Registry, capsule, AR-404 queue
and reciprocal ADR-0117 links agree that the record remains `in_progress`.

## Challenges encountered

Prior positive unit fixtures often replaced the authority helper, so those
tests alone could not establish real mutation reachability. Product commit
`45be7ea5` had already removed the permanent unavailable error; no runtime fix
was needed. SQLite read-only inspection may materialize WAL/SHM coordination
files; only those exact files are excluded from byte snapshots while all
logical Store contents remain separately compared.

The inherited worktree started at `08fab1c4`. It fast-forwarded safely to
`d28ccc23`, including the faithful AR-184 merge ledger, with all four dirty
draft hashes unchanged. The original 23:14 receipt retains its original IDs;
fresh updated-source runs do not impersonate that older operation.

An initial routing command used a nonexistent package `__main__` and failed
before evaluation. The actual console entry point then passed every gate.

## Decisions and alternatives

Apply existing ADR-0117 owner authority; do not invent a second human-presence
ceremony or restore deleted verifier machinery. Preserve ownership, exact
effects, lock/revalidation and recovery semantics. Do not uninstall any owner
integration merely to obtain a receipt. Do not call config-only fixture proof
an installed-wheel/native-process/unload canary or a Windows result.

## Verification

- Original private proof: host/CLI 68 passes/two native-Windows skips, private
  proof one pass, parser/owner-authority 59 passes; exact output in the receipt.
- Updated `d28ccc23` source: combined focused 127 passes/two native-Windows skips
  in 5.49s; named 29-module production spine 1,085 passes/three skips in 69.11s.
- Dashboard UI 224 passes; repository Ruff lint and all 768 formatting checks
  pass; routing evaluation passes every gate.
- Pre-commit metadata/docs `--require-tracker` pass for 1,238 files, policy and
  whitespace pass, worklog is current for 2,066 substantive commits. This
  immediate narrow ledger records the new substantive commit and is checked
  again before handoff.
- No exhaustive corpus, coverage shards, compatibility matrix, native Windows,
  provider call or full mutation-conformance rerun. The existing conformance
  test module is included in the fresh named spine. Remote parity/publication
  remains parent-coordinated while AR-409's filing is integrated separately.

## Follow-ups

Wait for the parent's explicit publication signal after AR-185/AR-408, then
merge current main normally and publish one PR. Keep `pr: null` until a PR
exists. AR-189 still needs its meaningful native Windows companion-binding,
handle-rename and PowerShell evidence before all-criteria acceptance. AR-190
and AR-191 are separate next packages; no backlog count is reduced here.

## Publication integration

Parent authorized serial AR-189 publication after AR-185/PR736 merged
`00fc1aef` and AR-408/PR737 merged `bfe21d66`. Both PR states and #732 CLOSED
were read back. Merge `de00886131f56529d44f06b34d2d660f8456bb8a`, exact subject
`chore(AR-189): integrate accepted activation and staffing receipts`, resolves
only overlapping documentary histories while preserving all incoming runtime
changes and both frozen acceptance files. The uninstall transaction modules
are byte-identical to `d28ccc23`; the integrated focused package passes 127
with two native-Windows skips in 5.50s. Prior named-spine/UI proof is reused at
that explicit scope rather than claiming AR-408 changed no inference bytes.

The merge's first-parent whitespace check reported existing trailing blank
lines in incoming AR-408 acceptance/capsule files. They were preserved rather
than changing the frozen packet; this branch's actual diff against origin/main
passes whitespace checks. The immediate ledger records both upstream
`bfe21d66` and integration `de008861`. No acceptance candidate is re-frozen,
reviewed again or silently edited.

Publication PR #738 contains the retained AR-189 proof, not a done-state flip
or tracker closure. The normal PR links this exact substantive/integration
history after strict documentation and tracker parity pass.
