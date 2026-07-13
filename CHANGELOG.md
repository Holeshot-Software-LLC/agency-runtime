---
title: "Changelog"
status: active
category: release
created: 2026-07-10
updated: 2026-07-13
tags: [release, changelog]
related:
  - docs/RELEASE_CHECKLIST.md
  - docs/roadmap/README.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
---

# Changelog

This project follows semantic versioning after the first published release.
Until then, changes accumulate under `Unreleased`; the package version remains
`0.1.0` and no public release or tag is claimed by this repository state.

Faithful commit history and reasoning-rich implementation notes remain in the
[worklog registry](docs/worklog/README.md). This file summarizes user-visible
changes rather than duplicating every commit.

## Unreleased

### Added

- Native, reversible host installation plans for Codex, Claude Code, Hermes,
  and OpenClaw, with explicit discovery-to-canary maturity.
- A dependency-light MCP stdio server and native Codex/Claude hook bridges.
- An optional, idempotent LiteLLM SDK callback and proxy callback object.
- A loopback-only authenticated operations dashboard with route inspection,
  evidence views, roster controls, host controls, and retention maintenance.
- Optional current-user dashboard services for Windows Task Scheduler and Linux
  `systemd --user`, installed by default with a mutation-free
  `agency install --no-dashboard` opt-out and explicit lifecycle commands.
- Structured dashboard configuration backed by the same typed, locked, atomic
  writer as CLI configuration, including ordered providers and write-only
  secrets.
- A responsive Signal Observatory with live bounded activity, accessible
  source-owned charts, animated event transitions, and reduced-motion and
  forced-colors support.
- Versioned routing, policy, delegation, and 1,000-agent performance evaluation.
- Governed bundled internationalization, payments and billing, and
  test-automation specialists plus an explicit generated availability registry
  for every companion-policy route.
- Windows and Ubuntu CI matrices plus isolated wheel smoke checks.
- Guided add/move/remove configuration for an authoritative four-entry provider
  chain, including authenticated Codex and Claude CLI judge transports.
- Persistent host-scoped soft controls shared by CLI, dashboard, MCP, and
  generated host command/skill surfaces, plus explicit `--native` lifecycle
  control.
- A nonmutating host-canary readiness report and exact-confirmed, nonce-bound
  live workflow with content-free fingerprinted attestations.
- A self-contained threat model, release gate, code of conduct, issue
  templates, pinned dependency groups, CodeQL, capability-aware dependency
  review, Dependabot, and offline workflow auditing for open-source operation.
- Strict bounded JSON, YAML, and regular-file readers shared by configuration,
  protocols, native inventory, provider responses, roster ingress, and
  persisted projections.

### Changed

- Pull requests use GitHub's native dependency-diff review when the repository
  exposes that capability and otherwise enforce the exact installed-runtime
  vulnerability audit, without requiring a billable security product.
- Routing cache and session state now include roster, configuration, and policy
  fingerprints; zero-signal routing abstains.
- Provider fallthrough rejects semantically invalid results and reports
  cumulative decision latency.
- Delegation execution gates dependents on successful prerequisites and merges
  only successful predecessor work.
- Runtime storage defaults to metadata-only capture and a 30-day retention
  policy when the dashboard applies maintenance.
- Dashboard activity now uses a consolidated metadata-only live endpoint,
  visibility-aware single-flight polling, stable revisions, and capped retry
  backoff while keeping host discovery and configuration off the fast path.
- CLI secret updates now use standard input or a hidden prompt instead of
  process arguments, and configuration writes reject stale revisions and
  invalid schema before replacement.
- Companion-policy validation now covers action and division routes, skips
  inactive roster-gated specialists with a recorded reason, and exits nonzero
  for missing enabled or unclassified routes. Policy evaluation includes
  resolved-companion regression gates.
- Typed provider chains now go directly to deterministic token routing after
  their final failure; legacy judge and Ollama settings apply only when no typed
  chain exists.
- Codex and Claude canaries use isolated temporary plugin profiles and preserve
  real-profile native facts separately; only current-profile attestations can
  promote native inspection maturity.
- Oversized CLI, installer, dashboard-service, configuration, delegation,
  selector, LiteLLM, and SQLite facades are split into cohesive modules while
  preserving their public and monkeypatch compatibility surfaces.
- Dashboard activity omits discarded sensitive fields at query time and reads
  materialized snapshot summaries; the representative 1,000-row projection is
  about 3.4 times faster and large snapshot projection no longer reparses
  manifests on every request.

### Fixed

- Failed load/delegation events are no longer promoted to successful evidence.
- Delegation evidence correlates to stable work-unit identity.
- Final response evidence is reconciled against canonical state and rejects
  spoofed or stale claims.
- OpenAI-compatible URL joining, Anthropic Messages request handling, and
  model-specific request parameters are normalized.
- Windows command shims and test-home boundaries no longer assume POSIX launch
  behavior or real user directories.
