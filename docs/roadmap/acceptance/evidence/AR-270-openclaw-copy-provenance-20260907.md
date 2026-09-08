---
title: "AR-270 installed-copy provenance source evidence"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [evidence, openclaw, uninstall, provenance]
related:
  - docs/roadmap/issue-AR-270-bind-openclaw-installed-copy-provenance.md
  - docs/roadmap/handoffs/issue-AR-270.md
  - docs/decisions/0108-retire-only-owned-host-integrations.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
---

# AR-270 installed-copy provenance source evidence

## Scope and governing contract

The owner requested implementation without new tests, CI, live canaries or
model evaluations. No tests below were executed; this is builder source evidence,
not isolated acceptance. No uninstall, disable, restart or owner config change
was made. ADR-0108 already requires exact owned-tree/install-ID/bundle identity,
closed native provenance, digest-bound replanning and native authority. This
package implements the existing contract rather than creating new authority.

## Existing failure

At source base `7c0c1221`, `_plugin_is_bound("openclaw")` requires the set of
direct native paths to equal only the managed target. `_direct_record_paths`
does not retain nested `install.sourcePath`; the native inspect fallback applies
the same validator. The canonical issue preserves two historical refusal
receipts, including operation `952ff8f6-a660-4309-ac54-191481944440` and plan
`a497a256064f2ececd2f27d11993cb681628e4094d2309b398c039d89ec7e2aa`.
Those are historical observations, not fresh expected-red test results.

## Current schema evidence

Read-only source inspection of installed OpenClaw 2026.8.2 found:

- `plugins-inspect-command-CUhvUuWZ.js`: inspect emits the plugin report and a
  sibling `install` record resolved for that exact plugin ID. SHA256
  `dd4ace92388e672a810248bd27c6e4976f882fa5601888d03a1b1cab9ad9e812`.
- `plugin-install-record-map-DPUdGGiU.js`: path source discriminator plus
  optional sourcePath/installPath/version fields. SHA256
  `56a7f232e685b17f653cf2c230104b55c67e50875637f9e46bac45cf9e1814e8`.

A separately authorized, read-only `openclaw plugins inspect agency-preflight
--json` used the installed Agency trusted native runner, without `--runtime`.
It returned exit 0 with neither stream truncated. Only allowlisted field names
and provenance were printed, never config bodies, credentials or model output.
Observed plugin ID/version were agency-preflight/0.1.0, with root field
`rootDir` and entry `extensions/agency-preflight/index.js`. The install record
reported source `path`, managed source `host-plugins/openclaw/agency-preflight`,
installed copy `extensions/agency-preflight` and version 0.1.0. Both paths have
their respective owner runtime/host prefixes; no equality between those roots
is inferred. The older flat root/source/install shape is preserved separately
from the current envelope; no old raw payload is fabricated.

## Candidate implementation

- Require exact plugin ID, path source, managed source equality, coherent copy
  root aliases and an entry strictly inside the separate copy root.
- Reject missing, malformed, relative, traversing, substituted and conflicting
  paths. Partial install metadata never falls back to direct-source acceptance.
- Treat native versions as optional; when present they must agree with the
  independently validated owned manifest, rather than becoming new authority.
- Join only an exact single-plugin inspect envelope with its own install record;
  duplicate plugin records and conflicting envelope/child provenance stay closed.
- Retain any exact Agency identity during OpenClaw extraction, then reject
  contradictory identity aliases before inventory can be treated as absence or
  replaced by a cleaner inspect record. Ordinary unrelated plugins remain ignored.
- Preserve the entire joined record in existing native-state hashing. No new
  mutation primitive, copied-file deletion or authority grant is introduced.

## Static checks and unrun regressions

Executed against the two owned source/test paths:

```bash
/tmp/agency-ar404-venv.AUBJlC/bin/ruff format agency_runtime/core/installer_uninstall.py tests/test_host_uninstall.py
/tmp/agency-ar404-venv.AUBJlC/bin/ruff check agency_runtime/core/installer_uninstall.py tests/test_host_uninstall.py
git diff --check
```

Initial Ruff identified test-function complexity 17 above limit 15. Two related
fault cases were grouped; final Ruff reported **All checks passed!**, formatting
left two files unchanged and diff check passed. No runtime test was run.

The original thirty-two added cases cover flat/enveloped receipts with root/rootDir aliases;
missing install fields; wrong identity, source, copy, version and path aliases;
relative/traversing/escaping entries; optional version omission; legacy direct
binding; duplicate/conflicting/unrelated envelopes; a symlink entry; write-free
inspect fallback; provenance changes altering both binding and plan digests; and
an unowned managed tree remaining blocked. These are written assertions only.

## First independent review and correction

One High finding was identified by source-only review: generic extraction chose
the first truthy identity alias. `id=agency-preflight` with an earlier conflicting
`pluginId` could disappear before the new leaf validator and be planned as native
absence. No test run or live reproduction is claimed for that finding.

The correction uses OpenClaw-specific any-identity extraction and explicit
identity-conflict refusal at both inventory and inspect admission. Twelve new
plan-level regression cases cover four conflicting identity aliases across
inventory, flat inspect and envelope inspect. A thirteenth extraction case
preserves unrelated plugins and the native human-readable name field. There
are now **45 added, unrun cases**. Failed identity admission has no successful
plan digest; accepted receipts retain the complete identity/provenance record
inside the existing native-state digest. The original High review is retained.

The final narrow independent source recheck at `fc699ff3` confirmed that the
High was resolved, both refusal paths precede binding/absence decisions, and
the twelve new cases exercise full planning. No additional scoped finding was
reported. The reviewer ran no tests, CI or native commands; this is not runtime
acceptance. Normal merge `a9073fe6` brought in published main `cb9e9a50` without
changing either AR-270 runtime/test blob.

## Pending

The original expected-red/focused runtime gates and isolated acceptance are
still pending. Separately authorized tracker
[#749](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/749) is open
with epic:install; strict parity is checked after current-main integration.
No native unload, uninstall or end-to-end completion is claimed.
