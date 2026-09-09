---
title: "AR-404 native terminal repairs and remaining gates"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-09
tags: [handoff, hermes, openclaw, live-evaluation]
related:
  - docs/roadmap/issue-AR-418-preserve-hermes-truncation-terminal-evidence.md
  - docs/roadmap/issue-AR-419-finalize-openclaw-cli-responses.md
  - docs/worklog/2026-09-08-hermes-openclaw-native-refresh.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/acceptance/evidence/AR-404-codex-roundtrip-20260908.md
  - docs/roadmap/acceptance/evidence/AR-404-final-installed-evaluation-20260907.md
  - docs/worklog/2026-09-08-codex-launch-roundtrip.md
  - docs/roadmap/issue-AR-413-preserve-http-status-in-staffing-receipts.md
  - docs/worklog/2026-09-08-fresh-codex-activation.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-404
branch: codex/ar404-terminal-reliability-20260909
evidence_commit: faf5645a6e7b9c86b15d6caad52b7ddbea6f032a
minimum_ledger_commit: 22f24eddeb5fc43a017c7d774f2fd14d1b727988
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 native reliability checkpoint

## Checkpoint

Current callback sourcefaf5645a/artifact22f24edd is installed,616exact files.
Focused131, production1151/3skip, UI224 and conformance188/188 pass. Three fixed
Hermes requests now enter the live_demo phase once each; no old receipt retries.

Active owned branch codex/ar404-terminal-reliability-20260909 starts at clean
synchronized c6c3e7b5. AR-426/#823 owns the new Hermes native hook-spill repair,
separate from AR-418 output truncation. Recipe18 refinement follows a failed tool-only native phase: models skipped
retrieval. Native ordered per-card callbacks now retrieve before the model runs;
131focused tests pass. Revised fast validation and native proof are pending.
Fast production1151/3skip, UI224, conformance188/188 and canonical616file
installation pass. Hermes native demo follows; other host projections unchanged.
Exact baseline: AR-426-exact-native-spill-and-terminal-audit-20260909.json.
Fresh Codex8/8trusted; process2200222 runs published6db15efbecbe, MCP responds,
classifier6,615installed files match prior wheel. Handoff trace01a086f4 is failed
staffing/classifier5 and has no finalization event; transport failure is separate.

## Completed evidence

Fixed ordinary review, same-session "go for it", and multi-step correction run
once each per host under360s cap. Full records are
AR-404-{host}-suite-after-planner-context-20260909.json; summary is
AR-404-planner-context-results-20260909.json. Result8/15:
Codex3/3, Claude2/3, OpenClaw2/3, Zcode1/3, Hermes0/3. Every failure retained.
Hosts ran sequentially; isolated acceptance could overlap, so durations are not
a controlled speed benchmark. No delivery, external messages or manual finalization.

Separate Claude full-card session545f5ca7-2937-412f-a9be-6b4e4c665204,
tracedf374667-2599-4798-a852-1e6f972aed25,239.508s, passes4exact native MCP cards,
five Store fields and authoritative accepted hash
f9b78ee4a8b0fd116e18fcffa0a9328ba67ff1b102586bf387f94845583f423b.
First planner reply rejected, one repair applied, independent critic applied.
Native proof: AR-404-claude-large-context-after-planner-context-20260909.json.
The original two-rejection Claude tracebe4757dc remains failed; exact second
semantic cause unknown. A new planner-only diagnostic reproduced the first
missing correctness review but its repair succeeded before the source change.

Fresh Codex hooks/list after owner review:8/8trusted,0modified/missing/duplicate.
Parent process still runs stale projection6e7dc299c23e; its MCP transport failed
on prior turns. Reinstall does not refresh a running process. Fresh native Codex
cases supply evidence, not the parent. Prior session01a08200-6530-79a3-a19c-4fb24b1983ae,
trace01a082b9-e7df-70e2-b76c-b8be7e01ad5a remains a separate failed staffing receipt.

## Exact blocker

Hermes review fails independent assurance; follow-up and multi-step fail terminal
validation with all five fields missing. Default native source7cd91114 unchanged;
upstream PR106490 remains OPEN at30f421ecce, complete patch retained under AR-418.
No upstream merge authority; installed adoption and original truncation cap remain
unproved. A version banner naming upstreambf53ff00 is not the checkout identity.

Zcode0.16.5 is installed/available, uses normal build mode and existing answering
configuration. Review/follow-up have exact cards and matching final headers but
earlier invalid terminal receipts; multi-step passes. Do not reopen failures.
Claude ordinary review and OpenClaw follow-up fail staffing; inspect exact receipts
before choosing a repair, never assume a critic veto is erroneous.

AR-423 native full-card gate passes but isolated closure is pending. Two review
passes retained absent criteria1/2: an orphan builder row omitted the pointer and
whole-file excerpts omitted later card rows. Corrected contiguous bounded packet
is prepared; local build_case proves the needed excerpts are included. No third
pass in this package under the repository's two-pass default.

## Same-task continuity

Continue the same user task. Preserve unrelated work and Windows items. At or
below50percent, commit the smallest substantive/ledger checkpoint and continue;
no empty checkpoint or forced transfer. Main synchronization and exact PR merge
records belong to this package, not a later optional cleanup.

## Next bounded work package

Complete AR-426 focused/fast validation, canonical install, affected Hermes native
card/header/terminal demo, then isolated acceptance and owned PR merge/worklogs.
No native spill/output budget changes. Zcode first outputs put permission prose
before headers; old terminal rejection is valid. No raw failed staffing selection
is retained, so critic correctness is unknown and its authority stays unchanged.
AR-423 third isolated pass question is pending; elapsed time is not authorization.
Hermes upstream PR106490 remains open at30f421ecce, default checkout7cd91114.

## Verification

Focused143pass, Claude context12pass, production1151pass/3skip, UI224pass,
Ruff/metadata/policy/worklog/routing/docs/tracker checks pass. Frozen conformance
188/188, no invalid/survived mutations. First baseline fixture failure under002
umask retained; rerun077 passes with unchanged source. Canonical build and smoke
pass, all615installed files match. No exhaustive workflow or Windows matrix.
AR-425 second isolated verdicts8862f6fa/d5fb19d3/e006aacb/1c0fa05a all satisfied;
first absent verdict retained. See 2026-09-09-planner-repair-context worklog.

## Constraints

Inference alone selects staff. Preserve independent critic, validators, caller
scope and trust. No manual specialists, extra retries, manual failed-receipt
acceptance or external messages. Keep Claude and Zcode explicitly in scope.
Use owned worktree -> PR -> merge and exact worklogs. Close only evidenced scopes.
