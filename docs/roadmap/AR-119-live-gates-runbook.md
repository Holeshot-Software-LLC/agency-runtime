---
title: "AR-119/AR-125 live-gates runbook"
status: active
category: roadmap
created: 2026-07-25
updated: 2026-07-25
tags: [roadmap, evaluation, live-gates, canary, AR-119, AR-125]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/issue-AR-178-evaluate-one-shot-applications-post-production.md
  - docs/roadmap/AR-119-acceptance-evidence.md
  - docs/decisions/0087-inference-decides-from-a-relevance-shortlist.md
  - docs/decisions/0102-defer-one-shot-application-evaluation.md
supersedes: []
superseded_by: null
type: roadmap
---

# AR-119 / AR-125 live-gates runbook

The deterministic acceptance for AR-119 and AR-125 is met and merged (`c6bc953`):
inference-first selection, the offline typed-recall floor, the stamped
`Recruited via` header, ZCode as the 5th host, enrichment wiring, full per-worker
selection-safety across all 272 workers, and the sharded CI (AR-117). The
remaining gates that keep #132 (AR-119) and #138 (AR-125) open are **live
execution gates** — they require a configured inference provider and, for
canaries, real host sessions.

## Resolved: enrichment now reaches the live route (read-time overlay)

A live `agency route` on a security-review ask previously abstained with
`no_safe_sufficient_team` even when the recruiter nominated the right specialist
as required and it was executable. Root cause: the planner emits units requiring
capabilities like `threat-modeling`/`audit`/`risk-analysis` (valid
`CORE_CAPABILITY_IDS`), but the security specialists' stored workforce contracts
declared only `analysis`/`review`/`testing`.

**Fixed** (PR #143): the enrichment overlay now adds these capabilities
(`roster/data/scope_qualifiers.json`), the loader processes `task_types`
(`roster/enrichment.py`), and `apply_enrichment_to_contract` applies the overlay
**at read time** in `workforce_index_snapshot` (`roster/workforce.py`) — option 3
from the original options list. This respects durable contract immutability (the
stored version is untouched) while the live route sees enriched
`capability_ids`/`stacks`/`domains`/`scope_qualifiers`.

**Verified live:** `agency route "Review this Python authentication code for
correctness and security"` now **accepts** reliably (3/3 runs) with a governed
5-unit team: `codebase-onboarding-engineer` (discovery) → `code-reviewer`
(correctness, 2 units) → `ai-generated-code-security-auditor` (security, 2
units), confidence 1.0. All 95 workforce/selection/staffing tests + 124
roster/hiring/cache tests pass.

## Prerequisite: configure a provider

Every live gate below requires at least one inference provider. The development
config at `~/.agency-runtime/agency.yaml` has the codex-subscription provider
(`gpt-5.6-luna`, low effort, transport codex); load it via `load_config()` (the
direct `AgencyConfig()` constructor does not read the file). Also set
`workforce.fast_call_budget = 2` (the default 1 exhausts the budget before the
recruiter runs).

---

This runbook is the exact, ordered procedure to close the live gates once the
enrichment-propagation blocker above is resolved and a provider is available.

## Prerequisite: configure a provider

Every live gate below requires at least one inference provider. Configure one
(for example the codex-subscription provider used during development):

```bash
agency config provider set codex-subscription \
  --type cli --transport codex --model gpt-5.6-luna \
  --reasoning-effort low --timeout 60
agency config validate
```

Confirm: `agency config show` lists at least one provider, and
`agency route "review this code" --json` returns a non-empty `selected_ids` with
`source: workforce_inference` (not `deterministic`).

## Fixed controls (do not change between gates)

- Roster generation 263 (272 governed workers after seeding known contractors).
- Provider/model/reasoning-effort as configured above; one compact planner call
  plus at most one bounded recruiter call (15000 ms cold gate).
- No scenario-specific routes, no weakened typed coverage.
- Malformed / timed-out / no-response upstream arms are **validity failures,
  never losses**.

## Gate 1 — small live smoke (proves the runtime end-to-end)

Before the heavy corpus, confirm the integrated path fires on the configured
provider. Telemetry first (`scripts/context_handoff_status.py --json --threshold 50`).

Prompts (config-valid arms only):

1. "Review this code for correctness and security"
2. "Fix the authentication bug"
3. "Write unit tests"
4. "Design a Git branching strategy" (multi-unit; expect `git-workflow-master`
   required + selected)

Expected: each returns `Recruited via: inference`, a correct specialist/team,
and the response header renders in the host. Malformed/timed-out arms are
recorded as validity failures, not losses.

## Gate 2 — ZCode main-session header + host canaries (#132 / #138)

- **ZCode header (main session):** in a real ZCode session with Agency
  installed, send a prompt and observe the Agency header (`[AGENCY PREFLIGHT]`
  + resident-manager kernel) and the `Recruited via:` line. The integration path
  is proven by `tests/test_zcode_header_proof.py`; this is the live confirmation.
- **5-host canaries:** run `agency smoke --agent <host> --json` for codex,
  claude, hermes, openclaw, and zcode. Each must report `passed: true` (zcode
  appears as `skip` on runners where it isn't installed — that is correct).

## Gate 3 — Agency-on/off paired graded-outcome corpus (#132 / #138)

The north-star proof. Run the held-out comparison corpus through both arms under
matched roster, host/model, workspace, and grading:

- **Agency-on arm** is valid only when the planned specialists were actually
  activated in the contexts that performed their units (check the `Recruited via`
  + activation receipts). Missing activation = invalid participation evidence,
  not a win or loss.
- **Agency-off arm** = the same host/model with Agency disabled (`agency off`).
- **Baseline** = the pinned upstream selector revision (recorded in the roster
  manifest).
- Grade artifacts blind to mode. Predeclare thresholds and graders; do not tune
  against the held-out set.

Release requires: zero forbidden/incompatible Agency selections, no
critical-domain regression, and a statistically defensible material improvement
in helpful-team selection and completed outcomes over the pinned upstream
baseline, within the synchronous latency contract.

Two complete corpora previously produced 19/19 safe Agency passes; the newest
returned 17/19. No corpus has yet produced 19 benchmark-valid upstream arms.
Obtain one complete corpus with 19 valid comparable upstream arms before any
defect claim.

## Gate 4 — reinstall verification (#132 / #138)

Reinstall the merged artifact on Windows and Linux and run the artifact smoke
(`agency smoke --all --json`). Verify exact-version specialist activation in the
performing context. A deterministic host contract is not a live runtime canary:
keep discovery, registration, enablement, loading, and canary claims separate in
evidence.

## Closure

- **#138 / AR-125** may close after its selection, matched-outcome, five-host,
  and exact-current artifact evidence in Gates 1–4 passes.
- **#132 / AR-119** (the umbrella) closes **last**, only after Gates 1–4 all
  have current evidence, the final PR is green + merged, and the installed
  artifact is verified. Closure needs explicit authorization. Until then both
  stay OPEN; `verify_tracker.py --allow-open-complete` may be used for a
  read-only parity audit in the meantime.

Complete one-shot applications are deferred to #153 / AR-178 as a non-blocking
post-production evaluation. They are not a prerequisite for either closure.
