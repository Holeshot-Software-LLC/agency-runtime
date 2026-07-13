---
title: "Capability-aware dependency review fallback"
status: active
category: worklog
created: 2026-07-13
updated: 2026-07-13
tags: [worklog, ci, security, supply-chain]
related:
  - docs/roadmap/issue-AR-07-public-release-readiness.md
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/RELEASE_CHECKLIST.md
  - docs/THREAT_MODEL.md
supersedes: []
superseded_by: null
type: worklog
commit: a60b41c47edaa357dec543358493bbeabf017d29
short: a60b41c
date: 2026-07-13
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/18
related_issues:
  - docs/roadmap/issue-AR-07-public-release-readiness.md
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
---

# Worklog detail: Preserve dependency audit without paid security

## Purpose

Keep pull-request dependency enforcement operational in private repositories
that do not expose GitHub's dependency-review API, without silently enabling a
potentially billable organization security product.

## Approach

- Probe the same base-versus-head dependency-graph capability needed by
  GitHub's native dependency-review action.
- Run the pinned native action when the API is available.
- Treat only the documented unavailable responses as a fallback condition.
- Install the pinned security extra and run the strict exact installed-runtime
  vulnerability audit when native review is unavailable.
- Fail closed on unexpected probe responses instead of silently bypassing both
  controls.

## Challenges encountered

The hosted action failed before examining dependencies because this private
repository has GitHub Code Security disabled. The corresponding dependency
comparison endpoint returned HTTP 404. Enabling the product can affect
organization billing, so the workflow needed a capability-aware path rather
than changing account settings as an implementation side effect.

## Decisions and alternatives

- **Enable GitHub Code Security.** Rejected as an implicit fix because billing
  and organization policy are outside a repository change.
- **Delete the dependency-review workflow.** Rejected because it would discard
  richer diff review when the repository becomes public or gains the licensed
  capability.
- **Allow the unsupported action to fail.** Rejected because that blocks every
  private-repository pull request without producing security evidence.

## Follow-ups

- Keep the native action and fallback audit pins current through reviewed
  Dependabot changes.
- When repository visibility or licensing changes, confirm the capability probe
  selects native dependency review and retain the fallback for portable forks.
