---
title: "AR-356 research-lifts implementation and backlog-triage capsule"
status: active
category: roadmap
created: 2026-09-01
updated: 2026-09-01
tags: [handoff, research-lifts, triage, reliability, fail-open]
related:
  - docs/roadmap/issue-AR-356-disclose-fail-open-staffing-in-capsule.md
  - docs/roadmap/issue-AR-360-battery-pass-k-grading.md
  - docs/roadmap/issue-AR-361-builder-evidence-isolated-verification.md
  - docs/roadmap/issue-AR-362-agent-chaos-harness-oracles.md
  - docs/roadmap/issue-AR-363-deployed-fix-witness-manifests.md
  - docs/roadmap/issue-AR-364-audit-external-review-cards.md
  - docs/roadmap/issue-AR-365-hermes-fail-open-gate-trace-resolution.md
  - docs/roadmap/issue-AR-353-intermittent-staffing-verdict-window-linux.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-356
branch: main
evidence_commit: 72b035c9b4143a50dcde5de64ea35076262ea472
minimum_ledger_commit: 72b035c9b4143a50dcde5de64ea35076262ea472
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/426
---

# AR-356 research-lifts implementation and backlog-triage capsule

Start-here capsule for a fresh session, anchored on AR-356 as the head of the
owner-approved implementation queue. Owner scope (2026-09-01): implement the
ten research lifts (AR-360..AR-364 plus the scope notes on
AR-120/266/336/355/356/357) and disposition the open backlog per the triage
below. Standing rules: attack every finding before reporting it; findings go
in repo docs, not the reply; prove gates locally (Actions is off); worklog
ledger dance on every change; end every turn with exactly one question.

## checkpoint

Main is fully green at `72b035c9` (verify_docs --require-tracker 961 files;
strict verify_tracker 356 items, 2 PR-tracked skips). The runtime is deployed
at that same commit: all four hosts wired to the launcher projection carrying
kernel v5, AR-346, and the AR-365 hotfix; all four batteries green and the
baseline adopted (claude 2.1.257, codex 0.152.0, hermes 0.21.0/7cd91114,
openclaw 2026.8.2).

The AR-353 intermittent staffing window is the dominant live failure. On
2026-09-01 ~20:29Z it hit four sessions within minutes
(`workforce_inference_failed`; staffing reasons `inference_invalid`,
`selection_confidence_too_low`, `staffing_critic_rejected`). A well-shaped
owner request (a UniFi client-drop investigation on openclaw) failed open
with the roster's `network-engineer` unreached — the planner call died before
any card ranking ran, and the reply went out unstaffed and headerless. That
is AR-356's exact case: the turn context never said staffing failed.

Deploy lore that recurs: claude `marketplace_add` needs the chmod dance after
host auto-updates (plugin dirs to 700, `@anthropic-ai` npm tree g-w
stripped); openclaw 2026.8.2 native install requires `openclaw plugins
install <path> --force --accept-capabilities` when the bundle digest changes
(fold into AR-358); the openclaw installer's `gateway_status` step always
fails while the gateway is deliberately stopped — diagnostic only; hermes
restarts tend to duplicate the dashboard process (kill by PID, never
`pkill -f` with a pattern your own shell contains, then one single start).

## completed-evidence

- The fail-open family is fixed and deployed: AR-345/344/343/346 landed, and
  AR-365 root-caused AR-346's live gap (fail-open turns never learn the
  preflight-minted composite trace) — PR #441, tick #442, battery-proven.
- AR-355 stage-complete: operator policy live every turn, kernel v5 deployed;
  remaining boxes need a fresh-session v5 binding observation and the
  token-cost measurement.
- The ten lifts are filed and merged: AR-360 #433, AR-361 #434, AR-362 #435,
  AR-363 #436, AR-364 #437 (PR #438, tick #439), AR-365 #440 (PR #441/#442).
- Session memory `fail-open-family-20260901.md` and
  `repo-research-lifts-20260901.md` carry deploy ledgers, provenance, and
  the rejected-on-doctrine list.

## exact-blocker

