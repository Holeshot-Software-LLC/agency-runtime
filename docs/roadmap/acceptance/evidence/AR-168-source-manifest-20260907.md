---
title: "AR-168 current source-manifest verification"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [evidence, packaging, reproducibility, backlog]
related:
  - docs/roadmap/issue-AR-168-rebuild-canonical-sdist-source-manifest.md
  - docs/roadmap/issue-AR-160-publish-platform-honest-native-release-artifacts.md
  - docs/roadmap/acceptance/evidence/AR-166-dashboard-authority-20260907.md
  - docs/decisions/0219-retire-removed-helper-release-obligations.md
  - scripts/canonicalize_distributions.py
  - scripts/verify_distribution.py
supersedes: []
superseded_by: null
---

# AR-168: Linux manifest evidence, Windows comparison retained

## Identity and current implementation

September 7, 2026, Linux x86-64 / Python 3.12.3. Clean candidate
6363a788132b8419c69f26a1dd802534e57782cd includes PR #717 and its merge ledger.
No runtime/test/script/workflow change: Git comparison of those four trees
against AR-166's 4a24477669e1b773b27626f2cd67631fbe78f875 exits zero.

The canonicalizer's _canonical_sdist_sources_payload derives membership from
validated actual files, excludes only root PKG-INFO/setup.cfg, sorts by
parent/name and joins with UTF-8 LF without a final newline. It never trusts
backend manifest rows. The verifier independently derives exact membership and
bytes and rejects malformed/duplicate paths, order, CRLF and missing members.
The removed native-helper licenses explain the historical trigger, not a reason
to delete generic normalization or restore helper payloads.

## Focused tests

```bash
PYTHONPATH=. python -m pytest tests/test_canonicalize_distributions.py \
  tests/test_distribution_verifier_hardening.py tests/test_build_distributions.py \
  -q -W error -k 'not native_windows'
```

**308 passed, one deselected, 33.83 seconds; no skips/failures.** The exclusion
is the actual Windows directory-attribute transition test, not a hidden Linux
failure. Included synthetic CRLF/Windows-shaped archives are portable fixtures.
The direct manifest regression supplies duplicated, missing and extra backend
rows and verifies the exact reconstructed self/member payload.

## Clean canonical build

Run the canonical builder with --expected-commit set to the full candidate above
and an absent dist directory under a newly created owner-private temporary
parent. No artifact is overwritten. Independently run verify_distribution.py
with that candidate and --artifact-set portable; run python -m twine check
--strict on both named outputs. All three commands exit zero.

| Artifact | SHA-256 |
|---|---|
| agency_runtime-0.1.0-py3-none-any.whl | 1e4115925b64195bc464195bcfee25b7a3a797a69e67f82b19d61fd4f47190da |
| agency_runtime-0.1.0.tar.gz | 1bb4dabce3c3fc4f10602cca63342b73a5e8a02d219428ccc9aa7e6fa2c90748 |

Direct readback of the resulting source archive finds 2,258 regular files,
2,256 manifest rows and 2,256 distinct rows. Root PKG-INFO/setup.cfg are absent
from the manifest, its own row is present, and neither CR nor trailing LF occurs.
Manifest SHA-256 is
4543ae3e266c51973d33e03103b504d82fe3d983537d7780cec6b9750566f759.
The independent verifier checks the full archive contract, not only these counts.
Hashes certify this clean candidate, not later documentation commits or main.

## Disposition and limits

Retain in_progress, with all five original criteria/states unchanged. No new
isolated acceptance run is warranted while actual Windows comparison is absent.
Native Windows remains owner work; pair both producers at one exact candidate
and compare complete source bytes before satisfying criterion 4 and AR-160.
No Windows producer, assembled release set, installed smoke or attended host
canary is claimed by this receipt. AR-160's earlier installed evidence is
separate; it is not silently relabeled as this artifact.

AR-166's same-byte named spine (1085/three existing skips, 66.99s) and the
earlier curated decision receipt are explicit reuse. Fresh UI passes 190 with
zero failures/skips, 201.580005 ms; fresh routing evaluation passes its
deterministic-candidate-recall-only contract, not live staffing. Metadata/policy/worklog,
strict docs/tracker, Ruff and diff checks run for these records. No exhaustive
corpus, matrix, workflow dispatch, acceptance rewrite or profile redesign.
Counts stay 40 mapped plus 84 legacy, 124 unfinished.
