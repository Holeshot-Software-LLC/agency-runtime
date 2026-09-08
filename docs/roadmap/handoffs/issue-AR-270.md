---
title: "AR-270 OpenClaw installed-copy provenance recovery capsule"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [handoff, openclaw, uninstall, provenance]
related:
  - docs/roadmap/issue-AR-270-bind-openclaw-installed-copy-provenance.md
  - docs/roadmap/acceptance/evidence/AR-270-openclaw-copy-provenance-20260907.md
  - docs/decisions/0108-retire-only-owned-host-integrations.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-270
branch: codex/ar270-openclaw-installed-copy-provenance
evidence_commit: fc699ff392f75c345064077b039d8fc15615dcf2
minimum_ledger_commit: 1e1f1c56f12856d27236f0939ff9765729393444
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/749
---

# AR-270 OpenClaw installed-copy provenance recovery capsule

## Checkpoint

Branch-only candidate; metadata identifies reviewed source and its integrated
ledger, not an accepted or installed changed build. Worktree:
`/tmp/agency-runtime-ar270-openclaw-installed-copy-provenance`.
Phase: focused_review complete, runtime verification deferred. Source ownership
is installer_uninstall.py and focused test_host_uninstall.py additions, plus
this issue's records.

## Completed evidence

The old direct-path equality rejects the historical installed-copy receipt.
Current read-only OpenClaw 2026.8.2 inspect confirms separate plugin/install
objects, rootDir, copied entry source and exact managed source path.
Candidate joins only an exact single-plugin envelope and validates the complete
closed provenance. Optional exposed versions bind to owned manifest version.
Forty-five regression cases are written, not run. Ruff and diff checks pass.
First independent review identified one High false-absence extraction gap;
candidate now detects every Agency identity and refuses conflicting aliases
before treating inventory as absent or substituting an inspect record.
Separately authorized tracker #749 is open under epic:install.
Final narrow source-only recheck found the High resolved with no additional
scoped findings. Both independent passes are preserved; neither ran tests.
Normal merge a9073fe6 integrated published main cb9e9a50, preserving source bytes.

## Exact blocker

Test execution, isolated acceptance and live delivery are not complete.
No completion claim.

## Same-task continuity

Owner instructed code-first with no new unit, CI, live or model evaluations.
Read-only native inspect was separately authorized and performed without runtime
loading; no uninstall/disable or owner profile mutation. At 14.8% remaining
telemetry, checkpoint this bounded candidate and continue the same task.

## Next bounded work package

Publish the reviewed candidate in_progress through a normal pull request.
Keep unrun regression and acceptance gates explicit until owner reopens testing.

## Verification

Static commands and unexecuted regression names are retained in the evidence
receipt. Do not relabel static checks as passing behavior tests.

## Constraints

No native uninstall, disable, restart, profile mutation, permission change or
provider call. Preserve the owned-tree, install-ID, bundle-digest, plan hashing,
operator-presence, lock, gateway and keep-files boundaries. No broad path alias
acceptance and no weakening of partial/conflicting receipt refusal.
