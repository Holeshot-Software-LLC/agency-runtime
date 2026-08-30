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
branch: codex/ar-203-readme-story-final-proof
evidence_commit: 5e3fab622b75f257e0ab4b74f1cc2c6d43b1d748
minimum_ledger_commit: 650f6d625f1d1467af26661abba217d0f671c68e
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
- PR 187 merged normally as exact main revision
  `26a3911e371e42bc004faabaa2fd0b802bf50fdd`; GitHub assigned no runner and
  executed zero hosted steps because of the account payment/spending limit.
- Exact build `0.1.0+g26a3911e371e` is installed. Codex and ZCode were
  refreshed; the owner expanded scope to include the dashboard, whose service
  is installed, owned, enabled, active, manifest-current, and reachable.
- Post-merge Codex review raised three P1 threads. The ledger claim is disproven
  by the preserved two-parent merge ancestry. Two source findings are valid:
  repair accepted rows outside its failed tuple, and sensitive planned-unit IDs
  could remain clear text in durable evidence.
- The current source rejects a repair before mutation unless its ordered IDs
  exactly match the recorded failures, and hashes sensitive unit IDs while
  preserving receipt idempotence. Focused boundary: 108 passed, 1 skipped.
  Decision conformance: 23/23 killed, zero survivors or invalid results, source
  unchanged.
- The post-review named fast gate passes: Python 675 passed and 6 skipped;
  dashboard UI 109 passed; routing evaluation 1.3.0 passed every gate;
  documentation validated 552 files; Ruff checked and format-validated all 603
  Python inputs.
- PR 188 merged with commit-preserving ancestry as exact main revision
  `5e3fab622b75f257e0ab4b74f1cc2c6d43b1d748`. Its only Codex P1 named a
  synthetic commit absent from GitHub; the actual remote graph preserves both
  ledgered commits. Hosted jobs again received no usable runner because of the
  account payment/spending limit.
- Exact build `0.1.0+g5e3fab622b75` is installed. Codex and ZCode refreshed;
  the dashboard is owned, enabled, active, current, drift-free, and reachable.
- Codex preflight found all eight events enabled and all eight hashes modified,
  with zero trusted. It attempted no model call and persisted no attestation.
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

The final build is installed and locally verified. Codex hook trust is the
first remaining boundary and requires the owner in a fresh terminal TUI.

## same-task-continuity

Keep online selection inference-owned. Do not enlarge call budgets, restore
deterministic role anchors, tune unrelated roster content, or force hiring when
existing specialists form a safe team.

## next-bounded-work-package

1. Ask the owner once to trust the final eight Codex hook hashes.
2. Verify exact activation without reinstalling.
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
- Touch only Codex, ZCode, and the owner-requested dashboard on this machine.
- One live trial per exact installed build; correction count must equal zero.
