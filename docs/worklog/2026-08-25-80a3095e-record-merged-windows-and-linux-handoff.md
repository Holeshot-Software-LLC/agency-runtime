---
title: "Worklog detail: Record merged Windows and Linux handoff"
status: active
category: worklog
created: 2026-08-25
updated: 2026-08-25
tags: [setup, windows, linux, jina, release, handoff]
related:
  - docs/roadmap/issue-AR-290-end-to-end-guided-setup.md
  - docs/roadmap/issue-AR-294-restore-expanded-configuration-regressions.md
  - docs/roadmap/handoffs/issue-AR-290.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 80a3095eaf7fd68f543fa6277da5bacd7029642e
short: 80a3095e
date: 2026-08-25
pr: null
related_issues:
  - docs/roadmap/issue-AR-290-end-to-end-guided-setup.md
  - docs/roadmap/issue-AR-294-restore-expanded-configuration-regressions.md
---

# Worklog detail: Record merged Windows and Linux handoff

## Purpose

Replace pre-merge and pre-credential setup notes with exact merged-source,
installed Windows, live Jina, dashboard, and Linux-continuation evidence.

## Approach

Merge current remote main without rewriting the existing worklog chain, repair
the two expanded regression fixtures, rerun the current source gates, install
the exact clean checkpoint, configure Jina through environment indirection,
exercise one bounded embedding and reranking call, refresh every detected
harness, and record a paste-ready Linux release-verification prompt.

## Challenges encountered

The exact reinstall changed the owned launcher identity and exposed one stale
Claude projection. An all-harness refresh cleared it. Restricted inspection
could not see the user-owned scheduled task, so normal-user status was used to
prove the dashboard service and host projections rather than inferring health.

## Decisions and alternatives

The Jina credential was kept out of argv, YAML, repository files, and displayed
evidence. Cold inventory and deterministic smoke remain distinct from attended
host trust, loading, and Rule-4 proof. Linux is assigned only the gates it can
observe and may not inherit Windows evidence.

## Verification

- The corrected expanded run passed 1,127 tests with 21 skips; all 136 dashboard
  UI tests, full Ruff and docs gates, routing thresholds, and 160 conformance
  mutations passed.
- Exact installed deterministic smoke passed 8/8, and installed affected
  modules hash-matched source.
- Bounded live calls applied `jina-embeddings-v3` at 1,024 dimensions and
  `jina-reranker-v3.5` over two documents without displaying the credential.
- Authoritative status reports `runtime_drift: null`; the dashboard service is
  owned, enabled, active, current, reachable, and open on loopback.
- The AR-290 capsule remains within 180 lines and 12 KiB, and all 828 Markdown
  files pass repository validation.

## Follow-ups

Obtain explicit authorization for AR-289 through AR-294 tracker creation before
repository-compliant merge. Complete attended Codex trust and fresh host
loading on Windows, then collect Linux artifact, local-provider, service, and
present-host evidence. No tag, publication, or release is authorized.
