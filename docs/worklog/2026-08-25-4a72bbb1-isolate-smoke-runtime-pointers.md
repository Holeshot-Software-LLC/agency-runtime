---
title: "Worklog detail: Isolate smoke runtime pointers"
status: active
category: worklog
created: 2026-08-25
updated: 2026-08-25
tags: [smoke, install, isolation, runtime-pointers]
related:
  - docs/roadmap/issue-AR-291-isolate-smoke-runtime-pointers.md
  - docs/roadmap/issue-AR-290-end-to-end-guided-setup.md
  - docs/roadmap/handoffs/issue-AR-290.md
  - agency_runtime/core/installer_orchestration.py
  - tests/test_installer_orchestration.py
  - tests/test_smoke_isolation.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 4a72bbb1f23b225005191b360c9cc8ff5d5e07cb
short: 4a72bbb1
date: 2026-08-25
pr: null
related_issues:
  - docs/roadmap/issue-AR-291-isolate-smoke-runtime-pointers.md
  - docs/roadmap/issue-AR-290-end-to-end-guided-setup.md
---

# Worklog detail: Isolate smoke runtime pointers

## Purpose

Prevent deterministic generated-host smoke from claiming its temporary
installation as an operator's current runtime. The leak made a later guided
setup report foreign-package drift for absent Hermes and OpenClaw hosts even
though the real Codex, Claude, ZCode, and dashboard mutations had succeeded.

## Approach

Keep ordinary default-owner-home installation unchanged, but suppress the
advisory runtime-pointer publication whenever the generic installer receives
an explicit alternate home. Add a direct helper contract for both branches and
exercise the real generated Hermes smoke installation while observing that it
makes no pointer publication call.

## Challenges encountered

The defect was visible only after source smoke and an installed setup ran in
sequence: generated bundle files were correctly temporary, while the separate
product-private pointer documents were not. Review therefore traced both the
temporary-home boundary and the independent pointer publication path. Cleanup
is intentionally deferred until the fixed commit is installed and the two
documents' exact host and source-root identities are revalidated.

## Decisions and alternatives

Runtime pointers describe the active default-owner installation, not every
possible target home. Redirecting them into each alternate home would create a
second pointer namespace that no host consumes; deleting all pointers after
smoke would risk removing legitimate Codex, Claude, or ZCode evidence. The
repair instead prevents the invalid write and limits cleanup to the two known
contaminated absent-host documents.

## Verification

- Installer orchestration, smoke isolation, smoke coverage, native installer,
  and doctor coverage passed all 194 tests with warnings as errors.
- The generated Hermes path in the isolation regression exercised the real
  adapter install and observed zero runtime-pointer publications.
- Full Ruff lint and format checks passed across 693 files.
- Metadata, policy availability, worklog, and documentation checks passed for
  813 Markdown files; `git diff --check` passed.

## Follow-ups

Install this exact repair, identity-check and remove only the contaminated
Hermes/OpenClaw pointer documents, then repeat installed deterministic smoke
and guided setup. Tracker creation remains pending separate authorization.
