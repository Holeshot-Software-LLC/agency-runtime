---
title: "AR-119 vision-completion autonomous loop brief"
status: active
category: roadmap
created: 2026-08-17
updated: 2026-08-17
tags: [roadmap, autonomous, loop, AR-119, AR-252, AR-253, AR-255, AR-256]
related:
  - docs/roadmap/AR-119-founding-vision.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/roadmap/AR-119-rule-host-evidence-matrix.md
  - docs/roadmap/AR-119-instrument-series-status.md
  - docs/roadmap/AR-119-overnight-autonomous-brief.md
  - docs/roadmap/AR-255-child-parity-design.md
  - docs/roadmap/issue-AR-256-canonical-nine-rule-completion-contract.md
supersedes: []
superseded_by: null
type: reference
issue_id: AR-119
---

# AR-119 vision-completion autonomous loop brief

The owner is remote through 2026-08-18 and has authorized a fresh session
to run this loop unattended. The goal is the nine-rule vision's completion
contract (AR-256), measured only by the evidence matrix. The loop STOPS —
it does not idle — per section 6. This brief was adversarially reviewed
before shipping; where it conflicts with the capsule, THE CAPSULE WINS.

## 1. Load order and ground rules

Read, in order: `docs/roadmap/handoffs/issue-AR-119.md` (the capsule —
its front matter names the working branch; that value is authoritative),
`AR-119-founding-vision.md`, this brief, then
`AR-119-overnight-autonomous-brief.md` **for its ENVIRONMENT TRAPS and
REFUTED lists, which remain live** (PATH must prepend `C:\agency-cli`;
never install with the packaged `agency.exe` — it is schema-pinned and
refuses the current store; eight preflight/litellm tests are red on clean
main and outside every gate — never attribute them to your changes; do
not re-chase hypotheses the REFUTED list already killed), then
`AR-119-instrument-series-status.md` and `AR-255-child-parity-design.md`.

The founding vision is the sole wording authority; the matrix the sole
completion authority; neither implementation nor simulation is host
proof. Never infer the target from reachability, row counts, or traffic.
The machine-state authority is `~/.agency-runtime/overnight-runtime-state.json`
— docs record history and may name older digests; the state file names
now. You must UPDATE that file after every install round. Check store vs
launcher `SCHEMA_VERSION` before believing any host measurement.

## 2. Authorizations (until 2026-08-18 23:59 local; section 6.4 is exempt)

- Work on the capsule's branch. Changes reach main ONLY through a PR
  whose check rollup you verified: state `CLEAN`, zero pending checks,
  zero conclusions other than SUCCESS or SKIPPED, and at least one
  completed SUCCESS check present (an empty rollup is NOT green — wait
  for checks to appear). Read this from `gh pr view --json`, never from a
  piped exit code. Never push directly to main; never skip or weaken a
  hook or gate (`--no-verify`, `SKIP_LOCAL_GATES` are forbidden). Red
  that job logs prove to be GitHub-infra (429/503 before repo code runs)
  gets `gh run rerun --failed` on the same commit, never a merge-through.
- Push mechanics: pushing the branch ref from the linked worktree fails
  in the pre-push hook; push the shared ref from the primary checkout
  instead, and treat THAT hook's pass as meaningless — the real gate is
  the full `run_local_gates.py` you already ran in the branch checkout.
  The primary checkout's local `main` is STALE (tens of commits behind
  origin) and carries the owner's WIP: never install from it, never gate
  against it, never commit/revert/stash in it.
- Install procedure, after every merge that changes the package tree:
  `git fetch origin`, verify the installing checkout's `HEAD^{tree}`
  equals `origin/main^{tree}`, confirm `git status --short` is clean,
  then `python -m agency_runtime.cli install --agent <host>` for claude,
  codex, and zcode from that checkout. Afterward verify all three
  `~/.agency-runtime/launchers/current-<host>.json` name ONE identical
  `runtime_digest` (AR-258) and update the runtime-state file. Docs-only
  merges need no reinstall; say so in the state file note instead.
- Run live canaries: isolated-profile, `--timeout 420`, exact confirm
  phrases, strictly serialized — launch, end the turn, analyze only on
  the completion notification. If no completion notification arrives
  within `--timeout` plus five minutes, the run is dead: read whatever
  report exists, record it as a failure, and move on — never wait
  indefinitely. Codex autonomous bypass is authorized; label all
  bypass-derived evidence as such — it never satisfies attended trust.
- Make delegated decisions per section 5, recording each one.

## 3. Forbidden at all times

