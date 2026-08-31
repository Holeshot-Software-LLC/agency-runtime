---
title: "AR-338: Verify the Windows harness set (codex, claude, zcode)"
status: open
category: roadmap
created: 2026-08-30
updated: 2026-08-30
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
