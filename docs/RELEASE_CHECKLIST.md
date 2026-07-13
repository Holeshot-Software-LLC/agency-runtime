---
title: "Release Checklist"
status: active
category: release
created: 2026-07-10
updated: 2026-07-13
tags: [release, verification]
related:
  - CHANGELOG.md
  - CONTRIBUTING.md
  - SECURITY.md
  - CODE_OF_CONDUCT.md
  - docs/THREAT_MODEL.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/roadmap/issue-AR-07-public-release-readiness.md
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
supersedes: []
superseded_by: null
---

# Release Checklist

This checklist gates a release; it is not evidence that a release has occurred.
Agency Runtime currently uses installation from this repository as its canonical
prerelease path. Choose and document any public package channel before publishing
or adding an index-install claim.

## 1. Scope and records

- [ ] The release scope maps to roadmap items and same-repository tracker issues.
- [ ] Every durable decision has an accepted ADR and registry row.
- [ ] Every substantive commit has its exact worklog row and reciprocal roadmap
      traceability.
- [ ] Tracker status matches local status, or an authorization-related mismatch
      is stated explicitly.
- [ ] `CHANGELOG.md` describes user-visible additions, changes, fixes, security
      changes, deprecations, and known limitations.
- [ ] The package version, release title, and proposed tag agree.

## 2. Truthful support matrix

- [ ] README host claims separate deterministic contract coverage from live
      discovery, registration, enablement, loading, and canary evidence.
- [ ] Every host called `runtime-verified` has a dated reproducible native
      canary on each operating system claimed by the release.
- [ ] Codex, Claude Code, Hermes, and OpenClaw install, disable, enable, rollback,
      preflight, evidence, and finalization paths have been exercised for the v1
      matrix or clearly marked below that maturity.
- [ ] Codex generated-bundle smoke proves the expected three hook events,
      commands, and timeout schema; native inventory proves plugin registration
      and enablement. Installation, status, and doctor report trust as
      `unverified` and never query or mutate Codex's live trust store. An
      operator reviews and trusts the hooks through `/hooks`, then starts a new
      session and records the release evidence. Any one-invocation canary bypass
      remains isolated and is never treated as durable installation trust.
- [ ] Windows npm command shims and POSIX executable launch are both verified.
- [ ] Ubuntu/WSL live evidence comes from a Linux environment with the project
      and test tooling installed; Windows-only evidence is not relabeled Linux.
- [ ] MCP initialization, tool discovery, bounded framing, errors, and at least
      one real stdio call pass from a packaged install.
- [ ] LiteLLM SDK registration and Proxy callback import are tested in supported
      LiteLLM versions, or the integration remains explicitly optional and
      contract-tested only.
- [ ] Generic CLI behavior is tested with an explicit argv command; an
      unconfigured backend remains unavailable.

Record dated live evidence in the release notes without committing secrets or
machine-specific credential paths.

## 3. Correctness and performance

```bash
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python -m pytest tests -q -W error -p no:cacheprovider -m "not performance" --cov=agency_runtime --cov-branch --cov-report=term-missing --cov-fail-under=100
python -m pytest tests -q -W error -p no:cacheprovider -m performance
node --test --experimental-test-coverage --test-coverage-lines=100 --test-coverage-branches=100 --test-coverage-functions=100 tests/dashboard_ui.test.mjs
agency eval delegation --json
agency eval routing --json --no-details
```

- [ ] The complete suite passes on Ubuntu CI for Python 3.10 through 3.14 and on
      Windows CI at the 3.10 and 3.14 support endpoints.
- [ ] The versioned routing report passes every checked-in threshold.
- [ ] Cache/stickiness tests prove roster, configuration, and policy isolation.
- [ ] Concurrent routing and evidence tests show no cross-request contamination.
- [ ] Delegation DAG tests cover failed prerequisites, missing results, duplicate
      work units, independent concurrency, and successful worktree merging.
- [ ] Evidence tests reject failed, stale, ambiguous, and spoofed claims.
- [ ] Measured runtime code reaches 100 percent line and branch coverage; any
      unreachable platform-only exclusion is narrow, documented, and reviewed
      rather than hidden through a broad omit rule.

## 4. Security and privacy

```bash
python scripts/verify_release_hygiene.py
python -m bandit -q -r agency_runtime -lll
python scripts/audit_runtime_dependencies.py
zizmor --pedantic --strict-collection --offline .
```

- [ ] No tracked secret, credential file, database, build output, generated host
      state, sibling path, or machine-specific absolute path is present.
- [ ] Dashboard tests enforce loopback binding, per-launch authentication,
      `Host`/origin checks, JSON mutations, exact confirmations, and restrictive
      response headers.
- [ ] Metadata-only capture and 30-day runtime retention remain the defaults.
- [ ] Opt-in content paths are bounded and redacted; limitations are documented.
- [ ] Native commands use argv execution, timeouts, bounded output, and validated
      success protocols.