No re-authentication or credential prompts of any kind; no openclaw or
hermes installs; no tracker writes; no tags, releases, force-pushes,
history rewrites, or repository-setting changes; no pushes to main; no
roster retirement approvals (`agency roster approve` after a retire is
the owner's half of a two-step fence — leave it to him). Never change
the value of `observability.capture_content`. Captured content flows
only through the surfaces that exist today (`runs.user_message`,
`native_child_captured_assignments`), must pass `redact_content`, and
stays local-only; building any NEW capture surface needs the owner.
Never weaken evidence or parity to hide codex's opaque channel. The
matrix's acceptance criteria and AR-256's contract are never edited to
make completion easier.

## 4. The working loop (keep exactly this shape)

Step 0 of EVERY cycle: check the clock against section 6.2 and evaluate
every stopping condition; within 60 minutes of expiry, begin 6.4 now.

1. Pick the highest-value unproven matrix cell or blocker from section 7;
   bound the attempt: 3 tries or 45 minutes, then record and move on.
   Re-picking a previously boxed blocker requires NEW evidence — a
   changed receipt shape, a merged fix, a recovered provider — not hope.
   The predecessor brief's spin-detection triggers apply verbatim: same
   error twice, tuning-and-hoping, or reading source to support rather
   than test a claim means STOP that line in the next action.
2. Implement on the branch. Code changes carry tests at the layer that
   would have caught the last regression (persisted-row, not
   pre-projection).
3. **Adversarial review before shipping**: attack every finding and
   change; review fan-outs use isolated worktrees or read-only agents
   ONLY (a "verify" agent edited the tree mid-review once already);
   apply confirmed findings yourself; re-test.
4. Ledger: conventional commit; `python scripts/update_worklog.py` as a
   SEPARATE `docs(worklog):` commit; `python scripts/verify_docs.py`;
   then the FULL `python scripts/run_local_gates.py`, solo, never
   concurrent with anything that runs pytest. Judge it by its own final
   summary line and its process exit code captured directly — never
   through a pipe that swallows status.
5. Merge-first: gates and verify_docs before any merge; never merge to
   unblock a measurement.
6. Measure with the series discipline: probe first (`agency eval
   routing` plus one accepted live draw in the store); if provider draws
   fail at two consecutive stages, back off at least 30 minutes on that
   measurement — backoff pauses the attempt clock, it does not extend
   work on the blocker — and do other section-7 work meanwhile; then a
   three-run serialized series, failures kept, reason codes per run.
7. Record in the repo, not the reply: the status doc, AR-255 for
   child-staffing findings, the matrix ONLY for cells actually proven
   (update-contract anchors at the candidate commit), and the capsule —
   which has a hard 180-line cap — at every checkpoint.
8. Checkpoint on `python scripts/context_handoff_status.py --json
   --threshold 50`: nearing compaction, refresh the capsule FIRST so any
   successor resumes from it (standing rule after compaction/restart).

## 5. Delegated decisions (record each as a "Delegated ruling")

The session may decide, without waiting, product and measurement calls of
kinds the owner has already exercised, inside these precedents:

- Small units still get cards (2026-08-17 ruling) — extend, don't
  reverse.
- Instrument wording may be hardened. The prompt is planner input: never
  name expertise, skills, capabilities, or staff in it; golden-pin every
  change; move the codex recognizer in the same commit.
- Claim a matrix cell only on artifact-grounded proof; prefer collecting
  a clean artifact over claiming an ambiguous one (the cancelled-hook R8
  session stays unclaimed).
- Reason-code splits stay per-run; never collapse codes a measurement
  needs separated.

NOT delegated, ever: anything in section 3; roster retirement approvals;
attended-trust actions (codex TUI); installs on absent hosts; any
reading that weakens the founding vision's wording or the matrix's
acceptance criteria; new capture surfaces.

## 6. Stopping conditions (stop means stop — report, no idling)

1. **Complete-or-blocked**: every matrix cell provable on this machine
   is proven at all four layers, and each remaining cell carries a
   recorded blocker that is either owner-physical (codex attended TUI
   trust; zcode CLI absent; openclaw/hermes absent — packet runs on the
   owner's boxes) or persistent-provider (the same provider stage failed
   across three series spaced over at least six hours — record it as
   `blocked-on-provider` and stop grinding it).
2. **Expiry**: 2026-08-18 23:59 local machine time.
3. **No-progress**: three consecutive cycles that produce no NEW proven
   matrix cell and no merged non-docs improvement. Recorded findings and
   docs-only merges do NOT reset this counter — they are the loop's
   exhaust, not its progress.
4. **Stop procedure** (authorized at any time, INCLUDING after expiry —
   finishing safely is exempt from the deadline): finish or abort any
   in-flight canary per the timeout rule; land or close any open PR;
   leave main and the installed hosts matched on one digest; refresh the
   capsule and the runtime-state file; write the final status doc opening
   with what runtime the machine is on.

## 7. Priority order at loop start

1. The small-unit-policy acceptance draw: one clean child draw that
   STAFFS the pure work unit → first `native_child_delivery_verifications`
   row ever → then pursue R4 claude Installed/Live per the matrix's
   criteria. Each deterministic link of the parent chain has now been
   proven green at least once across the 2026-08-17 series (routing
   acceptance, unpadded selection, card load, single child, verbatim
   capture, valid parent header) — never all in one run yet; a clean
   provider draw is the missing piece.
2. The remaining claude cells: R1 (Installed AND Live), R5 Live, R8 via
   a CLEAN artifact.
3. AR-252's collector, honoring its recorded constraints (the verdict
   binds the producer's transcript digest, unreadable to any verifier
   child — Agency supplies the binding; settle that first, as the issue
   requires): pair one real producer proof, one distinct verifier proof,
   and that verdict — nothing yet collects a real envelope.
4. AR-253 evidence: keep localizing the recruiter contract failures
   (decision "staff" + ranking + empty selection, provider-side) and the
   hook-window cancellation; file receipts, don't chase provider fixes.
5. Codex bypass series where measurable; record attended-trust blockers
   precisely. zcode: measure what exists, record the CLI absence.
6. AR-125 matched corpus ONLY after candidate and provider validity
   hold; malformed or timed-out arms are invalid, never upstream losses.
   Rule 9 cannot close until 1-8 are proven on all five hosts — expect
   to stop at condition 6.1 with the blocker list, not at "all nine
   done".
