---
title: "ADR-0154: Plain-text CLI cards over a rich dependency"
status: active
category: cli
created: 2026-08-04
updated: 2026-08-04
tags:
  - cli
  - presentation
  - dependency
  - parity
related:
  - docs/roadmap/issue-AR-236-achieve-full-cli-dashboard-parity.md
  - docs/roadmap/issue-AR-251-cli-presentation-richness.md
  - docs/roadmap/issue-AR-237-hiring-list-and-show-parity.md
  - agency_runtime/cli/_render.py
supersedes: []
superseded_by: null
---

# ADR-0154: Plain-text CLI cards over a rich dependency

## Context

AR-236 §10 calls for every CLI command to grow a card-style output mode
(`--card`), color-coded status matching the dashboard's CSS classes, and
live-watch where the dashboard has live SSE updates. The analysis doc
identified `rich` as the likely presentation library.

AR-237 (sub-issue 1) introduced `agency_runtime/cli/_render.py` with a
plain-text card layout: horizontal-rule dividers, tab-aligned field blocks,
and section bodies. It works without any external dependency and is
on-by-default when stdout is a TTY.

## Decision

Adopt the plain-text card layout from `_render.py` as the canonical CLI
presentation layer. Do **not** add `rich` (or any other presentation
library) as a runtime dependency.

Rationale:

1. **Zero-dependency install.** ADR-0024 and ADR-0028 establish the
   one-command install property. Adding `rich` to the runtime dependency
   closure breaks that property for a presentation concern.
2. **Universal rendering.** Plain-text cards render identically in every
   terminal, pipe, log capture, and CI output. `rich`'s color/markup can
   produce escape sequences in non-TTY contexts that break log scraping.
3. **Sufficient richness.** The card layout (dividers, tab-aligned fields,
   sections, truncation) gives the information-density parity the user
   asked for ("the CLI should be pretty too") without a TUI.
4. **Color is a follow-up, not a blocker.** ANSI color codes can be added
   to `_render.py` behind a TTY check without a library; the dashboard's
   CSS class names map to status tokens, not colors.

## Consequences

- Every CLI command that grows a `--card` mode uses `Card`,
  `CardField`, `CardSection`, and `render_cards` from `_render.py`.
- `--json` always wins over `--card` (machine-readable output is never
  decorated).
- Card mode is on-by-default when `stdout.isatty()` and no `--json` flag
  is present; off otherwise (pipes, redirects, CI).
- Live-watch (SSE consumption from the CLI) is deferred; it requires a
  streaming client and is not part of the card presentation layer.

## Alternatives

- **`rich` library.** Rejected: breaks the zero-dependency install
  property; escape sequences in non-TTY contexts; the card layout already
  achieves the information-density goal.
- **Full-screen TUI (ncurses/textual).** Rejected by the user in the
  analysis doc: "pretty CLI means `rich`-style card output, not a TUI."