- [ ] Security reporting instructions and the current supported-version statement
      are accurate.
- [ ] The threat model covers current assets, trust boundaries, controls, and
      residual risks; CodeQL completes natively when repository visibility and
      licensing permit it, or a positively recognized private/internal
      missing-entitlement response produces machine-readable evidence that
      analysis was not performed while Bandit, offline workflow auditing, and
      the exact installed-runtime vulnerability audit pass. Ambiguous probe
      responses fail closed. Dependency review passes through native diff review
      or that exact runtime audit.
- [ ] GitHub Actions use immutable SHAs, least-privilege permissions, and no
      persisted checkout credentials without an explicit need.

## 5. Documentation integrity

```bash
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py --require-tracker
python scripts/verify_tracker.py
git diff --check
```

- [ ] Every maintained Markdown file has valid front matter.
- [ ] No intra-repository link dangles and no doc depends on a sibling repo.
- [ ] README CLI examples match `agency --help` and actual exit behavior.
- [ ] Host paths and maturity labels match the installer source and doctor output.
- [ ] Contribution, code-of-conduct, security, threat-model, changelog,
      troubleshooting, and release-checklist documents are linked from README
      and `AGENTS.md`.

## 6. Build and isolated install

From a clean checkout:

```bash
python -m pip install ".[dev,release,security]"
python -m build --sdist --wheel
python -m twine check --strict dist/*
python scripts/verify_distribution.py dist
```

- [ ] Wheel and source distribution contain every package module and asset; the
      source distribution also contains governance docs, the threat model,
      release scripts, tests, and self-contained examples.
- [ ] Windows service contract tests prove current-user Task Scheduler
      registration, owned updates, rollback-on-failure, start/stop/restart,
      uninstall, readiness, and `--no-dashboard` without touching a real task.
- [ ] Linux service contract tests prove `systemd --user` registration,
      hardening, manager-unavailable truth, start/stop/restart, uninstall,
      readiness, and `--no-dashboard` without touching a real user manager.
- [ ] Dashboard configuration tests cover typed writes, redaction, write-only
      secrets, optimistic-concurrency conflicts, local-only enforcement, and
      sensitive confirmation phrases through both CLI and API.
- [ ] Dashboard live tests cover authenticated schema and metadata boundaries,
      stable revisions, one bounded activity read, stale-response cancellation,
      visibility lifecycle, terminal authentication, and capped retry behavior.
- [ ] Dashboard browser QA covers desktop and mobile layout, live controls,
      chart summaries, keyboard naming, reduced motion, forced colors, no
      horizontal page overflow, and a clean console.
- [ ] Every dashboard asset is present in wheel and source artifacts, passes the
      static CSP/security scan, and stays within the documented asset budget.
- [ ] Fresh Python 3.10 environments on Windows install the built wheel and
      source distribution separately, run `agency --help`, import package data,
      and pass the full packaged smoke procedure for each artifact.
- [ ] The same isolated wheel and source-distribution procedures pass on Ubuntu.
- [ ] `python -m pip check` passes for both artifacts in both environments.
- [ ] Rebuilding from the same source does not depend on untracked local files.

## 7. Publish and post-publish

Publishing, pushing, tagging, issue closure, and release creation are
outward-facing actions and require explicit authorization.

- [ ] Obtain approval for the exact tag, artifacts, destination, and release
      notes.
- [ ] Tag the reviewed commit; do not move an existing public tag.
- [ ] Publish the wheel and source artifact produced by the verified workflow,
      not a local rebuild.
- [ ] Verify hashes, metadata, install command, and CLI version from the public
      destination.
- [ ] Create release notes from `CHANGELOG.md` and include known support limits.
- [ ] Update tracker states only after the release outcome is confirmed.
- [ ] Start the next `Unreleased` changelog section.

## Current blockers

`AR-03` and `AR-04` are locally complete. The exact-confirmed Windows Codex
0.144.1 isolated-profile canary exited `0`, produced a valid six-line header,
and persisted one correlated routing/finalization attestation; isolated
conversation controls exercised disable and enable while ending enabled. The
canary used a one-invocation trust bypass and recorded no model receipt. It does
not establish durable real-profile trust, which remains an explicit `/hooks`
review and new-session step, and it does not establish Linux Codex maturity.

Final local warning-strict coverage, security, performance, dashboard,
wheel/source, and isolated Windows/WSL install gates pass. `AR-07`, `AR-16`,
and `AR-17` remain in progress only for the hosted Python, security, CodeQL,
and artifact matrix, review and merge, and the required worklog/clean-tree
closure. Claude Code, Hermes, and OpenClaw were absent and remain contract-only.
Publication remains a separate authorization-gated action, not evidence of
readiness.
