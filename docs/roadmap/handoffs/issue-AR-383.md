---
title: "AR-383 inferred subject projection handoff"
status: active
category: roadmap
created: 2026-09-03
updated: 2026-09-04
tags: [handoff, workforce, recall, staffing, hiring, recruiter, critic, planner]
related:
  - docs/roadmap/issue-AR-394-recruiter-teams-fail-or-mis-select.md
  - docs/roadmap/issue-AR-395-preflight-stage-vocabulary-is-incomplete.md
  - docs/roadmap/issue-AR-392-transport-failures-collapse-to-one-code.md
  - docs/roadmap/issue-AR-393-declared-gaps-leave-no-hiring-account.md
  - docs/roadmap/issue-AR-370-staffing-asks-the-wrong-question.md
  - docs/roadmap/issue-AR-396-a-non-json-reply-gets-no-second-ask.md
  - docs/roadmap/issue-AR-383-inferred-subject-context-fails-its-own-projection.md
  - docs/decisions/0212-ask-again-when-a-complete-reply-is-not-json.md
  - docs/decisions/0209-name-the-transport-cause-instead-of-one-code.md
  - docs/decisions/0208-carry-the-inferred-subject-beside-the-turn-context.md
  - docs/decisions/0207-tell-the-recruiter-how-its-ranking-becomes-the-team.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-383
branch: main
evidence_commit: d757c3b9d128ee911d931a5ef307567433861c83
minimum_ledger_commit: b1c2b5574c357224bbada8f303917a0154be3984
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/581
---

# AR-383 inferred subject projection handoff

> `main` at `d757c3b9` is unchanged by this session; five branches are open
> as PRs #632 to #636 and every closure below is branch-only until they merge.
> The recruiter is still where staffing dies, and the receipt now says why.

Start-here capsule. The install was already live, the recruiter's dominant
failure now names its cause, and the live-gated criteria are measured.

## checkpoint

**"Make e12c1bdd live" was already done.** The prior blocker was a misread:
`agency install --agent claude` ends by printing `reports[0]` of a *per-host*
drift list under a fixed line that names no host, and that report was codex's
(still on `afe1a92e`), not claude's. Proven three ways on 2026-09-04:
`launchers/current-claude.json` points at the `e12c1bdd` venv; the launcher
tree `runtime-sha256-df819e98…` is byte-identical to the checkout for every
file under `agency_runtime/` (one stale extra, `core/selector/domain_expansion.py`,
imported by nothing); and the `claude` process started at 14:54:01 local,
twenty minutes after `hooks.json` was rewritten. The AR-396 second ask was
visible on this session's first receipt. **Never read that warning as a claim
about the host you installed**; run `cli_install_drift_reports()` from the venv
and read each report's `host`.

**AR-395 / PR #632**, `eeb98653`, four of four verified on the first pass. The
issue named three missing stage labels; the AST scan the new test performs
found **six** — `hiring-critic`, `hiring-repair` and `hiring-repair-critic`
were also being written as `unknown`. AR-385's `STAGE_REPLY_BUDGET_TOKENS`
already enumerated all six, and the test now holds the two tables together.
No ADR: completing a list decides nothing.

**AR-394 / PR #633 / ADR-0213** (on that branch), `c2a923d4`, five of five
verified first pass, conformance 182 of 182. `SAFE_TEAM_SHORTFALL_CODES`: eight
closed causes on every `staff_without_safe_team` row, projected as
`safe_team_shortfall`. Absent-from-retrieval against present-and-ineligible is
one coverage question asked over the shown cards and then the whole roster:
`coverer_absent_from_retrieval` against `ranked_candidates_ineligible`. The
total classifier found the "budget starvation" tests mis-telling their fixture
(`complement_slots_exhausted`). ADR-0213: the verifier judges safety, retrieval
judges fit — all 33 verifier codes are structural, the roster held
`api-platform-engineer` beside `roblox-systems-scripter`, and the reranker's
20.4% contract-invalid rate costs candidates, not order, under additive recall.

**AR-392 / PR #634**, `0ff7d390`, re-frozen and five of five re-verified.
Criterion 1 had been contradicted for want of the configured timeout; the
real finding was that **no duration reached the durable receipt at all** —
1289 of 1289 attempts across the last 400 receipts carried neither figure.
Both attempt records now carry `timeout_ms`, and the projection carries both,
**added only when present**: `_native_child_route_projection_is_valid`
re-projects a stored route and requires a fixed point, and eleven host
delivery-proof tests failed when the keys were unconditional.

**Live operator change, criterion 4 of AR-394.** Every deployment behind the
six `task-agency-*-v2` aliases carries `timeout: 45.0` (read from
`GET /model/info`, 133 deployments). The six routed profiles that sat at
`timeout_ms: 30000` in `~/.agency-runtime/agency.yaml` are now `60000`; the
previous file is `agency.yaml.bak-ar394-20260904T192436Z`. `agency doctor`
reads every routed profile at 60 s or 120 s. The very next turn's second ask
completed instead of being cut at 30 s.

