---
title: "AR-202 active recovery capsule"
status: active
category: roadmap
created: 2026-07-30
updated: 2026-07-30
tags: [handoff, workforce, recruiter, repair, evidence, recovery]
related:
  - docs/roadmap/issue-AR-202-make-recruiter-repair-converge.md
  - docs/roadmap/issue-AR-200-diagnosable-decision-conformance.md
  - docs/roadmap/issue-AR-201-fund-default-workforce-repair.md
  - docs/decisions/0088-deterministic-typed-recall-offline-floor.md
  - docs/decisions/0113-prove-decision-conformance-with-isolated-mutations.md
  - docs/decisions/0114-fund-one-default-workforce-semantic-repair.md
  - docs/decisions/0115-aggregate-bounded-recruiter-repair-failures.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-202
branch: agent/ar-203-readme-story-proof
evidence_commit: 1e54967eb51412bae862b160a36612f7c9d1ed4f
minimum_ledger_commit: 0bb1614ef849903b9732ca4a0d02f910921389e5
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/182
---

# AR-202 active recovery capsule

## checkpoint

- PR 186 merged the activation repair as exact revision
  `830b878859318bc1288858ba65ba580bd98bf53e`; build
  `0.1.0+g830b87885931` is installed for Codex and ZCode only.
- Trial `ar203-830b878-ordinary-02` is terminal `NO-GO` and will not be rerun.
  It is the first live exercise of the nine-unit recruiter path after the
  activation repair.
- The first causal boundary is frozen: the ordinary recruiter system required
  every planned unit while the repair user prompt requested only invalid rows.
- The current source gives the repair a distinct satisfiable system contract
  and adds a fail-closed durable projection of allowlisted unit/invariant pairs.
- Two review passes are complete. The changed boundary passes 107 tests with
  1 skipped; decision conformance kills 21/21 mutations with zero survivors or
  invalid results and unchanged source.
- Named fast Python passes 675 tests with 6 skipped; dashboard UI passes 109;
  routing evaluation 1.3.0 passes every gate; documentation validates 551
  files; and Ruff checks and formats all 603 Python inputs.
- Owner-untracked analysis and lock files remain untouched.

## completed-evidence

- Exact trace `019fb417-f166-7461-a1db-e53ee0007045` records one route, one
  run, three model receipts, two finalizations, and nine typed work units.
- Planner call one applied. Recruiter call two was
  `provider_response_contract_invalid`; bounded repair call three was
  `provider_no_valid_response`.
- The route evaluated 272 candidates, retained 53 eligible, and abstained with
  zero selected, loaded, delegated, or hired specialists.
- The repair regression uses the real initial and repair system prompts. It
  fails if the repair prompt asks for all planned units or permits omission of
  a listed failed unit.
- Durable receipt tests prove valid unit/invariant pairs survive normalization
  while unknown codes and injected provider content are absent.

## exact-blocker

The source repair is reviewed and fast-green but not yet checkpointed, merged,
or exact-installed. Live convergence remains unproven until the one replacement
trial accepts a defensible specialist team.

## same-task-continuity

Keep online selection inference-owned. Do not enlarge call budgets, restore
deterministic role anchors, tune unrelated roster content, or force hiring when
existing specialists form a safe team.

## next-bounded-work-package

1. Checkpoint the reviewed source plus docs and its ledger entry.
2. PR, merge, and exact-install the revision for Codex and ZCode only.
3. Run one replacement trial. It must accept at least one specialist/team for
   the fixed prompt, or record a defensible gap and hiring decision.
4. Stop for owner direction if the same recruiter boundary fails again.

## verification

~~~text
python -m pytest tests/test_workforce_inference.py tests/test_routing_receipt_header.py tests/test_routing_correctness.py tests/test_workforce_selection_safety.py tests/test_decision_conformance.py -q -W error
agency eval decision-conformance --repository . --json
python scripts/context_handoff_status.py --json --threshold 50
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
git diff --check
~~~

## constraints

- Configured online selection remains inference-owned.
- Persist no provider content, raw response, unknown identifier, or exception
  text.
- Keep the one-repair fast budget fixed at three total calls.
- Preserve terminal traces and owner-untracked files.
- Touch only Codex and ZCode on this machine.
- One live trial per exact installed build; correction count must equal zero.
