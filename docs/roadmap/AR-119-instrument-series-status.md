---
title: "AR-119 instrument-series status for 2026-08-17 evening"
status: draft
category: roadmap
created: 2026-08-17
updated: 2026-08-17
tags: [roadmap, report, autonomous, AR-119, AR-255, AR-258, canary]
related:
  - docs/roadmap/AR-119-overnight-report.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/roadmap/AR-255-child-parity-design.md
  - docs/roadmap/AR-119-rule-host-evidence-matrix.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
supersedes: []
superseded_by: null
type: reference
issue_id: AR-119
---

# AR-119 instrument-series status, 2026-08-17 evening

**Your machine is running main's build: all three hosts (claude, codex,
zcode) pin runtime digest `084dd1851ca6…` — main tip `58af4d0c`, the merge
of PR #284 — with the installing tree verified identical to main's, store
schema 47, and doctor showing only the baseline cold-inventory warnings plus
the known codex attended-TUI trust item.** AR-258's one-digest property held
through both of today's install rounds: `512f41fd5859` (main `dfd482d0`) →
`d2d0119a492b` (merge `28f5e835`) → `084dd1851ca6` (merge `58af4d0c`).
`~/.agency-runtime/overnight-runtime-state.json` carries the same facts.

## 1. What merged

- **PR #283** (`28f5e835`): instrument v2 — the canary parent prompt demands
  an exclusive verbatim work-unit handoff (no role, no persona, no framing,
  nonce excluded), golden-pinned in tests, codex recognizer moving by
  construction. Merged only after a CodeQL rerun cleared a GitHub-side HTTP
  503 in the capability probe; every check that executed passed.
- **PR #284** (`58af4d0c`): instrument v3 — drops the "any expertise they
  need" clause (a regression test bans expertise/skill/capability/staff
  substrings in the prompt), bans environment inspection for the whole turn,
  ends with an explicit stop.

## 2. The v2 series (build `d2d0119a`): the finding that stands

Run 3 of the v2 series produced the day's positive result, in content:

- The parent handed its first child an assignment **exactly equal to the
  work unit** (decision `fc68eb32`, capture == unit, 138 chars). The
  verbatim-handoff goal of the instrument fix is proven live.
- The child judge **still declined** that pure assignment
  (`native_child_no_specialist_needed`; the funded repair produced no valid
  answer on that draw). **The embedded-role hypothesis is refuted for this
  unit: the decline is on the unit's own merits.** Whether a one-paragraph
  review brief is below the judge's card threshold is now the open product
  question (AR-255).
- The parent also spawned two post-return inspection errands (both
  `native_child_abstention_confirmed` — correct declines), so single-child
  collection refused with `multiple_child_artifacts`.

## 3. The v3 series (build `084dd185`): 0/3, with an honest correction

All three serialized v3 runs failed before the instrument could be
measured, and the failure pattern **refutes the v2-series attribution I
shipped in PR #284's rationale**:

- Run 1 (session `059ee7ea`): the planner call itself returned
  `provider_no_valid_response` → `workforce_provider_unavailable`. The
  prompt was never evaluated.
- Runs 2-3 (sessions `c77b21d3`, `64159eaa`; receipts `a85e4621`,
  `8c2bb917`): planner fine (correct one-unit review plan), then the
  recruiter response was rejected twice per run with
  `staff_without_safe_team` — **with the v3 prompt live in the run row and
  no expertise wording anywhere**. The clause was not the cause.
- The mechanism, read precisely from `_validate_nomination_decisions` and
  the receipts: the recruiter (sonnet via CLI) returns decision **"staff"
  with a ranked list but an empty selection** — a self-contradictory
  response the contract rightly rejects. The empty top-ranked-ineligibility
  field on the bare `code-reviewer` rejection proves the top candidate was
  deterministically executable; the model simply declined to select it.
- The same shape hit the resident-manager session on an unrelated clarify
  unit (receipt `6edd86ad`), and the morning's series was clean on
  code-identical routing. Every arrow points **provider-side**: sonnet's
  structured recruiting behavior drifted or degraded during the same window
  GitHub's API was returning 503s. This is AR-253 evidence, not an
  instrument defect and not a runtime regression.

## 4. The re-measured series (same evening) and the verdict

After `eval routing` passed and two live draws validated, the three-run
series was re-run (runs at 20:00, 20:06, 20:11 UTC):

- **Runs 1-2 measured clean and identically**: parent routing accepted
  (`891ef137`, `caf73863` — `code-reviewer` selected AND loaded, a series
  first), **exactly one child** (the whole-turn fan-out ban worked; v2's
  run had two inspection errands, these had zero), and the child's
  captured assignment **equaled the work unit exactly, both runs**. The
  judge declined the pure unit both times — run 2's decline is
  `native_child_abstention_confirmed` (`0165dff0`): the funded repair ran
  and the judge reaffirmed against the concrete set. That is the
  strongest-form decline the runtime can record.
- **Run 3 hit the recruiter defect again** (`workforce_inference_failed`,
  receipt `c3007311`): the provider-side flakiness is intermittent, not
  cleared — roughly one draw in three still fails this evening.
- Two v3 acceptance conditions met (equal-text capture; exactly one
  child); the third — no security-team padding — **failed both clean
  runs**: `application-security-engineer` rode alongside `code-reviewer`
  each time.

**Verdict:** the instrument is fixed and its question is answered. A child
handed a pure one-paragraph review unit, judged over the complete
universe, with a card selected and loaded at the parent, is declined —
repair-confirmed. Rule 4's remaining blocker on claude is not a wiring
defect, an instrument confound, or a routing accident: it is the judge's
card threshold for small units, which is an owner-level product question
(does a one-paragraph brief merit a card, or is silence correct?). The
parent-side header and the recruiter's intermittent contract failures
(AR-253) are the two runtime-side items still open.

## 5. Addendum: the small-unit policy series (build `cc478bc8`)

The owner ruled the same evening: **small units still get cards.** PR #287
(`99a7b3ac`) shipped the policy into the complete-universe judge prompt —
task size named a non-reason for an empty selection, coverage the only
decline ground, abstention escape kept — and all three hosts reinstalled
on one digest `cc478bc88258`. The three-run acceptance series then went
0/3 **on provider flakiness alone**, but run 2 moved the frontier:

- **Run 2 proved the parent chain fully green for the first time**:
  routing accepted with `code-reviewer` ALONE — the security-team padding
  is gone — and the parent emitted a **valid Agency header**, the first of
  any isolated-profile canary today. The chain then died at the child
  stage: `native_child_inference_unavailable` (the provider dropped the
  child judge's draw), so the policy itself is still unjudged.
- Runs 1 and 3 died at parent preflight (`workforce_provider_unavailable`,
  `workforce_inference_failed`) before reaching the instrument.

**Standing acceptance, unchanged:** one clean child draw that STAFFS the
pure work unit and the first `native_child_delivery_verifications` row
ever. Everything deterministic in the chain has now been proven green at
least once; the only remaining variable is a provider draw that survives.

## 6. Carried-over owner decisions

Unchanged from the overnight report section 4: codex attended TUI trust; a
fresh zcode session; whether the cancelled-hook artifact (session
`2b4b19d4`) counts for R8; keep-or-cull the two organically minted
contractors; the embedded-role product question — now sharpened by the
pure-unit decline; openclaw/hermes packet runs.
