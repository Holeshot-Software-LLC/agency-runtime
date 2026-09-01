---
title: "AR-336: Requalify the recruiter route for ordinary tasks"
status: in_progress
category: roadmap
created: 2026-08-29
updated: 2026-09-01
tags: [bug, reliability, workforce, recruiter, litellm, routes]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-335-make-content-invalid-completions-reach-fallback.md
  - docs/decisions/0192-route-content-invalid-completions-to-a-content-fallback-profile.md
  - agency_runtime/core/workforce/inference.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-336
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/353
depends_on: []
blocks: []
---

# AR-336: Requalify the recruiter route for ordinary tasks

## Problem

With the AR-335 content fallback live and funded, ordinary-turn staffing now
fails deterministically at the recruiter stage on content grounds:
MiniMax-M3 is rejected twice (`recruiter_candidate_positive_evidence_invalid`
on the funded repair) and the gpt-5.5 content-fallback is rejected twice
more, all four completions transport-successful. The same recruiter route
passes the simpler activation-canary staffing in the same hour, so the
failure is specific to ordinary-task nominations under the current recruiter
contract.

## Current state

- 2026-08-29 receipts (runtime `6606ebed`, config v4) under
  `~/.agency-runtime/evidence/ar297-live-harness-20260829/`: planner primary
  emits content-invalid completions and the Turbo content-fallback rescues
  the stage in three of three live turns; the recruiter stage then consumes
  its full funded chain and dies on content codes.
- Route health: the recruiter's order-2 transport fallback
  `chatgpt/gpt-5.6-luna` returns deterministic 403 HTML from the
  subscription backend on faithful clones
  (`ar335-content-fallback-aliases-20260829/`), implicating the production
  order-2 deployment as dead. The AR-335 recruiter content-fallback was
  therefore pointed at `chatgpt/gpt-5.5` reasoning-low, which answers but
  does not satisfy the recruiter contract on the observed task.
- Diagnosis caution recorded: bare `run_preflight` harness calls without
  capability receipts run with `context_host=unknown` and empty tools and
  produce misleading `agent_host_unsupported` rejections; only real hook
  turns or receipt-complete harnesses are faithful.
- Agency master control is OFF pending this repair; the promoted planner
  route, the content-fallback wiring, and host bundles stay installed.


- 2026-08-29 late evening: the bounded matrix (9 recruiter calls) revalidated
  MiniMax-M3 2/2 and gpt-5.5-low 2/2 on ordinary fixtures in a
  receipt-complete harness, exposing the earlier live rejections as a
  compound of Turbo-authored novel-capability plans plus the dead luna
  order-2. Route repairs applied with receipts
  (`ar336-recruiter-requalification-20260829/`): recruiter order-2
  luna -> gpt-5.5-low (`fc07bd43…`, carried a live turn immediately), and the
  planner content-fallback iterated Turbo -> qwen3-14b (context-ceiling
  refusal on stack-bearing prompts) -> gpt-5.6-terra medium (2/2 harness,
  then live openclaw/hermes/codex staffing). All four ordinary host turns
  then staff: claude and codex pass the full bar including finalization and
  the Agency header; openclaw and hermes staff completely with specialists,
  routes, and receipts, with finalization not observable in no-deliver /
  one-shot modes per their host contracts. Master control is restored to ON
  (generation 6) and doctor reports inference operational.

## Approach

Requalify the recruiter route against the current positive-evidence contract
using real ordinary-task fixtures: decide with the owner whether the
contract's evidence requirements need repair or the recruiter models need
replacement, following the AR-297 bakeoff pattern with bounded zero-retry
calls. Replace or remove the dead luna order-2 deployment. Re-enable master
control only after the four ordinary host turns pass.

Scope note (2026-09-01, owner-approved lift): qualification should
include trigger/routing evals over card descriptions — positive request
fixtures must rank their own card first against near-miss negatives,
and no two card descriptions may near-collide (pattern from
awesome-llm-apps `agent_skills/evals` tier 2). Routing today has no
description-level proof; this makes requalification testable instead of
anecdotal.

## Dependencies

AR-334 completion for the Codex ordinary turn (attended trust plus the
restricted current-profile canary on codex-cli 0.151).

## Acceptance

- [x] A repeated ordinary-task recruiter qualification passes on the
      selected primary and a working different-provider fallback.
- [x] The dead luna order-2 deployment is replaced or removed with receipts.
- [x] All four ordinary host turns pass preflight and staffing with
      retained receipts; claude and codex additionally prove finalization
      and the visible Agency header, while openclaw and hermes finalization
      stays unobservable in no-deliver/one-shot modes (recorded follow-up).
- [x] Master control is restored to ON.
