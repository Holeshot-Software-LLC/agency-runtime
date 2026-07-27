---
title: "Freeze every launch-critical executable identity before process creation"
status: accepted
category: decisions
created: 2026-07-16
updated: 2026-07-27
tags: [security, processes, executables, delegation, portability]
related:
  - docs/roadmap/issue-AR-176-align-full-gate-contract-fixtures.md
  - docs/roadmap/issue-AR-60-frozen-executable-identity.md
  - docs/roadmap/issue-AR-65-reject-cross-account-executable-namespaces.md
  - docs/roadmap/issue-AR-108-atomic-owned-process-containment.md
  - docs/roadmap/issue-AR-147-parse-complete-windows-acl-descriptors.md
  - docs/roadmap/issue-AR-164-reject-repository-ancestor-path-poisoning.md
  - docs/roadmap/issue-AR-187-isolate-native-host-lifecycle-cwd.md
  - docs/decisions/0038-refuse-executable-git-configuration-during-delegation.md
  - docs/decisions/0040-preserve-environment-owned-python-launchers.md
  - docs/decisions/0073-own-subprocess-trees-atomically.md
  - docs/decisions/0106-isolate-native-host-lifecycle-working-directories.md
  - docs/THREAT_MODEL.md
  - docs/TROUBLESHOOTING.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0055
type: decision
deciders: [maintainers]
---

# ADR-0055: Freeze every launch-critical executable identity before process creation

## Context

Argument-array execution prevents shell interpolation, but it does not make
command discovery safe. An empty, dot, relative, or current-directory `PATH`
entry can select a hostile repository file. A validated native executable,
interpreter, or wrapper can also be replaced before process creation, changing
what runs without changing the argv text.

Delegation is especially exposed because it intentionally operates near
untrusted repository content and may invoke a host CLI, interpreter, wrapper,
or Git. The launch contract must bind approval to filesystem identity, not only
to a command name or path string. Generated host and dashboard launchers remain
installed across processes and reboots, so their approval also needs a durable
content-bound manifest rather than only an in-memory pre-launch snapshot.

## Decision

Resolve launch commands only from an absolute explicit path or absolute
non-current-directory `PATH` entries. Reject relative explicit executables,
Windows links and reparse points, non-regular files, canonical targets inside
the delegated repository, and Windows native launchers without an allowlisted
native suffix. Require every canonical executable parent namespace to exclude
cross-account mutation: root- or current-user-owned, non-writable POSIX chains
without a default ACL at the final parent, or a Windows DACL that prevents
untrusted writes. For a transient process launch, resolve a POSIX launcher
symlink to its real executable target so a mutable symlink is not left in the
final argv. Persistent launchers use the separate manifest contract below to
preserve environment-owned virtual-environment spelling. Resolve Git and
operating-system utilities through the same trusted absolute-path boundary.
Before any Git-assisted root discovery, derive repository ancestors only from
inert filesystem markers. Exclude each complete ancestor boundary during both
`PATH` search and final lexical/resolved candidate validation so a nested
working directory cannot make a repository-owned sibling executable eligible.

Represent prepared argv as a typed value that carries every launch-critical
artifact. Canonicalize each artifact and freeze its path, device, inode,
type/mode, size, modification time, and Windows file attributes. Freeze both the
native executable and any interpreter or wrapper that participates in the
launch. Apply the same boundary to service-manager commands. Immediately before
process creation, re-read every artifact and fail closed unless the full
identity matches and its parent namespace remains trusted. Continue to execute
an argument array without a shell and retain bounded input, output, time,
environment, and process tree controls.

Repository-local Git configuration and executable attributes remain disabled
during delegated mutations under ADR-0038. This decision adds discovery and
artifact identity protection; it does not weaken those Git controls or replace
environment-owned virtual-environment launcher preservation under ADR-0040.

For persistent dashboard and host-adapter launchers, record both the exact
interpreter and package-owned `_bootstrap.py` in the managed ownership
manifest. Persist their lexical path identity, resolved target identity,
content digest, link target where applicable, ownership, and namespace trust.
Environment-managed POSIX interpreter symlinks retain their lexical argv
spelling so virtual environments continue to resolve the installed package,
while both the link and resolved file remain attested. Revalidate the manifest
at inspection and immediately before registration, start, or restart. Drift or
an unprovable identity makes host maturity stale and blocks execution until a
reviewed reinstall.

## Consequences

- A repository cannot gain execution merely by placing a familiar command name
  in its working directory or a relative `PATH` entry.
- Replacing or mutating a frozen executable, wrapper, or interpreter prevents
  the launch.
- Persistent service and adapter definitions cannot silently continue through
  an interpreter or package-bootstrap replacement after installation.
- Windows and POSIX share one high-level contract while keeping native suffix,
  reparse-point, and executable-bit checks platform appropriate.
- Test seams and custom backends must provide real absolute executable
  identities instead of relying on ambient command lookup.
- Revalidation narrows the substitution window but is not a claim of isolation
  from the same account between the final check and the operating system's
  executable open; that account remains inside the documented trust boundary.

## Alternatives

- Trust the first `PATH` match. Rejected because search order can include the
  working directory or another repository-controlled location.
- Validate only the final path string. Rejected because the object at that path
  can be replaced without changing the string.
- Hash executable contents only. Rejected because identity, kind, wrapper
  relationships, and path-bound trust still matter, and hashing every large
  runtime artifact would add avoidable startup cost.
- Copy every executable into an Agency-owned directory. Rejected because it
  forks host update and signature ownership and breaks environment-managed
  launchers.
