---
title: "AR-92: Redact roster source credentials from persistence and output"
status: in_progress
category: roadmap
created: 2026-07-18
updated: 2026-07-18
tags: [roster, credentials, privacy, security]
related:
  - docs/roadmap/issue-AR-83-manifest-roster-import.md
  - docs/decisions/0063-import-external-rosters-through-declared-manifests.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: security
issue_id: AR-92
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/93"
depends_on: [AR-68, AR-73, AR-83]
blocks: [AR-95]
---

# AR-92: Redact roster source credentials from persistence and output

## Problem

Roster source URLs containing query credentials can be persisted verbatim and
emitted through source-list, synchronization, upstream, and error JSON. Ingress
creates safe labels, but Store and CLI boundaries can retain the raw URL.

## Current state

Fetch behavior is bounded, but credential-bearing URL identity is not
consistently rejected or redacted at persistence and display boundaries. A
synthetic query-token probe was returned in operator-facing error JSON.

## Approach

Reject userinfo credentials, separate fetch authority from durable redacted
identity, prevent sensitive query values from reaching persistence or output,
and ensure exceptions and logs never echo them. Preserve a deterministic,
credential-free source identity for matching.

## Dependencies

AR-68 and AR-73 own trusted configuration namespaces. AR-83 owns manifest
source ingestion.

## Acceptance

- [ ] Userinfo credentials are rejected.
- [ ] Query credentials are never persisted or returned by CLI, dashboard, API, or errors.
- [ ] Authenticated fetching is unavailable unless a separate secret-safe mechanism exists.
- [ ] Credential-free canonical source matching remains deterministic.
- [ ] Common token, key, and signature query names plus arbitrary values are covered.
- [ ] Full coverage, documentation, packaging, Windows, and Linux gates pass.
