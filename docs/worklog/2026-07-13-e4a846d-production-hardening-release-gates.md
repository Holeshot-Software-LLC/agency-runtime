---
title: "Production hardening and release gates"
status: active
category: worklog
created: 2026-07-13
updated: 2026-07-13
tags: [hardening, release, portability, security, performance]
related:
  - docs/roadmap/issue-AR-07-public-release-readiness.md
  - docs/roadmap/issue-AR-16-linux-python-delegation-compatibility.md
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
  - docs/RELEASE_CHECKLIST.md
  - docs/THREAT_MODEL.md
supersedes: []
superseded_by: null
type: worklog
commit: e4a846d
short: e4a846d
date: 2026-07-13
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/18
related_issues:
  - docs/roadmap/issue-AR-02-specialist-coverage-gaps.md
  - docs/roadmap/issue-AR-03-supported-host-integrations.md
  - docs/roadmap/issue-AR-04-runtime-controls.md
  - docs/roadmap/issue-AR-05-guided-provider-configuration.md
  - docs/roadmap/issue-AR-06-cli-authenticated-judge-providers.md
  - docs/roadmap/issue-AR-07-public-release-readiness.md
  - docs/roadmap/issue-AR-09-windows-test-isolation.md
  - docs/roadmap/issue-AR-10-authoritative-runtime-evidence.md
  - docs/roadmap/issue-AR-11-routing-evaluation-and-performance.md
  - docs/roadmap/issue-AR-12-installed-operations-dashboard.md
  - docs/roadmap/issue-AR-13-optional-dashboard-service-configuration.md
  - docs/roadmap/issue-AR-14-live-signal-observatory.md
  - docs/roadmap/issue-AR-15-reliable-json-rejection-responses.md
  - docs/roadmap/issue-AR-16-linux-python-delegation-compatibility.md
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
---

# Worklog detail: Production hardening and release gates

## Purpose

Complete the integrated production-readiness pass across host installation,
routing and delegation, evidence integrity, configuration, local HTTP,
dashboard operation, persistence, packaging, portability, and open-source
governance. The change closes the local implementation gap for every roadmap
item while preserving truthful distinctions between contract coverage and live
host evidence.

## Approach

- Split oversized CLI, installer, dashboard-service, configuration,
  delegation, selector, LiteLLM, and SQLite facades into cohesive modules while
  preserving public imports and supported monkeypatch seams.
- Harden filesystem, JSON/YAML, subprocess, Git, Windows ACL, HTTP, MCP,
  provider, and evidence boundaries with bounded fail-closed contracts.
- Complete the source-owned live dashboard, shared CLI/dashboard configuration,
  optional Windows/Linux user service, and installed-distribution smoke path.
- Add pinned CI, CodeQL, dependency review, dependency audit, release hygiene,
  artifact verification, threat-model, and contributor-governance gates.
- Prove the current Codex bundle through native inventory, live control and
  keyless-provider paths, plus an exact-confirmed isolated-profile header
  canary without promoting real-profile trust.
- Replace the routing cache's per-hit 1,000-agent Python guard rebuild with
  detached mutation snapshots. Nested mutation invalidation remains complete,
  while profiled cache-hit routing became roughly ten times faster.

## Challenges encountered

- Codex command hooks needed PowerShell invocation semantics that preserve the
  executable argv and exact LF-delimited stdin on Windows. The corrected bundle
  passed a native Codex 0.144.1 isolated-profile canary; durable real-profile
  trust remains the operator's manual `/hooks` action.
- Windows restricted-token runs correctly denied temporary-file and child-
  process operations used by ACL, build, audit, and Node worker tests. Final
  gates were rerun with isolated paths under an unrestricted user token rather
  than weakening those security tests.
- A borderline performance sample exposed real O(roster) Python work on every
  cache hit. The hot path was optimized instead of relaxing the 2 ms gate or
  sampling until it happened to pass.
- Setuptools occasionally left a sparse source-distribution staging directory
  when Windows scanners held files open. Release hygiene now detects that
  residue, and final cleanup removed it after artifact verification.

## Decisions and alternatives

- Preserve security-significant manual host trust instead of auto-approving
  hooks or claiming isolated evidence as real-profile runtime maturity.
- Install and exercise both wheel and source distributions independently on
  Windows and Ubuntu; artifact-content inspection alone is not treated as an
  install proof.
- Keep exact 100 percent statement and branch coverage with targeted defensive-
  path tests; no broad omit rules or threshold reductions were introduced.
- Keep host claims capability-bound: absent Claude Code, Hermes, and OpenClaw
  installations remain contract-covered rather than live-verified.

## Verification

- Windows warning-strict coverage: `2255 passed`, `5 skipped`, `2 deselected`;
  `17,141` statements and `5,352` branches with zero misses or partials.
- Uninstrumented performance: `2 passed`, `2260 deselected`; all 25 routing
  gates passed, with routing p95 `11.032 ms`, cache-hit p95 `0.337 ms`,
  `154.14` calls/second, and overlap `8`.
- Dashboard JavaScript: `60/60` tests with exact line, branch, and function
  coverage across seven modules.
- Security and quality: Ruff/format, compile, Bandit high severity, strict
  offline Zizmor, dependency audit, dependency consistency, release hygiene,
  documentation/schema validation, and whitespace checks passed.
- Fresh final wheel and source distribution passed strict Twine and structural
  verification. Separate clean Python 3.14 installs passed packaged MCP/status
  (10 tools), authenticated dashboard health, configuration, all four host
  bundles, CLI smoke, and `pip check`.
- Local artifact SHA-256: wheel
  `7BC30937E3605507F1F41D49CC11FC18565F260D82EBCFC559BBBEA09AFCD7B0`;
  source distribution
  `EFE580D1F80AFFCA5EAEC33EC3862E327A9FCA3C8831F9E810989ECD42832135`.

## Follow-ups

- Run the reviewed commit through hosted Python, security, CodeQL, dependency-
  review, artifact, and Windows/Linux distribution-smoke jobs.
- After hosted CI is green, record the PR URL, mark AR-07/AR-16/AR-17 done,
  merge the reviewed branch, and verify that every linked tracker issue closes.
