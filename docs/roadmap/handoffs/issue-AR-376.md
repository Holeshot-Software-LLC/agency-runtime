---
title: "AR-376..379 hiring path handoff"
status: active
category: roadmap
created: 2026-09-02
updated: 2026-09-02
tags: [handoff, workforce, hiring, cost]
related:
  - docs/roadmap/issue-AR-376-hiring-sends-the-entire-workforce.md
  - docs/roadmap/issue-AR-377-hiring-payload-uncached-and-duplicated.md
  - docs/roadmap/issue-AR-378-hiring-failure-records-no-attempt.md
  - docs/roadmap/issue-AR-379-hire-schema-has-no-home-for-domain-procedure.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-376
branch: main
evidence_commit: 3e691161d7c309e9b7bec1d3dd8175d04a0a414e
minimum_ledger_commit: 3e691161d7c309e9b7bec1d3dd8175d04a0a414e
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/550
---

# AR-376..379 hiring path handoff

One capsule for four linked issues, all filed and none started. AR-376, 377
and 378 compound: the payload is huge, it is paid twice uncached, and when it
fails the receipt says nothing. AR-379 is independent and is an owner call.

## checkpoint

Main is green at `3e691161`: worklog current, 990 documents, strict tracker
parity on 370 items. All five hosts install and register; `agency smoke --all`
passes 5/5.

Nothing in the hiring path has been changed. Everything below is measurement.

Do not re-litigate two settled points:

1. **Sending every worker is correct.** The recruiter saw only a bounded
   recall sample (`MAX_HYBRID_DETAIL_CARD_BYTES`) and skips disabled workers
   outright (`inference.py:1568`), so hiring cannot delegate the comparison.
   `_HIRE_SYSTEM` requires an independent check against every worker including
   disabled, and hiring is the last gate before a worker becomes permanent.
   The defect is the *fields*, not the *rows*.
2. **Agency is advisory and never executes.** README.md:1063, ADR-0110,
   ADR-0107. A card describes what the host will do with the expertise.

## completed-evidence

Measured on this box against the shipped 291-worker roster.

- `hiring.py:2009` serializes `[item.to_dict() for item in contracts]`;
  `pipeline.py` passes `active_snapshot.contracts`.
- 1,455 bytes per worker; 463,254 bytes total; litellm reported
  **`prompt_tokens=132,581`** on two separate calls. The route declares
  `max_input_tokens=32768` and does not enforce it.
- A justified projection (identity, capability ids, domains, artifact kinds,
  scope qualifiers, not-for, authority, enabled) measures **137,132 bytes,
  3.4x smaller**. Dropped as unusable for duplicate detection: `version_hash`,
  `audit`, `composition`, `worker_id`, `schema_version`, `archetype`,
  `origin`, `employment`, `display_name`, `platforms`, `hosts`, `stacks`,
  `tool_classes`, `lifecycle_phases`, `context_mode`, `outcomes`.
- Caching: `workforce_cache` is used only by planner (`inference.py:3455`)
  and recruiter (`:3146`); `hiring.py` uses none. `structured_provider.py`
  has no `cache_control`. Two byte-identical back-to-back calls both reported
  `cached_tokens=1,280` of 132,581, **1.0%**.
- `_critic_prompt` (`hiring.py:798`) re-sends `complete_workforce`.
  `_CallBudget(hiring_call_budget)` defaults to 6 and is shared across
  generator, critic and repairs, so one hire can reach **~795k tokens**.
- On failure `_invoke` returns `(None, None)` (`hiring.py:714`) and records
  no attempt: observed `reason_codes=('hiring_inference_failed',)` with
  `attempts=()`, `worker=None`, `contract=None`.
- Hiring *does* work when given room: at a 600s timeout it returned
  `action: hire` in 23.3s and generated `host-time-environment-inspector`.
  Against the configured 30s provider timeout it is a coin flip.

## exact-blocker

None. All four are open and unstarted; the work is available now.

## same-task-continuity

Run outside the checkout or the working tree shadows the venv.

```bash
V=/home/holeshot/.local/share/agency-runtime/venvs/0abe4a77c87af87cf0d2789df77d40d4a6f80a44
set -a; . /home/holeshot/.config/ai-secrets/common.env; set +a
cd /tmp && $V/bin/python - <<'PY'
import json
from agency_runtime.core.roster.workforce import workforce_index_snapshot
from agency_runtime.core.store.sqlite import Store
snap = workforce_index_snapshot(Store())
wf = [c.to_dict() for c in snap.contracts]
print(len(wf), "workers,", len(json.dumps(wf)), "bytes")
PY
```

To read real `prompt_tokens`/`cached_tokens`, POST that payload to
`http://127.0.0.1:4000/v1/chat/completions` as `task-agency-hiring-generator-v2`
with `max_tokens: 16` and read `usage`. To exercise a real hire, call
`hire_contractor_for_gap(..., defer_commit=True)` so nothing persists.

Traps: `agency doctor`'s `max_input_tokens` is metadata, not a limit. A
successful hire at 23.3s does not mean the 30s timeout is safe.

## next-bounded-work-package

Take them in this order; each makes the next cheaper to verify.

1. **AR-378 first, not last.** Record an attempt on failure. Without it every
   other change here is verified blind. Smallest, and it is what cost the most
   diagnostic time.
2. **AR-376.** Scope the projection, justifying each retained field by
   duplicate detection or amend-overlap. Keep every worker, including
   disabled.
3. **AR-377.** Stop re-sending the workforce to the critic, or send only the
   rows its verdict needs; only then consider caching. A cache keyed on roster
   content misses exactly when the roster changes, which is when hiring runs.
4. **AR-379.** Owner decision, no code until it is made. Three options are in
   the issue, including leaving it alone.

## verification

1. Every change proves the local gates: focused tests, the named fast Python
   spine under `-W error`, ruff check and format, the four docs gates, the
   worklog dance, plus the routing and decision-conformance evals because
   `hiring.py` is a policy surface.
2. AR-376 and AR-377 each record measured tokens for one complete hire, before
   and after, including the critic call.
3. AR-378 proves a failing provider yields a non-empty attempts tuple.
4. A regression test pins that the projection cannot silently regain dropped
   fields and that no worker is omitted.

## constraints

- Never commit to `main`; branch in a worktree, PR, merge. GitHub Actions is
  off, so prove gates locally: ruff from
  `~/.cache/agency-runtime-ar281-trusted-venv/bin/`, then
  `python3 -m pytest $(WORKFLOW_CONTRACTS + PRODUCTION_SPINE)` with the system
  `python3`.
- `gh pr merge --rebase` rewrites SHAs, so every ledger row referencing one
  goes stale and `main` needs a follow-up `docs(worklog):` resync. Recover the
  annotations by matching on commit subject, not SHA.
- Run `agency install` under `umask 077`; the ambient umask is 0002 and
  Agency's private-path guard requires the final directory at 0700.
- The decision-conformance eval needs a `--copies` venv whose site-packages
  reaches user-site `pytest`; a symlinked venv resolves to the system
  interpreter and its isolated baseline cannot import pytest.
- `agency.yaml` is operator configuration: do not rewrite model routes without
  the owner's word. A canary pin was added 2026-09-02; backup alongside it.
- Findings go in repo docs, not the reply. One question per turn. Rule 8.
