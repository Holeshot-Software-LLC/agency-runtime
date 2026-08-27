---
title: "Prove exact host dashboard install"
status: active
category: worklog
created: 2026-08-27
updated: 2026-08-27
tags: [ar-297, linux, installation, dashboard, systemd]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - docs/decisions/0176-use-owner-runtime-temp-for-nonroot-user-services.md
supersedes: []
superseded_by: null
type: worklog
commit: 6d32c459dfc8b027d4873303a32f7dce33492c17
short: 6d32c459
date: 2026-08-27
pr: null
related_issues:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
---

# Worklog detail: Prove exact host dashboard install

## Purpose

Close the exact Linux host-install and authenticated-dashboard row for AR-297
using the immutable release candidate already proved in dedicated containers.

## Approach

Install the exact wheel in an owner-private candidate virtual environment, use
OpenClaw's native maintenance command to stop and restore its live gateway, and
run the single attended all-host install without an activation bypass. Verify
the resulting bundles, immutable packaged runtime, systemd contract,
authenticated HTTP boundary, restart behavior, and complete workforce prompt
independently of the installer.

## Challenges encountered

The first dry run correctly rejected a process-only LiteLLM key as unsuitable
for a durable service, and a second preflight correctly refused to mutate while
the OpenClaw gateway was live. The first immediate post-restart OpenClaw status
raced RPC readiness, while the next status passed. An initial packaged-context
attestation also caught checkout-current-directory import contamination; the
clean `/tmp` rerun bound the installed wheel to its immutable runtime. Each
negative diagnostic is retained rather than rewritten as success.

## Decisions and alternatives

Codex remains truthfully `activation_required` after the attended combined
install; no bypass was introduced. The dashboard service does not persist the
transient LiteLLM credential, no dashboard inference is claimed, and no foreign
host policy was overwritten. The native OpenClaw gateway was restored after
the bounded maintenance window.

## Verification

- Exact combined-install JSON `00d51490...b559` exits 1 solely for attended
  Codex activation; Hermes, OpenClaw, Claude, and dashboard installation pass.
- Packaged-context attestation `ec2f8fdd...9292` exits 0 and binds immutable
  runtime `dbf1581f...f301`; all four installed bundle digests are current.
- Systemd contract `b3ffa572...f888` and Agency restart
  `b72f17e7...94d8` exit 0 with the service enabled and active/running.
- Post-restart HTTP proof `358ab92e...d94f` exits 0 with 401/200 no-store auth
  behavior and exact 2,659-byte workforce prompt `c3cfc098...5848`.
- Browser proof `7b22dd85...c483` exits 0 with no console, page, or request
  failures; screenshot `222d5109...b5ac` shows the full owner view.
- Evidence receipt manifest `4b48dcc8...7e6b` binds the retained host artifacts.
- Metadata, policy, worklog, documentation, and diff checks all exit 0.

## Follow-ups

Complete ordinary Claude, Hermes, and OpenClaw turns, run every named repository
gate, remove all AR-297 proof containers, and issue the Linux-scoped verdict.