- Inline sequencing language now produces the same dependency edge in route
  explanations and delegated execution, and the v1.1 policy corpus prevents
  generic design work from being mislabeled as UI while recognizing
  authentication and deployment intents.
- The installed dashboard now parses its shipped JavaScript, refreshes evidence
  after route tests, renders long Windows paths without page overflow, hides
  nonexistent host roots, and displays routing decision IDs.
- Destructive retention input is rejected instead of clamped, and stale host
  inspections cannot offer enable/disable actions or survive a successful
  native state change.
- Full dashboard refreshes are abortable and generation-checked so startup,
  background restoration, and configuration mutations cannot apply stale
  snapshots.
- Routing-evaluation concurrency no longer depends on whether one CPU-bound
  narrowing call finishes inside a CPython thread-switch interval. Workers now
  synchronize from inside real narrowing progress, while a serialized
  narrowing regression still fails the overlap gate.
- Host adapters re-read persistent control at every boundary, trace correlation
  no longer falls back to a whole session, and native lifecycle success requires
  a proven inventory postcondition.
- Negated routing intent no longer leaks into policy, domain, token, or
  work-unit selection; explicit dependencies take precedence over incidental
  file overlap; output-format vocabulary no longer creates false graph edges.
- Nested roster snapshot diffs now materialize their real added, changed, and
  removed counts instead of reporting zero.
- Missing managed canary targets and empty file URLs no longer resolve
  implicitly to the current working directory.
- Routing cache hits compare detached mutation snapshots instead of rebuilding
  a 1,000-agent Python guard on every request, preserving nested-mutation
  invalidation while making the profiled hot path about ten times faster.
- Current Codex plugin manifests declare their hook bundle with the host's
  supported command schema. The exact-confirmed Windows Codex 0.144.1
  isolated-profile canary now loads those hooks and produces a valid
  nonce-correlated six-line response header. Its explicit one-invocation trust
  bypass remains isolated and never promotes durable real-profile trust.
- Windows dashboard task inspection rejects DTD and entity declarations before
  parsing bounded XML.

### Security

- Dashboard requests require a per-launch bearer token, valid loopback host,
  same origin, JSON mutation bodies, and exact confirmation phrases.
- Background dashboard tokens rotate per start and live only in an owner-only
  runtime descriptor; service definitions, argv, logs, and status output remain
  credential-free.
- HTTP request bodies and subprocess output are bounded; server errors are
  sanitized; optional content capture applies defensive redaction.
- Credentialed provider requests reject redirects, remote model catalogs are
  byte/count/string/control bounded, subprocess overflow is discarded while
  both pipes continue draining, and Windows batch shims never receive
  user-controlled provider or delegation arguments.
- Host canaries isolate home/temp state, disable mutating MCP tools, bound and
  sanitize process output, omit prompt/output content from attestations, and
  never forward dashboard bearer tokens across redirects.
- Custom config/database paths no longer rewrite shared parent permissions;
  database files and sidecars fail closed on Windows ACL errors, and database
  symlink or reparse-point paths are rejected before open.
- Credentialed remote providers now require HTTPS except on literal loopback,
  reject ambiguous URL components, and validate the same rule across config,
  discovery, doctor, and runtime request paths.
- Delegation now minimizes inherited environment state, sends Codex/Claude
  tasks through standard input, redacts task content from every result surface,
  and contains descendants with Windows Job Objects or POSIX process groups.
- Rejected JSON mutations drain bounded authenticated request bodies before
  responding, preventing intermittent Windows TCP resets from hiding the API
  error response.
- HTTP server tests now isolate configuration through pytest-managed temporary
  paths instead of leaking a POSIX-only global path across the Windows suite.
- Slotted Codex, Claude, and OpenClaw backends now call the shared parser
  explicitly, restoring structured delegation on Python 3.12 Linux; optional
  host capability tests no longer confuse an unusable WSL interop shim with a
  native executable.
- Protocol and configuration JSON rejects duplicate keys, non-finite numbers,
  oversized integers, excess bytes, deep nesting, and excess nodes; YAML also
  rejects aliases, merge keys, non-text keys, and shared containers.
- Delegated Git operations strip inherited Git configuration, disable hooks and
  fsmonitor, bound process output, and refuse executable filters, merge drivers,
  diff commands, and text converters before mutation.
- Windows owner-only permission setup detects restricted or indeterminate
  process tokens before changing a DACL, preventing a sandbox from locking
  itself out while preserving the fail-closed privacy contract.
- Existing exact owner-only Windows DACLs are verified and reused without a
  rewrite, including SQLite sidecars inherited from a recursively private
  parent; restricted tokens still fail before any required permission change.
- Roster downloads enforce one total deadline across slow reads; native canary
  credentials harden an empty destination before content exists; Git checkout
  hooks are suppressed; and strict finite JSON output is serialized before any
  protocol bytes are written.
