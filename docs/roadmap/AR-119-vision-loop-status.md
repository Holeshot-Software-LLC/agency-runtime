---
title: "AR-119 vision-completion loop final status"
status: active
category: roadmap
created: 2026-08-17
updated: 2026-08-18
tags: [roadmap, report, autonomous, loop, AR-119, AR-253, AR-255]
related:
  - docs/roadmap/AR-119-vision-completion-autonomous-brief.md
  - docs/roadmap/AR-119-instrument-series-status.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/roadmap/AR-119-rule-host-evidence-matrix.md
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
