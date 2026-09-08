---
title: "AR-312 explicit configuration document validation"
status: active
category: worklog
created: 2026-09-08
updated: 2026-09-08
tags: [configuration, cli, installation]
related:
  - docs/roadmap/issue-AR-312-validate-explicit-production-config.md
  - docs/roadmap/handoffs/issue-AR-312.md
  - docs/decisions/0006-config-first-redacted-configuration.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
supersedes: []
superseded_by: null
type: worklog
commit: null
short: null
date: 2026-09-08
pr: null
related_issues:
  - docs/roadmap/issue-AR-312-validate-explicit-production-config.md
---

# Worklog detail: Validate an explicit config without installed state

## Purpose

Make the README's fresh-container configuration preflight operate on the exact
file the following install consumes, before a Store or host integration exists.

## Approach

Add optional --config ABSOLUTE_PATH to config validate. With it, require one
existing link-safe identity and trusted parent namespace, read at most 1 MiB,
parse bounded UTF-8 YAML, and reuse the canonical persisted-document schema.
Without it, retain the current load_config plus doctor contract and exit codes.
Success output explicitly withholds installed-health claims. No provider, host,
Store, installed-config discovery, defaults or deployment overrides participate
in explicit document validation.

## Challenges encountered

The config-state reader repairs permissions on read and accepts missing files;
the runtime loader also accepts missing files as defaults. Neither is suitable
for an explicit write-free document check. The implementation reuses their
underlying non-mutating identity, namespace, bounded-read and schema contracts.

## Decisions and alternatives

No new policy: ADR-0006 owns strict config identity and schema; ADR-0173 owns
exact production-install binding. Do not replace doctor with structural checks,
promise usable credentials, or weaken installation's full readiness gate.
Empty partial documents remain schema-valid as before; null/nonmapping roots
remain invalid. Historical acceptance wording is preserved.

## Verification

Targeted Ruff lint passes; formatter applied two mechanical changes. Parser
golden regenerated mechanically to
7326a90eb99bf336caaa3412054c92210f5e50e58ed9e4869981ba41e0a86657
without executing any test function. Written focused coverage includes exact
file binding, missing/relative/linked/special/oversized inputs, invalid YAML,
secret-name validation and value-free errors, unchanged file bytes/modes,
absent Store, ignored ambient override and preserved bare doctor behavior.
Tests, CI, native/provider calls and acceptance are not run at this checkpoint.

## Follow-ups

Parent coordinates the owner-requested clean stop, serialized tracker filing,
normal PR publication, focused verification, installation and live evaluation.
AR-312 remains in_progress until its unchanged acceptance gates have evidence.
