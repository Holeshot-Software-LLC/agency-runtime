---
title: Roadmap
status: active
category: roadmap
created: 2026-07-10
updated: 2026-07-13
tags: [planning, tracker]
related: []
supersedes: []
superseded_by: null
---

# Roadmap

This registry is the canonical map from stable, repository-owned planning IDs to tracker-assigned issue numbers. Internal IDs never change and never inherit the tracker's number. When an issue is created, its title must begin with the internal ID in brackets, and its assigned URL must be written back to both this registry and the issue document.

## Items

| Internal ID | Item | Status | Priority | Epic | Tracker mapping |
|---|---|---|---|---|---|
| `AR-01` | [Selection explain receipts](issue-AR-01-selection-explain-receipts.md) | done | p1 | observability | [#1](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/1) |
| `AR-02` | [Close specialist coverage gaps](issue-AR-02-specialist-coverage-gaps.md) | done | p2 | roster-governance | [#2](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/2) |
| `AR-03` | [Prove supported-host integrations](issue-AR-03-supported-host-integrations.md) | done | p0 | host-integrations | [#3](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/3) |
| `AR-04` | [Add durable runtime controls](issue-AR-04-runtime-controls.md) | done | p1 | operations | [#4](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/4) |
| `AR-05` | [Complete guided provider configuration](issue-AR-05-guided-provider-configuration.md) | done | p1 | provider-configuration | [#5](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/5) |
| `AR-06` | [Implement CLI-authenticated judge providers](issue-AR-06-cli-authenticated-judge-providers.md) | done | p2 | provider-runtime | [#6](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/6) |
| `AR-07` | [Complete public release readiness](issue-AR-07-public-release-readiness.md) | in_progress | p1 | release | [#7](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/7) |
| `AR-08` | [Make documentation self-contained](issue-AR-08-self-contained-documentation.md) | done | p1 | documentation | [#8](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/8) |
| `AR-09` | [Isolate Windows tests from the real user profile](issue-AR-09-windows-test-isolation.md) | done | p0 | testing | [#9](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/9) |
| `AR-10` | [Make runtime evidence authoritative](issue-AR-10-authoritative-runtime-evidence.md) | done | p0 | observability | [#10](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/10) |
| `AR-11` | [Establish routing accuracy and performance gates](issue-AR-11-routing-evaluation-and-performance.md) | done | p0 | testing | [#11](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/11) |
| `AR-12` | [Ship a secure installed operations dashboard](issue-AR-12-installed-operations-dashboard.md) | done | p1 | operations | [#12](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/12) |
| `AR-13` | [Add an optional cross-platform dashboard service and configuration parity](issue-AR-13-optional-dashboard-service-configuration.md) | done | p1 | operations | [#13](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/13) |
| `AR-14` | [Transform the dashboard into a live signal observatory](issue-AR-14-live-signal-observatory.md) | done | p1 | operations | [#14](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/14) |
| `AR-15` | [Deliver reliable JSON rejection responses on Windows](issue-AR-15-reliable-json-rejection-responses.md) | done | p1 | operations | [#15](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/15) |
| `AR-16` | [Restore Linux and Python 3.12 delegation compatibility](issue-AR-16-linux-python-delegation-compatibility.md) | in_progress | p0 | testing | [#16](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/16) |
| `AR-17` | [Complete production hardening and portable release gates](issue-AR-17-production-hardening-portability.md) | in_progress | p0 | release | [#17](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/17) |
| `AR-18` | [Detect work-unit file paths containing spaces](issue-AR-18-work-unit-paths-with-spaces.md) | in_progress | p1 | testing | [#19](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/19) |
| `AR-19` | [Deliver reliable bounded overload responses](issue-AR-19-bounded-overload-responses.md) | in_progress | p0 | operations | [#20](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/20) |
| `AR-20` | [Validate documentation ledgers against canonical full history](issue-AR-20-full-history-ledger-ci.md) | in_progress | p0 | testing | [#21](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/21) |
| `AR-21` | [Make Windows child startup deterministic and fail closed](issue-AR-21-fully-resume-windows-children.md) | in_progress | p0 | host-integrations | [#22](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/22) |
| `AR-22` | [Serialize concurrent Windows storage ACL repair](issue-AR-22-concurrent-storage-acl-repair.md) | in_progress | p0 | operations | [#23](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/23) |
| `AR-23` | [Stabilize hosted Windows PowerShell integration gate](issue-AR-23-hosted-windows-powershell-gate.md) | in_progress | p0 | testing | [#24](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/24) |

## Traceability

This table links local scope to implementation evidence and durable decisions.
Tracker URLs are also retained in the mapping above because tracker numbers are
not stable internal identifiers.

| Roadmap item | Implementation commits | Governing decisions |
|---|---|---|
| [AR-01](issue-AR-01-selection-explain-receipts.md) | [`42f6580`](../worklog/README.md) | [ADR-0015](../decisions/0015-versioned-selection-explain-receipts.md) |
| [AR-02](issue-AR-02-specialist-coverage-gaps.md) | [`2515bfc`](../worklog/README.md) | [ADR-0013](../decisions/0013-approval-gated-roster-activation.md), [ADR-0021](../decisions/0021-full-companion-policy-with-precedence.md), [ADR-0033](../decisions/0033-explicit-companion-route-availability.md) |
| [AR-03](issue-AR-03-supported-host-integrations.md) | [`17a62dd`](../worklog/README.md), [`2515bfc`](../worklog/README.md) | [ADR-0024](../decisions/0024-native-host-packages-and-minimal-bridges.md), [ADR-0028](../decisions/0028-host-support-maturity-and-reversible-install.md), [ADR-0036](../decisions/0036-capability-bound-host-canary-attestations.md) |
| [AR-04](issue-AR-04-runtime-controls.md) | [`17a62dd`](../worklog/README.md), [`2515bfc`](../worklog/README.md) | [ADR-0010](../decisions/0010-one-command-install-and-reversible-toggle.md), [ADR-0024](../decisions/0024-native-host-packages-and-minimal-bridges.md), [ADR-0028](../decisions/0028-host-support-maturity-and-reversible-install.md), [ADR-0034](../decisions/0034-persistent-soft-host-control.md), [ADR-0036](../decisions/0036-capability-bound-host-canary-attestations.md) |
| [AR-05](issue-AR-05-guided-provider-configuration.md) | [`2515bfc`](../worklog/README.md) | [ADR-0006](../decisions/0006-config-first-redacted-configuration.md), [ADR-0008](../decisions/0008-ordered-provider-fallback.md), [ADR-0035](../decisions/0035-authoritative-bounded-provider-chain.md) |
| [AR-06](issue-AR-06-cli-authenticated-judge-providers.md) | [`2515bfc`](../worklog/README.md) | [ADR-0008](../decisions/0008-ordered-provider-fallback.md), [ADR-0035](../decisions/0035-authoritative-bounded-provider-chain.md) |
| [AR-07](issue-AR-07-public-release-readiness.md) | [`17a62dd`](../worklog/README.md), [`2515bfc`](../worklog/README.md), [`a60b41c`](../worklog/README.md), [`852359d`](../worklog/README.md), [`c7e06fd`](../worklog/README.md), [`a096236`](../worklog/README.md), [`26fd65a`](../worklog/README.md) | [ADR-0010](../decisions/0010-one-command-install-and-reversible-toggle.md), [ADR-0025](../decisions/0025-self-contained-linked-documentation.md), [ADR-0028](../decisions/0028-host-support-maturity-and-reversible-install.md), [ADR-0029](../decisions/0029-secure-local-dashboard-and-bounded-observability.md), [ADR-0030](../decisions/0030-versioned-quantitative-evaluation-gates.md), [ADR-0034](../decisions/0034-persistent-soft-host-control.md), [ADR-0035](../decisions/0035-authoritative-bounded-provider-chain.md), [ADR-0036](../decisions/0036-capability-bound-host-canary-attestations.md) |
| [AR-08](issue-AR-08-self-contained-documentation.md) | [`4d17668`](../worklog/README.md) | [ADR-0025](../decisions/0025-self-contained-linked-documentation.md) |
| [AR-09](issue-AR-09-windows-test-isolation.md) | [`a896c81`](../worklog/README.md), [`2515bfc`](../worklog/README.md), [`852359d`](../worklog/README.md), [`c7e06fd`](../worklog/README.md) | [ADR-0026](../decisions/0026-explicit-test-home-boundaries.md) |
| [AR-10](issue-AR-10-authoritative-runtime-evidence.md) | [`17a62dd`](../worklog/README.md), [`2515bfc`](../worklog/README.md) | [ADR-0007](../decisions/0007-six-line-evidence-header.md), [ADR-0011](../decisions/0011-explicit-delegation-evidence-lifecycle.md), [ADR-0016](../decisions/0016-central-finalization-and-session-correlation.md), [ADR-0027](../decisions/0027-authoritative-runtime-evidence-traces.md) |
| [AR-11](issue-AR-11-routing-evaluation-and-performance.md) | [`17a62dd`](../worklog/README.md), [`d1275c3`](../worklog/README.md), [`2515bfc`](../worklog/README.md) | [ADR-0001](../decisions/0001-layered-specialist-routing.md), [ADR-0015](../decisions/0015-versioned-selection-explain-receipts.md), [ADR-0021](../decisions/0021-full-companion-policy-with-precedence.md), [ADR-0030](../decisions/0030-versioned-quantitative-evaluation-gates.md) |
| [AR-12](issue-AR-12-installed-operations-dashboard.md) | [`17a62dd`](../worklog/README.md), [`2515bfc`](../worklog/README.md) | [ADR-0010](../decisions/0010-one-command-install-and-reversible-toggle.md), [ADR-0012](../decisions/0012-canonical-sqlite-audit-store.md), [ADR-0017](../decisions/0017-sanitized-server-error-boundary.md), [ADR-0027](../decisions/0027-authoritative-runtime-evidence-traces.md), [ADR-0029](../decisions/0029-secure-local-dashboard-and-bounded-observability.md) |
| [AR-13](issue-AR-13-optional-dashboard-service-configuration.md) | [`d1275c3`](../worklog/README.md), [`2515bfc`](../worklog/README.md) | [ADR-0006](../decisions/0006-config-first-redacted-configuration.md), [ADR-0010](../decisions/0010-one-command-install-and-reversible-toggle.md), [ADR-0029](../decisions/0029-secure-local-dashboard-and-bounded-observability.md), [ADR-0031](../decisions/0031-optional-user-dashboard-service-and-shared-configuration.md) |
| [AR-14](issue-AR-14-live-signal-observatory.md) | [`63ea805`](../worklog/README.md), [`2515bfc`](../worklog/README.md) | [ADR-0029](../decisions/0029-secure-local-dashboard-and-bounded-observability.md), [ADR-0031](../decisions/0031-optional-user-dashboard-service-and-shared-configuration.md), [ADR-0032](../decisions/0032-adaptive-authenticated-dashboard-polling.md) |
| [AR-15](issue-AR-15-reliable-json-rejection-responses.md) | [`2515bfc`](../worklog/README.md) | [ADR-0017](../decisions/0017-sanitized-server-error-boundary.md), [ADR-0029](../decisions/0029-secure-local-dashboard-and-bounded-observability.md) |
| [AR-16](issue-AR-16-linux-python-delegation-compatibility.md) | [`2515bfc`](../worklog/README.md), [`852359d`](../worklog/README.md), [`c7e06fd`](../worklog/README.md), [`a096236`](../worklog/README.md), [`26fd65a`](../worklog/README.md) | [ADR-0019](../decisions/0019-bounded-machine-readable-cli-delegation.md), [ADR-0035](../decisions/0035-authoritative-bounded-provider-chain.md), [ADR-0043](../decisions/0043-prime-stdin-before-windows-child-resume.md), [ADR-0044](../decisions/0044-preclose-bounded-windows-child-stdin.md) |
| [AR-17](issue-AR-17-production-hardening-portability.md) | [`e4a846d`](../worklog/README.md), [`a60b41c`](../worklog/README.md), [`852359d`](../worklog/README.md), [`c7e06fd`](../worklog/README.md), [`a096236`](../worklog/README.md), [`26fd65a`](../worklog/README.md) | [ADR-0027](../decisions/0027-authoritative-runtime-evidence-traces.md), [ADR-0028](../decisions/0028-host-support-maturity-and-reversible-install.md), [ADR-0029](../decisions/0029-secure-local-dashboard-and-bounded-observability.md), [ADR-0030](../decisions/0030-versioned-quantitative-evaluation-gates.md), [ADR-0036](../decisions/0036-capability-bound-host-canary-attestations.md), [ADR-0037](../decisions/0037-layered-pinned-supply-chain-gates.md), [ADR-0038](../decisions/0038-refuse-executable-git-configuration-during-delegation.md), [ADR-0039](../decisions/0039-fail-before-dacl-mutation-under-restricted-windows-tokens.md), [ADR-0040](../decisions/0040-preserve-environment-owned-python-launchers.md), [ADR-0041](../decisions/0041-bounded-asynchronous-overload-responses.md), [ADR-0042](../decisions/0042-local-only-bounded-work-file-inference.md), [ADR-0043](../decisions/0043-prime-stdin-before-windows-child-resume.md), [ADR-0044](../decisions/0044-preclose-bounded-windows-child-stdin.md) |
| [AR-18](issue-AR-18-work-unit-paths-with-spaces.md) | [`c7e06fd`](../worklog/README.md), [`a096236`](../worklog/README.md) | [ADR-0042](../decisions/0042-local-only-bounded-work-file-inference.md) |
| [AR-19](issue-AR-19-bounded-overload-responses.md) | [`a096236`](../worklog/README.md) | [ADR-0017](../decisions/0017-sanitized-server-error-boundary.md), [ADR-0029](../decisions/0029-secure-local-dashboard-and-bounded-observability.md), [ADR-0041](../decisions/0041-bounded-asynchronous-overload-responses.md) |
| [AR-20](issue-AR-20-full-history-ledger-ci.md) | [`26fd65a`](../worklog/README.md) | [ADR-0025](../decisions/0025-self-contained-linked-documentation.md), [ADR-0037](../decisions/0037-layered-pinned-supply-chain-gates.md) |
| [AR-21](issue-AR-21-fully-resume-windows-children.md) | [`26fd65a`](../worklog/README.md) | [ADR-0035](../decisions/0035-authoritative-bounded-provider-chain.md), [ADR-0043](../decisions/0043-prime-stdin-before-windows-child-resume.md), [ADR-0044](../decisions/0044-preclose-bounded-windows-child-stdin.md) |
| [AR-22](issue-AR-22-concurrent-storage-acl-repair.md) | [`26fd65a`](../worklog/README.md) | [ADR-0012](../decisions/0012-canonical-sqlite-audit-store.md), [ADR-0039](../decisions/0039-fail-before-dacl-mutation-under-restricted-windows-tokens.md) |
| [AR-23](issue-AR-23-hosted-windows-powershell-gate.md) | pending | None; test-only hosted-runner allowance |

## Dependency summary

- `AR-03` is complete with truthful maturity boundaries. The exact-confirmed
  Windows Codex 0.144.1 isolated-profile canary passed routing, evidence, and
  header finalization. Its one-invocation trust bypass does not establish
  durable real-profile `/hooks` trust or Linux Codex maturity; absent Claude
  Code, Hermes, and OpenClaw installations remain contract-only.
- `AR-05` is complete locally: guided configuration writes the authoritative
  bounded provider chain.
- `AR-06` is complete locally. Codex 0.144.1 completed an authorized keyless
  judge selection through the current authenticated CLI session; no Agency API
  key was configured or supplied.
- `AR-04` is complete locally. In an isolated Codex profile, the installed
  control skill and MCP server exact-confirmed disable and enable transitions,
  observed both effective states in live conversation turns, and ended enabled.
- `AR-16` and `AR-17` still block the release-readiness gate in `AR-07`
  pending hosted CI, review/merge, and clean-tree/worklog evidence. The
  `AR-03`, `AR-05`, `AR-06`, `AR-08`, `AR-09`, `AR-10`, `AR-11`,
  `AR-12`, `AR-13`, `AR-14`, and `AR-15` dependencies are complete locally.
- `AR-18` records the work-unit path-with-spaces bug surfaced by final Windows
  validation. Its fix is part of the reviewed portability branch and blocks
  `AR-17` until hosted CI and merge complete.
- `AR-01` is implemented and its tracker issue is closed.
- `AR-08` is implemented and its tracker issue is closed.
- `AR-09` is complete locally and prevents tests from escaping their explicit
  profile and temporary-directory boundaries.
- `AR-10` is complete locally and supplies the evidence-integrity prerequisite
  for trustworthy host telemetry and dashboard views.
- `AR-11` is complete locally and supplies the quantitative accuracy,
  determinism, concurrency, and performance release gates.
- `AR-12` is complete locally, including an isolated Ubuntu/WSL wheel and
  authenticated packaged-dashboard result.
- `AR-13` depends on the packaged dashboard from `AR-12` and adds the
  user-scoped Windows/Linux service lifecycle, installation opt-out, and shared
  dashboard/CLI configuration boundary. Its local acceptance criteria are
  complete.
- `AR-14` is complete locally: the installed surface is a genuinely live
  signal observatory with source-owned visualizations, accessible motion,
  adaptive polling, `60/60` JavaScript tests at exact line/branch/function
  coverage, and authenticated browser evidence.
- `AR-15` is complete locally: bounded authenticated request draining prevents
  Windows from replacing JSON rejection responses with TCP resets, and the HTTP
  fixtures no longer leak a POSIX-only configuration path.
- `AR-16` corrects Python 3.12 slotted-backend parsing and WSL interop capability
  handling. Ubuntu 24.04 WSL/Python 3.12 passed `2215` tests with `16` skips,
  plus both performance tests, from native ext4. A clean final wheel also passed
  packaged MCP, dashboard, configuration, asset, and four-host bundle smoke;
  the hosted matrix remains in progress.
- `AR-17` is the integrated production-hardening gate. It records the security,
  modularity, browser, host-contract, cross-platform suite, and live Codex work
  in this pass. Final local coverage, security, performance, artifact, isolated
  install, and isolated-profile Codex header-canary gates pass. Hosted CI,
  review/merge, and worklog/clean-tree closure remain pending.
- `AR-19` records the saturated-server Windows reset and accept-loop blocking
  bugs surfaced by final warning-strict validation. Its separately bounded
  overload workers block `AR-17` until hosted CI and merge complete.
- `AR-20` records the synthetic-merge and shallow-history mismatch in the
  history-derived worklog gate. Its targeted canonical-head checkout blocks
  `AR-17` until the hosted documentation-ledger job passes and the fix is
  merged.
- `AR-21` records the hosted PowerShell stdin race and the Windows native
  resume helper's incorrect ownership boundary. Its preclosed bounded-input
  contract and fail-closed single-count resume block `AR-17` until both hosted
  Windows versions pass and the fix is merged.
- `AR-22` records concurrent Store instances racing the same SQLite sidecar
  ACL. Its process-wide repair critical section and identity-checked sidecar
  retry block `AR-17` until the hosted Windows matrix and merge pass.
- `AR-23` records hosted Windows PowerShell cold-start variance exhausting the
  integration-only 20-second allowance. Its bounded 60-second test margin
  blocks `AR-17` until both hosted Windows versions pass and the fix is merged.

## Status conventions

- `open`: accepted into the roadmap but not complete.
- `in_progress`: implementation is underway and has an active owner.
- `blocked`: progress depends on an unresolved prerequisite.
- `done`: acceptance criteria are satisfied, even if tracker synchronization is waiting for approval.
- `wont_do`: deliberately declined, with the reason retained in the issue document.

## Tracker synchronization

1. Create tracker issues only after explicit approval for outward-facing changes.
2. Prefix each tracker title with its stable ID, for example `[AR-03] Prove supported-host integrations`.
3. Add the epic label represented by the document's `epic` field.
4. Write the tracker-assigned URL into the issue document's `tracker_url` and the mapping table above.
5. Keep roadmap and tracker status aligned; document any temporary mismatch explicitly.
