---
title: "Prove exact multi-harness installs"
status: active
category: worklog
created: 2026-08-27
updated: 2026-08-27
tags: [ar-297, claude, hermes, openclaw, container, install]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - docs/decisions/0181-use-litellm-aliases-as-host-inference-control-plane.md
supersedes: []
superseded_by: null
type: worklog
commit: 5e1decf8a4bf711e5f469185c8afd1442295cf41
short: 5e1decf8
date: 2026-08-27
pr: null
related_issues:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
---

# Worklog detail: Prove exact multi-harness installs

## Purpose

Close AR-297's separate production-container installation row with exact,
retained fresh-state evidence for Claude Code, native-UID Hermes, and OpenClaw
systemd after the already proven exact Codex transaction.

## Approach

Each harness used its exact `7dbd0cbc` image with host networking, the approved
mode-0600 Agency config, and explicit candidate/proof labels. Fresh absence was
proven before a non-mutating install dry run and one production install.
Claude received its existing first-party subscription state privately. Hermes
ran Agency as UID/GID 10000. OpenClaw used a running systemd user manager and a
mode-0600 native profile containing only the approved LiteLLM alias plus
environment SecretRefs; neither secret value entered retained evidence.

After installation, read-only status and native plugin commands captured
registration, enablement, and available runtime loading. Each Store and native
manifest/launcher was copied into owner-private evidence and hashed. This
package deliberately did not claim an ordinary post-install process.

## Challenges encountered

The first Claude setup-only container exited before Agency because its wrapper
copied credentials before creating `/root/.claude`. It remains retained as a
transparent negative receipt; a fresh replacement using the same image fixed
only that container setup. OpenClaw's successful dry run created an otherwise
empty Agency ephemeral directory. The native plugin remained absent, and the
exit-1 post-dry-run absence diagnostic is retained rather than discarded.

## Decisions and alternatives

The initial OpenClaw profile intended to use a LiteLLM generation alias rather
than a direct model identifier. Its gateway and LiteLLM credentials remained
exact environment SecretRefs. The gateway stayed stopped for safe
installation; a runtime plugin inspection proved all hooks without conflating
installation with the later ordinary turn.

## Verification

- Claude absence, dry-run, install, and status receipts are `f95648d6...9919`,
  `67f5125e...7467`, `798da70f...5afa`, and `bb4a673e...36fb`. Bundle
  `ea4e9444...783f` is registered/enabled; Store `6d9568d0...4dc2` passes
  quick-check with no ordinary run.
- Hermes absence, dry-run, install, and status receipts are
  `c90213d8...175c`, `f9c06879...9c59`, `d2d7ce1b...5ae1`, and
  `5cd0d280...f88`. Bundle `d7a3a3a7...3a33` is registered/enabled under
  UID 10000; Store `45f89485...887b3` passes quick-check with no ordinary run.
- OpenClaw absence, dry-run, install, and runtime-plugin receipts are
  `534327ca...74a`, `193e891f...6444`, `9a0f49b5...1b7a`, and
  `bfa7557a...b3f7`. Runtime-verified bundle `4d9afa0b...d79` loads all 13
  hooks. Store `c53dc2a9...01b6` passes quick-check with zero runs.
- The initial sanitized OpenClaw receipts `d7450a2a...627a` and
  `1fdf490a...d6d` preserve SecretRefs but use the nonexistent
  `task-agency-generator` spelling. Authenticated alias inventory
  `7163aa90...911a` caught that pre-turn error; correction `65ceab8f...d161`
  exits 0 and sanitized receipt `2180a4dc...23e8` proves current SHA
  `88409233...e909` uses exact `task-agency-generation` plus SecretRefs.
- Metadata, policy availability, worklog consistency, documentation validation
  for 905 Markdown files, and diff check pass with the repository on the exact
  clean checkpoint before this ledger update.

## Follow-ups

- Run later ordinary unattended Conveyor-equivalent processes in Codex,
  Claude, Hermes, and OpenClaw, retaining prompt visibility and Store/native
  correlations separately from installation evidence.
- Exact host installation, authenticated dashboard proof, named gates, and
  final container teardown remain pending under AR-297.
- Tracker writes, push, PR, merge, tag, signing, publication, release, and
  hosted workflow dispatch remain prohibited.
