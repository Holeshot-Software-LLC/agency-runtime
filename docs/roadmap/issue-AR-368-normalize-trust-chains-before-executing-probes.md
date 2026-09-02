---
title: "AR-368: Normalize a host's trust chains before the probe that runs it"
status: in_progress
category: roadmap
created: 2026-09-02
updated: 2026-09-02
tags: [installer, canary, trust-chain, operations]
related:
  - docs/roadmap/issue-AR-358-installer-doctor-trust-chain-self-healing.md
  - docs/roadmap/issue-AR-337-run-harness-battery-on-version-change.md
supersedes: []
superseded_by: null
type: issue
epic: install
issue_id: AR-368
priority: p2
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/500
depends_on: []
blocks: []
---

# AR-368: Normalize a host's trust chains before the probe that runs it

## Problem

AR-358 established the trust chains at install time. That is not enough for a
host that rewrites its own tree: Claude Code chmods its npm package tree
group-writable on every invocation, so the chain is broken again by the first
probe that runs the host, and the claude canary fails on
`executable parent namespace permits cross-account substitution`.

Measured live on 2026-09-02 (this box, runtime `48881d1d`):

- 11:27Z: `repair_trust_chains` reports 14 entries changed under
  `@anthropic-ai/claude-code`; the follow-up scan is empty.
- 11:28Z: the claude battery runs; the tree is 0775 again and the canary
  fails with the namespace error.
- 11:30:45 local: repaired again, mode 755, ctime moves.
- 11:37:30 local: after `agency install --agent claude` and the canary, mode
  is 0775 and ctime has moved again — the host itself did it.

## Current state

`agency doctor --fix-perms` and the installer both repair correctly (AR-358),
and both are immediately undone by the next host invocation. The battery
therefore cannot pass claude on this machine no matter how often an operator
repairs by hand.

## Approach

Normalize the host's own registered chains inside host inspection, immediately
before the probe that executes the host, so the chain is provably trusted at
the moment it is read. Keep it opt-in: `agency status` and `agency doctor`
inspect read-only and must never chmod as a side effect; the canary asks for
it. Record the repair as inspection evidence so it is never silent.

Found while working here: `test_doctor_converts_native_inventory_failure_to_structured_report`
and `test_doctor_inventory_failure_keeps_explicitly_disabled_hosts_passing` were
failing on main because they let `run_doctor` read this machine's recorded
battery outcomes, so the suite's verdict depended on whether the operator's last
battery passed. Both now isolate the machine-reading checks.

## Dependencies

- AR-358 owns the chain registry, the scan, and the bounded repair this reuses.

## Acceptance

- [x] An executing probe repairs the host's registered chains before reading
      them, and records what it changed as evidence. Evidence:
      `_normalized_chain_evidence` and its call site in
      `agency_runtime/core/installer_inventory.py`, plus
      `tests/test_trust_chain_repair.py::test_an_executing_probe_normalizes_the_chain_first`.
- [x] A read-only inspection never chmods. Evidence:
      `tests/test_trust_chain_repair.py::test_a_read_only_inspection_never_chmods`.
- [ ] The claude battery passes on this machine with the normalization live.
