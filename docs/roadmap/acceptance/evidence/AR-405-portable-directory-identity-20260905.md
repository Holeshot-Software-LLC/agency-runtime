---
title: "AR-405 portable directory-identity evidence"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [acceptance, testing, portability, release]
related:
  - docs/roadmap/issue-AR-405-make-directory-identity-regressions-portable.md
  - docs/roadmap/acceptance/issue-AR-405.md
  - docs/decisions/0074-build-byte-deterministic-release-artifacts.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
---

# AR-405 portable directory-identity evidence

## Reproduction and focused result

Linux/Python 3.12, isolated dev/release environment with the repository's
setuptools 83.0.0 and wheel 0.47.0 build-system pins installed. Starting source
is main 3ed51069a3a4d95022b9e92dbfb868deac74c678. The only executable-source
change in this package is tests/test_build_distributions.py; production
scripts/build_distributions.py and the runtime package remain unchanged.

Command before and after the test correction:

```text
python -m pytest tests/test_build_distributions.py -q -W error
before: 2 failed, 91 passed in 8.04s
after: 100 passed, 1 skipped in 5.25s
```

Both original failures require Windows attributes on a real Linux directory:
the fresh-directory volatile 0x10000000 bit and FILE_ATTRIBUTE_DIRECTORY.
Neither failure establishes a production identity defect. The after-run keeps
portable real filesystem assertions active: child creation/removal preserves
identity, a different directory and same-path replacement fail, and a regular
file replacing the directory is refused. Synthetic tests use only a local
module dependency replacement, not a process-wide os.lstat patch.

## Windows scope and retained history

No native Windows execution is available or claimed in this package. The one
Linux skip is test_native_windows_directory_volatile_attribute_transition;
it is Windows-only and also names an unsupported filesystem premise explicitly.
The portable tests and synthetic volatile-bit contract are not skipped.

Historical commit 71833c5c67218ee84edbed9291470f31105d0e05 records a measured
Windows transition in both the temporary and private runtime directories,
and its then-current 92 passing tests. That faithful Git record and the
production mask it introduced are retained; they are historical observations,
not current Windows validation. The native test retains the original
clear-after-first-child and stays-clear-after-removal observation when the
fresh-directory bit is actually present. Synthetic coverage cannot certify
a Windows build or paired artifact parity. AR-160 still owns current release
artifact proof; this test-only repair does not waive it.

## Delivery boundary

Named fast Python production spine: 1004 passed, three skipped in 63.23s.
Dashboard UI: 138 passed. The same seven-file focused command that previously
had two failures now returns 452 passed, three skipped in 11.68s. Its files are
test_installer_registration, test_native_installer, test_host_uninstall,
test_platform_wheel, test_build_distributions, test_canonicalize_distributions
and test_harness_battery. Ruff check and format (764 files) pass; routing gates
pass within the deterministic recall-only scope, not live staffing quality.

The observable outcome is a passing Linux build-test file without weakened
portable integrity assertions. The failing baseline, passing fixed run and
test diff supply that bounded local demo. No real host uninstall, gateway
stop/restart, artifact publication, exhaustive workflow or native Windows run
was performed. Existing runtime installation is unaffected by a test-only fix.

## Post-candidate verification checkpoint

Candidate 593f074f supplied all three satisfied isolated Codex acceptance
verdicts. PR #678 carries the test repair. The first decision-conformance command
inherited shell umask 0002 and failed the baseline setup in
ensure_private_directory with an untrusted creation boundary below the copied
test workspace. No mutation ran and source_unchanged was true. This is not a
directory-identity regression or a successful conformance result. The existing
AR-297 record documents protected umask 077 execution; a rerun with that scoped
process setting is in progress. Existing filesystem permissions and trust
policy were not modified. The protected rerun completed successfully: baseline
passed in 99.433 seconds, 182/182 mutations killed, zero survived/invalid,
source_unchanged=true. The ambient failure above remains retained. The
candidate's evidence sections above are frozen
and remain separate from this later checkpoint.
