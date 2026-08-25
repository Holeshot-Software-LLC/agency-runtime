---
title: "Worklog detail: Add guided setup journey"
status: active
category: worklog
created: 2026-08-25
updated: 2026-08-25
tags: [onboarding, cli, dashboard, documentation]
related:
  - docs/roadmap/issue-AR-290-end-to-end-guided-setup.md
  - docs/roadmap/handoffs/issue-AR-290.md
  - docs/decisions/0172-compose-first-run-setup-from-guarded-owner-operations.md
  - README.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 21243e7e55859017c5d8f486eadd1b17fd8de482
short: 21243e7e
date: 2026-08-25
pr: null
related_issues:
  - docs/roadmap/issue-AR-290-end-to-end-guided-setup.md
---

# Worklog detail: Add guided setup journey

## Purpose

Give a first-time consumer one canonical setup path without asking them to
reconstruct provider configuration, native harness wiring, dashboard service
installation, diagnostics, and deterministic smoke from separate commands.
Keep the public README useful to both a person and an installation agent while
stating the prerelease and live-evidence limits plainly.

## Approach

Add `agency setup` as a thin orchestrator over the existing guarded command
callbacks. Retain existing config by default, validate before any native
install, make host and dashboard scope explicit, run doctor after a partial
install, and keep deterministic smoke optional. Mirror the sequence in the
dashboard Settings view with bounded posture derived from current projections,
provider-editor navigation, and inert command copies. Rewrite the README entry
path around a quick start, setup diagram, provider/current-state matrices, and
a paste-ready interview prompt that never carries secret values.

## Challenges encountered

The sandbox could not establish the repository's host-private scratch
attestation and Node test-runner child process. The same focused commands ran
successfully at the approved private boundary. Decision conformance was kept
source-fingerprinted and untouched while it exercised 160 separate mutation
copies. The machine's supplied Jina credential was already present in chat and
was not copied into argv, files, logs, or evidence.

## Decisions and alternatives

ADR-0172 owns the compose-versus-duplicate decision. Expanding
`agency configure` was rejected because it would conflate a stable provider
wizard with native trust and service mutations. A dashboard host-install API
was rejected in favor of owner-attended terminal commands. Optional learned
recall remains an advanced post-primary-provider choice; typed recall is the
safe first-run default.

## Verification

- Focused setup/config/parser/install/dashboard-service coverage passed 255
  tests; final setup/parser coverage passed 32 tests with warnings as errors.
- The named warning-strict fast Python spine plus setup coverage passed 849
  tests with 20 skips.
- All 136 dashboard UI tests passed.
- Full Ruff lint and format checks passed across 693 files.
- Metadata, policy availability, worklog, and documentation checks passed for
  811 Markdown files; `git diff --check` passed.
- Routing evaluation passed every gate, and deterministic source smoke passed
  all eight checks across the Store, roster/parity, and five generated hosts.
- Decision conformance passed its baseline, killed all 160 curated mutations,
  reported zero survived/invalid results, and proved source inputs unchanged.
- Read-only GitHub checks found no release, tag, AR-290 issue, or AR-289/AR-290
  pull request.

## Follow-ups

Install this exact local checkpoint, refresh safely detected harnesses and the
dashboard, validate the retained config, and run installed deterministic smoke.
Learned recall stays typed-only until a rotated Jina key is supplied privately.
Tracker creation, push, PR, hosted matrices, signing, tag, and release remain
pending their separate authorization and release gates.
