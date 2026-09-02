---
title: "Third-party notices"
status: active
category: governance
created: 2026-07-17
updated: 2026-09-02
tags:
  - licensing
  - provenance
  - roster
related:
  - LICENSE
  - docs/roster-audit/audit-manifest.json
  - agency_runtime/core/roster/data/LICENSE.agency-agents.txt
  - agency_runtime/core/roster/data/LICENSE.ecc.txt
  - docs/roadmap/issue-AR-364-audit-external-review-cards.md
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

## ECC review cards

Two review specialists (`silent-failure-hunter`, `type-design-analyzer`) are
derived from the ECC agent catalog and audited under AR-364.

- License: MIT
- Copyright: Copyright (c) 2026 Affaan Mustafa
- Reviewed source revision: `ca185ef5f7667078a1e70a763bd3a9c71c48acf0`
  (repository recorded under `sources.ecc` in the audit manifest)
- Local license copy: `agency_runtime/core/roster/data/LICENSE.ecc.txt`
- Local provenance and semantic-audit evidence:
  `docs/roster-audit/batch-ecc-review.json` and
  `docs/roster-audit/batch-ecc-review-review.md`, pinned in
  `docs/roster-audit/audit-manifest.json` under `sources.ecc`

Only the two audited files were taken from that repository; the packaged
manifest records the originating repository per specialist so provenance never
blurs between sources.

## Retired Windows helper

The unreleased Agency-owned Windows operator-presence helper was retired before
public distribution under AR-197. Its C++/WinRT and Microsoft STL source,
binary, provenance, and local notice copies are not part of the maintained
source or package. Faithful planning and Git history preserve the prior review
record without making those retired files current distribution inputs.
