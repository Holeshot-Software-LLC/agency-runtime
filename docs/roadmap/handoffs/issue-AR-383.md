---
title: "AR-383 inferred subject projection handoff"
status: active
category: roadmap
created: 2026-09-03
updated: 2026-09-03
tags: [handoff, workforce, recall, staffing, hiring]
related:
  - docs/roadmap/issue-AR-383-inferred-subject-context-fails-its-own-projection.md
  - docs/roadmap/issue-AR-370-staffing-asks-the-wrong-question.md
  - docs/roadmap/issue-AR-373-recruiter-evidence-vocabulary.md
  - docs/decisions/0197-form-the-retrieval-subject-before-the-turn-that-needs-it.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-383
branch: claude/ar370-acceptance
evidence_commit: 4ce061fbfa19df42b9eed5002f628929e0f527e3
minimum_ledger_commit: 937eae79122b7fe110901b679f27f5ef8139666a
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/581
---

# AR-383 inferred subject projection handoff

Start-here capsule. AR-383 is filed and tracked; the work it opened up is
larger than the defect, and the ordering below matters.

## checkpoint

AR-383 is filed (#581), PR #582 open, six commits, all docs gates green. The
defect is traced and reproduced, not inferred.

The session's larger result is that **staffing rarely reaches a judgement at
all**. Across 45 preflight turns the recruiter, not the roster and not the
recruiter's judgement, is what ends most turns. AR-383 is real but is a
recall-quality and diagnosability defect, not the reason turns fail.

## completed-evidence

**AR-383 mechanism.** `_with_inferred_subject` emits
`{**projected_turn_context, "workforce_subject_hints": hints}`; on a fresh turn
that is a single-key mapping. `project_turn_routing_context`
(`turn_routing_context.py:166`) accepts only `{}` or the complete
`_TURN_ROUTING_CONTEXT_FIELDS` set, returns `None`; `project_unit_query`
(`hybrid_recall.py:268`) raises; `_run_hybrid_recall` (`inference.py:2045`)
swallows it as `dense_recall_projection_invalid`. Reproduced directly.

**Correlation.** Route path, 30 prompts: 17 ran the `subject` stage, all 17
applied, all 17 lost dense recall, 0 of the other 13 failed that way. Also
reproduces on the preflight path, so it is not diagnostic-surface-only.

**Two corrections are recorded in the issue and must not be re-introduced.**
An abstention split that mixed routing-status with staffing-code axes (19 of 22
by code, not 21), and a retracted causal claim: dense-recall loss is fail-open,
4 of the 17 still reached `inferred` and 3 of those staffed, so it is neither
necessary nor sufficient for a turn to fail.

**Two smokes, same 30 prompts, both with the credential sourced.**

| surface | staffed | note |
|---|---|---|
| `agency route --host codex` | 8 / 30 | `store=None`, so hiring is unreachable |
| `run_preflight` (real store) | 3 / 30 | 27 `no_specialist_fail_open` |

**Hiring.** Across 45 preflight receipts, hiring produced events **once**:
`hiring_status_abstained`, `hiring_inference_attempted`,
`hiring_critic_unavailable`, `provider_call_timed_out`. Zero contractors were
hired; `agent_hiring_cases` 41 and `agent_workers` 291 are unchanged.

## exact-blocker

Not AR-383. The recruiter returns a response that fails its contract twice in a
row, taking the turn to `inference_invalid`: **22 of 45** preflight receipts.
That is what stops turns before hiring can be considered, and it belongs to
AR-373.

Second, unexplained and worth its own look: `no_safe_sufficient_team` was
declared 5 times but hiring events appeared once, so **4 of 5 declared gaps
produced no hireable gap unit**. `_all_gap_units` / `_hireable_gap_units`
(`selector/pipeline.py`) is where that divergence lives.

## same-task-continuity

Four traps, each of which cost a wrong conclusion in this session:

1. **`LITELLM_API_KEY` must be in the invoking shell.** Every inline `api_key`
   in `~/.agency-runtime/agency.yaml` is empty, so resolution falls to
   `api_key_env`. Without it every staffing verdict reads
   `workforce_provider_unavailable` and measures the shell, not the runtime.
   Source only that one variable from `~/.openclaw/.env`.
2. **`agency route` passes `store=None`** (`cli/roster_commands.py:1147`). Gap
   hiring is structurally `not_attempted` there. Never draw a hiring
   conclusion from it.
3. **`run_preflight` needs a `capability_receipt`.** Without
   `native_adapter_capability_receipt(host, platform=..., session_id=...,
   trace_id=...)` every candidate is rejected `execution_host_unproven` and
   hiring never runs. This is the AR-374 host under-provisioning trap.
4. **LiteLLM response caching is on.** Identical requests return in 0.01s, so
   re-running the same prompt replays the previous outcome with
   `total_inference_calls: 0`. Use a fresh wording to measure again.

Harnesses and raw payloads are in this session's scratchpad, not the repo:
`smoke.py` (route path), `preflight_smoke.py` (real path), `prompts.json`
(the 30 reconstructed prompts plus install-shaped variants 31-34). The prompt
set is a **reconstruction** — the original 30 were never recorded, and it
yields 10 zero-signal of 30 where ADR-0197 costed 7 of 30.

Read hiring outcomes from `preflight_failure_receipts`
(`staffing_reason_codes`, `hiring_reason_codes`), not from
`PreflightResult.routing`, which is a narrowed model-facing projection that
drops `hiring_events`, `workforce_staffing` and `workforce_plan`.

## next-bounded-work-package

In this order. The first is the only one that unblocks measurement.

1. **Chase the recruiter contract failure (AR-373).** 22 of 45 turns die there.
   Capture the rejected payload against `provider_response_contract_invalid` and
   determine whether the model, the schema, or the validator is wrong. Nothing
   downstream can be measured until turns survive this stage.
2. **Fix AR-383** per its Approach: carry the hints beside the turn context
   rather than inside it, and preserve the rejected projection's reason in the
   attempt. Do not relax the all-or-nothing projection rule.
3. **Explain the 4-of-5 gap divergence** above, then re-measure hiring.
4. **Decide AR-370.** It cannot close: criteria 3, 5 and 6 have nothing
   implemented, and 4 resolves the reference but never records it. A drafted
   acceptance record exists in the session scratchpad
   (`ar370-acceptance-draft.md`), honest about all four, and validates
   structurally against `verify_docs.py`.

## verification

Docs-only work: `docs_metadata.py --check`, `update_worklog.py --check`,
`update_policy_availability.py --check`, `verify_docs.py`,
`verify_tracker.py`, `git diff --check`. All green at
`4ce061fbfa19df42b9eed5002f628929e0f527e3`, including tracker parity over 374
roadmap items.

Code changes to the recall or projection path additionally need the named fast
Python spine under `-W error`, `ruff check` and `ruff format --check`, plus
`agency eval routing` and `agency eval decision-conformance`. The routing eval
passed on a clean `main` this session, so it is a usable baseline.

## constraints

- **Operator config is currently modified.** `agency-hiring-critic.timeout_ms`
  is **120000**, raised from 30000 at the owner's request; 120000 is the schema
  maximum (`configuration_schema.py:813`). The backup is
  `agency.yaml.pre-critic-timeout` in the session scratchpad. The bump is
  **unevaluated** — no run reached the critic afterwards. Recommend reverting
  until hiring is reachable often enough to measure.
- The store was mutated by 45 preflight turns; a pre-run backup exists as
  `agency.db.pre-preflight-smoke`. No hires landed, so the roster is unchanged.
- `max_hires_per_day` is the default 3, which caps any hiring measurement.
- Never commit to `main`; branch in a worktree, PR, merge. Ledger dance on
  every substantive commit. Tracker writes are outward-facing and need
  authorization.
- `agency.yaml` is operator configuration: do not rewrite model routes without
  the owner's word.