None mechanical. The queue below is unblocked; the only waits are
observational (a live AR-353 window turn for AR-365's last box, a fresh
persistent claude session for AR-355's v5 binding line).

## same-task-continuity

Continue on `main`; no work-in-progress branches are open. Every item below
is filed with a tracker and an issue doc; create one branch per work package
and keep the ledger dance per commit. Rebase-merges rewrite SHAs — repoint
the annotated ledger row in a follow-up docs(worklog) tick (the #438→#439
pattern).

## next-bounded-work-package

Implementation queue, owner-approved order:

1. **AR-356 (#426, p1)** — honest fail-open capsule disclosure, including the
   scope note's tool-degradation extension — and **AR-366 (#444, p1)**, its
   delivery-side sibling: openclaw withheld an owner reply entirely on
   2026-09-01 (evaluated rejection on an unstaffed turn); fix with the gate
   shared from AR-365, never a third copy.
2. **Reliability cluster vs the AR-353 window** — AR-353 measurement (#417),
   AR-360 pass^k/pass@k battery grading (#433), AR-362 chaos harness with
   oracles (#435). Receipts already name three distinct staffing reason
   codes; chaos injection should pin each shape.
3. **AR-352 (#416)** — scope battery deltas by session (foreign-session
   contamination measured during both 2026-09-01 deploy sweeps).
4. **AR-365 (#440) final box** — observe one live fail-open hermes turn
   delivering the model's draft.
5. **AR-361 (#434)** — builder evidence + isolated single-check verification.
6. **AR-363 (#436)** — per-host deployed-fix witness manifests (would have
   caught the day's stale-hook drift and the AR-365 code-drift same-day).
7. **AR-364 (#437)** — audit `silent-failure-hunter` and
   `type-design-analyzer` (affaan-m/ECC) into the roster; then the
   AR-336/AR-120 scope notes (trigger/routing evals, monotone
   discoverability baseline).
8. **AR-357 (#427)** — canonical per-turn response contract; three receipts
   (two in the doc plus a third withheld header-following reply, 2026-09-01
   evening).
9. **Small fixes** — AR-359 stdin newlines (#429; then re-set the live
   operator policy with its line breaks), AR-358 trust-chain self-healing
   (#428; add the openclaw `--accept-capabilities` consent step), AR-354
   host-CLI coverage tests (#420).
10. **AR-355 (#422) finish** — fresh persistent claude session, verify
    `kernel_version = 5` in `resident_manager_bindings`, measure per-turn
    token cost via the context-budget method in the doc, flip boxes, close.

Backlog triage — owner-directed dispositions (verify before closing, cite
receipts in every close):

Close with evidence: AR-347 #404 (4/4 boxes; both strict gates green on main
since `c887190d`), AR-337 #362 (6/6; discipline shipped, exercised three
times on 2026-09-01), AR-298 #336 (9/9), AR-265 #317 (24/25; finish or waive
the last box), AR-127 #151 (zcode not registered on any host — close as
parked-until-zcode-exists with owner sign-off), AR-119 #132 (6/39 but
superseded by the shipped inference-first system — close as superseded and
file a residual for any concrete remaining gap).

Verify-then-close-or-finish: AR-199 #161 (25/28; its reopen gate was the
fail-open family, now fixed and deployed — re-verify the open boxes on live
codex turns), AR-344 #399 (before closing, check the codex Stop path for the
same trace-resolution gap AR-365 fixed on hermes — `_is_terminal_turn`,
adapters/hooks.py:3300 — a fail-open codex turn must not see "does not match
the exact response accepted"; fix if present), AR-261 #309 / AR-262 #311 /
AR-264 #313 (7/8, 7/9, 9/10 — finish honestly or record why they wait),
AR-115 #127 (9/12; overlaps AR-357 — fold or finish).

Keep open as active backlog: AR-266 #320 (p0, additive live, RAGLite
reference in-doc), AR-335 #350, AR-336 #353 (boxes checked; the scope note
carries the routing-evals work), AR-200 #175, AR-201 #180, AR-207 #196,
AR-208 #200, AR-209 #203, and the reopened operator-plane/parity family
AR-235 #244 / AR-236 #245 / AR-250 #259 / AR-251 #260 (AR-361 supplies
AR-235's isolated-review mechanism; schedule after the reliability cluster).
Evaluation epics AR-125 #138 and AR-178 #153 stay open; consider folding
AR-178 into AR-125 when picked up.

## verification

- Local gates for every change: focused tests, the named fast Python spine
  (AGENTS.md lists the files; `-W error`), ruff check + format (binary under
  `~/.cache/agency-runtime-ar281-trusted-venv/bin/`), both docs gates
  (`verify_docs.py --require-tracker`, `verify_tracker.py`), and the worklog
  dance. Decision-conformance eval needs copies-venv + umask 077; routing
  evals via `agency eval routing --json`.
- Any runtime deploy follows AR-337: venv pip-reinstall from the local git
  checkout pinned to the exact SHA with `--no-deps --force-reinstall
  --no-cache-dir`, `agency install` + per-agent, codex tmux re-trust
  (send-keys `2` + Enter), hermes single-process restart, openclaw gateway
  stop/install/start, four batteries, `agency battery --baseline`.

## constraints

- GitHub Actions is off — never claim CI ran; prove gates locally.
- The pre-tracker allow-list is frozen (AR-227/228 PR-tracked); new docs
  always carry `tracker_url`.
- Never name the legacy sibling repository in roadmap docs (verify_docs
  rejects it). sqlite3 CLI is absent (use the python3 module); bare
  foreground `sleep` is blocked (use a python time.sleep one-liner).
- Findings in repo docs; one question per turn; Rule 8 always.
