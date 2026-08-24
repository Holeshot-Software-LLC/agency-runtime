---
title: "AR-264: Compile actionable contractor execution profiles"
status: in_progress
category: roadmap
created: 2026-08-21
updated: 2026-08-21
tags: [contractors, hiring, prompts, workforce, dashboard, AR-119]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-122-contractor-hiring-and-lifecycle.md
  - docs/roadmap/issue-AR-123-workforce-cli-and-dashboard.md
  - docs/roadmap/handoffs/issue-AR-264.md
  - docs/roadmap/issue-AR-265-accept-openclaw-stopped-gateway-status.md
  - docs/roadmap/issue-AR-266-accept-openclaw-numeric-package-revision.md
  - docs/roadmap/issue-AR-267-create-nested-config-parents-privately.md
  - docs/roadmap/issue-AR-268-accept-null-openclaw-control-errors.md
  - docs/roadmap/issue-AR-269-bind-openclaw-installed-copy-provenance.md
  - docs/roadmap/issue-AR-270-accept-stopped-openclaw-uninstall-status.md
  - docs/roadmap/issue-AR-271-preserve-openclaw-model-receipt-fields.md
  - docs/roadmap/issue-AR-272-expose-openclaw-native-finalizer-tool.md
  - docs/roadmap/issue-AR-278-deliver-openclaw-finalizer-results.md
  - docs/decisions/0081-compile-contractors-from-governed-structured-contracts.md
  - docs/decisions/0162-compile-structured-contractor-execution-guidance.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: roster-governance
issue_id: AR-264
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/313
depends_on: [AR-122, AR-123, AR-278]
blocks: [AR-119]
---

# AR-264: Compile actionable contractor execution profiles

## Problem

Agency's governed contractor prompt establishes identity, scope, authority,
capabilities, exclusions, and evidence boundaries, but it gives the executing
child little role-specific working method. The fixed template serializes the
entire employment contract as dense JSON, including recruiter-only comparison
and evaluation metadata. It therefore constrains and identifies the worker
without guiding execution as clearly as the audited resident specialist cards.

The dashboard compounds that ambiguity by rendering `Evidence required: none
recorded` for packaged contractors even though their immutable revision
metadata and compiled prompt contain explicit evidence requirements.

## Current state

- Employment-contract and prompt-template v2 are implemented. New live hiring
  requires the closed profile while parser/compiler v1 remains replay-only.
- All 15 packaged contractors carry reviewed role-specific inspect, principle,
  failure, verification, and stop guidance. The exact assigned work unit still
  arrives separately from the native host.
- Compiler v2 emits a readable worker capsule and omits recruiter-only nearest
  worker and evaluation material. The TypeScript capsule is 2,710 bytes at
  `contractor-2-6b0d5cae3b65a44d`.
