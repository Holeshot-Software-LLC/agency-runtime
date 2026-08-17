---
title: "Overnight autonomous brief for the AR-119 remaining stages"
status: draft
category: roadmap
created: 2026-08-16
updated: 2026-08-16
tags: [roadmap, handoff, autonomous, AR-119, AR-255, AR-253, AR-258]
related:
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/roadmap/AR-119-founding-vision.md
  - docs/roadmap/AR-255-child-parity-design.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/roadmap/AR-119-rule-host-evidence-matrix.md
supersedes: []
superseded_by: null
type: reference
issue_id: AR-119
---

# Overnight autonomous brief

The prompt below is written to be pasted into a fresh session that runs
unattended. It is kept in the repository so the next session can read it after a
compaction rather than depending on chat scrollback.

## What this brief can and cannot deliver

Stated first because the prompt must not promise what the machine cannot do.

- **Reachable overnight:** claude, codex and zcode — install parity, the AR-255
  child-parity work, repeated canary series, and honest matrix updates for those
  three hosts.
- **Not reachable overnight:** openclaw and hermes are not installed on this box
  and the owner has asked that they not be installed. Their Installed and Live
  cells therefore **cannot** go green here. The most that is honest is to leave
  them provably ready for the owner's own boxes to verify independently.
- **Rule 9 cannot close.** It requires rules 1–8 proven on all five hosts. Two
  hosts are out of reach by construction, so any claim of a completed vision
  overnight would be false.

---

## The prompt

~~~text
You are continuing AR-119 for the repository at
C:\Workspaces\Holeshot Software\agency-runtime, unattended, overnight. The owner
is asleep and will read your report in the morning. Work continuously until the
acceptance list below is satisfied or you are genuinely blocked on something only
he can do.

WORK IN A WORKTREE, ON A BRANCH. NEVER ON MAIN.
  git -C "C:\Workspaces\Holeshot Software\agency-runtime" worktree add \
      ../agency-runtime-overnight -b overnight/ar119-vision-stages
Do all work in that worktree. Commit there, push that branch, and NEVER push to
main, merge to main, or commit in the primary checkout. Merging is the owner's
morning decision -- a bad night must not be able to reach main.

The primary checkout also holds his uncommitted WIP (see ENVIRONMENT TRAPS); a
worktree keeps you away from it, which is the second reason for this rule.

WHAT A WORKTREE DOES NOT ISOLATE -- know this before you install anything:
  - `~/.agency-runtime/agency.db` is machine-global. Every canary you run writes
    to his live store. That is expected and matches how tonight's runs worked.
  - Installed launcher projections are machine-global. Installing from the
    worktree republishes the host hooks to run YOUR BRANCH's code. The projection
    is a self-contained copy, so removing the worktree does not break it.

HE MUST WAKE UP TO A KNOWN-GOOD RUNTIME. This is a hard requirement.

You cannot avoid installing branch builds: host canaries execute the INSTALLED
projection, not the checkout, so branch code cannot be measured on a host any
other way. So install freely while you work, and then:

  1. RESTORE MAIN'S BUILD AS YOUR FINAL ACTION, for every host you touched:
       cd "C:\Workspaces\Holeshot Software\agency-runtime"   # primary, on main
       git status --short          # confirm main, and leave his WIP alone
       python -m agency_runtime.cli install --agent claude
       python -m agency_runtime.cli install --agent codex
       python -m agency_runtime.cli install --agent zcode
     Then VERIFY it took: read `~/.agency-runtime/launchers/current-<host>.json`
     and confirm the digest matches a fresh install from main, not your branch.
     Do not claim the restore; check it.

  2. KEEP A RUNTIME STATE FILE, updated immediately after EVERY install, at
     `~/.agency-runtime/overnight-runtime-state.json`:
       {"host": ..., "digest": ..., "branch": ..., "commit": ..., "at": ...,
        "is_main_build": true|false, "restore_command": "..."}
     Write it after the install, not before. If you crash, time out, or run out
     of budget mid-night, this file is the only thing that tells him what his
     hooks are actually running. Assume you will not get to say goodbye.

  3. If you are ever about to idle for a long stretch, restore main's build
     first and reinstall the branch when you resume. An unattended machine
     should sit on main's build by default.

EVIDENCE PRODUCED ON BRANCH CODE IS BRANCH EVIDENCE.
Every matrix cell you green must record the runtime digest AND the commit that
produced it. A cell proven by unmerged branch code is PROVISIONAL -- mark it so
in the matrix and in the report. It becomes real when he merges, not when you
measure it. Do not let a provisional cell read as proven; that is the exact
failure this matrix has already recorded three times.

