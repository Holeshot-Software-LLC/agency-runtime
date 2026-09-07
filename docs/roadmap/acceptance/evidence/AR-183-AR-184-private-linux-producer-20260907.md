---
title: "AR-183/AR-184 detached private-mode Linux producer evidence"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [evidence, release, packaging, linux, reproducibility]
related:
  - docs/roadmap/issue-AR-183-normalize-private-posix-wheel-modes.md
  - docs/roadmap/issue-AR-184-normalize-private-posix-sdist-modes.md
  - docs/decisions/0074-build-byte-deterministic-release-artifacts.md
  - docs/RELEASE_CHECKLIST.md
  - scripts/build_distributions.py
  - scripts/verify_distribution.py
  - tests/test_canonicalize_distributions.py
supersedes: []
superseded_by: null
---

# Detached private-mode Linux producer evidence

## Scope and immutable source

Observed September 7, 2026, approximately 23:05–23:10 UTC. This is a real Linux canonical
build from clean **detached** source commit
`08fab1c4fb9b7f8ed167f0aa4366182960f6eada`, under `umask 077`. It supplies the
same Linux-producer evidence to AR-183 and AR-184. It does not supply either
issue's Windows/Linux equality or merged-release-set evidence, nor issue an
acceptance verdict. No product source changed for this check.

The producer source is a separate detached worktree, not the evidence-writing
branch. Before and after production, `git rev-parse HEAD` returned the exact
SHA above, `git symbolic-ref -q HEAD` exited 1 with empty output, and
`git status --porcelain` was empty. The output directory was initially absent
under a new owner-private temporary parent outside the checkout. Both parent
and published output directory are mode `0700`.

Environment: Linux 7.0.0-29-generic, x86_64, glibc 2.39; Python 3.12.3;
`build` 1.5.0, `twine` 6.2.0. The source's isolated backend requirements remain
exact `setuptools==83.0.0` and `wheel==0.47.0`; the invoking environment has
those same versions. The earlier AR-407 artifact at
`ef6523b3779e7673051c1b758174d42ef64961d4` was a branch build, not this detached
source proof, and is not substituted for it.

## Commands and observed results

Paths below are portable parameter names: `AR183_SOURCE_TREE` is the fresh
detached worktree, `AR183_DIST_DIR` is the initially absent destination outside
it, and `AR183_PYTHON` is the trusted development interpreter. No owner home,
profile, installation, credential, provider or native host is changed.

```bash
git worktree add --detach "$AR183_SOURCE_TREE" 08fab1c4fb9b7f8ed167f0aa4366182960f6eada
cd "$AR183_SOURCE_TREE"
umask 077
umask
"$AR183_PYTHON" --version
env PYTHONPATH=. "$AR183_PYTHON" -m scripts.build_distributions "$AR183_DIST_DIR" --create-private-parent --expected-commit 08fab1c4fb9b7f8ed167f0aa4366182960f6eada
"$AR183_PYTHON" -m twine check --strict "$AR183_DIST_DIR/agency_runtime-0.1.0-py3-none-any.whl" "$AR183_DIST_DIR/agency_runtime-0.1.0.tar.gz"
env PYTHONPATH=. "$AR183_PYTHON" -m scripts.verify_distribution "$AR183_DIST_DIR" --expected-commit 08fab1c4fb9b7f8ed167f0aa4366182960f6eada --artifact-set portable
```

Producer stdout, exit 0:

```text
0077
Python 3.12.3
Canonical distribution build passed: agency_runtime-0.1.0-py3-none-any.whl, agency_runtime-0.1.0.tar.gz
```

Strict Twine stdout, exit 0; only the private destination path is replaced
with the portable parameter name:

```text
Checking
$AR183_DIST_DIR/agency_runtime-0.1.0-py3-none-any.whl: PASSED
Checking $AR183_DIST_DIR/agency_runtime-0.1.0.tar.gz: PASSED
```

Independent verifier stdout, exit 0:

```text
Distribution verification passed (artifact contents match release policy).
```

The host-default verifier also exited 0 before the explicit `portable` run.
These are direct builder/Twine/verifier executions, not mocked return values
or a unit-test-only producer. The exact clean-source and expected-commit
checks, production canonicalizer, and independent verifier were unpatched.

## Artifact identities and canonical modes

Read-only inspection at 23:07:30 UTC found exactly these two artifacts:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `agency_runtime-0.1.0-py3-none-any.whl` | 10,031,596 | `228ab9c0eac70764ce515fbd6ce2829437a7f78d081f702d790175c1033ac650` |
| `agency_runtime-0.1.0.tar.gz` | 30,497,093 | `2b0887ed60ab80caf71b6ad13efa27525f4d9e4aff845d74db8200989bf68d4d` |

Both published artifact files have filesystem mode `0644` inside the private
`0700` directory. The wheel has 619 ordinary regular members at `0644` and
one governed `agency_runtime-0.1.0.dist-info/RECORD` regular member at `0664`.
The sdist has 2,291 ordinary regular files at `0644` and 40 directories at
`0755`, with no other member types or modes. This census is of **canonical
outputs**; it is not presented as a retained pre-normalization archive census.

## Focused regressions

The evidence-writing branch was still clean at the same exact source SHA
when this four-module package ran:

```bash
env PYTHONPATH=. "$AR183_PYTHON" -m pytest tests/test_canonicalize_distributions.py tests/test_build_distributions.py tests/test_distribution_verifier_hardening.py tests/test_release_packaging.py -q -W error --tb=short
```

Final stdout line, exit 0:

```text
498 passed, 1 skipped in 40.38s
```

The skipped case is
`tests/test_build_distributions.py::test_native_windows_directory_volatile_attribute_transition`,
whose platform guard requires native Windows file attributes. Synthetic
Windows-format rejection and deterministic-container cases ran on Linux;
none is claimed as a native Windows producer. Relevant coverage includes:

- `test_wheel_normalization_accepts_owner_private_posix_source_modes` and
  `test_owner_private_and_public_posix_source_modes_converge_exactly`;
- `test_windows_private_source_mode_remains_rejected`,
  `test_unreviewed_record_modes_remain_rejected`, and the unreviewed POSIX
  wheel source-mode rejection matrix;
- `test_private_posix_sdist_modes_converge_with_public_modes` and
  `test_sdist_source_mode_allowlists_are_exact_across_all_permission_bits`.

## Remaining boundary

No native Windows producer, Windows/Linux sdist hash comparison or merged
three-file `release` artifact-set verification ran. Those remain explicit
unproven criteria and are reserved for the owner's Windows machine. A future
cross-platform comparison must use this same exact source SHA, or rebuild
both platforms at one newly frozen SHA; comparing different source commits
would not prove deterministic output. No exhaustive corpus, coverage shards,
six-interpreter matrix, installation, inference, signing, upload or release
publication was performed.
