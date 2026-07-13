---
title: "Production readiness refactor and operations dashboard"
status: active
category: worklog
created: 2026-07-11
updated: 2026-07-13
tags: [production-readiness, dashboard, cross-platform]
related:
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/decisions/0028-host-support-maturity-and-reversible-install.md
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
  - docs/decisions/0030-versioned-quantitative-evaluation-gates.md
supersedes: []
superseded_by: null
type: worklog
commit: "17a62dd5924a4a6fc5931ee355984f233b6e664d"
short: "17a62dd"
date: 2026-07-11
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/18
related_issues:
  - docs/roadmap/issue-AR-03-supported-host-integrations.md
  - docs/roadmap/issue-AR-04-runtime-controls.md
  - docs/roadmap/issue-AR-07-public-release-readiness.md
  - docs/roadmap/issue-AR-10-authoritative-runtime-evidence.md
  - docs/roadmap/issue-AR-11-routing-evaluation-and-performance.md
  - docs/roadmap/issue-AR-12-installed-operations-dashboard.md
---

# Worklog detail: Harden runtime and ship local operations dashboard

## Purpose

Move Agency Runtime from synthetic adapter coverage toward a production-ready,
cross-platform control plane for Codex, Claude Code, Hermes, OpenClaw, LiteLLM,
MCP clients, and generic CLI hosts. The change also makes runtime evidence
truthful, delegation executable, routing quantitatively gated, installation
reversible, and operations visible through an installed local dashboard.

## Approach

The refactor tightened one end-to-end contract rather than adding isolated
features. Routing now uses bounded fingerprinted caches, explicit abstention,
failure-aware provider fallback, and a versioned accuracy/performance suite.
Delegation uses real host backends, dependency-aware work units, isolated Git
worktrees, verified completion protocols, and authoritative correlated events.

Native installers discover each host independently, stage atomically, retain
backups, roll back safely, and report discovery, registration, enablement,
loading, and canary maturity separately. The store and LiteLLM integration
default to metadata-only bounded retention with opt-in redacted content.

The package now serves a loopback-only, per-launch-token dashboard with
route/explain testing, evidence and provider views, host maturity and controls,
roster governance, redacted configuration, and confirmed retention operations.
Packaging, CI, security, troubleshooting, release, and tracker-parity tooling
were added around the same runtime contract.

## Challenges encountered

- Native Windows, POSIX, WSL, and host-specific command lifecycles required
  explicit argv, timeout, quoting, process-tree, and maturity semantics.
- A real-browser pass caught a shipped JavaScript parse error, long-path
  overflow, stale host controls, invalid destructive-input clamping, a routing
  ID mismatch, and delayed evidence refresh that API-only tests had missed.
- A transient parallel-write failure corrupted two edited files. They were
  reconstructed from recorded successful patches and checked against the last
  green bytecode and test-function set before the complete suite was rerun.
- Owner-only privacy tests cannot be represented by the restricted sandbox
  token, so ACL-sensitive validation was rerun under the normal user token.

## Decisions and alternatives

Runtime claims follow
[ADR-0027](../decisions/0027-authoritative-runtime-evidence-traces.md);
generated files alone are not live support evidence. Host support and rollback
follow [ADR-0028](../decisions/0028-host-support-maturity-and-reversible-install.md),
so missing executables and unregistered plugins remain visible non-success
states. Dashboard binding, authentication, confirmations, and retention follow
[ADR-0029](../decisions/0029-secure-local-dashboard-and-bounded-observability.md).
The v1.1 corpus and graph-accuracy gate follow
[ADR-0030](../decisions/0030-versioned-quantitative-evaluation-gates.md).

A remote or framework-heavy dashboard was rejected in favor of package-owned
static assets and the existing Python services. Live model evaluation was
rejected as a release gate in favor of deterministic offline cases and bounded
benchmarks. Uniform generated Python hooks were not revived; each host keeps a
minimal native integration surface.

## Verification

- `python -m pytest tests -q`: 433 passed, one expected POSIX-only skip.
- Windows: routing v1.1 passed every gate; policy macro F1 was 0.9921,
  delegation and graph accuracy were 1.0, 1,000-agent p95 was 7.584 ms, and
  cache-hit p95 was 0.582 ms. Delegation evaluation passed 12/12 and generated
  host smoke passed 7/7.
- Ubuntu/WSL: an isolated wheel install loaded from its venv, served packaged
  dashboard assets, rejected unauthenticated API access, accepted the launch
  token, passed 7/7 smoke, passed v1.1 evaluation, and passed `pip check`.
- Browser verification covered authenticated and tokenless flows, route
  dependencies, immediate evidence refresh, decision IDs, desktop/mobile
  overflow, long Windows paths, and console errors.
- Wheel and source distributions passed strict Twine and content verification,
  installed outside the checkout, loaded dashboard assets, passed smoke, and
  had compatible dependency graphs.
- Ruff, compileall, high-confidence Vulture, high-severity Bandit, PyYAML
  vulnerability audit, NUL scanning, release hygiene, Markdown metadata,
  repository-link validation, tracker identity/count/label parity, and Git
  whitespace checks passed.
- The live doctor report correctly remained nonzero because the user database
  has no active roster and the default Ollama endpoint is unreachable. Codex
  was discovered but not registered; Claude Code, Hermes, OpenClaw, and
  LiteLLM were absent.

## Follow-ups

- [AR-03](../roadmap/issue-AR-03-supported-host-integrations.md) still requires
  reproducible live host canaries before any target is called runtime-verified.
- [AR-04](../roadmap/issue-AR-04-runtime-controls.md) still requires proven
  live reload/status and supported chat controls.
- [AR-07](../roadmap/issue-AR-07-public-release-readiness.md) still requires a
  clean hosted CI matrix, approved distribution scope, live support evidence,
  and explicit authorization before publishing.
- Tracker issues for locally complete AR-09 through AR-12 remain open because
  issue closure was not authorized.
