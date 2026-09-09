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
commit: a18e556c3b3de7b513f3e71a457f6e4430b1f076
short: a18e556c
date: 2026-09-09
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/816
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

## Shared staffing Hermes phase

The unchanged three requests returned in86.111s,83.279s,87.094s. Ordinary review
passes exact native card, five headers and matching authoritative accepted hash;
routing56.290s versus268.702s in the prior299.269s total sample. An invalid recruiter
candidate is retained before the existing bounded repair succeeds. Follow-up fails
critic_wrong_neighbor_selection; multi-step staff succeeds but output becomes
response_invalid. Neither is accepted or retried. Model receipt aliases are not
proof of the deployed backend and zero persisted per-call durations are unreported,
not instantaneous. All evidence is AR-404-hermes-suite-after-shared-staffing-20260909.json.
AR-418 remains open: upstream PR106490 is still unmerged, default7cd91114 unchanged.
OpenClaw and fresh trusted Codex are the next fixed phases; Claude grant is pending.


### Shared staffing native OpenClaw phase

Fresh ordinary CLI follow-up7bdd5df5-248a-48a1-aa2b-3667c35a2200 returns the
correct function in53.401s. Native llm_input with exact session/run contains the
complete selected card; five fields match Store; one authoritative accepted terminal
event binds response6d17389d102fb011d7aadc6d48f37a75a865f4f632d0b16513d55e314e3abbdf.
No --deliver, external message or manual finalization. The initial57.109s review
and95.268s multi-step fail staffing and stay in the same fixed-phase evidence.
Exact focused91passed/1skipped; the first command named a nonexistent test file
and ran no tests, retained in the packet. Isolated AR-419 verification follows;
this candidate does not establish all-host or all-case reliability.

Observer cleanup: stop/uninstall/start exits0; files, entry and permission removed.
Initial RPC warmup retained; subsequent read-only RPC check passes. Non-plugin
configuration sections unchanged. See the cleanup evidence JSON.

The first AR-419 builder record failed documentation validation for bare source
paths and one range beyond EOF; corrected to bounded path/line references before
isolated verification. No verdict was produced from the malformed record.


### Fresh trusted Codex phase

Ordinary review62.855s and same-session follow-up53.903s pass exact native cards,
five Store fields and matching authoritative accepted response hashes. Both have
classifier6; the fresh process now uses trusted hooks and current continuation.
Multi-step100.324s fails staffing and remains rejected, without an outer retry.
Full evidence: AR-404-codex-suite-after-shared-staffing-20260909.json. Native model
context does not expose the exact executing projection hash; the fresh receipt
and8/8trusted inspection are distinct from this parent's stale6e7dc299c23e runtime.
The optional policy-availability check initially lacked PYTHONPATH and could not
import the package; PYTHONPATH=. rerun passes without a source change.

First isolated AR-419 pass: criteria1/2/4 satisfied; criterion3 absent because
the focused packet omitted named malformed/cross-run/first-invalid regressions.
Retained the first record, ran existing host-hooks94 and terminal/boundary48 tests,
all passed. Added their exact evidence and source references for a second pass;
no production/test assertion changes or weakened acceptance.

## Scoped package result

The second frozen AR-419 packet satisfies all4criteria; first-pass absence retained.
Only the ordinary OpenClaw CLI finalization scope closes. Shared staffing is
applied and fresh trusted Codex passes2/3, Hermes1/3 and OpenClaw1/3. All9finish
within101seconds, but5fail; this is not a reliability guarantee. Claude remains
waiting_for_operator for two exact native rules; Hermes upstream adoption and
Zcode multi-step gates remain open under AR-404. Gateway healthy, observer removed.
No production Python, provider definitions, model overrides or validation bypass.

## Merged delivery

PR816 merged2026-09-09T14:17:38Z as271480fe21cb06d21c37889883613c86050657f0.
Exact subject: `Merge pull request #816 from Holeshot-Software-LLC/codex/ar404-shared-staffing-20260909`.
AR-419/#797 closed after all4isolated criteria passed. AR-404/418/423 remain open.
The shared-staffing branch is historical; use a new owned worktree for new changes.
