---
title: "Retire the obsolete Codex V2 grant checklist"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [codex, backlog, evidence, governance]
related:
  - docs/roadmap/issue-AR-191-support-codex-v2-hook-identity.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/acceptance/evidence/AR-191-v2-checklist-retirement-20260907.md
  - docs/decisions/0236-retire-obsolete-codex-v2-grant-checklist.md
supersedes: []
superseded_by: null
type: worklog
commit: 49bea737318f05667ab72a9c267fda05a31250c6
short: 49bea737
date: 2026-09-07
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/741
related_issues:
  - docs/roadmap/issue-AR-191-support-codex-v2-hook-identity.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
---

# Worklog detail: docs(backlog): retire obsolete Codex V2 grant checklist

## Purpose

Remove an obsolete July grant-era completion checklist without claiming its
original nine criteria are all satisfied or deleting useful implemented repairs.
AR-255 remains the current inference-owned, host-proven staffing successor.

## Approach

ADR-0236 applies existing ADR-0118/0156/0159 authority to this record retirement.
Set AR-191 to `wont_do`, superseded by AR-255, and preserve its full original
eight checked/one unchecked acceptance block byte-for-byte. Label the old July
implementation account historical. Keep exact aliases, argument preservation,
exit-code fidelity and current-profile existing-Store safeguards.

The receipt maps each criterion to current source, removed history or remaining
live evidence. Registry/queue/capsules and AR-255 reciprocal links agree; remove
AR-191's obsolete AR-180 dependency while retaining AR-255 and every broader
live gate. No production code, test or current runtime authority changes.

## Challenges encountered

Legacy `delegation_activation` tables and a surviving uncalled test helper can
mislead a name-based review into thinking the original grant chain still exists.
`b222414b` explicitly removed issuance/consumption APIs and retained read/attach
history. `7e1b3603` intentionally rejects invalid explicit parent turns instead
of falling back to another live trace. Neither should be restored to make old
checkboxes pass. Current immutable host-delivery receipts remain required.

The first draft's documentation gate found the unindexed AR-184 merge, new ADR
registry omission and reciprocal AR-180 dependency. Fast-forwarding to its
faithful `d28ccc23` ledger and completing the records resolved those errors;
the original failed check is retained in the receipt.

## Decisions and alternatives

Retirement is not acceptance. A September 7 restricted no-bypass Codex one-card
exec canary proves a host-written pre-speech v6 card and accepted v4-bound
finalization, not the removed July grant graph. AR-180 still owns broader
TUI/Desktop, ordinary encrypted-spawn, multi-card and literal child-only
limitations. Do not infer ongoing-parent staffing or fresh hook trust approval.

## Verification

- Fresh focused offline source proof at `c64ce3ce`: 23 passes in 3.47s; exact
  command and stdout in the receipt. Earlier 64 passes in 13.08s is explicitly
  retained summary-only history, not invented raw output.
- Source/tests/scripts remain identical after the `d28ccc23` merge-ledger
  update; no duplicate broad runtime evaluation is needed for records only.
- Metadata and docs `--require-tracker` pass for 1,240 files, policy and
  worklog pass, repository Ruff lint and format767 pass, and diff is clean.
- Original canonical acceptance block compares byte-for-byte equal twice.
  No acceptance verifier, model/native canary, Windows, exhaustive corpus,
  coverage shards or full mutation evaluation runs for this retirement.
- This immediate narrow ledger records the new substantive commit and is
  checked before handoff. Remote parity awaits parent integration of the
  separately filed AR-409; no stale global count or tracker action is claimed.

## Follow-ups

Parent explicitly authorized publication after AR-190/PR740. Normal merge
`889926d5` integrates exact main ledger `f0e38863`, preserving published
AR-185/189/190/408/409 source and records. Five shared documentation conflicts
were resolved as unions of their current records and the AR-191 retirement;
no product, test or script differs from incoming main, and the four frozen
AR-185/190/408/409 acceptance files compare byte-identical.

The identical focused 23-case command in the receipt was rerun on the merged
tree with raw stdout:

```text
.......................                                                  [100%]
23 passed in 3.09s
```

Exit0; repository Ruff passes,770 files formatted, branch diff clean. The
immediate ledger records this integration, preserving every historical subject
and annotation. Metadata/docs/strict tracker parity are checked again before
the PR. No new live canary or installed-artifact claim arises from this merge.

PR #741 carries the retirement through the normal exact-head merge path;
release the serial token to AR-192 after merge/readback. Final metadata/docs
require-tracker pass 1,261 files, worklog indexes 2,104 substantive commits,
and strict tracker parity passes 400 items/two historical PR exclusions.
Current native-child work remains in AR-255 and broader live proof in AR-180;
retiring AR-191 does not close either. Continue with AR-192 after publication.