- Pull request [#314](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/314)
  merged as exact main `da851c65`; installing it exposed that all 15 real
  package-v1 workers were preserved instead of advanced.
- The exact-main defect was a synthetic predecessor: the migration test minted
  the post-August-6 canonical version, while the real Store retained the older
  `contractor-1-sha256:<9 hex>` package identity. The backend contract also had
  pre-v2 capability and evidence fields that could not be reconstructed by
  merely deleting its execution profile.
- The repair pins all 15 historical v1 prompt hashes, reconstructs the two
  version identities that actually shipped, and revalidates prompt bytes,
  immutable revision metadata, and the current recruitment contract inside the
  Store transaction. Unknown Agency amendments and operator projections remain
  preserved.
- A transactionally backed-up disposable copy of the owner Store advanced
  15/15 workers, advanced none on its second pass, retained two-version lineage
  for every worker, and preserved TypeScript's two accepted outcomes and 2/3
  promotion readiness. Pull request
  [#315](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/315)
  merged that repair as exact main `f76050d7`; both PRs used `[skip ci]` and
  no hosted workflow ran.
- Before exact-main installation, the owner Store was copied to
  `pre-ar264-f76050d7-20260821T171621.410934Z.db` with SHA-256
  `9b9936456e90313b76920a4dfd3890c7c44b0243d4a2781592182325aa2bcdaa`.
  The real installation then upgraded all 15 known packaged contractors to
  revision 1 / contract v2 / two-version lineage. TypeScript retained its two
  accepted outcomes and 2/3 promotion readiness.
- Specialist prompt reads now decode exact active revision metadata, and the
  dashboard overlays its real `evidence_requirements` into owner detail.
- The repaired candidate passes all 14 governing local gates in 16.5 minutes:
  806 passed and 20 skipped in the production spine, 695 passed in AR-119
  matrix evidence, 161 passed in workflow contracts, and all 134 dashboard UI
  tests meet the configured coverage thresholds. The deterministic routing
  evaluation passes every correctness, safety, performance, and scale gate.
  Linux behavior, integration coverage shards, and the hosted-only mutation
  phase remain outside this local package.
- Exact main `f76050d7` is freshly installed for Claude, Codex, ZCode, and the
  dashboard. Their current bundle digests are `2eaa89cc75f8...`,
  `75f6519c74ba...`, and `2f1bb95ba204...`; all three native projections are
  current and report no configuration drift.
- After the reboot, the existing dashboard task was registered and current but
  stopped. Starting that owned task restored authenticated health. Dashboard
  and CLI then returned the same 31 contractor rows at digest
  `401e883532e9...`; after one bounded background host refresh, all five host
  rows matched at digest `003caceee19d...`, and master generation 56 matched.
- Skill capture is provider-free proven on this exact tree: three focused hook
  cases pass for Claude, Codex, and ZCode, each injecting its loaded skill into
  the first-pass header. The owner Store contains 19 historical skill-load
  rows. Fresh post-install Desktop task `01a02587-...` received no Agency header,
  hook-log event, Store run, or resident binding, so no skill was loaded and the
  historical rows were not projected as current evidence. Its first user turn
  was not the intended exact `agency status` control.
- The single exact-main Codex activation draw stopped at parent preflight
  `workforce_inference_failed` after valid planner and recruiter responses; it
  produced no routing decision, child, delegation, delivery, or final header.
  The first ZCode draw exited 0 and started a generic host child, but Agency
  failed its ordinary planner through the then-expired Claude subscription. It
  was not retried.
- Claude authentication was restored before one genuinely different COBOL/CICS
  and VSAM hiring draw. Session `560e6da4-...`, trace `66dca68e-...`, received
  a real installed Agency capsule; its accepted decision and applied standard-
  risk hiring case added active contractor `cobol-cics-vsam-diagnostics-
  specialist`, moving the contractor projection from 31 to 32. Native-child
  inference actually used `codex-subscription`. Claude's progress response
  omitted the required header, however, and its one child timed out before a
  conclusion at 420 seconds with no delivery-verification row. The draw was not
  retried.
- One conditional ZCode plural attempt then ran with the existing GLM child-
  judge pin and unchanged ordinary routing. Session `sess_524d8b86-...` exited
  0 and spawned a generic child, while Agency trace `b08d8d79-...` failed
  `workforce_inference_failed`: its Claude-backed planner applied, but both
  recruiter responses were contract-invalid `staff_without_safe_team`. The
  Store has no decision or card, the GLM child judge was never reached, and all
  four host artifacts contain zero Agency markers. It was not retried.
- The genuine hire is Store- and roster-backed; compliant Claude response
  headers, completed contractor execution, ZCode plural-card delivery, and the
  fresh Codex Desktop skill header remain unproven. Provider routing, Option A
  pins, and AR-119 matrix cells did not change.
- Post-recording documentation validation passes all 731 files, and 8 focused
  warning-strict tests pass for the exact OpenClaw/Hermes canary, artifact-
  reader, and native-child bridge boundaries used by the Linux handoff.
- Tracker [#313](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/313)
  remains open until the fresh-task and authenticated live boundaries above
  are completed.

### 2026-08-21 Linux OpenClaw pre-live checkpoint

- The Linux package uses fetched `origin/main` `4a326773` with repaired anchor `f76050d7` in ancestry and checkout-module CLI identity throughout.
- Before install, Store contractor count was zero. The first partial attempt seeded 263 roster entries and all 15 packaged contractors before stopping safely at launcher identity; later attempts reused them idempotently.
- Existing LiteLLM configuration is preserved through populated `LITELLM_API_KEY` and exact alias `task-agency-router`. Agency routes only OpenClaw and Hermes through harness profile `linux-task-agency-router`.
- OpenClaw install failures were preserved as AR-265 through AR-267. A later completed install accepted Telegram input but queued no reply because its healthy control payload with `error: null` exited 2; AR-268 has a failing-before/passing-after bounded bridge repair.
- Focused sets pass 45 registration, 18 version/live-gateway, and 59 configuration/streaming tests.
- The installed plugin was removed while stopped, all five native streaming values and the `task-general` host default/catalog were restored, and the 15-contractor Store state plus failed bundle evidence remain retained. AR-269 and AR-270 record two fail-closed uninstall compatibility defects.
- Baseline OpenClaw is active with Slack connected and Telegram polling. AR-271 preserved native model receipts, but the next control remained failed because the Agency plugin exposed no native finalizer. AR-272 adds only the Agency-owned `agency_finalize` wrapper; its pre-fix Node regression exited 91 and 65 focused OpenClaw tests pass. A clean checkpoint precedes installing that Agency integration and collecting fresh proof.
- Hermes remains running and untouched as break glass. Exact `task-agency-router` remains only in Agency's harness profile; no native host default uses it.
- Codex OAuth/configuration and the consumed Codex canary remain untouched. This Linux package has not moved any AR-119 matrix cell.

### 2026-08-23 Hermes install checkpoint

- Read-only preflight found Hermes Agent v0.20.4 at effective home
  `/home/holeshot/.hermes-nexus`, natively using `litellm/task-general` plus
  five fallbacks and nine enabled plugins. Agency was unregistered. Store
  backup SHA `affd8f8e...` has source/backup integrity `ok`, schema 47; all 15
  contractors remain present.
- The first stopped-gateway Agency install failed closed before plugin staging
  because the Hermes plugin parent was group-writable mode `0775`. Artifact SHA
  `72c3a7ac...` and the prepared launcher SHA `7c033c97...` are retained; the
  native config SHA remained `a984d934...`.
- Changing only that parent to owner-private `0700` and using process umask
  `0077` satisfied the existing trust boundary. Agency-only install
  `06bd5aa2-c8c3-4321-90b2-e413a142c4a7` completed with bundle `351a7108...`,
  runtime `70239e65...`, launcher `7c033c97...`, and artifact `93857d15...`.
  The installer did not restart Hermes.
- Hermes's native model/provider, five fallbacks, environment-file hash, and
  nine prior plugins remain unchanged. Config SHA `95b87b7f...` represents
  only native enablement of `agency-preflight` with tool override false. Plugin
  doctor proves import/registration, eight hooks, and zero tools.
- The exact Nexus gateway service is active/running after native restart.
  Fresh status, harmless skill, and exact substantive configuration-drift
  Telegram evidence remain pending. Codex OAuth/config/canary, Claude, and
  ZCode remain untouched; no matrix cell moved.

### 2026-08-24 OpenClaw refreshed-header candidate checkpoint

- Fresh OpenClaw status is retained as failed run `a4b27543...`, trace
  `7e7a6318...`: Store row `3b9037a9...` recorded `openclaw-operations`, but
  the native final copied the stale `Skills loaded: none` snapshot and terminal
  `25cf1630...` correctly rejected it before Telegram delivery.
- Installed-host inspection proves OpenClaw's 4,000-character,
  zero-minimum proportional recovery projection truncated the separate
  878-character updated context beside a 100,000-character native read result.
  This is not a LiteLLM alias, Telegram ingress, or Store-attribution failure.
- The reviewed Agency-only candidate prefixes the refreshed context into the
  dominant first text block, uses UTF-16-safe 100,000-character splitting,
  preserves observed native content/details, and fails closed if the native
  200-block ceiling cannot admit the split.
- Expected-red and the rejected over-limit draft remain preserved. The final
  focused slice passes 251 tests with 1 intentional skip; the fast spine passes
  840 / 3 skips, and installed-contract review passes.
- Clean repair/ledger `d7187e80` / `456a75b7` is installed into stopped
  OpenClaw as operation `fa68e6a4...`; bundle `36619063...`, runtime
  `573a6a14...`, launcher SHA `d65af026...`. Store backups remain identical,
  integrity `ok`, schema 47, contractors 15. Native restart, 12 hooks, and both
  channels are green; OpenClaw changed only `meta.lastTouchedAt`. Hermes and
  protected hosts remain untouched. Fresh live response evidence is pending.

## Approach

Add a closed, bounded employment-contract v2 `execution_profile` containing
role-specific inspect-first checks, working principles, failure modes,
verification steps, and stop conditions. Inference returns these fields as
untrusted structured data, never as a raw prompt. The fixed compiler owns the
instruction syntax and renders a readable execution capsule containing only
worker-relevant material; closest-worker comparisons and selection evaluations
remain recruiter evidence and do not enter child context.

Retain exact v1 parsing and byte-identical v1 compilation for historical or
pending hiring evidence. New inference candidates and packaged contractors use
v2. Advance an already-installed packaged v1 contractor through an auditable,
idempotent package-owned amendment that preserves its worker identity, prior
version, lineage, outcomes, and rollback evidence.

Project dashboard evidence requirements from the exact active revision
metadata already retrieved with the specialist prompt. Do not widen the compact
whole-workforce recruiter contract merely to repair an owner detail view.

## Dependencies

- AR-122 owns governed structured hiring, fixed compilation, and lifecycle.
- AR-123 owns truthful CLI and dashboard workforce detail.
- ADR-0081 forbids unrestricted inference-authored executable prompts.
- ADR-0162 defines the data/compiler boundary and immutable upgrade path.

## Acceptance

- [x] Employment-contract v2 requires a closed, bounded execution profile and
      rejects control-channel prose, hidden controls, unknown fields, and
      generic empty guidance.
- [x] The current hiring inference asks for reusable role-specific execution
      data without adding another provider call or allowing raw prompt output.
- [x] Compiler v2 renders readable inspect, working-method, failure, evidence,
      and stop sections while excluding recruiter-only comparison/eval fields.
- [x] Historical employment-contract v1 evidence still parses and compiles to
      the exact prior prompt bytes and hashes, including both package version
      identities that shipped.
- [x] Packaged contractors carry reviewed execution profiles, and reinstalling
      over either exact v1 package identity advances them through immutable,
      auditable, idempotent lineage while preserving amended contract metadata.
- [x] Workforce detail and the dashboard show the active revision's real
      evidence requirements; `none recorded` appears only when none exist.
- [x] Focused contract, hiring, Store, dashboard API, and dashboard UI tests
      pass with Ruff and documentation validation.
- [x] Tracker issue #313 is created and linked after explicit authorization.
- [x] The repaired candidate is merged to main, migrates the owner Store from
      both shipped package-v1 identities, is freshly installed into Claude,
      Codex, ZCode, and the dashboard, and has exact dashboard/CLI parity.
- [ ] Fresh authenticated Claude, Codex, and ZCode tasks produce Store-backed
      parent headers and complete the bounded staffing, skill, hiring, and reuse
      smoke. OpenClaw and Hermes remain deferred to the Linux handoff.
