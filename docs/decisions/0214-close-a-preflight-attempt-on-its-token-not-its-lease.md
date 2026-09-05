---
title: "Close a preflight attempt on its token, not its lease, and bound hiring by the lease"
status: accepted
category: decisions
created: 2026-09-05
updated: 2026-09-05
tags: [preflight, lifecycle, receipts, hiring, observability]
related:
  - docs/roadmap/issue-AR-398-a-gap-turn-that-outruns-its-lease-leaves-no-receipt.md
  - docs/roadmap/issue-AR-393-declared-gaps-leave-no-hiring-account.md
  - docs/roadmap/issue-AR-378-hiring-failure-records-no-attempt.md
  - docs/decisions/0210-account-for-every-declared-gap.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0214
type: decision
deciders: [owner]
---

# ADR-0214: Close a preflight attempt on its token, not its lease, and bound hiring by the lease

## Status

**Accepted 2026-09-05.** Implements AR-398 approach items 1 and 2 as measured
on the COBOL gap turn of 2026-09-05T03:46Z.

## Context

A preflight attempt holds a lease derived from the host's hook timeout (595 s
from the budget plus the store's margin, 600 s in the runs table here). The fail-open close, `Store.fail_preflight_attempt`, wrote its receipt
only inside an UPDATE that required the lease to be unexpired, and its caller
discarded the `False` it returned. The governed hiring loop, meanwhile, ran
one round per declared gap unit with no bound but the number of units. A
turn that declared six gaps ran fifteen hiring requests over 613 s, every
proposal `hire` and every critic `approved`, outran the lease, and vanished:
no receipt, no hiring case, a run left `in_progress`, while the host was told
`no_safe_sufficient_team`. The live store already held eleven runs in that
shape.

The lease clause protected nothing the token did not already protect. When an
expired attempt is recovered, `_recover_expired_preflight` replaces the token,
so a close whose token still matches is the only writer the run has; refusing
it lost the account and kept the run open.

## Decision

1. **The close is guarded by the attempt token alone.** `fail_preflight_attempt`
   still requires the run to be active, in progress and held by the given
   token. An expired lease no longer refuses the close; it is recorded as the
   receipt's lifecycle invariant, `preflight_lease_expired_before_close`,
   unless the failure already carries a stronger invariant. A token that no
   longer matches means another attempt owns the run and writes its own
   account; the close returns `False` and touches nothing.
2. **The hiring loop is bounded by the lease.** `run_preflight` binds the
   lease instant to the route request; `_run_gap_hiring` starts another round
   only when the time left fits the longer of one hiring provider deadline and
   the longest round measured this turn, plus a ten-second margin for the
   close. Units left unproposed carry `hiring_lease_budget_exhausted` on their
   hiring event, so the receipt says how many were skipped and why.
3. **Schema 49.** The receipt table's invariant CHECK gains the new code; a
   store built before this version is rebuilt in place, rows copied verbatim
   and its triggers recreated, the first time it is opened.

## Consequences

- Every fail-open turn leaves a receipt while its attempt still holds the run,
  however long its inference took. A late close is visible as such.
- A gap turn no longer spends more time than its lease on hiring; the units it
  did not reach are named rather than silently dropped. Their pending hires
  are not lost either: the loop stops before the lease, so the close that
  carries them still lands.
- The refused-close case that remains (a recovered attempt) is not silent: the
  recovering attempt writes the turn's receipt or ready result itself.
- Stores upgrade once; the rebuild copies every existing receipt.

## Rejected alternatives

- **Renew the main attempt's lease while hiring runs.** Keeps a stalled turn
  alive as long as it likes, which is what the lease exists to prevent, and
  would still exceed the host's own hook timeout.
- **Write an orphan receipt when the token no longer matches.** The store's
  scope trigger binds receipts to runs that are `preflight_failed`; a run
  owned by another attempt is not, and weakening that invariant for a case
  the new owner already accounts for buys nothing.
- **Bound each round by the worst case, `hiring_call_budget` calls at the
  provider deadline.** Six calls at 60 s each would forbid a second round on
  every 600 s lease; measured rounds cost about 100 s, so the floor is one
  provider deadline and the bar rises with what the turn has actually seen.
