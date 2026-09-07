---
title: "AR-164 exact retired-backend tree evidence"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [acceptance, evidence, git, executables]
related:
  - docs/roadmap/issue-AR-164-reject-repository-ancestor-path-poisoning.md
  - docs/roadmap/acceptance/issue-AR-164.md
  - docs/roadmap/acceptance/evidence/AR-164-executable-boundary-20260907.md
  - docs/decisions/0227-bind-executable-isolation-to-current-launch-surfaces.md
supersedes: []
superseded_by: null
---

# AR-164 exact retired-backend tree evidence

## Candidate tree snapshot

The first isolated criterion-5 check required actual candidate-state output,
not a narrative of deletion. Its absent verdict remains in 6ac3b1aa. The
following commands were run after clean preservation ledger
6c7ab0913b86220ef4eeec1a772e025b79bf13f0; both return zero.

```bash
git ls-tree 083ae8b58378d97c139cfb79debf0a49175b3f92:agency_runtime/core/delegation
```

Complete directory listing (Git object IDs, not claimed SHA-256 file hashes):

```text
100644 blob cd13882815195bb1300bd25d1252f0baf2cabcc3	__init__.py
100644 blob 448939d4ba00a29b964461229c9a4f5643c5c79b	backend_contracts.py
100644 blob be968d10b723a277b42aa39dba9a6447a4c8ced1	backend_process.py
100644 blob f8ec4ae22307adbf0314971f71fd437d5a1c5443	backend_process_compat.py
100644 blob c694c55ae61869932511c1407e7860c6290e4b79	backend_security.py
100644 blob 68f0959d1549b34f08e355166c15bed9bdd95b23	backends.py
100644 blob b949bf1b4809c36ff776b766aadbdea9e9d1401f	events.py
100644 blob b9067ca71d0a0cf1f0e1fd6674063bf7ac00c812	lifecycle.py
100644 blob c4f2952d73bb99a0c7d94f882ee50575f73b714b	lifecycle_graph.py
100644 blob c35de1df8a350658ef5b41eb4ccb8d6e18fa9521	lifecycle_types.py
100644 blob e5e7dfd8649f6a63b06ea3c784fe590ec9a20a3b	native_labels.py
```

None of backend_command.py, backend_hosts.py, ledger.py, lifecycle_dispatch.py
or lifecycle_orchestration.py is present in this complete candidate listing.
The surviving backends.py is the bounded-process compatibility facade, not a
replacement worker dispatcher.

```bash
git diff-tree --no-commit-id --name-status -r \
  fb34191f9380cdeab2895878e5a933c2cda35608 -- \
  agency_runtime/core/delegation/backend_command.py \
  agency_runtime/core/delegation/backend_hosts.py \
  agency_runtime/core/delegation/ledger.py \
  agency_runtime/core/delegation/lifecycle_dispatch.py \
  agency_runtime/core/delegation/lifecycle_orchestration.py
```

```text
D	agency_runtime/core/delegation/backend_command.py
D	agency_runtime/core/delegation/backend_hosts.py
D	agency_runtime/core/delegation/ledger.py
D	agency_runtime/core/delegation/lifecycle_dispatch.py
D	agency_runtime/core/delegation/lifecycle_orchestration.py
```

This is actual deletion-status output for the five retired modules, accompanied
by their continued absence in the reviewed candidate rather than only history.

## Unchanged implementation binding

```bash
git diff --exit-code 083ae8b5 -- agency_runtime tests scripts AGENTS.md pyproject.toml
git rev-parse 6c7ab091:agency_runtime
```

The comparison returns zero with empty output. The source tree object is:

```text
0ed31de7ec3b387ef463bd087a01eb4907de972c
```

It is the same agency_runtime tree object at 083ae8b5. This correction adds
documentation only, changes no requirement or implementation, and replaces only
criterion 5's retirement-evidence citation. A new candidate will bind the added
source; all seven checks receive new verdicts rather than carrying old ones.
