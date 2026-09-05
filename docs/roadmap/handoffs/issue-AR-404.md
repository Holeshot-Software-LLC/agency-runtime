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
  - docs/roadmap/acceptance/issue-AR-405.md
  - docs/roadmap/acceptance/issue-AR-285.md
  - docs/roadmap/handoffs/issue-AR-400.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-404
branch: codex/ar271-stopped-uninstall
evidence_commit: 4fdcd6a7b1ff3ae3ab8a666937adeb5d1111895b
minimum_ledger_commit: c998f6f5f1a78b0d676e95561de651b0479482c6
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 evidence-led backlog completion handoff

## Checkpoint

The owner asked to push and continue the backlog. Prior record cleanup is on
main via PR #676/#677 at 3ed51069. AR-405 is pushed and merged through PR #678
at 78e501b7; #675 is closed. Its merge ledger is the first commit of this
AR-271 branch. No implementation agents were delegated. Umbrella: implementing.
Current bounded outcome: allow ownership-bound uninstall from a proven stopped
OpenClaw receipt while preserving all last-moment safety checks.

## Completed evidence

- Frozen baseline: 155 unfinished records. AR-400/401/402/403 accepted closures
  left 151; four obsolete contracts AR-132/167/169/267 retired through cited
  successors left 147. AR-405 was newly filed outside the baseline and is now
  done: 147 baseline items plus AR-404 remain unfinished (148 current records).
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
  Isolated acceptance, final conformance, PR delivery and installed smoke are
  the remaining steps in this package, not claimed completed.

## Exact blocker

No code blocker for AR-271. Its real stopped receipt is now handled in tests;
acceptance and delivery are pending. The package does not authorize a real
host uninstall, automatic gateway stop/restart, or native trust bypass.
AR-285's historical receipt gap is separate and remains open.

The entire backlog is not complete. AR-348 still has no production enforcement
of actual creator/reviewer independence: the prior fake-response replay hired
on one provider despite strict_independence=true. AR-349 still discards the
rejected safety-repair case; its old test asserts hiring_case is None.
AR-350 is an unresolved owner-authority choice, not permission to remove gates.

## Same-task continuity

Reuse this owned worktree on its branch; never commit main directly. Each
substantive commit gets its immediately following narrow docs(worklog) ledger.
Freeze AR-271 acceptance to its implementation/evidence commit before running
the supported Codex excerpt-only verifier. Claude verifier transport remains
unavailable because its executable parent namespace is substitutable; no trust,
permission, credential or provider repair is authorized by backlog cleanup.

Runtime remains pinned at 1de05aea until this runtime change is merged. Then
install an exact non-editable main build, retain the old launcher/environment,
refresh integrations and run deterministic all-host smoke. The previous
test-only AR-405 merge did not require a new runtime payload.

## Next bounded work package

1. Complete AR-271 verification, isolated acceptance, PR/ledger merge and
   exact installed-source smoke. Keep failures and host-specific exits visible.
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

The current-turn Codex install refresh found installed files current, but
attended trust of eight hooks in a fresh terminal TUI remains unverified.
OpenClaw update needs gateway stop/restart consent; Hermes/ZCode need supported
ordinary-session proof. The earlier Claude native-child pass at 16:51Z belongs
to 1de05aea, not a future runtime. Never transfer that proof across builds.
No service interruption, credential creation, provider-policy change, publication
or exhaustive workflow dispatch is implied. Never mark AR-404 done while any
baseline item remains unaccounted for.
