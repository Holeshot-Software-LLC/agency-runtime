---
title: "Rewrite README for public users"
status: active
category: worklog
created: 2026-07-20
updated: 2026-07-20
tags: [documentation, onboarding, open-source]
related:
  - README.md
  - docs/roadmap/issue-AR-112-public-user-readme.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 4635a0b
short: 4635a0b
date: 2026-07-20
pr: "https://github.com/Holeshot-Software-LLC/agency-runtime/pull/116"
related_issues:
  - docs/roadmap/issue-AR-112-public-user-readme.md
---

# Worklog detail: Rewrite README for public users

## Purpose

Make the repository's front door useful to prospective users instead of asking
them to read an internal implementation and verification record.

## Approach

Replace the 1,179-line README with a 429-line user journey: product value,
plain-language operation, supported hosts, installation, daily controls,
dashboard, configuration and inference, evidence header, canaries, roster
updates, MCP and LiteLLM, privacy, troubleshooting, and development.

## Challenges encountered

The rewrite had to remove internal detail without weakening important honesty
about prerelease distribution, live host evidence, optional inference,
turn-scoped specialists, isolated canaries, and quarantined roster ingestion.

## Decisions and alternatives

Detailed roadmap, worklog, ADR, release-gate, and security implementation
material remains in its dedicated documentation. The public README links only
to the contributor, security, changelog, and troubleshooting surfaces users
are likely to need.

## Verification

All Markdown metadata and intra-repository links validate, the worklog remains
deterministic, and `git diff --check` passes.

## Follow-ups

None.
