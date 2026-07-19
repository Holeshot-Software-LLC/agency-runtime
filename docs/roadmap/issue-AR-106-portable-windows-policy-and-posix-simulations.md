---
title: "AR-106: Make Windows policy identity and POSIX simulations portable"
status: in_progress
category: roadmap
created: 2026-07-19
updated: 2026-07-19
tags: [testing, windows, portability, security]
related:
  - .github/workflows/ci.yml
  - .github/workflows/dependency-review.yml
  - docs/roadmap/issue-AR-104-run-hosted-portability-gates-in-trusted-boundaries.md
  - docs/decisions/0021-full-companion-policy-with-precedence.md
  - docs/decisions/0030-versioned-quantitative-evaluation-gates.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/decisions/0066-package-audited-roster-and-sync-quarantined-deltas.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-106
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/108"
depends_on: []
blocks:
  - AR-104
---

# AR-106: Make Windows policy identity and POSIX simulations portable

## Problem

The hosted Windows Python 3.10 and 3.14 matrix exposed several portability defects:
custom policy ownership compared the textual SDDL owner instead of the owner's
binary SID identity, one configuration test assumed a POSIX root on Windows,
and POSIX-branch simulations required `os.fchmod` even where the Windows Python
module does not export it. An isolated Python 3.10 child also emitted help text
in the Windows code page while its UTF-8 parent decoded the pipe. Those failures
masked the actual cross-platform release signal. On Python 3.14, a file added
during roster ingestion also evaded a directory-`mtime`-only mutation receipt.
The private-repository dependency-review fallback separately spent its entire
timeout installing unused security extras and did not prove the minimal runtime
dependency set.

## Current state

Windows can render an owner using a well-known SDDL alias even when that alias
resolves to the exact current TokenUser SID. The shared ACL layer already has a
native fail-closed binary SID comparison, but the custom-policy gate does not
use it. Several platform-simulation tests also mutate or delegate to the real
Windows `os` module while exercising POSIX-only calls.

## Approach

Reuse the shared native SID matcher for the custom-policy owner check while
retaining the requirement that the owner be exactly the effective user. Make
test paths native and absolute. Give simulated POSIX `os` facades the explicit
POSIX functions they exercise so the tests remain isolated from host-module
capabilities. Configure the package-owned bootstrap's output streams as UTF-8
before any host protocol or CLI module emits content. Bind roster discovery to
bounded, deterministic, no-follow entry snapshots at the manifest root and
every traversed directory, then revalidate those receipts after file reads.
Keep both discovery and revalidation within one source-wide entry budget. Make
the dependency fallback install the runtime and pinned audit tool only, while
still resolving the runtime's declared dependencies normally.

## Dependencies

None. This issue blocks the final hosted portability gate in AR-104.

## Acceptance

- [ ] An SDDL owner alias is accepted only when native binary comparison proves it is the current TokenUser SID.
- [ ] Foreign and broader trusted-system owners remain rejected for custom policy files.
- [ ] Configuration path tests use native absolute paths on Windows and POSIX.
- [ ] POSIX security-branch simulations pass on Windows without changing the process-wide `os` module.
- [ ] Package-owned isolated launchers emit deterministic UTF-8 on every supported Python version.
- [ ] Roster ingestion detects added, removed, renamed, or replaced entries without relying on directory `mtime` behavior.
- [ ] Roster directory discovery rejects links, reparse points, and special entries, and revalidates bounded source-wide receipts after all file reads.
- [ ] The dependency-review fallback installs and audits the exact runtime dependency set within its hosted timeout.
- [ ] Hosted Windows Python 3.10 and 3.14 jobs pass with warning-strict tests.
- [ ] Documentation, lint, coverage, and tracker validation pass.