READ FIRST, BEFORE ANY OTHER ACTION
  1. docs/roadmap/handoffs/issue-AR-119.md      (the capsule)
  2. docs/roadmap/AR-119-founding-vision.md     (what the product is FOR)
  3. docs/roadmap/AR-255-child-parity-design.md (the next change, already designed)
  4. docs/roadmap/AR-119-overnight-autonomous-brief.md (this brief)
Re-read items 1 and 2 IMMEDIATELY after every compaction, before resuming work.
That re-read is not optional and is the single thing that stops a fifth wrong
diagnosis; the capsule is what a compaction drops first.

HOW YOU WORK

Adversarial review at every checkpoint. Before you record any finding, attack
it: state what the evidence excludes, what it does NOT establish, and what
observation would refute it. When a later run refutes an earlier claim, retract
it by name in the doc rather than quietly moving on. Four diagnoses on this
staffing failure have already died this way -- ranking order, eligibility,
coverage, and the child's candidate universe -- each because a field was scored
over a WIDER set than the code actually searches. Ask, every time: which exact
set is this claim scored over?

Ledger flow, unchanged except for the branch. Conventional commits ending
"Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>". Findings go in the repo
docs, never only in your reply. After every substantive commit run
`python scripts/update_worklog.py` and commit the result as a SEPARATE
`docs(worklog):` commit. `python scripts/verify_docs.py` must pass before every
push. The active handoff capsule has a HARD 180-line cap -- keep edits
line-neutral by swapping content out, never by appending.

Do not stop to ask questions. There is no one to answer. Where you would
normally ask, instead: make the call, write the decision and its falsification
condition into the relevant doc, and list it under DECISIONS TAKEN in your
morning report. Never halt at a milestone.

STANDING AUTHORIZATIONS FOR THIS RUN
Granted by the owner and EXPIRING AT 08:30 LOCAL ON 2026-08-17, when he returns.
  - Push the overnight BRANCH to origin, repeatedly. Never main.
  - `python -m agency_runtime.cli install --agent <host>` from the checkout.
  - Run host canaries and inference-spending series as needed.
  - Use the Codex hook-trust bypass (see Stage 4).
  - Wire the child assignment into the existing owner-gated content capture, so
    a decline can finally be read against what the child was actually asked.
    CONDITIONS, all mandatory: it must pass through
    `agency_runtime.core.content_redaction.redact_content`, which bounds it to
    MAX_CAPTURE_CHARS and strips keys, tokens, JWTs, emails and card numbers; it
    must stay gated on `observability.capture_content` and must NOT change that
    flag's value; and it must be local storage only, never transmitted anywhere.
    Record in the morning report that child assignments are now being captured,
    so he can decide whether the wiring stays.
Nothing else is authorized. You may NOT: run `claude auth login` or any
re-authentication, install openclaw or hermes, open PRs, write to the tracker,
tag, release, or change repository settings.

ENVIRONMENT TRAPS -- these are known, do not rediscover them
  - Prepend C:\agency-cli to PATH or hosts read "native unverified".
  - The packaged `agency.exe` is pinned at SCHEMA_VERSION 45 and REFUSES to
    install against the schema-46 store. Always install with
    `python -m agency_runtime.cli install --agent <host>` from the checkout.
  - Claude isolated-profile canaries need an explicit `--timeout 420`. The
    undeclared 120 s default kills a cold profile mid-turn.
  - `tests/test_platform_wheel.py` fails to collect (no setuptools). Pre-existing
    machine noise; ignore it.
  - EIGHT tests are red on main in the preflight/litellm area and are NOT in any
    gate: test_configuration_identity (2), test_coverage_final_host_cli,
    test_http_server, test_http_server_coverage_complete, test_litellm_callback,
    test_litellm_hardening, test_litellm_reconciliation. Verified pre-existing by
    stashing. Do not attribute them to your changes; fixing them is optional and
    lower priority than the acceptance list.
  - The PRIMARY checkout has the owner's WIP: agency_runtime/cli/eval_commands.py
    is modified and captured_raw_responses.json, raw_responses_latest.json,
    workforce_eval_output.json are untracked. Working in the worktree keeps you
    clear of them. Never commit, revert or stash them, and never `git stash` in
    the primary checkout. Stage only your own files, by explicit path.
  - The pre-push hook runs `scripts/run_local_gates.py --fast`, which SKIPS the
    production spine because that gate is marked slow. Run the spine yourself
    before each push: `python -m pytest <PRODUCTION_SPINE> -q -W error`, reading
    the list from scripts/run_local_gates.py. A green push is not a green spine.

