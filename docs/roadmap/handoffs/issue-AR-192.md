---
title: "AR-192 current-policy hook-trust handoff"
status: active
category: roadmap
created: 2026-09-08
updated: 2026-09-08
tags: [handoff, codex, hooks, trust, recovery]
related:
  - docs/roadmap/issue-AR-192-fail-fast-on-codex-hook-trust-drift.md
  - docs/roadmap/acceptance/evidence/AR-192-hook-trust-reconciliation-20260908.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-192
branch: codex/ar192-hook-trust-reconciliation
evidence_commit: d39ec14dc0d79094cb8398d807da2554263a5c3f
minimum_ledger_commit: f0e388633f9fa22d7d81e8a40e7265d3e5262d18
hard_checkpoint_percent: 50
tracker_url: null
---

# AR-192 current-policy hook-trust handoff

## Checkpoint

Branch starts at clean f0e38863 after retained AR-190 publication. This package
reconciles an implemented trust preflight with current ADR-0173 modes. It does
not change runtime authority. Parent serializes publication after AR-191 and
owns all installed/native operations. No acceptance run has started.

## Completed evidence

At exact f0e38863, all product/script/test/packaging paths equal installed
candidate 4db6be16. The portable receipt contains exact source hashes.
Fresh focused trust, activation and canary tests pass 180 cases in 11.34 seconds;
six files pass Ruff lint/format. Stale trust prevents the model-runner call.
The prior real installed read-only probe found 8/8 enabled trusted hooks in
0.569 seconds; its selected-field projection is explicitly not full raw stdout.

Original criteria 1/2/6 remain verbatim in the receipt. Current criteria scope
the preflight to attended current-profile exact activation and require fresh
supported owner approval only when the settled definitions are not already
trusted. Explicit managed/autonomous modes are not relabeled as attended.
AR-191's obsolete grants are not restored; AR-255 owns native-child proof.

## Exact blocker

After exact 4db6be16 reinstall, the 00:30:44 UTC read-only native inspection
found 8 enabled, 8 modified and zero trusted hooks in 0.542472 seconds. Real
installed verification at 00:30:45–49 exited 1 in 3.488429 seconds with
`codex_hook_trust_not_ready` and `model_invocation_attempted=false`. Complete
sanitized stdout, hashes and capture receipts are portable in this repository.
This proves the live refusal path, not activation. Criterion 6 requires
supported native owner approval, then 8/8 trust and a successful no-bypass
canary. No acceptance run is justified for known absent proof; retain open.

## Same-task continuity

Continue in this exclusive branch. No user interruption is needed while
independent source/record work remains. Parent owns owner-profile changes,
native models and serial PR publication; preserve other workers' commits.

## Next bounded work package

1. Preserve the retained checkpoint through normal PR publication. No native
   approval, bypass, unchanged canary retry or acceptance call in this package.
2. After supported owner approval is available, inspect the exact settled
   definitions and run one attended no-bypass canary on the bound install.
3. Only after all six criteria have concrete evidence, freeze a pending builder
   and request isolated judgments. Stop current work at 01:00 UTC.

## Verification

Focused command: `python -m pytest tests/test_codex_hook_trust.py
tests/test_codex_activation_verification.py tests/test_codex_activation_canary.py
tests/test_host_canary.py -q -W error`: 180 passed in 11.34 seconds.
Ruff: six files clean/formatted. Reused exact-source named-spine evidence is
1085 passed/three skips in 69.50 seconds at combined f670e6b5; only the unrelated
AR-189 test was added afterward. Documentation gates remain to be run after
the complete evidence slice. No native Windows or exhaustive corpus executed.

## Constraints

No private trust writes, bypass substitution, owner install or new model call
by this worker. No new approval claim. Trusted inventory is admission, not
activation; a successful canary does not establish every host or child-only
delivery. At most two independent review passes; no fabricated verdicts.
