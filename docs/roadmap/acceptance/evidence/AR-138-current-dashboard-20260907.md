---
title: "AR-138 current packaged-dashboard verification"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [acceptance, dashboard, browser, accessibility]
related:
  - docs/roadmap/issue-AR-138-coherent-observable-dashboard-ui.md
  - docs/roadmap/acceptance/issue-AR-138.md
  - scripts/verify_dashboard_browser.py
  - scripts/verify_dashboard_browser.mjs
  - tests/dashboard_ui.test.mjs
supersedes: []
superseded_by: null
---

# AR-138 current packaged-dashboard verification

## Scope and candidate

The source repair is d7231df3, checkpointed with ledger 7892096d. Only dashboard
HTML/CSS changed in the runtime: accessible muted navigation/empty-state text,
named focusable scroll regions, named group roles, and auto-fitting metric cards.
No staffing, inference, host activation, server authentication or provider policy
changed. The original six acceptance criteria are unchanged.

A fresh wheel was built with the repository's pinned isolated build backend and
installed into a disposable target, not the owner's environment. Wheel SHA-256:

    f1c74fbc3d5999ebcfb97ed9e2b7fc450bf4548ad76e3dd3e813aef39e0ca6e1

All ten packaged dashboard HTML/CSS/JS/SVG assets were compared with source and
matched byte-for-byte. Their individual hashes are in the committed browser
report. The real packaged Python HTTP server served the real packaged assets
against a private five-agent Store. Host inventory was explicitly stubbed, and
Python outbound connections were denied so no provider or update call ran.
This is installed-wheel dashboard evidence, not a native-host or normal-profile
activation canary and not a whole-release certificate.

## Browser evidence

The final run began at 2026-09-07T04:54:57.219Z, using sandboxed Chromium
152.0.7977.64, Playwright 1.63.0 and axe-core 4.13.0. It returned exit 0 and
passed=true. Seven sections were tested at each viewport, with their applicable
metric/evidence reads awaited after the coherent full refresh.

| Viewport | Sections | Axe violations | Document width | Clipped metric cards |
|---|---|---|---|---|
| 1280 x 900 | 7 | 0 | 1280 px | 0 |
| 1024 x 768 | 7 | 0 | 1024 px | 0 |
| 375 x 812 | 7 | 0 | 375 px | 0 |

Sections: overview, routing, evidence, roster, workforce, hosts and settings.
The 375 px heading measured 56.796875 px high, not the original 280 px flex
basis. Desktop cards now wrap within their panels instead of hiding the
selection-concentration and calls-per-decision cards.

Each viewport also passed these actual-browser assertions:

- An actual control request occurred while an unsaved configuration field
  retained focus, its text selection, its value and every open settings detail.
- Keyboard ArrowDown scrolled the configuration output.
- A deliberately aborted control request retained the last good control revision
  and marked it stale visibly.
- The notice and application console contained the same valid UUIDv4 request ID.
- Removing the fault and refreshing recovered to fresh control data.

Final request IDs were 2866baf7-5812-4870-8f05-cae159808fff (1280),
7ab86d66-7446-4da7-8240-b8c1b5b3ec76 (1024), and
f41e8692-deef-4581-b718-735c07651569 (375). Unexpected console, page and HTTP
errors were zero before fault injection; deliberate network errors are separated
from that clean-page count.

Artifacts: [JSON report](AR-138-browser-20260907/report.json),
[desktop screenshot](AR-138-browser-20260907/1280-overview.png),
[intermediate screenshot](AR-138-browser-20260907/1024-overview.png),
[375 px screenshot](AR-138-browser-20260907/375-overview.png).

The JSON report SHA-256 is:

    92243da48f86ad9efe279ec3d10d4f6c79c55fab632f37f511661d9fc3477356

Axe checks WCAG 2.0/2.1 A/AA tags. It retains incomplete color-contrast results
for gradients, pseudo-elements, overlaps and very short text. Those are not
silently promoted into passes. This evidence makes no complete WCAG, screen
reader, every possible dataset, cross-browser or Windows certification claim.
Visual inspection of the final screenshots supplements the automated layout
measurements; native Windows execution remains with the owner.

## Current verification

- Four new focused unit regressions passed after red checks. The initial three
  failed before CSS/keyboard repair; the added group-role and expanded contrast
  assertions also failed before their repair.
- The complete UI suite passed 142 tests, no skips, 212.73ms. The exact checked-in
  coverage command passed at 96.92% lines, 86.62% branches and 95.71% functions:

      node --test --experimental-test-coverage \
        '--test-coverage-include=agency_runtime/dashboard/**/*.js' \
        --test-coverage-lines=95 --test-coverage-branches=86 \
        --test-coverage-functions=93 tests/dashboard_ui.test.mjs

- The UI suite includes stale live/full/control generation races, view intent
  races, inconsistent/missing snapshots, dirty forms, interaction restoration,
  and request-ID validation/rejection. These are deterministic unit checks,
  distinct from the real browser receipt above.
- Dashboard API/authentication/transaction modules passed 180 tests in 28.80s:

      python -m pytest tests/test_dashboard.py \
        tests/test_dashboard_auth_boundary_regression.py \
        tests/test_dashboard_transaction_refactors.py -q -W error

- The exact 29-module fast Python spine named in AGENTS.md passed 1085 with
  three existing skips in 69.50s.
- Routing evaluation returned passed=true, exit 0.
- Ruff check/format (765 files), browser-checker JavaScript syntax and diff
  checks passed at the source checkpoint. Documentation and acceptance gates
  are repeated at the final checkpoint.

The mistaken first diagnostic used historical 95/90/96 UI floors without source
inclusion; its failure is not hidden and did not change the actual CI floors.
The old wheel reproduced contrast/scroll issues and two clipped cards at 1280 px.
An initial repaired-wheel structural capture still showed metric loading states;
it was not used for final acceptance. The final checker explicitly awaits the
view-scoped reads and proves that the focus check executes a real control poll.

## Reproduction

From a development environment with the repository's build dependencies:

    qa_tools=$(mktemp -d)
    python -m build --wheel --outdir "$qa_tools/dist"
    python -m pip install --no-deps --target "$qa_tools/package" \
      "$qa_tools/dist/agency_runtime-0.1.0-py3-none-any.whl"
    npm install --prefix "$qa_tools" --save-exact --ignore-scripts \
      --no-audit --no-fund playwright@1.63.0 axe-core@4.13.0
    PLAYWRIGHT_BROWSERS_PATH="$qa_tools/browsers" \
      node "$qa_tools/node_modules/playwright/cli.js" install chromium
    PYTHONPATH="$qa_tools/package" PLAYWRIGHT_BROWSERS_PATH="$qa_tools/browsers" \
      python scripts/verify_dashboard_browser.py --tools "$qa_tools" \
      --package-root "$qa_tools/package" --output "$qa_tools/evidence"

The recorded run used --browser /snap/bin/chromium instead of downloading a
browser. Use an explicitly selected Chromium executable to reproduce that exact
browser version; otherwise the tool uses the browser pinned by Playwright.
The output directory must be new. No credential, host install, operator trust,
native gateway restart or source runtime package replacement is required.
