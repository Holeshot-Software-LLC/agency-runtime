---
title: "AR-78: Preserve the LiteLLM router when the actual model is unavailable"
status: done
category: roadmap
created: 2026-07-16
updated: 2026-07-17
tags: [litellm, models, receipts, observability, cli]
related:
  - docs/decisions/0003-response-telemetry-is-model-truth.md
  - docs/decisions/0047-reconcile-litellm-model-and-router-evidence.md
  - docs/roadmap/issue-AR-29-reconcile-litellm-model-and-router-evidence.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: observability
issue_id: AR-78
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/79"
depends_on: [AR-29]
blocks: []
---

# AR-78: Preserve the LiteLLM router when the actual model is unavailable

## Problem

The evidence header returned before rendering the LiteLLM router whenever a
receipt truthfully lacked an authoritative resolved model. Operators then lost
the verified router identity precisely on failed or telemetry-poor calls, even
though the receipt retained that identity.

## Current state

The implementation now renders a verified `model_group` router after both
successful provider/model evidence and truthful unavailable or failed states.
Non-LiteLLM and no-receipt formatting remains unchanged. Full-suite and
installed-host acceptance remain pending.

## Approach

Keep the unavailable or failure state authoritative and never promote the
router alias into an actual-model claim. When the source is verified LiteLLM
and `model_group` is present, append the router identity to that truthful state
using the same explicit `LiteLLM router` wording as successful receipts. A
representative unavailable result is `requested -> unavailable - no resolved
model telemetry via LiteLLM router <name>`.

## Dependencies

AR-29 and ADR-0047 own the separation between requested alias, LiteLLM router,
and actual provider model. This item closes the remaining presentation gap
without changing receipt reconciliation or provenance.

## Acceptance

- [x] Unavailable LiteLLM receipts retain an explicit router name in the Agency header.
- [x] Failed LiteLLM receipts retain an explicit router name without claiming an actual model.
- [x] Non-LiteLLM and no-receipt output remains unchanged.
- [x] Focused header and reconciliation tests pass with exact coverage.
- [x] Installed smoke, tracker, and merged-install gates pass.
