---
title: "AR-196 superseded recovery capsule"
status: active
category: roadmap
created: 2026-07-28
updated: 2026-07-30
tags: [handoff, dashboard, service, security, superseded]
related:
  - docs/roadmap/issue-AR-196-authorize-prepared-dashboard-service-repair.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/decisions/0117-unify-owner-control-authority.md
  - docs/roadmap/issue-AR-194-inspect-owned-service-runtimes-across-python-versions.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-196
branch: codex/ar-203-readme-story-final-proof
evidence_commit: ffec1027ad18dee38469e710cd38049c00e3c9e2
minimum_ledger_commit: fe68f86e36a2f2d82ae681d02c67ae5d4a0e6a06
hard_checkpoint_percent: 50
tracker_url: null
---

# AR-196 superseded recovery capsule

Bounded recovery projection for the former dashboard-service presence blocker.
The [canonical issue](../issue-AR-196-authorize-prepared-dashboard-service-repair.md)
is `wont_do` and superseded by
[AR-204](../issue-AR-204-reconcile-readme-story-contract.md).

## checkpoint

- ADR-0117 establishes normal owner CLI and owner-dashboard authority without a
  second human-presence ceremony.
- Commit `ffec102` deletes the unavailable verifier and its parser bindings.
- `dashboard service open` retains its owned-service inspection, repair, start,
  restart, authentication-descriptor, and postcondition behavior.
- The old multi-resource verifier design and its unsafe rollback claims remain
  rejected historical evidence; they are not a pending implementation plan.

## completed-evidence

- The dashboard-service test suite passed 77 tests after owner dispatch was
  restored.
- Owner CLI, parser, prepared transaction, host-control, security, native
  installer, upgrade, and release groups passed 708 tests with one platform
  skip in the AR-204 package.
- Model-facing hook, MCP, broker, generated-host, and restricted brokerage
  identities remain read-only; only normal owner execution changed authority.

## exact-blocker

AR-196 has no remaining independent blocker because its authority premise was
superseded. AR-204 owns the remaining dashboard work: owner-only server mutation
dispatch, broker denial, restored UI controls, authenticated render, reversible
write, and exact restoration proof.

## same-task-continuity

Do not resume the Windows Hello or presence-verifier design from this capsule.
Continue the active README-story goal through AR-204's bounded packages.

## next-bounded-work-package

No AR-196 package remains. Resume the AR-204 dashboard owner/broker and UI
package recorded in `docs/roadmap/handoffs/issue-AR-204.md`.

## verification

~~~text
python -m pytest tests/test_cli_owner_authority.py tests/test_dashboard_service.py -q -W error
python scripts/verify_docs.py
git diff --check
~~~

## constraints

- Preserve owned-service identity, locking, bounded rollback, and postcondition
  checks; removing the human distinction does not remove transaction safety.
- Do not widen broker, hook, MCP, generated-host, or restricted brokerage
  mutation authority.
- Preserve the owner-untracked analysis draft and `uv.lock`.