REFUTED -- do not re-chase these
  - Recruiter ranking ORDER is not the fault; code-reviewer ranks first.
  - Candidate ELIGIBILITY is not the fault; top_ranked_ineligibility is absent.
  - Requirement COVERAGE is not the fault; the axis is absent when scored over
    the executable ranked set.
  - The child's UNIVERSE is not the fault; code-reviewer is offered every time.
  - Child task SIZE is not the fault; declines at 541 and at 2,408 characters.

MEASUREMENT DISCIPLINE
Parent staffing is INTERMITTENT (observed red, red, green, green, green, green,
red, green). The child judge has declined 10 of 10. Therefore:
  - One green run proves nothing. Measure rates over a series of at least 3 runs.
  - Keep every failure; never retry-until-green, which turns a rate into a
    best-of.
  - Compare decisions-to-declines, not runs-to-runs: one observed run spawned six
    children and would otherwise dominate the rate.
  - A harness already exists at the path recorded in your scratchpad notes; if
    absent, rebuild it to these rules.

THE WORK, IN ORDER

Stage 0 -- FIRST, AND MOST IMPORTANT: sweep all nine rules, not just Rule 4.
  The owner has to deliver this vision soon, so the objective overnight is CELLS
  PROVEN, not one blocker chased to ground. A full session was just spent on
  Rule 4 alone. That was a mistake of focus and you must not repeat it.

  Read docs/roadmap/AR-119-rule-host-evidence-matrix.md. Every Installed and
  Live cell is `unproven` for every rule on every host -- 0 of 45 each. But the
  PARENT staffing path demonstrably works: it accepts routing decisions, selects
  specialists, writes `specialists_loaded`, and correlates receipts. Several
  rules are parent-side and may already be provable from evidence the runs you
  are about to do will produce anyway:
    - R1 "inference receipt joined to exact delivered card hashes" -- parent side.
    - R2 "native primary-caller artifact containing selected cards before first
      caller speech" -- parent side. The parent loads cards on nearly every turn.
    - R3 the same, with two or more compatible cards in one turn.
    - R6 contractor hiring -- OBSERVED LIVE tonight: `request-intake-analyst` was
      minted mid-run and the child universe grew 66 -> 67 in flight, with the
      offered digest moving f34c49c2566f -> b5b83ecc699e. Nobody captured that as
      Rule 6 evidence. It may already be sitting in the store.
  Only R4 requires the child judge to cooperate, and that is the one thing that
  has resisted all day.

  So: before touching P2, enumerate for each rule R1-R8 what its Installed and
  Live acceptance actually demands, and mark which are reachable WITHOUT the
  child judge. Collect those first. This is a lead, not a proven claim -- verify
  each rule's acceptance criteria against the matrix rather than assuming a
  parent turn satisfies it, and record any rule you find is NOT reachable that
  way, with the reason. If the lead is wrong, saying so is worth more than a
  cell claimed on a criterion you did not actually read.

  Never mark a cell proven on a Store row or model prose alone. The matrix's own
  rule stands: an installed or live result counts only when its host artifact
  supports it.

Stage 1 -- AR-255 P2: one funded repair before a child abstention is final.
  Designed in docs/roadmap/AR-255-child-parity-design.md; P1 already shipped.
  On an empty selected_ids from the child judge, make exactly ONE more inference
  call, then accept the answer. CRITICAL CONSTRAINT, which must survive your own
  review: the repair asks the judge to TEST ITS OWN ABSTENTION against the
  concrete candidate set. It must never instruct the model to pick something. A
  repair that says "choose one" converts honest abstentions into forced
  selections and puts deterministic code back in charge of staffing, violating
  ADR-0118. Record first-pass and post-repair abstentions under DISTINCT reason
  codes, or the next measurement cannot tell whether the repair did anything.
  Accept: unit tests green, full production spine green under -W error, install,
  then a 3-run series measured to the rules above.

Stage 2 -- Re-measure claude and update the matrix honestly.
  If the child staffs even once, native_child_delivery_verifications gets its
  first row ever; capture it and update
  docs/roadmap/AR-119-rule-host-evidence-matrix.md for claude only.
  If it still declines across the series, P2 is refuted for the child: say so in
  AR-255 by name, and record that the remaining instrument is the owner-gated
  observability.capture_content pointed at the child assignment. DO NOT enable
  or repoint content capture yourself -- that is the owner's call and is listed
  under MORNING DECISIONS.

