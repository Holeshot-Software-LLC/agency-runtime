---
title: "Separate reproducible unsigned builds from signed delivery"
status: accepted
category: decisions
created: 2026-07-27
updated: 2026-07-27
tags: [release, security, windows, signing, reproducibility, supply-chain]
related:
  - SECURITY.md
  - THIRD_PARTY_NOTICES.md
  - docs/THREAT_MODEL.md
  - docs/RELEASE_CHECKLIST.md
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
  - docs/roadmap/issue-AR-160-publish-platform-honest-native-release-artifacts.md
  - docs/roadmap/issue-AR-161-sign-and-license-windows-operator-presence-delivery.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/decisions/0074-build-byte-deterministic-release-artifacts.md
  - docs/decisions/0098-pair-portable-and-win-amd64-wheels.md
supersedes: []
superseded_by: null
id: ADR-0099
type: decision
deciders: [maintainers]
---

# ADR-0099: Separate reproducible unsigned builds from signed delivery

## Context

The native Windows operator-presence helper is built deterministically and its
source and PE bytes are hard-pinned. That gives reviewers a reproducible object
to compare with canonical source. It does not establish who published the
object. Authenticode adds publisher identity and tamper evidence meaningful to
Windows and enterprise application-control policy, but embedding a signature
and timestamp changes the PE bytes and normally cannot reproduce the original
unsigned digest.

Collapsing both properties into one hash would force one of two false claims:
that unsigned reproducibility establishes publisher trust, or that a signed
timestamped file is byte-identical to the deterministic unsigned build.

## Decision

Maintain two explicit artifacts and one recorded mapping:

1. The **unsigned review artifact** is built deterministically from canonical
   source under the pinned toolchain and flags. Independent verification records
   its source, toolchain, size, and SHA-256 identity. It is review evidence and
   is never the production delivery payload.
2. The **signed delivery artifact** is produced only by submitting that exact
   reviewed digest to an organization-controlled Authenticode boundary. Its
   SHA-256 identity, approved certificate subject and immutable identity, chain,
   SHA-256 signing algorithm, RFC 3161 timestamp, signing service/policy, and
   release are recorded separately.
3. One bounded provenance record maps the signed delivery identity back to the
   exact unsigned review identity. Both independent artifact verification and
   the release checklist reject a missing or ambiguous mapping.

Signing credentials stay outside the repository, packages, logs, and ordinary
CI workers. The release gate independently verifies the signed artifact with
the Windows default authentication policy and the exact approved publisher
constraint. A signature is supply-chain evidence only; it neither proves that a
human approved the current roster rollback nor weakens ADR-0096's same-call
native presence and transactional revalidation requirements.

The source license provenance and redistribution entitlement decision are
separate prerequisites to signing. C++/WinRT MIT and Microsoft STL
Apache-2.0 WITH LLVM-exception/NOTICE texts are retained locally from immutable
official sources. An owner-authorized legal review must still resolve the exact
MSVC, Windows SDK, `/MT` static runtime, and final distribution terms before
delivery. This decision records no legal clearance and no existing signature.

Official signing evidence:

- <https://learn.microsoft.com/en-us/windows/win32/seccrypto/signtool>
- <https://learn.microsoft.com/en-us/windows/security/application-security/application-control/app-control-for-business/deployment/use-code-signing-for-better-control-and-protection>

## Consequences

- Reviewers can reproduce and inspect the unsigned helper without access to a
  private key or timestamp service.
- Operators and enterprise policy can identify the approved publisher on the
  delivery bytes rather than trusting a repository hash alone.
- The unsigned and signed digests intentionally differ; provenance and release
  verification must retain both rather than overwrite one with the other.
- A signed release wheel can remain deterministic after its exact signed helper
  is fixed as an input, but re-signing is not claimed to reproduce the same PE
  bytes.
- Release automation needs a protected signing boundary, independent signature
  verification, revocation/timestamp policy, and key-rotation handling.
- The release remains blocked until the owner and authorized legal reviewer
  approve publisher identity and redistribution terms.

## Alternatives

- **Ship only the reproducible unsigned helper.** Rejected because a digest does
  not supply publisher identity or an enterprise signing trust path.
- **Commit a private signing key or general CI secret.** Rejected because it
  turns repository or runner compromise into durable publisher compromise.
- **Sign first and call the result reproducible.** Rejected because signatures
  and timestamps change bytes and depend on protected external state.
- **Treat the signature as operator presence.** Rejected because signing proves
  publisher and integrity properties, not current human intent for a mutation.
