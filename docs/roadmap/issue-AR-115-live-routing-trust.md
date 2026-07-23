---
title: "AR-115: Make live routing and Agency headers trustworthy"
status: open
category: roadmap
created: 2026-07-21
updated: 2026-07-21
tags: [routing, headers, delegation, dashboard, testing]
related:
  - README.md
  - agency_runtime/core/header/explanations.py
  - agency_runtime/core/selector/judge.py
  - agency_runtime/core/selector/pipeline.py
  - agency_runtime/server/mcp_tools.py
  - docs/decisions/0078-present-human-routing-evidence-and-abstain-on-noise.md
supersedes: []
superseded_by: null
type: issue
epic: routing
issue_id: AR-115
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/127
depends_on: []
blocks: [AR-116, AR-119]
---

# AR-115: Make live routing and Agency headers trustworthy

## Problem

A verified Codex turn exposed raw routing codes in the user-facing header,
selected unrelated geography and clinical specialists for a runtime/dashboard
question, and rejected delegation preparation when Codex described its native
worker more specifically than Agency's durable generic-worker attribution.
Passing synthetic evaluation scores did not catch this real prompt.

## Current state

Source and clean-distribution tests now reject the unrelated clinical,
geography, translation, and generic-operations matches from the observed
runtime/dashboard prompt. Configured Codex-subscription inference with an
explicit model requires `multi-agent-systems-architect` for that prompt and may
also select `technical-writer` for the readability work. The no-inference route
meets the same required/acceptable/forbidden contract. The exact installed candidate
still requires a fresh normal Codex task after plugin restart before this item
can close.

## Approach

Keep raw reason and effect codes in the signed durable receipt and render a
deterministic plain-English projection in the six-line response header. Require
a minimum signal before heuristic fallback may select a specialist; otherwise
abstain and let the resident orchestrator and chief of staff handle the turn.
Treat configured inference as a proposal that must still meet the operator's
confidence floor before any specialist prompt is hydrated. Make the native
Agency evidence capability visible to eligibility filtering, and avoid generic
domain expansions that outrank the purpose-built runtime specialists.
Normalize supported native-host worker labels to generic-worker at the MCP
boundary while continuing to reject arbitrary specialist-like attribution.
Validate companion-policy completeness against the full active roster before
host capability filtering, while continuing to route only specialists eligible
for the current host and platform.
Add the observed prompt and explicit forbidden specialists to regression and
live verification coverage.

## Dependencies

ADR-0001 defines layered routing, ADR-0011 defines delegation evidence,
ADR-0027 makes correlated receipts authoritative, and ADR-0030 requires
quantitative routing gates.

## Acceptance

- [x] User-facing Why and How lines are readable prose.
- [x] Raw reason and effect codes remain in durable routing receipts.
- [x] Weak heuristic collisions abstain instead of selecting unrelated specialists.
- [x] Low-confidence inferred candidates are removed before caching, hydration, or activation.
- [x] The native capability contract makes the audited runtime-evidence specialist eligible.
- [x] Deterministic fallback selects only strongly grounded compatible specialists.
- [x] Supported Codex native worker labels normalize to generic-worker attribution.
- [x] Policy completeness is validated against the full active roster, not the host-eligible subset.
- [ ] The observed prompt selects multi-agent-systems-architect or safely abstains in the installed runtime, with clinical, geography, translation, and generic operations specialists forbidden.
- [ ] Both configured-inference and no-inference installed cases pass the forbidden-specialist assertions.
- [x] Dashboard and public documentation explain the live test workflow.
- [ ] Full repository, hosted CI, merge, reinstall, and Codex smoke gates pass.
