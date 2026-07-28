---
title: "Resolve updates immutably and keep application attended"
status: accepted
category: decisions
created: 2026-07-28
updated: 2026-07-28
tags: [release, security, cli, dashboard, operations]
related:
  - docs/roadmap/issue-AR-188-add-immutable-update-discovery.md
  - docs/roadmap/issue-AR-190-make-upgrade-plans-runnable-in-uv-tools.md
  - docs/worklog/README.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/decisions/0091-least-privilege-subprocess-environments.md
  - docs/decisions/0096-require-operator-presence-for-persistent-controls.md
  - docs/decisions/0099-separate-reproducible-unsigned-builds-from-signed-delivery.md
  - docs/decisions/0104-refresh-existing-codex-through-an-exact-attended-transaction.md
  - docs/THREAT_MODEL.md
  - docs/RELEASE_CHECKLIST.md
  - agency_runtime/core/update_service.py
  - agency_runtime/cli/upgrade_commands.py
supersedes: []
superseded_by: null
id: ADR-0107
type: decision
deciders: [maintainers]
---

# ADR-0107: Resolve updates immutably and keep application attended

## Context

Agency Runtime needs a quick way to identify a running build and discover the
latest stable release, current development head, or an explicitly requested
release/ref. The repository is private during prerelease development, no stable
GitHub release currently exists, and version text alone does not identify an
editable checkout or an exact VCS installation.

Update discovery also crosses a supply-chain boundary. GitHub metadata and a
local cache are untrusted inputs, mutable selectors can move between inspection
and installation, and invoking pip or host registration from the authenticated
dashboard would convert a read-only observability bearer into package-mutation
authority. Codex refresh may separately require non-exporting operator presence.

## Decision

Separate identity, discovery, resolution, and application.

Expose a constant-time `-V`/`--version` package probe and a detailed `agency
version` identity that includes exact source/VCS commit when available. Resolve
each stable-release, `main`, canonical-version, or bounded-ref selector to one
full commit SHA. Validate the fixed official repository, GitHub object shape,
exact URL, sizes, controls, redirects, and timeout before using the result.
Prefer the configured GitHub CLI for private-repository access inside a
least-privilege environment; fall back only to fixed-origin public HTTPS.

Persist observations only in an owner-private, atomic, bounded cache and
revalidate them on every read. Dashboard startup may schedule stale stable and
main probes asynchronously. Ordinary interactive CLI startup may display a
validated cached stable-release notice; hooks, MCP, and other latency-sensitive
host paths do not check the network.

Do not call a differing mutable ref an available upgrade. Only canonical release
ordering can produce an automatic update notice. `agency upgrade` resolves the
requested selector, then prints an exact-SHA package command and a separate
Codex refresh command. It uses interpreter-bound isolated-mode pip only when a
stable regular pip entry point is inside that exact private, non-repository
prefix and a bounded `pip --isolated --disable-pip-version-check --version`
probe succeeds. When the executing environment has no pip, it accepts only an
exact bounded Agency uv-tool receipt, a safely resolved non-repository uv
executable, and no-config tool/bin probes bound to the current environment.
Target-changing uv/XDG environment overrides fail closed. A generated plan is
valid only unchanged in the same owner-controlled environment. An unknown
no-pip environment gets no install command. Agency never executes either step. The
dashboard remains read-only and may only display or copy the fixed attended
command for an owner terminal.

## Consequences

- Operators can distinguish package, source, and exact VCS builds and can
  prepare reproducible update commands without reconstructing Git syntax.
- A mutable selector cannot change between resolution and the printed install
  source because the plan contains the resolved full SHA.
- Private repository checks reuse configured `gh` authentication without
  copying credentials into Agency storage or dashboard responses.
- Dashboard and routine command startup stay responsive through local cache
  reads and background refresh; update failure does not block runtime work.
- Applying an update still requires an owner-controlled terminal and any native
  operator-presence/trust steps. This is deliberate, not a missing automation.
- A uv-managed tool does not need pip injected into its private environment;
  the attended plan uses its owning installer only after validating the exact
  Agency receipt. Other no-pip environments fail closed.
- A branch that differs from the installed commit is reported as different,
  not newer, until independent ancestry evidence exists.
- The cache can be stale for its documented TTL and GitHub can be unavailable;
  both states remain visible and operators can request `--refresh`.

## Alternatives

- **Execute pip directly from `agency upgrade`.** Rejected because discovery
  would gain package mutation authority and could bypass attended host refresh.
- **Always print `python -m pip`.** Rejected because uv tool environments omit
  pip by design and the resulting command cannot run.
- **Let the dashboard install or restart Agency.** Rejected because its bearer
  is observability authority, not proof of human presence.
- **Install directly from `main`, a tag, or `latest`.** Rejected because the
  selector can move after review and before dependency retrieval.
- **Use package version alone.** Rejected because editable and VCS installs at
  the same version can contain materially different source.
- **Probe GitHub synchronously on every command.** Rejected because it adds
  latency, consumes API/process budget, and would contaminate hook hot paths.
- **Treat every different `main` commit as an update.** Rejected because a
  local checkout may be ahead, diverged, or dirty; equality is not ancestry.
