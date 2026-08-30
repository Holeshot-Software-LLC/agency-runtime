---
title: "Pair portable and win_amd64 wheels for native delivery"
status: accepted
category: decisions
created: 2026-07-27
updated: 2026-07-27
tags: [release, packaging, windows, portability, wheels]
related:
  - docs/roadmap/issue-AR-107-build-release-artifacts-from-canonical-git-blobs.md
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
  - docs/roadmap/issue-AR-160-publish-platform-honest-native-release-artifacts.md
  - docs/roadmap/issue-AR-161-sign-and-license-windows-operator-presence-delivery.md
  - docs/roadmap/issue-AR-169-exclude-native-pe-from-portable-wheel.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/decisions/0074-build-byte-deterministic-release-artifacts.md
  - docs/decisions/0099-separate-reproducible-unsigned-builds-from-signed-delivery.md
  - docs/RELEASE_CHECKLIST.md
  - docs/THREAT_MODEL.md
supersedes: []
superseded_by: null
id: ADR-0098
type: decision
deciders: [maintainers]
---

# ADR-0098: Pair portable and win_amd64 wheels for native delivery

## Context

Agency Runtime's Python code is portable, but the first positive operator-
presence slice invokes a packaged Windows x86-64 PE executable. The release
contract before this decision put that executable in a `py3-none-any` wheel.
PyPA defines the platform tag as an installer compatibility claim, defines
`any` as any platform, and explicitly recognizes a native subprocess executable
as a reason a distribution can be platform specific.

Changing the only wheel to `win_amd64` would make the native claim honest but
would unnecessarily withdraw the portable routing, diagnostics, and read-only
surfaces from Linux and other environments. Keeping one universal wheel with a
dormant PE would continue to make a false compatibility claim and waste package
budget on unsupported systems.

## Decision

Publish two built distributions for each release version:

- a portable `agency_runtime-<version>-py3-none-any.whl` retaining native source,
  provenance, and notices but containing no Windows PE executable; and
- a `agency_runtime-<version>-py3-none-win_amd64.whl` containing the same
  shared runtime/audit payload plus the exact approved Windows x64 executable.

Both wheels use the same project name, version, Python compatibility,
dependencies, entry points, and portable package behavior. Their allowed delta
is finite: native payload files plus required WHEEL and RECORD differences.
The Windows wheel remains Python-ABI-independent (`none`) because the helper is
a subprocess rather than an imported extension. The portable wheel uses
`Root-Is-Purelib: true`; the Windows wheel uses `Root-Is-Purelib: false` and
installs through the platform-library root. Those fields are installation
placement, not publisher-trust evidence.

Each Linux/portable or Windows x64 producer builds and verifies one host-derived
wheel plus one source distribution. The merge gate requires the producer source
distributions to be byte-identical, requires exact equality for every shared
wheel payload, assembles the two wheels plus one source distribution, and
independently verifies that three-artifact set. It never compares the two wheel
containers as if their profile-specific bytes should be identical. A build from
the source distribution uses the same host-derived profile and fails if it can
produce a `py3-none-any` wheel containing the Windows executable.

The platform wheel is only a compatibility decision. ADR-0099 and AR-161 still
govern signed delivery, publisher identity, local notices, and legal approval.

Official packaging evidence:

- <https://packaging.python.org/en/latest/specifications/platform-compatibility-tags/>
- <https://packaging.python.org/en/latest/specifications/binary-distribution-format/>

## Consequences

- Linux and other portable consumers retain routing, diagnostics, and read-only
  behavior without receiving an unusable Windows executable.
- Supported Windows x64 installers can prefer the more specific platform wheel
  while retaining the portable wheel as an explicit fail-closed baseline.
- Release construction, artifact parity, upload atomicity, source-distribution
  behavior, and independent verification become multi-artifact contracts.
- A same-version install can expose different native capability by platform;
  status and diagnostics must report payload absence as unavailable, not as a
  failed or silently downgraded verification.
- Platform honesty does not establish Authenticode trust, legal redistribution
  rights, or an attended Windows Hello canary.

## Alternatives

- **Keep the PE in `py3-none-any`.** Rejected because `any` is a compatibility
  claim, not permission to ship dormant incompatible executable code.
- **Publish only `win_amd64`.** Rejected because the portable runtime remains
  useful and supported without the positive native mutation path.
- **Create a separately named companion distribution.** Rejected for the first
  release because it adds dependency-resolution and version-skew authority that
  one same-version paired release set avoids.
- **Download the helper on first use.** Rejected because it adds a credential,
  network, substitution, and rollback boundary to a local security control.
