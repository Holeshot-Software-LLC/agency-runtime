---
title: "AR-312 explicit configuration document validation handoff"
status: active
category: roadmap
created: 2026-09-08
updated: 2026-09-08
tags: [handoff, configuration, installation]
related:
  - docs/roadmap/issue-AR-312-validate-explicit-production-config.md
  - docs/decisions/0006-config-first-redacted-configuration.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - docs/worklog/2026-09-08-ar312-explicit-config-validation.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-312
branch: codex/ar312-explicit-config-validation
evidence_commit: f4264b54f68ebad6efc13df58b948642d81fe2ae
minimum_ledger_commit: 1048a12072b315ed09fcc7edb88c977df8a3004c
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/758
---

# AR-312 explicit configuration document validation handoff

## Checkpoint

Exclusive branch starts at clean ledger 1048a120. The metadata commits identify
the inherited clean floor, not this source slice's test result. The worklog
records the new source commit in its immediately following ledger. The owner
requested a clean stopping point before main installation and live evaluation.

## Completed evidence

Source tracing confirmed the parser lacked an explicit config flag and the
handler always ran doctor against ambient installed state. The new explicit
absolute-file branch uses bounded strict document validation with no defaults,
permission repair, Store, host or provider probe. Bare behavior remains intact.
README and parser goldens agree. Targeted Ruff and diff checks pass; focused
regressions are written, not yet executed.

## Exact blocker

Coordinated focused execution, installed evidence and isolated acceptance remain
pending. Authorized tracker #758 is filed; parent serializes publication. No done verdict.

## Same-task continuity

Preserve other workers' changes. Parent owns main integration, owner installation
and live evaluation. This worker finishes only the bounded source/records pair.

## Next bounded work package

Parent reviews the clean source checkpoint and runs coordinated wrap-up
verification. Validate a private exact file before
installation; do not infer installed health from structural success.

## Verification

Targeted Ruff lint/format and mechanical parser-golden regeneration only.
No test functions, CI, native/provider invocation or acceptance review executed.
When coordinated, focus on tests/test_cli_config_validate.py and
tests/test_cli_parser_contract.py before installed verification.

## Constraints

No missing-file fallback, ambient profile mutation, chmod, Store construction,
provider discovery, credentials in output, host installation, trust bypass, or
new schema/policy. Original acceptance criteria remain unchanged and unchecked.
