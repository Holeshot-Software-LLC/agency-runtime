---
title: "Build byte-deterministic release artifacts from canonical Git blobs"
status: accepted
category: decisions
created: 2026-07-20
updated: 2026-07-20
tags: [release, packaging, reproducibility, git, archives, portability]
related:
  - docs/roadmap/issue-AR-107-build-release-artifacts-from-canonical-git-blobs.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - scripts/build_distributions.py
  - scripts/canonicalize_distributions.py
  - scripts/prove_autocrlf_checkout.py
  - scripts/release_contract.py
  - scripts/release_git.py
  - scripts/verify_distribution.py
  - docs/RELEASE_CHECKLIST.md
  - docs/THREAT_MODEL.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0074
type: decision
deciders: [maintainers]
---

# ADR-0074: Build byte-deterministic release artifacts from canonical Git blobs

## Context

A clean Git status compares filtered content and does not prove that physical
working-tree bytes equal the reviewed blobs. On Windows, line-ending filters can
therefore feed CRLF bytes to a build backend even when the reviewed commit stores
LF. A backend also emits platform-dependent ZIP, gzip, tar, ownership, mode, and
timestamp metadata.

Normalizing those headers with the host's ZIP and gzip compressors is
insufficient for byte reproducibility. Different supported Python or zlib
implementations may emit different valid DEFLATE streams for the same payload,
and a verifier that accepts every valid stream cannot establish one canonical
artifact identity.

## Decision

Require a full reviewed commit that exactly matches a clean live `HEAD` before
and after construction. Read a bounded allowlist of regular, non-executable
release inputs from a hostile-config-free, identity-frozen Git session.
Independently rehash every materialized blob and reject links, special files,
path aliases, unsafe names, transformed bytes, mutable identities, or budget
violations before invoking the build backend.

Keep the shared portable-path, source-scope, archive-limit, canonical ZIP
policy, and checkout assertions over an injected frozen Git transport in the
small `scripts/release_contract.py` module. Builders and canonicalizers must
not import the independent distribution verifier, and the contract must not
import the Git transport, builder, writer, or verifier.

Treat the backend output as bounded source material, not as the release
container. Accept only a finite reviewed Windows/Linux source-header policy and
preserve every payload byte. Emit the canonical wheel with an owned ZIP32 writer
using contiguous stored members, explicit local and central headers, and no
extras, comments, descriptors, ZIP64, prefixes, gaps, or trailing bytes. Emit
the canonical source distribution with one fixed gzip header, deterministic
RFC 1951 stored-block segmentation, exact CRC32 and ISIZE, and canonical
PAX-tar headers, ownership, modes, times, padding, and end marker. Do not use
host-zlib output for canonical artifacts.

Verify the published pair independently. The verifier binds artifact and parent
directory identities, parses physical ZIP, gzip, and tar layouts itself before
high-level archive access, enforces the same declarative format policy without
calling the writer, compares generated metadata and shared payloads, and
requires every committed release byte to match the reviewed Git blob. Commit
fixed golden fixture digests and run them across every supported Python and
Windows/Linux CI cell.

Publish the complete wheel/source pair by one no-clobber directory rename only
after both artifacts pass pre-publication bounds and the Git and filesystem
identities remain unchanged.

## Consequences

- Clean-checkout line-ending filters cannot change a release payload.
- Canonical archive bytes do not depend on platform ZIP defaults or zlib
  heuristics.
- Stored members make artifacts larger than ordinary compressed output, but the
  result remains bounded, simple to verify, and reproducible.
- Build-backend upgrades may change generated payloads only when the independent
  verifier and reviewed golden contract accept the change.
- The builder and verifier require more explicit archive code and adversarial
  tests than a direct `python -m build` workflow.
- A release operator gets an all-or-nothing, no-overwrite pair rather than a
  partially updated `dist` directory.

## Alternatives

- **Build from a clean working tree.** Rejected because filtered cleanliness
  does not prove the physical bytes consumed by the backend.
- **Normalize line endings before building.** Rejected because that invents
  source bytes instead of using the reviewed Git blobs.
- **Use host `zipfile` and `gzip` compression with fixed timestamps.** Rejected
  because a valid DEFLATE bitstream is not an API-stable cross-version byte
  contract.
- **Pin one compressor environment.** Rejected because local Windows/Linux
  release operators would still need that environment and the artifact contract
  would depend on an opaque compressor implementation.
- **Weaken the verifier to semantic payload equality.** Rejected because the
  release claims one reviewed physical artifact pair, not an equivalence class
  of structurally different containers.
