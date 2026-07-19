---
title: "AR-68: Require trusted config and policy namespaces"
status: done
category: roadmap
created: 2026-07-16
updated: 2026-07-16
tags: [security, configuration, routing, policy, filesystem, testing]
related:
  - docs/decisions/0006-config-first-redacted-configuration.md
  - docs/decisions/0021-full-companion-policy-with-precedence.md
  - docs/roadmap/issue-AR-49-key-policy-cache-by-path-identity.md
  - docs/roadmap/issue-AR-50-fail-closed-runtime-environment-overrides.md
  - docs/THREAT_MODEL.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: security
issue_id: AR-68
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/69
depends_on: []
blocks: [AR-92]
---

# AR-68: Require trusted config and policy namespaces

## Problem

Canonical `load_config()` and custom companion-policy loading bounded and
identity-checked their final files but did not verify ancestor ownership and
mutation rights. An explicit or environment-selected path below a
cross-account-writable parent could therefore steer providers, storage,
capture, policy, and delegation. Restricted-host scratch also lacked a safe
path for creating missing nested configuration parents through its capability.

## Current state

CLI and dashboard configuration writers already shared a strong namespace
predicate. Canonical config and custom policy reads now apply it before cache
use and after content reads. Missing descendants below a live host-attested
capability are validated prospectively and created component-by-component with
private ACLs.

## Approach

Apply one trusted-namespace contract to explicit, environment-selected, and
bundled configuration inputs. Require real parent chains, root/current-user
ownership on POSIX, no cross-account mutation or final default ACL, and the
existing Windows DACL proof. Revalidate the file identity across bounded reads
and use the private-path capability when creating missing scratch descendants.

## Dependencies

ADR-0006 makes configuration runtime truth and ADR-0021 makes policy routing
truth. This item prevents either truth source from being selected through an
untrusted filesystem namespace.

## Acceptance

- [x] Canonical `load_config()` rejects explicit and environment paths under unsafe parents.
- [x] Custom and bundled policy paths require the same trusted namespace.
- [x] Safe root-owned and current-user namespaces remain portable.
- [x] Restricted host capability paths create missing private config descendants safely.
- [x] Link, default-ACL, Windows-DACL, and read-time swap cases fail closed.
- [x] Config, routing, host, full-suite, exact-coverage, and installed smoke gates pass.
