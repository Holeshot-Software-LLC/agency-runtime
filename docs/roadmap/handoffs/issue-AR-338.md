---
title: "AR-338 Windows bring-up capsule"
status: active
category: roadmap
created: 2026-08-30
updated: 2026-08-31
tags: [handoff, windows, codex, claude, zcode, release]
related:
  - docs/roadmap/issue-AR-338-verify-windows-harness-set.md
  - docs/roadmap/issue-AR-337-run-harness-battery-on-version-change.md
  - docs/decisions/0193-admit-newer-codex-releases-under-the-newest-proven-child-contract.md
  - docs/decisions/0194-admit-host-encrypted-codex-canary-task-delivery.md
  - docs/RELEASE_CHECKLIST.md
  - docs/TROUBLESHOOTING.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-338
branch: main
evidence_commit: 0abe4a77c87af87cf0d2789df77d40d4a6f80a44
minimum_ledger_commit: 0abe4a77c87af87cf0d2789df77d40d4a6f80a44
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/368
---

# AR-338 Windows bring-up capsule

Windows machine (codex, claude, zcode installed). Build, smoke, and
cross-OS parity are done; install and live proof remain.

## checkpoint

Windows release evidence is complete as of 2026-08-31. A clean clone at
exact main `0abe4a77` built per the release checklist on trusted
`C:\Python313`: twine strict and `verify_distribution` pass; win_amd64
wheel `54524be19ebd...1cb012`, sdist `15d87f7dda21...29a3ee`. Isolated
wheel and sdist smokes both pass (packaged imports, windows-x64 smoke
battery, `agency smoke --all`, `pip check`). Cross-OS byte-parity is
measured, not inferred: this machine rebuilt PR #365's synthetic merge
commit (same tree `49955b2f` as `0abe4a77`, committer time `1788116558`)
and reproduced the hosted CI artifacts byte-for-byte — sdist
`88692195bb4f...e8d876` equal to the hosted ubuntu and windows sdists,
wheel `eaded9bdfa17...4490bd` equal to the hosted windows wheel. Artifact
container timestamps are the commit's committer time, so hashes only
compare between builds of the same commit; payload members at real
`0abe4a77` are member-for-member identical to the hosted set.

Two capsule premises are corrected. First, repository Actions is running
again — PR #369's rollup is green including both artifact producers and
the artifact-parity merge gate — so the hosted gate does produce per-PR
cross-OS proof at synthetic merge commits; this machine's contribution is
the exact-commit evidence and the live harness set. Second, this machine
was not at a zero point: a 2026-08-28 install from
`codex/windows-harness-release-go` (20 commits ahead of then-main, now
200 behind) already registered codex, claude, and zcode at generation 56,
store schema 48 == current main, digests claude/zcode `4b496fe2ae31...`,
codex `0cfec2186f4d...`, codex hook trust `unverified`.

## completed-evidence

- Windows receipt with the full hash chain:
  `~/.agency-runtime/evidence/ar338-windows-20260831/windows-build-0abe4a77.json`.
- Exact-main artifacts: `~/.agency-runtime/release-artifacts/dist-0abe4a77...`;
  synthetic-replica artifacts under
  `~/.agency-runtime/candidate-0abe4a77-buildenv/synthetic-dist`.
- Verified wheel venv (the step-1 install source):
  `~/.agency-runtime/candidate-0abe4a77-runenv`.
- Hosted comparison set: CI run 33329754684/33329754685 artifacts for PR
  #365 (ubuntu sdist == windows sdist; artifact-parity job green).
- Linux receipts unchanged on the Linux box:
  `~/.agency-runtime/evidence/ar297-live-harness-20260829/` and
  `~/.agency-runtime/release-artifacts/dist-0abe4a77...`.

## exact-blocker

Unchanged: the owner's LiteLLM control-plane endpoint decision for this
machine — the Linux box's LiteLLM over the LAN, or a local instance —
gates `agency install --all --config`. The machine's current config is
the pre-AR-317 per-harness pattern (claude/codex CLI adapters, z.ai for
zcode, Jina recall routes), so the install is also the v4 alias cutover
(`content_fallback_routes`, `strict_call_budget: 8`). Set referenced
environment variables in the Windows user environment; never copy key
values into files.

## same-task-continuity

Do not re-run the build, parity, or smoke steps; reuse
`candidate-0abe4a77-runenv`. The running install's source branch carried
divergent AR-331/AR-333 fixes (0.150.1 lineage admission); main's
AR-334/ADR-0194 path supersedes them, so confirm local codex-cli >= 0.151
before replacing the projections. Host CLIs must resolve from
`C:\agency-cli`: the machine PATH's npm entry outranks the entire user
PATH, and a process without the prepend reads every host `native
unverified`. The POSIX `umask 077` canary pin is a deliberate no-op on nt
(private-path host-authority logic applies); the npm group-writable
hazard is POSIX-specific. Diagnosis discipline carries over: only hook
turns are faithful for staffing diagnosis (bare `run_preflight`
fabricates `agent_host_unsupported`), and every validity probe must
nonce-bust (the LiteLLM response cache returns cached hits on identical
prompts). Smoke isolation pattern when needed: override
`AGENCY_CONFIG_PATH`, `AGENCY_DB_PATH`, `HOME`, `USERPROFILE` per CI's
`smoke_distribution`.

## next-bounded-work-package

1. Owner interview: choose the LiteLLM endpoint (LAN vs local), set the
   env vars, compose the v4 config; then `agency install --all --config
   <config>` from `candidate-0abe4a77-runenv` — codex, claude, and zcode
   re-register on exact main, replacing the windows-go projections.
2. Codex attended trust (fresh terminal, `codex`, Trust all with all 8
   Agency hook events), then
   `agency install --agent codex --verify-activation` must exit 0.
3. Live proof: `agency host-canary claude --execute --mode agency`;
   `agency host-canary codex --profile-scope current-profile --execute
   --mode agency`; zcode readiness plus `agency smoke --agent zcode`.
4. `agency battery --baseline` records this machine's fingerprints. Do
   not run `--install-service` here: the trigger service is systemd-only
   and the scheduled-task analog is follow-up under AR-337.
5. Close the parity trail: the Linux `dist-0abe4a77` sdist hash must
   equal `15d87f7dda21...29a3ee`; record its portable-wheel hash, and
   when both wheel files sit on one machine run
   `python -m scripts.verify_distribution --artifact-set release` on the
   combined trio at real `0abe4a77`.
6. Retain receipts under
   `~/.agency-runtime/evidence/ar338-windows-20260831/` and record the
   ledger row.

## verification

Acceptance mirrors the roadmap doc: byte-identical sdist and
shared-payload wheel pair (tree-level proof recorded; Linux-hash
confirmation outstanding); install --all green for codex/claude/zcode
with the dashboard healthy; codex trust plus verify-activation exit 0;
live canaries for canary-capable hosts and zcode's supported surface;
battery baseline recorded; receipts retained and the ledger updated.

## constraints

All inference behind LiteLLM aliases; zero deployment retries; no Jina;
no Spark; never print or persist credentials; do not bypass Codex
activation; new trackers need owner authorization; owner interview before
any new model/endpoint/embedding/reranker/thinking/judge/harness-auth/
service choice; do not tag, sign, publish, or release without the owner's
explicit release decision (AR-161 requires a signed delivery payload and
legal disposition first).
