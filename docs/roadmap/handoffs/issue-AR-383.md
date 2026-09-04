---
title: "AR-383 inferred subject projection handoff"
status: active
category: roadmap
created: 2026-09-03
updated: 2026-09-03
tags: [handoff, workforce, recall, staffing, hiring, recruiter, critic, planner]
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
  - docs/decisions/0201-constrain-the-planner-domains-to-what-the-roster-serves.md
  - docs/decisions/0203-show-the-recruiter-the-complete-eligible-card-set-per-unit.md
  - docs/roadmap/issue-AR-387-recruiter-cards-carry-no-eligibility.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-383
branch: claude/ar383-capsule-env
evidence_commit: b349e59b4d27de609ea29a436273ff6353fe9800
minimum_ledger_commit: 7e40380960cd8316726a358ae54ac592b2a0e22a
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/581
---

# AR-383 inferred subject projection handoff

> `main` at `7e403809` carries ADR-0198 to ADR-0203 and the done AR-373,
> AR-384, AR-385, AR-386 and AR-387. This refresh records the verified codex
> activation and the launch-environment cause behind tonight's failures.

Start-here capsule. The planner side is closed, the recruiter's reply is
read where no safety property lives, every rejected attempt is recorded, the
recruiter sees the eligibility boundary it is held to (AR-387 done), the
merged runtime is installed and verified for claude and codex, and the
losses that remain are the critic's judgment, replies the transport cannot
read, and a launch environment that must carry the gateway key.

## checkpoint

