---
title: "AR-196 active recovery capsule"
status: active
category: roadmap
created: 2026-07-28
updated: 2026-07-28
tags: [handoff, dashboard, windows, state-machine, security, recovery]
related:
  - docs/decisions/0110-remove-agency-owned-windows-hello.md
  - docs/roadmap/issue-AR-197-remove-agency-owned-windows-hello.md
  - docs/roadmap/issue-AR-196-authorize-prepared-dashboard-service-repair.md
  - docs/decisions/0096-require-operator-presence-for-persistent-controls.md
  - docs/decisions/0109-prepare-dashboard-service-repair-before-operator-presence.md
  - docs/roadmap/issue-AR-194-inspect-owned-service-runtimes-across-python-versions.md
  - docs/worklog/2026-07-28-42da990-separate-codex-activation-child-goal.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-196
branch: main
evidence_commit: 42da9907c3d2389f6f8856c09f199da1da272d6a
minimum_ledger_commit: 850777897eee818545fd3d2569df8da850d6de03
hard_checkpoint_percent: 50
tracker_url: null
---

# AR-196 active recovery capsule

Bounded recovery projection for the dashboard-service production blocker. The
[canonical issue](../issue-AR-196-authorize-prepared-dashboard-service-repair.md)
owns acceptance and the governing decisions own authority semantics.

## checkpoint

- ADR-0111 supersedes the dashboard opt-in choice: bare `agency install` now
  means full applicable suite and `--no-dashboard` is the opt-out.
- AR-197 implementation removes the Agency-owned Windows Hello helper and keeps
  roster rollback and owned host uninstall unavailable. Harness install uses
  native harness lifecycle and dashboard failure is isolated from host work.
- `main`, local `HEAD`, and `origin/main` are exact commit
  `850777897eee818545fd3d2569df8da850d6de03`.
- Substantive AR-195 commit `42da990` separates the Codex activation parent
  probe from the direct child work-unit goal; ledger commit `8507778` records it.
- Agency is installed from exact revision `8507778`. The attended Codex refresh
  timed out at native presence and failed before commit, so the existing plugin
  remains activation-required and no live canary was rerun.
- The abandoned AR-196 implementation was fully removed. The only workspace
  residue is the owner-untracked analysis draft and `uv.lock`, both untouched.

## completed-evidence

- The original operator-presence error is genuine and safe: the generic
  dashboard-service family has no action-specific verifier, so it dispatches no
  persistent change.
- A temporary exact-installed dashboard returned HTTP 200 in 157 ms with CSP,
  `nosniff`, and referrer-policy headers. The UI contract suite passed all 109
  tests in 335 ms. Browser-control attachment failed in both Codex Browser and
  Chrome, so no visual or click-through claim is made.
- The temporary foreground dashboard was stopped and port 7810 was proven
  closed. Startup invoked the existing configured retention-maintenance path;
  it may have pruned rows older than the configured retention period. No row
  count was captured, so do not claim zero Store change.
- Independent red-team review rejected the draft before commit. It found that
  service activation also publishes owner and Codex-broker credential
  descriptors, may initialize or migrate the Store, starts retention pruning,
  and can leave a fresh or repaired worker alive while rollback reports success.
- The draft native prompt omitted exact account, task, path, runtime, manifest,
  Store, and credential consequences required by ADR-0096. Its raw configuration
  SHA could be a stable secret-dependent digest. Runtime-cache fallback and
  cleanup also lacked a safe consumer/ownership proof.

## exact-blocker

Dashboard installation is a multi-resource activation transaction, not a
single scheduled-task write. There is no commit boundary between a
write-restricted bootstrap worker and the ordinary worker that publishes
credentials and maintains Store data. Consequently, Windows Hello cannot yet
authorize the exact operation, and rollback cannot prove that the prior state
was restored. The current documented install/repair remains intentionally
fail-closed.

The attempted repair proved the dashboard service is an independent component
transaction, not authority for harness work. ADR-0111 keeps it in the default
suite while requiring its failure to remain isolated from host registration.
`--no-dashboard` explicitly excludes it when a host-only repair is wanted.

## same-task-continuity

This capsule replaces the unsafe implementation attempt with one bounded
architecture package. It does not authorize another exhaustive audit loop,
hosted workflow, tracker mutation, live Windows prompt, or service mutation.

## next-bounded-work-package

1. Finish AR-197 and AR-198 focused verification, write-free default-install
   dry run, and local substantive/ledger checkpoints.
2. Complete the already-pushed AR-195 path with one Codex-native refresh/trust
   and one activation canary; use `--no-dashboard` to keep that proof scoped.
3. Only if dashboard service installation still fails, specify a small Python
   state machine with states `prepared`, `presence_verified`,
   `bootstrap_started`, `bootstrap_proven`, `committed`, `rolled_back`, and
   `recovery_incomplete`. XState is a useful design reference, not a reason to
   add a JavaScript runtime.
4. Give that future bootstrap worker a Store-write-free, broker-free mode and a
   one-time coordinator commit handshake. Independently review its failure
   matrix before rebuilding the native helper or running another service canary.

## verification

~~~text
python -m pytest tests/test_native_installer.py tests/test_cli_parser_contract.py tests/test_cli_owner_authority.py -q -W error
ruff check agency_runtime tests scripts
ruff format --check agency_runtime tests scripts
python scripts/docs_metadata.py --check
python scripts/update_policy_availability.py --check
python scripts/update_worklog.py --check
python scripts/verify_docs.py
node --test tests/dashboard_ui.test.mjs
git diff --check
~~~

Do not run the exhaustive workflow, coverage shards, or compatibility matrix
for this package unless the owner explicitly asks.

## constraints

- Preserve generic fail-closed behavior until the complete transaction exists.
- Do not export, persist, simulate, or make model-callable a Windows presence
  result. Do not expose plaintext secrets or stable secret-dependent digests.
- Do not claim rollback success while a candidate process, runtime descriptor,
  broker credential, task, or manifest remains unproven.
- `dashboard service open` must be read-only; no implicit repair.
- Preserve the owner-untracked analysis draft and `uv.lock`.
- No tracker write, hosted workflow, package publication, signing, release, or
  exhaustive test without explicit authorization.
