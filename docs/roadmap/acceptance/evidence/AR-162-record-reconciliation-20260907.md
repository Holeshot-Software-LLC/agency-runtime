---
title: "AR-162 historical comparison and governed tracker reconciliation"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [evidence, ci, governance, acceptance]
related:
  - docs/roadmap/issue-AR-162-collapse-unavailable-codeql-fanout.md
  - docs/roadmap/issue-AR-347-reconcile-tracker-parity-backlog.md
  - docs/roadmap/acceptance/evidence/AR-162-codeql-capability-20260907.md
  - docs/decisions/0226-gate-codeql-savings-claims-on-matched-measurements.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
---

# AR-162: Record reconciliation after first review

## Preserved first review

Commit c456b6bda147bff619dc9bcb3efc81265b26aecb preserves all first verdicts at
candidate fcdcd6eb: 1–6 and 8 satisfied; 7 absent (no prior configuration cited)
and 9 absent (old criterion requires remote parity). No verdict is converted to
satisfied by the builder. This correction changes no workflow or test bytes.
The first evidence receipt remains unchanged at its original path.

## Historical event and concurrency comparison

The fan-out implementation entered in f64ba1e54b76cf4c05a7a6a290028f316467bd07,
whose stat identifies the CodeQL workflow change. Its preceding source is
92d56e49fc64de0911f82ab9f964780fdb23ba20. Read both that exact Git blob and the
repaired fcdcd6ebee6b522281d23a49d2bdc5f95c6649f9 blob; parse YAML and compare
only the event and concurrency projections. The comparison asserts equality
and exits zero: Historical event/concurrency comparison: identical.

| Revision | Entire codeql.yml SHA-256 |
|---|---|
| 92d56e49fc64de0911f82ab9f964780fdb23ba20 (before fan-out change) | 06b1ba06ce7cb969591d7d38d3fd413383c9647bc50af2a4fa7ebf1f4da97863 |
| fcdcd6ebee6b522281d23a49d2bdc5f95c6649f9 (repaired capability) | dd01b73be15fd00fe73231f2d1f2f5391dff74ed2a48e1fdca7def450bbbd545 |

The full files differ intentionally. Both selected projections are exactly:

    {
      "events": {
        "push": {"branches": ["main"]},
        "pull_request": {"branches": ["main"]},
        "schedule": [{"cron": "23 7 * * 1"}],
        "workflow_dispatch": null
      },
      "concurrency": {
        "group": "codeql-${{ github.workflow }}-${{ github.ref }}",
        "cancel-in-progress": true
      }
    }

Reproduce by reading git show <full-SHA>:.github/workflows/codeql.yml for each
listed commit, parsing with yaml.safe_load, and comparing the True key (PyYAML's
YAML-1.1 spelling of on) plus concurrency. This is source/configuration parity,
not a hosted run or runtime speed measurement. The unchanged current contract
tests explicitly assert the same values.

## Governed tracker scope

AR-347's owner-authorized reconciliation established pre-tracker-history.txt
as a versioned, self-shrinking exemption honored by both strict checks. AR-162
is explicitly listed at line 39; its canonical tracker_url is null and no
tracker has been created. The list is invalid if an entry later gains a URL,
so mapping requires removal from the exemption and exact ordinary parity.

The original ninth criterion demanded post-creation URL/state evidence even
though this record remains unmapped. ADR-0226 explicitly adopts the existing
AR-347 rule for the ninth criterion, preserving the old text and absent verdict.
This is not a retroactive claim that remote-parity proof exists. No duplicate
tracker is created or unrelated numbered GitHub issue closed.

## Verification and unchanged implementation

The workflow and tests are byte-identical to fcdcd6eb, verified by Git diff;
all runtime/scripts are also unchanged. Reuse the original receipt's 210-pass/
five-deselected final workflow package and 1085-pass/three-existing-skip spine.
The first 65-case focus, current calling-identity API read and no-savings
boundary remain evidence of their stated scope, not new executions.

Fresh validation with the pending second-review record: metadata and strict
documentation checks pass for 1174 Markdown files. Strict tracker validation
passes for 397 mapped roadmap items with two historical PR exceptions. Git diff
against fcdcd6eb is empty for .github, tests, scripts and agency_runtime; whitespace
checks pass. No tracker is created or state changed by these read-only checks.
All nine criteria require new isolated verdicts at the new frozen candidate.
