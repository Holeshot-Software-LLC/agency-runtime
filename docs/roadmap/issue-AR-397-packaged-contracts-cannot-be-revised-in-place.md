---
title: "AR-397: A packaged contract that already shipped at the current template cannot be revised in place"
status: done
category: roadmap
created: 2026-09-04
updated: 2026-09-05
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
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/654
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

Not every revision is blocked the same way. A lifecycle phase lives only in
the projected recruitment contract, so changing one keeps both the prompt hash
and the routing-metadata identity: the identity pass reports the worker
`existing` and the repair pass `reconcile_packaged_workforce_contracts`
re-projects the contract from the current package. Four definition fields
reach the routing metadata but not the compiled prompt: `hosts`, `platforms`,
the positive scenario (`preferred_scenarios`) and the negative scenario
(`avoided_scenarios`). A revision touching only those leaves the live worker
at the exact packaged prompt with a superseded metadata identity, which the
repair pass classifies as `revision_modified` and leaves alone, taking any
lifecycle change in the same revision down with it. Every change that reaches
the prompt, which is every capability, tool, evidence or scope edit, is blocked
as described above.

The guard itself is right: an owner- or inference-authored amendment must never
be overwritten by a package. The gap is that the packaged source can add
contracts and migrate templates, but cannot correct a contract it shipped the
day before, whether the correction touches the prompt or only its metadata.

## Current state

Surfaced on 2026-09-04 by the first adversarial review of PR #638 (AR-370
criterion 1). `monitoring-engineer` shipped in `be3702f7` covering the
`implementation` lifecycle only, so a provisioning unit labelled `release` had
no monitoring coverer. Adding the phase keeps the prompt hash and the metadata
identity, so this first revision travels through the repair pass. The mechanism
below is still load-bearing for it: the live worker's hiring case carries the
shipped identity's evidence, and `packaged_hiring_case_is_auditable` accepts
only the current package and its predecessors, so without the superseded
identity the live hire case reads as not auditable the moment the definition
changes (measured on a copy of the live store by the review of PR #640). The two contracts that landed a few hours earlier
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
through the existing amendment path and the hiring-case audit and the store's
packaged revision staging recognise the shipped identity.
`known_contractor_revision_metadata_authorities` names each superseded
metadata identity, so a revision touching only the four metadata-bearing
fields is re-projected by the repair pass instead of being reported as an
amendment. `install_known_contractors` checks every superseded pin before it
judges any worker, so a pin that does not match its reconstruction stops the
install on an up-to-date machine as well as on one that is behind.

Open here: a change to the installer's per-slug tables (`_DOMAINS`,
`_ARTIFACTS`, `_OPTIONAL_TOOLS`) also moves the metadata identity without
touching the prompt, and the existing hook covers only the single historical
transition from no declared optional tools to declared ones; and
`packaged_hiring_case_is_auditable` accepts an `amend` case only for the
current package, so a second in-place revision de-audits the first revision's
amend case (forensic only, since the audit gates the transition to `audited`
and not an already applied case).

First use: `monitoring-engineer` gains the `installation` phase, which projects
to the `release` lifecycle.

## Decision (2026-09-05): the per-slug tables are identity, pinned with the contract

The open case above is settled with the close. `_DOMAINS` and `_ARTIFACTS`
feed `categories` and `task_types` in `_known_contractor_agent`, and
`_OPTIONAL_TOOLS` shapes `required_tools` through `_required_tools` (the
packaged agent never carries an `optional_tools` key); all three land in
list fields of `revision_metadata`, so a table edit for a shipped slug moves
the live worker's metadata identity exactly as a `hosts` or `platforms` edit
does. The
superseded reconstruction, however, rebuilds a superseded contract through
the *current* tables, so it cannot represent a table value that has since
changed. The first table edit for a shipped slug must therefore ship the
prior values beside the superseded contract (a per-slug snapshot of the three
tables, pinned the way the prompt hash is) and the reconstruction must read
the snapshot instead of the tables. Nothing is pinned today: no shipped
slug's table entry has changed since the tables were introduced, so a pin
now would compare against nothing. The historical optional-tools hook in
`known_contractor_revision_metadata_authorities` stays as the one transition
that predates this rule.

The second remark stands as an accepted limit: `packaged_hiring_case_is_auditable`
accepts an `amend` case for the current package only, so a second in-place
revision de-audits the first revision's amend case. The audit gates the
transition to `audited`, never an applied case, so this is forensic and is
not reopened here.

Closed 2026-09-05 through the AR-361 flow: five criteria verified by the
isolated verifier against `45432976`, the two suites green at that tree, and
the monitoring engineer covering `release` on a copy of the live store after
the `c42fb0a5` install.

## Dependencies

- AR-370 criterion 1, whose operations contracts this mechanism first revises.

## Acceptance

- [x] A live worker whose prompt-changing superseded revision is packaged
      advances to the current package on `agency install`, is reported
      `upgraded`, and keeps the superseded prompt as history.
- [x] A live worker at the shipped monitoring identity is reported `existing`,
      not divergent, and its recruitment contract carries the `release`
      lifecycle after the install's repair pass.
- [x] A superseded revision whose reconstruction no longer matches its pinned
      prompt hash makes `agency install` fail closed on every machine, including
      one whose worker is already current.
- [x] A live worker at a superseded revision that differs only in a
      metadata-bearing field is reported `existing`, not divergent, and its
      recruitment contract carries the current metadata after the repair pass.
- [x] `monitoring-engineer` covers the `release` lifecycle on the live roster
      after install.
