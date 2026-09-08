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
commit: 7de977936b7e21e39aa1c730a5a086c1432ad62f
short: 7de97793
date: 2026-09-08
pr: null
related_issues:
  - docs/roadmap/issue-AR-312-validate-explicit-production-config.md
---

# Worklog detail: Validate an explicit config without installed state

Runtime source is 7de97793; focused-fixture correction and exact passing evidence
are committed as ee17a65d. Each substantive commit has an immediate ledger.

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
The original clean source checkpoint recorded tests as unrun. The parent then
authorized the focused pair only under umask 077:

```text
python -m pytest tests/test_cli_config_validate.py tests/test_cli_parser_contract.py -q -W error
```

First exact result: 1 failed, 47 passed in 1.03s. Failing node:
tests/test_cli_config_validate.py::test_explicit_validation_and_install_load_the_same_file.
The expected file-relative Store path differed from the suite's isolated
AGENCY_DB_PATH deployment override. This was not a runtime validation failure;
the explicit CLI branch had returned document-valid without creating state.
The bounded correction removes that override only inside the comparison test.
Runtime source remains byte-identical to 7de97793.

Final raw summary: `48 passed in 0.65s`, exit 0. Targeted Ruff prints
`All checks passed!` and `4 files already formatted`; diff check is clean.
No named spine, CI, installed smoke, native/provider call or isolated acceptance
review is claimed here. Tracker #758 was separately authorized and mapped.

## Follow-ups

Parent coordinates the owner-requested clean stop, serialized tracker filing,
normal PR publication, focused verification, installation and live evaluation.
AR-312 remains in_progress until its unchanged acceptance gates have evidence.

Integration `525029dd` preserves all wrap-up source slices and independent capsule/ledger records. Root source review confirms explicit absolute identity, bounded read, strict schema and no Store/provider or permission-repair dependency; no scoped correctness finding. Original 48-pass focused receipt stays exact.
