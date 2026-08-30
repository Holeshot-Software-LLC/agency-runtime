---
title: "AR-96: Serve a packaged dashboard favicon without console noise"
status: done
category: roadmap
created: 2026-07-18
updated: 2026-07-20
tags: [dashboard, browser, packaging, quality]
related:
  - docs/roadmap/issue-AR-71-dashboard-accessible-truthful-states.md
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: dashboard
issue_id: AR-96
priority: p1
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/97"
depends_on: [AR-71]
blocks: []
---

# AR-96: Serve a packaged dashboard favicon without console noise

## Problem

The dashboard shell did not declare or serve a favicon. Chromium therefore
requested `/favicon.ico` and logged a 404 during otherwise clean browser QA.
That breaks the clean-console release contract and leaves installed artifacts
without a first-party dashboard icon.

## Current state

The shell declares a local SVG favicon, the hardened loopback server serves it
with an exact media type, and wheel/source package manifests include the asset.
Focused server and packaging regressions, built-artifact inspection, and live
Chromium console QA pass. The cross-platform release matrix remains.

## Approach

Keep the icon self-contained with the existing static dashboard assets, serve
it through the same no-store security-header path, and include it explicitly in
both wheel package data and the source-distribution manifest. Browser QA must
prove the missing-icon request and its console error are gone.

## Dependencies

AR-71 owns truthful and accessible dashboard presentation. ADR-0029 owns the
local-only dashboard security boundary.

## Acceptance

- [x] The dashboard declares a local first-party favicon.
- [x] The server returns the icon with the correct media type and hardened headers.
- [x] Wheel and source-distribution manifests include the asset.
- [x] Focused static-server and packaging regressions pass.
- [x] Browser QA is console-clean and the complete release matrix passes.
