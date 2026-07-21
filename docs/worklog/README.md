---
title: Worklog
status: active
category: worklog
created: 2026-07-10
updated: 2026-07-21
tags: []
related: []
supersedes: []
superseded_by: null
---

# Worklog

This registry connects repository history to the roadmap and to optional detail records that preserve reasoning too large for a commit subject. Rows are chronological, and commit subjects are copied verbatim from Git.

## Ongoing policy

- Add every substantive commit to this registry with its short SHA, commit date, exact subject, related roadmap issue when known, and detail-file link when one exists.
- Add a detail file from [TEMPLATE.md](TEMPLATE.md) when a commit carries durable reasoning: approach, notable challenges, decisions or rejected alternatives, or follow-up work. Historical detail files are not backfilled; they begin going forward.
- A substantive commit must be indexed by an immediately following ledger update. A commit that changes only `docs/worklog/**` and the reciprocal commit cell in `docs/roadmap/README.md` must use the exact subject prefix `docs(worklog):` and is exempt from requiring its own row or detail file. No other paths are allowed. The updater and verifier recognize only this narrow exception, which allows the repository to return to a clean state without an infinite chain of ledger commits.
- Never rewrite a historical subject to remove a name or change its wording. Flag provenance-sensitive terms in the notes instead.
- Link only to records and tracker items for this repository. Do not add sibling-repository paths or dependencies.

## Commit index