**AR-387 is done** under **ADR-0203** (PRs #595, #596 and this flip): every
recall row carries `eligible_candidate_ids` (the verifier's eligibility over
the detail cards, complete and identity-sorted) and
`eligible_candidates_without_card`, the safe-team repair contract carries
`eligible_coverers_by_requirement`, and both prompts say a card outside the
list can only be forbidden or omitted, never staffed. The isolated verifier
contradicted criterion 3 at `7af9c43b` (the repair prompt stated the
consequence, not the treatment); `b349e59b` states it in the criterion's
terms and the second pass satisfied all four criteria.

- **AR-384 option 2** (ADR-0201): `platform-engineering` no longer promotes
  into `platform`; the planner sees `planning_taxonomy.domains_by_artifact_kind`
  and a unit with no served domain is bounced as `plan_unit_domains_unserved`
  (exempt: nothing proven for the kind, compiler-chosen or novel domains).
- **AR-373, AR-384, AR-385, AR-386 and AR-387 are done** (PRs #594, #589,
  #592, #590, this one); `verify_tracker.py` reports `missing_remote` for
  AR-384 to AR-387 until the owner authorizes their tracker issues, and #537
  still needs its closure.
- **Install**: venv `56e0b6dd` built at the AR-387 fix merge. claude complete
  and wired (`agency evidence wiring`: staged and invoked projection both
  `d1e25680`); codex `runtime-verified`, hooks trusted, attestation persisted,
  after the owner's attended trust; hermes and openclaw not reinstalled.
- **Launch environment**: every inference profile reads `LITELLM_API_KEY`
  from the launching process's environment only (no file fallback) and
  nothing on the host exports it. Every preflight of the 2026-09-03 claude
  session and both first codex verifications failed `preflight_failed` with a
  healthy gateway; the verification passed at once with
  `~/.config/ai-secrets/common.env` sourced. Unavailable staffing is first a
  missing key, not a gateway outage.
- **Critic variance**: the turn-205 team replayed six times per prompt with
  the cache bypassed: 6 of 6 approved on one prompt, 1 of 6 on the other.
- **ADR-0202**: a candidate row is read as the deployment sends it where no
  safety property lives (identity and score stay mandatory); a reply that is
  not a units object is recorded per unit and repaired; a verifier rejection's
  `unit=code` rows project onto the attempt and survive the read-back.

| eleven install wordings, strict mode, ADR-0203 runtime, store copy | turns |
|---|---|
| completed, critic approved | 5 (201, 204, 206, 207, 304); ADR-0202 run 4, ADR-0201 run 3, AR-386 run 2 |
| plan-authority units answered; ranked cards outside `eligible_candidate_ids` | 8; **0** |
| `staff_without_safe_team`, any unit | **0** (AR-386 run 5, ADR-0201 run 2) |
| critic `wrong-neighbor-selection` | 3 (203, 205, 208) |
| replies the transport could not read (no JSON object) | 2 (209 repair, 305) |
| reply shapes recorded and repaired (row shape, not a units object, `invalid_decision`) | 3 |

## completed-evidence

**On `main`.** ADR-0203 at `7af9c43b` (PR #595) and `b349e59b` (PR #596):
`_annotate_eligible_candidates`, `_eligible_coverers_by_requirement`, the
repair contract field, the prompt sentences,
`tests/test_recruiter_eligibility_view.py` (4 tests), one curated mutation,
`AR-387-evidence-20260903.txt` with both verifier passes; the frozen record
and done flip (PR #597). ADR-0202 at `760d631e` and `1c1bf079` (PR #591)
with `tests/test_recruiter_reply_residue.py` (16 tests) and AR-373 (#594).

**On the stack.** ADR-0201 at `7c67b524` (PR #588); the AR-384 and AR-386
flips (PRs #589, #590). **Capture recipe.** Scratchpad `capture387.py` to
`capture389.py` (a `_PlanPolicyValidationError` hook, `Store(db_path=<copy>)`),
`critic_replay.py` (patches `_http_payload` with `cache: {"no-cache": true}`),
store copy `agency.db.branch-copy` (generation 307), `PYTHONPATH=<worktree>`.

**Live facts worth keeping.** No `platform` or `desktop` on a plan unit in
33 turns; with the eligibility view the recruiter ranked only eligible cards
on every plan unit. The deployment still returns unreadable replies (209,
305), omits `score`, and once sent a `decision` outside staff/gap (304).

## exact-blocker

Nothing blocks at the contract level. Waiting for the owner: tracker issues
for AR-384 to AR-387 and closure of #537; the stale claude battery re-prove
(`agency battery` from a shell with `common.env` sourced). What remains in
the runtime is judgment and the deployment: three critic wrong-neighbour
vetoes of eleven and two replies the transport could not read.

## same-task-continuity

The previous capsules' traps hold. Three more:

1. **A stored contract does not re-project itself.** `_CATEGORY_DOMAINS`
   changes reach a store only through `reconcile_packaged_workforce_contracts`
   (`agency install`); measure on a reconciled copy.
2. **`plan_policy_violations` needs `known_domains`** beside `served_domains`,
   or a declared `novel_capability` unit is bounced back to the planner.
3. **Receipts re-project on read.** A row admitted only from a detail string
   vanishes when the receipt is read back; the list path must admit it too.
4. **The verifier reads "both prompts state X" literally.** Every prompt a
   criterion names must carry the criterion's phrase, not its consequence.
5. **Live host invocations need the key**: prefix `verify-activation`,
   `host-canary`, `battery` and the hosts with the `common.env` sourcing line.

## next-bounded-work-package

In this order.

1. **Owner steps**: tracker issues for AR-384 to AR-387 and closure of #537;
   re-prove the claude battery with `agency battery` (key sourced).
2. **Name the unset key**: `agency doctor` and the preflight failure receipt
   should say when the configured `api_key_env` is unset in the inspected
   environment instead of only `workforce_provider_unavailable` or
   `codex_collaboration_projection_unavailable`; file it, two-PR flow.
3. **Critic wrong-neighbour judgment on install teams** (203, 205, 208): the
   critic's contract could carry the eligibility view too, so it does not
   veto the only eligible planners as wrong neighbours; measure on the
   eleven wordings with the cache-bypassing replay.
4. **Unreadable deployment residue** (no JSON object, omitted `score`,
   `decision` outside staff/gap): operator territory at the LiteLLM alias;
   recorded, not fixed.
5. **Fix AR-383** per its Approach; then the 4-of-5 gap divergence; then
   AR-370.

## verification

At `b349e59b`: ruff clean but for one pre-existing RUF024; affected suites
197 passed, 1 skipped; named fast spine 1004 passed, 3 skipped under
`-W error`; decision-conformance 175 of 175 killed, tree unchanged;
`docs_metadata.py --check`, `update_worklog.py --check` and `verify_docs.py`
green. Verifier: pass 1 at `7af9c43b` satisfied 1, 2, 4 and contradicted 3;
pass 2 at `b349e59b` satisfied all four (runs `AR-387.N-20260903-*`, in the
record). Every flip so far verified `--all` satisfied. Activation:
`--verify-activation` with the key sourced returned `runtime-verified`,
`canary_passed`, attestation persisted; without it, `host-canary codex
--execute` recorded `preflight_failed`, an empty header and
`native_collaboration_topology_invalid`.

## constraints

- `agency.yaml` is operator configuration (`strict_call_budget`, recruiter
  `timeout_ms`, deployment order, `workforce.mode`).
- Never commit to `main`; worktree branch, PR, merge with `--merge`; ledger
  dance on every substantive commit; tracker writes need authorization.
- The live store was not written by this session; a reconciled copy was.
- Any live host invocation runs from a shell with
  `~/.config/ai-secrets/common.env` (mode 0600) sourced.
