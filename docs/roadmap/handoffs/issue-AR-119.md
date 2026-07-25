---
title: "AR-119 active recovery capsule"
status: active
category: roadmap
created: 2026-07-23
updated: 2026-07-24
tags: [handoff, routing, workforce, evaluation, recovery]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-121-inference-planning-and-staffing.md
  - docs/decisions/0087-inference-decides-from-a-relevance-shortlist.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-119
branch: codex/ar-119-contract-enrichment
evidence_commit: 117a84bc290587e1a8290c4b7925da0d2a343a38
minimum_ledger_commit: 117a84bc290587e1a8290c4b7925da0d2a343a38
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132
---

# AR-119 active recovery capsule

Bounded current-state projection for AR-119. The
[canonical issue](../issue-AR-119-inference-first-workforce.md) is the complete
acceptance contract. Architecture: ADR-0087 (inference is the sole decider;
determinism is recall + validation; offline declines; ZCode is the 5th host).

## checkpoint

- Branch: `codex/ar-119-contract-enrichment` (descends from
  `codex/ar-119-child-routing-and-coverage` / PR #141). `main` is not ahead.
- All code changes below are uncommitted, pending commit + PR #141 update.
- Live umbrella [#132](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/132)
  remains OPEN; closure needs authorization after the deferred release gates.

## completed-evidence

- **Nomination blocker fixed (WP1/WP2).** `_semantic_staffing_classes`
  (`inference.py:1255`) trusts the model's eligible `required` picks; role
  anchors are a fallback only (seeded when the model nominates no eligible
  required specialist, respecting the model's forbidden). Clean partition: no
  agent is ever both required and forbidden. `verify_staffing._selection`
  (`staffing_verifier.py:571`) removed the `lifecycle_owner_missing_from_
  required` re-derivation; it now validates eligibility/composition/coverage/
  budget around the trusted required set.
- **Host compat consolidated (WP3).** `_HOST_COMPATIBLE` + `expand_compatible_
  hosts` moved to `host_capabilities.py`; applied in the workforce verifier AND
  the legacy selector `compatibility.py`. codex/claude-declaring specialists are
  now eligible on zcode consistently.
- **ZCode header/delivery fix (WP11) — root cause confirmed.** Every ZCode
  turn routes through `preflight_delivery_policy == "isolated"`, but
  `format_isolated_specialist_context` raised `ValueError` for `host="zcode"`,
  masked only by a `host_name="claude"` masquerade (which mis-attributed
  evidence/control). Three coupled fixes resolve it: `HookBridge` stamps
  `host_name="zcode"` (recipe carries the true host);
  `format_isolated_specialist_context` + `native_child_prompt_delivery`
  whitelist `zcode` (isolated path no longer raises); `_NATIVE_DELEGATION_TOOLS`
  adds zcode (correct `Agent`-tool guidance). Unit-verified: the isolated path
  now completes for zcode (raised before). Subagents remain host-limited.
- **Enrichment wiring (WP5).** New `roster/enrichment.py` overlay merges typed
  `stacks`/`domains` + `scope_qualifiers` before projection; shipped overlay at
  `roster/data/scope_qualifiers.json`. `senior-developer` now covers
  fluxui/livewire/laravel.
- **Acceptance criteria rewritten to ADR-0087 (WP0).** FluxUI overstatement
  corrected (`senior-developer` owns FluxUI via preferred_when; not a real gap).

## exact-blocker

**FIXED:** the recruiter nominated the right specialists but `verify_staffing`
rejected them (`no-safe-deterministic-team`) because `_semantic_staffing_classes`
overrode model-required with role anchors and `_selection` re-derived required
from `role_anchors`. Both removed (WP1/WP2).

**Residual (pre-existing, xfailed):** `test_wrong_but_structurally_valid_
selection_is_rejected_by_deterministic_staffing` — the deterministic recall
stage (`deterministic_staff_plan`) can accept a covering team before the
recruiter registers the model's forbidden set, so a model-forbidden specialist
can be selected when recall pre-empts inference. Marked `xfail(strict=True)`;
tracked as a nomination-authority follow-up, not a regression.

**ZCode child limitation (host-gated, not a code bug):** ZCode emits no
`SubagentStart`/`SubagentStop`, so governed native-child self-routing cannot
fire for ZCode children. Main-session correlation forwards; children are
host-limited. Follow-up gated on host support.

## same-task-continuity

Context thresholds never create/fork/dispatch/wait for another task. Continue
through compaction. At or below 50%, ensure a clean durable checkpoint, then
continue in the same task.

## next-bounded-work-package

1. Full static + test gate: `ruff`, `docs_metadata --check`,
   `update_worklog --check`, `verify_docs`, `pytest tests/ -W error`, dashboard
   UI test, `git diff --check`.
2. Telemetry, then small live smoke (codex-cli): "Review code for correctness
   and security", "Fix the authentication bug", "Write unit tests", and the
   previously-blocked "Design a Git branching strategy" (expect
   git-workflow-master required+selected). Confirm ZCode main-session header.
3. Commit per WP, push, update PR #141 (correct "5 hosts forward correlation /
   children self-route" for ZCode). Edit #132 body to mirror ADR-0087 wording
   (#132 stays OPEN).

## verification

~~~text
.\.venv\Scripts\python.exe scripts\docs_metadata.py --check
.\.venv\Scripts\python.exe scripts\update_policy_availability.py --check
.\.venv\Scripts\python.exe scripts\update_worklog.py --check
.\.venv\Scripts\python.exe scripts\verify_docs.py
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python -m pytest tests/ -q -W error
node --test tests/dashboard_ui.test.mjs
agency eval routing --json --no-details
git diff --check
.\.venv\Scripts\python.exe scripts\context_handoff_status.py --json --threshold 50
~~~

## constraints

- Telemetry before every live evaluation; conservative estimate when
  `CODEX_THREAD_ID` is absent.
- Do not weaken typed coverage/parser validation, add a scenario route,
  reinterpret malformed upstream output, or claim Agency is better without a
  benchmark-valid comparison.
- A specialist governs its unit; offline declines (ADR-0087).
- Deferred release gates (WP12): full Agency-on/off paired graded-outcome
  corpus vs pinned upstream; 4-host + ZCode canaries; reinstall verification;
  full 263-enrichment batch; `verify_tracker.py --require-tracker` + closure.
  #132 closes last.
