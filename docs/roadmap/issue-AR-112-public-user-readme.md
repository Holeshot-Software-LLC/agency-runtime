---
title: "AR-112: Rewrite the README for public users"
status: done
category: roadmap
created: 2026-07-20
updated: 2026-07-20
tags: [documentation, onboarding, open-source]
related:
  - README.md
  - CONTRIBUTING.md
  - docs/TROUBLESHOOTING.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: documentation
issue_id: AR-112
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/117
depends_on: []
blocks: []
---

# AR-112: Rewrite the README for public users

## Problem

The top-level README had grown into a 1,179-line internal verification and
architecture record. New users had to navigate dated test receipts, decision
language, implementation boundaries, and security jargon before finding the
product explanation, installation commands, dashboard, or everyday controls.

## Current state

The README is now a 429-line public guide. It leads with the product's value,
explains the per-request specialist model in plain language, and keeps the
commands users need for installation, controls, dashboard operations,
configuration, inference, canaries, roster updates, MCP, LiteLLM, privacy, and
troubleshooting. Internal roadmap, worklog, ADR, and dated local receipt detail
remains in the repository's dedicated documentation system instead of the
public narrative.

## Approach

Organize the README around a new user's journey: understand the product,
install it, operate it, configure it, verify it, and find help. Replace internal
phrases with a description of observable behavior while retaining important
honesty about prerelease status, host maturity, evidence headers, isolated
canaries, and quarantined roster updates.

## Dependencies

None. Existing detailed contributor, security, troubleshooting, roadmap,
worklog, and decision documents remain authoritative for their audiences.

## Acceptance

- [x] The opening explains the end-user value and dynamic specialist model.
- [x] An ELI5 section explains turn-scoped loading and native delegation.
- [x] Install, host, dashboard, CLI, configuration, header, canary, roster, MCP, LiteLLM, privacy, and troubleshooting guidance remains available.
- [x] Internal roadmap, ADR, worklog, and dated verification detail is removed from the public narrative.
- [x] Internal security jargon is replaced by plain descriptions of user-visible behavior.
- [x] Documentation metadata, links, and tracker mapping validate.
