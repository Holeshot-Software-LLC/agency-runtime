---
title: "Apply approved shared staffing and verify native permission boundaries"
status: active
category: worklog
created: 2026-09-09
updated: 2026-09-09
tags: [inference, native, permissions]
related:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/issue-AR-419-finalize-openclaw-cli-responses.md
  - docs/roadmap/issue-AR-423-preserve-claude-hook-specialist-context.md
  - docs/decisions/0242-align-hermes-openclaw-with-owner-shared-staffing.md
supersedes: []
superseded_by: null
type: worklog
commit: null
short: null
date: 2026-09-09
pr: null
related_issues:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/issue-AR-419-finalize-openclaw-cli-responses.md
  - docs/roadmap/issue-AR-423-preserve-claude-hook-specialist-context.md
---

# Apply approved shared staffing and verify native permission boundaries

## Purpose

The owner explicitly authorizes shared staffing, reports Codex trusted, and asks
how to grant Claude tool access because launching it produces no prompt.

## Approach

Remove only the two host overrides with a validated candidate and compare-before-
replace check; retain a private backup. Global profiles, answering models and
unrelated settings stay byte-identical. Fresh resolution aligns all five hosts
for planner, recruiter, critic, hiring and recall routes. No specialist is selected
by this configuration change. ADR-0242 records the owner operating decision.

A fresh bounded Codex hooks/list inspection reports 8 enabled/trusted hooks,
0 modified/missing/duplicate entries. This clears the reported trust prerequisite;
fresh native accepted-turn evidence remains to be collected. Do not reinstall
Codex and invalidate the newly approved hooks.

Claude's official permissions reference confirms /permissions manages Allow rules;
normal startup alone does not trigger a tool-use permission request. The two exact
installed MCP rule names are documented in troubleshooting. The owner can save
them through the dialog or authorize their normal user-settings write. That grant
is still pending; no permission rule or bypass was applied during this checkpoint.

## Challenges encountered

The initial read-only route validation used an incorrect ProviderEntry field name
and stopped before configuration mutation. Corrected typed timeout access validates
the candidate and the applied result. Prior failed staffing, denied Claude calls
and both closed-transport parent finalizer attempts remain historical evidence.

## Decisions and alternatives

Per-tool native Allow rules are the supported permission mechanism. Do not enable
bypassPermissions, grant a whole server, fabricate hook hashes or manually accept
failed receipts. Preserve inference authority and independent critic/validators.

## Verification

Profile resolver checks pass. Inference-profile tests:88passed; named production
spine:1151passed/3skipped in69.99s; UI224passed. Ruff and docs1359passed. Production source is unchanged from cd86e40a,
so its frozen 188/188 conformance remains applicable. No exhaustive or Windows run.

## Follow-ups

Run the fixed native phase after_shared_staffing on Hermes/OpenClaw and a fresh
trusted Codex process, one attempt per case under the original 360-second bound.
Capture OpenClaw input with the previously verified bounded local observer and
remove it normally afterward. Claude awaits its exact native tool grant; Zcode's
prior accepted review/follow-up and failed multi-step stay explicitly in scope.
Keep AR-404/418/419/423 open until their isolated gates have current evidence.

## Native observation checkpoint

Normal OpenClaw observer stop/install/grant/start exits zero, with only plugin
configuration changed. Native runtime imports all three callbacks for exactly
the new review/follow-up and multi-step session keys. The immediate RPC check
is still warming up; the subsequent read-only check is healthy, without another
restart. Per-session16events,1MiB/event and8MiB/process bounds remain. No delivery
or external message is requested. Observed callbacks and exact cards remain to
be collected from the new native phase; registration alone is not proof.
