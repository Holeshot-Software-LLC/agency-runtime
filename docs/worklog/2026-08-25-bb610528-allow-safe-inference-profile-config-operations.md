---
title: "Worklog detail: Allow safe inference profile config operations"
status: active
category: worklog
created: 2026-08-25
updated: 2026-08-25
tags: [configuration, inference, security, cli, jina]
related:
  - docs/roadmap/issue-AR-293-safe-inference-profile-config-operations.md
  - docs/roadmap/handoffs/issue-AR-290.md
  - docs/decisions/0006-config-first-redacted-configuration.md
  - docs/decisions/0153-adopt-per-stage-inference-profile-routes.md
  - docs/decisions/0171-separate-native-and-structured-reranker-transports.md
  - agency_runtime/core/configuration_patch.py
  - agency_runtime/core/configuration_service.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: bb6105287338636c326771ff4ea42d115256339d
short: bb610528
date: 2026-08-25
pr: null
related_issues:
  - docs/roadmap/issue-AR-293-safe-inference-profile-config-operations.md
---

# Worklog detail: Allow safe inference profile config operations

## Purpose

Close the guarded configuration gap that prevented the documented Jina and
local/LiteLLM setup journey from creating named stage profiles and dotted
capability routes without manually editing YAML.

## Approach

The transactional patch service now validates one dynamic named profile and
the complete route map through the existing schema helpers. Direct profile
keys are rejected in ordinary set operations and accepted only through the
write-only secret operation. Ordinary profile edits preserve an existing
direct key unless the operator explicitly switches to `api_key_env`.
Secret-presence projection now reports only the boolean state for named profile
keys. README and the AR-290 recovery capsule document the guarded commands,
Windows evidence, and exact Linux continuation protocol.

## Challenges encountered

The installed CLI initially failed closed with `operation path is not
supported`. After reinstalling the repaired candidate, its changed launcher
identity caused the dashboard restart guard to refuse a stale launcher. The
owned dashboard service was explicitly reinstalled and returned to current,
active, reachable state. The external approval boundary separately rejected
tracker creation because push/merge authorization did not explicitly authorize
issue and label mutations; no tracker object was created.

## Decisions and alternatives

Manual YAML editing and storing the supplied key in a profile were rejected.
Dynamic operations reuse ADR-0006's transaction/redaction boundary and
ADR-0153's existing profile schema instead of introducing a second writer.
The route map remains one atomic value because dotted route identifiers cannot
be represented safely as another dotted operation path. No new architectural
decision was required.

## Verification

- 146 focused configuration, CLI, inference-profile, embedding, reranker, and
  security tests passed with warnings as errors; the dedicated secret
  preservation/environment-switch regression also passed.
- Ruff lint and format checks passed for every affected Python file.
- Metadata, policy availability, worklog, documentation validation, and diff
  checks passed; documentation validation covered 818 Markdown files.
- The installed CLI wrote environment-referenced Jina profiles and both recall
  routes. Bounded Agency transport checks applied exact embedding and native
  reranker model receipts without exposing the credential.
- The repaired owned dashboard service is installed, enabled, active, current,
  reachable, and opened on loopback.

## Follow-ups

- Obtain explicit tracker authorization and create/link AR-289 through AR-293.
- Merge current remote `main` without rewriting these recorded commit SHAs,
  then run the named fast and release-relevant source gates.
- Complete attended Windows host activation locally and the bounded Linux
  artifact/service/local-provider continuation described in the AR-290 capsule.
- Do not tag or create a release until every canonical checklist gate has
  current proof and explicit publication authorization.
