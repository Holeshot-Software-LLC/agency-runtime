---
title: "AR-355: Deliver the owner's working agreements as a second resident manager and make the steward roster-aware"
status: done
category: roadmap
created: 2026-09-01
updated: 2026-09-02
tags: [resident-managers, steward, prompt-surface, governance]
related:
  - docs/roadmap/issue-AR-265-contextual-turn-classification.md
supersedes: []
superseded_by: null
type: issue
epic: product
issue_id: AR-355
priority: p2
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/422
depends_on: []
blocks: []
---

# AR-355: Deliver the owner's working agreements as a second resident manager and make the steward roster-aware

## Problem

The owner wants two things on every turn, on every host: (a) five
engineering working agreements, and (b) the steward to be
agency-aware. Today the only every-turn, cross-host injection surface
Agency owns is the resident-manager channel, and it carries exactly one
manager (`agency-steward`), whose kernel is deliberately a short
governance contract (turn framing, evidence boundary,
anti-self-staffing). Folding conduct norms into the steward would
dilute a contract where every line binds, and kernel edits are
versioned events (the kernel hash is pinned in bindings and header
contracts), so the wording could not be tuned without a release.

## Owner authorization

Design agreed with the owner 2026-09-01 in-session: a second resident
manager carrying the working agreements, config-sourced so the owner
edits wording without a code release; plus one descriptive
roster-awareness line in the steward (kernel v5). Awareness only — the
steward must never imply or instruct delegation: staffing identity
comes from recorded inference, and a delegation-nudging steward would
push hosts toward self-staffing (the failure class the critic and
AR-265 exist to prevent).

## Proposed working-agreements manager text (owner-editable)

> [Working agreements — owner]
> 1. Ask, don't assume. When something is unclear, ask before writing a
>    line. Never make silent assumptions about intent, architecture, or
>    requirements. Running unattended, pick the most reasonable
>    interpretation, proceed, and record the assumption rather than
>    blocking.
> 2. Implement the simplest solution for simple problems and better
>    solutions for harder problems. Do not over-engineer or add
>    flexibility nothing needs yet.
> 3. Do not touch unrelated code — but surface bad code and design
>    smells you discover to the owner as separate recorded issues.
> 4. Flag uncertainty explicitly (see 1). Where it helps, run a small,
>    localised, low-risk experiment and bring the hypothesis and
>    results for discussion. Confidence without certainty causes more
>    damage than admitting a gap.
> 5. Better ideas are always welcome — especially durable improvements
>    over tactical changes. Do not hesitate to suggest one.

## Proposed steward addition (kernel v4 → v5, one line)

> A governed workforce of specialists exists. When this turn's capsule
> names specialists, treat them as present expertise; when it names
> none, the turn is honestly unstaffed.

## Approach

1. Discover how resident managers are defined, hashed, and delivered
   (`RESIDENT_MANAGER_SLUG_SET`, kernel rendering, the `managers=` list
   in the binding line) and what pins the kernel hash (bindings, header
   contract, batteries).
2. Add a `working-agreements` manager whose body loads from
   owner-editable config (default text above shipped as the fallback),
   with its own content hash in the binding line for auditability.
3. Bump the steward kernel to v5 with the single roster-awareness line;
   re-wire and battery per the version-change discipline (AR-337).
4. Budget check: measure the added per-turn tokens on the smallest
   context host (hermes) before shipping.

## Dependencies

- Owner review of the two text blocks above before implementation.

## Implementation (2026-09-01)

Discovery changed the shape, in the direction the design wanted: the
runtime already ships the exact owner channel — `operator_policy`
(config field, bounded 2048 chars / 40 lines, rendered with its own
header/footer, content-hashed separately from the kernel, injected
every turn beside the steward). The "second resident manager" is
realized by that shipped block rather than new manager plumbing: the
five working agreements are now set as this installation's operator
policy (`agency config set operator_policy --stdin`), live-verified in
a fresh preflight capsule (policy block, agreement text, and
never-blocks footer all present) with no deploy required, and
owner-editable exactly as specified. One rendering note: the YAML set
flattened the numbered list onto one line; content is intact and the
numbering keeps it readable.

The steward roster-awareness line landed as kernel v4 → v5
(`resident_managers.py`): version 5, budget 1024 → 1280 chars (the
kernel sat at 1014/1024), the approved line added after the
delegation-neutrality sentences, and the v5 pins extended so the
awareness line and the anti-self-staffing guarantees must both survive
any later trim. Binding reuse re-injects automatically on contract
change (`_row_uses_current_contract`), so v5 needs only the ordinary
runtime deploy, riding the next cycle together with AR-346.

Deploy update (2026-09-01 evening): the combined cycle ran — venv
respun at main `c887190d`, all four hosts re-wired to launcher
projection `eed132308c55` (verified to carry the v5 kernel header and
the AR-346 status set), codex hooks re-trusted (`runtime_verified`),
hermes and the openclaw gateway restarted, and all four harness
batteries passed with the baseline adopted (claude 2.1.257, codex
0.152.0, hermes 0.21.0/7cd91114, openclaw 2026.8.2). Stage-complete;
the remaining boxes await a live v5 binding observation from a fresh
persistent session (existing sessions keep their pre-deploy hooks by
design — the deploy session itself still binds v4) and the token-cost
measurement. Measurement method note (owner-approved lift, 2026-09-01):
use a context-budget audit — per-component token estimates for kernel +
operator policy + capsule + header snapshots per turn — in the shape of
ECC's `context-budget` skill.

## Acceptance

- [x] Every staffed and unstaffed turn on all four hosts carries the
      working agreements alongside the steward, and the text is
      changeable through owner config without a code release
      (delivered via the shipped `operator_policy` block; live-verified
      2026-09-01).
- [x] The steward carries the roster-awareness line and still never
      implies delegation; the anti-self-staffing language is unchanged
      (live-observed 2026-09-01 ~21:55Z: a persistent claude session
      rebound to `rmb-ab4a5952…` with `kernel=v5:62c94d87…`,
      `delivery=injected`, and the delivered kernel text carries the
      approved line between delegation-neutrality and
      anti-self-staffing).
- [x] Kernel v5 lands through the version-change discipline (re-wire +
      battery), with the binding line reporting the manager and kernel
      hash (v5 rode the 2026-09-01 deploy cycles with all four
      batteries green; the "both managers" wording resolved to steward
      kernel + separately-hashed operator_policy block per the
      implementation section).
- [x] Per-turn token cost of the addition is measured and recorded —
      `agency evidence context-budget` (this change) sizes each component
      with the code that renders it; measured 2026-09-02 on this
      installation (tiktoken cl100k_base as the proxy tokenizer, chars/4
      otherwise): steward kernel v5 1187 chars / ~254 tokens; the v5
      roster-awareness line 173 chars / ~35 tokens; the live five-line
      operator policy block 1456 chars / ~290 tokens; binding line 292 /
      ~120; routing context (two specialists) 818 / ~183; UserPromptSubmit
      header snapshot 523 / ~114; the AR-356 disclosure line 291 / ~59.
      The AR-355 addition therefore costs ~325 estimated tokens per ready
      turn (kernel line plus policy block) on claude/codex/zcode; a whole
      fail-open turn is ~837 tokens with the kernel injected and ~583 once
      the binding is reused (AR-367), and a staffed turn ~1552 tokens with
      the median replayed specialist capsule (2895 chars, 5 staffed ready
      turns replayed from the newest 52).
