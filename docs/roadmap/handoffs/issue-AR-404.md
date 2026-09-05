---
title: "AR-404 evidence-led backlog completion handoff"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [handoff, backlog, acceptance, delivery]
related:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/AR-404-backlog-dispositions-20260905.md
  - docs/roadmap/AR-404-backlog-inventory-20260905.md
  - docs/roadmap/issue-AR-271-accept-stopped-openclaw-uninstall-status.md
  - docs/roadmap/acceptance/issue-AR-271.md
  - docs/roadmap/acceptance/evidence/AR-271-installed-delivery-20260905.md
  - docs/roadmap/acceptance/issue-AR-405.md
  - docs/roadmap/acceptance/issue-AR-285.md
  - docs/roadmap/handoffs/issue-AR-400.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-404
branch: codex/ar271-installed-delivery
evidence_commit: 5434836eec4efe70432e50ca3c732dc65c63e209
minimum_ledger_commit: 0fc41acceda567017f5c7f2054218c38a52514e9
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 evidence-led backlog completion handoff

## Checkpoint

The owner asked to push and continue the backlog. Prior record cleanup is on
main via PR #676/#677 at 3ed51069. AR-405 is pushed and merged through PR #678
at 78e501b7; #675 is closed. AR-271 is accepted and merged through PR #679 at
5434836e. Its exact non-editable package is installed; the previous launcher
and environment are retained. No implementation agents were delegated.
Umbrella: implementing. The bounded stopped-uninstall contract is done;
installed-source smoke passes and remaining native gates stay explicit.

## Completed evidence

- Frozen baseline: 155 unfinished records. AR-400/401/402/403 accepted closures
  left 151; four obsolete contracts AR-132/167/169/267 retired through cited
  successors left 147. AR-405 was newly filed outside the baseline and is now
  done. With AR-271's accepted closure, 146 baseline items plus AR-404 remain
  unfinished (147 current records).
- AR-400..403 fixes: PR #669 at 1de05aea, immutable installed build, projection
  349f1ae7fc74; twelve satisfied isolated criteria. Earlier AR-397/398/399
  bookkeeping reconciled #654/#670/#671. Native evidence remains scoped below.
- First semantic batch: preserve historical criteria, retire only obsolete
  policies, and use ADR-0219 for the current paired no-helper release contract.
  AR-160 keeps actual cross-OS producer proof. Original inventory is not a
  claim that every remaining item has been semantically reviewed.
- AR-285: exact parent/current replay proves the original classifier repair,
  with eleven negative/legacy cases. Isolated criteria 1/3/4 satisfied, 2/5
  absent. Needs actual trusted-runner wiring citations and a successful
  changed-precondition dry-run receipt; historical installs do not supply both.
  No gateway lifecycle change was performed to manufacture those receipts.
- AR-405: red Linux build file 91 pass/two fail, fixed 100 pass/one native-only
  skip. Portable real I/O and object/kind replacement stay active; synthetic
  Windows volatile attributes are covered without a Windows claim.
  Wider files 452 pass/three skips; fast spine 1004 pass/three skips; UI 138.
  Three isolated criteria satisfied against 593f074f. Protected umask 077
  conformance passed baseline and killed 182/182, source unchanged. The initial
  ambient 0002 private-boundary failure is retained, not relabeled.
- AR-271: offline production replay returns install=False/uninstall=None for
  the same stopped/inactive/dead exit-1 receipt. Regression-first tests:
  seven fail/fifteen pass. Production now extracts the existing install
  classifier and imports it in uninstall; command runners and authority remain.
  Focused installer/uninstall/CLI suite: 248 pass/two Windows-only skips (7.38s).
  Named fast spine: 1030 pass/three skips (63.79s), UI 138, Ruff/format pass.
  Tests cover registered/already-detached plugins, write-free plans, retained
  byte equality, owner denial, launcher/environment/revalidation drift and
  live/unknown state after approval or immediately before commit.
  All three isolated criteria are satisfied against 4fdcd6a7 (runs aaea78e6,
  b9ab27a1 and dc532503). Protected conformance passed baseline (99.682s), killed
  all 182 mutations and preserved source. Routing and 104 docs/acceptance/tracker
  tests pass; strict tracker parity passes. PR #679 is merged; no live uninstall
  is claimed.
