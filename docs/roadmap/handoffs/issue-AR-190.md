---
title: "AR-190 active recovery capsule"
status: active
category: roadmap
created: 2026-07-28
updated: 2026-07-28
tags: [handoff, updates, uv, security, recovery]
related:
  - docs/roadmap/issue-AR-190-make-upgrade-plans-runnable-in-uv-tools.md
  - docs/decisions/0107-resolve-updates-immutably-and-keep-application-attended.md
  - docs/worklog/README.md
  - README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-190
branch: main
evidence_commit: 1011a89c61ab7cb1230336b790930f74be85782a
minimum_ledger_commit: 68206003d4d9fbb3b738ec75f89b6dc6ef7eef91
hard_checkpoint_percent: 50
tracker_url: null
---

# AR-190 active recovery capsule

Bounded current-state projection for runnable attended upgrade plans. The
[canonical issue](../issue-AR-190-make-upgrade-plans-runnable-in-uv-tools.md)
owns the complete problem, approach, acceptance, and implementation evidence.

## checkpoint

- Branch `main` began this package at clean substantive/ledger checkpoint
  `1011a89`/`6820600`; this capsule ships with the reviewed AR-190 recovery
  candidate that follows it.
- End-of-package telemetry reported 41.2 percent remaining and required a clean
  durable checkpoint before live evaluation.
- The user-owned untracked files
  `docs/analysis/2026-07-25-deep-audit-findings.md` and `uv.lock` remain
  unchanged and excluded.

## completed-evidence

- The planner recognizes a uv-owned Agency environment only after validating a
  bounded exact receipt, private prefix, package and interpreter binding,
  canonical Agency entry point, non-repository uv launcher, and exact default
  tool/bin targets. Target-changing uv/XDG overrides fail closed.
- POSIX uv symlinks require stable owner/root-owned executable identity whose
  resolved target is inside the exact tool prefix. Windows copied entry points
  remain non-link executables.
- Pip is used only outside uv ownership after its package entry point is bound
  to the exact non-repository interpreter and a bounded `pip --isolated
  --disable-pip-version-check --version` probe succeeds. Both displayed Python
  commands use `-I`; refresh cannot import a dirty caller checkout.
- Windows copy/paste output uses the PowerShell call operator and inert
  single-quoted arguments. An unavailable plan exits nonzero. The dashboard
  remains a copy-only fixed CLI selector and never receives installer argv.
- The focused update/CLI package passes 65 tests in 2.68 seconds on Windows,
  with one POSIX-only symlink test intentionally skipped. Targeted Ruff, format,
  and diff checks pass. Metadata, policy, and documentation validation pass for
  487 Markdown files.
- Independent security and operational rereviews report no remaining scoped
  blocker. A bounded read-only candidate probe against the actual uv 0.10.9
  installation selects the expected tool, prefix, bin directory, entry point,
  and isolated Codex refresh interpreter.

## exact-blocker

- The reviewed candidate has not yet been committed, installed from its exact
  final SHA, or used for the attended Codex refresh. Those are the next bounded
  package, not evidence supplied by this recovery checkpoint.
- Fresh Codex hook trust and a successful native specialist activation canary
  remain required before claiming the installed header path works.
- Tracker creation is an outward-facing write pending explicit authorization.
- No exhaustive workflow, hosted compatibility matrix, or signed public
  release gate ran. None is authorized or required for this checkpoint.

## same-task-continuity

The telemetry threshold requires this clean durable checkpoint, then continued
work in the same task. It does not pause, transfer, or authorize a new task, an
exhaustive workflow, or unattended simulation of human presence.

## next-bounded-work-package

1. Commit this candidate and its exact worklog ledger, then push `main` without
   dispatching the exhaustive workflow.
2. Reinstall Agency from that exact SHA and verify `agency version --json` plus
   a live `agency upgrade` plan from outside the repository.
3. Run one attended `agency install --agent codex --no-dashboard --json`, then
   establish fresh terminal hook trust and run one bounded activation canary.
4. Record exact success or failure evidence and issue a scoped GO/NO-GO.

## verification

~~~text
python -m pytest tests/test_update_service.py tests/test_cli_upgrade.py -q -W error
ruff check agency_runtime/core/update_service.py agency_runtime/cli/upgrade_commands.py tests/test_update_service.py tests/test_cli_upgrade.py
ruff format --check agency_runtime/core/update_service.py agency_runtime/cli/upgrade_commands.py tests/test_update_service.py tests/test_cli_upgrade.py
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
node --test tests/dashboard_ui.test.mjs
agency eval routing --json --no-details
git diff --check
~~~

## constraints

- Use the named fast production spine and focused behavior checks only. Do not
  run or dispatch the exhaustive corpus, coverage shards, compatibility matrix,
  or exact-SHA release workflow unless the owner explicitly requests it.
- Do not execute a displayed upgrade plan automatically. It is valid only
  unchanged in the same owner-controlled environment that generated it.
- Do not simulate hook trust, native child activation, or Agency evidence.
  Owner CLI execution needs no Agency presence ceremony; stop only at genuine
  external credentials, signing, publication, or harness trust that lacks a
  supported autonomous mode.
- Do not stage or alter the user-owned analysis draft or `uv.lock`.
- No tracker creation, package publication, tag, release, signing action, or
  exhaustive workflow dispatch without explicit authorization.
