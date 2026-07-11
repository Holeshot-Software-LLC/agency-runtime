---
title: Roadmap
status: active
category: roadmap
created: 2026-07-10
updated: 2026-07-11
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
| `AR-02` | [Close specialist coverage gaps](issue-AR-02-specialist-coverage-gaps.md) | open | p2 | roster-governance | [#2](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/2) |
| `AR-03` | [Prove supported-host integrations](issue-AR-03-supported-host-integrations.md) | in_progress | p0 | host-integrations | [#3](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/3) |
| `AR-04` | [Add durable runtime controls](issue-AR-04-runtime-controls.md) | in_progress | p1 | operations | [#4](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/4) |
| `AR-05` | [Complete guided provider configuration](issue-AR-05-guided-provider-configuration.md) | open | p1 | provider-configuration | [#5](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/5) |
| `AR-06` | [Implement CLI-authenticated judge providers](issue-AR-06-cli-authenticated-judge-providers.md) | open | p2 | provider-runtime | [#6](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/6) |
| `AR-07` | [Complete public release readiness](issue-AR-07-public-release-readiness.md) | in_progress | p1 | release | [#7](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/7) |
| `AR-08` | [Make documentation self-contained](issue-AR-08-self-contained-documentation.md) | done | p1 | documentation | [#8](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/8) |
| `AR-09` | [Isolate Windows tests from the real user profile](issue-AR-09-windows-test-isolation.md) | done | p0 | testing | [#9](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/9) (open; closure requires approval) |
| `AR-10` | [Make runtime evidence authoritative](issue-AR-10-authoritative-runtime-evidence.md) | done | p0 | observability | [#10](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/10) (open; closure not performed) |
| `AR-11` | [Establish routing accuracy and performance gates](issue-AR-11-routing-evaluation-and-performance.md) | done | p0 | testing | [#11](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/11) (open; closure not performed) |
| `AR-12` | [Ship a secure installed operations dashboard](issue-AR-12-installed-operations-dashboard.md) | done | p1 | operations | [#12](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/12) (open; closure not performed) |
| `AR-13` | [Add an optional cross-platform dashboard service and configuration parity](issue-AR-13-optional-dashboard-service-configuration.md) | done | p1 | operations | [#13](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/13) (open; closure not performed) |

## Traceability

This table links local scope to implementation evidence and durable decisions.
Tracker URLs are also retained in the mapping above because tracker numbers are
not stable internal identifiers.

| Roadmap item | Implementation commits | Governing decisions |
|---|---|---|
| [AR-01](issue-AR-01-selection-explain-receipts.md) | [`42f6580`](../worklog/README.md) | [ADR-0015](../decisions/0015-versioned-selection-explain-receipts.md) |
| [AR-02](issue-AR-02-specialist-coverage-gaps.md) | Pending | [ADR-0013](../decisions/0013-approval-gated-roster-activation.md), [ADR-0021](../decisions/0021-full-companion-policy-with-precedence.md) |
| [AR-03](issue-AR-03-supported-host-integrations.md) | [`17a62dd`](../worklog/README.md) | [ADR-0024](../decisions/0024-native-host-packages-and-minimal-bridges.md), [ADR-0028](../decisions/0028-host-support-maturity-and-reversible-install.md) |
| [AR-04](issue-AR-04-runtime-controls.md) | [`17a62dd`](../worklog/README.md) | [ADR-0010](../decisions/0010-one-command-install-and-reversible-toggle.md), [ADR-0024](../decisions/0024-native-host-packages-and-minimal-bridges.md), [ADR-0028](../decisions/0028-host-support-maturity-and-reversible-install.md) |
| [AR-05](issue-AR-05-guided-provider-configuration.md) | Pending | [ADR-0006](../decisions/0006-config-first-redacted-configuration.md), [ADR-0008](../decisions/0008-ordered-provider-fallback.md) |
| [AR-06](issue-AR-06-cli-authenticated-judge-providers.md) | Pending | [ADR-0008](../decisions/0008-ordered-provider-fallback.md) |
| [AR-07](issue-AR-07-public-release-readiness.md) | [`17a62dd`](../worklog/README.md) | [ADR-0010](../decisions/0010-one-command-install-and-reversible-toggle.md), [ADR-0025](../decisions/0025-self-contained-linked-documentation.md), [ADR-0028](../decisions/0028-host-support-maturity-and-reversible-install.md), [ADR-0029](../decisions/0029-secure-local-dashboard-and-bounded-observability.md), [ADR-0030](../decisions/0030-versioned-quantitative-evaluation-gates.md) |
| [AR-08](issue-AR-08-self-contained-documentation.md) | [`4d17668`](../worklog/README.md) | [ADR-0025](../decisions/0025-self-contained-linked-documentation.md) |
| [AR-09](issue-AR-09-windows-test-isolation.md) | [`a896c81`](../worklog/README.md) | [ADR-0026](../decisions/0026-explicit-test-home-boundaries.md) |
| [AR-10](issue-AR-10-authoritative-runtime-evidence.md) | [`17a62dd`](../worklog/README.md) | [ADR-0007](../decisions/0007-six-line-evidence-header.md), [ADR-0011](../decisions/0011-explicit-delegation-evidence-lifecycle.md), [ADR-0016](../decisions/0016-central-finalization-and-session-correlation.md), [ADR-0027](../decisions/0027-authoritative-runtime-evidence-traces.md) |
| [AR-11](issue-AR-11-routing-evaluation-and-performance.md) | [`17a62dd`](../worklog/README.md), [`d1275c3`](../worklog/README.md) | [ADR-0001](../decisions/0001-layered-specialist-routing.md), [ADR-0015](../decisions/0015-versioned-selection-explain-receipts.md), [ADR-0021](../decisions/0021-full-companion-policy-with-precedence.md), [ADR-0030](../decisions/0030-versioned-quantitative-evaluation-gates.md) |
| [AR-12](issue-AR-12-installed-operations-dashboard.md) | [`17a62dd`](../worklog/README.md) | [ADR-0010](../decisions/0010-one-command-install-and-reversible-toggle.md), [ADR-0012](../decisions/0012-canonical-sqlite-audit-store.md), [ADR-0017](../decisions/0017-sanitized-server-error-boundary.md), [ADR-0027](../decisions/0027-authoritative-runtime-evidence-traces.md), [ADR-0029](../decisions/0029-secure-local-dashboard-and-bounded-observability.md) |
| [AR-13](issue-AR-13-optional-dashboard-service-configuration.md) | [`d1275c3`](../worklog/README.md) | [ADR-0006](../decisions/0006-config-first-redacted-configuration.md), [ADR-0010](../decisions/0010-one-command-install-and-reversible-toggle.md), [ADR-0029](../decisions/0029-secure-local-dashboard-and-bounded-observability.md), [ADR-0031](../decisions/0031-optional-user-dashboard-service-and-shared-configuration.md) |

## Dependency summary

- `AR-03` blocks host-facing controls in `AR-04` and truthful support claims in `AR-07`.
- `AR-05` establishes the configuration path needed to expose `AR-06` cleanly.
- `AR-03`, `AR-04`, `AR-05`, and `AR-06` still block the release-readiness gate in `AR-07`; the `AR-08`, `AR-09`, `AR-10`, `AR-11`, `AR-12`, and `AR-13` dependencies are complete locally.
- `AR-01` is implemented and its tracker issue is closed.
- `AR-08` is implemented and its tracker issue is closed.
- `AR-09` is implemented locally. Its tracker issue remains open until closure is approved.
- `AR-10` is complete locally and supplies the evidence-integrity prerequisite for trustworthy host telemetry and dashboard views. Tracker #10 remains open because closure was not part of this change.
- `AR-11` is complete locally and supplies the quantitative accuracy, determinism, concurrency, and performance release gates. Tracker #11 remains open because closure was not part of this change.
- `AR-12` is complete locally, including an isolated Ubuntu/WSL wheel and
  authenticated packaged-dashboard result. Tracker #12 remains open because
  closure was not authorized.
- `AR-13` depends on the packaged dashboard from `AR-12` and adds the
  user-scoped Windows/Linux service lifecycle, installation opt-out, and shared
  dashboard/CLI configuration boundary. Tracker #13 remains open because
  closure was not part of the tracker-creation authorization.

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
