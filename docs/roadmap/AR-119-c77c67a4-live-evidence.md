---
title: "AR-119 installed and live evidence at candidate c77c67a4"
status: active
category: roadmap
created: 2026-08-17
updated: 2026-08-17
tags: [roadmap, evidence, hosts, AR-119, AR-255]
related:
  - docs/roadmap/AR-119-rule-host-evidence-matrix.md
  - docs/roadmap/AR-119-overnight-report.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
supersedes: []
superseded_by: null
type: reference
issue_id: AR-119
---

# AR-119 installed and live evidence at candidate c77c67a4

Every claim below is bound to one runtime: merge commit
`c77c67a4271a86051c1551ab61628959fc5bcb34` (PR #275), installed on 2026-08-17
between 03:01 and 03:03 UTC as runtime digest
`2cd2981585843ebbfa4f02012c1648b76587f00c19c3ebf0cb51e8a22009e97a` for claude,
codex, and zcode (one digest, AR-258), from a clean tree whose
`agency_runtime/` object equals main's (`git rev-parse` tree
`0e7d1a328098…`). The claude plugin's `hooks.json` pins
`runtime-sha256-2cd298158584…`, closing the wiring chain. The measurement
session `aa740d50-74f6-468c-b223-cce6ddfedf6d` was a fresh real-profile
`claude -p` session started 03:55 UTC, after the installs; hooks reload only
in a fresh session, so its evidence is the installed projection's. Store rows
are correlation only; each claim's origin authority is the host-authored
artifact (ADR-0156). Timestamps are UTC.

The primary host artifact is the session transcript
`~/.claude/projects/C--Workspaces-Holeshot-Software-agency-runtime--claude-worktrees-remote-control-7efcd5/aa740d50-74f6-468c-b223-cce6ddfedf6d.jsonl`
and its persisted attachment side files under
`aa740d50-74f6-468c-b223-cce6ddfedf6d/tool-results/`, written by Claude Code
itself. Machine copies are not embedded here; the artifact stays where the
host wrote it.

## R2 claude installed

A fresh session on the exact-candidate projection activated the R2 delivery
path end to end: the UserPromptSubmit hook of the installed runtime attached
`[AGENCY LOADED] Complete current-turn specialist instruction capsule` (record
9, 04:02:48.098, persisted side file `hook-4a16f3ce…-additionalContext.txt`,
18,310 bytes) and the store gained the accepted routing decision and
`specialists_loaded` rows written by the installed runtime for that trace.
Limitation: activation is shown by one turn; it is not a rate.

## R2 claude live

The same turn is a real live turn on the owner's profile. The capsule carries
the selected cards' entries with whole instruction bodies for four
specialists — `application-security-engineer`, `codebase-onboarding-engineer`,
`security-implementation-engineer`, `software-test-engineer` — attached
before the first caller speech (first assistant record 10 at 04:02:53.769; by
timestamp and file order). Store join: routing decision accepted at 04:02:47
(283.2 s, trace `399604da`), four `specialists_loaded` rows on the same
trace, zero `delegation_events` for the session — no child existed that
could have received the cards instead. Limitation: the decision selected
seven specialists and four were loaded; the artifact proves the loaded set,
and the narrowing is recorded, not hidden.

## R3 claude installed

Same activation artifact as R2 installed: the installed projection delivered
a multi-card capsule (four compatible cards in one turn) into the caller's
turn, pre-speech. Limitation: one turn, not a rate.

## R3 claude live

The R2 live artifact carries **four** compatible cards' whole instruction
bodies in one turn (`Instructions:` appears four times in the capsule side
file), each also present as a `specialists_loaded` row on the same trace.
Rule 3 asks for two or more; the turn delivered four. Limitation: same 7→4
narrowing note as R2 live.

## R5 claude installed

