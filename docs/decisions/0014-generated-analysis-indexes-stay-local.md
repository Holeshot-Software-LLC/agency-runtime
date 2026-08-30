---
title: Keep generated analysis indexes out of version control
status: accepted
category: decisions
created: 2026-07-10
updated: 2026-07-10
tags: [repository, generated-files, maintenance]
related: []
supersedes: []
superseded_by: null
id: ADR-0014
type: decision
deciders: []
---

# ADR-0014: Keep generated analysis indexes out of version control

## Context

Code graph and chunk-analysis tools produce large databases, caches, reports, and rendered graph artifacts. These files are reproducible, machine-specific, and can dwarf meaningful source changes.

## Decision

Do not track generated code-analysis indexes or their output directories. Ignore the known tool directories and regenerate them locally when analysis is needed.

Generated reports are not documentation merely because they use Markdown. If a generated result contains a durable conclusion, capture that conclusion in a maintained repository document rather than committing the generator cache.

## Consequences

- Repository history remains focused on source and maintained documentation.
- Clones are smaller and diffs are reviewable.
- Generated analysis must be recreated before use.
- Any durable finding needs an intentional human-maintained record.

## Alternatives

- Commit all generated outputs. Rejected because large, rapidly stale artifacts obscure meaningful changes.
- Commit only the generated Markdown report. Rejected because it still becomes stale without a maintenance contract.
- Store generated artifacts in a release or external cache. Permissible for distribution, but not part of the source repository contract.

## Provenance

Commit 442b91a removed generated graph and chunk indexes from tracking and added ignore rules. The README contributing guidance requires those indexes to be regenerated on demand.
