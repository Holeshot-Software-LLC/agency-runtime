---
title: "AR-358: Installers leave their trust chains trusted; doctor offers the fix"
status: in_progress
category: roadmap
created: 2026-09-01
updated: 2026-09-02
tags: [installer, doctor, trust-chain, operations]
related:
  - docs/roadmap/issue-AR-337-run-harness-battery-on-version-change.md
supersedes: []
superseded_by: null
type: issue
epic: install
issue_id: AR-358
priority: p2
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/428
depends_on: []
blocks: []
---

# AR-358: Installers leave their trust chains trusted; doctor offers the fix

## Problem

The storage/executable trust rules (final parent dir mode 700, no
group-writable ancestors, no group/other-writable executables) are
enforced at read time but never established at write time, so every
external writer breaks them and an operator rediscovers the chmod
dance by forensics. Measured three separate times during the
2026-09-01 deploy alone: the Claude Code auto-updater left the
`~/.npm-global/@anthropic-ai` tree group-writable (canary
`group_writable: 14/16`), `npm install -g openclaw` left
`openclaw.mjs` group-writable (probe: "executable artifact permits
group or other writes"), and `claude plugin update` recreated
non-700 cache directories (`wiring unavailable — the host wiring file
is not trusted`). Session memory records each rediscovery costing
15-60 minutes.

## Current state

The fixes are operator lore (umask 077 + `chmod -R g-w` +
`find … -type d -exec chmod 700`), living in session memory and
handoff capsules instead of the product.

## Approach

Two layers: (1) every Agency installer/updater step normalizes the
permissions of exactly the trees it writes or depends on before the
trust probe runs (it knows the chains — marketplaces, plugin caches,
launcher trees, and the host executable chains it probes); (2)
`agency doctor` gains a `--fix-perms` (or equivalent consented) mode
that applies the same normalization to the known chains instead of
only diagnosing, with a dry-run listing. Never touch paths outside
the known chains.

## Dependencies

- None.

## Implementation (2026-09-02)

- `agency_runtime/core/trust_chain_repair.py` (new) owns a fixed per-host
  chain registry -- Claude's plugin cache and npm package tree, OpenClaw's
  npm package tree, Agency's runtime home and marketplaces -- resolved from
  the host-root and executable identities the installer already used, never
  from caller-supplied paths. `scan_trust_chains` is content-free (path
  classes, break kinds, counts). `repair_trust_chains` applies only the
  minimal mode change the trust rule needs, only with explicit consent, only
  on entries the current account owns, and never through a symbolic link:
  the chmod goes through a descriptor opened `O_NOFOLLOW` and matched to the
  lstat snapshot's identity, kind, and owner before `fchmod`.
- Installers normalize before probing: `_normalize_host_trust_chains` runs
  ahead of the OpenClaw plugin install and the Claude marketplace step, and
  a failure afterwards is explained with the untrusted chain instead of the
  host's opaque text. An injected command runner against the ambient home
  observes and never chmods, so the embedding boundary is unchanged.
  `install_agent_adapter` now passes the executable it already resolved, so
  the registry never consults PATH on its own.
- `agency doctor` lists every break with the repair command (the dry run),
  and `agency doctor --fix-perms` is the operator's consent to apply it.
- OpenClaw 2026.8 withholds a changed bundle's hooks until capabilities are
  accepted, which is why the 2026-09-01 deploy saw install and enable both
  succeed while the plugin stayed disabled-in-config. Registration probes the
  host version once and adds `--accept-capabilities` only for versions that
  require it.

Found while working here: `test_openclaw_install_guard_allows_only_proven_stopped_gateway`
asserted that a 2026.7.1 host is *allowed* to install, which went stale when
`2a5d52cd` adopted the 2026.8 line the day before. It was failing on main. The
fixture now pins `MINIMUM_OPENCLAW_VERSION` and asserts the refusal for the
older line as well.

## Acceptance

- [x] A fresh `agency install`/`--agent` run on trees freshly broken by
      npm or the claude auto-updater passes its own trust probes
      without manual chmod. Evidence: `_normalize_host_trust_chains` in
      `agency_runtime/core/installer_registration.py` runs before the
      install/marketplace probe, and
      `tests/test_trust_chain_repair.py::test_the_claude_npm_self_update_break_is_found_and_repaired`
      shows a freshly broken tree scanning clean after repair.
- [x] `agency doctor` can list and, with consent, repair permission
      breaks on the known chains only. Evidence: `_trust_chain_checks` in
      `agency_runtime/core/doctor.py`, the `--fix-perms` flag, and
      `tests/test_trust_chain_repair.py::test_doctor_lists_breaks_and_repairs_them_only_with_consent`
      plus `::test_repair_refuses_without_consent_and_outside_the_registry`.
- [x] Regression tests cover the three measured break shapes. Evidence:
      `tests/test_trust_chain_repair.py` -- the Claude npm self-update, the
      OpenClaw global install, and the plugin-cache directories that were not
      owner-private, plus the group-writable ancestor and the symlink refusal.
