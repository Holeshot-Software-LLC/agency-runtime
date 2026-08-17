---
title: "AR-119 overnight report for 2026-08-17"
status: draft
category: roadmap
created: 2026-08-16
updated: 2026-08-16
tags: [roadmap, report, autonomous, AR-119, AR-255, AR-258]
related:
  - docs/roadmap/AR-119-overnight-autonomous-brief.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/roadmap/AR-119-rule-host-evidence-matrix.md
  - docs/roadmap/AR-255-child-parity-design.md
supersedes: []
superseded_by: null
type: reference
issue_id: AR-119
---

# AR-119 overnight report

**Your machine is running main's build: all three hosts (claude, codex, zcode)
pin runtime digest `16f1e720f15d…` built from a clean tree at main tip
`c6df1449`, verified by reading every `current-<host>.json` after install.**
AR-258's one-digest property is restored. `~/.agency-runtime/
overnight-runtime-state.json` carries the same facts.

This report is written incrementally through the night so a crash cannot erase
it; the DRAFT marker leaves only when the session ends.

## 1. Proven

- **AR-258 one digest, again.** codex was at `530f6df6`, zcode at `980eb2d1`;
  both now run `16f1e720f15d` alongside claude. Store schema 46 == launcher
  schema 46; the doctor drift check passes. Evidence: the three
  `current-<host>.json` files, install output, runs recorded post-install.
- **The repaired runtime records.** Claude baseline canary run 1
  (2026-08-17T02:08Z) wrote its run row and its own failure receipt; run 2
  (02:15Z) staffed the parent fully.
- **Parent staffing live on the main build** (claude baseline run 2, trace
  `17d236b3`): routing decision `3721c950` accepted with
  `code-reviewer + application-security-engineer`, both loaded,
  `receipt_proven: true`, latency 104,972 ms (the known AR-253 overrun band).

## 2. Refuted / narrowed

- **Child task size does not explain the declines, further.** Decline #12
  (decision `4c1f3350`, 02:15:13Z) carries `task_chars: 3040` — beyond the
  previous 541–2,408 range — with `code-reviewer` offered (digest
  `b5b83ecc699e`), `confidence: 0.9`, 5.8 s. The size axis is now excluded up
  to 3,040 characters.
- Baseline (pre-P2) child record now stands at **12 abstained, 1 unavailable,
  2 invalid, 0 staffed** across all recorded native-child decisions.

## 3. Decisions taken in the owner's absence

1. **Installed from the clean session worktree, not the primary checkout.**
   The primary carries your WIP in `agency_runtime/cli/eval_commands.py`; an
   install from there would have baked uncommitted WIP into the published
   projection. The worktree sits at the identical commit `c6df1449` with a
   clean tree, so the projection is a pure main build. Falsification: if a
   clean-tree install from the primary at `c6df1449` yields a digest other
   than `16f1e720f15d`, the "content-determined digest" premise is wrong and
   the runtime-state file must be corrected.
2. **AR-255 P2 reason-code split settled** (see the design doc):
   `native_child_abstention_confirmed` = repair ran and reaffirmed;
   `native_child_no_specialist_needed` (legacy) = abstention stood because the
   repair could not produce a valid answer. Falsification recorded in the
   design doc.
3. **Canary series serialized, never concurrent.** Concurrent host canaries
   would contend on the same inference providers and could depress staffing
   rates; rates measured under contention would not be comparable to the
   existing series.
4. **Commit trailer names Fable 5**, the model actually driving this session,
   where the brief's template said Opus 5.

## 4. Morning decisions for the owner

- (placeholder: filled at end of night)

## 5. Still blocked, and whose hands it needs

- **openclaw / hermes**: not installed here by your instruction; their
  Installed/Live cells cannot move. Verification packet: see section 7.
- **Rule 9**: cannot close while two hosts are out of reach by construction.

## 6. Caveats

- Any codex result produced tonight uses the authorized
  `install --agent codex --verify-activation --autonomous` surface and carries
  `trust_bypass_used: true`. Every such matrix cell is labeled bypass-derived
  and none satisfies an attended-trust criterion.

## 7. Branch and state

- Branch: `claude/remote-control-14de96` (session worktree
  `remote-control-7efcd5`). Head at the time of each update is in git.
- Nothing committed in the primary checkout; your WIP untouched.
- P2 implemented and committed (`966e8bae`); merge gated on the full
  production spine + matrix-evidence suites under `-W error`, in flight.
- Child assignment content capture: NOT wired as of this update; the standing
  authorization conditions are recorded in the brief. If wired later tonight,
  this line changes.
