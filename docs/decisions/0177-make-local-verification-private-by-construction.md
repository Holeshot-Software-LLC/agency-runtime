---
title: "Make local verification private at repository-owned boundaries"
status: accepted
category: decisions
created: 2026-08-26
updated: 2026-08-26
tags: [testing, packaging, security, permissions, developer-experience]
related:
  - docs/roadmap/issue-AR-302-owner-private-local-verification.md
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - scripts/canonicalize_distributions.py
  - tests/conftest.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0177
type: decision
deciders: [maintainers]
---

# ADR-0177: Make local verification private at repository-owned boundaries

## Context

The documented local build and named Python spine can start under a cooperative
POSIX umask of 0002. The wheel producer projects that umask into ordinary raw
members as mode 0664, while pytest creates shared fixture descendants that may
be group-writable. The release canonicalizer previously admitted only the 0600
and 0644 POSIX projections, and configuration trust correctly refused the
group-writable fixture namespace. Operators could make both commands pass with
an undocumented umask and temporary-root preamble, but the repository-owned
creation boundaries should establish their own contracts.

Security tests also create persistent launcher fixtures. Running them through a
Python below a replaceable checkout namespace produces many downstream
refusals, even though one early executable-namespace diagnosis is sufficient.

## Decision

Admit raw mode 0664 only for ordinary non-executable POSIX wheel and sdist file
members, plus mode 0775 for sdist directories, while they remain inside the
builder's independently validated mode-0700 staging directory. Continue to
canonicalize files to exactly 0644 and directories to 0755, retain the exact
RECORD contract, reject executable/special/unreviewed modes, and publish only
canonical mode-0644 artifact files.

At pytest configuration time on POSIX, establish umask 0077 before fixture
storage is created and restore the caller's exact umask during unconfiguration.
Create the shared offline-config namespace explicitly through the production
private-directory helper and harden its file to 0600. Before test execution,
validate `AGENCY_CI_PYTHON` or the selected base interpreter through the same
persistent executable-namespace predicate used by production launchers. An
unsafe interpreter stops once with a bounded instruction to select an OS- or
owner-protected executable.

## Consequences

The documented commands are independent of an ambient cooperative umask. Raw
producer variance converges to identical canonical bytes, and no group-writable
archive or configuration state crosses a trust boundary. Tests that explicitly
exercise other umasks may still set and restore them inside their own bounded
case.

Developers whose virtual environment lives below an untrusted collaborative or
temporary path must name a trusted fixture interpreter. The test process may
still import the reviewed worktree through `PYTHONPATH`; durable launcher
fixtures never treat that worktree interpreter as persistent authority.

## Alternatives

Documenting `umask 0077` as a required operator preamble was rejected because
it leaves correctness outside the repository command. Weakening configuration
or executable namespace validation was rejected because the failed paths are
genuinely replaceable. Accepting arbitrary wheel modes was rejected because the
finite source allowlist is part of the supply-chain boundary. Copying the entire
development environment to a hidden trusted path was rejected because exact
interpreter selection is simpler and auditable.
