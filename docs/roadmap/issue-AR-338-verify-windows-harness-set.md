---
title: "AR-338: Verify the Windows harness set (codex, claude, zcode)"
status: open
category: roadmap
created: 2026-08-30
updated: 2026-08-31
tags: [host-integrations, windows, codex, claude, zcode, release]
related:
  - docs/roadmap/handoffs/issue-AR-338.md
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-337-run-harness-battery-on-version-change.md
  - docs/decisions/0194-admit-host-encrypted-codex-canary-task-delivery.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-338
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/368
depends_on: []
blocks: []
---

# AR-338: Verify the Windows harness set (codex, claude, zcode)

## Problem

The Linux machine is fully verified on exact main: all four resident
harnesses live-green, codex activation attested on codex-cli 0.151 under
ADR-0194, and the AR-337 battery armed. The owner's Windows machine carries
codex, claude, and zcode, and nothing has proven that harness set against
the current runtime. Separately, the release contract requires
byte-identical cross-OS source distributions and a shared-payload
win_amd64/portable wheel pair, and the hosted merge gate that would prove
this cannot run while repository Actions billing is disabled — so the
Windows bring-up is also the only near-term path to that release evidence.

## Approach

Follow the handoff capsule (`docs/roadmap/handoffs/issue-AR-338.md`): build
the exact-main distributions on Windows per the release checklist and
compare them byte-for-byte against the retained Linux artifacts; install
the runtime and register codex, claude, and zcode; complete one attended
codex trust round; run verify-activation and the live canaries; and record
receipts under the machine's own evidence namespace. Windows-specific
expectations are carried in the capsule: the POSIX umask pin is a
deliberate no-op on nt (private-path host-authority logic applies), the
battery core works but its trigger service is systemd-only (the scheduled
task analog is follow-up under AR-337), and the npm group-writable hazard
is POSIX-specific.

## Current state (2026-08-31)

The release-evidence half is done on the Windows machine. A clean clone at
exact main `0abe4a77` built per the checklist (twine strict and
`verify_distribution` pass; wheel `54524be19ebd...1cb012`, sdist
`15d87f7dda21...29a3ee`), and isolated wheel plus sdist smokes pass. The
cross-OS claim is measured: rebuilding PR #365's synthetic merge commit
(identical tree `49955b2f`, its committer timestamp) on this machine
reproduced the hosted ubuntu and windows CI artifacts byte-for-byte, and
artifact container timestamps were shown to derive from the committer
time, which is why only same-commit builds hash-compare. Two premises
changed since filing: repository Actions runs again (PR #369's rollup is
green including the artifact-parity gate), and the machine was not at a
zero point — a 2026-08-28 install from `codex/windows-harness-release-go`
already registered codex, claude, and zcode at store schema 48 with codex
hook trust `unverified`.

Later the same day the exact-main install landed: `agency install --all`
from the verified wheel venv registered codex, claude, and zcode on
runtime digest `c4815c3a6931...` with the standing per-harness
agency.yaml. zcode smoke passes 4/4 and its readiness receipt is
retained. The package also surfaced two Windows defects, described in the
capsule with fix directions: the dashboard-service environment guard
refuses to start the fresh worker whenever a config-declared credential
env name is present in its inherited user-registry environment (the
sanctioned secret location on Windows), and `agency battery --baseline`
silently adopts nothing because the version observer cannot execute npm
`.cmd` shims without a shell. The 08-26 old-runtime dashboard worker was
restored and serves meanwhile. Remaining: attended `claude login` plus
the claude live canary rerun (the claude CLI OAuth session is expired
machine-wide, which is also what failed today's canary), codex attended
trust plus `verify-activation`, the two defect fixes, and Linux-side
hash confirmation of the retained `dist-0abe4a77` set. Details in the
capsule and the machine-local receipt
`~/.agency-runtime/evidence/ar338-windows-20260831/windows-build-0abe4a77.json`.

## Owner interview outcome (2026-08-31)

The LiteLLM-endpoint dependency is resolved as a split inference backing
under one config model. This Windows machine keeps its per-harness
CLI/API configuration — claude via the Claude CLI profiles, codex via the
codex CLI profiles, zcode via its Anthropic-compatible API profiles, and
the Jina embedding/reranker recall routes — with no LiteLLM control
plane. The Linux machine keeps its LiteLLM alias routing (the v4
pattern). The owner's stated invariant: per-harness configuration exists
on both machines — each harness has its own config regardless of which
machine it is installed on; the LiteLLM alias layer is a per-machine
backing inside those per-harness sections, never a repo-global
constraint. Reaching the Linux box's LiteLLM over the LAN was considered
and rejected: it binds to loopback (127.0.0.1:4000) on that machine, and
exposing it would be a new harness-auth/service surface with no payoff
while this machine's per-harness inference is already proven. The install
therefore proceeded with the standing agency.yaml rather than a
`--config` bind.

## Dependencies

The v4 configuration pattern with an owner decision on the LiteLLM control
plane endpoint for the Windows machine (shared LAN endpoint versus a local
instance) — an owner interview before install, consistent with the
harness-auth and service constraints. No new inference routes.

## Acceptance

- [ ] Windows-built exact-main sdist is byte-identical to the Linux sdist
      and the wheel pair satisfies the shared-payload release contract.
- [ ] `agency install --all` registers codex, claude, and zcode on Windows
      with the dashboard healthy.
- [ ] Codex attended trust completes and `verify-activation` exits 0 on the
      Windows profile.
- [ ] Live canaries pass for the hosts exposing a canary mode; zcode proves
      its supported readiness surface.
- [ ] `agency battery --baseline` records the Windows harness fingerprints;
      the trigger-service gap is logged under AR-337.
- [ ] Receipts are retained and the ledger records the verification.
