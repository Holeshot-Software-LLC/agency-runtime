---
title: "Isolate native host lifecycle working directories"
status: accepted
category: decisions
created: 2026-07-27
updated: 2026-07-27
tags: [security, processes, host-integrations, installation, codex]
related:
  - docs/roadmap/issue-AR-164-reject-repository-ancestor-path-poisoning.md
  - docs/roadmap/issue-AR-187-isolate-native-host-lifecycle-cwd.md
  - docs/decisions/0055-freeze-executable-identity-before-launch.md
  - docs/decisions/0091-least-privilege-subprocess-environments.md
  - docs/decisions/0104-refresh-existing-codex-through-an-exact-attended-transaction.md
  - docs/THREAT_MODEL.md
  - agency_runtime/core/installer_native.py
  - agency_runtime/core/prepared_codex_install.py
supersedes: []
superseded_by: null
id: ADR-0106
type: decision
deciders: [maintainers]
---

# ADR-0106: Isolate native host lifecycle working directories

## Context

ADR-0055 recursively excludes the target working tree from executable discovery
and final artifact acceptance. That is required for delegation and repository
operations, but native plugin inventory and registration do not operate on a
repository. Using an arbitrary ambient CWD as their target boundary creates two
opposite failures: a broad directory such as the user's home rejects legitimate
user-installed tools below it, while simply removing CWD exclusion would admit
repository-controlled sibling executables.

Native lifecycle children also have no product reason to inherit a repository
or other ambient working directory. Discovery, child PATH construction, final
artifact acceptance, and the actual process CWD must describe one coherent
authority boundary.

## Decision

Run ordinary native host lifecycle commands from a newly allocated
owner-private ephemeral directory. Use that exact directory as the current
directory for PATH sanitization, executable preparation, identity freezing, and
process execution. Retain every ambient ancestor that carries a recognized
repository marker as a recursive forbidden root, discovered by inert filesystem
inspection without running Git. The private launch tree is also forbidden.

For the prepared existing-Codex refresh, use the already-existing validated
owner-private Agency runtime root as the stable working directory for the full
frozen transaction. Discover the bare Codex command through the sanitized PATH,
freeze its complete canonical launcher identity, bind the least-privilege
environment, validate the private working directory before every native call,
and execute every inventory and registration step from that directory.

The shared repository helper keeps its existing default behavior. Only callers
whose operation is explicitly repository-independent may omit the ordinary
ambient CWD tree, and they must retain all marker-derived repository ancestors
plus an explicit trusted launch tree. Shell-free argv, namespace trust, bounded
I/O and time, process-tree containment, and immediate identity revalidation are
unchanged.

## Consequences

- Native install and inspection work is independent of where the operator ran
  `agency`, including a broad home directory.
- Repository PATH poisoning remains rejected even when lifecycle execution
  moves to a private working directory.
- Native children cannot consult repository-controlled relative files through
  their process CWD.
- Each ordinary native command creates and removes a small private ephemeral
  directory; prepared Codex refreshes reuse the already validated private
  runtime root so the working directory survives the attended transaction.
- Custom command-runner test seams retain their prior ambient behavior because
  they do not execute a production child process.

## Alternatives

- **Stop excluding the ambient CWD globally.** Rejected because it reopens
  repository and sibling-directory executable poisoning.
- **Special-case the user's home as trusted.** Rejected because path names are
  not authority evidence and a repository may live below the home.
- **Run lifecycle commands from the host executable directory.** Rejected as
  the general policy because Agency does not own that directory and the child
  has no need to treat it as working data.
- **Require operators to run installation only from a particular directory.**
  Rejected because correctness and security must not depend on undocumented
  shell location.
