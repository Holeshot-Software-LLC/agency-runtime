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

## 4. Verdict and next measurement

- Instrument v3 is **live on the machine and unmeasured**: its hypothesis
  (no expertise wording + whole-turn fan-out ban ⇒ clean routing and exactly
  one child) is neither confirmed nor refuted.
- Re-run the three-run v3 series when a recruiter draw validates again
  (cheap probe: any interactive turn routing successfully, or
  `agency eval routing`). No code change is warranted on tonight's
  evidence; the wording change PR #284 shipped is harmless and keeps the
  planner-input hygiene test.
- The v2 positive finding (verbatim handoff proven; judge declines pure
  unit on merits) does not expire with the v3 blockage — it is the
  capture lane's second content-level settlement, recorded in AR-255.

## 5. Carried-over owner decisions

Unchanged from the overnight report section 4: codex attended TUI trust; a
fresh zcode session; whether the cancelled-hook artifact (session
`2b4b19d4`) counts for R8; keep-or-cull the two organically minted
contractors; the embedded-role product question — now sharpened by the
pure-unit decline; openclaw/hermes packet runs.
