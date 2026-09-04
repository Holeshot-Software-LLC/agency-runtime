---
title: "AR-383 inferred subject projection handoff"
status: active
category: roadmap
created: 2026-09-03
updated: 2026-09-04
tags: [handoff, workforce, recall, staffing, hiring, recruiter, critic, planner]
related:
  - docs/roadmap/issue-AR-383-inferred-subject-context-fails-its-own-projection.md
  - docs/roadmap/issue-AR-391-recruiter-prompt-misstates-how-its-ranking-becomes-the-team.md
  - docs/roadmap/issue-AR-390-recruiter-cards-hide-the-outcomes-that-name-the-work.md
  - docs/roadmap/issue-AR-389-critic-judges-neighbours-it-cannot-see.md
  - docs/roadmap/issue-AR-388-unset-credential-reads-as-provider-unavailable.md
  - docs/roadmap/issue-AR-387-recruiter-cards-carry-no-eligibility.md
  - docs/roadmap/issue-AR-370-staffing-asks-the-wrong-question.md
  - docs/decisions/0197-form-the-retrieval-subject-before-the-turn-that-needs-it.md
  - docs/decisions/0203-show-the-recruiter-the-complete-eligible-card-set-per-unit.md
  - docs/decisions/0205-show-the-critic-the-eligible-neighbourhood-it-judges-against.md
  - docs/decisions/0206-show-every-outcome-on-the-card.md
  - docs/decisions/0207-tell-the-recruiter-how-its-ranking-becomes-the-team.md
  - docs/decisions/0208-carry-the-inferred-subject-beside-the-turn-context.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-383
branch: main
evidence_commit: e12c1bddd2cbdf0c9d7a26b09f3c963434375409
minimum_ledger_commit: b1c2b5574c357224bbada8f303917a0154be3984
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/581
---

# AR-383 inferred subject projection handoff

> `main` at `e12c1bdd` carries ADR-0198 to ADR-0212. AR-383, AR-391 and
> AR-396 are closed. Staffing still fails, and the recruiter is where.

Start-here capsule. The planner side is closed, the inferred subject reaches
recall, a complete reply that is not JSON now gets a second ask, and what
remains is the recruiter itself.

## checkpoint

