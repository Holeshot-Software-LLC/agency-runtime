---
title: "AR-253: Dynamic team dispatch on every harness — close the last four gaps"
status: open
category: roadmap
created: 2026-08-05
updated: 2026-08-05
tags: [workforce, staffing, delegation, harnesses, eval, doctrine]
related:
  - docs/roadmap/issue-AR-202-make-recruiter-repair-converge.md
  - docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md
  - agency_runtime/core/workforce/staffing_verifier.py
  - agency_runtime/core/header/contract.py
  - agency_runtime/adapters/hooks.py
supersedes: []
superseded_by: null
type: issue
epic: workforce
issue_id: AR-253
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-253: Dynamic team dispatch on every harness

## What already works (proven live, 2026-08-05, Claude host)

The full ecosystem loop executed in a real session: preflight classified the
turn, the recruiter staffed by inference (single-specialist and seven-unit
multi-specialist plans with dependency edges), the parent dispatched a native
`Agent` child per plan row, `PreToolUse` enforced byte-exact goal binding and
injected the immutable specialist prompt only into the child, the one-use
grant was consumed against observed child identity, and the Stop gate
machine-verified the response header against Store evidence — including
correctly terminating parent turns that under-declined strongly-preferred
rows. The staff-first doctrine (5783bdfe) removed the forced-gap refusal
machinery; the recruiter now returns staff decisions with required picks on
the asks that abstained for months.

The header is not model-trustable by accident: `validate_completion_policy`
rewrites/terminates on any header line that does not match recorded evidence.
Decline receipts are the sanctioned alternative to dispatch and do satisfy
the strong-delegation contract when recorded for every row.

## The four remaining gaps

1. **Conversational-turn Stop blocks (defect).** Several plain conversational
   turns were blocked with "could not verify or persist the turn-scoped
   evidence contract" — `evaluate_completion_policy` raised and the hook
   fail-closed. Diagnose why evaluation throws on turns with no plan (likely
   closed-run/reservation state after a prior terminal), and make
   verification unavailability on *evidence-free* turns degrade to accept
   with a recorded diagnostic instead of blocking the host.
2. **CLI/eval staffing context parity.** The `native-delegation` tool must be
   present in the eval and `agency route` staffing contexts (owner's pending
   `eval_commands.py` diff plus the same line for the route CLI), so probe
   surfaces match in-harness truth, where staffing already works.
3. **Staffing-rate eval (the number).** `agency eval staffing`: run a fixed
   ask set through the live pipeline per harness and report staffed%,
   dispatched%, and per-stage latency. Weekly cadence; a red number blocks
   feature work. This is the tripwire that prevents autonomous drift.
4. **Cross-harness dispatch proof.** Repeat the live loop on codex (hooks
   trusted; per-hook `enabled` must be switched on in the TUI `/hooks`
   screen — no CLI surface exists in codex 0.146), then hermes/openclaw on
   the agent box (bundles now ship MCP configs; smoke validates shape).
   ZCode follows its Agent-tool path. Record one attested end-to-end turn
   per harness.

## Acceptance

- One recorded turn per harness: plan → staff → dispatch-per-row (or
  explicit decline receipts) → header verified against evidence.
- `agency eval staffing` green (staffed ≥ 95% on the fixed ask set) on
  claude and codex from this machine; hermes/openclaw from the agent box.
- Zero conversational-turn hard blocks across a full working session.
