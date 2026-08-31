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
  - docs/roadmap/issue-AR-339-admit-durable-user-scope-credentials-in-dashboard-service-guard.md
  - docs/roadmap/issue-AR-340-observe-npm-shim-harness-versions-in-battery.md
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

Release evidence and the exact-main install are done; what remains is two
attended owner actions and two filed-pending Windows defects.

## checkpoint

The 2026-08-30 zero-point premise and the LiteLLM dependency are both
resolved. Release evidence (2026-08-31): exact-main `0abe4a77` built on
Windows per the checklist — twine strict and `verify_distribution` pass,
wheel `54524be19ebd...1cb012`, sdist `15d87f7dda21...29a3ee`; isolated
wheel+sdist smokes pass; cross-OS parity measured by rebuilding PR #365's
synthetic merge commit (tree `49955b2f` == `0abe4a77`'s) byte-identically
to the hosted ubuntu/windows CI artifacts. Container timestamps derive
from the committer time, so only same-commit builds hash-compare.

Owner decision (2026-08-31): split inference backing under one config
model. Windows keeps the per-harness CLI/API config with Jina recall
routes and **no LiteLLM**; the Linux machine keeps LiteLLM alias routing.
Per-harness config exists on both machines — each harness has its own
config regardless of machine; the LiteLLM alias layer is a per-machine
backing inside those sections, never a repo-global constraint. LAN reuse
of the Linux LiteLLM was rejected (loopback-only at 127.0.0.1:4000).

Install (2026-08-31): `agency install --all` from the verified wheel venv
first registered codex, claude, and zcode on exact-main `0abe4a77`
(digest `c4815c3a6931...`); after ADR-0195 merged the same day, all three
hosts and the dashboard service were re-pinned to exact main `9521a4a4`
(digest `d2fd5aa2d3ef...`), which carries the AR-339/AR-340 fixes and the
role-null lineage admission. The dashboard service is registered and
serving on the fresh runtime (AR-339 closed). zcode smoke passes 4/4 and
its readiness receipt is retained; zcode exposes no noninteractive canary
mode by design. The battery baseline records claude 2.1.250 and codex-cli
0.150.1 (pre-upgrade); re-adopt it after the upgraded codex's first green
canary so the AR-337 change gate tracks 0.151.0.

## completed-evidence

- Machine receipt (hash chain, install, defects, canary outcomes):
  `~/.agency-runtime/evidence/ar338-windows-20260831/windows-build-0abe4a77.json`,
  plus `claude-canary-0abe4a77.json` and `zcode-readiness-0abe4a77.json`.
- Artifacts `~/.agency-runtime/release-artifacts/dist-0abe4a77...`; wheel
  venv `~/.agency-runtime/candidate-0abe4a77-runenv`; synthetic-replica
  dist under `candidate-0abe4a77-buildenv/synthetic-dist`.
- Linux receipts unchanged on the Linux box (`ar297-live-harness-20260829`,
  `dist-0abe4a77...`).

## exact-blocker

None on this machine. The sole remaining AR-338 item is cross-machine:
the Linux `dist-0abe4a77` hash confirmation (sdist must equal
`15d87f7dda21...29a3ee`) and the combined-set
`verify_distribution --artifact-set release` once its portable wheel sits
beside the Windows pair.

Claude went live 2026-08-31 after three measured host-behavior fixes in
the isolated canary staging: claude 2.1.250 stopped activating
`--plugin-dir` hooks (and `--setting-sources=` suppresses staged
settings), so the isolated home is now staged through the CLI's own
`plugin marketplace add` + `plugin install`; and a freshly installed
plugin's prompt hooks skip the first session, so one bounded warm-up turn
makes the canary the home's second session. The passing receipt
(`claude-canary-9521a4a4.json`) carries a valid header, fully proven
isolated plugin, and a hash-bound `minimal-change-engineer` card
delivered to the host-authored child. Codex passed the same day
(verify-activation exit 0 plus an attested current-profile canary).

## same-task-continuity

Do not re-run build, parity, smoke, or the install; the runenv and the
`c4815c3a...` projections stand. Prepend `C:\agency-cli` to PATH for any
process running `agency` (machine-PATH npm entry outranks the user PATH).
Run installs with configured credential env names unset in the installing
process (`env -u JINA_API_KEY`) — they stay persisted user-scope. The
POSIX umask pin is a no-op on nt; the npm group-writable hazard is
POSIX-specific. Only hook turns are faithful for staffing diagnosis; all
of today's `workforce_provider_unavailable` receipts trace to the expired
claude OAuth, not to routing. The windows-go branch's divergent
AR-331/333 fixes are superseded by main's 0.149–0.151 parser range.

## next-bounded-work-package

1. Owner: `claude login`; then rerun
   `agency host-canary claude --execute --mode agency --confirm
   "RUN LIVE claude CANARY"` from the runenv and retain the receipt.
2. Owner: codex attended trust, then
   `agency install --agent codex --verify-activation` exit 0; then
   `agency host-canary codex --profile-scope current-profile --execute
   --mode agency`.
3. At the next anchored install, let `agency install --all` register the
   dashboard service on a fixed runtime (closes AR-339's last box and the
   dashboard-healthy acceptance).
4. Close the parity trail: Linux `dist-0abe4a77` sdist hash must equal
   `15d87f7dda21...29a3ee`; record the portable-wheel hash; when both
   wheels sit on one machine run `verify_distribution --artifact-set
   release` on the combined trio.
5. Record the ledger row for each advance.

## verification

Acceptance mirrors the roadmap doc: byte-identical sdist and
shared-payload wheel pair (tree-level proof recorded; Linux-hash
confirmation outstanding); install --all green for codex/claude/zcode
with the dashboard healthy (hosts green; dashboard blocked by the env
guard defect); codex trust plus verify-activation exit 0; live canaries
for canary-capable hosts and zcode's supported surface (zcode smoke 4/4
recorded); battery baseline recorded (done
2026-08-31: claude 2.1.250, codex-cli 0.150.1); receipts retained and the
ledger updated.

## constraints

On this machine the owner-approved posture is per-harness CLI/API
inference with Jina recall routes and no LiteLLM; the Linux machine keeps
all inference behind LiteLLM aliases. Zero deployment retries; no Spark;
never print or persist credentials (secrets live in the Windows user
environment); do not bypass Codex activation; new trackers need owner
authorization; owner interview before any new model/endpoint/embedding/
reranker/thinking/judge/harness-auth/service choice; do not tag, sign,
publish, or release without the owner's explicit release decision
(AR-161 requires a signed delivery payload and legal disposition first).