Stage 3 -- Codex.
  Codex is stale at projection 530f6df6c4b6, several behind, which breaks
  AR-258's one-digest property. Install it from the checkout.
  The owner has explicitly authorized the hook-trust BYPASS for tonight, which
  the capsule otherwise forbids. Use it -- and be scrupulous about what it means:
  any evidence produced under it carries trust_bypass_used: true, it is NOT
  attended trust, and it must NOT be recorded as satisfying an attended-trust
  acceptance criterion. Label every codex cell it produces as bypass-derived in
  the matrix and in your report. If a result would only be green under bypass,
  say exactly that.

Stage 4 -- zcode.
  zcode is stale at 980eb2d1b755, two projections behind. Install from the
  checkout and drive it through the zcode CLI. ADR-0087 treats zcode as using
  the same hook model as codex/claude, so specialists declaring codex or claude
  are eligible there. Run the same canary series discipline.

Stage 5 -- Claude in a separate CLI session.
  The parent-staffing measurements so far come from isolated-profile canaries.
  Drive a separate `claude` CLI session against the real profile as an
  independent reading. Note that a session started BEFORE an install keeps
  calling the old launcher -- the cure is a restart, never another install.

Stage 6 -- openclaw and hermes, without installing them.
  They are absent from this box and you may not install them. Do NOT fabricate
  or infer their cells. Instead produce, in the repo, a single self-contained
  verification packet the owner can run on his own boxes: the exact commands,
  the expected evidence rows and their acceptance conditions, and the digest of
  the runtime they must be running to be comparable. State plainly in the matrix
  that both hosts remain unproven here and why.

PRIORITY, IF YOU RUN SHORT OF TIME
Order by cells proven per hour, not by how interesting the problem is:
  1. Stage 0's nine-rule sweep on claude -- likely the largest single gain.
  2. Stage 3/4 installs, so codex and zcode share one digest and the same sweep
     can be repeated on them.
  3. P2, which unlocks R4 only.
  4. Everything else.
If you must choose, three hosts with several rules proven beats one host with
Rule 4 proven. Say in the report which you chose and why.

ACCEPTANCE -- you are done when all of these hold
  [ ] Every rule R1-R8 assessed for Installed/Live reachability without the
      child judge, with the unreachable ones named and justified.
  [ ] P2 implemented, tested, installed, and measured over >= 3 runs.
  [ ] claude, codex and zcode all running the SAME runtime digest (AR-258).
  [ ] The matrix reflects measured reality for those three hosts, with every
      bypass-derived codex cell labelled as such.
  [ ] openclaw and hermes have a runnable verification packet and are recorded
      as unproven here.
  [ ] Every finding carries its falsification condition.
  [ ] Worklog regenerated and docs validation passing; the overnight branch
      pushed, main untouched, nothing committed in the primary checkout.
  [ ] The capsule is current, still <= 180 lines, and points a fresh session at
      the true remaining blocker.
  [ ] MAIN'S BUILD IS INSTALLED for every host you touched, VERIFIED by reading
      the current-<host>.json digests -- not merely reinstalled and assumed.
  [ ] `~/.agency-runtime/overnight-runtime-state.json` reflects that final state.
  [ ] Every branch-derived matrix cell is marked provisional.

MORNING REPORT -- write it to docs/roadmap/AR-119-overnight-report.md and commit
  1. What is now PROVEN, with the run ids and digests that prove it.
  2. What is now REFUTED, named, including any of your own claims.
  3. DECISIONS TAKEN in his absence, each with the falsification condition.
  4. MORNING DECISIONS he must make, phrased as concrete choices.
  5. What is still blocked and exactly whose hands it needs.
  6. Anything you did that carries a caveat -- especially every codex result
     obtained under the trust bypass.
  7. The branch name and head commit; confirmation that MAIN'S build is what is
     installed right now, with the verified digest per host; which cells are
     provisional pending merge; and whether child assignments are now being
     captured. He merges; you do not.

Open the report with one line stating what runtime his machine is on. That is
the first thing he needs and the thing most likely to be wrong.

Do not overstate. If the child judge still declines after P2, the correct report
says the vision did not complete overnight and names precisely why. That is a
better morning than a green board that does not survive his first question.
~~~
