---
title: "Keep OpenClaw finalization first-pass after tool use"
status: in_progress
category: roadmap
created: 2026-08-22
updated: 2026-08-22
tags: [openclaw, finalization, reliability, safety]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-272-expose-openclaw-native-finalizer-tool.md
  - docs/roadmap/issue-AR-276-gate-openclaw-provider-calls-on-agency-preflight.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/roadmap/AR-119-openclaw-hermes-verification-packet.md
  - docs/decisions/0049-openclaw-final-only-full-payload-delivery.md
  - docs/decisions/0120-construct-first-pass-evidence-headers.md
  - agency_runtime/core/installer_payload_openclaw.py
  - agency_runtime/adapters/openclaw/node_bridge.py
  - tests/test_security_turn_boundaries.py
  - tests/test_adapter_parity.py
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-277
priority: p0
tracker_url: null
depends_on: [AR-272, AR-276]
blocks: [AR-119]
---

# AR-277: Keep OpenClaw finalization first-pass after tool use

## Problem

OpenClaw received a valid Agency preflight and completed a substantive native
inspection, but its host model stopped after a preliminary sentence instead of
calling the registered `agency_finalize` tool. Agency correctly terminalized
the unheaded draft as `response_invalid`; Telegram could not queue a reply.
The finalizer guidance was present, but it was not salient enough after several
ordinary host tool calls.

## Current state

Fresh session `ar276-openclaw-nexus-restart-qwen14b-20260822-a`, native
run/trace `35efa94c-d8d9-4354-863f-d22ad852ca22`, and Store run
`e2e9e65d-540c-4aa7-86c5-b945cbc6ac62` preserve the exact required
restart-safety request. Routing decision
`c6e5e20a-af1c-454b-8344-cc66b2b9f187` accepted three LiteLLM stages through
profile `linux-task-agency-router`, requested alias/model-group
`task-agency-router`, and zero fallback. The Store selected
`ai-evaluation-engineer` and `ai-data-remediation-engineer`, and recorded skill
`openclaw-operations` as row `050e585d-f042-46f8-8b24-95b656e605b2`.

The native model used read-only tools, then returned an unheaded preliminary
sentence without calling `agency_finalize`. Finalization
`7d5428e7-469f-45cd-9920-da553e4cfa7e` records all required header fields
missing and `response_invalid`. Response/transcript hashes are
`f4f6d7b7...` / `f0f9e359...`. This is failed delivery, not accepted
substantive evidence.

A one-revision candidate was tested locally, then rejected before commit or
installation because it contradicted ADR-0120's first-invalid-response terminal
contract. Its red/green artifacts remain retained; no live host received it.
The replacement expected-red fails at exit 219 with SHA-256 `1c2f962e...`.
The first-pass-only candidate makes the native tool's persistent system
guidelines mandatory after every other tool call and repeats the exact gate at
the end of per-turn Store context. Focused tests pass 2/2; affected suites pass
47 security-boundary, 36 OpenClaw installer, and 24 OpenClaw adapter-parity
tests.

Agency-only install `e834190a-0dfe-4fba-a0cd-df2d7d75e250` loaded the clean
candidate with bundle `521b1480...`, runtime `b5d546a6...`, and launcher SHA
`41415e79...`. OpenClaw's `task-general` primary and six fallbacks remained
unchanged; Telegram and Slack were connected and probe-green. Fresh changed
trace `07e5ec33-7f33-4a0f-966e-d93ff4361b68` accepted all three exact Agency
LiteLLM stages with no fallback, but the native host made 31 read-only tool
calls and hit the 240-second provider timeout before natural finalization.
Store run `6726b5ce-c632-4af4-8f37-5a99301835d0` remains `active`/`ready` with
no terminal finalization or `agency_finalize` call. This is a retained host
timeout, not successful delivery or an Agency-router failure.

## Approach

Strengthen only the registered native tool metadata and Store-backed preflight
context. State that a preflight-enabled turn remains incomplete until the
single first-pass `agency_finalize` call, repeat the rule after other tool use,
and say explicitly that no correction pass exists. Preserve the unchanged
terminal `before_agent_finalize`, Store verifier, outbound seal, and no-retry
contract.

This requires no OpenClaw model/provider/channel change and no new durable
decision: it conforms to ADR-0049 and ADR-0120 rather than superseding them.

## Dependencies

- AR-272 registered Store-backed OpenClaw native finalizer.
- AR-276 installed prompt-build preflight and input gate.
- OpenClaw 2026.7.1-2 prompt-guideline and prompt-injection contracts.

## Acceptance

- [x] Preserve the exact failed substantive native transcript and Store terminal receipt.
- [x] Reject the policy-conflicting revision candidate before commit or installation.
- [x] Add a focused expected-red for persistent mandatory first-pass guidance.
- [x] Strengthen system and per-turn guidance without enabling a second model pass.
- [x] Preserve first-invalid-response terminalization and final-only outbound enforcement.
- [x] Affected focused OpenClaw tests and lint checks pass.
- [x] Install Agency only into stopped OpenClaw from a clean local checkpoint.
- [x] Preserve the first changed live work unit as a native provider timeout with no finalization claim.
- [ ] A genuinely changed fresh substantive work unit calls `agency_finalize`, delivers the exact header, and correlates Store/provider evidence.
- [ ] Post-live Store backup, host health, documentation gates, and local recovery pair pass.
- [ ] Tracker creation remains pending separate authorization.
