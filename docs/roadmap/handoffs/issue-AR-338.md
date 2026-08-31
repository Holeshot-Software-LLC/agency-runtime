---
title: "AR-338 Windows bring-up capsule"
status: active
category: roadmap
created: 2026-08-30
updated: 2026-08-30
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

Start here on the Windows machine (codex, claude, zcode installed).

## checkpoint

Linux is fully verified at exact main `0abe4a77`: four harnesses
live-green, codex activation attested on codex-cli 0.151 under ADR-0194,
`verify-activation` exit 0, AR-337 battery armed with all doctor rows
passing. Windows work has not started; this capsule is its zero point.

## completed-evidence

- Linux receipts: `~/.agency-runtime/evidence/ar297-live-harness-20260829/`
  (`codex-canary-cp-0abe4a77.json`, `codex-verify-activation-0abe4a77.stdout`,
  `claude-canary-0abe4a77.json`, `*-ordinary-receipt.json`,
  `host-install-0abe4a77.json`).
- Linux release artifacts for byte-parity comparison:
  `~/.agency-runtime/release-artifacts/dist-0abe4a77…` (sdist + portable
  wheel, twine strict pass, verify_distribution pass).
- Windows portability is CI-proven per merge (py3.11-3.13 portability
  contract; win_amd64 build job on windows-2022).

## exact-blocker

One owner decision gates install: the LiteLLM control-plane endpoint for
the Windows machine — the Linux box's LiteLLM over the LAN, or a local
instance. The v4 configuration pattern (`ar297-litellm-v4-*.yaml`:
planner/recruiter `content_fallback_routes`, `strict_call_budget: 8`)
carries over unchanged either way. Set referenced environment variables in
the Windows user environment; never copy key values into files.

## same-task-continuity

The generated codex hooks carry `commandWindows` forms and the ADR-0194
parser is path-neutral under `CODEX_HOME`, so the 0.151 contracts proven on
Linux apply as-is. The POSIX `umask 077` canary pin is a deliberate no-op
on nt (private-path host-authority descendant logic applies); the npm
group-writable hazard is POSIX-specific and its Windows analog would
surface through the same content-free posture probes as ACL causes.
Diagnosis discipline carries over: only hook turns are faithful for
staffing diagnosis (bare `run_preflight` fabricates
`agent_host_unsupported`), and every validity probe must nonce-bust
(the LiteLLM response cache returns cached hits on identical prompts).

## next-bounded-work-package

1. PowerShell, clean clone at `0abe4a77` or later, per
   `docs/RELEASE_CHECKLIST.md`: capture `AGENCY_RELEASE_COMMIT`, run
   `python -m scripts.build_distributions <dist> --create-private-parent
   --expected-commit <commit>`, then `twine check --strict` and
   `python -m scripts.verify_distribution`.
2. Compare against the Linux artifacts: the sdist must be byte-identical
   and the win_amd64/portable wheel pair must share payloads. Record both
   hash sets — this is the cross-OS release proof the hosted gate cannot
   produce while repository Actions billing is disabled.
3. Create a venv from the verified wheel; `agency smoke` must pass.
4. `agency install --all --config <config>` — codex, claude, and zcode
   register (no hermes/openclaw on this machine).
5. Codex attended trust (fresh terminal, `codex`, Trust all with all 8
   Agency hook events), then
   `agency install --agent codex --verify-activation` must exit 0.
6. Live proof: `agency host-canary claude --execute --mode agency`;
   `agency host-canary codex --profile-scope current-profile --execute
   --mode agency`; zcode readiness plus `agency smoke --agent zcode`.
7. `agency battery --baseline` records this machine's fingerprints. Do not
   run `--install-service` here: the trigger service is systemd-only and
   the scheduled-task analog is follow-up under AR-337.
8. Retain receipts under a machine-local evidence namespace and record the
   ledger row.

## verification

Acceptance mirrors the roadmap doc: byte-identical sdist and
shared-payload wheel pair; install --all green for codex/claude/zcode with
the dashboard healthy; codex trust plus verify-activation exit 0; live
canaries for canary-capable hosts and zcode's supported surface; battery
baseline recorded; receipts retained and the ledger updated.

## constraints

All inference behind LiteLLM aliases; zero deployment retries; no Jina; no
Spark; never print or persist credentials; do not bypass Codex activation;
new trackers need owner authorization; owner interview before any new
model/endpoint/embedding/reranker/thinking/judge/harness-auth/service
choice; do not tag, sign, publish, or release without the owner's explicit
release decision (AR-161 requires a signed delivery payload and legal
disposition first).
