---
title: "Hermes and OpenClaw native refresh"
status: active
category: worklog
created: 2026-09-08
updated: 2026-09-08
tags: [hermes, openclaw, native, verification]
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/795
related:
  - docs/roadmap/issue-AR-419-finalize-openclaw-cli-responses.md
  - docs/roadmap/issue-AR-418-preserve-hermes-truncation-terminal-evidence.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/handoffs/issue-AR-404.md
  - docs/worklog/2026-09-08-trusted-native-acceptance.md
supersedes: []
superseded_by: null
related_issues:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
---

# Hermes and OpenClaw native refresh

## Outcome and scope

Owner approved refreshing Hermes, then OpenClaw with its normal gateway
stop/update/restart workflow, followed by one ordinary native turn per host.
Check actual staffing, injection, truthful headers and terminal finalization.
Source baseline is clean main24b50cb8. AR-414/415 completion proves Codex only;
AR-404 remains open. No broad backlog, Windows or credential changes.

## Installed checkpoint

Both hosts initially report registered/enabled, loaded unknown, no attestation,
and published projection4d2934ddb59e behind installed source6e7dc299c23e.
Hermes normal `agency install --agent hermes --no-dashboard --json` succeeds
at2026-09-08T19:53:11Z. Plugin enabled and listed by native CLI, hook budget read
succeeds. Bundlebdce2726fd101e572287ba5ebc9c938f8ac66a3d39f6065222d9a5e3a78f2ea9;
backup identifier20260908T195311.634794Z. Runtime remains unverified until fresh
native execution. No dashboard start or existing Hermes process termination.

## Verification

Existing same-source checks immediately precede this package: focused108pass,
production1151pass/3skip, UI224pass, Ruff and routing pass; frozen-source
conformance188/188pass. Production/test/script diff from source8629e2ed is empty.
All614installed files match the verified wheel. This package changes host
integration and records, not Python defaults. Native evidence follows; installer
success is not native proof. No exhaustive corpus or cross-platform claim.

## Follow-ups

Run fresh Hermes and OpenClaw native turns after their normal refresh; inspect
exact failures rather than retrying for approval. Preserve operator files and
restore OpenClaw gateway service after the approved maintenance window.

## Hermes native result

Fresh ordinary `hermes --usage-file <capture> -z <supplied-review>` ran
19:55:07.459800Z to20:00:47.520245Z,340.061s, exit0. Exact session and
content-free receipt plus supplied-task output live in the repository JSON
`docs/roadmap/evidence/AR-404-hermes-native-20260908.json`.
Staffing accepted code-reviewer in146.452s on existing host-specific
linux-task-agency-router/task-agency-router planner/recruiter/critic routes.
All recorded staffing stages applied. This did not exercise Codex's repaired
recruiter route. Native api_content contains the complete specialist contract;
its SHA256 isf9e8834e0d6a5071fbfaee12222b5226a16430ada9c2fde6454099b162de8259.

Hermes executed only the supplied inline example and searched for agency_finalize.
It then returned `Response truncated due to output length limit`, no five headers,
no finalizer call, zero terminal events and active Agency run. Native usage says
completed=false. The first answering model receipt isglm-5.2 viaalias-hermes-chat;
no raw second response or actual token cap is proven. AR-418/#796 owns this
new failure. No approval-seeking retry or provider/model change was performed.

## OpenClaw maintenance checkpoint

Native stop initially required explicit confirmation via its documented --force
flag. The owner's approval already covered stopping this gateway; the confirmed
normal stop succeeded, followed by inactive/dead state and a free listening port.
Normal installer completed with backup20260908T200236.612935Z and bundle
6cc9430de88468f19b9718fd0bb7bbf4b41675e90ae19292a3c3624f380b8922.
Native plugin installation and enablement succeeded. Existing final-only streaming
policy remained unchanged; the whole native configuration and every top-level
section hash matched the pre-maintenance baseline.

Native gateway start succeeded. Immediate status showed running before RPC was
ready; a subsequent bounded read proved rpc.ok=true. Service restored before the
native trial. Installer loaded/runtime-verified status is not a completed-turn
claim. No dashboard, credential or provider configuration was changed.

## OpenClaw native result

One normal CLI turn used the configured OpenClaw owner agent and a fresh session
key, with no specialist/model override and no --deliver external message.
20:06:06.231368Z to20:08:02.755003Z,116.524s, exit0. Trace
bfbdfdc5-59b8-481d-b0d6-8e4f4abc872a, native session
ccce9bc3-4818-4454-b5bd-6ade5ded98fb. Native key and own-task response are retained
in docs/roadmap/evidence/AR-404-openclaw-native-20260908.json.

Staffing accepted code-reviewer in91.052s. All five response fields match the
installed Store header reader. Native actual answering metadata identifies
litellm/task-general; the header truthfully identifies the workforce wrapper.
Response, native final-visible and native final-raw text share SHA256
f504298853514c59178dfe43af577b6b814a201ad6a903b72ad65deba5103052.
Native statusok/summarycompleted/stopReasonstop does not prove Agency completion:
Store remainsactive/ready, terminal IDnull, zero finalization events. No native
tool call or manual finalization occurred. AR-419/#797 records the missing
ordinary terminal handoff and exact injection evidence.

Native trajectory prompt/system prompt are redacted; finalPromptText contains
only the350-character caller prompt. Exact card injection is therefore unproved.
Native installed index.js, openclaw.plugin.json and package.json match staged
bytes; index.js SHA256eccc1eb668c671d1b2ba8b0de6de09d6a88cc8874e4a37afabc6a857242bef38.
No further native retry was used to seek approval.

## Final verification scope

Fresh focused Hermes/OpenClaw/installer254passed/1skipped in6.28s. Named fast
production1151passed/3skipped in77.73s; UI224passed. Production/test/script
sources remain identical to verified8629e2ed, so prior frozen-source
conformance188/188 with source_unchanged=true remains applicable. Docs1341files, metadata, Ruff779files and routing pass; strict tracker parity
is checked before merge. No exhaustive
corpus, Windows or compatibility matrix, hosted dispatch, external message or
performance certification. Both native attempts are terminal as processes; their
unfinalized Agency runs are preserved as evidence, not manually repaired.

Both integrations are refreshed; the OpenClaw gateway is restored RPC-green.
The bounded verification outcome is negative for complete native acceptance:
Hermes has staffing/injection but truncation failure; OpenClaw has staffing and
truthful headers but no finalization or exact card proof. AR-418/419 and umbrella
AR-404 remain open. Next repair those exact lifecycle failures before another
success claim. The package does not undo the separately accepted Codex proof.

## Publication checkpoint

PR795 merged as `ca0914cd25fa4f565fc1339da44882b07520edde` with the exact
subject `docs(hosts): merge PR795 refreshed native verification`. This merge
records both observed native failures and leaves AR-404, AR-418 and AR-419 open.
