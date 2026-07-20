---
title: "Bind isolated canaries to explicit Agency modes"
status: accepted
category: decisions
created: 2026-07-20
updated: 2026-07-20
tags: [canary, runtime-control, codex, claude, testing, evidence]
related:
  - docs/roadmap/issue-AR-111-honor-global-mode-in-isolated-canaries.md
  - docs/roadmap/issue-AR-57-durable-agency-wide-master-switch.md
  - docs/roadmap/issue-AR-79-installed-isolated-header-proof.md
  - docs/roadmap/issue-AR-88-compare-agency-native-outcomes.md
  - docs/decisions/0036-capability-bound-host-canary-attestations.md
  - docs/decisions/0053-durable-fail-enabled-master-control.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0076
type: decision
deciders: [maintainers]
---

# ADR-0076: Bind isolated canaries to explicit Agency modes

## Context

An isolated Codex or Claude canary replaces the user home so credentials and
managed plugin registration can be tested without trusting the real profile.
The Agency-wide master switch also lives below the user home. Without an
explicit projection, an isolated profile created while Agency is globally off
materializes the default enabled state and can falsely report an Agency-on run
as a native-only comparison.

Agency-on and native-only trials also require opposite evidence. Agency-on must
prove the installed response header and correlated runtime activity. Native-only
must prove that the same registered integration was bypassed and emitted no
Agency activity.

## Decision

Every isolated live canary declares either `agency` or `native-only` mode and
uses a distinct exact confirmation phrase. Before host execution, read the real
profile's authoritative master-control document without the enforcement
fail-enabled fallback. Require its enabled state to match the requested mode,
then materialize and re-read that state in the owner-private isolated home.

Re-read the real authoritative document after invocation and immediately before
success. Any read failure or document drift fails the canary closed.

Agency mode retains the existing header, nonce-bound evidence, profile-identity,
and durable-attestation requirements. Native-only mode requires a successful
nonempty response, proven isolated plugin registration or load request, no valid
Agency header, and zero new rows in every runtime-evidence category. A
native-only success never creates an Agency canary attestation.

## Consequences

- An isolated home can no longer silently reset an off comparison to Agency-on.
- Paired trials are explicit, reproducible, and machine-distinguishable.
- Concurrent control changes invalidate the observation instead of producing
  ambiguous evidence.
- Native-only proves bypass behavior without weakening or uninstalling the
  native integration.
- Operators must intentionally toggle the global switch and use the matching
  confirmation phrase for each half of an A/B comparison.

## Alternatives

- **Copy the control file as an opaque artifact.** Rejected because the isolated
  namespace must apply its own owner/path validation and durable publication.
- **Pass only an environment override.** Rejected because host hooks enforce the
  canonical durable control boundary, not an untrusted process-local hint.
- **Infer native-only from a missing header.** Rejected because a broken hook,
  empty response, emitted evidence, or control race could look identical.
- **Uninstall the plugin for native-only trials.** Rejected because that tests a
  different installation state and cannot prove the master bypass works.