`agency eval spawn-authority --json` executed with the analyzed package root
literally the installed launcher tree
(`~/.agency-runtime/launchers/runtime-sha256-2cd2981585843…/site-packages/agency_runtime`,
verified by importing and printing the package path before the run): 5/5
cases pass — process-origin and worker-origin modules disjoint, worker origin
confined to host boundaries, every process-capable module purpose-declared,
and both injected-violation controls detected. Limitation: the separation is
host-neutral by construction, so this is one measurement, not five; and the
case list is five at this candidate where the `e216670a` narrative described
eight.

## R6 claude installed

The installed projection ran the whole hiring ladder inside a real turn:
hiring case `6c04ac6e-…` (04:11:13, status `applied`) with staged model
receipts, critic approval on a different provider than the creator, and a
security review recording `verdict: "safe"` with six annotation reasons —
the first applied hire recorded on the post-fix runtime. Worker filed as
`origin='agency'`, `employment_class='contractor'`
(`agent_workers.created_at` 04:11:13.464). Limitation: single organic
occurrence.

## R6 claude live

Turn 2 of session `aa740d50` (04:06:44) named a capability the roster lacked;
the ladder minted `function-naming-advisor` mid-turn and the new card — entry
plus whole instruction body — was dealt into the very turn whose gap created
it, visible in the turn-2 capsule side file, attached before that turn's
first assistant record. Turn 3 (04:14:25) made a same-domain request: the
store loaded `function-naming-advisor` again (trace `fb45d24e`, 04:15:24)
with exactly one `agent_workers` row ever and zero further hiring cases for
the slug — filed in the pool for next time, reused without re-hiring. A
second organic mint the same night (`contractor-reuse-system-analyst`,
04:20:24) corroborates the ladder. Limitation: the reuse turn ran in the same
session; a cross-session reuse was not measured tonight.

## R7 claude installed

The installed projection expired turn 1's cards at turn close and told the
next turn: store `specialists_loaded.expired_at` for all four turn-1 cards
equals run 1's `ended_at` (04:04:04) exactly, and turn 2's capsule attachment
opens with the expiry notice. Limitation: one two-turn observation.

## R7 claude live

Turn 2's capsule side file (record 25, 04:11:13, persisted
`hook-…-additionalContext.txt`, 15,487 bytes) states
`[AGENCY SPECIALIST EXPIRY] … no longer loaded: application-security-engineer,
codebase-onboarding-engineer, security-implementation-engineer,
software-test-engineer` — every turn-1 card named, none re-delivered (turn 2
loaded `code-reviewer` and `function-naming-advisor` instead), attached
before turn 2's first assistant record. Same identity held in its own turn,
absent from the next, expiry stated. Limitation: expiry-notice delivery rides
the next turn's capsule; a turn with an empty context projection would not
carry it.

## Not moved at this candidate

- **R1 and R4 claude**: still blocked by the child judge, now proven to
  decline on the merits — the post-P2 series (3 runs) recorded per-run child
  splits legacy / legacy / `native_child_abstention_confirmed`, with the
  confirmed row (`d6b514f7`, 03:36:59) written by the repair branch of the
  installed runtime. No v6 envelope exists; `native_child_delivery_verifications`
  still has zero rows.
- **R8 claude**: a candidate artifact exists (session `2b4b19d4`, 03:43:42 —
  hook cancelled by the host after 486 s, turn proceeded unstaffed and
  answered; run terminalized `response_invalid`; zero routing or failure
  receipts). Not claimed: the unstaffing came from host cancellation rather
  than Agency's own fail-open branch, and the terminal state contradicts a
  clean "proceeded" reading. Recorded for the owner's judgment.
- **codex**: projection installed at the one digest; the authorized
  `--verify-activation --autonomous` run reported "Codex files are installed,
  but bypass-mode activation was not proven" (`hook_trust_status:
  unverified`, no persistent trust changed). Bypass-derived and unproven;
  no codex cell moves.
- **zcode**: projection installed at the one digest; no `zcode` executable
  exists on this box and the canary names no noninteractive mode, so
  installed activation and live proof need the owner's own zcode session.
- **openclaw / hermes**: absent by instruction; see the verification packet.
