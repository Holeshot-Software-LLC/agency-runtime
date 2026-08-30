---
title: "AR-71: Make dashboard states accessible, truthful, and discoverable"
status: done
category: roadmap
created: 2026-07-16
updated: 2026-07-18
tags: [operations, dashboard, accessibility, responsive-design, correctness]
related:
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
  - docs/decisions/0031-optional-user-dashboard-service-and-shared-configuration.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-71
priority: p1
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/72"
depends_on: []
blocks: [AR-94, AR-96]
---

# AR-71: Make dashboard states accessible, truthful, and discoverable

## Problem

Installed-dashboard review found several gaps that synthetic DOM tests could
not prove: low-contrast supporting text, an unknown host runtime state rendered
as enabled, blank host views when discovery returns nothing, weak skip-link
destination feedback, and hidden mobile navigation affordance. These issues can
mislead operators or make important controls harder to discover.

## Current state

The dashboard already has bounded live refresh, typed confirmations, protected
default agents, generation-checked controls, reduced-motion behavior, forced-
color rules, keyboard-operable evidence tabs, and responsive layouts. The
remaining presentation defects are isolated to state rendering and CSS, and a
real installed-browser matrix remains required before completion.

## Approach

Raise the muted small-text token to WCAG AA contrast, represent unknown host
state explicitly, render informative empty states, preserve visible focus
feedback after skip-link navigation, and retain a mobile cue that the navigation
rail scrolls. Add deterministic regressions, then verify the installed dashboard
at desktop and mobile sizes with reduced motion, forced colors, live refresh,
configuration mutations, console monitoring, and overflow checks.

## Dependencies

ADR-0029 governs the secure local dashboard and ADR-0031 governs the optional
cross-platform dashboard service. This issue does not broaden either trust
boundary or change the configuration/control contracts.

## Acceptance

- [x] Supporting text at small sizes meets WCAG AA contrast against its surfaces.
- [x] Unknown host runtime state is displayed as unknown and cannot imply enabled.
- [x] Overview and Hosts views explain a legitimate empty discovery result.
- [x] Skip-link navigation leaves a visible focus indication at the main content.
- [x] Mobile navigation remains discoverable and usable at 320px without document overflow.
- [x] Focused JavaScript and server regressions pass at exact coverage.
- [x] Installed desktop, mobile, reduced-motion, forced-colors, live, config, console, and overflow QA passes.
- [x] Full-suite, packaging, tracker, and merged-install gates pass.
