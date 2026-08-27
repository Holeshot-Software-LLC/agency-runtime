---
title: "Diagnose Hermes tool transport"
status: active
category: worklog
created: 2026-08-27
updated: 2026-08-27
tags: [ar-297, hermes, litellm, ollama, tool-calling, container]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - docs/decisions/0181-use-litellm-aliases-as-host-inference-control-plane.md
supersedes: []
superseded_by: null
type: worklog
commit: e56d1f4b4b4041b378f1d20d229352a533623120
short: e56d1f4b
date: 2026-08-27
pr: null
related_issues:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
---

# Worklog detail: Diagnose Hermes tool transport

## Purpose

Record the first later ordinary Hermes process without overstating its native
exit 0, prove complete Agency specialist-card visibility independently, and
isolate the exact tool-call transport mismatch before the bounded retry.

## Approach

Hermes ran as native UID/GID 10000 through normal `hermes chat -q`, with no
activation bypass or ignore/safe flags. The approved LiteLLM credential entered
only process memory. Post-turn Agency and native Hermes SQLite snapshots were
copied into private evidence, integrity checked, and projected into
content-minimized receipts. LiteLLM spend rows, plugin registration, enabled
tool inventory, and the local Mistral template were correlated separately.

The failing AR-297-owned `task-agency-hermes` deployment was then removed and
recreated on the same approved Mistral backend, endpoint, 65,536-token context,
and disabled-thinking setting. Only the LiteLLM provider transport changed from
`ollama/` text completion to `ollama_chat/`, which preserves the model's native
tool-call envelope. The current deployment declares function calling because
the retained model template proves that capability.

## Challenges encountered

The native process returned exit 0, but the Agency output gate correctly
withheld the draft. Mistral emitted a 178-byte textual `clarify` JSON object
instead of a structured call, so no `agency_finalize` invocation occurred.
This required separating native process success, routing, prompt visibility,
model receipts, and accepted finalization rather than treating one exit code as
the matrix verdict.

## Decisions and alternatives

No model, endpoint, context, thinking level, authentication route, or service
manager changed. Switching to another local model would require an owner
interview and was unnecessary because the installed Mistral template already
contains native tool-call branches. The first failure remains immutable
evidence; it is not overwritten or reclassified after the transport repair.

## Verification

- Native stdout/stderr/exit hash to `cef7b4ec...f849`,
  `2615ac5e...340e`, and `bde29436...120`; the exit file records 0 while the
  visible response is Agency's fail-closed replacement.
- Agency Store `01ca5974...b14` passes SQLite quick-check. Correlation
  `6011ee8b...a5fd` proves one accepted route, the selected
  `section-508-accessibility-specialist`, six alias-only receipts, and one
  `response_invalid` finalization.
- Native state `a71855e7...524e` passes SQLite quick-check. Receipt
  `87866dee...c7e9` proves the 397-byte task hash `fb36e4a...26235` and one
  exact occurrence of the selected 3,227-byte card `589a6e0c...303e` in the
  7,321-byte native API user content.
- Plugin doctor, enabled tools, Mistral template, and LiteLLM spend receipts
  hash to `5de107fb...c496`, `ef80af98...c1a5`, `706c4d11...98c8`, and
  `32964473...0917`.
- Old deployment removal and corrected sole-deployment creation receipts hash
  to `958a2d6c...8c40` and `584558db...639`; the current deployment is
  `4089bb62-1a0a-4658-a6b3-89115512f0fe`.
- Metadata, source-bound policy availability, worklog consistency,
  documentation validation for 907 Markdown files, and diff check all exit 0.
  Final documentation-validation stdout hashes to `f79bd970...f140`.

## Follow-ups

- Retry the same ordinary Hermes process through the corrected alias and require
  accepted finalization plus exact post-turn prompt/Store/native correlation.
- Complete ordinary Codex, Claude, and OpenClaw proofs, then host installation,
  authenticated dashboard evidence, named gates, and final container teardown
  under AR-297.
- Tracker writes, push, PR, merge, tag, signing, publication, release, and
  hosted workflow dispatch remain prohibited.
