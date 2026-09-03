---
title: "AR-383 inferred subject projection handoff"
status: active
category: roadmap
created: 2026-09-03
updated: 2026-09-03
tags: [handoff, workforce, recall, staffing, hiring, recruiter, critic]
related:
  - docs/roadmap/issue-AR-383-inferred-subject-context-fails-its-own-projection.md
  - docs/roadmap/issue-AR-384-staff-decisions-die-on-uncoverable-typed-requirements.md
  - docs/roadmap/issue-AR-385-structured-reply-budget-truncates-nominations-silently.md
  - docs/roadmap/issue-AR-386-strict-critic-vetoes-verifier-accepted-install-turns.md
  - docs/roadmap/issue-AR-373-recruiter-evidence-vocabulary.md
  - docs/roadmap/issue-AR-370-staffing-asks-the-wrong-question.md
  - docs/decisions/0198-waive-the-typed-requirements-the-roster-declares-but-cannot-serve.md
  - docs/decisions/0199-give-each-inference-stage-its-own-reply-budget.md
  - docs/decisions/0200-bind-the-strict-critic-to-the-advisory-doctrine.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-383
branch: claude/ar384-closure
evidence_commit: 6b79736c0116331094630f7f252fa68992a1fb8d
minimum_ledger_commit: 8fde90dfcf746eb84abe288d7272c3db3441d2dd
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/581
---

# AR-383 inferred subject projection handoff

