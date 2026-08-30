---
title: "AR-139: Restore the installed release asset budget"
status: open
category: roadmap
created: 2026-07-26
updated: 2026-07-26
tags: [release, packaging, dashboard, assets, performance]
related:
  - docs/RELEASE_CHECKLIST.md
  - tests/test_release_packaging.py
  - agency_runtime/dashboard
supersedes: []
superseded_by: null
type: issue
epic: release
issue_id: AR-139
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-139: Restore the installed release asset budget

## Problem

The packaged dashboard asset payload is 263,374 bytes against the strict
263,168-byte release ceiling, blocking release by 206 bytes.

## Current state

The independent release-packaging suite passes 14 tests and fails only this
exact budget. Raising the limit after observing the result would weaken a
release control rather than repair the regression.

## Approach

Remove at least 207 bytes of redundant generated/static payload without
minifying away source reviewability, changing the budget, or dropping required
content. Verify canonical Git-blob packaging and installed rendering.

## Dependencies

None.

## Acceptance

- Canonical packaged assets remain strictly below the existing ceiling.
- Dashboard behavior, CSP, accessibility, source maps if governed, and exact
  manifest membership remain intact.
- Release packaging and deterministic artifact tests pass from a clean tree.

## Implementation evidence

Redundant ES-module strict declarations and duplicate lifecycle/null-check
bytes first restored the ceiling with only 17 bytes of margin. The final
maintainable pass consolidates repeated model discovery, record validation,
lifecycle checks, definition/token rendering, and worker-history rendering;
normalizes the seven JavaScript modules to tab indentation; and removes only
CSS declarations exactly superseded later in the same top-level cascade. It
adds no build dependency, opaque minifier, generated bundle, or content cut.

Canonical dashboard assets are now 258,787 bytes against the unchanged
263,168-byte ceiling: 4,381 bytes of margin and a 21,169-byte reduction from
the 279,956-byte pre-repair build. The dashboard interaction suite passes all
101 tests at 98.61 percent line, 91.06 percent branch, and 97.90 percent
function coverage. Release-resource, served-shell, ES-module allowlist, syntax,
Ruff, format, and diff checks pass. Desktop and 390x844 Chromium smoke preserve
the sampled computed layout, seven navigation controls, skip link, single
visible view, and zero horizontal overflow. Fresh artifact-installed rendering
and final clean-tree release construction remain.
