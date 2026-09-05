---
title: "AR-348: strict_independence is enforced nowhere in production"
status: in_progress
category: roadmap
created: 2026-09-01
updated: 2026-09-05
tags: [workforce, hiring, security, configuration]
related:
  - docs/roadmap/acceptance/issue-AR-348.md
  - docs/decisions/0153-adopt-per-stage-inference-profile-routes.md
  - docs/decisions/0221-enforce-hiring-independence-on-resolved-provider-chains.md
  - docs/roadmap/acceptance/evidence/AR-348-strict-independence-20260905.md
  - docs/roadmap/issue-AR-235-autonomous-gap-hiring-with-isolated-security-review.md
  - docs/roadmap/issue-AR-347-reconcile-tracker-parity-backlog.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-348
priority: p2
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/406
depends_on: []
blocks: []
---

# AR-348: strict_independence is enforced nowhere in production

## Problem

`enforce_strict_independence`
(`agency_runtime/core/inference_profiles.py:362-395`) is defined,
exported, and tested (`tests/test_inference_profiles.py`) but has no
production caller — a repo-wide search finds only its definition and
tests. Setting `inference.strict_independence: true` therefore silently
does nothing: a hiring security reviewer and contract creator on the
same provider are never rejected, defeating the independence control
AR-235 specified.

## Current state

Both unchanged acceptance criteria are satisfied against c9b678a5. The protected
conformance attempt stopped in fixture setup because it inherited umask 0002;
zero mutations ran and source stayed unchanged. A targeted diagnostic reproduced
the same known private-directory boundary. The documented process-local 0077
rerun and merged installed smoke are pending; do not claim the failed gate passed.

Implemented on the working branch under ADR-0221. Focused package: 413 passed,
one existing skip (20.52s); named spine: 1075 passed, three existing skips
(72.29s). The new boundary recheck tests supplement the original 43-case red
matrix. UI/routing/Ruff pass. Two new curated mutations extend conformance to
184 cases; its 17 catalog tests pass. Full protected run, isolated acceptance,
main publication and installed smoke remain pending. Status is not done.

Fresh reproduction against main 6307e17d: 43 new public-entry-point cases yield
20 failures (strict=true does not raise), 23 passes, in 14.14 seconds. The
negative cases cover both critic and security review across explicit/default
profiles, harness routing, the environment harness override, legacy chains,
creator/reviewer/shared content fallbacks, and safety-repair creators. Positive
controls cover strict=false warnings and distinct-provider normal/repair hires.
All provider calls are deterministic fakes; Store effects use temporary databases.
No user configuration, credential, host trust, or Windows runtime is changed.

Found by the AR-347 per-criterion audit of AR-235 (2026-09-01). The
config field exists (`core/config.py:348`, `config_defaults.yaml:97`),
`route_requires_independence` and `INDEPENDENCE_ROUTE_TOKENS` exist,
and same-provider detection is recorded on hiring cases — only the
enforcement call is missing.

## Approach

Keep the existing adapter-plus-model identity and warning-only default. Extend
`enforce_strict_independence` to accept the actual resolved provider chains,
including content fallbacks. Reject overlaps before initial hiring inference
and before an otherwise-used safety-repair call; check the actual critic and
security-review chains at their invocation boundaries. Use the existing
ConfigValidationError, without selecting replacement providers or spending
another model call. Preserve the two original acceptance criteria below.

The original suggestion was a single call at security-review route resolution.
That is insufficient: the helper re-resolves only global profiles, skips legacy
resolution failures, ignores content fallbacks, and cannot identify a later
safety-repair creator. This ticket's proposed implementation is not authoritative.

## Dependencies

None; independent of the AR-235 dashboard plane.

## Acceptance

- [ ] `strict_independence: true` with a same-provider reviewer/creator
      pairing fails the hiring attempt with the documented config
      error, proven by a focused test through the production call path.
- [ ] `strict_independence: false` behavior is unchanged (warning
      recording only).