> **This capsule is not on `main`.** It lives on branch `claude/ar384-closure`,
> the top of a stack: `claude/ar386-critic-contract` (PR #586) on
> `claude/ar385-reply-budget` (PR #585) on `claude/ar384-coverage-gaps`
> (PR #584) on `claude/ar373-recruiter-payload` (PR #583) on
> `claude/ar370-acceptance` (PR #582). ADR-0198, ADR-0199, ADR-0200 and the
> AR-384, AR-385 and AR-386 documents are on the same stack. Merge the open
> PRs in order with `--merge`, or check out `claude/ar384-closure` before
> relying on any of them. If you are reading this from `main`, the PRs have
> merged and this note is spent.

Start-here capsule. The install path now completes end to end under strict
mode on some wordings; what remains is recruiter-side residue.

## checkpoint

The previous package's items 1 to 3 are done on the stack above.

- **AR-385** (ADR-0199, feat `0f70496c`): each workforce stage owns its
  reply budget (recruiter and hiring 16384, planner 4096, critics 2048,
  subject 1024), the cap adds the gateway's thinking allowance, a reply that
  reaches the cap is `provider_response_truncated` with a `truncation`
  record on both receipts, and a cut nomination row costs only its unit.
  Config: `reply_budget_tokens` on a profile or provider entry.
- **AR-386** (ADR-0200, feat `6b79736c`): the critic contract and system
  prompt state the advisory doctrine with `veto_grounds` and
  `never_veto_for`; a veto's codes ride on the staffing decision as
  `critic_<code>` beside `staffing_critic_rejected`, so the preflight
  receipt's `staffing_reason_codes` and the fail-open disclosure name it.
- **AR-384 closure**: record frozen to `1711bcaa`, verifier run: criteria
  1 and 3 satisfied, criterion 2 **contradicted** on the literal unit id
  (the fresh-wording turn staffed `operations-manager` on the captured
  shape, which the planner named `unit-install-plan`). Status stays
  `in_progress`; the done flip needs the owner's call below.

| eleven install wordings, strict mode, AR-386 runtime | turns |
|---|---|
| critic approved; turn **accepted** with a staffed team | 2 (209, 304) |
| critic vetoed, `wrong-neighbor-selection` only, named on the receipt | 4 (204, 205, 208, 305) |
| `staff_without_safe_team` on a coverable token (AR-384 `domain:platform`) | 3 (201, 206, and 202's repair) |
| `recruiter_candidate_row_shape_invalid` on first attempt (AR-373 residue) | 2 (202, 207) |
| recruiter declared a gap, hiring ran, no hire landed | 1 (203) |

No live reply was truncated under the shipped budgets; a six-unit throttle
nomination completed at 2277 tokens where the old cap cut it at 2048.

## completed-evidence

**On the stack.** `core/reply_budget.py`, transport usage reading and
`project_reply_truncation` (AR-385, `tests/test_reply_budget_truncation.py`,
43 tests). `_critic_receipt_codes`, `_critic_rejected_staffing`, the doctrine
fields in `_strict_critic` (AR-386, `tests/test_strict_critic_doctrine.py`).
Five curated decision-conformance mutations added across both; the
`recruiter-repair-allows-unlisted-row-overwrite` anchor refreshed. Acceptance
records for AR-385 and AR-386 drafted at `candidate_commit: pending`, each
with an evidence file under `docs/roadmap/acceptance/evidence/`.

**Capture recipe, branch code.** `PYTHONPATH=<worktree>` with the installed
venv python (`~/.local/share/agency-runtime/venvs/0abe4a77.../bin/python`),
harness copied from the AR-384 session and extended to record the transport's
truncation fields and to read `store.get_preflight_failure_receipt` back.
Session scratchpad: `capture385.py`, `capture385b.py` (recruiter budget forced
to 256 in process), `capture385c.py` (allowance zeroed too: the live cut),
`capture386.py`, `raw385*/`, `raw386/`. Store backup
`agency.db.pre-ar385-141812`.

**Live facts worth keeping.** Two of twelve recruiter calls on the AR-385 run
ended at the recruiter profile's 30000 ms `timeout_ms` with no reply: with
the cap no longer bounding a long reply, the timeout is the binding
constraint. One 941-token recruiter reply closed its `units` array early and
continued (structural model error, refused by the transport). The receipt's
`_identity` digests any id containing the marker `token`, so
`unit-implement-token-bucket` shows as a `sha256:` on the receipt. Turns that
run the subject stage log `recall_embedding skipped
dense_recall_projection_invalid`, which is AR-383 live.

## exact-blocker

Nothing blocks the install path as such any more: two of eleven install
wordings completed. The remaining losses are the recruiter's, in this order:
`staff_without_safe_team` on the coverable `domain:platform` token (AR-384
option 2, the planner-versus-roster vocabulary collision), AR-373's
row-shape and evidence residue on the MiniMax deployment, the four
wrong-neighbour vetoes (the same collision seen from the critic), and one gap
that hiring declined. Closing AR-385 and AR-386 needs their second PRs.
AR-384's done flip is blocked by its criterion 2 wording: it names
`unit-install-operation` literally, and no fresh planner run reproduces a
unit id, so a literal verifier contradicts any live turn even though turn
304 today staffed `operations-manager` on both plan-authority install units
of that shape and completed. Rewording the criterion to the unit shape is
the owner's call; then re-verify.

## same-task-continuity

The nine traps from the previous capsule hold. Three more:

1. **The disclosure line has a 512-character budget** and now carries up to
   four staffing codes including projected critic codes; the projection
   bounds a code to 56 characters for that reason. Do not widen either.
2. **LiteLLM caches on the whole request body.** A changed `max_tokens`
   is a cache miss, so this session's recruiter replies were fresh even on
   yesterday's wordings; a re-run with identical bodies replays.
3. **`verify_acceptance.py` exports the candidate with `git archive`**, so a
   closure PR can sit at the top of the stack while citing an older commit.

## next-bounded-work-package

In this order.

1. **AR-384 option 2**: constrain the planner's `domains` to what the roster
   serves for the unit's authority, starting with the `platform` collision;
   the three `staff_without_safe_team` turns and the four wrong-neighbour
   vetoes all trace to it. Measure on the same eleven wordings.
2. **AR-373 residue**: `recruiter_candidate_row_shape_invalid` on first
   attempts (two of eleven) and the evidence charset; the MiniMax deployment
   does not honour the strict `json_schema` `required` list.
3. **AR-384 criterion 2**: owner rewords it to the unit shape (plan
   authority, `desktop` and `operations` domains) rather than the literal
   id, or accepts a re-freeze to a candidate carrying turn 304; re-run
   `scripts/verify_acceptance.py --issue AR-384 --criterion 2 --provider
   codex`; flip to `done`. AR-385 and AR-386 closure PRs likewise: freeze to
   `0f70496c` and `6b79736c`, verify `--all`, flip.
4. **Recruiter timeout**: raise `agency-recruiter.timeout_ms` (owner's
   configuration) or measure how often 30 s is hit under the new cap.
5. **Fix AR-383** per its Approach; then the 4-of-5 gap divergence; then
   AR-370.

## verification

At `6b79736c`: ruff clean; `tests/test_strict_critic_doctrine.py` 5 passed;
critic, receipt, chaos and disclosure suites 486 passed, 1 skipped; named
fast spine 1165 passed, 3 skipped under `-W error`; `eval routing` passed;
decision-conformance 172 killed, 0 survived, `source_unchanged: true`;
`docs_metadata.py --check`, `update_worklog.py --check`,
`update_policy_availability.py --check`, `verify_docs.py`, `git diff
--check` green. `verify_tracker.py` reports `missing_remote` for AR-384,
AR-385 and AR-386 by design. Pre-existing failures on base `7a08a3e9`, not
ours: `test_public_api` (legacy roster), `test_cli_judge_providers`,
`test_durable_continuation` (3), `test_http_server` (2),
`test_native_child_delivery_verification_ledger` (3).

## constraints

- `agency.yaml` is operator configuration: the recruiter's `timeout_ms`,
  the deployment order and `workforce.mode: strict` are the owner's call.
- `max_hires_per_day` is the default 3; no hire landed this session.
- Never commit to `main`; branch in a worktree, PR, merge with `--merge`.
  Ledger dance on every substantive commit. Tracker writes need
  authorization; AR-384, AR-385 and AR-386 carry `tracker_url: null`.
