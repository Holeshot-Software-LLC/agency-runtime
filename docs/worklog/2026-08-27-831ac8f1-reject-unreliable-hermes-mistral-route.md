---
title: "Reject unreliable Hermes Mistral route"
status: active
category: worklog
created: 2026-08-27
updated: 2026-08-27
tags: [ar-297, hermes, mistral, litellm, unattended, finalization]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - docs/decisions/0181-use-litellm-aliases-as-host-inference-control-plane.md
supersedes: []
superseded_by: null
type: worklog
commit: 831ac8f19941adbcf883dfbf8d409b33e6962cda
short: 831ac8f1
date: 2026-08-27
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/337
related_issues:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
---

# Worklog detail: Reject unreliable Hermes Mistral route

## Purpose

Close the bounded Mistral investigation with a self-contained ordinary task and
record why the approved Hermes model route cannot support the unattended
governed-finalization gate reliably.

## Approach

R3 used the same production container, UID/GID 10000, authenticated LiteLLM
alias, Mistral backend, endpoint, context, disabled thinking, normal Hermes
configuration, four-turn limit, and no bypass flags. Only the task changed: an
exact retained HTML fragment supplied all evidence locally and prohibited
files, network, browser access, external services, mutation, and questions.

Post-turn Agency and native Hermes databases were backed up through SQLite,
copied into owner-private evidence, integrity checked, and projected into
content-safe receipts. Separate offline native inspection compared raw and
model-visible tool definitions and exercised the read-only `tool_describe`
bridge without making a model call.

## Challenges encountered

Mistral produced a substantive report and copied the initial Agency header, but
made zero tool calls. The complete API content contained the exact specialist
card and the direct-or-bridge finalizer instruction. The raw registry exposed
`agency_finalize`; Hermes correctly deferred it behind its three bridge tools,
listed it in the embedded catalog, and returned its schema through
`tool_describe`. Task access and host bridge availability are therefore ruled
out, leaving model adherence as the failed compatibility gate.

## Decisions and alternatives

No fourth Mistral retry is justified after three distinct bounded failures.
No model, alias target, endpoint, context, thinking level, authentication route,
or service setting was changed. The mandated owner interview must select any
replacement Hermes route. The fail-closed responses and all three native exit-0
files remain retained rather than being promoted as completion.

## Verification

- The 684-byte task hashes to `7411494b...49de` on host and container.
- Native stdout/stderr/exit hash to `a94a1e6c...8a68`,
  `9e844172...fff1`, and `bde29436...120`.
- Agency Store/correlation hash to `80942b3b...3944` and
  `6d1d3f52...8a29`; native state/receipt hash to `00211b3c...b1c` and
  `f3b89dac...cf92`. Both databases pass quick-check and the receipt exits 0.
- Accepted routing selects `section-508-accessibility-specialist`; its exact
  3,227-byte card occurs once in the 7,608-byte API content.
- The 3,627-byte draft hashes to `62b553e6...5fd0`, records zero tool calls,
  and terminates as `response_invalid`, missing only `actual_model_selected`.
- Metadata, policy availability, worklog consistency, documentation validation
  for 908 Markdown files, and diff check all exit 0.

## Follow-ups

- Interview the owner for the next local model behind the stable authenticated
  `task-agency-hermes` alias, then require an accepted ordinary R4 receipt.
- Complete ordinary Codex, Claude, and OpenClaw proofs, exact host install and
  authenticated dashboard evidence, named gates, and final teardown under
  AR-297.
