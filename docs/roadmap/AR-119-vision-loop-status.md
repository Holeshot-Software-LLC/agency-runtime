---
title: "AR-119 vision-completion loop status"
status: draft
category: roadmap
created: 2026-08-17
updated: 2026-08-17
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

# AR-119 vision-completion loop status

**The machine is on main's build: all three hosts (claude, codex, zcode) pin
runtime digest `cc478bc88258…` (merge `99a7b3ac`, PR #287), store schema 47 ==
checkout 47 == launcher 47, verified read-only at 2026-08-18T01:55Z.** The
loop session (authorized through 2026-08-18 23:59 local) works on the
capsule's branch in `agency-runtime-ar119`, fast-forwarded to `94489201`
(origin/main tip). `native_child_delivery_verifications` still holds zero
rows, ever.

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

### Series 2 ledger (small-unit-policy acceptance, runtime `cc478bc88258…`)

- **Run 1** (launched ~03:40Z, run `a41782e8`, receipt `f6e49b1c`):
  FAILED at parent preflight — planner `provider_no_valid_response`,
  receipt `workforce_provider_unavailable`. Identical stage to series 1
  runs 2-3. Failure kept; run 2 next, serialized.
