---
title: "AR-383 inferred subject projection handoff"
status: active
category: roadmap
created: 2026-09-03
updated: 2026-09-03
tags: [handoff, workforce, recall, staffing, hiring, recruiter]
related:
  - docs/roadmap/issue-AR-383-inferred-subject-context-fails-its-own-projection.md
  - docs/roadmap/issue-AR-384-staff-decisions-die-on-uncoverable-typed-requirements.md
  - docs/roadmap/issue-AR-385-structured-reply-budget-truncates-nominations-silently.md
  - docs/roadmap/issue-AR-373-recruiter-evidence-vocabulary.md
  - docs/roadmap/issue-AR-370-staffing-asks-the-wrong-question.md
  - docs/decisions/0197-form-the-retrieval-subject-before-the-turn-that-needs-it.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-383
branch: claude/ar373-recruiter-payload
evidence_commit: 827a46c2cf465d28c853a9c50df913a67e727d6c
minimum_ledger_commit: 152bdf0b430810dd0bd9deeb6abc6e976a478ffb
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/581
---

# AR-383 inferred subject projection handoff

> **This capsule is not on `main`.** It lives on branch
> `claude/ar373-recruiter-payload`, which stacks on `claude/ar370-acceptance`
> (PR #582). The AR-383, AR-384 and AR-385 issue documents it cites are on the
> same branches. Merge the open PRs or `git checkout claude/ar373-recruiter-payload`
> before relying on any of them. If you are reading this from `main`, the PRs
> have merged and this note is spent.

Start-here capsule. The staffing investigation now has three filed defects in
front of AR-383, in a known order of weight.

## checkpoint

Item 1 of the previous package is answered. The recruiter's double contract
failure was captured in process, request and raw reply, on five fresh turns
(`827a46c2`). It is three defects wearing one reason code, and only one of
them is the model's.

| share of 48 rejected recruiter attempts (45-turn smoke) | code | owner | who is wrong |
|---|---|---|---|
| 31 | `staff_without_safe_team` | **AR-384**, filed | the planner-to-verifier contract: the unit named a typed token no eligible contract covers, so no `staff` answer could validate |
| 8 | none recorded | **AR-385**, filed | the runtime: replies cut at the hardcoded 2048-token budget, rejected as a plain `ValueError`, blank on the receipt |
| 9 | `invalid_candidate` | AR-373, updated | the contract charset again (underscore codes Agency itself shows), forbidden rows without `positive_evidence`, prose after a misleading retry |

AR-384 and AR-385 carry `tracker_url: null` and `pending authorization` in
the roadmap index; `verify_tracker.py` is red until the owner authorizes the
GitHub issues, exactly as AR-383 was between filing and mapping.

## completed-evidence

**Capture method, reusable.** `capture.py` in the session scratchpad hooks
`structured_provider.open_no_redirect` and `_read_http_response` (exact HTTP
request, response headers, raw body), `invoke_structured_provider_result`
(provider, stage, prompt, schema, parsed value), and the constructors of
`_NominationValidationError`, `_StaffingVerificationError` and
`_CriticValidationError` (every failure with its `diagnostic_code` and repair
contract). Output: `raw/<id>-calls.json`; `analyze.py` cross-references a
turn's plan, `typed_recall`, response rows and failures. Nothing in the
runtime records the raw reply, so this is the only way to see it.

**Which deployment answered.** The `x-litellm-model-id` response header and
the gateway's Postgres `LiteLLM_SpendLogs` table (`model`, `model_group`,
`completion_tokens`, `cache_hit`) name it. The recruiter route was served by
`anthropic/MiniMax-M3` on 55 of 60 smoke calls and 8 of 9 captured calls; the
one captured turn the gateway handed to `chatgpt/gpt-5.5` (after a fallback
the gateway did not log) returned clean codes on every row and was accepted.

**AR-384 instance.** helix-install turn, `unit-install-operation` (plan
authority, domains `desktop`+`operations`): `typed_recall.uncovered_requirements`
said `domain:desktop` before the recruiter spoke; the only `desktop` contract
has modify authority; `capability:operations` is carried by 6 of 291
contracts. The roster has 0 untyped contracts, so the wildcard coverage escape
in `_coverage` no longer exists. The repair contract listed the sole coverer
as `excluded` and asked for a covering complement.

