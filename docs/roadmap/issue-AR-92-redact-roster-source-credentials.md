---
title: "AR-92: Redact roster source credentials from persistence and output"
status: done
category: roadmap
created: 2026-07-18
updated: 2026-07-20
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

Durable source identity rejects userinfo, every non-empty query, and fragments
before persistence. One-shot HTTP ingestion may carry query authentication only
to the network request; candidate content, source labels, errors, and durable
records receive the query-free identity. Legacy unsafe rows are disabled,
redacted, and purged during schema migration.

## Approach

Reject userinfo credentials, separate fetch authority from durable redacted
identity, prevent sensitive query values from reaching persistence or output,
and ensure exceptions and logs never echo them. Preserve a deterministic,
credential-free source identity for matching.

## Dependencies

AR-68 and AR-73 own trusted configuration namespaces. AR-83 owns manifest
source ingestion.

## Acceptance

- [x] Userinfo credentials are rejected.
- [x] Query credentials are never persisted or returned by CLI, dashboard, API, or errors.
- [x] Query-authenticated fetching is confined to the content-free transient fetch boundary.
- [x] Credential-free canonical source matching remains deterministic.
- [x] Common token, key, API-key, and signature query names plus arbitrary values are covered.
- [x] Full coverage, documentation, packaging, Windows, and Linux gates pass.
