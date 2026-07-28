---
title: "AR-198 active recovery capsule"
status: active
category: roadmap
created: 2026-07-28
updated: 2026-07-28
tags: [handoff, installation, host-integrations, dashboard, recovery]
related:
  - docs/roadmap/issue-AR-198-install-applicable-suite-by-default.md
  - docs/roadmap/issue-AR-197-remove-agency-owned-windows-hello.md
  - docs/decisions/0111-install-the-applicable-suite-by-default.md
  - docs/decisions/0110-remove-agency-owned-windows-hello.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-198
branch: main
evidence_commit: f5ca172eb1195358188e7594ef13a8bedc7f986c
minimum_ledger_commit: cd0a88af64ffb4eb796469353691a3e84496067e
hard_checkpoint_percent: 50
tracker_url: null
---

# AR-198 active recovery capsule

## checkpoint

- Bare install now selects automatic host discovery and dashboard installation.
- Explicit `--agent` narrows host scope; `--no-dashboard` is the opt-out.
- Host outcomes are isolated from one another and from dashboard failure.
- Agency-owned Windows Hello product, native, build, and package paths are being
  removed under AR-197; unrelated positive mutations remain unavailable.
- Owner-untracked analysis and `uv.lock` files remain untouched.

## completed-evidence

- Installer and authority-boundary focused suites passed: 358 tests. Packaging
  and canonicalization focused suites passed: 324 tests.
- Documentation validation, Ruff checks, Ruff formatting, and diff whitespace
  passed at the hard checkpoint.
- A write-free `agency install --dry-run --json` detected Codex and ZCode,
  produced a ready dashboard plan, and returned `ok=true`, `complete=true`.
- The named fast production spine passed 646 tests with 6 skipped. The dashboard
  UI suite passed all 109 tests when run outside the restricted token sandbox;
  the sandboxed attempt failed at Node worker spawn with `EPERM` before tests.
- Routing evaluation schema/version 1.3.0 passed every configured gate.
- Release verification retains a generic ban on executable and disguised PE
  payloads after retiring the one packaged native executable.
- No live install, service mutation, tracker write, or hosted workflow ran.

## exact-blocker

The local implementation package is complete. The same-repository tracker item
cannot be created without outward-write authorization.

## same-task-continuity

Continue locally through focused review, fast verification, write-free demo,
substantive commit, and the required worklog ledger commit.

## next-bounded-work-package

1. After explicit authorization, create and map the same-repository AR-197 and
   AR-198 tracker items without changing the completed local evidence.
2. Run a separately scoped Codex-native refresh/trust and activation canary for
   AR-197; keep the dashboard excluded from that host-only proof.

## verification

~~~text
python -m pytest tests/test_native_installer.py tests/test_cli_parser_contract.py tests/test_cli_operator_presence.py -q -W error
python -m pytest tests/test_platform_wheel.py tests/test_release_packaging.py tests/test_distribution_verifier_hardening.py tests/test_canonicalize_distributions.py -q -W error
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
node --test tests/dashboard_ui.test.mjs
agency install --dry-run --json
git diff --check
~~~

## constraints

- Preserve component-level fail-closed postconditions and truthful partial
  results.
- Keep MCP, hooks, broker, and dashboard request paths read-only for persistent
  mutations.
- Preserve owner-untracked files.
- Do not mutate trackers, services, installed hosts, packages, or hosted
  workflows without explicit authorization.
