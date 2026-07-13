---
title: "Cross-platform production hardening and host operations"
status: active
category: worklog
created: 2026-07-12
updated: 2026-07-13
tags: [production-readiness, security, delegation, providers, cross-platform]
related:
  - docs/decisions/0033-explicit-companion-route-availability.md
  - docs/decisions/0034-persistent-soft-host-control.md
  - docs/decisions/0035-authoritative-bounded-provider-chain.md
  - docs/decisions/0036-capability-bound-host-canary-attestations.md
supersedes: []
superseded_by: null
type: worklog
commit: "2515bfc119e5313d55bef5b7d8f6ac9325342a91"
short: "2515bfc"
date: 2026-07-12
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
---

# Worklog detail: Complete cross-platform production hardening

## Purpose

Close the remaining deterministic production-readiness gaps across specialist
routing, provider setup, CLI-authenticated judges, native host integration,
runtime controls, delegation containment, local storage, dashboard transport,
packaging, and Windows/Linux support. The change also turns each support claim
into an evidence-separated contract instead of inferring runtime maturity from
an installed file or executable.

## Approach

The runtime now validates every companion route against either a governed
bundled specialist or an explicit roster-gated reason. Provider configuration
uses one authoritative four-entry chain shared by the wizard, doctor, and
selector. Credentialed remote endpoints require HTTPS, while literal loopback
HTTP remains available for local compatible servers.

Codex and Claude judge prompts use standard input, bounded output, isolated
home/temp state, minimal allowlisted environments, and recursively redacted
results. Delegated processes launch inside a suspended-assignment Windows Job
Object or an owned POSIX process group. Timeouts, partial I/O-worker startup,
and successful parents that leave descendants behind all terminate the owned
tree and fail explicitly.

Host controls persist independently from native registration and are checked at
every adapter boundary. Canary readiness and exact-confirmed execution use
capability probes, isolated plugin profiles, nonce-bound query fingerprints,
and content-free attestations. Storage opens current schemas without taking a
schema-write lock, preserves custom parent permissions, restores migration
indexes, rejects future schemas, and fails closed on unsafe Windows database
paths or ACLs.

The dashboard and control API share bounded authenticated request handling.
Rejected JSON mutations consume only a safe declared body before responding so
Windows clients receive the JSON error instead of an intermittent TCP reset.
HTTP fixtures now restore temporary configuration state on every platform.

## Challenges encountered

- A second adversarial review found eight production blockers after the first
  green suite: shared-parent ACL mutation, inherited credential leakage,
  credentialed plaintext HTTP, prompt disclosure, escaped descendants, a lost
  SQLite migration index, unnecessary schema write locking, and a canary auth
  fallback to the real profile.
- Windows process containment required creation-time suspension, Job assignment
  before resume, kill-on-close semantics, handle cleanup on every failure path,
  and deterministic cleanup of partially started pipe workers.
- The first isolated Windows rerun revealed a PowerShell harness mistake; it was
  discarded and rerun with both `HOME` and `USERPROFILE` correctly redirected.
- That corrected run exposed an intermittent connection abort on a valid `415`
  response. The root cause was closing a Windows socket with unread request
  bytes, not a routing or JSON error.
- Native Ubuntu/Python 3.12 exposed zero-argument `super()` binding to the
  pre-transformation form of slotted dataclass backends. Explicit base-parser
  dispatch restored Codex, Claude, and OpenClaw protocol handling.
- WSL lacked pip and `python3-venv`; Linux validation used an ext4 source copy,
  Ubuntu's installed PyYAML, and only pytest's pure-Python modules, leaving the
  distribution unchanged.
- One isolated Codex judge call ran before explicit live-call authorization due
  to a delegated audit mistake. It succeeded, but is not accepted as AR-06
  release evidence without the operator's explicit decision. No repository,
  Codex config, or Codex auth file was changed by that call.

## Decisions and alternatives

[ADR-0033](../decisions/0033-explicit-companion-route-availability.md)
requires every policy route to be available or explicitly gated rather than
silently falling back to a generic specialist.
[ADR-0034](../decisions/0034-persistent-soft-host-control.md) keeps reversible
runtime control separate from native plugin installation.
[ADR-0035](../decisions/0035-authoritative-bounded-provider-chain.md) makes the
visible provider chain authoritative and defines the hardened CLI and HTTP
boundaries.
[ADR-0036](../decisions/0036-capability-bound-host-canary-attestations.md)
separates deterministic readiness from a live, authorized canary.

Detached child processes were not treated as successful background work because
the backend contract cannot account for or cancel them after returning. Shared
custom parent directories were not forcibly hardened because file ownership
does not imply authority over an operator-managed directory. Live model and
host evidence was not fabricated from deterministic tests.

## Verification

- Native Windows/Python 3.13: 684 passed, four expected skips, with unraisable
  resource warnings promoted to errors.
- Native ext4 Ubuntu WSL/Python 3.12: 673 passed, 15 expected platform/host
  skips; all previously failing structured backends pass.
- Final Windows/Python 3.14 wheel: clean isolated install, packaged dashboard,
  charts, canary and eval assets present, structured Codex/Claude/OpenClaw
  parsing passed, CLI help passed, and `pip check` found no broken requirements.
- Routing v1.2: required Recall@3 1.0, policy macro F1 0.9945, delegation and
  graph accuracy 1.0, 1,000-agent routing p95 6.491 ms, and cache-hit p95
  0.589 ms. Delegation evaluation passed 12/12.
- Dashboard JavaScript lifecycle/security suite: 13 passed. Warning-strict
  dashboard and HTTP files: 74 passed.
- Fresh wheel and source archives passed strict Twine metadata and distribution
  content verification. The generated Codex plugin passed the local official
  plugin validator.
- Ruff, compileall, Bandit, dependency audit, policy generation, release
  hygiene, Markdown metadata, repository links, worklog generation, and Git
  whitespace checks passed.

## Follow-ups

- [AR-03](../roadmap/issue-AR-03-supported-host-integrations.md) requires the
  explicitly authorized native host canary evidence for each final support
  claim.
- [AR-04](../roadmap/issue-AR-04-runtime-controls.md) requires authorized live
  control execution inside every host ultimately called verified.
- [AR-06](../roadmap/issue-AR-06-cli-authenticated-judge-providers.md) requires
  operator acceptance of existing evidence or one authorized live keyless judge
  canary.
- [AR-07](../roadmap/issue-AR-07-public-release-readiness.md) and
  [AR-16](../roadmap/issue-AR-16-linux-python-delegation-compatibility.md)
  require a clean hosted CI matrix after publication of this branch.
- Tracker records for AR-14 through AR-16 and issue closure remain
  authorization-gated outward actions.
