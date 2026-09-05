---
title: "AR-398: A gap turn whose hiring loop outruns the preflight lease leaves no receipt, no hiring case and a run stuck in progress"
status: open
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [workforce, hiring, receipts, observability, staffing, preflight]
related:
  - docs/roadmap/issue-AR-393-declared-gaps-leave-no-hiring-account.md
  - docs/roadmap/issue-AR-378-hiring-failure-records-no-attempt.md
  - docs/roadmap/issue-AR-392-transport-failures-collapse-to-one-code.md
  - docs/roadmap/acceptance/evidence/AR-393-evidence-20260904.txt
  - agency_runtime/core/preflight.py
  - agency_runtime/core/store/preflight.py
  - agency_runtime/core/workforce/hiring.py
supersedes: []
superseded_by: null
type: issue
epic: observability
issue_id: AR-398
priority: p1
tracker_url: null
depends_on: []
blocks: []
---

# AR-398: A gap turn whose hiring loop outruns the preflight lease leaves no receipt, no hiring case and a run stuck in progress

## Problem

A turn that declares `no_safe_sufficient_team` on several units runs the
governed hiring loop once per gap unit: a hiring-generator call, a
hiring-critic call and, for a hire, a security review. Each call is bounded
by its provider timeout, but the loop as a whole is bounded by nothing except
the run's preflight lease, which is `hook_timeout_seconds` (600 s on this
box). When the loop outruns the lease, the failure writer refuses the turn:
`fail_preflight_attempt` (`agency_runtime/core/store/preflight.py`) inserts
the receipt only inside an UPDATE guarded by
`preflight_state = 'in_progress' AND preflight_lease_expires_at >= now`, the
UPDATE matches no row, the function returns `False`, and the only caller
(`agency_runtime/core/preflight.py`, the fail-open close) discards that
return. The host is still handed the fail-open context naming the gap. The
lease renewal loop in `core/preflight.py` serves child routes only; the main
attempt's lease is never extended while hiring runs.

## Current state

Measured 2026-09-05 while re-measuring AR-393 criterion 5, on a copy of the
live store with the real `UserPromptSubmit` hook from venv `c42fb0a5` and the
credential sourced (evidence: `docs/roadmap/acceptance/evidence/AR-393-evidence-20260904.txt`,
section 7). A COBOL z/OS batch request, which no roster card covers,
produced six gap units. The hiring loop made fourteen calls over those units
in 613 s: every generator reply was `hire`, every critic `approved`, every
security review `safe`. The store copy then held, for trace `66d5588b`:

| table | row |
|---|---|
| `preflight_failure_receipts` | none |
| `agent_hiring_cases` | none |
| `runs` | `status active`, `preflight_state 'in_progress'`, attempt token still set, lease expired at `03:56:02Z`, `preflight_result` empty |

The host was told `[Agency staffing failed this turn:
substantive_specialist_unavailable; staffing: no_safe_sufficient_team,
recruiter_abstained]`. Nothing the host could read points at the six hire
proposals or at the reason the turn has no account.

Three receipts of this shape are also candidates for the 42 silent rows
AR-393 counted, but that cannot be established from a receipt that was never
written; the run rows left at `in_progress` with an expired lease are the
durable trace to count.

## Approach

Proposed; not implemented.

1. **The failure writer must not fail silently.** A refused close should be
   recorded somewhere the operator can read: at minimum the caller logs the
   `False` and writes a receipt row through a path that does not require the
   lease, since a fail-open context was delivered and the turn happened.
2. **The hiring loop needs its own budget under the lease.** The loop should
   stop proposing hires when the remaining lease cannot fit another unit, and
   the receipt should say how many gap units were left unproposed and why.
3. **Or the main attempt renews its lease while it works**, the way child
   routes do, so a long but legitimate loop is not cut off by a limit meant
   for a stalled one; the host-side hook timeout still bounds the process.
4. **Count the stuck runs.** `runs` rows at `preflight_state = 'in_progress'`
   with an expired lease and no receipt are this defect's trace; `agency
   doctor` or the dashboard should report them.

## Dependencies

- AR-393 accounted for every declared gap that reaches the receipt; this is
  the case where the receipt itself is lost.

## Acceptance

- [ ] A turn whose fail-open close is refused by the lease guard still leaves
      a receipt naming the refusal, and the run does not stay `in_progress`.
- [ ] The hiring loop stops within the lease, and the receipt names how many
      gap units were left unproposed and why.
- [ ] Replaying the COBOL shape against a store copy produces a receipt with
      a non-empty hiring account and a hiring case per proposed hire.
- [ ] `agency doctor` reports runs left at `in_progress` past their lease.