**AR-385 instance.** Three of nine MiniMax replies stopped at exactly 2048
completion tokens with closed JSON whose last unit row lacked `unit_id`; the
gateway maps `reasoning_effort: medium` to a thinking budget capped at
`max_tokens - 1`, so thinking and answer share the budget. Spend log: 5 of 55
smoke calls at the cap.

**AR-383 status.** Unchanged: filed, traced, reproduced, not fixed. Its
correction ledger in the issue document still stands and must not be
re-introduced.

## exact-blocker

AR-384. Until a `staff` decision on a unit with a roster-wide uncovered token
can validate, every install-flavoured request and every review unit carrying
a scarce domain dies at the recruiter regardless of model, and hiring is
never reached. The fix is an owner decision between three approaches recorded
in the issue; option 1 (advisory roster-wide gaps, conjunctive rule kept for
coverable tokens) is the smallest and matches what the prompt already
promises.

## same-task-continuity

The four traps from the previous capsule still hold; two more from this
session:

1. **`LITELLM_API_KEY` must be in the invoking shell**; every inline
   `api_key` in `~/.agency-runtime/agency.yaml` is empty. Source only that
   variable from `~/.openclaw/.env`.
2. **`agency route` passes `store=None`**; never read hiring from it.
3. **`run_preflight` needs a `capability_receipt`** from
   `native_adapter_capability_receipt(host, platform=..., session_id=...,
   trace_id=...)` or everything is `execution_host_unproven`.
4. **Gateway response caching replays identical prompts** in 0.01s with
   `total_inference_calls: 0`; five receipts at 16:15 UTC are one cached
   answer. Fresh wording every time.
5. **`actual_model` on receipts is the route alias**, never the deployment.
   Read the header or the spend log. gpt-5.5 spend rows show zero tokens
   because the gateway's cost tracking fails for that model; the rows are
   real calls.
6. **A blank rejected recruiter attempt on a receipt is not "no information"**;
   it is AR-385's plain `ValueError` path. Check `completion_tokens` in the
   spend log before reading anything else into it.

Store backups: `agency.db.pre-preflight-smoke` (previous session scratchpad)
and `agency.db.pre-capture-123724` (this session's). Five more preflight turns
were persisted; no hire landed (`agent_workers` 291, `agent_hiring_cases` 41).

## next-bounded-work-package

In this order.

1. **Owner decision on AR-384's approach**, then implement it. Code on the
   verifier path: fast Python spine under `-W error`, `ruff check`, `ruff
   format --check`, `agency eval routing`, `agency eval decision-conformance`.
   Re-measure with fresh wording; acceptance is the helix turn staffing
   `unit-install-operation`.
2. **AR-385**: stage-owned reply budget and a truncation record on the
   receipt. Independent of 1; small.
3. **AR-373 residue**: admit `_` in nomination evidence (the ineligibility
   vocabulary Agency shows), default absent evidence arrays on forbidden
   rows. Then re-run the live criterion.
4. **Fix AR-383** per its Approach. Carry the hints beside the turn context,
   preserve the rejected projection's reason, keep the all-or-nothing rule.
5. **Explain the 4-of-5 gap divergence** (`_all_gap_units` /
   `_hireable_gap_units` in `selector/pipeline.py`), then re-measure hiring.
6. **Decide AR-370**; the drafted acceptance record from the previous session
   scratchpad is honest about criteria 3, 5 and 6 having nothing implemented.

## verification

Docs-only work: `docs_metadata.py --check`, `update_worklog.py --check`,
`update_policy_availability.py --check` (needs the package importable: run
with the installed venv's python and `PYTHONPATH` at the checkout),
`verify_docs.py`, `git diff --check`. All green at `152bdf0b`.
`verify_tracker.py` reports `missing_remote=['AR-384', 'AR-385']` by design
until the tracker mapping is authorized.

The installed runtime (`venvs/0abe4a77...`) is byte-identical to `main` for
the whole package, verified by directory diff, so every measurement here is of
current code.

## constraints

- `agency-hiring-critic.timeout_ms` is still **120000**, unevaluated; backup
  `agency.yaml.pre-critic-timeout` in the previous session scratchpad.
- `agency.yaml` is operator configuration. Reordering the recruiter route's
  deployments (gpt-5.5 before MiniMax) would likely raise the staffed rate,
  and is the owner's call, not a branch change.
- `max_hires_per_day` is the default 3.
- Never commit to `main`; branch in a worktree, PR, merge with `--merge`.
  Ledger dance on every substantive commit. Tracker writes need authorization.