<!-- worklog:start -->
| Short SHA | Date | Subject | Related issue | Detail |
|---|---|---|---|---|
| `5eb4de1` | 2026-07-08 | Add complexity tier to model header + fix post_api_request race condition | null | null |
| `cfc7d38` | 2026-07-08 | Fix dynamic model resolution: capture actual model from response, not SpendLogs | null | null |
| `886d6cf` | 2026-07-08 | Fix: post_tool_call hook captures specialist loads, not just skills | null | null |
| `2434f30` | 2026-07-08 | Wire portable agency_runtime into live Hermes plugin (Step 2-3 cutover) | null | null |
| `3b39f58` | 2026-07-09 | config-first secrets, doctor auth, packaging hardening, portability fixes | null | null |
| `c2d1274` | 2026-07-09 | fix: pre_llm_call always injects routing, pre_verify enforces specialist loading | null | null |
| `dc0be8d` | 2026-07-09 | feat: multi-provider fallback chain with config-first auth | null | null |
| `a7bba3a` | 2026-07-09 | feat: one-command install, on/off toggle, comprehensive README | null | null |
| `8f6d320` | 2026-07-09 | docs: add agency-runtime session handoff | null | null |
| `8b377b1` | 2026-07-09 | feat: harden agency runtime delegation evidence | null | null |
| `442b91a` | 2026-07-09 | chore: untrack generated code indexes | null | null |
| `3b24614` | 2026-07-09 | feat: harden yolo roster sync and specialist preflight | null | null |
| `42f6580` | 2026-07-10 | feat: add routing explain receipts | [AR-01](../roadmap/issue-AR-01-selection-explain-receipts.md) | null |
| `6dc35cd` | 2026-07-10 | fix: repair mcp finalization tool | null | null |
| `bb0c12d` | 2026-07-10 | fix: keep http finalize evidence on session id | null | null |
| `9e57cf1` | 2026-07-10 | fix: sanitize http server error responses | null | null |
| `4f477f6` | 2026-07-10 | fix: preserve delegate type errors | null | null |
| `3954d35` | 2026-07-10 | fix: bound cli delegation waits | null | null |
| `d9379f3` | 2026-07-10 | feat: add json delegate results | null | null |
| `2235d7e` | 2026-07-10 | fix: avoid shelling out for adapter availability | null | null |
| `901a880` | 2026-07-10 | fix: lower trivial_msg_threshold to 8 + persist nontrivial via store | null | null |
| `be4f52f` | 2026-07-10 | fix: trivial threshold, removed 'next'/'status' from trivial patterns, added DEFAULT orchestrators | null | null |
| `31443bc` | 2026-07-10 | feat: bundle full 16-action companion policy, add agency policy CLI, surface companions in route | null | null |
| `badb180` | 2026-07-10 | fix: DEFAULT companions load even for trivial messages (ping/ok/yes) | null | null |
| `63b75ee` | 2026-07-10 | Fix agency preflight host plugin wiring | null | null |
| `4d17668` | 2026-07-10 | docs: establish linked roadmap worklog and decision system | [AR-08](../roadmap/issue-AR-08-self-contained-documentation.md) | [detail](2026-07-10-4d17668-documentation-system.md) |
| `a896c81` | 2026-07-10 | fix: isolate generated plugin tests from user home | [AR-09](../roadmap/issue-AR-09-windows-test-isolation.md) | [detail](2026-07-10-a896c81-windows-test-isolation.md) |
| `17a62dd` | 2026-07-11 | feat: harden runtime and ship local operations dashboard | [AR-03](../roadmap/issue-AR-03-supported-host-integrations.md), [AR-04](../roadmap/issue-AR-04-runtime-controls.md), [AR-07](../roadmap/issue-AR-07-public-release-readiness.md), [AR-10](../roadmap/issue-AR-10-authoritative-runtime-evidence.md), [AR-11](../roadmap/issue-AR-11-routing-evaluation-and-performance.md), [AR-12](../roadmap/issue-AR-12-installed-operations-dashboard.md) | [detail](2026-07-11-17a62dd-production-readiness-refactor.md) |
| `d1275c3` | 2026-07-11 | feat: add optional dashboard service and config parity | [AR-11](../roadmap/issue-AR-11-routing-evaluation-and-performance.md), [AR-13](../roadmap/issue-AR-13-optional-dashboard-service-configuration.md) | [detail](2026-07-11-d1275c3-optional-dashboard-service-configuration.md) |
| `afdf8d1` | 2026-07-11 | docs: sync AR-13 tracker mapping | [AR-13](../roadmap/issue-AR-13-optional-dashboard-service-configuration.md) | null |
| `63ea805` | 2026-07-11 | feat: turn dashboard into a live signal observatory | [AR-14](../roadmap/issue-AR-14-live-signal-observatory.md) | [detail](2026-07-11-63ea805-live-signal-observatory.md) |
| `2515bfc` | 2026-07-12 | feat(runtime): complete cross-platform production hardening | [AR-02](../roadmap/issue-AR-02-specialist-coverage-gaps.md), [AR-03](../roadmap/issue-AR-03-supported-host-integrations.md), [AR-04](../roadmap/issue-AR-04-runtime-controls.md), [AR-05](../roadmap/issue-AR-05-guided-provider-configuration.md), [AR-06](../roadmap/issue-AR-06-cli-authenticated-judge-providers.md), [AR-07](../roadmap/issue-AR-07-public-release-readiness.md), [AR-09](../roadmap/issue-AR-09-windows-test-isolation.md), [AR-10](../roadmap/issue-AR-10-authoritative-runtime-evidence.md), [AR-11](../roadmap/issue-AR-11-routing-evaluation-and-performance.md), [AR-12](../roadmap/issue-AR-12-installed-operations-dashboard.md), [AR-13](../roadmap/issue-AR-13-optional-dashboard-service-configuration.md), [AR-14](../roadmap/issue-AR-14-live-signal-observatory.md), [AR-15](../roadmap/issue-AR-15-reliable-json-rejection-responses.md), [AR-16](../roadmap/issue-AR-16-linux-python-delegation-compatibility.md) | [detail](2026-07-12-2515bfc-cross-platform-production-hardening.md) |
| `e4a846d` | 2026-07-13 | feat(runtime): finish production hardening and release gates | [AR-02](../roadmap/issue-AR-02-specialist-coverage-gaps.md), [AR-03](../roadmap/issue-AR-03-supported-host-integrations.md), [AR-04](../roadmap/issue-AR-04-runtime-controls.md), [AR-05](../roadmap/issue-AR-05-guided-provider-configuration.md), [AR-06](../roadmap/issue-AR-06-cli-authenticated-judge-providers.md), [AR-07](../roadmap/issue-AR-07-public-release-readiness.md), [AR-09](../roadmap/issue-AR-09-windows-test-isolation.md), [AR-10](../roadmap/issue-AR-10-authoritative-runtime-evidence.md), [AR-11](../roadmap/issue-AR-11-routing-evaluation-and-performance.md), [AR-12](../roadmap/issue-AR-12-installed-operations-dashboard.md), [AR-13](../roadmap/issue-AR-13-optional-dashboard-service-configuration.md), [AR-14](../roadmap/issue-AR-14-live-signal-observatory.md), [AR-15](../roadmap/issue-AR-15-reliable-json-rejection-responses.md), [AR-16](../roadmap/issue-AR-16-linux-python-delegation-compatibility.md), [AR-17](../roadmap/issue-AR-17-production-hardening-portability.md) | [detail](2026-07-13-e4a846d-production-hardening-release-gates.md) |
| `a60b41c` | 2026-07-13 | fix(ci): preserve dependency audit without paid security | [AR-07](../roadmap/issue-AR-07-public-release-readiness.md), [AR-17](../roadmap/issue-AR-17-production-hardening-portability.md) | [detail](2026-07-13-a60b41c-dependency-review-fallback.md) |
| `852359d` | 2026-07-13 | fix(ci): harden hosted cross-platform verification | [AR-07](../roadmap/issue-AR-07-public-release-readiness.md), [AR-09](../roadmap/issue-AR-09-windows-test-isolation.md), [AR-16](../roadmap/issue-AR-16-linux-python-delegation-compatibility.md), [AR-17](../roadmap/issue-AR-17-production-hardening-portability.md) | [detail](2026-07-13-852359d-hosted-cross-platform-verification.md) |
| `c7e06fd` | 2026-07-13 | fix(ci): close final hosted portability gaps | [AR-07](../roadmap/issue-AR-07-public-release-readiness.md), [AR-09](../roadmap/issue-AR-09-windows-test-isolation.md), [AR-16](../roadmap/issue-AR-16-linux-python-delegation-compatibility.md), [AR-17](../roadmap/issue-AR-17-production-hardening-portability.md), [AR-18](../roadmap/issue-AR-18-work-unit-paths-with-spaces.md) | [detail](2026-07-13-c7e06fd-final-hosted-portability.md) |
| `a096236` | 2026-07-13 | fix(runtime): close hosted portability and overload gaps | [AR-07](../roadmap/issue-AR-07-public-release-readiness.md), [AR-16](../roadmap/issue-AR-16-linux-python-delegation-compatibility.md), [AR-17](../roadmap/issue-AR-17-production-hardening-portability.md), [AR-18](../roadmap/issue-AR-18-work-unit-paths-with-spaces.md), [AR-19](../roadmap/issue-AR-19-bounded-overload-responses.md) | [detail](2026-07-13-a096236-hosted-portability-overload.md) |
| `26fd65a` | 2026-07-13 | fix(runtime): close final hosted Windows and ledger gaps | [AR-07](../roadmap/issue-AR-07-public-release-readiness.md), [AR-16](../roadmap/issue-AR-16-linux-python-delegation-compatibility.md), [AR-17](../roadmap/issue-AR-17-production-hardening-portability.md), [AR-20](../roadmap/issue-AR-20-full-history-ledger-ci.md), [AR-21](../roadmap/issue-AR-21-fully-resume-windows-children.md), [AR-22](../roadmap/issue-AR-22-concurrent-storage-acl-repair.md) | [detail](2026-07-13-26fd65a-final-hosted-windows-ledgers.md) |
| `11387ad` | 2026-07-13 | test(ci): stabilize hosted Windows PowerShell gate | [AR-17](../roadmap/issue-AR-17-production-hardening-portability.md), [AR-23](../roadmap/issue-AR-23-hosted-windows-powershell-gate.md) | [detail](2026-07-13-11387ad-hosted-windows-powershell-gate.md) |
| `d9f6d37` | 2026-07-13 | fix(evidence): stabilize same-timestamp event order | [AR-17](../roadmap/issue-AR-17-production-hardening-portability.md), [AR-24](../roadmap/issue-AR-24-deterministic-evidence-ordering.md) | [detail](2026-07-13-d9f6d37-deterministic-evidence-ordering.md) |
| `5515757` | 2026-07-14 | Merge pull request #18 from Holeshot-Software-LLC/codex/production-readiness-dashboard | [AR-07](../roadmap/issue-AR-07-public-release-readiness.md), [AR-16](../roadmap/issue-AR-16-linux-python-delegation-compatibility.md), [AR-17](../roadmap/issue-AR-17-production-hardening-portability.md), [AR-18](../roadmap/issue-AR-18-work-unit-paths-with-spaces.md), [AR-19](../roadmap/issue-AR-19-bounded-overload-responses.md), [AR-20](../roadmap/issue-AR-20-full-history-ledger-ci.md), [AR-21](../roadmap/issue-AR-21-fully-resume-windows-children.md), [AR-22](../roadmap/issue-AR-22-concurrent-storage-acl-repair.md), [AR-23](../roadmap/issue-AR-23-hosted-windows-powershell-gate.md), [AR-24](../roadmap/issue-AR-24-deterministic-evidence-ordering.md) | [detail](2026-07-14-5515757-pr-18-merge.md) |
| `6756b87` | 2026-07-14 | docs(roadmap): reconcile merged release state | [AR-07](../roadmap/issue-AR-07-public-release-readiness.md), [AR-16](../roadmap/issue-AR-16-linux-python-delegation-compatibility.md), [AR-17](../roadmap/issue-AR-17-production-hardening-portability.md), [AR-18](../roadmap/issue-AR-18-work-unit-paths-with-spaces.md), [AR-19](../roadmap/issue-AR-19-bounded-overload-responses.md), [AR-20](../roadmap/issue-AR-20-full-history-ledger-ci.md), [AR-21](../roadmap/issue-AR-21-fully-resume-windows-children.md), [AR-22](../roadmap/issue-AR-22-concurrent-storage-acl-repair.md), [AR-23](../roadmap/issue-AR-23-hosted-windows-powershell-gate.md), [AR-24](../roadmap/issue-AR-24-deterministic-evidence-ordering.md) | [detail](2026-07-14-6756b87-post-merge-reconciliation.md) |
| `e5f4a8c` | 2026-07-18 | feat(runtime): harden dynamic agency orchestration | [AR-25 through AR-97](../roadmap/README.md) | [detail](2026-07-18-e5f4a8c-dynamic-agency-hardening.md) |
| `a022b5d` | 2026-07-18 | fix(dashboard): validate installed control identity | [AR-98](../roadmap/issue-AR-98-validate-dashboard-service-launcher-status.md), [AR-99](../roadmap/issue-AR-99-dashboard-broker-materialized-master-control.md) | [detail](2026-07-18-a022b5d-dashboard-control-identity.md) |
| `cbe9bc9` | 2026-07-18 | fix(runtime): harden installed control transitions | [AR-89](../roadmap/issue-AR-89-operational-roster-inference-parity.md), [AR-100](../roadmap/issue-AR-100-wait-for-windows-dashboard-runtime-exit.md), [AR-101](../roadmap/issue-AR-101-enforce-restricted-global-master-switch.md) | [detail](2026-07-18-cbe9bc9-installed-control-transitions.md) |
| `c8ebbfa` | 2026-07-19 | test(runtime): cover defensive control branches | [AR-100](../roadmap/issue-AR-100-wait-for-windows-dashboard-runtime-exit.md), [AR-101](../roadmap/issue-AR-101-enforce-restricted-global-master-switch.md) | [detail](2026-07-19-c8ebbfa-defensive-control-coverage.md) |
| `3ded6a4` | 2026-07-19 | test(dashboard): cover delegation plan fallback | [AR-89](../roadmap/issue-AR-89-operational-roster-inference-parity.md) | null |
| `164188b` | 2026-07-19 | fix(roster): reconcile legacy bundled contracts | [AR-82](../roadmap/issue-AR-82-full-roster-unit-routing.md), [AR-84](../roadmap/issue-AR-84-bounded-semantic-agent-cards.md), [AR-86](../roadmap/issue-AR-86-govern-complete-upstream-roster-lifecycle.md), [AR-87](../roadmap/issue-AR-87-bounded-native-delegation-plans.md), [AR-91](../roadmap/issue-AR-91-enforce-governed-roster-activation.md), [AR-92](../roadmap/issue-AR-92-redact-roster-source-credentials.md), [AR-102](../roadmap/issue-AR-102-refresh-legacy-bundled-roster-contracts.md) | [detail](2026-07-19-164188b-legacy-bundled-contract-reconciliation.md) |
| `664fcf1` | 2026-07-19 | test(ci): import Windows ctypes types portably | [AR-103](../roadmap/issue-AR-103-import-windows-ctypes-fixtures-portably.md) | [detail](2026-07-19-664fcf1-portable-windows-ctypes-fixtures.md) |
| `11a2c86` | 2026-07-19 | fix(runtime): close ingestion and hosted portability gaps | [AR-86](../roadmap/issue-AR-86-govern-complete-upstream-roster-lifecycle.md), [AR-95](../roadmap/issue-AR-95-bind-remediation-resolution-authority-to-complete-durable-evidence.md), [AR-102](../roadmap/issue-AR-102-refresh-legacy-bundled-roster-contracts.md), [AR-103](../roadmap/issue-AR-103-import-windows-ctypes-fixtures-portably.md), [AR-104](../roadmap/issue-AR-104-run-hosted-portability-gates-in-trusted-boundaries.md) | [detail](2026-07-19-11a2c86-governed-ingestion-portability.md) |
| `0df5050` | 2026-07-19 | fix(ci): harden hosted runtime portability | [AR-104](../roadmap/issue-AR-104-run-hosted-portability-gates-in-trusted-boundaries.md) | [detail](2026-07-19-0df5050-hosted-runtime-portability.md) |
| `0c41fbd` | 2026-07-19 | fix(ci): preserve durable hosted runtime authority | [AR-104](../roadmap/issue-AR-104-run-hosted-portability-gates-in-trusted-boundaries.md) | [detail](2026-07-19-0c41fbd-durable-hosted-runtime-authority.md) |
| `89576f0` | 2026-07-19 | fix(windows): report protected root receipt failures | [AR-104](../roadmap/issue-AR-104-run-hosted-portability-gates-in-trusted-boundaries.md) | null |
| `07de83c` | 2026-07-19 | fix(windows): accept protected canonical ACL receipts | [AR-104](../roadmap/issue-AR-104-run-hosted-portability-gates-in-trusted-boundaries.md) | null |
| `a1c6744` | 2026-07-19 | fix(windows): classify canonical ACL receipt failures | [AR-104](../roadmap/issue-AR-104-run-hosted-portability-gates-in-trusted-boundaries.md) | null |
| `31516d1` | 2026-07-19 | fix(windows): scope trusted bootstrap root ownership | [AR-104](../roadmap/issue-AR-104-run-hosted-portability-gates-in-trusted-boundaries.md) | [detail](2026-07-19-31516d1-scope-windows-bootstrap-ownership.md) |
| `b05b180` | 2026-07-19 | fix(windows): normalize hosted private root ownership | [AR-104](../roadmap/issue-AR-104-run-hosted-portability-gates-in-trusted-boundaries.md) | [detail](2026-07-19-b05b180-normalize-hosted-private-root-ownership.md) |
| `361962f` | 2026-07-19 | fix(windows): normalize private executable owner identity | [AR-104](../roadmap/issue-AR-104-run-hosted-portability-gates-in-trusted-boundaries.md) | [detail](2026-07-19-361962f-normalize-private-executable-owner-identity.md) |
| `9400f76` | 2026-07-19 | fix(codex): report all installed hook events | [AR-105](../roadmap/issue-AR-105-current-codex-hook-event-count.md) | [detail](2026-07-19-9400f76-report-all-installed-hook-events.md) |
| `3f9eb96` | 2026-07-19 | fix(dashboard): redact failed manager probe output | [AR-38](../roadmap/issue-AR-38-dashboard-service-environment-durability.md) | [detail](2026-07-19-3f9eb96-redact-failed-manager-probe-output.md) |
| `22434e8` | 2026-07-19 | fix(mcp): validate injected Store identities | [AR-47](../roadmap/issue-AR-47-freeze-store-config-identity-at-construction.md), [AR-48](../roadmap/issue-AR-48-enforce-strict-schema-on-config-read.md) | [detail](2026-07-19-22434e8-validate-injected-store-identities.md) |
| `fdaad17` | 2026-07-19 | docs: reconcile runtime identity and routing contracts | [AR-36](../roadmap/issue-AR-36-config-relative-runtime-paths.md), [AR-46](../roadmap/issue-AR-46-bind-routing-to-store-config-identity.md), [AR-58](../roadmap/issue-AR-58-unit-aware-delegation-assignment.md), [AR-81](../roadmap/issue-AR-81-conflict-safe-direct-context.md) | [detail](2026-07-19-fdaad17-reconcile-runtime-identity-routing-contracts.md) |
| `987c32a` | 2026-07-19 | fix(portability): close Windows ingestion and CI gaps | [AR-104](../roadmap/issue-AR-104-run-hosted-portability-gates-in-trusted-boundaries.md), [AR-106](../roadmap/issue-AR-106-portable-windows-policy-and-posix-simulations.md) | [detail](2026-07-19-987c32a-windows-ingestion-portability.md) |
| `be4b3ff` | 2026-07-19 | Merge pull request #104 from Holeshot-Software-LLC/codex/turn-scoped-agency-lifecycle | null | null |
| `46f203a` | 2026-07-20 | fix(release): build artifacts from canonical Git blobs | [AR-107](../roadmap/issue-AR-107-build-release-artifacts-from-canonical-git-blobs.md), [AR-108](../roadmap/issue-AR-108-atomic-owned-process-containment.md) | [detail](2026-07-20-46f203a-canonical-release-source.md) |
| `bb8ce93` | 2026-07-20 | fix(portability): harden hosted release proofs | [AR-107](../roadmap/issue-AR-107-build-release-artifacts-from-canonical-git-blobs.md), [AR-108](../roadmap/issue-AR-108-atomic-owned-process-containment.md) | [detail](2026-07-20-bb8ce93-hosted-release-portability.md) |
| `9f98db3` | 2026-07-20 | fix(release): canonicalize generated metadata | [AR-107](../roadmap/issue-AR-107-build-release-artifacts-from-canonical-git-blobs.md) | [detail](2026-07-20-9f98db3-generated-metadata-canonicalization.md) |
| `3515d4e` | 2026-07-20 | fix(release): verify backend manifest order | [AR-107](../roadmap/issue-AR-107-build-release-artifacts-from-canonical-git-blobs.md) | [detail](2026-07-20-3515d4e-backend-manifest-order.md) |
| `9843025` | 2026-07-20 | test(portability): make process fixtures race-free | [AR-109](../roadmap/issue-AR-109-hosted-process-security-test-fidelity.md) | [detail](2026-07-20-9843025-process-fixture-fidelity.md) |
| `4dccae7` | 2026-07-20 | fix(preflight): preserve lease safety margin | [AR-109](../roadmap/issue-AR-109-hosted-process-security-test-fidelity.md) | [detail](2026-07-20-4dccae7-store-clock-portability.md) |
| `e6e1b25` | 2026-07-20 | Merge pull request #111 from Holeshot-Software-LLC/codex/canonical-release-source | [AR-107](../roadmap/issue-AR-107-build-release-artifacts-from-canonical-git-blobs.md) | null |
| `0f374b4` | 2026-07-20 | fix(dashboard): preserve WSL systemd config trust | [AR-110](../roadmap/issue-AR-110-preserve-wsl-systemd-service-trust.md) | [detail](2026-07-20-0f374b4-wsl-systemd-config-trust.md) |
| `615d88c` | 2026-07-20 | fix(canary): bind isolated runs to global mode | [AR-111](../roadmap/issue-AR-111-honor-global-mode-in-isolated-canaries.md), [AR-88](../roadmap/issue-AR-88-compare-agency-native-outcomes.md) | [detail](2026-07-20-615d88c-isolated-canary-modes.md) |
| `f5fe972` | 2026-07-20 | fix(canary): bind hook control capability | [AR-111](../roadmap/issue-AR-111-honor-global-mode-in-isolated-canaries.md) | [detail](2026-07-20-f5fe972-hook-control-capability.md) |
| `b8f80bd` | 2026-07-20 | fix(hooks): bind authoritative master control | [AR-111](../roadmap/issue-AR-111-honor-global-mode-in-isolated-canaries.md) | [detail](2026-07-20-b8f80bd-authoritative-hook-control.md) |
| `cb17e0d` | 2026-07-20 | test(portability): normalize hook control contracts | [AR-111](../roadmap/issue-AR-111-honor-global-mode-in-isolated-canaries.md) | [detail](2026-07-20-cb17e0d-portable-hook-control-tests.md) |
| `123910a` | 2026-07-20 | test(coverage): exercise hook control rejection paths | [AR-111](../roadmap/issue-AR-111-honor-global-mode-in-isolated-canaries.md) | [detail](2026-07-20-123910a-hook-control-coverage.md) |
| `edb922c` | 2026-07-20 | docs(roadmap): complete isolated canary control | [AR-111](../roadmap/issue-AR-111-honor-global-mode-in-isolated-canaries.md) | [detail](2026-07-20-edb922c-complete-isolated-canary-control.md) |
| `a869e51` | 2026-07-20 | Merge pull request #114 from Holeshot-Software-LLC/codex/wsl-private-tmp-namespace | [AR-79 through AR-85, AR-88, AR-89, AR-107, AR-109 through AR-111](../roadmap/README.md) | [detail](2026-07-20-a869e51-pr-114-merge.md) |
| `55c4dfe` | 2026-07-20 | docs(roadmap): close merged readiness gates | [AR-79 through AR-85, AR-88, AR-89, AR-107, AR-109, AR-110](../roadmap/README.md) | [detail](2026-07-20-55c4dfe-final-readiness-reconciliation.md) |
| `4635a0b` | 2026-07-20 | docs: rewrite README for public users | [AR-112](../roadmap/issue-AR-112-public-user-readme.md) | [detail](2026-07-20-4635a0b-public-readme.md) |
| `de875f6` | 2026-07-20 | docs(roadmap): track public README rewrite | [AR-112](../roadmap/issue-AR-112-public-user-readme.md) | null |
| `280b0b7` | 2026-07-20 | Merge pull request #116 from Holeshot-Software-LLC/codex/pr114-merge-ledger | [AR-79 through AR-85, AR-88, AR-89, AR-107, AR-109, AR-110, AR-112](../roadmap/README.md) | [detail](2026-07-20-280b0b7-pr-116-merge.md) |
| `9d4e55b` | 2026-07-20 | fix(ci): isolate wall-clock performance gates | [AR-113](../roadmap/issue-AR-113-isolate-performance-gates.md) | [detail](2026-07-20-9d4e55b-isolate-performance-gates.md) |
| `c994882` | 2026-07-20 | docs(roadmap): complete performance gate isolation | [AR-113](../roadmap/issue-AR-113-isolate-performance-gates.md) | null |
| `a751046` | 2026-07-20 | Merge pull request #121 from Holeshot-Software-LLC/codex/performance-gate-isolation | [AR-113](../roadmap/issue-AR-113-isolate-performance-gates.md) | [detail](2026-07-20-a751046-pr-121-merge.md) |
| `58026a5` | 2026-07-20 | fix(installer): require verified Codex hook activation | null | null |
| `527659d` | 2026-07-20 | Merge pull request #124 from Holeshot-Software-LLC/codex/ar-114-guided-codex-activation | null | null |
| `7e24323` | 2026-07-21 | fix(installer): identify Codex terminal hook review | null | null |
| `5d2bafb` | 2026-07-21 | Merge pull request #125 from Holeshot-Software-LLC/codex/ar-114-codex-tui-hook-trust | null | null |
| `5467026` | 2026-07-21 | docs(roadmap): record verified Codex hook activation | null | null |
| `0d892e8` | 2026-07-21 | Merge pull request #126 from Holeshot-Software-LLC/codex/ar-114-activation-proof | null | null |
| `673988d` | 2026-07-21 | feat(routing): bound native child inference and expose account models | [AR-115](../roadmap/issue-AR-115-live-routing-trust.md), [AR-116](../roadmap/issue-AR-116-bound-child-routing-and-oauth-model-selection.md) | [detail](2026-07-21-673988d-bound-native-child-routing.md) |
| `49e8f99` | 2026-07-21 | fix(routing): bound child inference and parallelize CI | [AR-115](../roadmap/issue-AR-115-live-routing-trust.md), [AR-116](../roadmap/issue-AR-116-bound-child-routing-and-oauth-model-selection.md), [AR-117](../roadmap/issue-AR-117-parallelize-pr-verification.md) | [detail](2026-07-21-49e8f99-review-fixes-and-parallel-ci.md) |
| `e0870fa` | 2026-07-21 | test(coverage): cover model cache waiter reuse | [AR-116](../roadmap/issue-AR-116-bound-child-routing-and-oauth-model-selection.md), [AR-117](../roadmap/issue-AR-117-parallelize-pr-verification.md) | null |
| `1b28e89` | 2026-07-21 | test(delegation): allow concurrent unit completion order | [AR-116](../roadmap/issue-AR-116-bound-child-routing-and-oauth-model-selection.md), [AR-117](../roadmap/issue-AR-117-parallelize-pr-verification.md) | null |
| `e2cb50d` | 2026-07-21 | test(routing): cover child coalescing timeout | [AR-116](../roadmap/issue-AR-116-bound-child-routing-and-oauth-model-selection.md), [AR-117](../roadmap/issue-AR-117-parallelize-pr-verification.md) | null |
| `6f97dcc` | 2026-07-21 | ci: defer full compatibility matrix to main | [AR-117](../roadmap/issue-AR-117-parallelize-pr-verification.md) | null |
| `aefeb28` | 2026-07-21 | ci: validate PR ledgers at canonical head | [AR-117](../roadmap/issue-AR-117-parallelize-pr-verification.md) | null |
| `afd7199` | 2026-07-21 | style(ci): format workflow contract assertion | [AR-117](../roadmap/issue-AR-117-parallelize-pr-verification.md) | null |
| `795deef` | 2026-07-21 | fix(routing): enforce safe selection and child evidence | [AR-115](../roadmap/issue-AR-115-live-routing-trust.md), [AR-116](../roadmap/issue-AR-116-bound-child-routing-and-oauth-model-selection.md), [AR-118](../roadmap/issue-AR-118-reconcile-native-child-activation-evidence.md) | null |
| `0b21bdb` | 2026-07-21 | test(routing): cover recovery edge paths | [AR-115](../roadmap/issue-AR-115-live-routing-trust.md), [AR-116](../roadmap/issue-AR-116-bound-child-routing-and-oauth-model-selection.md) | null |
<!-- worklog:end -->

## Provenance notes

- `2434f30` contains the name `Hermes` in its historical subject. The subject is retained exactly as committed for faithful provenance; the name does not create an active cross-repository link or dependency.
- `8f6d320` records a handoff document that was later removed. The subject remains part of the immutable commit record; no deleted document was restored for this worklog.