## completed-evidence

Branch commits, none on `main`: AR-395 `eeb98653`/`a0527fd7`; AR-394
`c2a923d4`/`f8cec26c`; AR-392 `0ff7d390`/`f3241502`; AR-370 `5e08435b`;
AR-393 `18c04e21`. Acceptance records frozen at the first SHA of each,
evidence files under `docs/roadmap/acceptance/evidence/`, verdicts recorded.
Recipe: copy the store; `GET /model/info` with the key for deployment facts;
`agency search` from the `e12c1bdd` venv, key-free, for retrieval.

## exact-blocker

**Staffing still ends at the recruiter, and now at the planner too.** Across
the last 400 receipts the recruiter was `provider_response_contract_invalid`
on 395 of 529 attempts (74.7%). On this session's own turns the planner
returned `provider_model_text_not_json` twice in a row — the AR-396 second ask
fired, both replies were prose — so the recruiter never ran. That is the
gateway's `task-agency-planner-v2` deployments (`chatgpt/gpt-5.5`,
`openai/glm-5-turbo`) answering with text; it is not a runtime defect and no
code on any branch addresses it. Until a recruiter proposal is accepted:

- **AR-393 c5** cannot be measured: zero receipts declare
  `no_safe_sufficient_team` since the fix landed (16:01Z), and zero since the
  last declaring receipt at `2026-09-03T18:42:33Z`; the 150 receipts since all
  end at routing. The record was re-frozen at `18c04e21` and re-verified: four of five
  satisfied, criterion 5 **contradicted** — the verifier reads it literally,
  and zero over an empty window is not the count it asks for, nor are the 42
  pre-fix rows named. Open until a staffed turn declares a gap.
- **AR-370 c1** is a **roster addition** (PR #635, doc-only): both phrases
  score 0.0 against all 291 live contracts and fall back to slug order; the
  two corpus cards are eval fixtures and no operations division exists live.
  Owner-authored contracts via the `agency-runtime` source, then a staffed turn.

## deployment-residue

The timeout half is closed live (above). Two unfiled observations: `agency
doctor` says `adapter_claude: not natively registered` while the hooks fire
every turn; and `_workforce_timeout_checks` says the deployment timeout is
unreadable, yet `/model/info` returns it for all 133 deployments.

## same-task-continuity

Every earlier trap holds. Five more from this session:

1. **The install drift warning is host-agnostic.** See checkpoint.
2. **`decision-conformance` must run from `agency-conformance-venv`**; the
   system interpreter fails the baseline and reads `killed=0/182`.
3. **The projected attempt dict is a delivery-proof input.** A key added to
   `project_model_receipt_attempts` unconditionally breaks the fixed point
   `_native_child_route_projection_is_valid` requires. Add only when present.
4. **One heredoc per shell call, `&&` after every gate.** Two heredocs in one
   chain committed a script as a subject; a `;` after `verify_docs.py` let a
   commit through. Write messages with `printf` to a file.
5. **A moved candidate re-binds every digest**: re-freezing a record means
   re-verifying every criterion, not the one you changed.

## next-bounded-work-package

1. **Merge in order: #632, #633, #634, #635, #636.** After #632 each later
   branch conflicts only on `docs/worklog/README.md` (append-only rows, keep
   both) and #633 on one `docs/roadmap/README.md` row. Not rebased: a rebase
   would orphan the frozen candidate SHAs. `git merge origin/main` per branch.
2. **`agency install --agent claude` from the merged venv**, without the
   key, then confirm with `cli_install_drift_reports()` per host.
3. **The planner's prose replies.** Replay the failing planner payload against
   each `task-agency-planner-v2` deployment with `cache: {"no-cache": true}`
   and see which one answers with text; this is operator deployment order.
4. **The two operations contracts** for AR-370 c1, owner-authored through the
   `agency-runtime` source: `service-operations-engineer` and
   `monitoring-engineer` as `routing_v1.py` already describes them.
5. **The doctor timeout check** could compare against `/model/info` — small,
   and it would have caught criterion 4 by itself.

## verification

AR-395: 10 new tests (8 fail on `main`), verifier 4 of 4. AR-394: 28 new,
10 failed of 1663 selected and the identical set on `main`, conformance 182
of 182, verifier 5 of 5. AR-392: 5 new, 32 failed of the wider selection and
the identical set on `main`, verifier 5 of 5 after re-freeze. Ruff at parity
(7 findings, 11 files); `verify_docs.py` passes on every branch.

## constraints

- `agency.yaml` is operator configuration and was changed live with a dated
  backup; `strict_call_budget`, deployment order and `workforce.mode` were not
  touched. Never commit to `main`; worktree branch, PR, merge with `--merge`;
  ledger dance on every substantive commit; tracker writes need authorization.
- The live store is read-only to a session; every measurement above is from a
  copy. Live host invocations need `common.env` sourced under `set -a`;
  `agency install` runs without the key.
