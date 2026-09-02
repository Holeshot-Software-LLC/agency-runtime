---
title: "AR-374 host-capability eligibility handoff"
status: active
category: roadmap
created: 2026-09-02
updated: 2026-09-02
tags: [handoff, workforce, eligibility, staffing]
related:
  - docs/roadmap/issue-AR-374-host-capability-vocabulary-gap.md
  - docs/roadmap/issue-AR-373-recruiter-evidence-vocabulary.md
  - docs/roadmap/issue-AR-336-requalify-the-recruiter-route-for-ordinary-tasks.md
  - docs/roadmap/issue-AR-370-staffing-asks-the-wrong-question.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-374
branch: main
evidence_commit: 2d47e405ce505b8df38d316acd3283d7b460302d
minimum_ledger_commit: 2d47e405ce505b8df38d316acd3283d7b460302d
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/540
---

# AR-374 host-capability eligibility handoff

Start-here capsule for a fresh session. The subject is one question: why can
Agency not staff an ordinary request on this installation, now that every
earlier blocker in the chain is fixed?

## checkpoint

The measurement this issue was filed on is exact and reproduces. The
conclusion drawn from it was wrong, and the issue now records the correction.

`agent_tools_missing` compares the **work unit's** `required_tools` against
the host's proven tools. It never reads `contract.tool_classes`. So the
"219 of 291 workers are permanently ineligible" framing describes no gate in
the staffing path: measured, **0 of those 219** raise `agent_tools_missing`
for a unit that requires no tools, while a worker declaring *no* tools at all
is rejected when the unit demands one the host lacks.

The capsule's own reproduction over-constrained the host. It passed three
tools and omitted `test-execution`, which every real host proves and which
the planner asks for. Re-run with the real nine, the install request planned
three units needing only `repository-read` and `test-execution` — no
`agent_tools_missing` anywhere.

## completed-evidence

Against the bundled 265-card manifest and the live 291-worker store:

- All five execution hosts prove the identical nine capabilities.
- The roster demands 246 distinct tool classes; **238 (97%) are unprovable
  by any host**. `native-delegation` is demanded by no card.
- 218/265 bundled cards (82%) and 219/291 live workers (75%) demand at least
  one unprovable class. Top: `browser-interaction` 55, `web-research` 43,
  `analytics-reader` 27, `database-access` 19.

Hypotheses, all three answered in the issue:

1. Roster over-declares — **rejected as a cause**; produces no ineligibility.
2. Host under-declares — **confirmed and inert**. The floor is a floor:
   `native_adapter_capability_receipt` unions adapter-reported tools onto it
   (`host_capabilities.py:776`), but every production caller omits
   `available_tools` and no detection exists.
3. Vocabulary mis-scaled — **confirmed and dominant**.

Landed: `tests/test_host_capability_vocabulary_drift.py` and
`tests/data/ar374_capability_vocabulary_baseline.json`. Both drift directions
were deliberately induced and both fail the guard with an actionable message.

## exact-blocker

None on the tools axis. On a real host context the tools gate is clear.

The live blocker now is the recruiter: `provider_no_valid_response` on one
run and `provider_response_contract_invalid` on another, with the AR-373 fix
confirmed present in the installed venv. That is a provider or contract
problem and needs its own issue, not this one.

## same-task-continuity

Deterministic, no host and no key needed. Run with cwd outside the checkout
or the working tree shadows the venv:

```bash
V=/home/holeshot/.local/share/agency-runtime/venvs/0abe4a77c87af87cf0d2789df77d40d4a6f80a44
cd /tmp && $V/bin/python - <<'PY'
from agency_runtime.core.host_capabilities import _NATIVE_HOST_CAPABILITIES
from agency_runtime.core.roster.workforce import workforce_index_snapshot
from agency_runtime.core.store.sqlite import Store
snap = workforce_index_snapshot(Store())
nine = set(_NATIVE_HOST_CAPABILITIES["claude"])
blocked = [c for c in snap.contracts if not set(c.tool_classes) <= nine]
print(len(blocked), "of", len(snap.contracts), "demand an unprovable class")
PY
```

To see that this does not gate staffing, pass one of those blocked contracts
and a no-tool unit to `typed_staffing_ineligibility`: the result is `()`.

Traps: a bare harness without `LITELLM_API_KEY` reports
`workforce_provider_unavailable` and looks like a code fault;
`configured_workforce_providers(cfg, stage=...)` is a legacy accessor — read
`out.attempts[*].requested_model` instead.

## next-bounded-work-package

The owner picks one; they have different blast radii and the issue records
all three. Smallest first:

1. Validate the planner's `required_tools` against `host_context.available_tools`
   so an out-of-floor value never becomes a roster-shaped abstention.
2. Collapse the tool-class vocabulary to what a host can prove, moving
   specialism terms off the eligibility axis.
3. Feed real capability detection into `available_tools`.

Two follow-ups are recorded in the issue and have no internal ID yet: the
unvalidated planner `required_tools`, and the upstream selection eval
filtering on `contract.tool_classes` so it cannot reach 82 percent of the
roster.

## verification

1. Hypotheses each confirmed or rejected against measured evidence. **Done.**
2. Unstaffable share stated per host with responsible classes. **Done.**
3. Drift guard pinning the two vocabularies together. **Done**, both
   directions proven to fail.
4. Local gates on every change: focused tests, the named fast Python spine
   under `-W error`, ruff check and format, both docs gates, the worklog
   dance, plus routing and decision-conformance evals if a routing or policy
   surface changed.
5. An ordinary install request staffs a specialist, or the reason it should
   not is recorded. **Open** — blocked on the recruiter provider failure.

## constraints

- Never commit to `main`; branch in a worktree, PR, merge. GitHub Actions is
  off -- prove gates locally: ruff from
  `~/.cache/agency-runtime-ar281-trusted-venv/bin/`, then
  `python3 -m pytest $(WORKFLOW_CONTRACTS + PRODUCTION_SPINE)` with the system
  `python3` (the trusted venv is not an OS-protected interpreter and the
  spine refuses it), plus the mutation-snippet check.
- Ledger dance on every substantive commit; new docs carry `tracker_url`.
- Findings go in repo docs, not the reply. One question per turn. Rule 8.
- `agency.yaml` is operator configuration: do not rewrite model routes
  without the owner's word.
