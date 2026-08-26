---
title: "AR-291: Isolate smoke runtime pointers"
status: done
category: roadmap
created: 2026-08-25
updated: 2026-08-26
tags: [smoke, install, isolation, runtime-pointers, reliability]
related:
  - docs/roadmap/issue-AR-290-end-to-end-guided-setup.md
  - agency_runtime/core/smoke.py
  - agency_runtime/core/installer_orchestration.py
  - agency_runtime/core/runtime_staleness.py
  - tests/test_smoke_isolation.py
  - tests/test_installer_orchestration.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-291
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/329
depends_on: []
blocks: [AR-290]
---

# AR-291: Isolate smoke runtime pointers

## Problem

`agency smoke --all` installs generated host bundles under an alternate
temporary `home_dir`, but generic installation still publishes each exercised
host's advisory runtime pointer under the real operator
`~/.agency-runtime/launchers`. The generated bundle files are isolated while
the current-host projection metadata is not.

The AR-290 installed dogfood run proved the impact. Source smoke wrote Hermes
and OpenClaw pointer documents naming the development worktree even though both
hosts are absent on this machine. A later real `agency setup --all` correctly
registered Codex, Claude, and ZCode, yet its all-host residual drift audit found
the contaminated absent-host pointers and returned exit 1 after successful
mutations.

## Current state

- The runtime pointer is advisory; host hooks never use it to choose executable
  code.
- Generic installation publishes the pointer before staging the host bundle.
- Smoke passes an explicit temporary `home_dir` to every generated-host
  install but does not redirect the product-private launcher root.
- The exact contaminated Hermes/OpenClaw pointer files are identified and can
  be removed after the repair is installed. Codex, Claude, and ZCode pointers
  already name the installed uv package and must be preserved.
- Tracker issue [#329](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/329)
  is linked and closed to match this completed record.

## Approach

Publish a generic install's advisory runtime pointer only for the default owner
home (`home_dir is None`). An explicit alternate home remains fully capable of
staging and validating a generated integration, but it cannot claim to be the
current operator installation. Keep ordinary default-home installs unchanged.

Add a focused helper contract proving default-home publication and alternate-
home suppression, then extend the real smoke-isolation regression to prove a
Hermes bundle exercise makes no pointer publication call. Remove only the two
source-smoke pointer documents after verifying their exact host and source-root
identity, reinstall the repaired package, rerun installed smoke, and repeat
guided setup/doctor.

## Dependencies

- AR-290's installed setup dogfood is the observed failure and acceptance path.
- Runtime pointers remain advisory under the existing staleness contract.
- Cleanup must not remove Codex, Claude, or ZCode pointers or any host bundle.

## Acceptance

- [x] An alternate-home generic install does not publish an operator runtime
      pointer; a default-home install still does.
- [x] `agency smoke --all` leaves pre-existing operator pointer documents
      byte-identical and creates no absent-host pointer.
- [x] Focused smoke/installer tests and the relevant fast-spine tests pass with
      warnings as errors; Ruff, docs, and diff gates pass.
- [x] Only the contaminated Hermes/OpenClaw pointer documents are removed after
      exact identity verification.
- [x] The repaired installed `agency setup --non-interactive --all` no longer
      reports foreign-package residual drift; ordinary native-trust warnings
      remain truthful.
- [x] Tracker issue #329 is linked and closed to match canonical done status.

## Verification evidence

The alternate/default-home publication contract and the real generated-Hermes
smoke path have failing-before regression coverage. The focused smoke,
installer orchestration, native installer, and doctor group passed all 194
tests with warnings as errors. Full Ruff lint and format, metadata, policy,
worklog, 814-file documentation, and diff checks passed before the checkpoint.

The clean repaired tree was installed and its setup, pointer-isolation, native
Jina reranker, and dashboard files hash-matched source. After exact host and
source-root validation, only `current-hermes.json` and
`current-openclaw.json` were removed; the Codex, Claude, and ZCode pointers
remained byte-identical. Installed deterministic smoke passed 8/8 checks and
recreated neither absent-host pointer. Repeated setup reported no residual
runtime drift. Its remaining hard exit was separately isolated as AR-292's
setup return-code classification bug, not an AR-291 failure.
