---
title: "Isolate Hermes tool admission gap"
status: active
category: worklog
created: 2026-08-27
updated: 2026-08-27
tags: [ar-297, hermes, tool-calling, container, unattended]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - docs/decisions/0181-use-litellm-aliases-as-host-inference-control-plane.md
supersedes: []
superseded_by: null
type: worklog
commit: 9a7a99bfd850e92adb75700e926db5c6bbc69abf
short: 9a7a99bf
date: 2026-08-27
pr: null
related_issues:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
---

# Worklog detail: Isolate Hermes tool admission gap

## Purpose

Record the corrected ordinary Hermes R2 without promoting its native exit 0,
bind the complete prompt and Store evidence, and move the next investigation
from LiteLLM serialization to Hermes tool-definition admission.

## Approach

The same normal UID/GID 10000 `hermes chat -q` process ran through the corrected
`ollama_chat/` deployment, with the approved alias, backend, endpoint, context,
thinking level, and process-memory authentication unchanged. Agency and native
Hermes SQLite snapshots were projected into content-safe correlation receipts.
A bounded temporary structural graph confirmed that the installer facade calls
`render_hermes_plugin`; runtime inspection then compared dynamic registry state
with the actual model-visible tool definitions.

## Challenges encountered

Hermes again returned exit 0 while Agency correctly rejected the ungoverned
draft. Unlike R1, the model emitted normal assistant text after the chat
transport correction, but it still made no tool call. Hermes also printed
`Unknown toolsets: agency-runtime`. The registry contains the dynamically
registered `agency_finalize`, yet the 21 definitions supplied to the model omit
it and the generated plugin manifest declares no `provides_tools` entry.

## Decisions and alternatives

No third live retry was started. Changing models or aliases would require an
owner interview and would not address a tool absent from the model definition.
The next package must identify the exact registry/filtering defect and add a
focused regression before changing the generated plugin. R1 and R2 remain
immutable negative evidence.

## Verification

- Native stdout/stderr/exit hash to `a94a1e6c...8a68`,
  `988c3550...2bfb`, and `bde29436...120`; the exit file records 0.
- Agency Store `5c95a565...cdd4` and native state `a937c8f9...b1f7` pass
  SQLite quick-check. Correlation `2ebc93fd...712e` binds accepted routing and
  `response_invalid`; native receipt `a2a44504...761b` exits 0.
- The 397-byte task hashes to `fb36e4a...26235`; the 3,227-byte specialist card
  `589a6e0c...303e` appears exactly once in the 7,321-byte API content.
- The 842-byte assistant response hashes to `c97fa7fa...fb19`, ends with
  `finish_reason=stop`, and records zero native tool calls.
- Metadata, policy availability, worklog consistency, documentation validation
  for 907 Markdown files, and diff check all exit 0. Final documentation stdout
  hashes to `f79bd970...f140`; the retained initial failures show the corrected
  full-SHA and `PYTHONPATH` invocation rather than hiding them.

## Follow-ups

- Trace Hermes model-tool filtering and generated manifest registration, add a
  focused regression, and make the smallest source repair if confirmed.
- Rebuild the exact candidate after any source change, repeat the four clean
  installs as required, and finish the four ordinary harness proofs under
  AR-297.
- Host installation, authenticated dashboard evidence, named gates, teardown,
  and the Linux-scoped verdict remain pending.
