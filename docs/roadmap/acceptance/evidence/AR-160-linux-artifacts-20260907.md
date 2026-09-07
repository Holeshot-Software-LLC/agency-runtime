---
title: "AR-160 current Linux artifact and installed-contract receipt"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [evidence, packaging, linux, release, backlog]
related:
  - docs/roadmap/issue-AR-160-publish-platform-honest-native-release-artifacts.md
  - docs/decisions/0219-retire-removed-helper-release-obligations.md
  - docs/roadmap/acceptance/evidence/AR-156-verification-workflow-20260907.md
  - docs/roadmap/acceptance/evidence/AR-159-branch-protection-20260907.md
  - docs/RELEASE_CHECKLIST.md
  - scripts/build_distributions.py
  - scripts/verify_distribution.py
  - scripts/smoke_installed_distribution.py
supersedes: []
superseded_by: null
---

# AR-160: Current Linux artifact evidence

## Identity and scope

September 7, 2026, Linux x86-64 / Python 3.12.3. Clean reviewed candidate:
f1c7d0b06f23f6683b367c31ff913d5cf7369645, after PR #711 and its publication
ledger. All source/tests/workflow bytes remain those of b499e7fb; no packaging
code or policy change. Build uses canonical Git blobs, an absent output directory
and an owner-private parent outside the worktree. No old artifact is overwritten.

| Canonical artifact | SHA-256 |
|---|---|
| agency_runtime-0.1.0-py3-none-any.whl | ee057f8bfb2b0743398a74e2837fe252fdc563d20d387758932ae224e5bcae5b |
| agency_runtime-0.1.0.tar.gz | 2e84b43d5a3d22a7527d18fb1158f321ca6f66b3681bba5731ceba45c24da0ad |

## Focused contract verification

```bash
PYTHONPATH=. python -m pytest tests/test_release_contract.py \
  tests/test_build_distributions.py tests/test_distribution_verifier_hardening.py \
  tests/test_smoke_isolation.py -q -W error -k 'not native_windows'
```

**258 passed, one deselected, 35.56 seconds; no skips/failures.** The excluded
test is the actual Windows directory-attribute transition case. Linux-executable
synthetic platform/path/mode fixtures are not native Windows proof. Both profiles
set includes_native_executable=false; executable and structurally valid PE
payloads remain rejected, including renamed content. The full-set verifier test
uses synthetic fixtures and is not an actual Windows producer receipt.

## Canonical build and independent verification

At the exact clean candidate, the canonical builder emits the named portable
wheel and source distribution. The independent verifier passes with
`--expected-commit f1c7d0b06f23f6683b367c31ff913d5cf7369645 --artifact-set portable`;
strict Twine passes both artifacts. SHA-256 values above were read from the
published local pair. Use the release checklist's canonical builder command
with this expected commit and a new private destination to reproduce it.

No Windows wheel was built, renamed or retagged. The three-artifact release-set
gate is intentionally not claimed. A later documentation commit changes the
source archive; these hashes certify this candidate only, not a future main.

## Two fresh installed environments

Create two separate Python virtual environments outside the checkout. Install
the wheel into one and source distribution into the other, with isolated-mode
pip; both install agency-runtime 0.1.0 and PyYAML 6.0.3. The source install builds
its own portable wheel; its container bytes are not claimed identical to the
canonical wheel. Imports in both resolve to their own site-packages.

Run the following with each environment's Python, from outside the checkout,
using umask 077. AGENCY_REVIEWED_CHECKOUT denotes the absolute reviewed checkout
path; imports are isolated to the installed environment:

```bash
python -I "$AGENCY_REVIEWED_CHECKOUT/scripts/smoke_installed_distribution.py" \
  --expected-version 0.1.0 --artifact-set portable
python -I -c 'from agency_runtime.cli.entrypoint import main; raise SystemExit(main())' \
  smoke --all --json
python -I -m pip check
```

Both environments exit zero for every command:

- Packaged smoke: version 0.1.0; all ten assets; config and loopback dashboard
  health pass; MCP exposes eight tools and executes agency.status successfully.
- Roster: 265 approved, zero quarantined/retired, matching the manifest. Both
  offline selection cases return no specialists with inference unavailable,
  rather than inventing staffing success.
- Deterministic smoke: eight pass, zero fail/skip. SQLite, roster and five-case
  host parity pass; Claude, Codex, Hermes, OpenClaw and ZCode generated bundles
  pass. Codex lists all eight hooks; OpenClaw syntax passes; ZCode's generated
  process/config/toggle checks pass; Hermes exposes the native finalizer contract.
- CLI --help and --version each exit zero with empty stderr (3360 and 13 stdout
  bytes respectively). pip check reports no broken requirements.

The smoke helper uses private temporary state; it does not activate the owner's
normal sessions. Generated registration, loading fixtures and process invocation
are not a native attended host canary or quality staffing/hiring evaluation.

## Retained gaps and reuse

AR-160 remains in_progress with all five current criteria unchanged. Owner
Windows producer proof, identical two-producer source archives, shared payload parity,
assembled release-set verification, applicable live host evidence and publication
authority remain explicit. The July billing explanation is historical; AR-159's
fresh audit establishes no current hosted checks but not their cause.

AR-156's named spine (1085/three existing skips), UI (188/current floors) and
21 loaded-browser checks are reused for unchanged inputs, not rerun here.
No exhaustive corpus/matrix, manual workflow dispatch, native Windows or live
activation is claimed. Counts remain 40 open trackers plus 89 unfinished legacy
records. This receipt supports a retained record, not an isolated acceptance.
