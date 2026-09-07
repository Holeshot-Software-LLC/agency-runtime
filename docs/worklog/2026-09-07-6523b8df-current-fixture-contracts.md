---
title: "Align current evidence and trust fixtures"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [testing, evidence, security, backlog]
related:
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
  - docs/roadmap/acceptance/evidence/AR-176-fixture-contracts-20260907.md
  - docs/roadmap/handoffs/issue-AR-404.md
supersedes: []
superseded_by: null
type: worklog
commit: 6523b8dfc8071c12b843f29555d551b3be0b0c74
short: 6523b8df
date: 2026-09-07
pr: null
related_issues:
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
---

# Worklog detail: test(runtime): align stale evidence and trust fixtures

## Purpose

Make the six carried stale cases test today's intentional runtime behavior
rather than restore removed fallback, public-delegation or retry policies.

## Approach

Repair three test boundaries: native event evidence, POSIX Store trust and
public routing. Preserve real ACL, owner, inode, link, replay, operator-prompt
and no-implicit-turn protections. No Python product changes.

## Challenges encountered

All six original cases fail on unchanged tests. The first repaired run passes
five, then the public-route case reaches another stale coordinator-seeding
expectation. Current inference-only policy makes that installation a no-op.
After correction all six pass in 2.30s.

The subsequent combined 14-module run reports 466 passed, one existing skip,
64 Windows-named deselections and one failure in 77.40s. The failing historical
installer fixture records cleanup instead of actually removing its stage;
the hardened product now detects that retained stage. Baseline reproduction
and a faithful cleanup double are the next bounded fix, not a runtime rollback.
This combined package is not green.

## Decisions and alternatives

Existing ADR-0105 and ADR-0224 govern bounded checks. Keep historical exhaustive
results as history, preserve the 97-percent floor, and do not dispatch an
unrequested exhaustive workflow. Source authority takes precedence over stale
agent-written expectations.

## Verification

Six repaired cases pass, focused lint/format and diff checks pass.
Combined package failure is explicitly recorded above. No new acceptance
verdict, aggregate coverage result or native activation is claimed.

## Follow-ups

Finish the combined fixture package, native output diagnostics, bounded
acceptance and normal PR/merge. Continue oldest-first until the owner's cutoff.

## Source checkpoint

6523b8df (6523b8dfc8071c12b843f29555d551b3be0b0c74) retains both focused red stages and the passing six-case repair. The combined installer fixture failure is preserved as unfinished work.

## Current complete package

49b307ff (49b307ff3ae7d248bee0b7135d5b0843daa9b1de) repairs the main-reproduced retained-stage fixture using real guarded cleanup. Seven focused cases pass; combined package 467 passes/one skip/64 Windows-named deselections, named spine 1085/three skips, UI 224/current floors and Node smoke contracts 36 pass. Existing ADR-0105/0224 reconcile only obsolete exhaustive gates; faithful July criteria and red diagnostics remain. Runtime bytes equal the AR-175 installed artifact source a96483ad.

## Frozen current candidate

9a42c162 (9a42c1627e4cd6bd6002833c83b093ba6c72c6a7) freezes eight builder-only criteria at 49b307ff. Dry-run checks confirm every cited excerpt is included (1,512–16,303 characters per packet). The original verdicts have not run yet. AR-388's documented owner-private client environment exists and contains the configured variable; this changed precondition permits a new bounded native check without provisioning or persisting a key.

## First isolated review preserved

969f7190 (969f7190266cdfcfaaed5968a74ddb7983d68273) records five satisfied criteria and three unresolved evidence findings (2 absent, 3 contradicted, 7 absent). Do not erase those verdicts or mark done. Review each exact reason and fix only a justified current-contract/evidence gap before the second/final pass.

## Bounded review correction

5df50bc1 (5df50bc1099ca843758fa840e30c545ffd8a5197) makes the two argv doubles require and compare executable-namespace inputs and preserve roots identity through freezing. Sixty focused service/real-Store activation checks pass. Queue-cache isolation is not claimed as full authority proof; the final packet must include the original six-failure summary. Acceptance wording and production runtime remain unchanged.

## Final reviewed candidate

8b4c1fca (8b4c1fca2205e3132133e6ecc4c4ef62238bc653) seals the current 15-module run (525 passes, one skip, 64 Windows-named deselections; 84.33s), fresh named spine (1085 passes, three skips; 72.16s) and strict records. Prior UI and Node contracts remain unchanged. The final isolated review will rerun all eight criteria at this new candidate; first verdicts remain at 969f7190.

## Final verification packet

201d0cfc (201d0cfc8ba1578b3eaf52dd35d94c8a6a3112be) binds all eight criteria to 8b4c1fca. All cited excerpts fit after dry-run validation; real Store authority replaces the deliberately isolated cache helper, and the exact six-failure summary is present. This is the second/final independent pass, not an erased first review.

## Second and final isolated review

4a7b155d (4a7b155d15a245b88fe9f44a06f3ec0060671b15) records six satisfied criteria. Criterion 2 remains absent because the packet does not enumerate every relevant original double and production argument; criterion 5 remains absent because it does not include the historical changed-module inventory. These are explicit traceability limits, not failed runtime tests. No third independent review is authorized by the default bounded workflow. Publish the seven repairs and stronger argument checks while retaining AR-176 in_progress, with these exact remaining criteria.

## Publishable retained disposition

b4edca75 (b4edca75f6e0a6c29fc9f3734997d68031688c59) retains AR-176 in_progress with six accepted/two absent criteria and publishes the actual native findings: Codex current-profile v4 activation passes at 22:04:41Z; OpenClaw ordinary staffing and five-field output pass, with limited prompt augmentation evidence; Hermes/Claude failures are traced to timed/invalid inference rather than assumed missing credentials. Existing client credential reuse is child-only, with no persistent credential or trust changes. Queue remains 119. Next after normal merge is AR-177.
