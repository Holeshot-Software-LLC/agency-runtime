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
evidence_commit: 76dea219742cc1f846ee212b35d968c634edb148
minimum_ledger_commit: 76dea219742cc1f846ee212b35d968c634edb148
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
- Release verification retains a generic ban on executable and disguised PE
  payloads after retiring the one packaged native executable.
- No live install, service mutation, tracker write, or hosted workflow ran.

## exact-blocker

The named fast spine and dashboard UI suite must pass before the package is
done. The same-repository tracker item
cannot be created without outward-write authorization.

## same-task-continuity

Continue locally through focused review, fast verification, write-free demo,
substantive commit, and the required worklog ledger commit.

## next-bounded-work-package

1. Remove all current release and documentation claims for Agency-owned
   Windows Hello while preserving faithful historical records.
2. Run focused installer, authority-boundary, packaging, and documentation
   checks.
3. Run the named fast production spine and a write-free default-install dry run.
4. Record exact evidence in AR-197, AR-198, and this capsule; commit the result
   and its worklog ledger locally.

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
