---
title: "AR-83: Import manifest-backed upstream agent rosters into quarantine"
status: done
category: roadmap
created: 2026-07-17
updated: 2026-07-18
tags: [roster, import, quarantine, manifests, security]
related:
  - docs/decisions/0013-approval-gated-roster-activation.md
  - docs/decisions/0063-import-external-rosters-through-declared-manifests.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: roster-governance
issue_id: AR-83
priority: p1
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/85"
depends_on: [AR-02, AR-28]
blocks: [AR-86, AR-91, AR-92, AR-93]
---

# AR-83: Import manifest-backed upstream agent rosters into quarantine

## Problem

Large upstream-style agent libraries use a root division manifest and often
provide only a display name in Markdown front matter. Generic recursive import
either misses useful metadata or trusts undeclared directories too broadly.

## Current state

A manifest-aware local import path now validates declared divisions and feeds
every accepted definition into the bounded quarantine and immutable review
path. Imported definitions remain quarantined until explicit approval and
activation. AR-86 owns official-upstream delta synchronization. The merged
roster contains 263 approved agents, zero quarantined agents, and passes the
full-roster participation and recall gates.

## Approach

Validate the root manifest, traverse only declared division directories, derive
missing slugs and divisions deterministically from trusted relative paths, and
feed each definition through the existing bounded quarantine ingress. Reject
malformed manifests, duplicate identities, path escapes, and unsafe files.

## Dependencies

AR-02 owns coverage-gap discovery and AR-28 owns reversible activation controls.

## Acceptance

- [x] Declared manifest divisions import deterministically.
- [x] Missing slugs and divisions derive from bounded trusted metadata.
- [x] Undeclared directories, duplicates, malformed manifests, and path escapes fail closed.
- [x] Every imported prompt remains quarantined until explicit activation.
- [x] Full branch and merged-install gates pass.
