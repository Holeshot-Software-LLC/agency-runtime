---
title: "AR-235 active recovery capsule"
status: active
category: roadmap
created: 2026-08-04
updated: 2026-08-04
tags: [handoff, workforce, hiring, security, routing, recovery]
related:
  - docs/roadmap/issue-AR-235-autonomous-gap-hiring-with-isolated-security-review.md
  - docs/roadmap/reference-workforce-inference-stages.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-122-contractor-hiring-and-lifecycle.md
  - docs/roadmap/issue-AR-228-eliminate-deterministic-staffing-authority.md
  - agency_runtime/core/workforce/hiring.py
  - agency_runtime/core/workforce/hiring_contract.py
  - agency_runtime/core/workforce/inference.py
  - agency_runtime/core/config_defaults.yaml
  - agency_runtime/core/structured_provider.py
  - agency_runtime/dashboard/dashboard-render.js
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-235
branch: main
evidence_commit: e87747d8ab5991080487de4c55773c54d3bc59ee
minimum_ledger_commit: e87747d8ab5991080487de4c55773c54d3bc59ee
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/244
---

# AR-235 active recovery capsule

Bounded current-state projection for the autonomous gap-hiring task.
The [canonical issue](../issue-AR-235-autonomous-gap-hiring-with-isolated-security-review.md)
owns the full acceptance history; the
[inference-stages reference](../reference-workforce-inference-stages.md)
owns the per-stage prompt, schema, profile, and receipt inventory.

## checkpoint

- Planning pair exists in the working tree only: the AR-235 issue,
  the reference doc, and the registry updates are uncommitted at
  `e87747d`. Branch `main` resolves to that commit; no substantive
  AR-235 code, test, or config change has landed yet.
- Tracker is live: [issue #244](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/244)
  carries the full AR-235 body, the `epic:routing` label, and
  matches the local planning record. No `gh` auth handling was
  needed — `gh` is already installed and authenticated as
  `lkrammes` with the `repo` scope, token in the OS keyring.
- One local helper file remains in the working tree:
  `scripts/strip-frontmatter.ps1` (a one-shot PowerShell helper
  used to extract the issue body). Hard-delete was policy-blocked;
  it stays until the next-bounded-work-package or operator cleanup.
- The pre-existing worklog drift (`e87747d`, `4928a87` not matching
  history) was present before AR-235; not introduced by this work.

## completed-evidence

- The current code shape is documented from `hiring.py` and
  `hiring_contract.py`: deterministic regex risk classifier at
  `hiring_contract.py:68-80`; amend-first wiring ready but gated
  by `allow_existing_worker_amendment: bool = False` at
  `hiring.py:1430`; bounded repair mechanics for JSON in
  `_invoke` and the `hiring-repair`/`hiring-repair-critic`
  stages; per-stage model knobs at `config_defaults.yaml:63-66`;
  hiring caps at lines 76-77; auto-promote knob at 78; review
  window at 79.
- The conveyor project's reference pattern is documented from
  `conveyor/src/config/types.ts:294-310` and
  `conveyor.config.example.json:184-238`: per-stage
  `(adapter, model, thinkingLevel, capabilityClass)` profile
  with routes, default-profile fallback, and explicit
  `(model, thinkingLevel)` for the repair agent so the fixer
  cannot silently inherit the builder.
- The recruiter's `duplicate_evidence.coherent_amendment_target`
  plus the `amend` action in `HIRING_RESPONSE_SCHEMA`
  (`hiring.py:347`) are the amend-first plumbing.
  `_amendment_agent` at `hiring.py:977` is the implementation
  the amend-first default will switch on.
- The `inference.routes` / `inference.profiles` migration
  shape, per-adapter `thinking_level` mapping, and
  same-provider warning semantics are captured in the
  reference doc.
- Two new stage prompts are drafted in the reference doc:
  `_SECURITY_REVIEW_SYSTEM` and `_SAFETY_REPAIR_SYSTEM`. They
  are not yet in the code; the doc captures design intent so
  the implementation is reviewable before code lands.

## exact-blocker

- Planning pair (AR-235 issue, reference doc, registry updates)
  is uncommitted. Per AGENTS.md "A commit cannot contain its
  own SHA" — the worklog ledger commit records the substantive
  commit, not itself.
- No code change has started; user explicitly paused
  implementation ("dont start any coding changes yet"). Next
  step is commit + push + sync; subsequent slices await
  greenlight per slice.
- Tracker creation/closure for sibling "pending authorization"
  ARs remains blocked on operator authorization.
- No automatic CI ran for this planning work. Exhaustive
  coverage, the four-shard 97% coverage gate, and the
  six-interpreter compatibility matrix are
  `workflow_dispatch`-only and were not requested.
- `main` lacks authorized branch protection; required contexts
  are an outward setting change owned by AR-159.
- The 3 pre-existing `verify_docs.py` worklog errors
  (`e87747d` missing, `4928a87` inaccurate) are not introduced
  by AR-235 and are out of scope here.

## same-task-continuity

Context thresholds never create, transfer, pause, or stop this
task. Continue the same persistent goal from the planning pair
through normal compaction. Subsequent slices await explicit user
greenlight per slice.

## next-bounded-work-package

1. Commit the planning pair (AR-235 issue, reference doc,
   registry updates) as one substantive commit.
2. Commit the worklog update and registry backref as the
   matching `docs(worklog):` ledger commit (exempt from
   requiring another row, per AGENTS.md).
3. Push the pair to `origin/main`; verify the registry still
   resolves; `gh issue view 244` to confirm tracker parity.
4. Remove `scripts/strip-frontmatter.ps1` from the working
   tree (operator action; hard-delete was policy-blocked from
   this side) or move it under a clearly-local path.
5. Pause for user greenlight. Proposed slice order:
   profile schema + routes → security review → amend-first →
   cap removal → auto-promotion → dashboard views. Each slice
   is a separate PR with focused tests and a focused review.

## verification

~~~text
python scripts/docs_metadata.py --check
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
gh issue view 244 --repo Holeshot-Software-LLC/agency-runtime --json state,labels
git diff --check
# After commit + push:
python scripts/update_worklog.py --check
# After the first implementation slice lands, add the relevant
# fast spine from AGENTS.md (test_workforce_dynamic_hiring,
# test_workforce_hiring_contract, test_workforce_selection_safety,
# test_workforce_promotion, test_routing_correctness).
~~~

## constraints

- No push, PR, hosted dispatch, publication, tracker mutation,
  tag, release, trust-store action, or repository setting
  change without authorization.
- Do not start implementation slices without explicit user
  greenlight. The "dont start any coding changes yet" directive
  stands until the user unblocks it.
- Preserve the 12 KiB / 180-line hard cap. If the next slice's
  state does not fit, archive this capsule under
  `docs/roadmap/handoffs/archive/` and start a fresh one with a
  new SHA pair, per AGENTS.md.
- Keep AR-235 in `open` until every acceptance item has current
  evidence. Do not mark it `done` on the strength of the
  planning pair alone.
- Do not delete or rewrite any planning artifacts (AR-235
  file, reference doc, registry rows, this capsule) without
  first moving them to `archive/`. The historical record is
  the source of truth.
- Do not introduce live-evaluation admission or modify
  `hard_checkpoint_percent`. The fixed 50% threshold is the
  only field accepted by the capsule schema.
- Do not bind AR-235 to AR-122 with `depends_on` until AR-122
  reciprocates with `blocks: [AR-235]`. Current relationship
  is in the `related` list only.
