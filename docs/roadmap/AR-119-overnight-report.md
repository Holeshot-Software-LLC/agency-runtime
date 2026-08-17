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
pin runtime digest `2cd298158584…` — the post-P2 main (`c77c67a4`, the merge
of PR #275) — verified by reading every `current-<host>.json` after install,
with the installing tree's `agency_runtime/` verified bit-identical to main's.**
AR-258's one-digest property held all night: first at `16f1e720f15d`
(pre-merge main `c6df1449`), then at `2cd298158584` after the merge. At no
point tonight was branch-only code installed.
`~/.agency-runtime/overnight-runtime-state.json` carries the same facts.

**Merged to main tonight, under the standing authorization** (full spine green
locally — 1,462 then 793 post-fix — CI green 13/13 on the exact head, docs
valid): AR-255 P2 (`966e8bae`) and the hiring verdict repair (`e41ac039`),
via merge commit `c77c67a4` on [PR #275].

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

## 1a. Stage 0 sweep: which layers the child judge actually blocks

Fifteen analysis agents swept R1–R8 acceptance criteria against the matrix,
AR-256's layer definitions, the code anchors, the live store, and the host
artifacts on disk; every "reachable" claim was then adversarially verified.
Result, for claude:

| Rule | Installed w/o child judge | Live w/o child judge | Verdict |
|---|---|---|---|
| R1 | **no** | **no** | both-no (v6 envelope is the only hash-carrying artifact; its only writer is a judge-accepted child staffing) |
| R2 | yes | yes | CONFIRMED |
| R3 | yes | yes | REFUTED as stated → corrected: claude-only, and only after the matrix candidate advances to the installed commit |
| R4 | **no** | **no** | both-no (as expected) |
| R5 | yes | yes | CONFIRMED |
| R6 | yes | yes | CONFIRMED (parent-path hiring ladder) |
| R7 | yes | yes | CONFIRMED (two consecutive parent turns) |
| R8 | yes | yes | CONFIRMED (declines are generative: an unstaffed turn that proceeds is the evidence) |

- **The brief's "R1 is parent-side" lead is refuted.** Every R1 anchor is the
  native-child staffing path; the parent capsule carries no hash and no
  decision id, and no shipped code computes a parent-side join. **P2 therefore
  unlocks R1 and R4 together**, doubling its value.
- The single `v6` marker among retained child transcripts is a **false
  positive** (an analysis agent's grep output quoted inside a tool result, not
  launch text). Genuine v6 envelopes ever delivered here: still zero.
- codex generalization: uncertain until hook trust advances (bypass path
  authorized tonight); zcode: the sweep's verifier called it not reachable
  unattended — to be tested against the brief's zcode-CLI instruction before
  accepting.
- Cross-cutting precondition from the verifier: **advance the matrix
  `candidate_commit` to the installed commit and re-run the source-evaluation
  baseline before greening any cell**; the `source_unchanged` carry-forward
  does not apply across ~1,070 runtime insertions.

## 2. Refuted / narrowed

- **Child task size does not explain the declines, further.** Decline #12
  (decision `4c1f3350`, 02:15:13Z) carries `task_chars: 3040` — beyond the
  previous 541–2,408 range — with `code-reviewer` offered (digest
  `b5b83ecc699e`), `confidence: 0.9`, 5.8 s. Decline #13 (`19f89c78`,
  02:20:43Z) at 1,867 chars, confidence 0.95. The size axis is excluded up to
  3,040 characters.
- Baseline (pre-P2) claude series is complete at n=3 on digest `16f1e720f15d`:
  parent staffed 2/3 (the miss is the known recruiter stage,
  `workforce_inference_failed`/`inference_invalid`; successes routed
  `code-reviewer + application-security-engineer` at 105.0 s and 90.0 s);
  child: 2 decisions, 2 declines, 0 staffed. Decisions-to-declines, not
  runs-to-runs.
- **Found in passing, verified against the store: passing contractor security
  reviews are recorded `verdict: "unsafe"`.** `hiring.py:2091` computes
  `"unsafe" if security_reasons else "safe"`, but reviewers now annotate
  passes with reasons — all three applied hires since 08-16 15:39 carry 7–9
  pass-shaped reasons and the mislabel. Evidence-integrity bug only (the gate
  uses a different signal); flagged for a daytime fix, and every R6 citation
  tonight carries this caveat.
- **The brief's Stage 4 ("drive zcode through the zcode CLI") is refuted for
  this box, by measurement.** No `zcode` executable exists on PATH or in
  `C:\agency-cli`, and the zcode canary readiness itself reports "host
  executable not discovered" and "host has no proven read-only, bounded
  native-child noninteractive canary mode". zcode therefore gets install
  parity only tonight (same digest as claude/codex); installed *activation*
  and every Live cell need your own zcode session in the morning.

## 1b. Post-P2 series (per-run split, running)

Digest `2cd298158584` (post-merge main `c77c67a4`); the installed projection
verified to contain the P2 code (`repair_abstention_task` and the confirmed
reason are in the launcher tree).

| Run | Parent | Child decisions (per-run split) |
|---|---|---|
| 1 | staffed `code-reviewer + application-security-engineer`, routing 123.3 s | 1 decision: abstained under **legacy** `native_child_no_specialist_needed` — under P2 semantics the repair could not produce a valid answer. task_chars 1,278, 67 candidates, conf 0.95, first-call 5.0 s (decision `e78ee5de`, 03:17:47Z) |
| 2 | staffed, routing 88.6 s | 1 decision: abstained under **legacy** code again. task_chars 1,369, conf 0.9, first-call 7.0 s (decision `b8fa9526`, 03:28:19Z) |
| 3 | staffed, routing 101.3 s | 1 decision: **`native_child_abstention_confirmed`** — the first confirmed row ever. task_chars 3,431, conf 0.87, 9.5 s (decision `d6b514f7`, 03:36:59Z) |

One repair-failure hypothesis already refuted deterministically: the repair
preamble adds 477 chars against a 1.25 MiB complete-universe prompt budget
(`_MAX_COMPLETE_CANDIDATE_PROMPT_BYTES`), so over-budget preflight failure is
excluded. Remaining candidates — provider/contract rejection on the second
call, or a response-shape violation elicited by the repair phrasing — are
indistinguishable from the store (the gap above).

**Series verdict (n=3, decisions-to-declines 3/3, 0 staffed):**

1. **The P2 repair path is proven live** — run 3's confirmed code can only be
   written by the repair branch of the installed `2cd298158584` runtime.
2. Runs 1–2 show the repair transport is as intermittent as the recruiter:
   repair attempted, no valid answer, abstention stood unconfirmed.
3. **AR-255's falsification clause fires**: P1 and P2 both shipped and the
   child still declines across a comparable series, including once after
   testing its own abstention against the concrete candidate set. The judge
   declines **on the merits**; the fault is upstream in what the parent
   chooses to delegate. The remaining instrument is the owner-gated
   `observability.capture_content` pointed at the child assignment — wiring
   it (flag untouched) is authorized tonight; enabling the flag is the
   owner's morning decision.

- **P2 observability gap, found on run 1:** the persisted decision drops
  `provider_attempts`, and the child judge's calls mint no `model_receipts`
  rows (only the parent planner/recruiter do). The store therefore cannot
  distinguish "repair reached the provider and failed" from "repair raised
  before any call". If the series ends with only legacy-code abstentions and
  zero `native_child_abstention_confirmed`, that gap is the first thing to
  instrument — a receipt row for the repair call, or the owner-gated content
  capture.

## 2a. Repaired tonight

- **The hiring verdict mislabel is fixed on the branch** (`e41ac039`): the
  recorded `critic_evidence.security_review.verdict` now carries the
  reviewer's own gate signal — the same field the hire gate and the
  safety-repair loop branch on — instead of re-deriving from reason-list
  emptiness. Regression test added for an annotated pass; the unsafe-rejects
  path was already pinned. No runtime reader consumed the recorded string, so
  the change is evidence-integrity only. Note: the task chip for this fix was
  also started separately; if a duplicate branch/worktree appears for it, this
  branch already carries the fix.

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
