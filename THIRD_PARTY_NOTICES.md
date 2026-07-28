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

## Retired Windows helper

The unreleased Agency-owned Windows operator-presence helper was retired before
public distribution under AR-197. Its C++/WinRT and Microsoft STL source,
binary, provenance, and local notice copies are not part of the maintained
source or package. Faithful planning and Git history preserve the prior review
record without making those retired files current distribution inputs.