- Installed delivery: build 0.1.0+g5434836eec4e, projection 1d617ca589a2.
  All eight deterministic smoke checks pass, including five host contracts.
  Native refresh is partial: Claude/Hermes/ZCode registered/enabled, Codex
  requires attended hook trust, OpenClaw is live and was not replaced.
  Installer-managed dashboard restart succeeded and fourteen Claude package
  permissions were repaired under recorded consent. Claude readiness passed,
  but a presence-only check found this shell lacks configured LITELLM_API_KEY;
  no current-build live canary was attempted or claimed.

## Exact blocker

No code blocker for AR-271. Its real stopped receipt is now handled in tests;
isolated acceptance, final verification, merge and installed smoke are complete.
Native activation still needs the host/operator steps below. The package does
not authorize a real host uninstall, gateway stop/restart, or native trust bypass.
AR-285's historical receipt gap is separate and remains open.

The entire backlog is not complete. AR-348 still has no production enforcement
of actual creator/reviewer independence: the prior fake-response replay hired
on one provider despite strict_independence=true. AR-349 still discards the
rejected safety-repair case; its old test asserts hiring_case is None.
AR-350 is an unresolved owner-authority choice, not permission to remove gates.

## Same-task continuity

Reuse this owned worktree on its branch; never commit main directly. Each
substantive commit gets its immediately following narrow docs(worklog) ledger.
AR-271's frozen candidate remains 4fdcd6a7 with its three satisfied isolated
Codex verdicts; do not rerun them for delivery-only records. Its earlier Claude
verifier transport failed namespace trust. The later install reports a bounded
package repair, not proof that every parent-namespace check is now satisfied.
No manual credential, trust or provider-policy repair was performed.

The installed runtime is pinned to main 5434836e, not the editable worktree.
Current acceptance candidate and merged runtime/test/tool sources are identical.
Delivery-only records need strict docs/tracker/ledger checks, not another slow
source-identical spine or conformance run. Complete their PR and merge ledger.

## Next bounded work package

1. Finish the installed-evidence PR/merge ledger, preserving partial native
   refresh and the exact build. AR-271 source and acceptance are already done.
2. Verify implemented inspection work AR-298; reconcile AR-337 four-host
   battery scope and AR-351's obsolete domain-axis clause before implementation.
3. Deliver AR-348/349 genuine hiring-safety fixes with legacy, per-harness,
   fallback and safety-repair coverage; retain the AR-350 product decision.
4. Continue AR-253 quality/latency evidence and reconcile AR-393's impossible
   retroactive-receipt requirement without rewriting history.

## Verification

Named fast spine and focused changed-path tests are mandatory, not exhaustive
coverage or the full interpreter matrix. Decision conformance uses a protected
umask 077 process workspace; ambient 0002 failure is already documented under
AR-297. Strict docs/tracker and exact ledger checks govern parity. Isolated
criterion verdicts gate done, not the builder's checked boxes.

## Constraints

Codex's installed hooks are refreshed, but attended trust of eight hooks in a
fresh terminal TUI remains unverified. An existing process can retain old hooks.
OpenClaw update needs gateway stop/restart consent; Hermes/ZCode need supported
ordinary-session proof. Claude needs the existing configured credential in its
live environment; the earlier 16:51Z child pass belongs only to 1de05aea.
Never transfer proof across builds. Beyond the installer-managed dashboard
restart, no service interruption is implied; no credential creation, provider
policy change, publication or exhaustive dispatch is authorized by this package.
Never mark AR-404 done while any baseline item remains unaccounted for.
