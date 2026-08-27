---
title: "Prove ordinary Codex completion"
status: active
category: worklog
created: 2026-08-27
updated: 2026-08-27
tags: [ar-297, codex, unattended, containers, finalization]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
supersedes: []
superseded_by: null
type: worklog
commit: c5749a29b700446ad5157b62cc4d6c984624ccf9
short: c5749a29
date: 2026-08-27
pr: null
related_issues:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
---

# Worklog detail: Prove ordinary Codex completion

## Purpose

Close the later ordinary Codex row with one normal unattended managed-hook
invocation after the first attempt's opaque collaboration failure.

## Approach

R2 retained an exact direct-only self-contained task and used stdin so its hash
covered the precise native input. The same exact container, ChatGPT auth,
default model, managed policy, read-only sandbox, dedicated empty Git worktree,
and process-memory LiteLLM credential were preserved. No tool, child,
collaboration, activation bypass, or configuration change was used.

## Challenges encountered

The optional remote Cloudflare MCP still logged one OAuth diagnostic, but it
was unrelated to Agency and did not stop the turn. Unlike R1, the explicit
direct-only constraint prevented Codex from creating an opaque child, allowing
the normal Stop hook to validate the parent response directly.

## Decisions and alternatives

R1 remains retained as fail-closed evidence and is not rewritten as success.
R2 required no model, auth, endpoint, or Agency route choice. Codex is closed
independently while the other three ordinary harnesses remain open.

## Verification

- Exact 824-byte task: `3ef304e5...dd3`.
- Native stdout/stderr/exit: `69f672c2...2874`, `5079dcb4...365f`, and
  `bde29436...120`.
- Native receipt/rollout: `53598f2a...5fd5` and `693e9dfe...4cd9`; the exact
  2,659-byte card occurs once and there is no child or collaboration call.
- Store correlation `b269dc11...478d` passes quick-check and binds accepted
  finalization `f7937fc5...46e6` with `missing=[]`.
- Metadata, policy, worklog, documentation, and diff checks all exit 0.

## Follow-ups

Refresh Claude's same-method OAuth, select the Hermes and OpenClaw aliases,
then continue host/dashboard proof, named gates, and teardown.
