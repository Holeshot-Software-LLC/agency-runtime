---
title: "AR-119 installed and live evidence at runtime 99a7b3ac"
status: draft
category: roadmap
created: 2026-08-18
updated: 2026-08-18
tags: [roadmap, evidence, hosts, AR-119, AR-255]
related:
  - docs/roadmap/AR-119-rule-host-evidence-matrix.md
  - docs/roadmap/AR-119-c77c67a4-live-evidence.md
  - docs/roadmap/AR-119-vision-loop-status.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
supersedes: []
superseded_by: null
type: reference
issue_id: AR-119
---

# AR-119 installed and live evidence at runtime 99a7b3ac

Every claim below is bound to one runtime: merge `99a7b3ac` (PR #287, the
owner's small-unit policy), whose `agency_runtime/` tree equals every
later main tip through `f980f27e` (docs-only merges since; verified by an
empty `git diff 99a7b3ac origin/main -- agency_runtime/`) — installed on
2026-08-17 (before 21:00 UTC, per the runtime-state file) as runtime digest
`cc478bc88258210b24dfd8f990caa76b41b4585de72a68c45d4c040b74c7f5e5` for
claude, codex, and zcode (one digest, AR-258), store schema 47 == checkout
47 == launcher 47. PRs #288–#290 after the install are docs-only, so the
installed build equals main for the package tree. Store rows are
correlation only; each claim's origin authority is the host-authored
artifact (ADR-0156). Timestamps are UTC.

The measurement session for R1/R4/R5-Live is the loop session itself —
Claude Code session `f3066348-ca45-4318-9095-878a4a23c5c2`, a fresh
real-profile session started 2026-08-18 00:04, after the installs. Its
primary artifacts are the parent transcript
`~/.claude/projects/C--Workspaces-Holeshot-Software-agency-runtime/f3066348-ca45-4318-9095-878a4a23c5c2.jsonl`
and the child transcript
`…/f3066348-…/subagents/agent-a3b16809ebb7e199e.jsonl`, written by Claude
Code itself and retained where the host wrote them.

## R4 claude installed

At 01:47:41Z the installed projection's hook staffed a harness-spawned
native child just-in-time: `routing_decisions` row
`native-child-3507ad1491c2c291f8709239ea5697d6` (`applied`, source
`native_child_inference`, provider `codex-subscription`, 11.85 s), and the
envelope it rendered names the installed runtime itself —
`runtime_digest` = `candidate_digest` = `cc478bc88258…` — closing the
wiring chain from inside the artifact. Limitation: one child, one turn;
the runtime's own in-lifetime collector (canary-only) never evaluated this
delivery, so `native_child_delivery_verifications` remains empty; the
verification below is reproducible from the retained artifacts instead.

## R4 claude live

The child transcript's record zero (type=user, isSidechain=true,
01:47:41.715Z) carries `[AGENCY INFERENCE TEAM v6]` inside the assignment
text, before any child speech. The sealed payload binds: `launch_id` =
`binding_id` = `toolu_01NpSMbfcshZ8UgNYQ71Fvkm` — the exact Agent tool_use
id recorded in the parent transcript; `parent_session_id`/`parent_trace_id`
= this session and trace `1b717647…`; `task_sha256 7ee6b9cecc53…` — equal
to an independent recompute of SHA-256 over the parent-recorded 2,020-char
assignment, and to the store's captured-assignment hash; one card,
`codebase-onboarding-engineer`, `specialist_prompt_hash 4af8a247…`,
`specialist_version sha256:36a665df…` — both exactly equal to the live
roster row's `current_hash`/`current_version`; issued 01:47:40.953Z,
delivered inside its 60 s validity window. This is a correlated native
child artifact with exact card hashes before first speech, live, on the
owner's real profile. Limitations: a single occurrence; the child's
assignment was a ~2,000-character research unit, so the small-unit
question (AR-255) stays open; `provider_receipt_digest` inside the
envelope was not independently recomputed.

## R1 claude installed

The same envelope is the inference receipt joined to exact delivered card
hashes, delivered by the installed projection: decision id, provider
identity, and the exact card hash/version travel sealed in one object that
the store's decision row, captured-assignment row, and roster row each
join exactly. Limitation: the join is proven through the decision id,
task hash, and card hashes; the envelope's own `provider_receipt_digest`
binding was not independently recomputed.

## R1 claude live

Same artifact, same joins, on a live real-profile turn: inference chose
the specialist (`native_child_inference`, `applied`), and the exact chosen
card's hash arrived in the child's first record. Limitations: as R1
installed; one occurrence.

## R5 claude installed

`agency eval spawn-authority --json` re-executed at this candidate with
the analyzed package root literally the installed launcher tree
(`~/.agency-runtime/launchers/runtime-sha256-cc478bc88258…/site-packages/agency_runtime`,
asserted by importing and printing the package path in-process before the
run, after an earlier attempt was caught importing a checkout tree and
discarded): 5/5 cases pass — process-origin and worker-origin modules
disjoint (295 modules, 21 process-capable, 5 worker-origin, overlap 0),
worker origin confined to the five host boundaries, every process-capable
module purpose-declared, both injected-violation controls detected.
Limitation: the separation is host-neutral, so this is one measurement.

## R5 claude live

A live host-originated spawn with Agency recording rather than starting
it: the parent transcript's Agent tool_use (host-initiated), the
`delegation_events` row (`backend=delegate_task`, `status=completed`,
`error=ok`, worker `claude-agent:a3b16809ebb7e199e`) recording the host's
own delegation, the staffing decision above (Agency's only role:
choosing cards for the child the host created), and the installed-tree
separation proof. Agency started no process; the host originated the
worker; Agency recorded it. Limitation: one spawn; the negative half
(no Agency-started process at any seam) rests on the installed
spawn-authority separation rather than a whole-turn seam sweep.

