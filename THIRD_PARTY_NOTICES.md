---
title: "Third-party notices"
status: active
category: governance
created: 2026-07-17
updated: 2026-07-27
tags:
  - licensing
  - provenance
  - roster
related:
  - LICENSE
  - docs/roster-audit/audit-manifest.json
  - agency_runtime/core/roster/data/LICENSE.agency-agents.txt
  - agency_runtime/native/windows/operator_presence/LICENSE.cppwinrt.txt
  - agency_runtime/native/windows/operator_presence/LICENSE.microsoft-stl.txt
  - agency_runtime/native/windows/operator_presence/NOTICE.microsoft-stl.txt
  - docs/roadmap/issue-AR-161-sign-and-license-windows-operator-presence-delivery.md
  - docs/decisions/0099-separate-reproducible-unsigned-builds-from-signed-delivery.md
supersedes: []
superseded_by: null
---

# Third-party notices

## Upstream specialist roster

Agency Runtime includes governed specialist contracts derived from the Agency
Agents catalog maintained by AgentLand Contributors.

- License: MIT
- Copyright: Copyright (c) 2025 AgentLand Contributors
- Reviewed source revision: `459dce837db3bdfdc4763d3fefd1fd854e73c8f1`
- Local license copy:
  `agency_runtime/core/roster/data/LICENSE.agency-agents.txt`
- Local provenance and semantic-audit evidence:
  `docs/roster-audit/audit-manifest.json`

The installed runtime is self-contained. It does not read from or depend on an
external checkout during routing. Executable specialist context is generated
from the reviewed, bounded contracts; source paths and hashes are retained only
as provenance.

## Windows operator-presence helper

The reviewed Windows x64 helper is compiled from repository source using
C++/WinRT headers and Microsoft C++ Standard Library/runtime components. The
following local files reproduce the official upstream license and notice text
with repository LF line-ending normalization:

### C++/WinRT

- License: MIT
- Copyright: Copyright (c) Microsoft Corporation
- Official upstream repository: `microsoft/cppwinrt`
- Official source revision:
  `76ab8890c1cce78a9c68d3a99a5eb8129be9a3f0`
- Official source path at that revision: `LICENSE`
- Local license copy:
  `agency_runtime/native/windows/operator_presence/LICENSE.cppwinrt.txt`
- Local SHA-256:
  `c2cfccb812fe482101a8f04597dfc5a9991a6b2748266c47ac91b6a5aae15383`

### Microsoft C++ Standard Library

- License: Apache-2.0 WITH LLVM-exception
- Copyright: Copyright (c) Microsoft Corporation
- Official upstream repository: `microsoft/STL`
- Official license source revision:
  `219514876ea86491de191ceaa88632616bbc0f19`
- Official license source path at that revision: `LICENSE.txt`
- Official notice source revision:
  `ee74822eae8830e440b1480526145b24c19ffbe4`
- Official notice source path at that revision: `NOTICE.txt`
- Local license copy:
  `agency_runtime/native/windows/operator_presence/LICENSE.microsoft-stl.txt`
- Local notice copy:
  `agency_runtime/native/windows/operator_presence/NOTICE.microsoft-stl.txt`
- Local license SHA-256:
  `7c68a47568bd633f7a71ee5e2038660a2cc62ce8a5405999e2b69fab3f37469c`
- Local notice SHA-256:
  `4b8b8c5386b37247443a0591df1ae8deeb9be3cfe4a10e1c2e65d1486dac81cd`

These records establish source provenance and preserve upstream text. They do
not establish that the exact MSVC edition/operator, Windows SDK, `/MT` static
CRT/runtime, signed artifact, or intended distribution channel is legally
cleared for delivery. AR-161 remains blocked until the owner and an authorized
legal reviewer record that exact entitlement and notice disposition.
