---
title: "AR-119 vision-completion loop final status"
status: active
category: roadmap
created: 2026-08-17
updated: 2026-08-21
tags: [roadmap, report, autonomous, loop, AR-119, AR-253, AR-255]
related:
  - docs/roadmap/AR-119-vision-completion-autonomous-brief.md
  - docs/roadmap/AR-119-instrument-series-status.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/roadmap/AR-119-rule-host-evidence-matrix.md
  - docs/roadmap/AR-119-39ff6dca-recruiter-diagnostic-evidence.md
  - docs/roadmap/AR-119-fcffd96c-hiring-diagnostic-evidence.md
  - docs/roadmap/issue-AR-259-preserve-terminal-hiring-state.md
  - docs/roadmap/AR-119-9685a16d-accepted-outcome-evidence.md
  - docs/roadmap/AR-119-2919802e-accepted-outcome-proof.md
  - docs/roadmap/issue-AR-260-accept-verified-launch-bindings-in-outcome-canary.md
  - docs/roadmap/AR-119-f4f3d45e-hiring-risk-evidence.md
  - docs/roadmap/issue-AR-261-disambiguate-technical-diagnosis-risk.md
  - docs/roadmap/issue-AR-262-preserve-slow-host-dashboard-parity.md
  - docs/roadmap/issue-AR-263-restore-codex-desktop-parent-hook-delivery.md
  - docs/roadmap/AR-255-child-parity-design.md
supersedes: []
superseded_by: null
type: reference
issue_id: AR-119
---

# AR-119 vision-completion loop final status

**Your machine is on main's build.** All three hosts (claude, codex,
zcode) pin runtime digest `cc478bc88258…` — merge `99a7b3ac`, PR #287,
your small-unit policy — with store schema 47 equal to both checkout and
launcher, verified by reading the three `current-<host>.json` files at
the close of the run. Everything merged after that install (PRs
#288–#293) is docs-only, so no reinstall is owed and the installed build
equals main for the package tree.
`~/.agency-runtime/overnight-runtime-state.json` carries the same facts.

**This is the final status document for the loop run of 2026-08-18.** The
loop stopped on condition 6.1: every matrix cell still open now carries a
recorded blocker that is yours — physically or by decision. It did not
stop because it ran out of time.

## The one-paragraph version

The night's real gain is narrower than it looked at 04:00, and it is
still worth having: **the first `[AGENCY INFERENCE TEAM v6]` envelope
ever observed on this machine**, delivered pre-speech to a live
harness-spawned child and verified to the byte across parent artifact,
child artifact and store. R2, R3 and R7 are genuinely proven at all four
layers on claude. **Four cells I promoted earlier in the run — R1, R4,
R5, R6 — I retracted the same day after adversarial review, by name,
before you read them.** The acceptance draw you were waiting for finally
landed and answered: with your small-unit policy live in the installed
prompt, the child judge **declined** the pure unit. Three canary series
(nine runs) otherwise fought provider flakiness all night.

## Cycle log

### Cycle 0 — session bring-up (2026-08-18 00:04–02:00 UTC)

Load order completed: capsule, founding vision, loop brief (read from
`origin/main` before the local sync existed), overnight brief traps/refuted
lists, instrument-series status, AR-255 design, full evidence matrix.

**Finding: `core.worktree` hijack in the shared `.git/config` (REPAIRED).**
The primary checkout's `.git/config` carried
`core.worktree = .../.claude/worktrees/remote-control-7efcd5` — left behind
by the 2026-08-17 remote-control session. Because `core.worktree` in the
shared config applies to every worktree of the repository, **every git
status/diff/merge run in the primary checkout or any linked worktree was
silently measuring the remote-control directory instead of its own**, while
non-git filesystem reads told the truth about the real directories. Observed
symptoms before diagnosis: phantom `??` entries for files absent on disk,
"modified" listings for ~70 clean files, and a refused fast-forward naming
untracked files that did not exist. Repaired 2026-08-18T01:37Z with
`git config --unset core.worktree` in the primary; verified by
`git rev-parse --show-toplevel` returning each checkout's own path, the
primary then showing exactly the owner's known WIP
(`agency_runtime/cli/eval_commands.py` +8/−2, three untracked eval JSONs),
and the ar119 worktree showing a clean tree that fast-forwarded to
`94489201` without complaint.

- *What this excludes:* any conclusion drawn from git working-tree state in
  the primary or ar119 checkouts between the remote-control session's start
  and the repair is suspect; commit-level facts (log, ls-remote, show) were
  never affected. No commit, stash, revert, or install was performed through
  the corrupted view tonight.
- *Falsification:* if git status in the primary again lists files that
  `Test-Path` denies, the diagnosis was incomplete — re-check
  `core.worktree`, `git config --show-origin --list`, and fsmonitor state
  before trusting any tree.
- *Owner note:* whatever tool wrote `core.worktree` into the shared config
  (plausibly the remote session's worktree tooling on abnormal exit) may do
  it again; the repair is one `git config --unset core.worktree` away.

**Provider health at loop start: the recruiter defect is live right now.**
This resident-manager session's own turns sampled eight routing draws
between 23:50Z and 01:32Z: one clean apply (23:50:13Z), then
`staff_without_safe_team` recruiter double-rejections at 23:50:24Z, 00:10Z,
00:32Z, 01:32Z; planner `provider_no_valid_response` at 00:03Z and 00:47Z;
planner `provider_response_contract_invalid` double-rejection at 01:12Z.
Same shape the 2026-08-17 evening series recorded: decision "staff", ranked
list present, empty selection — provider-side, AR-253's ledger.

**Delegated ruling (applies brief §4.6):** two consecutive stages failed
provider draws within this window, so the §7.1 acceptance-draw measurement
enters a ≥30-minute backoff from the 01:32Z receipt (resume no earlier than
02:02Z). Backoff pauses the attempt clock; provider-independent §7 work
proceeds meanwhile. *Falsification:* a probe after 02:02Z that passes
`agency eval routing` and lands one accepted live draw ends the backoff;
three such backoffs across six hours with the same stage failing records
`blocked-on-provider` per stopping condition 6.1.

### Interim work during backoff (in progress)

Assessing provider-independent claude cells named by §7.2, against the
matrix's exact authorities:

- **R8 Installed/Live** ("native host publication artifact showing an
  unstaffed turn proceeded"): tonight's fail-open turns in this real-profile
  session on the installed projection — runs with `preflight_failed` status
  whose turns nonetheless produced published host output — are candidate
  clean artifacts, stronger than the deliberately unclaimed cancelled-hook
  session `2b4b19d4`. Not yet claimed; needs the artifact/store join built
  and checked against the authority wording first.
- **R1 Installed/Live** ("inference receipt joined to exact delivered card
  hashes"): this session's accepted turn-1 routing (specialist loaded,
  `workforce_inference`) plus the injected capsule may satisfy the join;
  needs the exact card-hash join read out of the store and the host
  artifact before any claim.
- **R5 Live** (native spawn-origin artifact): this session's host-initiated
  subagent spawn (Explore, ~01:50Z) is a live host-originated spawn with
  Agency recording rather than starting it; assessment pending.

No matrix cell has been changed. Any new cell requires advancing
`candidate_commit` per the update contract, with citations re-anchored.

### Cycle 1 — first live v6 delivery observed; probe green; series started (02:00–02:10 UTC)

**Finding: the first v6 envelope ever observed in a host-authored child
artifact — the capsule's "one child spawned from this runtime settles v6"
question is settled live.** This loop session's own research subagent
(host-spawned via the Agent tool at 01:47Z) was staffed by the child judge
(`routing_decisions` row `applied`, source `native_child_inference`,
provider `codex-subscription`, 11.85 s, selected
`codebase-onboarding-engineer`), its assignment captured verbatim
(`native-child-3507ad1491c2c291f8709239ea5697d6`), and the child transcript
`~/.claude/projects/C--Workspaces-Holeshot-Software-agency-runtime/f3066348-ca45-4318-9095-878a4a23c5c2/subagents/agent-a3b16809ebb7e199e.jsonl`
carries `[AGENCY INFERENCE TEAM v6]` inside record zero (type=user,
isSidechain=true — the canonical shape), before any child speech. The sealed
payload binds `launch_id` = the Agent tool-use id, the parent session and
trace ids, the exact card hash (`specialist_prompt_hash 4af8a247…`, version
`sha256:36a665df…`), and `candidate_digest` = the installed runtime
`cc478bc88258…`.

- *What this establishes:* JIT native-child staffing, the v6 renderer, and
  pre-speech delivery work end to end, live, on the installed projection,
  in a real profile. The child judge can staff a harness-spawned child.
- *What it does NOT establish:* the §7.1 acceptance draw (this unit was a
  ~2,000-char research task, not the 138-char pure review unit; the
  small-unit question stays open), and no R4 matrix cell (the in-lifetime
  collector never ran, so `native_child_delivery_verifications` is still
  zero rows; conservative reading of R4's authority keeps the cell
  untouched until a collector-verified proof exists).
- *Falsification:* if the envelope in that artifact fails hash or binding
  checks against the store's decision row, the delivery claim dies; the
  artifact is retained where the host wrote it.

**Probe (brief §4.6) passed both halves at ~02:05Z:** `agency eval routing
--json --no-details` exited 0 with `passed: true` (v1.4.0), and the store
gained hook-path draws after the backoff receipt — `accepted` parent
decision 01:52:57Z and the `applied` child decision above. Backoff ended.
Canary readiness for claude: `ready: true`, `trust_mode: attended`,
isolated-profile, no unmet prerequisites, confirm phrase verified.

**Series run 1 of ≥3 launched** (isolated-profile, `--timeout 420`,
serialized; report to the session scratchpad, essentials to be quoted here;
failures kept; per-run reason codes). Acceptance unchanged: one clean child
draw that staffs the pure unit and the first
`native_child_delivery_verifications` row ever.

### Series ledger (small-unit-policy acceptance, runtime `cc478bc88258…`)

- **Run 1** (02:02:48–02:04:24Z, run `98b0ec8c`, receipt `d5062324`):
  FAILED at parent preflight — planner applied (haiku), recruiter rejected
  twice `provider_response_contract_invalid` (sonnet), receipt reason
  `workforce_inference_failed`. Routing 0, specialists 0, delegations 0;
  the parent turn still finalized (fail-open honored, finalization
  `7707109b`). The instrument was never reached. Note: the report's
  `native.canary` block is empty — the canary does not preserve the parent
  transcript, so a preflight-failed run cannot double as an R8 publication
  artifact under the current report shape (parked as a post-series
  candidate improvement).
- **Run 2** (02:11Z, run `c9535668`, receipt `aa12fb29`): FAILED at parent
  preflight — planner `provider_no_valid_response` (haiku), receipt reason
  `workforce_provider_unavailable`. Nothing downstream ran.
- **Run 3** (02:47Z, run `dbdb8fba`, receipt `a7999a88`, launched after
  the probe passed on two accepted hook-path draws at 02:15Z/02:35Z):
  FAILED at parent preflight — planner `provider_no_valid_response`,
  identical to run 2.

**Series verdict: 0/3, all provider-killed before the instrument** —
recruiter contract-invalid ×2, then planner dead ×2. Second consecutive
provider-killed series tonight (the 2026-08-17 policy series was the
first). A third failing series spaced ≥6 h from the first records
`blocked-on-provider` (6.1). The session's own turn draws intermittently
succeed in the same window, so this is intermittency under load, not an
outage; account-level rate pressure is a plausible mechanism (the owner
flagged model-limit pressure tonight). Next series no earlier than ~03:30Z;
provider-independent §7.2 work proceeds meanwhile.

**Delegated ruling (brief §4.6): two consecutive provider-stage failures →
30-minute backoff on the series from 02:11:24Z, resume no earlier than
02:41:24Z.** Backoff pauses the attempt clock. Interim work: §7.2 evidence
inventory (provider-independent). *Falsification:* an accepted hook-path
draw in the store after 02:41Z reopens the series; a third consecutive
provider-killed series over ≥6 h records `blocked-on-provider` per
stopping condition 6.1.

### Cycle 2 — §7.2 inventory: the v6 chain verifies end to end (02:15–02:35 UTC)

**Negative first: this session is not a clean R2/R3 parent-side vehicle.**
In this interactive real-profile session's transcript, the first
`[AGENCY LOADED]` attachment record lands at index 87 (00:07:58Z) while the
first assistant record is index 11 (00:03:57Z) — the caller speaks while
routing resolves, so pre-speech delivery cannot be shown from this session.
The `claude -p` one-shot sessions passed R2/R3 because they wait; the
interactive path does not. (This is an artifact-timing observation about
the transcript record order, not a delivery regression claim.)

**Positive: the 01:47Z live child delivery verifies across three
independent surfaces, with exact-hash joins at every seam:**

1. *Parent host artifact* — this session's transcript records the Agent
   tool_use `toolu_01NpSMbfcshZ8UgNYQ71Fvkm` with the full 2,020-char
   assignment; `sha256(prompt)` = `7ee6b9cecc53…` (recomputed
   independently).
2. *Child host artifact* — `subagents/agent-a3b16809ebb7e199e.jsonl`
   record zero (type=user, isSidechain=true), timestamp 01:47:41.715Z,
   carries the v6 envelope inside the assignment text, pre-speech:
   `task_sha256` = `7ee6b9cecc53…` (equals the parent-side recompute),
   `binding_id`/`launch_id` = that exact tool_use id,
   `decision_id native-child-3507ad1491…`, card
   `codebase-onboarding-engineer` with `specialist_prompt_hash 4af8a247…`
   and `specialist_version sha256:36a665df…`, `runtime_digest` =
   `candidate_digest` = installed `cc478bc88258…`, delivered inside its
   60 s validity window (issued 01:47:40.953Z).
3. *Store correlation* — `routing_decisions` row with that exact id
   (`applied`, source `native_child_inference`, provider
   `codex-subscription`, same trace/session), captured-assignment row with
   the same `task_sha256` (capture text bounded at the documented
   `MAX_CAPTURE_CHARS = 2000`, hence hash-binds-original by design), and
   the roster row `agent_workers.codebase-onboarding-engineer` whose
   `current_hash`/`current_version` equal the envelope's card hash and
   version exactly.

**What this makes claimable and what it does not.** This is live
R4-authority-shaped evidence ("correlated native child artifact with exact
card hashes before first speech") and an R1-shaped live join (inference
receipt identifiers sealed with exact delivered card hashes in one
envelope). It is deliberately NOT claimed in the matrix yet: (a) the
matrix's `candidate_commit` still anchors `f2f3ca88` (tree == PR #275)
while this artifact binds runtime `cc478bc88258` (tree == merge
`99a7b3ac`), so a candidate advance with citation re-anchoring must come
first — and that advance demotes the existing installed/live claude cells
proven on `2cd29815` until re-proven; (b) the runtime's own collector
never evaluated this delivery (`native_child_delivery_verifications`
remains zero rows — the collector is canary-in-lifetime only); (c) the
`provider_receipt_digest` binding was not independently recomputed
(writers: `native_child_decision.py`, `native_child_prompt_delivery.py`).
*Falsification:* any of the recorded hashes failing a re-check against the
retained artifacts kills the claim; the artifacts stay where the host
wrote them.

Also this cycle: PR #290 opened (docs-only ledger increment; merge only on
a verified-CLEAN rollup), and the AR-252 fourth-constraint decision is
settled as a delegated ruling in `issue-AR-252` — the verdict is a joint
object with its division named in the envelope; the one-use capability
seal stays untouched and unwidened.

### Cycle 3 — candidate advance to `f980f27e` with re-proof sweep (02:50–03:30 UTC)

PR #290 merged 02:47:36Z on a verified-CLEAN rollup (docs-only; no
reinstall owed; runtime-state note updated). The candidate advance then
proceeded with data:

- **Tree equality verified**: `git diff 99a7b3ac origin/main --
  agency_runtime/` is empty, so main tip `f980f27e143f…` binds the
  installed digest `cc478bc88258…` exactly, per the `f2f3ca88` precedent.
- **R5 Installed re-proven** against the launcher tree — after an
  adversarial catch: the first eval run silently imported the PRIMARY
  checkout's stale tree because `python -m` puts the current directory
  ahead of `PYTHONPATH`; it was discarded and re-run with cwd inside the
  launcher's site-packages and the imported path asserted in-process.
  Rule for future sessions: **never trust a "-m agency_runtime" run
  without printing `agency_runtime.__file__` from the same cwd.**
- **Citation re-anchor sweep** (read-only agent, verified): between the
  old candidate's tree and `f980f27e`, all changes are pure insertions;
  exactly one matrix anchor moves — R1 claude Implementation
  `native_child_staffing.py:876-1031 → 923-1084`. Flagged in passing: the
  R7 Implementation anchor `store/evidence.py:1298-1340` straddles
  construct boundaries (it cleanly contains only `complete_run`) — a
  pre-existing imprecision, left for the owner rather than silently
  re-scoped tonight.
- **R2/R3 re-proven live** on the installed runtime: fresh real-profile
  `claude -p` session `1eaa3a55` — accepted decision, four cards selected
  AND loaded (no narrowing), whole instruction bodies in the persisted
  18,748-byte capsule side file, attached pre-speech (record 8 vs 9),
  zero delegations. R7 Installed already holds in the store
  (`expired_at == ended_at` exactly, all four rows); the resumed turn 2
  for R7 Live is in flight.
- **R6 claude demotes** to prior-candidate context (organic hire cannot
  be restaged on demand) — the update contract working as designed.

**Morning decisions queued:** (1) canary parent-transcript preservation
(a new capture surface — owner-gated by brief §3) to make preflight-failed
runs double as R8 artifacts; (2) the R7 anchor re-scope above; (3) whether
the joint-verdict ruling in AR-252 stands.

### Cycle 4 — candidate advance merged; organic hire recurs (03:35–03:50 UTC)

- **Full local gates: 14/14 passed in 14.5 min** at the candidate (after
  two honest catches: the first run died at gate 3 because the ar119 venv
  lacked pip — repaired with `ensurepip` — and an appended `echo` had
  masked a gate failure exit once already; the detached re-run was judged
  by its own summary line).
- **PR #291 merged 03:46:58Z on a verified-CLEAN rollup** (0 pending, 0
  non-SUCCESS/SKIPPED, 8 SUCCESS). The matrix's candidate is now
  `3269ff67`: R1 and R4 claude proven at all four layers — the first
  Installed and Live layers either rule has had on any host — plus R5
  complete, R2/R3/R7 re-proven, R6 demoted. Docs-only merge; no reinstall
  owed.
