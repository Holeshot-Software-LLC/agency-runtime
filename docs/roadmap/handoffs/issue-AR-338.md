---
title: "AR-338 Windows bring-up capsule"
status: active
category: roadmap
created: 2026-08-30
updated: 2026-09-01
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

Release evidence, the 2026-08-31 bring-up, and the 2026-09-01 `ec6c4b49`
re-pass are recorded below; outcomes live in next-bounded-work-package.

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

None. AR-338 is complete (2026-08-31): the owner-reported Linux
`dist-0abe4a77` sdist hash equals the Windows build byte-for-byte, the
win_amd64/portable pair shares all 592 payload members (measured against
the tree-identical hosted portable wheel; Linux portable wheel
`afb419a3...` recorded), and every acceptance box on the roadmap doc is
checked. Optional strengthening whenever both wheel files sit on one
machine: `verify_distribution --artifact-set release` on the combined
trio.

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

Re-pass executed 2026-09-01 on this machine: all three hosts and the
dashboard service moved from exact-main `9521a4a4` to exact-main
`ec6c4b49` (runtime digest `23ebce86d6f4...`) through the checklist
wheel path — build, strict twine, `verify_distribution`, and `pip check`
pass; wheel `c401048c...5bca2`, sdist `79ae0de4...e1663`; store schema
48 on both pins, no migration. Codex attended trust re-done and
`verify-activation` exit 0 ("Codex current-profile activation
verified"); the burned-refresh-token and ACL-probe branches never fired.
zcode smoke 4/4 with retained receipt. Battery baseline re-adopted at
observed claude 2.1.250 / codex-cli 0.151.0 (no drift, so the change
gate owes no drills). Claude isolated canary: passed on attempt 5
(~13:05Z) — header valid, `code-reviewer` selected and loaded, and a
hash-bound `minimal-change-engineer` card delivered pre-speech to the
host-authored child, bound to candidate digest `23ebce86d6f4`. Earlier
attempts: one killed by the default 120 s timeout, two critic-rejected,
one killed by the launcher's own tool cap; receipts retained. Evidence:
`~/.agency-runtime/evidence/ar338-windows-20260901/`.

Findings the next session needs: claude 2.1.250 `-p` turns now run
hooks — a staffed preflight alone ran 76 s, so the canary's default
120 s timeout cannot fit a staffed turn; pass `--timeout 600` (the
cap). The canary receipt's `new_ids` delta absorbs concurrent sessions'
store writes (it matched another session's turn-ends to the
millisecond); join receipts to `runs.session_id` and keep only the
isolated-home sessions before diagnosing. Since 2026-08-31 ~16:48Z the
box shows intermittent claude-harness staffing-verdict failures
(`staffing_critic_rejected`, `required_composition_agent_missing`,
`inference_invalid`, `selection_confidence_too_low`) interleaved with
confidence-1.0 acceptances on both the old and new runtimes — the
pattern predates this re-pass (this session's own first turn failed at
11:46:58Z, before the install finished), and codex-side inference
passed cleanly in the same window, so it is shaped like the claude
inference route, not the re-pin. The standing noise source is the
owner's long-running Claude desktop-app session (embedded CLI 2.1.247,
alive since 2026-08-29 on retired launcher `4b496fe2`, 184 preflight
failures at a ~4-minute automated cadence) — the owner restarted it
2026-09-01 ~12:59Z, every launcher-bound process on the box now runs
`23ebce86d6f4`, and the canary passed on the very next attempt in that
cleaned-up window.

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
