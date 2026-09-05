---
title: "AR-405: Make Windows directory-identity regressions portable"
status: open
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [testing, portability, release, windows, linux]
related:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/issue-AR-160-publish-platform-honest-native-release-artifacts.md
  - docs/decisions/0074-build-byte-deterministic-release-artifacts.md
  - tests/test_build_distributions.py
  - scripts/build_distributions.py
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-405
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/675
depends_on: []
blocks: []
---

# AR-405: Make Windows directory-identity regressions portable

## Problem

Two unguarded tests in tests/test_build_distributions.py assume that real
temporary directories carry Windows st_file_attributes. On Linux the attribute
is absent, so both fail before exercising the intended identity boundary:
test_directory_identity_survives_the_directory_being_written_to and
test_directory_identity_still_pins_kind_and_exact_object (lines 530-569).

## Current state

Reproduced on Linux/Python 3.12 at unchanged runtime/test source 6edfa6d8 during
AR-404 triage. Seven focused files returned 443 passed, two skipped and these
two failures in 11.73 seconds. The failing assumptions predate this review
(git blame identifies 71833c5c). No product identity regression is established.
Initial collection also required the repository-pinned setuptools 83.0.0 and
wheel 0.47.0 in the isolated test environment, not merely build isolation.

## Approach

Separate a deterministic synthetic attribute-transition contract from native
platform evidence. Keep portable directory kind/object replacement checks
active on Linux; bound any real Windows attribute observation to Windows and
its actual filesystem behavior. Do not skip the entire identity test family,
change production identity semantics to satisfy a fixture, or call a simulated
Windows transition a live Windows build. Retain the original failure evidence.

## Dependencies

AR-160 retains current release artifact proof. ADR-0074's exact filesystem and
Git-blob integrity boundary must not be weakened. This test-only correction is
a separate bounded package from the documentation cleanup that discovered it.

## Acceptance

- [ ] Synthetic tests prove that changing only the volatile Windows attribute does not alter directory identity, while directory kind or exact-object replacement still does.
- [ ] The complete tests/test_build_distributions.py file passes on Linux without suppressing its portable identity assertions; native-only observations are explicitly scoped.
- [ ] Relevant current Windows evidence is retained when available, and missing native Windows execution remains explicit rather than claimed from a simulation.
