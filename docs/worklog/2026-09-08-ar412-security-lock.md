---
title: "Refresh two vulnerable optional-tooling lock entries"
status: active
category: worklog
created: 2026-09-08
updated: 2026-09-08
tags: [security, dependencies, lockfile]
related:
  - docs/roadmap/issue-AR-412-refresh-vulnerable-tooling-lock.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 7e66ea8412a3223f4c5601f598b233ec7b3251ce
short: 7e66ea84
date: 2026-09-08
pr: null
related_issues:
  - docs/roadmap/issue-AR-412-refresh-vulnerable-tooling-lock.md
---

# Worklog detail: Refresh vulnerable optional-tooling lock entries

## Purpose

Remove the two presently alerted package versions from the reproducible optional
release/security tool resolution without changing core runtime dependencies.

## Approach

Targeted uv lock upgrades pip to 26.2.1 and cryptography to 50.0.1. Preserve
the other 64 package records and every direct requirement. Canonical AR-412
links the primary advisories, PyPI metadata, exact dependency paths and tracker.

## Challenges encountered

The repository alert's runtime-scope label does not describe the optional-extra
graph; source inspection is needed to avoid overstating core exposure. The
maintainer's cryptography severity differs from the aggregate alert. Neither
difference justifies keeping a vulnerable pin. An initial read-only uv tree
command used unsupported --all-extras and exited2; no mutation occurred.

## Decisions and alternatives

Apply ADR-0037; no new policy. Do not broaden to all-dependency updates or add
unneeded core dependencies. Installed owner tools remain untouched.

## Verification

The resolver completed in 860ms; artifact URLs/hashes changed only with the
two package versions. Primary metadata supports Python >=3.10. Source and
record checks are distinct from tests: no pytest, CI, installed tooling or
acceptance execution is claimed.

## Follow-ups

Publish a normal PR. Later authorized isolated tooling checks and acceptance
remain AR-412 work; issue stays in_progress.

Source `7e66ea84` is the exact targeted lock refresh. The successful corrected read-only `uv tree --locked --universal --invert --package pip --package cryptography` confirms both optional-extra dependency paths without changing the lock or installing any package.

Integration `362a6c1e` preserves the published installed-delivery and retained Hermes purpose-boundary records with their faithful merge ledgers. Independent source ownership and deferred execution remain unchanged.