- **The R6 gap is already closing again**: at 03:45:45Z the loop
  session's own turn organically ran the full hiring ladder on this
  runtime — hiring case `9afaec53` applied, `operations-recovery-plan-reviewer`
  filed (`contractor`, `origin=agency`) and dealt into the very turn whose
  gap created it. The re-proof now lacks only a same-domain reuse turn
  loading it from the pool with no new hiring case; watching for it in
  subsequent turns. *Falsification:* a reuse turn that re-hires instead of
  pool-loading refutes the "filed for next time" half on this runtime.

### Series 3 ledger (small-unit-policy acceptance, runtime `cc478bc88258…`)

- **Run 1** (started ≥08:02Z for the 6.1 spacing; run pair recorded, decision
  `0d611578` 08:05:11Z): FAILED in a **new class** — the parent's routing
  accepted but selected `agency-governance-request-clarifier` (not
  `code-reviewer`, a series first), the parent then fanned out to multiple
  children despite the v3 whole-turn ban (`multiple_child_artifacts`), no
  child staffing decisions were recorded at all, and the final header was
  absent. This is model-behavior nondeterminism, not a provider-stage
  kill: the consecutive-provider-kill chain is broken, no backoff owed,
  and any 6.1 recording must describe a MIXED blocker. Failure kept.
- **Run 2** (08:09–08:11Z): **the best parent result of the night** —
  parent decision `f1715d12` accepted with **`code-reviewer` ALONE**
  (57.9 s, no security-team padding, matching the owner's v3 acceptance
  condition), exactly one child delegation, and only ONE unmet
  prerequisite left in the whole report. Then the child judge draw
  `60da5803` died provider-side at 15.3 s —
  `inference_unavailable` / `native_child_inference_failure`, empty
  selection, no capture row — so the collector honestly reported
  `delivery_marker_absent`. **Third child-stage provider kill**, now
  spanning >6 h: 2026-08-17 evening policy series, 03:50Z, 08:10Z.
- **Run 3** (11:14–11:15Z): **THE ACCEPTANCE DRAW LANDED AND THE JUDGE
  ANSWERED.** Parent decision `1ab1ad0f` accepted with `code-reviewer`
  ALONE (51.2 s, no padding), exactly one child, and the child's captured
  assignment is **138 characters equal to the pure work unit** ("Identify
  the primary behavioral regression risk of replacing return value with
  return value.strip()…"). The child judge evaluated it over the complete
  71-candidate universe — `code-reviewer` among the offered ids, digest
  `5733d4e7…`, provider `claude-subscription`, `inference_attempted:
  true`, `inference_mode: abstained` — and **abstained**
  (`inference_abstained` / `native_child_inference_abstained`, 12.4 s).

**§7.1 IS ANSWERED, NEGATIVELY — and this supersedes the earlier
`blocked-on-provider` framing.** The instrument is fully working: the
pure unit reached a live child judge, over the complete universe, with
the owner's small-unit policy live in the installed prompt (verified in
the launcher's own `judge_protocol.py`: "task size alone is never a
reason to return an empty selection"). The judge declined anyway.

*What this does NOT establish, precisely:* the abstention is **first-pass
and unconfirmed**. The recorded reason is
`native_child_no_specialist_needed`, which the source reserves for "the
repair could not produce a valid answer, so the first-pass abstention
stands unconfirmed" — i.e. the AR-255 P2 funded repair ran and failed to
return a valid answer, almost certainly the same provider flakiness.
The strongest-form decline (`native_child_abstention_confirmed`) has been
observed only ONCE, on 2026-08-17, on the PRE-policy runtime. So: one
post-policy first-pass abstention, not a rate, not repair-confirmed.
*Falsification:* a post-policy draw that returns
`native_child_abstention_confirmed` settles this as the judge's
considered position; any draw that staffs `code-reviewer` refutes it and
mints the first `native_child_delivery_verifications` row.

**Series 3 verdict: 0/3 for staffing** (instrument disobedience;
child-draw provider kill; answered abstention) — but run 3 converted the
§7.1 question from "blocked" to "answered, negatively", which is the
outcome the owner actually needed from this series.

### Series 2 ledger (small-unit-policy acceptance, runtime `cc478bc88258…`)

- **Run 1** (launched ~03:40Z, run `a41782e8`, receipt `f6e49b1c`):
  FAILED at parent preflight — planner `provider_no_valid_response`,
  receipt `workforce_provider_unavailable`. Identical stage to series 1
  runs 2-3. Failure kept; run 2 next, serialized.
- **Run 2** (03:48–03:57Z, run `9bbe05e5`): **the parent chain went green
  on this runtime** — planner applied; recruiter rejected once then
  applied; parent decision `e346e782` accepted with `code-reviewer`
  selected AND loaded (`application-security-engineer` padding returned);
  receipt proven; exactly one child delegation (`e965ec7a`). Then the
  child staffing draw `f1cb84be` died provider-side:
  `inference_unavailable`, source `native_child_inference_failure`, empty
  selection — the judge never answered, no capture row, and the collector
  honestly reported `delivery_marker_absent`. The parent's final response
  header also failed this run (yesterday's policy-series run 2 had one —
  intermittent model behavior, noted). **The small-unit policy therefore
  remains unjudged: the pure unit has still never reached a child-judge
  draw that survived.** This is AR-253 evidence: the child-stage draw has
  now been provider-killed in both the 2026-08-17 policy series and
  tonight's series 2.

**Delegated ruling (brief §4.6): runs 1-2 both provider-killed → second
30-minute backoff, run 3 no earlier than ~04:25Z.** Interim: branch sync
with origin/main; R6 pool-reuse watch continues.

- **Run 3** (04:20–04:3xZ): FAILED at parent preflight again (one
  preflight failure, zero routing). **Series 2 verdict: 0/3
  provider-killed** — planner-dead, parent-green/child-draw-dead,
  preflight-dead. Second consecutive provider-killed series tonight.

### Cycle 5 — between-series consolidation (04:35Z–)

- **Series 3 is scheduled no earlier than 08:05Z**, so the three series
  span ≥6 h (series 1 started 02:02Z); if series 3 also dies at provider
  stages, the §7.1 measurement records `blocked-on-provider` per stopping
  condition 6.1 and stops grinding.
- **AR-252 finding, sharpened:** with the joint-verdict ruling recorded
  and the one-use canary-only capability seal deliberately unwidened, the
  pairing collector CANNOT be built tonight — one envelope needs a
  producer proof and a distinct verifier proof held together, nothing
  today can hold two sealed capabilities at once, and an unsealed
  side-path would weaken the evidence contract. The seal decision (widen
  vs redesign) is a threat-model change and is queued as a MORNING
  DECISION, not taken. *Falsification:* if the owner rules the seal may
  widen to exactly-two one-use consumptions inside one atomic pairing
  transaction, the collector build unblocks immediately.
- **AR-253 receipts filed** for tonight's samples (see the issue doc's
  dated section): recruiter `staff_without_safe_team` ×4 (23:50–01:32Z),
  planner `provider_no_valid_response` ×5 (00:03–04:3xZ across both
  canary series), planner contract-invalid double-rejection ×1 (01:12Z),
  child-draw `native_child_inference_failure` ×1 (03:50Z), against
  accepted draws at 01:47Z (child, staffed), 01:52Z, 02:15Z, 02:35Z,
  02:58Z, 03:06Z, 03:50Z (parent chain green).

## Final status — 2026-08-18

### 1. What is PROVEN

- **R2, R3, R7 claude at all four layers**, candidate `1bd7e37c` (package
  tree == installed `cc478bc88258…`). Fresh real-profile `claude -p`
  session `1eaa3a55`: accepted decision `949ced13` (109.5 s), **four
  cards selected AND loaded with no narrowing**, whole instruction bodies
  in an 18,748-byte persisted capsule attached pre-speech (record 8 vs
  9), zero delegations; resumed turn 2 (run `bfb6c3a5`) carries the
  expiry notice naming all four turn-1 cards pre-speech (record 56 vs
  57), none re-delivered, `expired_at` equal to run 1's `ended_at`
  exactly. Honest caveat: those three rules rest on **two** live events,
  not six.
- **The first verified v6 child delivery** — kept as an existence proof,
  not a cell: child `agent-a3b16809ebb7e199e` record zero, 01:47:41.715Z,
  pre-speech, `launch_id` equal to the parent tool_use id (corroborated
  by the host's own `.meta.json`), `task_sha256` equal to an independent
  recompute over the parent-recorded prompt (which contains no marker, so
  it is a genuine independent witness), card body **byte-identical** to
  `agent_versions.content`, `runtime_digest` equal to the installed
  digest.
- **The section 7.1 acceptance question is ANSWERED, negatively.** Series
  3 run 3, 11:14–11:15Z: parent accepted `code-reviewer` **alone**
  (51.2 s, no padding), exactly one child, captured assignment **138
  characters equal to the pure work unit**, judged over the complete
  71-candidate universe with `code-reviewer` offered — and the judge
  **abstained**. The policy was live in the prompt that judged it,
  verified in the launcher's own `judge_protocol.py`. Qualifier that
  matters: first-pass and **unconfirmed** — the recorded reason is the
  one reserved for "the repair could not produce a valid answer", so the
  P2 repair ran and died, almost certainly the same provider flakiness.
- **A real environment defect, found and repaired**: a stale
  `core.worktree` in the shared `.git/config`, left by an earlier
  remote-control session, was silently pointing every worktree's git view
  at the wrong directory. The owner's WIP was never touched.

### 2. What is REFUTED — including my own claims

- **R1 and R4 claude Installed+Live — retracted by me.** Delivery ran
  **one in fourteen** harness-spawned children at this candidate; three
  unstaffed siblings inside the measuring session carry **no receipt**
  explaining their non-delivery; `native_child_delivery_verifications` is
  still empty, and the matrix's own text says a collector-minted proof is
  the only thing that satisfies Rule 4. Worst of it: **the promotion
  reversed this session's own recorded conservative reading with no
  decision written down** — the exact failure this matrix has logged
  three times. One stated corroboration was also plainly wrong: the
  store's `captured_task` is a 2,000-character truncation and its hash
  does not match the envelope.
- **R5 claude Installed+Live — retracted.** The spawn-authority eval
  emits no package path, and `modules: 295` is shared by both checkouts
  and eight launcher trees, so it cannot evidence which tree it read; the
  Live sentence "Agency started no process" is falsified by its own
  turn's `codex-subscription` CLI call (11.85 s, ending 1.4 s before the
  delegation row). The correct phrasing is "started no **worker**".
- **R6 claude Installed+Live — retracted.** The ladder itself is sound on
  the exact installed candidate, with a real cross-provider security
  review (`verdict: safe`) — an earlier worry that only an inline audit
  existed was **my error**. What fails is the authority's **host-backed
  use** clause: the host's own headers on both turns read
  `agency-steward` with `Recruited via: none`, the only text naming the
  contractor as loaded is Agency-authored, and both runs terminated
  `response_invalid`.
- **"Blocked-on-provider" for section 7.1 — superseded** by run 3's
  answer.

### 3. DECISIONS TAKEN in the owner's absence, each with its falsification

1. **AR-252 joint-verdict shape**, recorded as a delegated ruling in the
   issue: the verdict is a joint object — verifier-authored semantic
   half, collector-assembled binding half, division named explicitly in
   the envelope. *Falsified if* the owner rules the division inadequate;
   every envelope stays auditable by its named halves.
2. **The one-use capability seal was NOT widened**, so the AR-252 pairing
   collector was not built. *Falsified if* the owner rules the seal may
   widen to exactly two consumptions inside one atomic pairing
   transaction — the build unblocks immediately.
3. **Series backoffs and spacing**: 30 minutes after two consecutive
   provider-stage kills, at least 6 hours across series. *Falsified if* a
   clean draw arrives inside a backoff window.
4. **Retracting four cells rather than qualifying them.** *Falsified if*
   the owner judges the existence proof sufficient for R4 Live with the
   delivery rate disclosed in the Limitation column — that is a
   defensible reading, and it is his to make.

### 4. MORNING DECISIONS — concrete choices

1. **R8 capture surface.** Allow the canary to preserve a bounded,
   redacted parent transcript so a preflight-failed run can prove "an
   unstaffed turn proceeded"? It is a **new capture surface**, which
   section 3 reserves to the owner. Yes or no.
2. **AR-252 capability seal.** Widen the one-use verified-delivery
   capability to exactly two consumptions inside one atomic pairing
   transaction, or redesign the collector around a single capability?
   Nothing collects a real envelope until this is chosen.
3. **The small-unit policy, given the answer.** The judge declined the
   pure 138-character unit *with* the policy live. Sharpen the policy
   further, accept the decline as correct behaviour for a one-paragraph
   brief, or re-measure for a repair-confirmed decline first?
4. **Does the joint-verdict ruling stand?**
5. **R4's standard.** Keep the strict collector-only reading, or accept a
   host-artifact existence proof with a disclosed delivery rate?

### 5. Still blocked, and whose hands it needs

- **codex** — attended TUI trust; bypass evidence never counts. Owner.
- **zcode** — no CLI executable on this box. Owner.
- **openclaw / hermes** — absent by instruction; the runnable
  verification packet is in the repo for the owner's own boxes.
- **R8 and the AR-252 collector** — the two decisions above. Owner.
- **The unexplained non-deliveries** — three harness-spawned children in
  one session got no card, and no receipt explains why. That is the
  sharpest *engineering* lead left and it is **not** blocked on the
  owner: a receipt bound to every child launch would turn a 1-in-14
  mystery into a measurement.
- **Provider flakiness (AR-253)** — receipts filed, no chase attempted.

### 6. Caveats

No codex bypass runs were performed, so nothing here is bypass-derived.
Every canary was isolated-profile, attended trust, `--timeout 420`,
strictly serialized. The R6 evidence came from a sibling autonomous
session on the same machine — same host, same installed digest, but a
conflict-of-interest note worth the owner's eye. No installs were
performed and no host was touched.

### 7. Branch, commits, and what is where

Branch `codex/ar119-vision-mitigation-handoff`. PRs #290, #291, #292 and
#293 all merged to main on verified-CLEAN rollups; the retraction commits
sit on the branch for review. The full local gate suite passed **14 of 14
in 14.5 minutes** before the candidate advance. Main is untouched except
through those PRs, nothing was committed in the primary checkout, and the
owner's WIP there is exactly as he left it.

## Correction, 2026-08-18: the receipts were never missing, and R4's real blocker is the capability seal

This section retracts a claim this session made hours earlier and replaces
it with a measured one. It was written after the loop stopped, on the
owner's instruction to start the receipt-binding work — and the first step
of that work showed the work was largely unnecessary.

### Retracted: "three harness-spawned children got no card and no receipt explains why"

That sentence appeared in the final status document and in the capsule.
**Two of the three are fully explained, and their receipts existed the
whole time.** Launch `toolu_01Uoswski9DJv7Hz4jg1SYFg` (11:21:06Z) has
decision `19d542bf` recorded at 11:21:05.97, and the 11:21:39Z launch has
`cb5a4f26` at 11:21:37.79 — both `inference_invalid` /
`native_child_inference_failure`, the same child-stage provider failure
the canary series recorded three times.

The reason both the reviewer and this session missed them is instructive:
**we looked for a `launch_id` column and there isn't one.** The linkage is
`context_fingerprint`, a deterministic digest of (host, parent session,
parent trace, launch id, task sha256). Recomputing it from the child's own
`.meta.json` `toolUseId` plus the parent-recorded prompt reproduces the
stored value exactly — verified: computed `11eb6a90b71cc871d4c57bb706a77f74`,
stored `11eb6a90b71cc871d4c57bb706a77f74`. Receipts are joinable to child
launches today, with no schema change and no new capture.

This is the fourth time in this effort that a claim died because it was
scored over the wrong set. The rule the capsule already states — *ask
which exact set this claim is scored over* — should have been applied to
the word "unexplained" before it was written down.

### The one genuine silent hole (narrow, real, worth fixing)

