---
title: "Import external rosters through declared manifests into quarantine"
status: superseded
category: decisions
created: 2026-07-17
updated: 2026-07-18
tags: [roster, import, quarantine, manifests, supply-chain]
related:
  - docs/roadmap/issue-AR-83-manifest-roster-import.md
  - docs/decisions/0013-approval-gated-roster-activation.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/worklog/README.md
supersedes: []
superseded_by: docs/decisions/0066-package-audited-roster-and-sync-quarantined-deltas.md
id: ADR-0063
type: decision
deciders: [maintainers]
---

# ADR-0063: Import external rosters through declared manifests into quarantine

## Context

External agent libraries can provide useful specialist breadth, but their
directory layouts, metadata completeness, and prompt authority are not trusted
runtime contracts. Recursively importing every Markdown file broadens the
supply-chain boundary and can turn examples, hidden directories, duplicate
roles, or path tricks into active instructions.

## Decision

Support generic local roster roots with an optional validated root division
manifest. When present, traverse only its declared relative division paths.
Derive a missing slug from a bounded display name and a missing division from
the trusted declared path using deterministic normalization. Feed every parsed
definition through the existing bounded ingress and duplicate checks. Reject
malformed manifests, unsafe paths or file types, identity collisions, and
unbounded metadata. Import always ends in quarantine; activation remains an
explicit, reversible approval action.

Do not hardcode or auto-download any particular upstream repository. Provenance
is the operator-selected local source and its validated content hash.

## Consequences

- Upstream-style multi-division libraries can be inspected without manual file conversion.
- Undeclared material does not silently enter the candidate roster.
- A successful import is not an endorsement, semantic audit, or activation.
- Operators still need to review prompt quality and instruction conflicts before enabling roles.

## Alternatives

- Recursively import all Markdown. Rejected because it makes directory contents an implicit authority manifest.
- Auto-enable imported roles. Rejected because foreign prompts require explicit approval.
- Vendor one named upstream roster. Rejected because the runtime should provide a generic governed boundary, not a repository dependency.

## Provenance

AR-83 records implementation and verification; commit provenance is added after
the substantive commit exists.
