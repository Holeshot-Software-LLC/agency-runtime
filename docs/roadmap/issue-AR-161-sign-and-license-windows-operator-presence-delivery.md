---
title: "AR-161: Sign and license Windows operator-presence delivery"
status: blocked
category: roadmap
created: 2026-07-27
updated: 2026-07-27
tags: [release, security, windows, signing, licensing, supply-chain]
related:
  - SECURITY.md
  - THIRD_PARTY_NOTICES.md
  - docs/THREAT_MODEL.md
  - docs/RELEASE_CHECKLIST.md
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
  - docs/roadmap/issue-AR-160-publish-platform-honest-native-release-artifacts.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/decisions/0098-pair-portable-and-win-amd64-wheels.md
  - docs/decisions/0099-separate-reproducible-unsigned-builds-from-signed-delivery.md
  - agency_runtime/native/windows/operator_presence/LICENSE.cppwinrt.txt
  - agency_runtime/native/windows/operator_presence/LICENSE.microsoft-stl.txt
  - agency_runtime/native/windows/operator_presence/NOTICE.microsoft-stl.txt
supersedes: []
superseded_by: null
type: issue
epic: release
issue_id: AR-161
priority: p0
tracker_url: null
depends_on: [AR-160]
blocks: [AR-143]
---

# AR-161: Sign and license Windows operator-presence delivery

## Problem

The reviewed Windows operator-presence helper is reproducible and byte-pinned,
but it is unsigned. A digest proves that the runtime received the reviewed
bytes; it does not associate those bytes with the organization, satisfy an
enterprise publisher policy, or give Windows a trusted Authenticode identity.
Signing changes the PE bytes, so treating the reproducible unsigned digest as
the delivery digest would also make the release provenance false.

The helper is built with C++/WinRT headers, Microsoft STL, MSVC 19.44, Windows
SDK 10.0.26100.0, and `/MT` static runtime linkage. Official upstream sources
identify C++/WinRT as MIT and Microsoft STL as Apache-2.0 WITH LLVM-exception
and publish an STL NOTICE. Those source notices do not by themselves prove the
organization's Visual Studio, Windows SDK, static CRT, or other redistributable
entitlement for this exact delivery.

## Current state

The repository pins the unsigned source and executable identities and records
the compiler, SDK, flags, and target in provenance. Exact local copies of the
official C++/WinRT license and Microsoft STL license/NOTICE are now retained
beside the native source for release packaging. No organization-approved
publisher identity, code-signing certificate, timestamp service, signed helper,
signature receipt, or legal entitlement decision is recorded.

AR-161 is therefore blocked. Its tracker creation remains pending authorization,
and implementation cannot proceed autonomously because publisher identity,
signing-key custody, and legal approval belong to the owner/organization.

## Approach

Implement ADR-0099 as a two-stage trust chain. First, build and independently
verify the deterministic unsigned review artifact from the exact canonical
source and toolchain, recording its digest and provenance. Only then submit
that exact artifact to an organization-controlled signing boundary. Record the
signed digest, certificate subject and immutable identity, chain, RFC 3161
timestamp evidence, signing policy, and exact mapping back to the reviewed
unsigned digest. Never place a private signing key or reusable credential in
the repository or ordinary build artifacts.

Require an independent Authenticode verification gate using the Windows default
authentication policy and the organization-approved publisher identity. Treat
missing signatures, warnings, wrong publishers, untrusted chains, invalid or
absent timestamps, altered signed bytes, and unsigned-to-signed mapping gaps as
release failures. Package only the signed delivery helper in the Windows wheel;
retain the unsigned artifact solely as review/reproducibility evidence.

Have the owner or authorized counsel review the exact Visual Studio edition and
subscription used, build-operator entitlement, Windows SDK terms and redist
list, `/MT` static CRT/runtime content, C++/WinRT and STL notice obligations,
and every final wheel/source artifact. Record a bounded decision and required
notices without interpreting this repository's technical evidence as legal
advice.

## Dependencies

AR-160 supplies the platform-honest `win_amd64` delivery boundary. The owner
must authorize the legal publisher name, certificate or managed signing
service, key-custody policy, timestamp service, and final distribution channel.
An authorized legal reviewer must resolve the MSVC/Windows SDK/static-runtime
redistribution and notice obligations for the exact toolchain and artifact.

## Acceptance

- [x] Exact upstream C++/WinRT MIT and Microsoft STL Apache-2.0 WITH
  LLVM-exception license/NOTICE texts are retained locally with immutable
  official-source provenance.
- [ ] The owner records the legal publisher identity and authorizes the signing
  certificate or managed signing service, key custody, timestamp service, and
  distribution channel.
- [ ] Authorized legal review records the exact Visual Studio/MSVC, Windows SDK,
  `/MT` static CRT/runtime, C++/WinRT, STL, and final-artifact redistribution and
  notice disposition. Repository maintainers do not self-approve this gate.
- [ ] One deterministic unsigned helper is independently rebuilt, verified, and
  recorded as the review artifact before any signing operation.
- [ ] The signing boundary accepts only that exact unsigned digest, protects all
  private key material outside ordinary CI, uses an approved SHA-256/RFC 3161
  policy, and emits a separately identified signed helper.
- [ ] Release provenance binds the signed digest, certificate identity and
  chain, trusted timestamp, signing policy, and exact unsigned review digest.
- [ ] Independent Windows verification rejects missing, warning-bearing,
  untrusted, expired-at-signing, revoked, wrong-publisher, wrong-policy,
  untimestamped, or altered signatures and fails closed when online revocation
  status required by policy is unavailable.
- [ ] The `win_amd64` wheel contains only the approved signed helper and all
  required local notices; portable wheels contain neither signed nor unsigned
  Windows executable payloads.
- [ ] Signed-wheel install and runtime diagnostics expose bounded publisher and
  helper provenance without treating a signature as operator presence.
- [ ] A fresh attended Windows 11 x64 Windows Hello success-and-denial canary
  passes from the exact signed release candidate before AR-143 can close.
