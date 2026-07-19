---
title: "Worklog detail: Harden hosted runtime portability"
status: active
category: worklog
created: 2026-07-19
updated: 2026-07-19
tags: [ci, portability, windows, linux, security, python, node]
related:
  - docs/roadmap/README.md
  - docs/decisions/0030-versioned-quantitative-evaluation-gates.md
  - docs/decisions/0040-preserve-environment-owned-python-launchers.md
supersedes: []
superseded_by: null
type: worklog
commit: 0df5050b674d312d7c13a991affc0c57a75298d3
short: 0df5050
date: 2026-07-19
pr: "https://github.com/Holeshot-Software-LLC/agency-runtime/pull/104"
related_issues:
  - docs/roadmap/issue-AR-104-run-hosted-portability-gates-in-trusted-boundaries.md
---

# Worklog detail: Harden hosted runtime portability

## Purpose

Close the portability and resource-safety defects exposed by PR #104's hosted
Windows, Linux, Python 3.10, Python 3.14, and artifact-smoke lanes without
weakening the runtime's production trust boundaries.

## Approach

Hosted Windows jobs can now bootstrap one owner-private CI root atomically with
an exact protected DACL while holding and revalidating the trusted parent
identity. Normal runtime directory creation remains strict; only the explicit
CI bootstrap receives this narrowly scoped authority, and every descendant
returns to the ordinary validation path.

Hosted Node executables are copied into the private run boundary through a
bounded, identity-stable, hash-verified mirror. A durable manifest binds the
source identity, target identity, size, and digest, so reuse is idempotent and
tampering, replacement, or incomplete collisions fail closed. Artifact smoke
prefers this verified mirror without relaxing production executable checks.

Configuration loading now retries boundedly until both file identity and all
materialized environment inputs are stable. Each attempt consumes one frozen
environment snapshot, preventing live-environment ABA from changing credential
fallbacks mid-load. The selected config path is the call's explicit
linearization point; a later `AGENCY_CONFIG_PATH` change selects a distinct
cache entry on the next call.

Python compatibility fixes provide exception notes on 3.10, normalize terminal
`Z` timestamps before `fromisoformat`, use the portable `lstat` test seam on
3.14, and close `HTTPError` responses before raising deterministic failures.

## Challenges encountered

GitHub's Windows process token and runner-owned tool directories are
intentionally unsuitable for production private storage and executable trust.
The first bootstrap design trusted too broad an ancestor, and the first config
stability loop considered only file identity. Independent review caught both
gaps. The final implementation pins the exact parent namespace, validates it
before and after atomic creation, and snapshots every environment value that
can affect materialization.

The local Codex sandbox also runs under a restricted Windows token. Direct
release audits therefore had to execute inside the same owner-private HOME and
TEMP boundary used by hosted CI; failure outside that boundary was the expected
security behavior, not a reason to bypass it.

## Decisions and alternatives

Production storage and executable validation remains fail closed. Rejected
alternatives were loosening ACL requirements for hosted runners, trusting the
shared Node tool cache directly, repairing pre-existing permissive directories,
or accepting a best-effort config read during concurrent file or environment
changes.

The CI root bootstrap is explicit and non-general-purpose. The Node mirror is
content- and identity-bound rather than PATH-bound. Config path selection is
linearized once per call, while configuration values are materialized from a
single immutable environment snapshot.

## Verification

- Focused hosted-boundary and compatibility suites: 263 passed and 1 skipped.
- Expanded config concurrency suite: 71 passed, including file churn,
  environment churn, dynamic-key ABA, and default-path transition regressions.
- Dependency audit: no known vulnerabilities in the owner-private boundary.
- Delegation evaluation: all 12 cases passed in the owner-private boundary.
- Ruff, formatting, Bandit, release hygiene, documentation validation, routing
  evaluation, and whitespace checks passed.
- Independent security review found no remaining P0 or P1 defect; the one P2
  config race it found was fixed and re-reviewed clean.

## Follow-ups

Run PR #104's hosted matrix and immutable artifact smoke against this commit.
AR-104 remains in progress until every hosted Windows, Linux, Python, coverage,
performance, dashboard, security, build, and artifact gate is green.