**AR-391 / ADR-0207** (#611-#616): acceptable cards are added only as
typed-coverage complements, the ranking is read as order alone, and a unit's
confidence is the lowest selected rank score. **AR-383 / ADR-0208** (#617):
the inferred subject rides beside the turn context and reaches the planner,
the recall query and the recruiter as `inferred_work_subject`.

**AR-396 / ADR-0212** (#628, merged `b2433867`), five of five criteria
satisfied on the first pass: `_invoke_stage` gave a *complete* reply that was
not a JSON object no second ask, while a cut reply and a contract-invalid one
each got one. Every route resolves to one provider profile, so that ended the
stage on a single call with the attempt allowance and the call budget unspent.
Two staffing turns died there on 2026-09-04 (receipts 17:32:40Z, 17:44:25Z)
while the same planner payload, replayed ten times with the gateway cache
bypassed, answered with valid JSON ten of ten in 12.87-22.83 s. **AR-394** and
**AR-395** were filed in the same PR and are not fixed.

- **Install**: venv `e12c1bdd` is built and is **not** what the hooks run --
  see exact-blocker. Run `agency install` itself WITHOUT the key; codex needs
  the attended `Trust all and continue` in a fresh `codex` TUI, then `agency
  install --agent codex --verify-activation` with `common.env` sourced.
- **Launch environment**: check it first, and mind two traps, both hit on
  2026-09-04. `common.env` carries **no `export` keywords**, so `source
  common.env && claude` leaves the key unexported; use `set -a && . ~/.config/ai-secrets/common.env
  && set +a && claude`. And `pgrep -x claude | head -1` returns the **oldest**
  of about nine `claude` processes: walk up from the shell's `$$` through `ps
  -o ppid=` to the ancestor named `claude`, then read `/proc/<pid>/environ`.
  `/clear` reuses the running process, so a post-launch export never lands.

## completed-evidence

**On `main`.** ADR-0207 at `d3bea30f` (#611) with corrections `2c092cb8`,
`606e70ea`, `3a94b8da`, flipped in #616; ADR-0208 at `169220ce` (#617);
ADR-0212 at `e12d721d` (#628) with `tests/test_non_json_reply_second_ask.py`,
its acceptance record and evidence at `551d08db` and verdicts at `8059fade`.
**Capture recipe.** Scratchpad `capture392.py`, `recruiter_replay_h.py`,
`derive_h.py`, `smoke383.py`, store copy at generation 307,
`PYTHONPATH=<worktree>`; for the 2026-09-04 recruiter runs, the real hook
binary against a copied `agency.yaml` carrying `store.db_path`.

## exact-blocker

**AR-394: the recruiter stage.** With the key reaching the hooks and the
gateway healthy (`/models` 200, 124 deployments, every `task-agency-*-v2`
alias present), staffing still fails. Four live `UserPromptSubmit`
reproductions against an isolated store copy on 2026-09-04: three failed, one
staffed.

| shape | detail |
|---|---|
| `selection_confidence_too_low` then `staff_without_safe_team` | `required_count=1`, `ranked_executable_count=2`, `maximum_selected_per_unit=4`, axis `domain` |
| `invalid_candidate` then `staff_without_safe_team` | same repair outcome |
| `provider_call_timed_out` | the runtime's 30 s deadline against the deployment's 45 s, on a 22,601-token prompt |

A fifth run, instrumented at the verifier, was **accepted** with
`roblox-systems-scripter` on a rate-limiting unit at confidence 0.9 against
the 0.8 floor. Both halves are one problem: weak candidate sets are either
rejected or staffed. Every failing run also carried `recall_reranker:
provider_response_contract_invalid` from the local
`qwen3-14b-abliterated:latest` profile.

**The AR-396 fix is on `main` and is not live.** `agency install --agent
claude` from the `e12c1bdd` venv registers the plugin, then reports *"the
published projection still differs from this CLI; your hooks did not pick up
this source"*: they stay staged from venv `afe1a92e`, and
`install_commands.py:1799-1803` says a foreign-package report cannot survive
an install from this package, so the pointer was not rewritten. Owner step;
`agency upgrade --channel main` prints the intended command.

Also owner-side: tracker issues AR-384 to AR-396, closure of #537, `agency
battery` with the key sourced (`harness_battery_claude` fails in `agency
doctor` today), and the attended codex trust.

## deployment-residue

Named, not gone. ADR-0209 split the causes; the configuration half stands:
every workforce profile in `agency.yaml` carries `timeout_ms: 30000` while
every deployment behind the three v2 aliases carries `timeout: 45.0`, so a
call answered between 30 and 45 seconds is aborted by the runtime's own socket
deadline. Seen live again on 2026-09-04 as a recruiter
`provider_call_timed_out`. Operator configuration either way; AR-392 c1 is the
code half and is still open.

## same-task-continuity

Earlier capsules' traps hold (one `&&` chain, never `tail` on a gate; the
verifier reads a criterion's phrase literally in every prompt it names; a
phrase split across adjacent literals still counts; a live run and the
conformance eval cannot share a tree). Four more, all from 2026-09-04:

1. **`git checkout <ref> -- .` inside a worktree silently reverts your working
   tree** while leaving HEAD alone. Compare with `git show <ref>:<path>` or a
   second worktree.
2. **`ruff check` and `ruff format --check` do not pass on `main`**: pinned
   0.15.20 reports 11 findings and 12 unformatted files tree-wide. Gate on
   *parity* with that baseline, and format only what you touched.
3. **Reproduce hooks against a copied store**: append `store: {db_path: <copy>}`
   to a copied `agency.yaml` and drive the real hook binary.
4. **LiteLLM caches completions in Redis**; send `cache: {"no-cache": true}`.

## next-bounded-work-package

In this order; 4-6 are gated behind 1 and 2.

1. **Make `e12c1bdd` live.** The AR-396 second ask cannot help a turn while
   the hooks run `afe1a92e`.
2. **AR-394**, the recruiter stage: what an unavailable header means today.
3. **AR-395**, two lines plus a test: add `subject`, `security_review` and
   `safety_repair` to `PREFLIGHT_PROVIDER_STAGES`. Take it before 4-6; it
   makes every receipt they read legible.
4. **AR-370 c1**: "configure the gateway" and "install this: <url>" score 0.0
   against all 291 live contracts and fall back to slug order.
   `service-operations-engineer` and `monitoring-engineer` are in
   `core/evals/data/routing_v1.py` but not in the live roster.
5. **AR-392 c1**, verifier-contradicted: attempts record `latency_ms`, not the
   configured timeout. Every attempt in a fresh 2026-09-04 receipt has
   `latency_ms: None`.
6. **AR-393 c5**: the after-install window holds zero declaring receipts.

## verification

`169220ce` (AR-383): new tests 6; affected 493; spine 1165 under `-W error`;
conformance 182 of 182. `d3bea30f` plus three corrections (AR-391): new tests
6; affected 239; conformance 180 of 180; verifier six of six on pass three.
`e12d721d` (AR-396): new tests 9, four of which fail on `main`; affected 201;
docs, hygiene, metadata, ledger and whitespace gates pass; ruff at parity with
`main`; verifier five of five on pass one.

## constraints

- `agency.yaml` is operator configuration (`strict_call_budget`, recruiter
  `timeout_ms`, deployment order, `workforce.mode`). Never commit to `main`;
  worktree branch, PR, merge with `--merge`; ledger dance on every substantive
  commit; tracker writes need authorization.
- The live store is read-only to a session; reconcile a copy instead. Any live
  host invocation runs from a shell with `~/.config/ai-secrets/common.env`
  (mode 0600) sourced under `set -a`.
