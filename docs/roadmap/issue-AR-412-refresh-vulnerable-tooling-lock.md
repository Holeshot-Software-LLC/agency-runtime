---
title: "AR-412: Refresh vulnerable optional-tooling lock entries"
status: in_progress
category: roadmap
created: 2026-09-08
updated: 2026-09-08
tags: [security, dependencies, release, lockfile]
related:
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/roadmap/handoffs/issue-AR-412.md
  - docs/worklog/README.md
  - pyproject.toml
  - uv.lock
supersedes: []
superseded_by: null
type: issue
epic: security
issue_id: AR-412
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/750
depends_on: []
blocks: []
---

# AR-412: Refresh vulnerable optional-tooling lock entries

## Problem

Two open repository Dependabot alerts identify vulnerable versions in uv.lock:
pip 26.1.2 and cryptography 49.0.0. Keeping them in the checked-in resolution
propagates known vulnerable tooling when contributors request those extras.
This is not evidence that Agency's minimal runtime is directly exploitable.

## Current state

`uv lock --upgrade-package pip --upgrade-package cryptography` using uv 0.11.8
resolved all 66 packages in 860ms and changed only the two requested package
records: pip to 26.2.1 and cryptography to 50.0.1, including artifact hashes.
All direct requirements, other pins and the Python >=3.10 floor remain unchanged.
No owner environment was installed, upgraded or relabeled patched.

Dependency provenance from the lock is explicit:

- `security` extra → pip-audit → pip-api → pip.
- `release` extra → twine → keyring → Linux secretstorage → cryptography.
- The default runtime still requests only PyYAML.

The [pip maintainer repair](https://github.com/pypa/pip/pull/14110) removes a
second URL-path decode and hardens download-path joins. Repository alert #2,
GHSA-qwm4-qh6w-59xr, identifies versions below 26.2.0 as affected.
The [cryptography maintainer advisory](https://github.com/pyca/cryptography/security/advisories/GHSA-g6cj-pr64-35w5)
identifies distinguishable PKCS#7 decryption failures, introduced in 44.0.0
and repaired in 50.0.0. Its application-specific attack prerequisites are not
established in Agency. The repository alert labels it high while the maintainer
page labels it moderate; the patch decision does not depend on that difference.

PyPI metadata for [pip 26.2.1](https://pypi.org/pypi/pip/26.2.1/json) declares
Python >=3.10; [cryptography 50.0.1](https://pypi.org/pypi/cryptography/50.0.1/json)
declares >=3.9 excluding 3.9.0/3.9.1. This supports the declared project floor,
not a claim of an executed interpreter compatibility matrix.

## Approach

Refresh only affected transitive package records under ADR-0037. Retain pinned
direct tooling, immutable artifact hashes, minimal runtime dependencies and
optional security/release separation. No new package, resolver policy, scanner
exception, security-product setting or durable architectural decision is needed.

## Dependencies

The existing release/security extras own later installed tooling verification.
The owner's code-first direction defers tests, CI and acceptance; the lock
refresh is implemented, not accepted completion. Hosted alert processing may
lag publication and is observed separately from this source change.

## Acceptance

- [ ] Locked pip and cryptography versions are outside both affected ranges,
      with metadata supporting the project's Python floor.
- [ ] Other resolved packages and runtime/build/tool requirements are unchanged;
      the optional-tool dependency paths are documented accurately.
- [ ] Authorized installed security/release checks establish working tooling
      behavior; historical owner environments are not relabeled patched.
