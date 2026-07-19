---
title: "AR-93: Reject invisible Unicode controls at roster ingestion boundaries"
status: in_progress
category: roadmap
created: 2026-07-18
updated: 2026-07-18
tags: [roster, unicode, security, ingestion]
related:
  - docs/roadmap/issue-AR-83-manifest-roster-import.md
  - docs/roadmap/issue-AR-86-govern-complete-upstream-roster-lifecycle.md
  - docs/roadmap/issue-AR-95-bind-remediation-resolution-authority-to-complete-durable-evidence.md
  - docs/decisions/0063-import-external-rosters-through-declared-manifests.md
  - docs/decisions/0066-package-audited-roster-and-sync-quarantined-deltas.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: security
issue_id: AR-93
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/94"
depends_on: [AR-83, AR-86]
blocks: [AR-95]
---

# AR-93: Reject invisible Unicode controls at roster ingestion boundaries

## Problem

Runtime source scanning rejects C0 and C1 controls plus selected mojibake, but
permits Unicode format controls such as right-to-left overrides, isolates, and
zero-width characters. A U+202E probe passed parsing and remained in an
executable prompt, enabling reviewer, log, and UI deception.

## Current state

One shared scanner now rejects every Unicode `Cf` format control, unsafe C0/C1
controls, and conservative high-signal encoding corruption before persistence,
review, or activation. Findings retain bounded exact UTF-8 byte offsets and a
commitment to every occurrence without rendering the source. JSON, YAML, and
Markdown wrappers cannot hide a control. The packaged-roster loader applies the
same policy to prompt bodies and every manifest text, list, and path field, so a
co-located attacker cannot bypass it by recomputing prompt, version, manifest,
and digest values. Normal visible internationalized text and prompt
LF/CR/tab layout remain supported. Repository-wide release gates remain.

## Approach

Use Unicode-category-aware scanning for invisible and bidirectional format
controls, preserve exact UTF-8 offsets in findings, and enforce the same scanner
before persistence, review, and activation. Allow an exceptional format
character only at a narrowly documented non-roster protocol boundary.

## Dependencies

AR-83 owns the manifest ingress boundary. AR-86 owns the governed upstream
lifecycle and remediation queue.

## Acceptance

- [x] Bidi overrides, isolates, marks, zero-width controls, and unsafe Unicode format characters are quarantined.
- [x] Findings name codepoints and exact byte offsets without rendering unsafe source text.
- [x] JSON, YAML, and Markdown wrappers cannot bypass the scan.
- [x] Normal visible internationalized text and line or tab controls remain supported.
- [ ] Full coverage, documentation, packaging, Windows, and Linux gates pass.