Exactly one child launch left nothing: `a2bd9b49…` at 02:59:41Z. At that
instant **no parent run was open** in the session — the previous run
closed 02:51:29 and the next opened 03:02:34.
`_native_child_staffing_parent` therefore returned no trace, and both
`staff_native_child` and `_record_native_child_unstaffed` returned
silently, the latter by explicit design ("persist one content-free reason
only when its parent is exact and live"). That case is genuinely
indistinguishable from a hook that never ran, which is the exact confusion
this project has been bitten by twice.

Bounded fix, for whenever it is scheduled: record one content-free
observation — host, launch id, session id, reason
`native_child_parent_not_live` — when a child launch is seen and declined
for want of a live parent. Note that the existing receipt lanes are
trace-keyed, so this needs either a nullable-trace row or its own lane,
and a new table means a `SCHEMA_VERSION` bump, which on this machine
disables every hook until all three hosts are reinstalled. Sequence it
deliberately; do not let it ride along with other work.

### The finding that matters more: R4 and AR-252 share one blocker

`agency evidence children --host claude --json` already exists, already
scans the artifact root (157 artifacts, 659 filesystem entries), and
already finds our v6 delivery: `v6: true`, `pre_speech: true`,
`correlated: true`, `decision_id native-child-3507ad14…`, the exact card
in `diagnostic_cards`. It reports `verified_delivery: false` for a named
reason — **`host_hook_output_origin_not_proven`**.

Reading `_expected_v6_reason`: that reason is returned when `expected is
None` and the artifact carries no structural hook-output marker.
`expected` is the **one-use verified-delivery capability**, which
`_consume_verified_host_child_delivery` pops on read and whose sole
production consumer is `canary_proof.py`, collecting inside a disposable
host profile under ADR-0158. A read-only CLI projection cannot supply it
and must not consume it.

**So Rule 4 Live can only ever be proven inside a canary run.** Not
because receipts are missing, and not because delivery is broken — the
delivery is real and verifies to the byte — but because the only code path
permitted to *verify* a delivery is the canary's in-lifetime private-lease
collector. That is why `native_child_delivery_verifications` has zero rows
after fourteen child launches, one of them a perfect delivery.

And the canary path requires the child judge's draw to survive the
provider, which it has not done once in this machine's recorded history.

**This unifies two open items.** AR-252's pairing collector is blocked on
the same one-use seal (constraint 2 in its issue: nothing can hold two
such capabilities at once). The seal is therefore not just AR-252's
question — it is simultaneously the reason Rule 4 cannot be proven outside
a disposable profile. Whatever is decided about widening, redesigning, or
keeping it should be decided once, for both.

**Falsification:** if a future `agency evidence children` run reports
`verified_delivery: true` for any artifact without a canary having
consumed a capability for it, this reading is wrong. If the owner rules
that an origin-proof may come from a source other than the one-use
capability, R4 Live becomes provable from artifacts already on disk today.

### The child-to-receipt join needs no code change, and the fix I tried was wrong

Attempted 2026-08-18, reverted the same session. Recorded because the
attempt is what produced the answer.

**What I tried and why it failed.** The plan was to make the join
first-class by adding `launch_id` to the native-child routing-decision
projection and to `_ROUTING_DECISION_FIELDS`. A persisted-row test made it
pass. It also broke **five existing contracts** that are green on the
unmodified tree (verified by stashing: 137 passed clean, 133 passed plus 5
failures with the change): four native-child staffing tests began
returning `native_child_routing_decision_unavailable` — the sealed
success-route readback rejecting the changed projection — plus one
ready-receipt test. Removing the field from the success path alone did not
clear it, so the blast radius comes from widening the **shared** decision
allowlist, not from the native-child route. `_ROUTING_DECISION_FIELDS` is
load-bearing for every routing decision and for the ready-receipt payload;
it is not a place to add a field casually. Reverted to clean.

**What actually works, today, with the store as it stands.** Three
independent join keys already exist, and each covers a different case.
Applied to the four harness-spawned children of session `f3066348`:

| child | join that resolves it | outcome |
|---|---|---|
| `a3b16809…` | v6 envelope `decision_id` in record zero | staffed (`applied`) |
| `a3b13d36…` | `sha256(child's own assignment)` == `routing_decisions.query_hash` | declined (`inference_invalid`) |
| `a8796913…` | recomputed `context_fingerprint` | declined (`inference_invalid`) |
| `a2bd9b49…` | none — genuinely unrecorded | silent hole |

Note the complementarity: the fingerprint resolves `a8796913` but not
`a3b13d36`; the `query_hash` route resolves `a3b13d36` but not
`a8796913`. Either alone looks like a 50% evidence gap; together they
leave exactly one unresolved child. **This retracts the sharper form of
my earlier claim that receipts are reliably joinable by fingerprint — they
are joinable, but only by trying all three keys.**

The `query_hash` route is the most useful of the three because it needs
nothing but the child artifact: strip any appended v6 envelope from record
zero, hash the remainder, and look it up among that session's decisions.

**The one real hole, unchanged:** `a2bd9b49…` launched 02:59:41Z when no
parent run was open (previous run closed 02:51:29, next opened 03:02:34).
`_native_child_staffing_parent` returns no trace, and both
`staff_native_child` and `_record_native_child_unstaffed` return silently
by design. That case still reads exactly like a hook that never ran.

**Next step, when it is scheduled:** build the three-key resolver as a
read-only projection (extending `agency evidence children`, which already
walks the artifact root) rather than changing what is written. It turns
delivery into a countable rate immediately and carries none of the risk
that broke five contracts here. Only after that is the silent hole worth a
schema decision, because only then is its true frequency known — one in
fourteen is an upper bound measured by hand, not a rate.

*Falsification:* if a child artifact resolves under none of the three keys
while its decision demonstrably exists (as `a3b13d36`'s did, with
`task_chars` matching to the character), then a fourth key is in play and
the resolver is incomplete.

### The delivery rate is now a command, and it reads 1 staffed of 14

`agency evidence child-launches` shipped 2026-08-18. It reports one outcome
per harness-spawned child — staffed, declined, or unrecorded — by trying the
three join keys already in the Store, and it is read-only: no writes, no
capability consumption, no minted receipts, so an outcome is a diagnostic and
never delivery proof (ADR-0156).

**First real measurement**, scoped to the current install:

~~~text
agency evidence child-launches --host claude --since 2026-08-17T21:00:00.000Z
claude: 14 child launches since 2026-08-17T21:00:00.000Z --
        1 staffed, 6 declined, 7 with no record
  46 launch(es) fell before the window
~~~

This replaces the hand-measured "1 in 14 delivered, 13 unexplained" with
something a rerun can reproduce. Six of the thirteen non-deliveries carry a
recorded reason; they are Rule 8 working, not evidence gaps.

**Two findings the build produced, both of which read exactly like a host
that never spawned anything — the failure shape this project has been bitten
by three times:**

1. The default artifact root holds children **two** directories down
   (`<project>/<session>/subagents/`). A single-depth glob reported **zero
   launches** on the first live run. Both shapes are accepted now, pinned by
   a test.
2. An artifact root spans every runtime that ever ran on the machine. Counting
   all 60 launches against today's install would report a rate for runtimes
   that never saw them, so `--since` scopes the window and states what it
   excluded rather than dropping it silently.

**Caveat, stated because the number is not yet trustworthy in one direction:
7 is an UPPER BOUND on the true silent count.** The `context_fingerprint`
key does not appear to fire through the CLI path — child `a8796913…`
resolves by fingerprint in a manual recompute but reads `unrecorded` here.
The other two keys are sound, and the one genuinely silent child from the
overnight run (`a2bd9b49…`, launched 02:59:41Z with no open parent run)
reports correctly. *Falsification:* if wiring the fingerprint lookup
correctly moves `a8796913…` from `unrecorded` to `declined`, the true silent
count is 6 or fewer and the headline rate improves accordingly.

**What this does not change.** Rule 4 Live still cannot be proven from these
artifacts: `agency evidence children` continues to report
`host_hook_output_origin_not_proven`, because only the canary's in-lifetime
private-lease collector may consume the verified-delivery capability. The
capability seal remains the blocker, for R4 and AR-252 alike.

## Owner ruling, 2026-08-18: what "done" means, and what it does not change

The owner ruled directly: **done for this session means claude, codex, zcode —
in that order.**

**What this fixes.** The completion contract was unsatisfiable on this machine.
Rule 9 requires rules 1-8 on all five supported hosts; openclaw and hermes are
absent by the owner's own instruction, so the matrix could never close and every
plan built on it inherited an open end. Session completion is now measured
against three hosts, worked in the stated priority order: **claude first, then
codex, then zcode.**

**What this deliberately does NOT change, and must not be read as changing.**

- **Rule 9 itself is untouched.** The founding vision still requires parity on
  all five hosts, and `AR-119-founding-vision.md` remains the sole wording
  authority. Its `canonical_block_sha256` is unchanged because no rule text
  changed. A semantic change to the nine rules needs an explicit owner
  confirmation and a new canonical digest; this ruling is not one and must not
  be used as a precedent for one.
- **No matrix cell moves.** openclaw and hermes rows stay `unproven`, with their
  existing reason. The matrix's own contract is that an unavailable host stays
  unproven and that a host becoming unavailable cannot improve a cell; scoping a
  session's definition of done cannot improve one either.
- **R9 stays `unproven` on every host.** It derives from R1-R8 across all five;
  narrowing the session's scope does not narrow the rule's.

**How to read the two together.** Session scope answers "what do we work on and
when do we stop"; Rule 9 answers "what does the product claim". The claim is
still five-host parity. What changed is that the session no longer waits on two
hosts nobody can reach from here.

*Falsification:* if a future session reports the nine-rule vision as complete
while openclaw and hermes remain unproven, this ruling has been misread — it
scopes the session, never the vision.

### Push blocked by a pre-push/worktree git-config fault (2026-08-18, boxed)

Work through commit `49736e26` is committed on the branch and **not pushed**.
The full 14-gate suite passed (14.0 min) before these commits; docs added after
it are docs-only with `verify_docs` green.

**What blocks it.** The pre-push hook runs `run_local_gates.py --fast` with
`GIT_DIR` set and no work tree, and gates whose tests shell out to `git`
(`test_ci_change_scope.py`, `test_release_packaging.py`) fail there with
`fatal: this operation must be run in a work tree` — while passing standalone
(19 passed, and 14/14 gates green). Pushing from the primary hits the same
class of fault.

**Why it appeared now.** The repository's shared config carries `bare = true`
with `extensions.worktreeConfig = true`. Earlier pushes worked because
`core.worktree` pointed the primary at the `remote-control-7efcd5` worktree —
the same setting diagnosed as the "git status lies" hijack. Removing that
worktree and unsetting `core.worktree` removed the compensation and exposed
`bare = true` underneath. So the hijack was load-bearing for pushes, which
nothing recorded.

**Current state, verified:** primary on main `4939466d` with the owner's WIP
intact and `git status` working; ar119 clean at `49736e26`; `core.bare` false
per-worktree; `core.worktree` unset everywhere.

**Do not** push with `SKIP_LOCAL_GATES=1` — forbidden, and it would skip the
gates that catch exactly this class of fault. The bounded next step is to
decide whether `bare = true` in the shared config is intentional; if it is not,
correcting it there (rather than per worktree) should restore ordinary pushes
from any checkout. *Falsification:* if a push succeeds from a fresh clone of
the same branch, the fault is local config, not the hook.

### The push path writes `core.bare = true` into the real repository config

Isolated 2026-08-18 by direct measurement, after the earlier entry blamed a
pre-existing `bare = true`. **That reading was incomplete: the corruption is
created by the push itself.**

Measured, in order, on the same tree:

1. Set `core.bare false` in `.git/config`; confirm `git rev-parse
   --is-bare-repository` is `false`, `git ls-files` exits 0, and
   `test_tracked_release_inputs_pass_hygiene_check` **passes**.
2. Run `git push origin <branch>`. The pre-push hook's gates fail on
   `tests/test_ci_change_scope.py` and `tests/test_release_packaging.py`.
3. Read `.git/config` again: **`bare = true`**.

So each push attempt corrupts the repository config and then reports the
failure that corruption causes. The failing tests shell out to `git ls-files`,
which returns exit 128 (`fatal: this operation must be run in a work tree`) in
a repo marked bare. They pass standalone and passed in the full 14-gate suite;
they fail only after a push attempt has flipped the flag.

**Consequences worth acting on.** A test or script in the pre-push path is
writing to the real `.git/config` — mutating developer machine state as a side
effect of running gates. That is a defect in its own right, independent of
AR-119: it also explains why `git status` in the primary checkout stopped
working mid-session, and it is the mechanism that made `core.worktree` look
load-bearing (it was compensating for a flag something keeps setting).

**Do not** work around this with `SKIP_LOCAL_GATES=1`; that hides the defect
and skips gates. The bounded next step is to find the writer: run the pre-push
gate list one file at a time with `.git/config` watched for modification, and
start with the two suites that fail, since both exercise packaging and CI
scope logic that reads repository layout.

*Falsification:* if `bare` stays `false` across a push attempt on a fresh
clone, the writer is local to this repository's configuration rather than the
gate code.

**State left for the owner:** `core.bare` restored to `false`; both checkouts
verified healthy; owner WIP untouched; work committed through `cdfbcddb` and
**not pushed**.

## Session 2026-08-19: codex canary series, the seal decision, and R8 from disk

Runtime for everything below: installed digest
`f7b84c8a40fab541640d07a341af92591ba1f2f4d7dfd11124208635116f9dbb`
(merge `6ba837fa`, PR #296), schema 47 == store 47, all three hosts on one
digest. **This is a NEWER candidate than the matrix's `1bd7e37c`** (whose
package tree equals merge `99a7b3ac`, digest `cc478bc88258…`). No matrix
cell is moved by this session; see "what claiming R8 would cost" below.

Note for anyone re-running these commands: `agency` on PATH resolves to
`~/.local/bin/agency.exe`, which is **schema 45** and refuses the store with
`database schema is newer than this runtime (47 > 45)`. Every command below
was run as `python -m agency_runtime.cli …` from this checkout, whose tree is
the installed `source_root` recorded in
`~/.agency-runtime/launchers/current-<host>.json`. `C:\agency-cli` holds the
**host** CLIs (`claude.CMD`, `codex.CMD`), not the Agency CLI.

### Codex canary series — three runs, deterministic, and NOT the AR-253 flake

Probe first: `agency eval routing --json --no-details` returned
`passed: true` (v1.4.0). Readiness for codex: `ready: true`,
`unmet_prerequisites: []`, `trust_mode: attended`. Three serialized live runs
followed (`--execute --confirm "RUN LIVE codex CANARY" --timeout 420`), runs
`231919ee` 03:53:28Z, `c7bea5d0` 03:55:59Z, `e70b6bd7` 03:58:09Z.

**All three runs are identical in every recorded field.** That is the
finding: this is not load-shaped and it is not the provider defect AR-253
tracks.

~~~text
canary_passed        false   (x3)
invocation.status    failed  -> codex_collaboration_projection_unavailable
collaboration_diagnostic
  spawn_count 1  child_start_count 1  wait_count 1  tool_output_count 2
  followup_count 0  child_interaction_count 0  agent_message_count 9
  unexpected_item_count 0   reason native_collaboration_topology_invalid
preflight            workforce_inference_failed / runtime_error
provider attempts    planner   codex-fast gpt-5.6-terra applied
                     recruiter codex-fast gpt-5.6-terra applied
cardinalities        routes 0  native_child_routes 0
                     native_child_deliveries 0  specialist_loads 0
~~~

Two things in that block deserve to be read slowly.

**1. Both provider stages APPLIED.** On claude the parent-stage failures in
this same window are provider rejections — `no_safe_sufficient_team`,
`recruiter_abstained`, `inference_unavailable`, `composition_order_invalid`.
On codex the planner and recruiter each returned
`structured_response_applied` and preflight *still* failed. Nothing here
resembles the AR-253 recruiter/planner defect, and chasing provider health
will not move it.

**2. The topology counts all PASS, and the diagnostic still reports
failure.** Walk `_codex_collaboration_diagnostic_reason`
(`agency_runtime/core/canary_backends.py:2346-2373`) with the observed
counts: spawn is present and unambiguous, followup is correctly absent under
the canary contract, wait is present and unambiguous,
`tool_output_count 2 >= spawn 1 + followup 0 + wait 1`,
`child_start_count 1 >= spawn_count 1`,
`child_interaction_count 0 >= followup_count 0`. Every guard passes and the
function falls through to its terminal
`return "native_collaboration_topology_invalid"` — a reason with no success
counterpart. `_CODEX_COLLABORATION_FAILURE_REASON_BY_DIAGNOSTIC` then maps
it to `codex_collaboration_projection_unavailable`.

So the reported reason is **misleading by construction**: the topology is not
invalid. The diagnostic only runs when the strict projection already returned
`collaboration is None`, and it cannot name why. The honest reading is
"the strict collaboration projection failed for a reason the content-free
diagnostic cannot express", not "codex built an invalid topology".

**What codex actually did: it spawned the child and the child started.**
`spawn_count 1`, `child_start_count 1`. The host side worked. What failed is
Agency's ability to *read* it.

*Falsification:* a codex canary run whose counts differ from the block above,
or one where `collaboration` is non-null, refutes the determinism claim. A
fourth run with a different `reason` refutes the fall-through reading.

### The claude control — both hosts fail, at different walls

Comparing three codex canary runs against claude's *real-profile* turns would
have been a confound, so a claude canary was run in the same window under the
same flags.

~~~text
claude canary: invocation.status  completed        (codex: failed)
               isolated_plugin    invoked+loaded   (codex: registered+enabled)
               host_child_collection_reason  delivery_marker_absent
               header_missing     2 fields         (codex: all 5)
               trust_bypass_used  false            (codex: true)
               no preflight failure, no evidence block
~~~

**This is the answer to "compare the child judge's behaviour against
claude's".** The two hosts stop at different places:

- **claude** reaches child-delivery collection. The in-lifetime collector
  ran and returned `delivery_marker_absent` — it looked in the child artifact
  for the v6 marker and did not find one. The child-judge path is *reached*
  and fails one step from the end.
- **codex** never reaches it. The parent's own preflight dies first, no
  routing decision is recorded at all, and `native_child_routes` is 0. The
  child judge is never invoked, so there is no codex child-judge behaviour to
  compare yet.

Corroborating the second point from the store: **codex's last
`routing_decisions` row of any kind is 2026-08-11T22:04:22Z.** The canary
used to record them (45 rows `codex_activation_canary_inference`,
2026-07-31 through 2026-08-03); it records none now.

### Codex Rule 4 is blocked one layer EARLIER than the seal

This is the fact that reorders the priorities, and it is deliberate design,
not a regression.

`agency_runtime/core/child_delivery_evidence.py:636-641`, the first statement
in `_expected_v6_reason`:

~~~python
if host == "codex":
    # Codex 0.147 stores the delegated input as ordinary developer/user
    # records and carries the actual V2 inter-agent message opaquely. There
    # is no host-authored field identifying Agency's hook output.
    return "unsupported_opaque_interagent_channel"
~~~

It returns **before the capability seal is consulted at all**. And
`agency_runtime/adapters/hooks.py:1310-1320` refuses to staff a codex native
child whenever `attest_codex_plaintext_spawn` cannot authenticate the spawn,
recording `_record_native_child_unstaffed` with the same reason and never
blocking the child.

**Therefore: whichever way the seal is decided, codex Rule 4 does not move.**
Codex can be staffed when its spawn is plaintext-attestable, but a codex
delivery can never *verify* through this path. This is exactly what ADR-0158
already states ("Codex card delivery through the current opaque channel
remains unsupported; Codex remains a supported host and proceeds
unstaffed") — the canary series is the first live confirmation of it on this
machine, and it is the documented state, not a defect to chase.

### The one-use verified-delivery capability seal — the decision

`native_child_delivery_verifications` holds **0 rows, ever**. The seal has
never been consumed successfully.

The seal is two independent gates, both in `child_delivery_evidence.py`:

1. **The `expected` capability.** `_expected_v6_reason` returns
   `host_hook_output_origin_not_proven` when `expected is None` **and**
   `structural_hook_output` is false (lines 640-646). The read-only entry
   points pass `structural_hook_output=False` hardcoded (lines 1151, 1226),
   so `agency evidence children` can never verify.
2. **The sealed atomic Store consumer.** `_consume_exact_verification`
   requires a `_NativeChildDeliveryVerificationConsumer` built with the
   module-private `_VERIFICATION_CONSUMER_SEAL`; anything else returns
   `atomic_verification_consumer_not_supplied`. Only the Store's own
   `_record_native_child_delivery_verification` can mint the row.

**The reason for gate 1 is not paranoia — it is a gap in Claude Code's
artifact format.** The comment at lines 1147-1150 states it: Claude
identifies record zero as side-chain child input but does not tag any
substring as hook-authored, so exact one-use expected-decision correlation is
required before this can verify. The host cannot self-attest which bytes in
record zero came from the hook. The one-use capability substitutes for a
marker the artifact does not carry.

**Option A — keep the seal one-use and canary-only; make the canary
deliver.** The claude control already names the exact remaining step:
`delivery_marker_absent`. The collector runs in-lifetime inside the
disposable profile and finds no v6 marker in the child it spawned; the work
is to make that child actually receive a card.

*Costs:* no new capture surface, no schema bump, no ADR change, no widening
of ADR-0158 — the cheapest path by far, and the only one that needs no owner
authorization under §3 of the loop brief. *What it permanently forfeits:*
Rule 4 Live becomes provable **only** inside a canary. The real-profile v6
delivery of 2026-08-18 01:47Z — the one fully-bound existence proof this
project has — stays unverifiable forever, and delivery can never be measured
as a rate on the owner's real profile. AR-252's collector must then also live
inside a canary.

**Option B — let the host artifact self-attest: make `structural_hook_output`
true for claude.** Change what the hook writes into the child's record zero
so the artifact carries a host-distinguishable hook-output marker. Then
`expected=None` yields `expected_decision_not_supplied` — a nameable, weaker
state — instead of `host_hook_output_origin_not_proven`, and a read-only
consumer can mint a *distinguishable* verdict. The type already contemplates
this: `_NativeChildDeliveryVerificationConsumer`'s own docstring reads
"Sealed adapter for the Store's atomic **or read-only** exact consumer."

*Costs:* (a) it changes what is written into a host artifact — a **new
capture surface**, which §3 of the loop brief reserves to the owner; (b) it
needs a new verification lane and therefore a `SCHEMA_VERSION` bump, which
disables every hook machine-wide until every host is reinstalled; (c) it sits
against ADR-0158's "No CLI or dashboard operation may mint a delivery
receipt, and Store-only state cannot create the capability" — to keep that
guarantee the read-only verdict must be typed so it can never be counted as a
Rule 4 proof, which means the strong claim still requires Option A's canary
anyway. *What it buys:* real-profile deliveries become countable, which is
what turns Rule 4 from an existence proof into a rate, and it is the only
option that ever lets the 01:47Z artifact be verified.

**Neither option moves codex** (previous section). If the priority order is
codex-first, the seal is not the thing standing in the way — the opaque
inter-agent channel is.

*Falsification:* if a read-only consumer can be built that satisfies
`_consume_exact_verification` without the Store's private method, gate 2 is
weaker than described. If any claude child artifact is found carrying a
host-authored field that identifies hook output, the line-1147 comment is
stale and Option B is far cheaper than costed here.

### R8 claude — provable from a fail-open turn already on disk, no new capture surface

**Asked and answered: yes, R8 does not need the proposed canary
parent-proof.** The morning decision to add a bounded parent-proof to the
canary attestation can be declined on evidence grounds.

The artifact is this very session. Run `e9715480`, trace
`2a77824c-d862-4f64-b3ac-ee186e958b94`, session
`abaccac6-ca45-4abd-91ec-c6a31a9f8c5b`, host claude, real profile,
`status = preflight_failed`, started 03:42:54.194Z, ended 03:46:30.052Z,
turn_sequence 1013. Host artifact:
`~/.claude/projects/C--Workspaces-Holeshot-Software-agency-runtime--claude-worktrees-ar119-vision-mitigation-5fbd88/abaccac6-ca45-4abd-91ec-c6a31a9f8c5b.jsonl`
(287 records), written by Claude Code and retained where the host wrote it.

The three facts the authority needs, all from the host's own file:

| # | Record | Time | What it shows |
|---|---|---|---|
| 1 | 2, `hook_success` SessionStart | 03:42:53.278Z | `command` names `C:\Python313\python.exe -I -S …\launchers\runtime-sha256-f7b84c8a40fa…\site-packages\agency_runtime\_bootstrap.py` — the installed launcher, by digest |
| 2 | 9, `hook_additional_context` UserPromptSubmit | 03:46:30.231Z | the **entire** delivered context, 1 element, 1,309 chars, inline |
| 3 | 11, `assistant` | 03:46:31.858Z | the host's first published text, 1.63 s later |

Record 9 is the decisive one. It is retained **inline and complete** in the
host transcript — not a side file — and it contains the resident-steward
kernel and nothing else. Checked by substring: `[AGENCY LOADED]` absent,
`[AGENCY` absent, `Instructions:` absent, `CARD ` absent. Store corroboration
on the trace: `specialists_loaded` 0, `routing_decisions` 0,
`delegation_events` 0, `skills_loaded` 0. The receipt is
`workforce_inference_failed` / `["inference_invalid"]` at 03:46:30.052Z,
179 ms before the host wrote record 9, and `agency evidence rejections`
partitions this trace under **"Agency was blind"**, not "withheld".

**Why this is stronger than the cells retracted on 2026-08-18.** The R5
retraction died because the negative half ("Agency started no process") was
borrowed from source reading rather than measured. Here the negative is
*observed*: the complete delivered context is present in the host's own
artifact, and it demonstrably contains no card. Absence in a retained record
is a measurement, not an inference. And the R5 retraction's own prescribed
remedy — run the eval through the installed launcher's own bootstrap, which
executes under `-I -S`, and retain the command line — is present here for
free, because Claude Code records the full hook command line itself
(records 2, 17, 19, 24, 28, 33, 35, all naming digest `f7b84c8a40fa`).

**Three honest limits, stated before anyone promotes this.**

1. **The UserPromptSubmit record does not itself carry the command line.**
   Record 9 has no `command`, `exitCode`, or `durationMs`. Its binding to the
   installed launcher comes from neighbouring host records in the same
   session and the same turn (record 2 at 03:42:53, record 17 at 03:46:52),
   both naming `f7b84c8a40fa`. Claude Code runs all Agency hooks from one
   settings config, so this is sound — but it is an inference across records,
   not a byte-level property of record 9.
2. **`inference_invalid` is not the purest form of "unavailable".** It means
   inference ran and its output failed validation, which is nearer "Agency
   could not assemble a safe team" than "Agency was unreachable". Rule 8's
   operative line is that Agency never *withholds*, and the turn was plainly
   not withheld. A cleaner instance would be one of the
   `workforce_provider_unavailable` traces (`99124b2b` 03:08:24Z,
   `911912d8` 03:00:53Z), both in session `f3066348`.
3. **One turn, not a rate** — the same limitation every proven claude cell
   carries.

**What claiming it would cost.** This evidence sits at digest
`f7b84c8a40fa`; the matrix candidate is `1bd7e37c` / `cc478bc88258…`.
Marking R8 Installed/Live requires advancing `candidate_commit` under the
matrix update contract and **re-anchoring every existing citation** — R2, R3
and R7's proven cells included. That is the real price, and it is a
bookkeeping price, not an evidence price. No cell is moved here.

*Falsification:* if record 9's `content` list is found to be truncated by
Claude Code rather than complete, the observed-absence argument collapses to
an inference and this is no stronger than the retracted cells. If any
`specialists_loaded` row is later found on trace `2a77824c`, the turn was not
unstaffed and the candidate is void.

### Correction recorded against this session's own work

An earlier reading of these runs held that **empty `staffing_reason_codes` on
the codex receipts was a codex evidence-parity defect** — codex recording
`[]` where claude records a populated list. The control refutes it: codex has
recorded populated codes 16 times (`inference_invalid` x7,
`no_safe_sufficient_team`/`recruiter_abstained` x6,
`independent_assurance_missing` x2, `inference_unavailable` x1, latest
2026-08-14), and claude has 11 empty receipts of its own. The column is not
host-specific and the finding was withdrawn before it was reported. What
survives is narrower and still worth knowing: **every codex receipt since
2026-08-14 is empty, and all three canary receipts are empty** — consistent
with the canary path rather than with the host.

### `delivery_marker_absent` is the policy working — and it settles §7.1

Diagnosing why the claude canary stopped at `delivery_marker_absent` produced
a larger result than the diagnosis. **The canary's child got no card because
the child judge deliberately declined to staff it, and this time the decline
is repair-confirmed.**

First, what the reason code actually means
(`child_delivery_evidence.py:1698-1735`): `delivery_marker_absent` is
returned *after* `_trusted_launch_prefix_bytes` accepted the file. The child
artifact was found, passed the ownership/link/parent-chain guard, and was
read — it simply carried no v6 envelope. This is explicitly separated in the
source from `artifact_not_trusted` because the two "have opposite fixes". So
the collector is working; there was nothing to collect.

**The canary parent run is `43a081d6`**, session
`df0fd324-8aeb-44f1-937e-5cf455be4bc7`, trace `1330662e`, 04:00:52 →
04:03:20Z, and it did **not** fail preflight — it terminated
`response_invalid`. The parent was staffed normally: decision `c75f7f6c`
`accepted` over 293 candidates, selecting `code-reviewer` and
`application-security-engineer`, with two matching `specialists_loaded` rows
and one completed `delegation_events` row (`unit-05d45f7553`, backend
`delegate_task`).

**Then the child judge ran, and declined.** Decision `5c963e09`:

~~~text
status               inference_abstained
source               native_child_inference_abstained
native_child_reason  native_child_abstention_confirmed
provider             claude-subscription     latency_ms 13974
task_chars 138       task_lines 1            candidate_count 71
inference_attempted true  inference_configured true  inference_required true
inference_mode       abstained
selected_ids []      semantic_ids []         top_score 0.0
offered_agent_digest 5733d4e7aa75fb48812f9e7733ba811deec06b12180a50a4272c594f018e0897
~~~

The captured assignment is 138 characters, one line, recorded verbatim:

> Identify the primary behavioral regression risk of replacing return value
> with return value.strip() in a Python text-normalization helper.

**This is the §7.1 acceptance draw, and it lands on the settling condition.**
The capsule recorded the open question as: the 2026-08-18 11:15Z draw
abstained "first-pass only; the repair returned no valid answer, so it is
unconfirmed. **A repair-confirmed post-policy decline would settle it**; any
staffing refutes it."

`native_child_abstention_confirmed` is precisely that. The two reasons are
deliberately split — `native_child_staffing.py:91-99` states that the legacy
reason "means the first-pass abstention stood because the repair could not
produce a valid answer; the confirmed reason means the judge tested its own
abstention on the repair call and reaffirmed it. They must never collapse
into one code." The confirmed branch (line 1223) is reachable only after a
second `query_judge` call on `repair_abstention_task(original_task)` with
`candidate_scope="complete"`, which must return `status == "applied"` **and**
`inference_mode == "inferred"`, whose `selected_ids` must be a `list` (strict
`type(...) is not list` check at line 1196) and must be empty. Anything less
falls to the legacy unconfirmed reason at line 1209.

So: the pure 138-char unit, the complete 71-candidate universe with its
offered-agent digest recorded, the owner's small-unit policy live, a funded
repair call, and a reaffirmed decline — on the **current** runtime
`f7b84c8a40fa`, not the 2026-08-18 one. Two independent clean draws now
return the same answer.

**The one real weakness, stated plainly.** The repair call leaves **no
retained receipt**. `_unstaffed` (`native_child_staffing.py:645-701`)
persists only the routing projection and the captured assignment;
`provider_attempts` are returned in-process on `NativeChildStaffingResult`
and never written. The two `model_receipts` rows on this trace are both
stamped 04:02:00.784 — the parent's planner (haiku) and recruiter (sonnet);
the child judge's decision at 04:02:35.498 has none. **The confirmation
therefore rests on the reason code's code-level invariant, not on an
independent artifact.** That invariant is genuine — unlike R6's
`critic_evidence["approved"]`, which was a hardcoded literal, this branch is
actually gated on an applied, inferred repair result — but nothing on disk
cross-checks it. The only corroborating signal is the 13,974 ms latency, and
that is weak: the 2026-08-18 01:47Z child staffing took 11,850 ms for what
appears to have been a single call, so 13.97 s is on the short side for two.
Do not quote this cell as receipt-backed.

*Falsification:* if a future draw records `native_child_abstention_confirmed`
with a latency inconsistent with two provider calls, or if the confirmed
branch is found reachable without an applied repair, the settlement is
unconfirmed again. Any draw that **staffs** the 138-char unit refutes it
outright.

### What this does to the seal decision

**It removes the naive form of Option A.** "Make the canary deliver" was
costed as fixing `delivery_marker_absent`. There is no defect to fix: the
canary's child is unstaffed because the owner's own small-unit policy tells
the judge to decline a 138-character unit, and the judge is obeying it twice
over. Rule 8 is working exactly as written.

The consequence is sharp. **The claude canary cannot produce a Rule 4 Live
proof while its work unit is the 138-char pure unit** — and that unit is the
canary contract's own fixture. Option A therefore is not "fix a bug"; it is
"change what the canary asks for, to a unit the judge will actually staff",
which changes the canary contract and the fixture that §7.1 was designed to
measure. That is a different and larger decision than the one it was costed
as, and it partly collides with AR-125's matched-corpus constraint: a canary
whose unit is chosen because it gets staffed is no longer a neutral probe.

Option B's costs are unchanged, and so is the finding that **neither option
moves codex**.

*Falsification:* if the canary's work unit is configurable without touching
the ADR-0158 contract or the §7.1 fixture, Option A is cheaper than this
paragraph claims and should be re-costed.

#### Addendum: the canary fixture is deliberately not configurable

Testing the falsification above — "if the canary's work unit is configurable
without touching the ADR-0158 contract or the §7.1 fixture, Option A is
cheaper than this paragraph claims" — the answer is **no, and by design.**

`agency_runtime/core/activation_canary_contract.py` holds the unit as a
module constant, `CODEX_ACTIVATION_CANARY_WORK_UNIT`, and three other things
are derived from it rather than declared alongside it:

- `CODEX_ACTIVATION_CANARY_PROMPT` embeds the unit verbatim and is the
  parent's prompt. Run `43a081d6`'s `user_message` is this prompt, so **the
  claude canary uses the codex activation-canary contract** — one fixture
  serves both hosts.
- `_CODEX_ACTIVATION_CANARY_TASK` is built by `re.escape` over that prompt,
  so per the source comment "prompt and codex recognizer move together by
  construction", and `is_exact_codex_activation_canary_task` requires a
  `fullmatch`.
- "The acceptance criterion compares the child's captured assignment to the
  work unit for **exact equality**."

So changing the unit changes the prompt, the codex recognizer regex, and the
acceptance criterion simultaneously, on both hosts. That is intentional
coupling, not incidental.

**The constraint that makes Option A hardest is recorded in the same file.**
The prompt is also planner input, and the comment states that v2's phrase
"any expertise they need" produced "invented capability requirements no card
could cover (`staff_without_safe_team`)", so **"no wording here may name
expertise, skills, or capabilities"**. The obvious way to make a unit
staffable — describing the expertise it needs — is precisely the wording that
already broke this fixture once, and `staff_without_safe_team` is the same
code still appearing on claude's real-profile receipts today.

The file also records that the first captured-assignment run (AR-255,
"Settled 2026-08-17") saw the parent add a "you are acting as…" preamble and
errand children, "which the child judge correctly declined" — the same judge
behaviour observed again today, for the third time.

**Net effect on the seal.** Option A requires editing a constant that is
simultaneously the codex activation recognizer, the cross-host canary prompt,
and the exact-equality acceptance criterion, under a standing prohibition on
naming expertise in it. It is not a bug fix and it is not a small change.
This should be weighed against Option B's schema bump rather than assumed
cheaper than it.

*Falsification:* if a second work-unit constant can be introduced for the
claude child-delivery canary without touching
`is_exact_codex_activation_canary_task` or the codex recognizer, the coupling
is separable per host and Option A narrows to a claude-only change — though
Rule 9 would then want the same treatment justified on codex.

#### Separability tested: the coupling IS separable, and no existing test breaks

The falsification left open above — "if a second work-unit constant can be
introduced for the claude child-delivery canary without touching
`is_exact_codex_activation_canary_task` or the codex recognizer, the coupling
is separable per host and Option A narrows to a claude-only change" — was
tested by tracing every consumer of the fixture. **It is separable.** This
partially reverses the previous addendum's conclusion, which over-costed the
mechanical side.

Full consumer inventory (`grep` over the whole tree, `__pycache__` excluded):

| Consumer | Gate | Affected by a claude-only prompt? |
|---|---|---|
| `canary.py:47` `CANARY_PROMPT = CODEX_ACTIVATION_CANARY_PROMPT` | alias | No — leave the alias alone |
| `canary_proof.py:416` `base_prompt = facade.CANARY_PROMPT if mode == "agency" else …` | **not host-aware** | **the single change point** |
| `canary_proof.py:428` `require_exact_activation_rollout=host == "codex" and mode == "agency"` | already codex-gated | No |
| `pipeline.py:925` (rebind canary goal) | `is_exact_codex_activation_canary_task` → `host == "codex"` | No |
| `pipeline.py:1711` (planning options) | same | No |
| `preflight_recipe.py:589` (work-unit replay) | same, plus a route-source gate | No |
| `store/preflight.py:430` | route-source gate | No |

`is_exact_codex_activation_canary_task` requires `host == "codex"` in its own
body, so all three recognizer call sites are dead on the claude path by
construction, and the exact-rollout requirement is *already* written as a
per-host branch.

**Corroborated empirically, not just by reading.** The claude canary parent
decision `c75f7f6c` recorded `source: "computed"` — **not**
`codex_activation_canary_inference`. The codex activation-canary machinery
demonstrably did not fire on the claude canary run, which is what the source
reading predicts. (This matters: the matrix has been burned three times by
source-read evidence that stopped being true.)

**No existing test breaks**, because the cheapest shape leaves
`CANARY_PROMPT` pointing at the codex constant and adds a separate one:

- `tests/test_activation_canary_contract.py:147` pins
  `canary.CANARY_PROMPT == CODEX_ACTIVATION_CANARY_PROMPT` — unchanged.
- `tests/test_canary_coverage_complete.py:189,196` read `canary.CANARY_PROMPT`
  for policy-trigger and one-unit assertions — unchanged.
- `tests/test_canary_coverage_complete.py:443-467`, the
  `_prepare_live_invocation` contract test, exercises **host `"codex"` only**
  in both mode branches — unchanged by a `host == "claude"` selection.
- `tests/test_codex_activation_canary.py:507-516` prints `CANARY_PROMPT` in a
  codex subprocess — unchanged.

Baseline confirmed green before drawing this conclusion:
`pytest tests/test_activation_canary_contract.py -q` → **21 passed**.

So the mechanical cost of Option A is **one new constant plus one host-aware
line**, with new tests wanted for the new constant rather than existing ones
rewritten.

**What is still expensive, and it is not engineering.** The judge declined
because the owner's small-unit policy told it to, so Option A's real content
is choosing a unit the judge will staff. That choice is fenced on three
sides, and the fences are load-bearing:

1. The prompt is **planner input on claude too**. AR-255's v2 series showed
   that naming what the work needs produced invented capability requirements
   and `staff_without_safe_team` — the same reason code still appearing on
   claude's real-profile receipts today (03:45:55Z, 03:28:59Z, 03:12:10Z,
   02:56:13Z). The obvious way to make a unit staffable is the one wording
   already proven to break it. `test_activation_canary_prompt_never_names_expertise_for_the_planner`
   bans `expertise`, `skill`, `capabilit`, `staff` — and it is written against
   the codex constant, so a new constant would need that guard added
   deliberately or it silently loses the protection.
2. `_explicit_indivisible_unit_request` must keep returning true or the
   planner regains license to decompose the turn into errands — the exact
   failure the 2026-08-17 captured-assignment run recorded.
3. Transport bounds: `MAX_ROUTING_SIGNAL_CHARS` and `MAX_WORK_UNIT_CHARS`.

**And the Rule 9 objection stands.** A claude-only canary unit is a per-host
branch, which the founding vision calls a smell to justify. There is
precedent in this very file (`require_exact_activation_rollout` is codex-only,
`NATIVE_ONLY_CANARY_PROMPT` is a mode variant), so it is justifiable rather
than forbidden — but it has a real cost beyond style: **claude and codex
canaries would stop measuring the same thing**, which breaks the matched
comparison this session used to locate the two hosts' different walls, and
touches AR-125's matched-corpus constraint.

**Net re-costing, third pass.** Option A is cheap to *wire* and expensive to
*specify*. The engineering is a one-line branch; the deliverable is a work
unit that the child judge will staff without naming expertise, without
becoming decomposable, and without making the two hosts incomparable. That is
an owner policy decision about what the canary is allowed to ask for, not a
task that can be closed by writing code.

*Falsification:* if a candidate unit is drafted that the judge staffs while
passing the expertise ban, the indivisible-unit check and the transport
bounds, then Option A is fully costed and cheap, and the seal should be
decided in its favour. If three such drafts are declined in a series, the
small-unit policy and canary-based Rule 4 proof are in genuine tension and
Option B's schema bump becomes the better buy.

### RETRACTION, same session: the §7.1 settlement above does not stand

**Earlier in this session I recorded §7.1 as settled by a repair-confirmed
decline. Measurement now refutes it, and the retraction is mine, before it
reached any matrix cell.** The settlement condition was stated in the capsule
as "a repair-confirmed post-policy decline would settle it; **any staffing
refutes it**." Staffing has now been observed on the identical unit.

#### The instrument, and why it is comparable

A read-only probe reproduces exactly the call `staff_native_child` makes —
`query_judge(task, eligible_catalog, config=snapshot.config,
max_selected=MAX_INFERENCE_TEAM_CARDS, candidate_scope="complete")` — and
never calls `_unstaffed`, `_record_decision`, or
`_record_captured_assignment`, so it writes nothing to the Store.

Building the universe by re-filtering the catalog was **not** trusted:
a first attempt with `capability_status=""` produced 33 eligible agents, not
71, which would have silently measured a different universe. Instead the
judge's own recorded universe was rebuilt from decision `5c963e09`'s
`offered_agent_ids`, and validated against its `offered_agent_digest`:

~~~text
recorded slugs         71
digest recomputed      5733d4e7aa75fb48812f9e7733ba811deec06b12180a50a4272c594f018e0897
digest recorded        5733d4e7aa75fb48812f9e7733ba811deec06b12180a50a4272c594f018e0897   MATCH
missing from snapshot  0
catalog rebuilt        71 agents
~~~

So the universe is provably identical to the one the canary's child judge
saw, not merely similar.

#### The measurement

Four units, serialized, each deterministically pre-screened against the
`expertise`/`skill`/`capabilit`/`staff` ban and `MAX_WORK_UNIT_CHARS`. All
four passed the screen; all four were put to the judge.

| Unit | Chars | Result | Selected | Conf |
|---|---|---|---|---|
| **A — control, the exact 138-char unit** | 138 | **STAFFED** | `minimal-change-engineer` | 0.90 |
| B — same domain, richer | 251 | STAFFED | `code-reviewer` | 0.98 |
| C — security-framed | 234 | STAFFED | `ai-generated-code-security-auditor` | 0.98 |
| D — multi-consequence | 372 | STAFFED | `code-reviewer` | 0.96 |

**The control is the finding.** Unit A is byte-identical to
`CODEX_ACTIVATION_CANARY_WORK_UNIT`, the unit the canary's child judge
declined twice — once first-pass on 2026-08-18, once repair-confirmed today.
Over the digest-identical 71-agent universe it was **staffed**, `status
applied`, `inference_mode inferred`, confidence 0.90.

#### The one thing that differs, and it is the likely cause

The canary's child judge ran on **`claude-subscription`**. This probe ran on
**`codex-subscription (cli:codex)`** — all four draws.

`~/.agency-runtime/agency.yaml` lists `codex-subscription` first in
`providers:` and leaves `judge.model` empty, so an unconstrained judge call
takes the head of the provider list. Inside the canary's restricted isolated
profile the codex transport is not available, so the judge falls through to
`claude-subscription`. That is the mechanism that best fits the evidence.

**So the correct reading is: the decline is not a property of the work unit,
the small-unit policy, or the catalog. It tracks the provider.** The unit is
demonstrably staffable; one provider staffs it and the other declines it.

*Falsification, and this is the next measurement:* force the probe onto
`claude-subscription` and re-run unit A. If it declines there, the abstention
is provider-conditional and confirmed. If it staffs, the difference lies in
the canary's isolated environment rather than the provider identity, and the
prompt/profile must be examined instead.

#### What this does to the seal, third correction

My previous re-costing said Option A was "cheap to wire, expensive to
specify", because the deliverable was thought to be designing a unit the
judge would staff. **That premise is now refuted: the existing unit is
staffable.** If the abstention is provider-conditional, Option A may reduce to
pinning or ordering the child judge's provider inside the canary — no new
unit, no fixture change, no Rule 9 divergence, and none of the
matched-corpus damage. That would make Option A decisively cheaper than
Option B again.

It also raises a question larger than the seal, and it belongs to AR-253
rather than here: **the child judge's provider is selected by config list
order with an empty `judge.model`**, so which model judges a harness-spawned
child depends on provider availability in the ambient environment. Two
environments therefore disagree about whether the same child needs a
specialist. Rule 1 says selection is inference-based; it does not
contemplate the selection changing because a transport was absent.

*Do not promote any cell from this section.* It is a probe, not a host
artifact, and its provider does not match the canary's.

### CONFIRMED: the child judge's decline is provider-conditional

The measurement named as the next bounded work package has been run, and it
returns the first branch. **Same task, same universe, same code — the answer
depends on which provider answers.**

The probe is now a committed script, `scripts/ar119_child_judge_probe.py`, so
this is reproducible rather than reconstructed from prose. It rebuilds the
judge's universe from a recorded decision's `offered_agent_ids`, refuses to
run unless the recomputed `offered_agent_digest` matches, and restricts the
inference chain with `dataclasses.replace(config, providers=(one,))`. It
reports **which provider answered** rather than which one was requested.

#### Instrument validation

Default chain (config order), the byte-identical 138-char control unit:

~~~text
universe 71 agents | digest 5733d4e7aa75... VERIFIED | provider (config order)
run 1: applied / inferred | staffed | ["minimal-change-engineer"] | conf 0.93
       provider codex-subscription (cli:codex)
~~~

That reproduces the earlier finding, so the instrument is sound before the
comparison is drawn.

#### The comparison

Forced onto `claude-subscription`, three serialized runs, failures kept:

| Run | Status | Mode | Staffed | Conf | Provider that answered |
|---|---|---|---|---|---|
| 1 | `inference_unavailable` | unavailable | no | 0.00 | *(none — transport flake)* |
| 2 | `applied` | inferred | **no** | 0.75 | `claude-subscription (cli:claude)` |
| 3 | `applied` | inferred | **no** | 0.75 | `claude-subscription (cli:claude)` |

**0 staffed / 3.** Runs 2 and 3 are genuine applied inferences that returned
an empty selection — deliberate declines, not failures. Run 1 was a transport
flake and is retained rather than dropped.

Against the same unit and the same digest-verified 71-agent universe,
`codex-subscription` staffs (`minimal-change-engineer`, 0.90 and 0.93 across
two draws) and `claude-subscription` declines twice.

**A corroboration worth noting:** both claude-subscription declines report
confidence **0.75**, which is exactly the confidence recorded on the canary's
own child decision `5c963e09`. The probe is reproducing the canary's observed
behaviour, not merely something adjacent to it.

#### What this settles

1. **Blocker 1 is confirmed.** The decline is a property of the provider, not
   of the work unit, the small-unit policy, or the catalog.
2. **The §7.1 retraction stands and is now explained.** The unit was never
   "too small to staff"; one provider staffs it. The earlier settlement read a
   provider difference as a policy result.
3. **Option A is the cheap path, and it is cheaper than even the separability
   analysis suggested.** It needs no new work unit, no new prompt constant, no
   change to `canary_proof.py:416`, no Rule 9 divergence and no
   matched-corpus damage. It reduces to pinning which provider the child judge
   reaches inside the canary. **The seal should be decided for Option A.**

#### The larger question this exposes, which is not AR-119's

`agency.yaml` leaves `judge.model` empty and lists `codex-subscription` first,
so an unconstrained judge call takes the head of the provider list, and the
canary's restricted profile — which has no codex transport — silently falls
through to `claude-subscription`. **Two environments therefore disagree about
whether the same harness-spawned child needs a specialist.**

Rule 1 says selection is inference-based. It does not contemplate the
selection changing because a transport happened to be absent. Whether that is
acceptable is an owner question, and it belongs to AR-253 rather than here,
but it should not be closed silently: today it is the difference between a
child that gets a card and one that does not.

*Falsification:* if a later series on `claude-subscription` staffs this unit,
the decline is not provider-determined but load- or model-version-dependent,
and the seal decision must be re-opened. Two applied declines at identical
confidence make that unlikely but not impossible; the probe makes re-running
it cheap, which is the point of committing it.

*Scope:* this is a probe, not a host artifact. It correlates; it cannot
originate a Rule-4 claim (ADR-0156). **Do not promote any matrix cell from
it.**

### OWNER DECISION: Option A is per harness and canary-only

The owner chose Option A on 2026-08-19 and refined it to one persistent pin
for each harness, so switching harnesses does not require reordering the global
provider chain. ADR-0160 owns the mechanism:

- `canary.child_judge_provider_by_host.<host>` names one configured CLI
  provider;
- both the initial child-judge call and its one abstention repair see only
  that provider, with no fallback;
- the disposable environment must project the same requested identity or the
  call fails before inference;
- requested and actual answering providers remain separate evidence; and
- outside canary mode, child staffing is byte-for-byte on the original
  provider-chain path.

The map is host-neutral, not a brand-pairing rule. For the measured control,
`claude -> claude-subscription` is expected to decline and is the explicit
falsification path; `claude -> codex-subscription` is the current
evidence-backed passing choice. The owner profile has not been changed, so no
installed choice is claimed here.

The owner also identified the intended `zcode -> GLM subscription` pairing.
The local candidate can now resolve the existing `zcode-recruiter`
Anthropic-compatible inference profile and narrow it into the canary's sole
provider without changing the ordinary chain. Historical ZCode Store receipts
show successful GLM-5.2 profile calls, but they predate this candidate. ZCode
still lacks a safe noninteractive canary backend, so neither the profile nor
those receipts are installed/live proof.

Local source now implements the typed map, exact provider resolution,
environment/config equality check, one-provider narrowing, cross-provider
credential isolation, and requested/answered proof projection. Focused tests
cover initial and repair calls, mismatch-before-inference, ordinary-turn
noninterference, typed config updates, and Claude-to-Codex auth isolation.
All 14 local gate contracts then passed across the attached run and exact
reruns: the production spine passed 794 tests with 20 skips, the AR-119 matrix
evidence suite passed 670, and the dashboard passed 134 with its coverage
thresholds. The alignment preserved the exact mutation-snippet guard and made
the setup-failure fixture's deadline robust under full-suite load. No live
canary was run, no owner config or install was changed, and **no matrix cell
moved**.

### OWNER CLARIFICATION: Codex parent works; the blocker is child proof

The owner confirmed the scope after observing another live request-scoped
Codex parent turn. That turn carried `host=codex`, Agency preflight inference,
the loaded specialist capsule, and the required Agency response header. This is
direct current-turn evidence that the Codex **parent** integration routes and
delivers Agency context.

It does not falsify the canary result. The three serialized canaries concern a
different boundary: Codex starts its native child, but Agency cannot read the
opaque collaboration record required to prove the child's delivered cards.
The accurate status is therefore:

- Codex parent routing/header delivery: operational in the observed live turn;
- Codex native child creation: observed;
- Codex native-child card delivery: not host-proven;
- Codex Rule 4 Installed/Live and Rule 9: still open.

Never shorten that to “Codex does not work.” Equally, never promote a matrix
cell from the visible parent header alone; the matrix still requires its named
authority at the exact candidate.

### OWNER PHASE: three hosts now, two deferred without waiver

The owner set this development phase to Claude, Codex, and ZCode, then plans to
move development to the OpenClaw box for live OpenClaw work. Hermes and OpenClaw
are exempt from this session's Option-A milestone only. They remain required by
the founding five-host Rule-9 contract.

The bounded Option-A milestone is complete only when:

1. Claude uses the measured passing `codex-subscription` pin and produces the
   approved fresh host artifact;
2. Codex retains working parent routing and exact pin/no-fallback contracts,
   with native-child proof explicitly waiting on the upstream host capability;
3. ZCode has an executable, isolated GLM judge path that records which provider
   actually answered and cannot change ordinary staffing. On the current
   hook-only integration this is an attended installed Agent-tool call, not a
   synthetic noninteractive backend.

ZCode is the remaining host-proof gap. The installed Agency profile's ordinary
provider chain has only `codex-subscription` and `claude-subscription`, but its
inference profile registry already has bounded ZCode/GLM profiles. The local
candidate resolves `zcode-recruiter` only inside the canary and leaves the
ordinary chain byte-for-byte unchanged. ZCode still has no safe noninteractive
native canary backend. Source tests now prove that its documented Agent
`PreToolUse` event reaches native-child staffing and that profile-only pins need
no CLI credential projection. Because the installed host has no launchable CLI
here and no child lifecycle events, the next proof is an attended installed
ZCode call. A direct hook simulation cannot satisfy host proof.

The complete execution sequence is recorded in the canonical AR-119 issue under
“Owner-scoped completion sequence — 2026-08-19.” No matrix cell moved here.

### LIVE CHECKPOINT: Option A delivered; proof correlation needed one repair

The approved local package installed the pushed candidate into Claude, Codex
and ZCode. All three manifests resolve launcher runtime
`59580436f7f10de09ab2e100994f2c785f0bce418419bcea1a7d331e1f890a2c`;
status reports current launchers and no runtime drift. The persisted canary map
reads exactly `claude -> codex-subscription`, `codex -> codex-subscription`, and
`zcode -> zcode-recruiter`. The failed whole-map CLI write changed nothing;
three supported host-key writes then succeeded. Ordinary staffing was not
changed.

The first fresh Claude attempt was not a child-judge measurement. Its ordinary
parent recruiter returned two invalid oversized teams, so preflight stopped
before a child existed. The report correctly recorded requested
`codex-subscription`, zero routing receipts for the child, and no delivery.

The bounded second attempt reached the target boundary:

- parent trace `940bbcb0-d1c1-4d0f-a271-b52e7fa62bf9` selected and loaded
  `code-reviewer`, completed with a valid five-field header and spawned exactly
  one child;
- native decision `native-child-7624e16e5d24ff8be84ab066af5a6e5a` applied
  `minimal-change-engineer` at confidence 0.91 in 9,269 ms;
- the route's requested provider and sole applied answering provider are both
  `codex-subscription`;
- the Claude-written pre-speech artifact matches that exact card, decision,
  provider-receipt digest, launch binding, install, and candidate digest; and
- the atomic consumer created the Store's first immutable
  `native_child_delivery_verifications` row.

The report nevertheless returned red because the pre-Option-A Claude validator
compared the child-selected `minimal-change-engineer` card against the distinct
parent `code-reviewer` route. It also preferred the artifact projection when
looking for provider attempts, although those attempts live on the exact Store
native-child route. The artifact and route themselves agree; this was a proof
projection defect, not a staffing or provider failure.

Commit `14de2f74` now joins the collector-sealed Claude artifact to its exact
Store native-child route, validates their ordered cards and immutable bindings,
keeps the parent route check separate, rejects a requested/answering provider
mismatch, and reports the answering provider from the route. Its regression
deliberately uses a `code-reviewer` parent and a `minimal-change-engineer` child.
Focused and widened local checks pass: **134 passed**, plus Ruff check and
format check. The source fix is newer than the installed launcher, so the next
live action is reinstalling this checkpoint and collecting one attested Claude
run. ZCode still needs its attended installed Agent `PreToolUse` attribution;
Codex child proof still waits upstream. **No matrix cell moved.**

### LIVE CHECKPOINT: repaired runtime installed; refresh stopped before child

Claude, Codex, and ZCode now resolve the same repaired launcher runtime,
`51b3202a2acb3301b3278b5e19d23027441f0b193f9a86d431a76a609fde6bcf`.
Their fresh install manifests and launcher receipts agree. The persisted map
still reads `claude -> codex-subscription`, `codex -> codex-subscription`, and
`zcode -> zcode-recruiter`; the ordinary provider chain remains Codex then
Claude, and content capture remains enabled.

Claude readiness passed with the new install current, registered, enabled, and
free of stale prerequisites. The two approved live attempts after reinstall did
not reach the child-judge boundary:

- trace `c775ba30-ea66-41d5-9912-26094bdcb32f`, receipt
  `3832e7aa-7095-47a3-8ebc-52bf2adea0e9`, stopped at parent routing after two
  `claude-sonnet` recruiter responses proposed unsafe oversized teams
  (`staff_without_safe_team`);
- trace `34b7b35e-af0c-418f-ae99-8021b7ba3b0f`, receipt
  `c7ae4580-83d4-495e-bf28-91e3bf070b32`, stopped earlier when the
  `claude-haiku` parent planner produced no valid response
  (`provider_no_valid_response`).

Both reports named requested child pin `codex-subscription`, but neither
created a child route, called a child judge, produced a delivery marker, or
persisted an attestation. They are parent-preflight outcomes, not provider-pin
measurements. This package stops the Claude retry series here. The earlier
verified Claude artifact and immutable decision `native-child-7624e16e…` still
prove requested and answering `codex-subscription` on the pre-repair runtime;
the repaired digest does not yet have a green end-to-end attestation.

The installed ZCode 3.6.5 desktop executable and its real seven-event hook
registration are available. Before the attended call the Store has zero ZCode
`native_child_inference` rows, giving an exact attribution baseline. The next
live action is one fresh ZCode Agent call launched with canary mode, the
persistent `zcode-recruiter` identity, and the managed install home projected;
a direct hook simulation remains invalid. Codex parent evidence and its opaque
child boundary are unchanged. **No matrix cell moved.**

### ATTENDED ZCODE CHECKPOINT: GLM pin attributed; prompt hydration remains open

The approved installed call ran after ZCode updated from 3.6.5 to 3.8.1. It
submitted the exact 138-character activation unit through ZCode Agent and
created exactly one native child, `agent_526b8a7a-4732-455c-8e93-c0cec510e418`.
The child returned a substantive review of the silent whitespace-contract
change and the parent reported `code-reviewer` recruitment. The visible answer
does not itself prove that the specialist prompt reached the child.

The durable attribution is the Store and installed hook sequence:

- parent run `ada04710-19a2-4938-a2ae-e7ff10b9bdc2`, trace
  `8cd9de8d-7a81-490f-aca5-34b36b7d8727`, session
  `sess_fe90fa0f-97eb-407a-9e37-399e97ddf87f`;
- parent route `c65ee011-7389-4798-85b4-4558619fbaf4` selected
  `code-reviewer` at confidence 1.0;
- native-child route `625e688c-b13c-4330-a569-224f2cbadcf0` recorded both
  requested and actual provider as `zcode-recruiter`, confidence 0.85, for task
  hash `05d45f7553e81e8536e5d43fd07da8b18b195c6ffc0a35ff7e43c2f202861eee`;
- installed hooks traversed SessionStart, UserPromptSubmit, PreToolUse,
  PostToolUse and Stop; delegation `5e746a59-d5ad-4f84-81a4-491ea580b0a1`
  completed with native run
  `zcode-agent:agent_526b8a7a-4732-455c-8e93-c0cec510e418`.

This is actual-provider evidence, not an inference from the configured label.
The failure projection says `native_child_prompt_hydration_failed`, but that
branch is reachable only after the judge result is applied/inferred, exactly
one applied provider attempt has a canonical receipt, and the selected IDs and
compatibility checks pass. Provider identity is projected from the answering
result separately from `requested_provider`. The canary-only resolver exposed
only `zcode-recruiter`; the persisted ordinary chain remained Codex then Claude
and content capture remained enabled.

The failure occurred after GLM answered: `_hydrate_team` could not recover the
selected specialist prompt, the failure projection intentionally cleared its
selected IDs, no captured assignment was written, and Agency failed open to a
generic ZCode child. AR-135 already owns that prompt-consumption gap. Therefore
this call closes Option A's ZCode provider-pin/attribution requirement but does
not prove ZCode Rule 4, host-delivered cards, or specialist execution.

With Claude's exact requested/answering `codex-subscription` route, Codex's
operational parent plus explicit opaque-child exception, and this attended
ZCode/GLM route, **Option A is complete locally from the owner-defined
three-host provider-pinning perspective**. The repaired Claude runtime still
lacks a fresh green end-to-end attestation; Codex child proof remains upstream-
blocked; OpenClaw and Hermes remain deferred, not waived. No Rule-9 claim and
**no matrix cell moved**.

### SOURCE CHECKPOINT: ZCode hydration root cause repaired locally

The attended failure was not a missing prompt, inactive worker, changed roster,
oversized card, or bad content. A read-only reconstruction of its exact ZCode
capability boundary reproduced 72 eligible cards. Twenty-eight active cards,
including `code-reviewer`, store their valid prompt identity as
`sha256:<64 hex>`; the other 44 use the bare digest. `_hydrate_team` supported
only the latter because it compared `content_digest_identity(hash)` back to the
stored string before reading the prompt.

The local fix keeps both identities in their proper authority domains: the
exact prefixed or bare Store identity is used for versioned lookup and body
verification, while the v6 delivery card receives the canonical bare digest
required by the decision and host-proof schemas. A regression proves the exact
prefixed key reaches Store and the parsed/persisted delivery remains canonical.
The same read-only live catalog now hydrates 72/72 with 28 canonicalizations and
zero failures; no judge or other provider was called.

Core native-child staffing, envelope, and decision tests pass **117/117**.
Wider native-hook and proof consumers pass **162**; three unrelated ledger tests
still assert schema 46 although this branch's committed Store is schema 47.
Ruff check and format pass on the two changed files. The repair is source-only
at this checkpoint: the installed runtime remains `51b3202a2acb…`, no attended
recheck has run, no specialist-delivery claim follows, and **no matrix cell
moved**.

### CONFIRMED: repaired ZCode hydration reaches the host-written child

Clean ledger head `c165a51e` passed all 12 fast local gates in 1.3 minutes
before installation. ZCode alone was then reinstalled from that checkpoint:
runtime `f24664b87f3b0fe6a2490ef7dfbf8685c5d0d8a5e27b191902063bd43b41189f`,
bundle `da04cfbf784755ccf122fea07638951c76669f3ce376f50fbf2fbba01896e61a`,
install `759efa16-bdce-4fcb-ab3c-b3b3c0bcf3d8`. Claude and Codex remain on
`51b3202a2acb…`; ordinary provider order remains unchanged.

The first attended message after restart contained only the 138-character
unit, so it was a parent-only control, not a native-child measurement. Parent
route `92c5a7e5…` loaded `code-reviewer`, recorded `delegate=false`, and created
no child route. It is excluded rather than silently counted. The corrected,
pinned 755-character parent prompt then created exactly one ZCode Agent child:

- parent trace `5edde147-a618-4035-abc0-c49ec581a90d`, session
  `sess_aded0d1d-5a89-447d-a158-3012f2c87062`, parent route `06fae2da…`;
- native-child decision `native-child-aa6e5296b9e34d3238b9e408dcb61904`,
  applied/inferred, confidence 0.85, exact 72-candidate boundary;
- requested and answering child provider `zcode-recruiter`, provider type
  `anthropic`, requested model `GLM-5.2`; the parent router separately used
  `claude-subscription`, demonstrating that the pinned variable was the child
  judge rather than the host or parent transport;
- selected card `python-application-engineer`, version
  `contractor-1-sha256:27736661e`, canonical prompt digest `27736661ee05…`;
- launch/binding `call_1f2255f916544728a79ea34b`, child
  `agent_07b6377b-a2bc-454f-a334-bf60ec5664d5`, exit code 0.

ZCode itself wrote the decisive artifact under
`~/.zcode/cli/agents/sess_aded0d1d-…/agent_07b6377b-…/`. `metadata.json`
binds the parent session and tool-use ID to the child. Transcript record zero
is `turn_started`, sequence zero, and its input already contains the complete
`[AGENCY INFERENCE TEAM v6]` envelope before child speech. The same envelope is
present in the child model-I/O rollout. Its 2,928-character card body is
byte-identical to the immutable Store version whose key is
`sha256:27736661…`; v6 correctly carries the canonical bare digest. The exact
original task and hash, all decision fields, card projection, record-zero
ordering, parent/child binding, Store body, and issue/expiry window pass 14/14
mechanical checks. Artifact hashes are metadata `f9a95f7ca518…` and transcript
`630e494cba39…`.

PostToolUse records `generic-worker` because that field is the native ZCode
lifecycle identity; it does not claim which Agency card was delivered. The
visible header therefore says `delegated: none`, while the host-written record
zero independently proves the selected card reached the child. No ZCode row
was added to `native_child_delivery_verifications`, and the child workspace was
the primary checkout rather than the linked worktree; its four existing dirty
paths all predate this run and the read-only review changed none of them. Those
limits remain explicit.

The prefixed-hash defect is therefore repaired in source, installed, and live
on ZCode. Together with Claude's attributed pin and Codex's operational parent
plus explicit upstream child-proof exception, **Option A is complete from the
owner-scoped Claude/Codex/ZCode perspective**. This does not re-promote R1, R4,
R5, or R6, formalize R8, complete AR-252, close Rule 9, or move any matrix cell.
OpenClaw and Hermes remain deferred for this session.

### MAIN CHECKPOINT: PR #298 merged and exact-main runtime installed

PR #298 merged the verified Option A rollup to `main` as `ae1964fa` from exact
head `2f6ed88d`. The complete local harness passed 14/14 in 14.7 minutes: 161
workflow-contract tests, 151 mutation snippets, 796 production-spine passes
(20 skipped), 670 AR-119 evidence tests, and 134 dashboard tests. The pre-push
hook independently passed 12/12. Both head and merge commits carried GitHub's
skip instruction; GitHub created no hosted Actions run for either SHA.

A clean main-equal checkout then installed all three owner-scoped hosts with
dashboard installation opted out. Every manifest points to the same launcher
runtime `12ce2b614e359e1c97a574b31cfdc189c09e7276cf51ef6c9a341112645bcf3a`:

- Claude install `79053bdd-3cbf-47cb-996e-a33ba82a2b58`, bundle `d701a815…`;
- Codex install `aa095210-8721-4a5b-825d-75a4e6f71012`, bundle `2ad1a6b3…`,
  registered with the expected fresh-session activation requirement;
- ZCode install `f82ad76f-0d45-4ff5-8c30-51b7e6a7ed76`, bundle `f812867c…`,
  seven owned handlers registered with global hooks still enabled.

The deterministic `agency_runtime.cli smoke` contract passed 4/4 separately
for Claude, Codex, and ZCode: private schema-47 Store, 263-card starter roster,
5/5 host parity, and the host-specific generated plugin/hook contract. These
are install checks, not provider calls or live-host proof. Fresh parent CLI
smokes and the separately authorized Codex child canary remain next. The
primary checkout's four named owner-WIP paths were not touched. No rule was
promoted, no candidate advanced, and **no matrix cell moved**.

### LIVE MAIN: Claude parent header smoke passes

The first fresh Claude CLI prompt required only `PARENT_SMOKE_OK`, conflicting
with the installed header contract. Session `aaeea445-35f7-4041-a09f-fc27381ef4e1`
shows Agency injected the current capsule and exact header snapshot, then the
Stop hook rejected the headerless body as `AGENCY RESPONSE INVALID`. That
prompt-invalid attempt is excluded rather than counted as an activation result.

The single corrected prompt explicitly permitted the header. Fresh session
`831eed9e-4367-4380-ada6-0db5fe4be0d7` completed in one turn with no tools or
delegation and returned the exact five-line Agency header followed only by
`PARENT_SMOKE_OK`. It recorded `agency-steward` plus
`agency-governance-request-clarifier`, `delegated: none`, and workforce inference
`claude-sonnet/sonnet`; the host call itself reported `claude-opus-5`. This is
installed-main parent/header proof only. It moves no rule or matrix cell.

### LIVE MAIN: Codex trust bypass runs; generic smoke abstains

Fresh Codex CLI thread `01a01c51-f856-71c2-804e-54ed64a2bd82`, trace
`01a01c51-ffb6-7a33-a0bd-22c21b0418f9`, ran with
`--dangerously-bypass-hook-trust`, read-only sandboxing, and tool/child paths
disabled. Host inventory shows merged-main plugin
`0.1.0+codex.5d5f0eb77307` enabled. The rollout contains the installed resident
kernel before the model response, proving the invocation-only trust bypass ran
the hook rather than merely trusting registration state.

Planner and recruiter both applied through `codex-fast/gpt-5.6-terra`, then
staffing declined with `substantive_specialist_unavailable`,
`no_safe_sufficient_team`, and `recruiter_abstained`. With no loaded capsule,
there was no Agency header snapshot; Codex failed open and returned only
`PARENT_SMOKE_OK`, with no tools or child. This is a valid abstention and hook
execution result, not parent-header proof. The staffable review control remains
the next header test. No rule or matrix cell moved.

### LIVE MAIN: Codex staffable parent header passes

Fresh Codex CLI thread `01a01c57-6d65-7951-8cf3-bcde70cbd6d2` used the same
invocation-only hook-trust bypass with every tool and child path disabled. The
staffable text-normalization review control returned the exact five-line Agency
header, loaded `agency-steward`, `codebase-onboarding-engineer`, and
`code-reviewer`, delegated none, and reported workforce inference
`codex-fast/gpt-5.6-terra`. Its one-sentence body correctly named silent loss of
significant boundary whitespace. This proves merged-main Codex parent routing
and header delivery; it does not prove child delivery or move a matrix cell.

### LIVE MAIN: Codex child rerun stops before child start

The one approved merged-main child canary ran with the invocation-only hook
trust bypass and exact 420-second command. The wrapper exited 1 because the
proof failed, while the bounded Codex host invocation itself exited 0 without
timeout or truncation. `trust_bypass_used` is true and the installed bundle is
the expected `2ad1a6b34b64…` from install
`aa095210-8721-4a5b-825d-75a4e6f71012`.

Store correlation is session `01a01c5a-9f31-7653-8bf2-a59cbfdff700`, trace
`01a01c5a-9f79-7951-a501-63e3aa1466fb`, run
`81893528-8763-433c-9347-8e2c016d5815`, and request/query hash
`74ea67295095b38973dda887023fb125534c0c75045df25f85382e41fc233f64`;
the exact nonce is `77c5b76ad57caf8fb3ceb472bbcd7a8b`.
The run closed `preflight_failed`; failure
`310f2925-f009-4511-a96c-12bbdb55a929` records
`workforce_inference_failed`. Parent planner and recruiter both answered through
`codex-fast/gpt-5.6-terra` with `structured_response_applied`, but no route,
specialist load, delegation, native-child route, delivery, worker run, or
finalization was created.

The invocation explicitly reports requested child-judge provider
`codex-subscription`; it does **not** report an answering child provider because
the child judge was never reached. The collaboration diagnostic observed one
spawn, one wait, two tool outputs, zero child starts, and no unexpected tools.
Its terminal reason is `native_child_start_missing`, projected as
`codex_native_child_start_missing`; the header and response were consequently
unproven. This differs from the older three-run 1-spawn/1-start opaque-
projection series. It is a bounded exact-main parent-preflight outcome, not a
pin falsification, Codex Rule-4 proof, or install failure. No rule was promoted,
the candidate did not advance, and **no matrix cell moved**.

### LIVE MAIN: ZCode exposes a first-response header-delivery defect

Fresh ZCode session `sess_88f7185c-16d2-4dec-873f-8843629bd5e0`, Agency trace
`ca770802-6bff-417a-b13e-5e0765efa76f`, ran the staffable text-normalization
control without tools or delegation. The ZCode parent answered through its
configured `builtin:zai-coding-plan/GLM-5.3` host model and produced the correct
one-sentence regression assessment. Agency's separate workforce planner and
recruiter both answered through `claude-subscription/sonnet`; the distinction
between host model and Agency inference transport is observed rather than
inferred.

The Stop hook correctly rejected that first response and committed terminal
finalization `8bb6ea7c-c6a5-4ae5-a71a-569d4af3a2f8` at evidence revision 10.
The submitted header named only `code-reviewer` and reported `none observed`;
the authoritative turn required `agency-steward, code-reviewer` and the
Claude/Sonnet workforce-inference receipt. Its persisted missing list is exactly
`agencies_loaded, actual_model_selected`; the other three evidence fields and
the response body were valid.

Host I/O proves why a blind retry would be invalid: ZCode received the resident
manager once and a placeholder-only header template, but received zero
occurrences of `claude-subscription` or the exact model line enforced at Stop.
The shared Store-backed snapshot helper admitted only Claude and Codex. A local
candidate now admits ZCode on that same initial and updated parent-header path,
with no child-lifecycle change. The widened hook/parity suite passes 144 tests;
the final focused initial-header, updated-header, and ZCode child-lifecycle set
passes 7 tests; focused Ruff and diff checks pass. The governing local fast
harness passes all 12 gates in 1.3 minutes. This candidate is not yet merged,
installed, or live-proven. No rule was promoted, the candidate did not advance,
and **no matrix cell moved**.

### LIVE MAIN: repaired ZCode parent header passes through the bundled CLI

PR #299 merged exact head `cfdaacb6` to main as `f203dc66`; both commits carry
the GitHub skip instruction and no hosted Actions run was created. The pre-push
hook passed 12/12 local gates. ZCode alone was reinstalled from a clean detached
checkout of that exact merge: install `c28d34aa-8ded-4740-90f1-b22b0af191db`,
bundle `749a449cc6d6…`. Its deterministic source smoke passed 4/4.

The desktop package does contain a headless runtime even though it installs no
`zcode` command: `resources/glm/zcode.cjs`, version 0.16.3. Fresh one-shot
session `sess_d4ac6d99-a8e6-4f43-ab81-c19902f23d86` ran the staffable
text-normalization control with every model tool denied. ZCode model-I/O binds
request `c59e7205-9138-4203-a1ab-3378e20316fb` to provider `zai`, requested
model `glm-5.2`, and the provider's actual response model `glm-5.3`; it records
one request, `finishReason=stop`, and zero tool calls. The host trace is
`d3f6efd5-9e14-4e34-81c6-bb2fae78d9d9`.

Agency independently correlated that session to trace
`498d64b3-8643-4c38-8c0f-922e3837cf8d`. Its separate workforce inference
answered through `claude-subscription/sonnet`, loaded `agency-steward` and
`code-reviewer`, and delegated none. The response began with the exact five
authoritative fields, then a correct boundary-whitespace risk. Stop committed
authoritative finalization `65038045-64e3-41f2-88e5-32b0ce476b3e` as
`accept/completed`; `missing` is null, and there are zero delegation or
specialist-activation rows. Extra retired `Why`/`How` prose remains a bounded
producer-prompt follow-up, not a header mismatch.

This closes the merged/installed/live ZCode parent-header repair and completes
the owner-authorized rollout package. It is parent proof, not a new child draw,
Rule-4 promotion, candidate advance, or matrix change. Option A remains complete
for the owner-scoped Claude/Codex/ZCode phase; OpenClaw and Hermes remain
deferred, not waived.

### CODEX 0.148 FALSIFICATION DRAW: parent preflight stops before spawn

One owner-authorized Codex child canary ran from clean detached `f203dc66`,
whose code is byte-equivalent to current main `b908b747`; the intervening PR
#300 commits are documentation-only. Readiness proved Codex CLI 0.148.0,
install `aa095210-8721-4a5b-825d-75a4e6f71012`, bundle `2ad1a6b34b64…`,
enabled master/runtime controls, current launcher artifacts, and zero unmet
prerequisites. The exact 420-second invocation used the invocation-only trust
bypass. The wrapper exited 1 because proof failed; the bounded Codex process
exited 0 without timeout or output truncation.

Store correlation is session `01a02050-07c6-73e0-ba0c-c66c571b4edf`, trace
`01a02050-0812-7921-afce-37abef8fbfa5`, run
`8a57c558-f612-458d-a6d5-eb0cfe722735`, and request/query hash
`fe412425e693df0b60f1f7d5e03750b465d7dd2e98f78ad47fcf1af4405e933d`.
Failure `8ec959bb-700e-41c1-9346-91f1722e74d4` closed the run
`preflight_failed` / `workforce_inference_failed`. Parent planner and recruiter
both answered through `codex-fast/gpt-5.6-terra` with
`structured_response_applied`, but no route, specialist load, delegation,
native-child route, delivery, worker run, or finalization was created.

The invocation requested child-judge provider `codex-subscription`; no child
judge answered because native collaboration was never reached. Its content-free
diagnostic observed seven parent agent messages and zero spawns, child starts,
waits, tool outputs, interactions, follow-ups, or unexpected items, yielding
`parent_spawn_missing` / `codex_parent_spawn_missing`. This run therefore does
not test, prove, or falsify Codex 0.148's conditional plaintext collaboration
path. It does not supersede the older 0.147 1/1 opaque-projection series or the
prior exact-main 1/0 run. Do not repeat it without a new upstream surface or a
deterministic parent-preflight repair target. No rule was promoted, the
candidate did not advance, and **no matrix cell moved**.

### CLAUDE ACCEPTED-OUTCOME DRAW: parent planner contract invalid

PR #301 merged the eight-commit AR-119/AR-252 outcome package to exact main
`5a1d863c` on 2026-08-20. Both the PR head and merge commit carried
`[skip ci]`; GitHub reported the PR cleanly mergeable and created no hosted
run. The push hook passed all 12 local gates in 0.9 minutes. The earlier exact
code candidate retained its 14/14 complete harness, 151/151 mutation, and 46/46
focused evidence.

Claude was then installed from a clean detached checkout at that merge. Install
`3c0f9bb6-ca93-444b-a965-c10706e67b67` staged bundle
`7a526cd548a92d207e17f6df270aab2a8bde1ffbd9eaef7b03bd5989d39c6ba2`,
retained backup `20260820T182048.584843Z`, and finished registered, enabled,
and non-partial. Readiness on Claude Code 2.1.226 was green with zero unmet
prerequisites. The owner-authorized isolated command used the exact
`RUN LIVE claude ACCEPTED-OUTCOME CANARY` confirmation and 420-second bound.
The host process exited 0 without timeout or truncation; the proof wrapper
exited 1.

Pair `5a1be926bf1b0d1e86148b382f474f8d` failed closed at
`delivery_marker_absent`. It requested the evidence-backed Claude canary pin
`codex-subscription` and targeted contractor
`typescript-application-engineer` / worker
`54cb1db1-7c55-5d13-9fff-ddb1bd5ca921`, but never reached the child judge.
Store session `c6a4a7ea-ce8c-4ec8-8a7c-4be9ecb3bd25`, trace
`2d918a99-32c0-40bd-a9e9-f53dea2834df`, run
`6312eeae-5532-4eba-90b1-f2eb23bb379c`, and failure
`61ec6d6d-74d9-4de7-86f0-288606c7b9dc` prove the earlier boundary:
`preflight_failed` / `workforce_inference_failed`. Two serialized planner
attempts through `claude-haiku` / requested and actual `haiku` were rejected as
`provider_response_contract_invalid`; there is no applied model receipt,
routing decision, worker run, or delivery verification in that window.

The host wrote exactly two candidate child artifacts, so the collector reached
the two-artifact gate, but their first authoritative v6 read carried no delivery
marker because Agency preflight had staffed neither child. No accepted outcome,
attestation, or promotion was written. This is a deterministic isolated-parent
preflight target, not evidence against the child-judge pin or Claude's native
child surface. Do not repeat the live draw until that contract failure is
reproduced and repaired locally. No rule was promoted, the candidate did not
advance, and **no matrix cell moved**.

### LOCAL REPAIR CANDIDATE: accepted-outcome parent work is indivisible

The exact merged-main canary prompt was 2,316 characters and returned false
from the existing `_explicit_indivisible_unit_request` detector. It therefore
did not give the parent planner the repository's durable one-work-unit signal
before asking Claude for two serial children. The local canary-only candidate
now says that the accepted-outcome canary is exactly one indivisible work unit
and must not be split or decomposed. Its 2,367-character prompt returns true
from the same production detector. No provider, model profile, ordinary-turn
behavior, Store contract, or global configuration changed.

The exact prompt contract passes 11/11 focused tests; the widened canary,
collector, activation-contract, and workforce-inference surface passes 102/102.
Ruff lint and format checks pass, and the local fast harness passes all 12
gates in 1.3 minutes, including 161 workflow contracts, 151 mutation snippets,
and 134 dashboard tests. This is a local repair candidate, not proof that a
fresh Claude invocation will staff. No provider was called, no outcome or
promotion was written, the candidate did not advance, and **no matrix cell
moved**.

### MAIN CHECKPOINT: indivisible-parent repair merged and installed

PR #302 published exact repair head `c798562f` and merged it to main as
`a102a932a64d43a8cb0c4b914823bcf1755ad85b`. The non-draft PR was
CLEAN/MERGEABLE with an empty check rollup. Both head and merge subjects carried
`[skip ci]`; GitHub created no hosted run. The exact head passed the 12-gate
fast harness in 1.3 minutes before push and the pre-push hook independently
passed all 12 in 0.9 minutes.

A clean detached checkout moved from prior main `5a1d863c` to exact merged
main and installed Claude only. Install
`4c6d8a17-902e-4de6-8b8a-15de14276eca` staged bundle
`b0b5073ca7cbe4dc5ad7dbdaabb6d9a2af9f5168d9987262027ff21a650d9721`,
retained backup `20260820T192318.474752Z`, and finished registered, enabled,
and non-partial. Readiness on Claude Code 2.1.226 is true with zero unmet
prerequisites, current launcher artifacts, and configured Claude child pin
`codex-subscription`.

No live command or provider call had run at this checkpoint. The one authorized
420-second accepted-outcome draw is next. No outcome, attestation, promotion,
candidate advance, or matrix move follows from publication, installation, or
readiness alone.

### SECOND CLAUDE ACCEPTED-OUTCOME DRAW: planner fixed, recruiter unsafe

The one authorized exact-main draw ran pair
`6e0eff1149894c830127417a1411f06d` with the required confirmation and
420-second bound. Claude exited 0 without timeout or output truncation; the
proof wrapper exited 1 at `delivery_marker_absent`. It requested child pin
`codex-subscription`, targeted `typescript-application-engineer` /
`54cb1db1-7c55-5d13-9fff-ddb1bd5ca921`, and wrote no attestation,
accepted outcome, or promotion.

The Store locates the exact boundary at session
`7c19bc88-37bc-4fec-b26d-6cadc67532a9`, trace
`055d329f-2b78-4f6c-88d8-17f721a0ebf5`, run
`2dbc72dd-e080-4241-88f8-e65e508b4931`, and failure
`88840ca1-c17c-4c83-9fa8-377b9b3fcc39`. The run closed
`preflight_failed` / `workforce_inference_failed`. Unlike the first draw,
the `claude-haiku` planner returned `structured_response_applied` for one
unit. The configured `claude-sonnet` recruiter then returned
`provider_response_contract_invalid`: its `unit-parseport-impl` staff
decision could not form a safe capability team from the four ranked candidates
`typescript-application-engineer`, `minimal-change-engineer`,
`developer-tooling-engineer`, and `backend-service-engineer`. The funded
repair attempt ended `provider_no_valid_response`.

There are zero routing decisions, applied model-receipt rows, specialist loads,
delegation events, child scopes, captured assignments, worker runs, delivery
verifications, finalizations, attestations, skills, or worker-outcome events on
that trace. The collector's `delivery_marker_absent` result occurs only after
its exact-two in-window artifact gate; therefore Claude created the requested
pair, but the first artifact lacked an Agency v6 delivery marker because
preflight never staffed. No child judge answered.

This falsifies the old planner-blocker hypothesis and live-proves the local
indivisible-work repair at its intended boundary. The remaining blocker is the
same intermittent Claude/Sonnet recruiter structured-response behavior already
documented in the instrument series, not the child pin, host Agent topology, or
Store outcome recorder. The one draw is consumed and was not retried. No rule
was promoted, the candidate did not advance, and **no matrix cell moved**.

### LOCAL CANDIDATE: accepted-outcome parent recruiter is pinned separately

The owner chose the narrow branch on 2026-08-20: keep the Claude parent host,
keep its existing Haiku planner route, and constrain only the accepted-outcome
parent recruiter's initial call and funded repair to `codex-subscription`.
This is a new role-specific pin, not a reuse or widening of Option A's child
judge authority.

The local candidate adds
`canary.accepted_outcome_parent_recruiter_provider_by_host.<host>`. Production
preparation resolves that pin exactly once, the disposable accepted-outcome
backend projects its own provider identity and bounded CLI credentials, and
workforce routing consumes it only for `stage=recruiter` with route key
`workforce.recruiter`. A missing, ambiguous, unsupported, or mismatched pin
fails closed without falling back. The parent planner, ordinary Claude turns,
ordinary activation canaries, and independently configured child judge remain
on their existing paths.

This is local source and test evidence only. The owner config still has no
parent-recruiter entry, no install or provider call followed, and the consumed
draw was not repeated. Therefore no accepted outcome, promotion, rule, candidate,
or matrix state moves at this checkpoint.

Local verification is green: the bounded configuration/canary set passed
137 tests with 4 skips and the unrelated historical fast-default assertion
deselected; host-canary/workforce routing passed 152; child/activation/hook
noninterference passed 182; the warning-strict production spine passed 797
with 20 skips; and all 12 fast local gates passed in 1.2 minutes. Documentation
validation covers 713 files. The slow 14-gate harness, hosted CI, installation,
and live inference were not run.

### CHECKPOINT PLAN: finish the 19 August review scope

1. **Freeze Option A.** Preserve per-harness child-judge pins and the current
   Claude, Codex, and ZCode evidence; do not spend more provider calls re-proving
   the seal without a falsification target.
2. **Publish and prove the isolated Claude parent recruiter.** The owner chose
   the local canary-only `claude -> codex-subscription` recruiter pin. Finish its
   local gates and recovery pair, then obtain fresh authority for push/PR/merge,
   owner-config update, exact-main install, and one bounded falsification draw.
   No general-turn route change or unapproved retry is authorized.
3. **Make the Rule-8 claim only after the owner accepts its cost.** Advance the
   candidate to the disk-proven `f7b84c8a40fa` boundary and re-anchor R2/R3/R7;
   no new capture surface or live draw is needed. Re-run the fixed 15,000 ms cold
   control and proportional gates at that exact candidate.
4. **Treat Codex as parent-solid and child-upstream-blocked.** Keep its passing
   parent header proof. The 0.148 draw stopped before spawn; do not repeat it
   until a new upstream surface or deterministic preflight repair exists. Rule
   4 still requires a started child and readable host-authored delivery artifact.
5. **Finish ZCode beyond Option A.** Retain this parent proof and the existing
   one-card child artifact, then prove the plural-card Rule-4 contract, accepted
   outcomes, promotion, and latency on an exact merged install.
6. **Move to the OpenClaw box next.** Scope its missing Rule-4 route, implement
   it through review/fast gates, install there, and collect host-written live
   evidence. Hermes follows as the fifth host in a later authorized package.
7. **Close the cross-host program last.** Run the matched Agency-on/off corpus,
   complete benchmark validity and cold/warm/fan-out bounds, reconcile every
   exact-candidate matrix cell, then prove Rule 9 from the complete five-host
   set. Hosted/release verification runs once at the end under fresh funding
   and publication authority.

### NO-COST DIAGNOSTIC: parent pin worked; recruiter contract was unsafe

PR #303 merged exact parent-pin head `dbfe2b0d` to main as `eff66c67` with
skip instructions and no hosted run. A clean exact-main install refreshed the
shared Claude, Codex, and ZCode projections before the single authorized Claude
draw. The owner config then requested `claude -> codex-subscription` for the
accepted-outcome parent recruiter while preserving the separate child pin.

Pair `39ff6dca0e5885d132cefadecc3e1fdb` proves that route was honored: its
Haiku planner applied, and both recruiter attempts actually reached
`codex-subscription` / `gpt-5.6-terra`. Both were rejected
`staff_without_safe_team` for `unit-parseport-impl-verified`. Attempt one
ranked four real implementation candidates with no axis; the funded repair
ranked two and left `capability` uncovered. Parent preflight therefore failed
before any route, child judge, card delivery, outcome, attestation, or
promotion. The authorized draw was not retried and **no matrix cell moved**.

The read-only investigation and exact limits are in
[`AR-119-39ff6dca-recruiter-diagnostic-evidence.md`](AR-119-39ff6dca-recruiter-diagnostic-evidence.md).
The full 2,367-character parent prompt is exactly reconstructable, while the
two raw recruiter bodies and byte-exact dynamic recruiter prompt are not: the
Store retained only their allowlisted failure projections and did not retain
the applied planner document or provider bodies. The source prompt nevertheless
showed the defect directly. It never said `required` is mandatory selection,
its machine response contract did not define how classifications derive the
team, and repair feedback omitted the prior classifications, team-search
counts, complement slots, and exact missing coverage.

The local provider-free candidate repairs only that boundary. It makes
`required`/`acceptable`/`forbidden` selection semantics explicit, supplies a
bounded prompt-only safe-team repair contract without proposing a replacement
team, excludes model-forbidden coverage from axis diagnosis, and persists only
the three content-free team-search counts previously requested in AR-253.
Provider routes, canary pins, owner config, and ordinary turns are unchanged.
Focused recruiter/receipt/conformance verification passes 97/97; the production
spine passes 797 with 20 skips and deterministic matrix regressions pass 695.
All 14 local gates pass in 13.9 minutes. Commits `e7e4e285` / `1dd70983` are local;
no provider, host CLI, config write, install, publication, or live draw followed.

### EXACT-MAIN DRAW: recruiter output is valid; hiring state is ambiguous

PR #304 merged the recruiter safe-team repair as `c279bca9` with `[skip ci]`
and no hosted run. Claude, Codex, and ZCode were reinstalled from that exact
main tree before one Claude accepted-outcome draw. Pair
`fcffd96cf0fe7e2ef01ad7a3e030c8a9` reached an applied Haiku planner and an
applied pinned `codex-subscription` / `gpt-5.6-terra` recruiter. It then failed
closed as `no_safe_sufficient_team` / `recruiter_abstained`, before any routing
decision, child judge, card delivery, outcome, attestation, or promotion.

This is safe behavior and proves the repaired recruiter output contract was
accepted. It is not good selection: the active and host-eligible
`typescript-application-engineer` contract is an exact TypeScript,
implementation, and runtime-validation match. The draw was not retried.

The empty durable `hiring_reason_codes` field cannot distinguish no hiring
event from a deferred terminal hire or approval event that was later rolled
back with failed atomic preflight. The Store correctly has no pending hiring
mutation in either case. The exact read-only evidence, Store limits, and parent
prompt hashes are recorded in
[`AR-119-fcffd96c-hiring-diagnostic-evidence.md`](AR-119-fcffd96c-hiring-diagnostic-evidence.md).

AR-259 is the bounded no-cost diagnostic repair. Its local candidate projects
only the closed hiring status and whether a positive inference-call count was
consumed into the existing content-free failure receipt. It does not retain
worker identity, notification, prompt, response, or pending contract, and it
does not change provider routing or selection. Focused warning-strict
preflight/dynamic-hiring verification passes 103/103. Recovery pair
`de9ef543` / `13413c53` passes all 12 proportional local gates in 1.3 minutes.
Publication, exact-main installation, and one decisive draw remain; **no matrix
cell moved**.

### EXACT-MAIN DRAW: accepted host outcome; reporter rejects launch binding

PR #306 merged AR-259 as exact main `06f10171` with `[skip ci]` and no
hosted run. Exact-main installs refreshed Claude, Codex, and ZCode. The single
telemetry-preceded Claude draw for pair
`9685a16db43269c171c6c702aa9322c9` then completed producer and verifier native
children through the requested `codex-subscription` provider and recorded one
accepted outcome for the existing TypeScript contractor. The private host
collector returned `accepted`; no timeout, truncation, preflight-failure
receipt, second draw, or retry followed.

The top-level canary still failed closed because its reporter admitted only
`child_id` route bindings. Both verified Claude deliveries use the supported
prelaunch shape `binding_kind = launch_id` and `binding_id = launch_id`; each
delivery separately records the actual child ID learned from the host artifact.
All other route/delivery parent, launch, nonce, decision, digest, card, and
provider facts correlate. The exact Store rows and evidence limits are in
[`AR-119-9685a16d-accepted-outcome-evidence.md`](AR-119-9685a16d-accepted-outcome-evidence.md).

AR-260 is a provider-free reporter repair. It projects child identity from the
verified delivery and accepts only exact child-ID or exact launch-ID bindings;
unknown and mismatched bindings stay rejected. The disposable host artifacts
were removed with the isolated profile, so Store correlation is not promoted
into retained Rule-4 proof. This draw proves reuse, not a new hire, and **no
matrix cell moved**.

### EXACT-MAIN PROOF: Claude outcome reporter passes

PR #308 merged AR-260 as exact main `00c4dc7e` with `[skip ci]`; GitHub showed
zero branch or merge workflow runs. Fresh Claude, Codex, and ZCode installs all
name runtime digest `75e998e4af26...` and status reports no drift.

The sole telemetry-preceded Claude draw for pair
`2919802e595027a84c37f82a3bf59690` completed both native routes, and producer
plus verifier actually answered through the requested `codex-subscription`.
The reporter projected distinct host-observed child IDs and returned
`canary_passed=true`; acceptance event `0c2dc63a...` was recorded for the
existing TypeScript contractor. Claude exited 0 without timeout or truncation,
and no retry followed.

The exact report and limitations are in
[`AR-119-2919802e-accepted-outcome-proof.md`](AR-119-2919802e-accepted-outcome-proof.md).
AR-260 is complete. This is accepted-outcome reuse, not a new hire or promotion.
The isolated profile retained no host artifact and no attestation, so **no
formal Rule-4 matrix cell moved**.

### ORDINARY CLAUDE DRAW: hiring reached approval, then rolled back

One telemetry-preceded exact-main Claude turn requested a read-only SAP
ABAP/CDS/HANA cardinality diagnosis through exactly one native child. Session
`f4f3d45e-6c83-470e-9f9f-9eafb06c0651` exited 0 and the child produced a
substantive answer without tools or file changes. It was nevertheless a generic
native child, not an Agency-staffed specialist.

AR-259 makes the preflight boundary decisive. Receipt `ab343cd9...` records an
applied Haiku planner, applied Sonnet recruiter, staffing abstention, terminal
`hiring_status_pending_approval`, and `hiring_inference_attempted`. The Store
has no correlated hiring case after atomic rollback, and the workforce stayed
at 31 contractors. The draw was not retried.

Provider-free compilation reproduces the causal product defect: a contract
whose narrow scope says "Read-only diagnosis of ABAP CDS association
cardinality" is classified `medical` and owner-approval-required because the
deterministic risk table treats bare `diagnosis` as medical authority without
domain context. Raw hiring content is intentionally unavailable, so the exact
generated field is not claimed. The exact facts and limits are in
[`AR-119-f4f3d45e-hiring-risk-evidence.md`](AR-119-f4f3d45e-hiring-risk-evidence.md).

AR-261 narrows only that overloaded marker: diagnosis is exempted only when
technical context is asserted and medical context is absent; context-free,
medical, clinical, or patient diagnosis remains owner-gated. The mandatory
isolated security reviewer and all other risk classes remain unchanged.
Focused hiring-contract and dynamic-hiring tests pass 88/88, and all 12
proportional local gates pass in 1.3 minutes. PR #310 merged the repair to exact
main `692a9257` with `[skip ci]`; GitHub recorded zero branch or merge workflow
runs. Claude, Codex, and ZCode were freshly installed from that merge with no
reported runtime drift.

### EXACT-MAIN CLAUDE DRAW: authentication stopped before staffing

Before the draw, the complete contractor roster contained 31 workers and exact
searches for `erlang`, `beam`, and `nif` returned zero matches. Provider-free
compilation of the proposed Erlang/OTP BEAM scheduler contract returned no risk
classes, `human_approval_required=false`, and `enabled=true`. Telemetry then
reported 35.8 percent remaining against the 50-percent checkpoint; the clean
merged-main commit above satisfied that checkpoint.

The single post-fix attempt used fresh Claude session
`9b7c38b0-2a51-4ab1-b9af-8d6f67e6c4c2`. Claude's host-written transcript
proves the exact installed SessionStart and UserPromptSubmit hooks ran, the
plugin instruction and resident-steward frame loaded, and no Agent call or
child launch followed. The parent stopped with `OAuth session expired and
could not be refreshed`, zero input/output tokens, and zero cost. `claude auth
status` then reported `loggedIn=false`, `authMethod=none`.

Agency trace `2f3a63c8-cc2f-42c6-984b-6b4be2d49e09` and immutable failure
receipt `93f0adfd-4005-4785-983f-25077da1b0b9` close the other side of the
boundary: stage `routing`, reason `workforce_provider_unavailable`, one failed
`claude-haiku` planner attempt with `provider_no_valid_response`, staffing
reason `inference_unavailable`, and no hiring reason codes. Recent intent and
post-start child-launch projections are empty; the contractor count remains
31. This is installed-hook and authentication evidence, not staffing, hiring,
reuse, or an AR-261 behavioral result. Do not retry this session or work unit.
A fresh Claude login and explicit authorization for a genuinely different draw
are required. **No matrix cell moved.**

### LOCAL DASHBOARD PARITY REPAIR: slow host evidence becomes observable

The durable service was refreshed from exact main `692a9257` and proved active,
reachable, manifest-current, and definition-current. The authenticated
workforce surface exactly matched CLI at 294 workers, 263 employees, 31
contractors, and 32 hiring cases. Host parity exposed one independent defect:
CLI and authenticated `/api/hosts` reported current Claude installation state,
but the rendered panel remained `inspection-stale`.

AR-262 separates refresh cadence from the bounded actionability horizon. A
host inspection still refreshes after three seconds and each request still has
a two-second deadline. A completed last-good result may now remain actionable
for at most 30 seconds while its refresh runs; after that it is sanitized and
reported stale exactly as before. This bridges the dashboard's 15-second poll
without weakening fail-closed expiry or generation-bound host mutations.

The local candidate passes 189 affected Python/hardening tests and 134 dashboard
UI tests; the warning-strict production spine passes 802 with 20 skips, all 12
proportional local gates pass in 1.6 minutes, and focused Ruff checks are green.
Installed as owner-private runtime digest `9e0a85aa...`, it renders Claude as
registered, native enabled, runtime on, and
`enabled-runtime-unverified` after a normal refresh without `/api/hosts`
prewarming. Codex, ZCode, OpenClaw, Hermes, and all workforce counts match the
CLI projections. Tracker #311 is now linked under explicit owner authorization,
and the no-Actions publication sequence is active. No provider call, host draw,
candidate promotion, rule promotion, or matrix movement followed.

### CODEX DESKTOP REGRESSION: current parent task has no hook snapshot

The current Codex Desktop package `26.818.3698.0` uses embedded CLI
`0.149.0-alpha.4` and reports hooks stable, the Agency plugin enabled, and its
current hook states trusted. Nevertheless, the active task has no current
`SessionStart` or `UserPromptSubmit` hook-log entry, no injected Agency
snapshot, and no current Store run or resident-manager binding. Its rendered
`Agency/Agencies loaded: none` is therefore invalid fallback evidence: it hides
activation unavailability rather than proving an empty Agency selection.

This does not retract the fresh Codex CLI parent control, which loaded
`agency-steward` and emitted the exact Store-backed header. It scopes the new
failure to the Desktop frontend/task lifecycle. Open upstream Codex reports
21639 and 33413 describe the same class of frontend hook-dispatch gap; AR-263
owns the self-contained local product record. No provider call, child draw,
candidate promotion, rule promotion, or matrix movement followed.

### EXACT-MAIN AR-264 INSTALL: shipped contractors advance to v2

PR #315 merged the shipped package-v1 migration repair as exact main
`f76050d7` with `[skip ci]`; no hosted workflow ran. Before installation, the
owner Store was copied to
`pre-ar264-f76050d7-20260821T171621.410934Z.db`. The 21,999,616-byte backup
passes SQLite integrity and has SHA-256
`9b9936456e90313b76920a4dfd3890c7c44b0243d4a2781592182325aa2bcdaa`.

Installing that exact merge advanced all 15 known packaged contractors from
either shipped package-v1 identity to revision 1, employment contract v2, and
two-version lineage. TypeScript remains worker `54cb1db1-...`, version
`contractor-2-6b0d5cae3b65a44d`, with its two accepted outcomes and 2/3
promotion readiness intact. Claude, Codex, and ZCode were freshly installed at
bundle digests `2eaa89cc75f8...`, `75f6519c74ba...`, and
`2f1bb95ba204...`; their native projections and launchers are current. This is
merged migration and installation proof, not live contractor execution proof.

### EXACT-MAIN SMOKE: Codex and ZCode stop before Agency child proof

The single Codex activation draw used session
`01a0255a-b6ba-7880-a427-982c4397c8fd` and trace
`01a0255a-c4b2-7472-8617-6534e9a8fa21`. Its `codex-fast` planner and recruiter
responses were applied, but preflight ended `workforce_inference_failed` with
no routing decision, specialist, spawn, delegation, delivery, skill, or final
header. The isolated host artifact did load the `agency-steward` parent frame;
it then truthfully reported that no accepted plan row supplied a native task.
This is parent hook delivery inside the isolated CLI canary, not a Codex child
measurement and not retroactive evidence for the already-running Desktop task.

The single ZCode draw exited 0 in host session
`sess_57b47433-ac40-4dcf-b9c8-ca9ec9784320` and started generic child
`agent_469477bd-183d-4725-9209-541c79802cd4`. Agency run
`62345127-0dd0-439a-9baa-1e32a485d9fa`, trace
`37bdf697-e521-452c-8c44-c594a8fa2caf`, stopped earlier:
`workforce_provider_unavailable` after its ordinary parent planner reached the
expired `claude-subscription`. It wrote no decision, specialist, skill,
delegation, worker run, or model receipt. The host artifacts contain zero
`[AGENCY INFERENCE TEAM v6]` markers, so the process-scoped GLM child-judge pin
was never exercised. The generic child is not Agency staffing. Neither draw was
retried, provider routing stayed unchanged, and no matrix cell moved.

### EXACT-MAIN OBSERVABILITY: dashboard parity and skill capture

After reboot, the dashboard registration and exact-main manifest remained
owned and current, but its scheduled worker was stopped. Starting the existing
service restored authenticated health without reinstalling or changing config.
Dashboard `/api/workforce` and exact-main CLI then returned the same 31
contractor rows at digest `401e883532e9...`. The host surface initially exposed
Claude as truthfully stale while its bounded background inspection ran; the
second poll completed all five inspections. Dashboard and CLI host projections
then matched exactly at digest `003caceee19d...`, with identical master
generation 56.

Skill capture is provider-free proven on this exact tree. Three focused hook
cases pass: Claude `Skill`, Codex `skill_view`, and ZCode `Skill` persist the
loaded skill and inject it into the updated first-pass header. The owner Store
contains 19 historical `skills_loaded` rows, including Codex `openai-docs`.
Those rows prove the capture path has operated, not that this already-running
Desktop task received the new install's lifecycle hooks. A completely new
Codex task must show the fresh header and skill line; if it does not, AR-263
remains the exact boundary. Claude authentication is still expired. No hire,
accepted outcome, promotion, rule promotion, or matrix movement followed.

### FRESH DESKTOP RECHECK: lifecycle dispatch remains absent

Completely new Codex Desktop task
`01a02587-1489-7e13-834e-3299ae05fb43` began at
`2026-08-21T18:13:24Z`, after the exact-main installation. Its persisted task
record has one user turn and no prior turn: the first user message was the
AR-119/AR-264 recovery prompt, not the intended exact `agency status` control.
The first assistant response at `18:13:38Z` contains no `Agency/Agencies
loaded` or `Skills loaded` header and no v6 marker.

The independent lifecycle sources agree. `hooks.log` last changed at
`2026-08-21T17:52:11Z` and contains no task or turn ID. Read-only Store queries
return zero runs, resident-manager bindings, and skill rows for task
`01a02587-...` and turn `01a02587-1dd6-...`; the Store still contains 19 total
historical skill rows. Therefore this is another AR-263 Desktop hook-dispatch
observation, not a valid empty selection and not exact-status prompt proof. A
skill was deliberately not loaded without authoritative activation.

No Codex canary, provider call, child, Store mutation, provider-route change,
rule promotion, candidate advance, or matrix movement followed. Claude login
remains the operator gate before any new Claude or ZCode Agency-parent draw.

### EXACT-MAIN AUTHENTICATED CLAUDE HIRE: parent passes, child times out

The owner restored Claude login and `claude auth status` reported first-party
`claude.ai` authentication on the Max subscription. A provider-free baseline
found no COBOL, CICS, VSAM, COMMAREA, or z/OS contractor among the existing 31.
One genuinely different, telemetry-preceded draw then used Claude session
`560e6da4-75b6-41c8-8733-5dc101d6a14b` and Agency trace
`66dca68e-2d98-4ffd-abd9-44555bb875a5`.

Agency's installed `UserPromptSubmit` hook injected an 8,164-character current-
turn capsule at SHA-256 `b25aafcb92aaf7f2077f37b47d743d1e0a8944866e4356dc6d9c7a93fa063038`.
Its exact header named `agency-steward` plus
`cobol-cics-vsam-diagnostics-specialist`, `delegated: none`, `Skills loaded:
none`, workforce inference through Sonnet, and `Recruited via:
inferred+hiring`. The Store agrees: run `849ce231-...` reached preflight
`ready`, decision `2f589fa7-...` was accepted at confidence 1.0, hiring case
`35f59955-...` was applied as standard risk without owner approval, and one
`specialists_loaded` row was written. Workforce projection now contains 32
contractors, including active Agency contractor `cobol-cics-vsam-diagnostics-
specialist` as worker `7c7306dc-...`.

Claude then emitted one progress sentence without the required five-line
header and called exactly one native `Agent`. Native-child decision
`native-child-cca0f519569741f4f09095124af80a3b` selected the same specialist
through actual provider `codex-subscription`, but child
`aa0a0207e0caa208d` remained an open generic worker run. It produced only an
incomplete thinking record before the parent hit the fixed 420-second ceiling.
There is no child delivery-verification row, no child conclusion, and no final
parent response; Store run `849ce231-...` remains active because termination
precluded finalization. This proves a genuine post-AR-261 hire and a healthy
Agency parent path, not compliant response-header emission, verified card
delivery, or completed contractor execution. The draw is consumed and was not
retried.

### EXACT-MAIN ZCODE PLURAL ATTEMPT: recruiter rejects; child stays generic

With the Claude parent path restored, one new ZCode recovery-and-security work
unit ran from a clean 50.1-percent telemetry checkpoint. Host session
`sess_524d8b86-4a46-4e09-99bf-5c1653e5d068` exited 0 and started exactly one
native child, `agent_ce74bc0f-7091-4b61-aec7-91ffe90742c1`, which returned a
substantive no-tool PostgreSQL recovery runbook and threat model.

Agency evidence invalidates that prose as plural-card proof. Run
`d8c3b9a5-...`, trace `b08d8d79-...`, ended `preflight_failed` /
`workforce_inference_failed`. Its `claude-subscription` Sonnet planner applied,
but both recruiter attempts were contract-invalid with
`staff_without_safe_team`: the unit required three specialists, allowed four,
and each response ranked six executable candidates without a safe team. The
Store contains no routing decision, specialist, Agency worker run, delegation,
captured assignment, or delivery verification, so the process-scoped
`zcode-recruiter` / GLM child judge was never reached.

All four host artifacts are retained. The 2,232-record child transcript and
its metadata/output files contain zero `[AGENCY INFERENCE TEAM v6]`, native-
child, or Agency-header markers, including record zero. The child is generic
host work, not Agency staffing. The draw is consumed and was not retried;
ordinary provider routing and all Option A pins remain unchanged. No rule was
promoted and **no AR-119 matrix cell moved**.

Post-recording governance passes metadata for 731 Markdown files, policy and
worklog checks, documentation validation for all 731 files, and `git diff
--check`. The focused exact-main Linux boundaries pass 8/8 warning-strict tests:
unsupported host-canary execution, unsupported child-artifact reading, and the
Hermes/OpenClaw native-child bridge cases. The first sandboxed invocation
stopped before collection on the private-root trust guard; the identical run
with its required owner-private test root passed in 2.56 seconds. No product
code changed in this evidence slice.


## 2026-08-21 — OpenClaw parent receipt repair installed; post-fix proof pending

The Linux package uses branch `codex/ar119-openclaw-hermes-litellm` from fetched
main `4a3267738bb20519500513ea1498fc68f8ea9443`. Native OpenClaw remains
`litellm/task-general`; only Agency profile `linux-task-agency-router` requests
LiteLLM alias `task-agency-router`. Hermes remains running and untouched.

OpenClaw `2026.7.1-2` now installs and starts with 13 plugins, connected Slack,
and active Telegram polling. AR-268 repaired the concrete outage where a valid
control envelope with `error: null` exited 2. Exact installed bridge status now
exits 0. The first fresh local control after that repair is retained as failed,
not promoted: session `57f19f38-338d-4d93-9c46-eac7b6a4831a`, trace
`4959bd8c-a0bc-4e3d-bcb9-8cbcc1441547`, ended `response_invalid`; finalization
event `01af794d-fb97-41c5-8920-2a8bfc2a3558` names missing field
`actual_model_selected`. The visible Agency-shaped header is therefore not
Store-backed acceptance evidence.

AR-271 records the exact cause: installed OpenClaw supplies the model through
`model_call_ended.event.model` when hook context omits `modelId`, and Agency
serialization dropped all receipt fields. The new executable Node regression
failed pre-fix with exit 83 and passes after the bounded fallback and serializer
allowlist repair. Only the Agency integration in OpenClaw was reinstalled; the OpenClaw host
package was not. Its new bundle digest is
`38dadb1a1a14d5f95319dcc401883a54e6415cf9392803e1b81906ceff718107`; launcher
runtime digest is `f7741ed6bfde2844a18151fa43f6536761ba1b6a97a35bdc524d770447309a62`;
launcher SHA-256 is `bb033f9b4facce1d78b42b246e0087f8ef6862d825ddcc48cad73b74dc4c5608`.
Redacted native-config comparison shows only the OpenClaw touch timestamp.

Telemetry reached 43.1 percent, so the post-fix live control waits for the clean
substantive/worklog checkpoint required by repository policy. Telegram has no
post-restart inbound receipt yet. The LiteLLM callback cannot import Agency on
this shared proxy, so actual model may remain unavailable; the requested alias
must not be promoted. No AR-119 matrix cell moved.




## 2026-08-21 — OpenClaw native Agency finalizer repair pending checkpoint

The first post-AR-271 local control is retained as failed evidence. OpenClaw
session `264a65e9-7462-4ea7-9b40-9b38206f1b35`, Agency trace
`94f32f04-3b72-4ffa-8801-953b320e657f`, preserved four native `task-general`
request receipts but delivered no Store-backed header. Run
`2bf6cbd5-d7c9-417a-b423-eeb52b4646de` ended `response_invalid`; finalization
`a5b24d7f-933c-4aa3-8171-3d6ad0547cac` records all five required fields
missing. Native plugin inspection reported zero tools and zero MCP servers even
though the managed bundle retained `.mcp.json`.

AR-272 isolates the defect to the Agency-generated OpenClaw plugin: preflight
required canonical `agency.finalize`, but OpenClaw had no native callable tool
backing it. The new provider-safe `agency_finalize` wrapper delegates bounded
arguments to the unchanged canonical Store finalizer. It introduces no correction
pass and preserves strict finalization and outbound delivery. The executable
regression failed before repair with Node exit 91, and 65 focused OpenClaw
security, adapter, and installer tests pass under process-local umask `0022`.

The next mutation is not an OpenClaw reinstall. After the required clean local
commit pair, stop the existing gateway, run the Agency installer only for target
`openclaw`, inspect the resulting Agency tool, and restart the same gateway.
OpenClaw remains `2026.7.1-2` on native `litellm/task-general`; Agency alone
requests `task-agency-router` through harness profile
`linux-task-agency-router`. Claude, ZCode, Codex, and Hermes remain outside the
mutation boundary. No matrix cell moved.
