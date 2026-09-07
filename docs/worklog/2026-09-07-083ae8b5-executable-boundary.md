---
title: "Verify current executable-isolation surfaces"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [security, executables, evidence, backlog]
related:
  - docs/roadmap/issue-AR-164-reject-repository-ancestor-path-poisoning.md
  - docs/roadmap/acceptance/evidence/AR-164-executable-boundary-20260907.md
  - docs/decisions/0227-bind-executable-isolation-to-current-launch-surfaces.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 083ae8b58378d97c139cfb79debf0a49175b3f92
short: 083ae8b5
date: 2026-09-07
pr: null
related_issues:
  - docs/roadmap/issue-AR-164-reject-repository-ancestor-path-poisoning.md
---

# Worklog detail: Current executable isolation

## Approach and decision

The original ancestor PATH boundary remains implemented. No code/test change
was needed. Job B deliberately deleted the direct host/command worker backends
named in old criterion 5. ADR-0227 explicitly maps that one requirement to
current CLI-provider, installer, dashboard and smoke launch paths; the old
wording and other six criteria remain. This neither restores deleted worker
execution nor relaxes executable trust. Native Windows qualification stays
distinct from portable spelling/PATHEXT simulations; AR-187 retains attended
lifecycle proof. Existing legacy tracker exemption applies.

## Verification

Fresh warning-strict discovery: 38 pass/one native-Windows deselection (0.14s);
six-module current launch package: 129 pass/23 Windows-named deselections (3.39s);
surviving Git/process: 24 pass/three Windows-named deselections (0.63s).
No skips/failures/new suppressions. Source/test/script/gate bytes equal fcdcd6eb;
reuse named spine 1085/three existing skips and same-byte AR-163 DOM 188 results.
Strict docs pass 1180 Markdown files, tracker parity 397 mapped/two historical
PR exceptions, Ruff check/format 766 files, metadata/policy/worklog/diff clean.
No exhaustive dispatch, native Windows, trust bypass or attended host run.

## Follow-ups

Freeze all seven rowsets at 083ae8b5 and require isolated candidate-bound
verdicts before completion. Publish one PR and normal merge, then AR-165.

## Frozen review

48ac7535 freezes all seven rowsets at 083ae8b5 and records the decision's
evidence candidate. Strict docs pass 1181 Markdown files before the freeze.
The review starts only after the clean immediate ledger; no builder verdict.

## First isolated review

At 083ae8b5, criteria 1–4 and 6–7 satisfy. Criterion 5 is absent: the four
current launch excerpts demonstrate integration, but the receipt describes
retired-backend absence without actual Git output. Preserve all seven verdicts
before adding a full candidate tree listing and exact deletion-status output.
No code or requirement change follows from this evidence gap.

## Exact absence correction

2a7c20c5 supplies actual complete candidate-directory and deletion-status
output. Source tree 0ed31de7ec3b387ef463bd087a01eb4907de972c is unchanged;
product/tests/scripts/gate comparison returns zero. Only criterion 5's evidence
citation changes. All first verdicts remain at 6ac3b1aa; no verdict is copied
to the new candidate. Strict docs pass 1182 Markdown files.

8c80dc16 freezes the second record at 2a7c20c5. The source tree still equals
0ed31de7ec3b387ef463bd087a01eb4907de972c. All seven isolated checks run again
after the clean ledger; this is the second and final ordinary review pass.
