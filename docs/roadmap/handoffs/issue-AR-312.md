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
evidence_commit: 7de977936b7e21e39aa1c730a5a086c1432ad62f
minimum_ledger_commit: a9f2fc954d376a00fe05985d52defe30e6d9e383
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/758
---

# AR-312 explicit configuration document validation handoff

## Checkpoint

Exclusive branch starts at clean ledger 1048a120. Runtime source 7de97793 and
immediate ledger a9f2fc95 are frozen. One subsequent test-only fixture correction
does not alter runtime source. The owner requested a clean stopping point before
main installation and live evaluation; parent owns those operations.

## Completed evidence

Source tracing confirmed the parser lacked an explicit config flag and the
handler always ran doctor against ambient installed state. The new explicit
absolute-file branch uses bounded strict document validation with no defaults,
permission repair, Store, host or provider probe. Bare behavior remains intact.
README and parser goldens agree. Targeted Ruff and diff checks pass. The first
focused run reports 1 failed/47 passed because the test compared file-relative
Store paths while the suite supplied a deployment override. Removing only that
test-local override yields 48 passed in 0.65s. No runtime code changed.

## Exact blocker

Installed evidence and isolated acceptance remain pending. Authorized tracker
#758 is filed; parent serializes publication. No done verdict.

## Same-task continuity

Preserve other workers' changes. Parent owns main integration, owner installation
and live evaluation. This worker finishes only the bounded source/records pair.

## Next bounded work package

Parent reviews the clean source checkpoint and runs coordinated wrap-up
verification. Validate a private exact file before
installation; do not infer installed health from structural success.

## Verification

Targeted Ruff lint/format/diff pass. Under umask 077, the parent-authorized
tests/test_cli_config_validate.py and tests/test_cli_parser_contract.py pair passes
48 tests in 0.65s with -q -W error. The prior fixture failure is retained in the
canonical issue/worklog. No CI, native/provider invocation or acceptance review.

## Constraints

No missing-file fallback, ambient profile mutation, chmod, Store construction,
provider discovery, credentials in output, host installation, trust bypass, or
new schema/policy. Original acceptance criteria remain unchanged and unchecked.
