---
title: "Keep automatic work-file inference local and bounded"
status: accepted
category: decisions
created: 2026-07-13
updated: 2026-07-13
tags: [delegation, security, paths, portability, performance]
related:
  - docs/roadmap/issue-AR-17-production-hardening-portability.md
  - docs/roadmap/issue-AR-18-work-unit-paths-with-spaces.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0042
type: decision
deciders: [maintainers]
---

# ADR-0042: Keep automatic work-file inference local and bounded

## Context

Delegation infers shared work files from natural-language work-unit
descriptions so conflicting tasks can be serialized. Descriptions can contain
compact paths, existing paths with spaces, URLs, Markdown, and planned files
that do not yet exist. Treating every path-like substring as a local file can
create false conflicts. On Windows, probing a protocol-relative path can also
initiate outbound UNC or SMB filesystem access during what should be local
planning.

Recovery of a spaced path can expose a suffix that independently matches the
compact-path expression. An unbounded stream of embedded or rejected matches
could also consume disproportionate parsing and filesystem work.

## Decision

Explicit work-unit file fields remain authoritative. Automatic inference
accepts bounded compact local paths and a bounded set of supported file suffix
candidates. A spaced candidate is accepted only when it is an existing regular
file, and later matches inside that recovered span are ignored.

Reject matches inside URL tokens and reject protocol-relative or network-root
tokens before constructing a Path or consulting repository discovery. This
applies through quoting, parentheses, and Markdown wrappers. Preserve normal
local assignment and colon-delimited syntax. Bound both total raw candidates
and accepted paths.

## Consequences

- Local worktree conflict inference handles real paths containing spaces
  without emitting duplicate suffix roots.
- URLs cannot cause local-file false positives, and inferred paths cannot
  initiate network-share probing.
- A legitimate UNC path must be supplied explicitly rather than inferred from
  prose.
- Very late candidates beyond the scan cap are intentionally ignored; explicit
  file fields provide the lossless path for large generated work plans.
- Planned compact local paths remain usable even before the file exists.

## Alternatives

- **Probe every path-looking token.** Rejected because URLs and network roots
  can create false conflicts and external filesystem side effects.
- **Infer only whitespace-free paths.** Rejected because normal Windows and
  Linux checkouts can contain spaces.
- **Accept every spaced suffix without checking the filesystem.** Rejected
  because surrounding prose would become a path.
- **Remove automatic inference.** Rejected because existing callers rely on
  safe natural-language conflict detection; explicit fields remain preferred.