## R2 claude installed

A fresh real-profile `claude -p` session on the installed projection
(session `1eaa3a55-e7ad-4309-a61d-1a054aae3e55`, started 02:56:56Z from
the ar119 worktree) activated the delivery path end to end: the
UserPromptSubmit hook attached the `[AGENCY LOADED]` capsule as transcript
record 8 (02:58:49.750, persisted side file
`hook-3576769e-…-additionalContext.txt`, 18,748 bytes), and the store
gained the accepted routing decision (`949ced13`, 109.5 s, trace
`442b50db`) and four `specialists_loaded` rows written by the installed
runtime for that trace. Limitation: one turn, not a rate.

## R2 claude live

The same turn is a real live turn on the owner's profile: the capsule
carries the selected cards' entries with whole instruction bodies
(`Instructions:` appears four times in the side file) for
`codebase-onboarding-engineer`, `application-security-engineer`,
`secrets-credential-hygiene-engineer`, `code-reviewer`, attached before
the first assistant record (record 8 at 02:58:49.750 vs record 9 at
02:58:51.404). Store join: decision `accepted` with exactly those four
selected, four `specialists_loaded` rows on the same trace, zero
`delegation_events` for the session — no child existed that could have
received the cards instead. Selected and loaded sets are equal (4/4),
with no narrowing. Limitation: one turn.

## R3 claude installed

Same activation artifact as R2 installed: the installed projection
delivered a multi-card capsule — four compatible cards in one turn —
into the caller's turn, pre-speech. Limitation: one turn.

## R3 claude live

The R2 live artifact carries four compatible cards' whole instruction
bodies in one turn, each also present as a `specialists_loaded` row on the
same trace. Rule 3 asks for two or more; the turn delivered four, and the
selected set equals the loaded set. Limitation: one turn.

## R7 claude installed

The installed projection expired turn 1's cards at run close: all four
`specialists_loaded.expired_at` values equal the run's `ended_at`
(03:02:32.057455) exactly, and turn 2's capsule attachment opens the next
turn with the expiry notice. Limitation: one two-turn observation.

## R7 claude live

The resumed turn 2 of session `1eaa3a55` (run `bfb6c3a5`, 03:05:52Z)
received its capsule as record 56 (03:06:38.679, persisted side file
`hook-1b86c5a5-…-additionalContext.txt`), before turn 2's first assistant
record 57 (03:06:54.170). It states `[AGENCY SPECIALIST EXPIRY] … no
longer loaded: application-security-engineer, code-reviewer,
codebase-onboarding-engineer, secrets-credential-hygiene-engineer` —
every turn-1 card named, none re-delivered: turn 2's accepted decision
(`d05cd5d9`, 03:06:38) selected and loaded `ci-operations-advisor` and
`sre-site-reliability-engineer` instead. Same identity held in its own
turn, absent from the next, expiry stated. Limitation: the expiry notice
rides the next turn's capsule, so an empty-context turn would not carry
it.

## R6 claude installed

The installed projection ran the whole hiring ladder organically inside a
real turn of a different project's session (conveyor worktree session
`b97eb5cb-8d87-4fed-9c1f-b1f3399533b1`, 05:05:48Z): hiring case
`bfe8a9cb` (`hire`, `applied`, work unit
`unit-deployment-readiness-review`, trace `01605b15`) carries gap,
duplicate, and contract evidence, staged model receipts
(`inference_required: true`), an independent critic receipt
(`approved: true`, compiled prompt hash `373fb41e…`), an inline dynamic
audit (`status: approved`, `contract_valid: true`, revision
`dynamic-v1-373fb41e…`), and a contract hash; the worker
`deployment-readiness-reviewer` was filed `origin='agency'`,
`employment_class='contractor'` at 05:05:48.462. A second organic mint
the same night (`operations-recovery-plan-reviewer`, case `9afaec53`,
03:45:45Z, this loop session) corroborates the ladder. Limitation: the
dynamic-hire path records its audit inline rather than as the separate
security-review row the `2cd29815`-era proof cited; stated as measured.

## R6 claude live

The new card was dealt into the very turn whose gap created it — the
session transcript's capsule record 1948 (05:05:48) names
`deployment-readiness-reviewer` with its instruction body — and **a later
turn of the same session reused it from the pool with no further hiring
case**: `specialists_loaded` row at 06:29:49.879, capsule record 2611
(06:29:50), and zero `agent_hiring_cases` rows after the mint. Filed in
the pool for next time, found there, hired nobody. Limitations: the reuse
turn ran in the same session (cross-session reuse still unmeasured), and
the traffic was another project's autonomous session — organic with
respect to this loop, but the machine had exactly one interactive owner
absent all night.

## Not moved at this candidate

- **R8 claude**: no clean "unstaffed turn proceeded" host publication
  artifact exists yet. The canary discards the disposable-profile parent
  transcript, so tonight's three preflight-failed runs (0/3 series,
  provider-killed) could not double as R8 artifacts; preserving a bounded
  parent-proof in the canary attestation is proposed as a morning decision
  (it is a new capture surface, which section 3 of the loop brief reserves
  to the owner).
- **codex / zcode / openclaw / hermes**: unchanged from candidate
  `f2f3ca88`; see the matrix and the owner-run verification packet.
