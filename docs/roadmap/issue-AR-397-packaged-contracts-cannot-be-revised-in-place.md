---
title: "AR-397: A packaged contract that already shipped at the current template cannot be revised in place"
status: in_progress
category: roadmap
created: 2026-09-04
updated: 2026-09-04
tags: [workforce, roster, packaging, install]
related:
  - docs/roadmap/issue-AR-370-staffing-asks-the-wrong-question.md
  - agency_runtime/core/workforce/known_installer.py
  - agency_runtime/core/workforce/known_contractors.py
supersedes: []
superseded_by: null
type: issue
epic: workforce
issue_id: AR-397
priority: p2
tracker_url: null
depends_on: []
blocks: []
---

# AR-397: A packaged contract that already shipped at the current template cannot be revised in place

## Problem

`install_known_contractors` advances a live packaged worker only when its
stored identity is an exact predecessor package (the `exact_predecessor` check
in `agency_runtime/core/workforce/known_installer.py`), and the predecessors
it knows are reconstructions of earlier *template* versions: the v1,
malformed-v1, v2 and v3 tables, each keyed by prompt hash and each rebuilt by
re-parsing the current definition at an older schema version. A content change
to a definition that already shipped at the current template, such as a new
lifecycle phase or a reworded capability, produces an identity that matches no
predecessor, so the live worker is reported `preserved` and keeps the old
contract indefinitely.

Not every revision is blocked. A lifecycle phase lives only in the projected
recruitment contract, so changing one keeps both the prompt hash and the
routing-metadata identity: the identity pass reports the worker `existing` and
the repair pass `reconcile_packaged_workforce_contracts` re-projects the
contract from the current package. Every change that reaches the prompt, which
is every capability, scenario, tool or scope edit, is blocked as described.

The guard itself is right: an owner- or inference-authored amendment must never
be overwritten by a package. The gap is that the packaged source can add
contracts and migrate templates, but cannot correct a contract it shipped the
day before, whether the correction touches the prompt or only its metadata.

## Current state

Surfaced on 2026-09-04 by the first adversarial review of PR #638 (AR-370
criterion 1). `monitoring-engineer` shipped in `be3702f7` covering the
`implementation` lifecycle only, so a provisioning unit labelled `release` had
no monitoring coverer. Adding the phase keeps the prompt hash and the metadata
identity, so this first revision travels through the repair pass; the next
correction to either contract's prose would not, which is what the mechanism
below is for. The two contracts that landed a few hours earlier
are the first packaged contracts revised at the current template, which is why
the gap had not been hit before.

## Approach

Keep every superseded revision of a packaged definition verbatim
(`SUPERSEDED_KNOWN_CONTRACTOR_CONTRACTS` in
`agency_runtime/core/workforce/known_contractors.py`, built by the same helper
as the current definition) and pin its prompt hash in
`agency_runtime/core/workforce/known_installer.py` beside the template tables.
`_known_contractor_predecessor_packages` returns the template predecessors and
the superseded revisions together, so a prompt-changing revision advances
through the existing amendment path and the hiring-case audit and roster sync
recognise the shipped identity. A pin that does not match its reconstruction
fails closed, exactly as the template tables do. A change to the installer's
per-slug tables (`_DOMAINS`, `_ARTIFACTS`, `_OPTIONAL_TOOLS`) alters routing
metadata without touching the prompt and is covered today only for optional
tools; that remains open here.

First use: `monitoring-engineer` gains the `installation` phase, which projects
to the `release` lifecycle.

## Dependencies

- AR-370 criterion 1, whose operations contracts this mechanism first revises.

## Acceptance

- [ ] A live worker whose prompt-changing superseded revision is packaged
      advances to the current package on `agency install`, is reported
      `upgraded`, and keeps the superseded prompt as history.
- [ ] A live worker at the shipped monitoring identity is reported `existing`,
      not divergent, and its recruitment contract carries the `release`
      lifecycle after the install's repair pass.
- [ ] A superseded revision whose reconstruction no longer matches its pinned
      prompt hash makes the install fail closed rather than advance.
- [ ] `monitoring-engineer` covers the `release` lifecycle on the live roster
      after install.
