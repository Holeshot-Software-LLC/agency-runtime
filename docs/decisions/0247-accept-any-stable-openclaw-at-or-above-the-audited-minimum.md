---
title: "Accept any stable OpenClaw at or above the audited minimum"
status: accepted
category: decisions
created: 2026-09-10
updated: 2026-09-10
tags: [openclaw, installer, hosts]
related:
  - docs/roadmap/issue-AR-435-install-into-the-openclaw-version-the-host-runs.md
  - docs/roadmap/issue-AR-267-accept-openclaw-numeric-package-revision.md
  - docs/decisions/0049-openclaw-final-only-full-payload-delivery.md
  - docs/TROUBLESHOOTING.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0247
type: decision
deciders: [owner]
---

# ADR-0247: Accept any stable OpenClaw at or above the audited minimum

## Status

**Accepted 2026-09-10.** Owner decision during the AR-433 reinstall: "it should
install into whatever openclaw version that's installed on the host machine."

## Context

The installer's OpenClaw gateway guard refused any version outside the exact
`2026.8` release line while its own error text promised "2026.8.2 or newer
(stable)". The line pin dated from the 2026-09-01 adoption of 2026.8.2, when
the post-install harness battery on that version was treated as the line's
hook-compatibility audit, and from AR-267's earlier `2026.7`-only contract.
On 2026-09-10 the host had moved to `OpenClaw 2026.9.3 (1391f7c)`; the guard
blocked before mutation, so openclaw alone kept the previous runtime while the
other four hosts were reinstalled.

## Decision

1. `openclaw_version_supported` accepts a parsed stable version when it is at
   or above `MINIMUM_OPENCLAW_VERSION` as a whole, with no release-line
   equality. The minimum stays `2026.8.2`.
2. The parser is unchanged: prereleases, alphanumeric suffixes, extra
   components and unknown strings are still refused; wholly numeric
   distribution revisions are still accepted (AR-267).
3. Hook compatibility on a newer line is evidenced by what already runs after
   every install: the post-install harness battery, native inventory and the
   runtime inspection step, plus the host's own fresh turns. A release-line
   pin is not part of that evidence.
4. The stopped-gateway consent rule and the fail-closed ordering of the guard
   are unchanged.

## Consequences

- An OpenClaw upgrade on the host no longer strands the openclaw plugin on an
  old runtime digest; the installer targets the version present.
- A hook contract change in a newer OpenClaw would surface as a failed battery
  or runtime inspection after install rather than as a refusal before it. That
  is the trade the owner chose; the refusal path remains for prereleases and
  versions below the minimum.
- The troubleshooting text no longer describes a `2026.7.x` pin.

## Alternatives

- **Raise the pin to `2026.9`.** Rejected: it recreates the same refusal at the
  next host upgrade and contradicts the "or newer" the installer states.
- **Requalify each line by hand before enabling it.** Rejected by the owner
  for this host; the post-install battery is the qualification.
