---
title: "Third-party notices"
status: active
category: governance
created: 2026-07-17
updated: 2026-07-17
tags:
  - licensing
  - provenance
  - roster
related:
  - LICENSE
  - docs/roster-audit/audit-manifest.json
  - agency_runtime/core/roster/data/LICENSE.agency-agents.txt
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
