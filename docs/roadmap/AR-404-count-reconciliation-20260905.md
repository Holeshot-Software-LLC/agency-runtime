---
title: "AR-404 tracker versus historical-record count reconciliation"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [backlog, reconciliation, evidence]
related:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/AR-404-backlog-dispositions-20260905.md
  - docs/roadmap/pre-tracker-history.txt
  - scripts/verify_tracker.py
supersedes: []
superseded_by: null
---

# AR-404 tracker versus historical-record count reconciliation

## Starting snapshot

The owner correctly observed 43 open tracker issues. At main e4255836, the
147 figure meant local front matter, not 147 demonstrated defects:

| Population | Count | Meaning |
|---|---:|---|
| Open same-repository tracker issues | 43 | All map to local unfinished records |
| Unfinished pre-tracker local records without tracker issues | 104 | Historical reconciliation queue, not automatically current work |
| Total local open/in_progress records | 147 | 54 open plus 93 in_progress |

There were 398 canonical issue documents: 240 done, 11 wont_do, and 147
unfinished. The complete tracker join contains 264 AR issues, the legacy
exemption set contains 132 records of all statuses, and two old records use
PR history. No unmatched non-exempt unfinished issue was found.

`verify_tracker.py` reports the number of local records checked, including
exemptions; its previous "396 roadmap items" success line does not mean
396 actual tracker issues. Its join and exemption rules explain the count.

Reproduction: use the verifier's front_matter and shared pre-tracker parser,
join with `gh issue list --state all --limit 1000 --json number,title,state,url`,
and partition local status open/in_progress into mapped OPEN and unmapped
pre-tracker entries. The two groups are disjoint and total 147. These are
snapshot counts; later closures or filings are reported as deltas.

## Owner-directed relevance review

The owner asked to close verified completed work, assess each agent-written
ticket against the current product rather than treating it as a specification,
and leave Windows-specific implementation/verification for the Windows machine.
The product goal is reliable and reasonably fast inference-owned staffing,
hiring, host execution and truthful operations. Old priorities and checkbox
counts are not authority to recreate obsolete designs or require unrelated
certification on each small feature.

Current code, focused tests, actual supported evidence and accepted successor
decisions determine the disposition. Completed work closes after its applicable
verification; superseded or irrelevant proposals retire with a reason; genuine
remaining gaps keep a bounded issue. Do not manufacture a live or Windows pass.

## First concrete checks

- AR-149's claimed keep-alive request-ID defect is already fixed. Current real
  HTTP tests prove separate request identities and correlated Store/log/error
  boundaries. Its old complete-corpus closure condition is superseded by
  ADR-0105, not an instruction to rerun exhaustive integration.
- AR-152's source uses one stable container listener and semantic buttons; its
  fifty-render soak passes. The separate aggregate UI coverage command fails
  the current function floor and is recorded once as AR-406 (#682), not
  misreported as a listener regression or a green coverage result.
- AR-139's historical 263,168-byte ceiling is not the current product budget:
  later explicit audits cover required setup/prompt UI and the current test
  enforces 378 KiB. Review its successor chain before any retirement; do not
  remove required UI to recover an obsolete ceiling.
- AR-129/130's documents already describe implemented security fixes, but
  include platform proof. Their Windows obligations stay with the owner.

These checks support the owner's suspicion of stale bookkeeping. They do not
yet establish that a majority of all 104 historical records are complete.
