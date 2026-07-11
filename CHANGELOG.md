---
title: "Changelog"
status: active
category: release
created: 2026-07-10
updated: 2026-07-11
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
- Versioned routing, policy, delegation, and 1,000-agent performance evaluation.
- Windows and Ubuntu CI matrices plus isolated wheel smoke checks.

### Changed

- Routing cache and session state now include roster, configuration, and policy
  fingerprints; zero-signal routing abstains.
- Provider fallthrough rejects semantically invalid results and reports
  cumulative decision latency.
- Delegation execution gates dependents on successful prerequisites and merges
  only successful predecessor work.
- Runtime storage defaults to metadata-only capture and a 30-day retention
  policy when the dashboard applies maintenance.
- CLI secret updates now use standard input or a hidden prompt instead of
  process arguments, and configuration writes reject stale revisions and
  invalid schema before replacement.

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

### Security

- Dashboard requests require a per-launch bearer token, valid loopback host,
  same origin, JSON mutation bodies, and exact confirmation phrases.
- Background dashboard tokens rotate per start and live only in an owner-only
  runtime descriptor; service definitions, argv, logs, and status output remain
  credential-free.
- HTTP request bodies and subprocess output are bounded; server errors are
  sanitized; optional content capture applies defensive redaction.
