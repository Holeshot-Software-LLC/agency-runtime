---
title: "AR-404 backlog inventory at delivery checkpoint"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [backlog, inventory, planning]
related:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/README.md
  - docs/roadmap/AR-256-done-acceptance-reconciliation.md
supersedes: []
superseded_by: null
---

# Backlog inventory, 2026-09-05

Read-only inventory of canonical issue front matter at 559b08eb, before
completion of AR-400 through AR-403 and before adding AR-404 itself.
155 unfinished records: 56 open and 99 in_progress. Priorities: 105 p0, 39 p1,
eight p2 and three p3. Priority labels alone therefore do not order this work.
Five have acceptance files at this checkpoint (AR-370, AR-393 and the three new
builder records); existence is not a passing verdict. The first audit, before
those three builder files, found only two. Blank tracker front matter often
belongs to the closed pre-tracker historical allowlist: use verify_tracker,
not a naive count, to identify parity defects.

The table is a complete inventory, not 155 claims of independent live bugs.
Checked boxes are historical source assertions, not fresh acceptance judgments.
Related/superseding records and accepted decision chains must be checked before
changing behavior. Do not implement an obsolete proposal merely to close it.

## Delivery lanes

| Lane | Count | Next action before closure |
|---|---:|---|
| A: current review delivery | 4 | Finish exact-candidate acceptance, preserve native operator blockers |
| B: security and hiring invariants | 18 | Reproduce against current code, pin fail-closed expectations, fix or cite superseding implementation |
| C: staffing quality and performance | 33 | Map implementation/evidence; run representative no-gap/gap and parent/child quality/latency cases |
| D: native hosts, installation and provider plumbing | 51 | Separate code defects from trust, restart, platform and live-proof requirements |
| E: release and test infrastructure | 20 | Reconcile with current release policy; platform evidence requires its actual platform |
| F: dashboard, operations and product | 29 | Verify the exact visible outcome and remaining acceptance, then implement the smallest missing slice |

## Complete unfinished inventory

| Issue | Title | Status | Priority | Lane | Checked / criteria | Acceptance file |
|---|---|---|---|---|---|---|
| [AR-115](issue-AR-115-live-routing-trust.md) | AR-115: Make live routing and Agency headers trustworthy | open | p0 | C | 9/12 | none |
| [AR-119](issue-AR-119-inference-first-workforce.md) | AR-119: Implement inference-first real-time workforce and contractor lifecycle | in_progress | p0 | C | 6/39 | none |
| [AR-120](issue-AR-120-normalized-workforce-recruitment-index.md) | AR-120: Normalize and audit the complete workforce recruitment index | open | p0 | C | 0/4 | none |
| [AR-125](issue-AR-125-workforce-and-one-shot-evaluation.md) | AR-125: Prove workforce selection, host portability, and Agency-on/off value | open | p0 | C | 3/6 | none |
| [AR-127](issue-AR-127-zcode-stop-rejection-shape.md) | AR-127: Make ZCode Stop rejections actually block | open | p0 | D | 0/0 | none |
| [AR-129](issue-AR-129-isolate-subprocess-environments.md) | AR-129: Isolate subprocess environments | open | p0 | B | 0/0 | none |
| [AR-130](issue-AR-130-revalidate-store-trust.md) | AR-130: Revalidate Store trust at authoritative boundaries | open | p0 | B | 0/0 | none |
| [AR-131](issue-AR-131-complete-mcp-cli-host-contracts.md) | AR-131: Complete MCP and CLI host contracts | open | p0 | D | 0/0 | none |
| [AR-132](issue-AR-132-hire-deterministic-safe-gaps.md) | AR-132: Hire deterministic safe staffing gaps | open | p0 | C | 0/0 | none |
| [AR-135](issue-AR-135-complete-zcode-integration.md) | AR-135: Complete ZCode native integration end to end | open | p0 | D | 0/0 | none |
| [AR-138](issue-AR-138-coherent-observable-dashboard-ui.md) | AR-138: Make dashboard refresh coherent, accessible, and observable | open | p1 | F | 0/0 | none |
| [AR-139](issue-AR-139-restore-release-asset-budget.md) | AR-139: Restore the installed release asset budget | open | p0 | E | 0/0 | none |
| [AR-140](issue-AR-140-scale-routing-and-retrieval.md) | AR-140: Scale routing, retrieval, and CLI startup | open | p1 | C | 0/0 | none |
| [AR-145](issue-AR-145-restore-python-release-coverage.md) | AR-145: Restore the Python release coverage gate | open | p0 | E | 0/0 | none |
| [AR-147](issue-AR-147-parse-complete-windows-acl-descriptors.md) | AR-147: Parse complete Windows ACL descriptors | open | p0 | B | 0/0 | none |
| [AR-148](issue-AR-148-fail-malformed-remediation-signatures-closed.md) | AR-148: Fail malformed remediation signatures closed | open | p1 | B | 0/0 | none |
| [AR-149](issue-AR-149-fresh-dashboard-request-ids.md) | AR-149: Issue a fresh dashboard request ID per HTTP request | open | p0 | F | 0/0 | none |
| [AR-150](issue-AR-150-coordinate-dashboard-refresh-epochs.md) | AR-150: Coordinate dashboard refresh commit epochs | open | p0 | F | 0/0 | none |
| [AR-151](issue-AR-151-align-route-lab-host-eligibility.md) | AR-151: Align Route Lab host eligibility with the server | open | p1 | F | 0/0 | none |
| [AR-152](issue-AR-152-bound-dashboard-live-listeners.md) | AR-152: Bound dashboard live-listener retention | open | p1 | C | 0/0 | none |
| [AR-153](issue-AR-153-complete-worker-detail-evidence.md) | AR-153: Complete and bound worker-detail evidence | open | p1 | F | 0/0 | none |
| [AR-154](issue-AR-154-fail-malformed-initial-pages-closed.md) | AR-154: Fail malformed initial dashboard pages closed | open | p1 | F | 0/0 | none |
| [AR-155](issue-AR-155-bound-dashboard-hiring-evidence.md) | AR-155: Bound dashboard hiring evidence delivery | open | p1 | F | 0/0 | none |
| [AR-156](issue-AR-156-restore-cost-bounded-verification.md) | AR-156: Restore cost-bounded verification feedback | open | p1 | E | 0/0 | none |
| [AR-157](issue-AR-157-quiet-public-http-disconnects.md) | AR-157: Treat public HTTP client disconnects as transport completion | open | p1 | F | 0/0 | none |
| [AR-158](issue-AR-158-disambiguate-multi-surface-observation-tests.md) | AR-158: Disambiguate multi-surface observation test evidence | open | p1 | F | 0/0 | none |
| [AR-159](issue-AR-159-enforce-production-branch-protection.md) | AR-159: Enforce production branch protection | open | p0 | E | 0/0 | none |
| [AR-160](issue-AR-160-publish-platform-honest-native-release-artifacts.md) | AR-160: Publish platform-honest native release artifacts | in_progress | p0 | E | 9/10 | none |
| [AR-162](issue-AR-162-collapse-unavailable-codeql-fanout.md) | AR-162: Collapse unavailable CodeQL fanout | open | p1 | E | 0/0 | none |
| [AR-163](issue-AR-163-reopen-stale-remediation-authority.md) | AR-163: Reopen stale remediation resolution authority | in_progress | p1 | B | 0/0 | none |
| [AR-164](issue-AR-164-reject-repository-ancestor-path-poisoning.md) | AR-164: Reject repository-ancestor PATH poisoning | in_progress | p0 | B | 7/7 | none |
| [AR-165](issue-AR-165-fail-ambiguous-dependency-review-capability-closed.md) | AR-165: Fail ambiguous dependency-review capability probes closed | in_progress | p0 | B | 0/0 | none |
| [AR-166](issue-AR-166-truthful-dashboard-disclosure-and-correlation.md) | AR-166: Keep dashboard disclosure and correlation truthful | in_progress | p2 | F | 0/0 | none |
| [AR-167](issue-AR-167-normalize-windows-release-source-modes.md) | AR-167: Normalize Windows release-source modes | in_progress | p0 | E | 4/6 | none |
| [AR-168](issue-AR-168-rebuild-canonical-sdist-source-manifest.md) | AR-168: Rebuild the canonical sdist source manifest | in_progress | p0 | E | 3/5 | none |
| [AR-169](issue-AR-169-exclude-native-pe-from-portable-wheel.md) | AR-169: Exclude the native PE from portable wheels | in_progress | p0 | E | 3/6 | none |
| [AR-170](issue-AR-170-fail-dashboard-response-correlation-closed.md) | AR-170: Fail dashboard response correlation closed | in_progress | p1 | B | 8/9 | none |
| [AR-171](issue-AR-171-redact-dashboard-lifecycle-reasons.md) | AR-171: Redact dashboard lifecycle reasons | in_progress | p1 | B | 5/6 | none |
| [AR-172](issue-AR-172-make-roster-pages-snapshot-consistent.md) | AR-172: Make roster pages snapshot-consistent | in_progress | p1 | F | 6/7 | none |
| [AR-173](issue-AR-173-correlate-route-lab-observations.md) | AR-173: Correlate Route Lab observations | in_progress | p1 | F | 4/5 | none |
| [AR-174](issue-AR-174-short-circuit-docs-only-ci.md) | AR-174: Short-circuit documentation-only CI | in_progress | p1 | E | 6/8 | none |
| [AR-175](issue-AR-175-retire-dashboard-control-fallback.md) | AR-175: Retire the non-atomic dashboard control fallback | in_progress | p1 | B | 5/6 | none |
| [AR-176](issue-AR-176-align-full-gate-contract-fixtures.md) | AR-176: Align full-gate fixtures with hardened runtime contracts | in_progress | p0 | E | 7/8 | none |
| [AR-177](issue-AR-177-make-exhaustive-python-ci-manual.md) | AR-177: Make exhaustive Python CI manual | in_progress | p0 | E | 5/7 | none |
| [AR-178](issue-AR-178-evaluate-one-shot-applications-post-production.md) | AR-178: Evaluate complete one-shot applications after production launch | open | p2 | E | 1/6 | none |
| [AR-180](issue-AR-180-prove-codex-specialist-activation-canary.md) | AR-180: Prove Codex specialist activation in the live canary | open | p0 | D | 6/12 | none |
| [AR-181](issue-AR-181-bound-all-host-smoke-launcher-preparation.md) | AR-181: Bound all-host smoke launcher preparation | in_progress | p1 | E | 0/0 | none |
| [AR-183](issue-AR-183-normalize-private-posix-wheel-modes.md) | AR-183: Normalize owner-private POSIX wheel modes | in_progress | p0 | E | 3/5 | none |
| [AR-184](issue-AR-184-normalize-private-posix-sdist-modes.md) | AR-184: Normalize owner-private POSIX sdist modes | in_progress | p0 | E | 4/6 | none |
| [AR-185](issue-AR-185-bind-codex-activation-verification.md) | AR-185: Bind Codex activation verification to a fresh exact proof | in_progress | p0 | B | 8/9 | none |
| [AR-187](issue-AR-187-isolate-native-host-lifecycle-cwd.md) | AR-187: Isolate native host lifecycle commands from the caller CWD | in_progress | p0 | D | 5/6 | none |
| [AR-189](issue-AR-189-add-owned-host-integration-uninstall.md) | AR-189: Add ownership-bound host-integration uninstall | in_progress | p0 | D | 0/12 | none |
| [AR-190](issue-AR-190-make-upgrade-plans-runnable-in-uv-tools.md) | AR-190: Make attended upgrade plans runnable in uv tools | in_progress | p0 | E | 4/5 | none |
| [AR-191](issue-AR-191-support-codex-v2-hook-identity.md) | AR-191: Support the Codex V2 native-spawn hook identity | in_progress | p0 | D | 8/9 | none |
| [AR-192](issue-AR-192-fail-fast-on-codex-hook-trust-drift.md) | AR-192: Fail fast on Codex hook trust drift | in_progress | p0 | D | 5/6 | none |
| [AR-193](issue-AR-193-preserve-authoritative-windows-master-reads.md) | AR-193: Preserve authoritative Windows master reads for UAC-filtered owners | in_progress | p0 | B | 4/5 | none |
| [AR-194](issue-AR-194-inspect-owned-service-runtimes-across-python-versions.md) | AR-194: Inspect owned service runtimes across Python versions | in_progress | p1 | F | 4/5 | none |
| [AR-195](issue-AR-195-separate-codex-canary-parent-and-child-goals.md) | AR-195: Separate Codex canary parent and child goals | in_progress | p0 | D | 5/7 | none |
| [AR-197](issue-AR-197-remove-agency-owned-windows-hello.md) | AR-197: Remove Agency-owned Windows Hello | in_progress | p0 | B | 5/6 | none |
| [AR-199](issue-AR-199-restore-codex-workforce-evidence.md) | AR-199: Restore Codex workforce selection and evidence | in_progress | p0 | C | 25/28 | none |
| [AR-200](issue-AR-200-diagnosable-decision-conformance.md) | AR-200: Make workforce decisions diagnosable and mutation-conformant | in_progress | p0 | C | 13/18 | none |
| [AR-201](issue-AR-201-fund-default-workforce-repair.md) | AR-201: Fund the default workforce repair path | in_progress | p0 | C | 10/15 | none |
| [AR-207](issue-AR-207-persist-preflight-delegation-failure-diagnostics.md) | AR-207: Persist preflight and delegation failure diagnostics | in_progress | p0 | F | 11/18 | none |
| [AR-208](issue-AR-208-preserve-codex-host-notices-in-product-evidence.md) | AR-208: Preserve exact Codex host notices in product evidence | in_progress | p0 | F | 7/11 | none |
| [AR-209](issue-AR-209-bind-opaque-codex-child-launches.md) | AR-209: Bind opaque Codex child launches to exact plan rows | in_progress | p0 | E | 11/23 | none |
| [AR-235](issue-AR-235-autonomous-gap-hiring-with-isolated-security-review.md) | AR-235: Make gap contractor hiring autonomous with isolated security review and amend-first staffing | open | p0 | C | 0/12 | none |
| [AR-236](issue-AR-236-achieve-full-cli-dashboard-parity.md) | AR-236: Achieve full CLI and dashboard functional and presentational parity | open | p0 | F | 10/25 | none |
| [AR-250](issue-AR-250-upgrade-flow-parity.md) | AR-250: Upgrade flow parity (sub-issue 9 of AR-236) | open | p2 | F | 1/2 | none |
| [AR-251](issue-AR-251-cli-presentation-richness.md) | AR-251: CLI presentation richness (sub-issue 10 of AR-236) | open | p2 | F | 2/3 | none |
| [AR-252](issue-AR-252-record-verified-acceptance-outcomes.md) | AR-252: Record host-evidenced, independently verified outcomes for automatic promotion | open | p0 | C | 5/7 | none |
| [AR-253](issue-AR-253-dynamic-team-dispatch-on-every-harness.md) | AR-253: Prove staffing latency, rate, and cross-host parity | open | p0 | C | 0/8 | none |
| [AR-255](issue-AR-255-inference-owned-host-proven-child-staffing.md) | AR-255: Make native child staffing inference-owned and host-proven | open | p0 | C | 5/7 | none |
| [AR-258](issue-AR-258-reconcile-the-installed-projection.md) | AR-258: Reconcile the installed projection before any host proof | open | p0 | D | 0/6 | none |
| [AR-261](issue-AR-261-disambiguate-technical-diagnosis-risk.md) | AR-261: Disambiguate technical diagnosis from medical authority | in_progress | p0 | B | 7/8 | none |
| [AR-262](issue-AR-262-preserve-slow-host-dashboard-parity.md) | AR-262: Preserve slow host inspection parity in the dashboard | in_progress | p0 | F | 7/9 | none |
| [AR-263](issue-AR-263-restore-codex-desktop-parent-hook-delivery.md) | AR-263: Restore Codex Desktop parent hook delivery | open | p0 | F | 0/7 | none |
| [AR-264](issue-AR-264-compile-actionable-contractor-execution-profiles.md) | AR-264: Compile actionable contractor execution profiles | in_progress | p0 | C | 9/10 | none |
| [AR-265](issue-AR-265-contextual-turn-classification.md) | AR-265: Separate contextual inquiry from execution authority | in_progress | p0 | C | 24/25 | none |
| [AR-266](issue-AR-266-dense-hybrid-workforce-recall.md) | AR-266: Recall the complete workforce with dense hybrid retrieval | in_progress | p0 | C | 12/12 | none |
| [AR-267](issue-AR-267-accept-openclaw-numeric-package-revision.md) | AR-267: Accept OpenClaw numeric package revisions | in_progress | p0 | D | 4/4 | none |
| [AR-270](issue-AR-270-bind-openclaw-installed-copy-provenance.md) | Bind OpenClaw installed-copy provenance | open | p0 | D | 4/8 | none |
| [AR-271](issue-AR-271-accept-stopped-openclaw-uninstall-status.md) | Accept stopped OpenClaw uninstall status | open | p0 | D | 0/0 | none |
| [AR-272](issue-AR-272-preserve-openclaw-model-receipt-fields.md) | Preserve OpenClaw model receipt fields | in_progress | p0 | F | 2/5 | none |
| [AR-273](issue-AR-273-expose-openclaw-native-finalizer-tool.md) | Expose OpenClaw native finalizer tool | in_progress | p0 | F | 7/8 | none |
| [AR-274](issue-AR-274-model-agnostic-structured-inference-profiles.md) | Make structured inference profiles model-agnostic | in_progress | p0 | D | 13/14 | none |
| [AR-275](issue-AR-275-record-openclaw-native-skill-reads.md) | Record authorized OpenClaw native skill reads | in_progress | p0 | F | 10/11 | none |
| [AR-276](issue-AR-276-preserve-planner-repair-diagnostics.md) | Preserve planner repair diagnostics | in_progress | p0 | D | 13/16 | none |
| [AR-277](issue-AR-277-gate-openclaw-provider-calls-on-agency-preflight.md) | Gate OpenClaw provider calls on Agency preflight | in_progress | p0 | F | 16/18 | none |
| [AR-278](issue-AR-278-keep-openclaw-finalization-first-pass.md) | Keep OpenClaw finalization first-pass after tool use | in_progress | p0 | F | 10/11 | none |
| [AR-279](issue-AR-279-deliver-openclaw-finalizer-results.md) | Deliver accepted OpenClaw finalizer results instead of silent replies | in_progress | p0 | F | 55/58 | none |
| [AR-280](issue-AR-280-exclude-hermes-internal-post-response-preflight.md) | Exclude Hermes internal post-response calls from Agency preflight | open | p1 | F | 0/6 | none |
| [AR-281](issue-AR-281-route-native-children-through-host-profiles.md) | Route native children through host-scoped inference | in_progress | p0 | C | 13/14 | none |
| [AR-282](issue-AR-282-deliver-finalized-openclaw-child-announcements.md) | Deliver finalized OpenClaw child announcements | in_progress | p0 | D | 12/14 | none |
| [AR-283](issue-AR-283-persist-openclaw-child-terminals-after-delivery.md) | Persist OpenClaw child terminals after announcement delivery | in_progress | p0 | D | 10/11 | none |
| [AR-284](issue-AR-284-disambiguate-provider-fallback-receipts.md) | Disambiguate provider fallback receipts from inference-stage ordinals | open | p1 | C | 0/6 | none |
| [AR-285](issue-AR-285-accept-openclaw-stopped-gateway-status.md) | AR-285: Accept OpenClaw stopped gateway status | in_progress | p0 | D | 5/5 | none |
| [AR-286](issue-AR-286-configure-bounded-embedding-dimensions.md) | AR-286: Configure bounded embedding dimensions | in_progress | p0 | C | 7/8 | none |
| [AR-287](issue-AR-287-bind-host-hook-timeouts-to-inference-budgets.md) | AR-287: Bind host hook timeouts to inference budgets | in_progress | p0 | D | 7/9 | none |
| [AR-298](issue-AR-298-expose-complete-workforce-prompts.md) | AR-298: Expose complete workforce prompts | in_progress | p0 | C | 9/9 | none |
| [AR-299](issue-AR-299-local-ollama-canary-child-judge.md) | AR-299: Allow a local Ollama canary child judge | in_progress | p0 | D | 3/5 | none |
| [AR-300](issue-AR-300-bind-explicit-install-config-to-managed-canary.md) | AR-300: Bind the explicit install config to the managed canary | in_progress | p0 | D | 4/6 | none |
| [AR-301](issue-AR-301-private-systemd-dashboard-namespace.md) | AR-301: Support private non-root systemd dashboard namespaces | open | p0 | D | 4/5 | none |
| [AR-302](issue-AR-302-owner-private-local-verification.md) | AR-302: Make local verification owner-private by construction | open | p0 | E | 4/5 | none |
| [AR-303](issue-AR-303-bound-full-roster-embedding-requests.md) | AR-303: Bound full-roster embedding requests | in_progress | p0 | C | 8/9 | none |
| [AR-304](issue-AR-304-preserve-recruiter-critic-validation-diagnostics.md) | AR-304: Preserve recruiter and critic validation diagnostics | in_progress | p0 | C | 8/9 | none |
| [AR-305](issue-AR-305-normalize-planner-novelty-absence.md) | AR-305: Normalize planner novelty absence sentinels | in_progress | p0 | C | 5/6 | none |
| [AR-306](issue-AR-306-bind-strict-critic-semantics.md) | AR-306: Bind strict critic to verified staffing semantics | in_progress | p0 | C | 7/8 | none |
| [AR-307](issue-AR-307-project-canary-inference-credentials.md) | AR-307: Project exact canary inference credentials | in_progress | p0 | D | 6/7 | none |
| [AR-308](issue-AR-308-bind-activation-canary-delegation.md) | AR-308: Bind activation canary delegation | in_progress | p0 | C | 7/9 | none |
| [AR-309](issue-AR-309-restore-codex-0149-activation-proof.md) | AR-309: Restore Codex 0.149 activation proof | in_progress | p0 | D | 4/8 | none |
| [AR-310](issue-AR-310-require-managed-codex-canary-store.md) | AR-310: Require the exact Store for managed Codex canaries | in_progress | p0 | D | 4/5 | none |
| [AR-311](issue-AR-311-inject-exact-codex-canary-native-plan.md) | AR-311: Inject the exact Codex canary native plan | in_progress | p0 | D | 5/6 | none |
| [AR-312](issue-AR-312-validate-explicit-production-config.md) | AR-312: Validate an explicit production config before installation | open | p1 | D | 0/5 | none |
| [AR-313](issue-AR-313-trust-normal-umask-codex-artifacts.md) | AR-313: Trust normal-umask Codex artifacts by integrity | in_progress | p0 | D | 6/8 | none |
| [AR-314](issue-AR-314-bind-codex-default-canary-role.md) | AR-314: Bind the Codex 0.149 default canary child role | in_progress | p0 | D | 5/7 | none |
| [AR-315](issue-AR-315-project-codex-canary-install-home.md) | AR-315: Project Codex canary install-home authority | in_progress | p0 | D | 4/5 | none |
| [AR-316](issue-AR-316-size-ollama-selector-judge-context.md) | AR-316: Size Ollama selector-judge context for complete catalogs | open | p0 | D | 2/5 | none |
| [AR-317](issue-AR-317-route-agency-inference-through-litellm-aliases.md) | AR-317: Route Agency inference through LiteLLM aliases | in_progress | p0 | C | 5/8 | none |
| [AR-318](issue-AR-318-bound-codex-activation-child-wait.md) | AR-318: Bound the Codex activation child wait above observed latency | in_progress | p0 | D | 2/4 | none |
| [AR-319](issue-AR-319-honor-pinned-canary-judge-timeout.md) | AR-319: Honor the pinned canary judge profile timeout | in_progress | p0 | D | 2/4 | none |
| [AR-320](issue-AR-320-bound-codex-wait-to-full-child-staffing.md) | AR-320: Bound the Codex wait to the full child staffing path | in_progress | p0 | D | 2/4 | none |
| [AR-321](issue-AR-321-select-reliable-free-litellm-child-judge.md) | AR-321: Select a reliable free LiteLLM child judge | in_progress | p0 | D | 4/6 | none |
| [AR-322](issue-AR-322-bind-codex-child-session-to-canary-parent.md) | AR-322: Bind Codex child sessions to the exact canary parent | in_progress | p0 | D | 5/7 | none |
| [AR-323](issue-AR-323-remove-stale-ledger-schema-literals.md) | AR-323: Remove stale native-child ledger schema literals | open | p1 | E | 0/4 | none |
| [AR-324](issue-AR-324-bind-codex-canary-child-through-host-lineage.md) | AR-324: Bind the Codex canary child through host-authored lineage | in_progress | p0 | D | 5/7 | none |
| [AR-325](issue-AR-325-restore-codex-first-complete-callback-reconciliation.md) | AR-325: Restore Codex first-complete-callback reconciliation | in_progress | p0 | D | 5/7 | none |
| [AR-326](issue-AR-326-admit-terminal-codex-host-artifact-collection.md) | AR-326: Admit terminal Codex host-artifact collection | in_progress | p0 | D | 4/5 | none |
| [AR-327](issue-AR-327-replay-codex-delivery-receipts-across-append-only-completion.md) | AR-327: Replay Codex delivery receipts across append-only completion | in_progress | p0 | D | 5/6 | none |
| [AR-328](issue-AR-328-seal-hermes-install-tree.md) | AR-328: Seal the managed Hermes bytecode cache | in_progress | p0 | D | 7/8 | none |
| [AR-329](issue-AR-329-freeze-codex-inspector-bootstrap-as-persistent-input.md) | AR-329: Freeze the Codex inspector bootstrap as a persistent input | in_progress | p0 | D | 2/5 | none |
| [AR-330](issue-AR-330-support-codex-0150-collaboration-rollouts.md) | AR-330: Support Codex 0.150 collaboration rollouts | in_progress | p0 | D | 4/8 | none |
| [AR-335](issue-AR-335-make-content-invalid-completions-reach-fallback.md) | AR-335: Make content-invalid completions reach the different-provider fallback | open | p0 | C | 0/4 | none |
| [AR-336](issue-AR-336-requalify-the-recruiter-route-for-ordinary-tasks.md) | AR-336: Requalify the recruiter route for ordinary tasks | in_progress | p0 | C | 4/4 | none |
| [AR-337](issue-AR-337-run-harness-battery-on-version-change.md) | AR-337: Run the harness canary battery on any host version change | in_progress | p1 | F | 6/6 | none |
| [AR-344](issue-AR-344-codex-fail-open-stop-terminal-exit.md) | AR-344: Codex fail-open turn ends in Stop replay-mismatch and TUI exit | open | p1 | F | 1/3 | none |
| [AR-348](issue-AR-348-enforce-strict-independence-in-production.md) | AR-348: strict_independence is enforced nowhere in production | open | p2 | B | 0/2 | none |
| [AR-349](issue-AR-349-persist-rejected-hiring-cases.md) | AR-349: Repair-budget exhaustion persists no rejected hiring case | open | p2 | B | 0/3 | none |
| [AR-350](issue-AR-350-risk-classifier-verdict-vs-hint.md) | AR-350: classify_contractor_risk still acts as a binding verdict, not a hint | open | p3 | B | 0/3 | none |
| [AR-351](issue-AR-351-close-sibling-axis-empty-declarations.md) | AR-351: Explicit-empty sibling axes still grant coverage or silently never match | open | p3 | B | 0/3 | none |
| [AR-353](issue-AR-353-intermittent-staffing-verdict-window-linux.md) | AR-353: Intermittent staffing-verdict failures now measurable on the Linux box | in_progress | p2 | C | 0/3 | none |
| [AR-359](issue-AR-359-preserve-operator-policy-newlines.md) | AR-359: config set --stdin flattens operator_policy newlines | in_progress | p3 | D | 1/2 | none |
| [AR-365](issue-AR-365-hermes-fail-open-gate-trace-resolution.md) | AR-365: Hermes fail-open pass-through unreachable live — gate cannot resolve the closed run | in_progress | p1 | D | 3/4 | none |
| [AR-366](issue-AR-366-openclaw-fail-open-withhold.md) | AR-366: OpenClaw withholds fail-open replies — evaluated rejection fires on turns staffing never reached | in_progress | p1 | D | 3/4 | none |
| [AR-367](issue-AR-367-fail-open-resident-binding-claim.md) | AR-367: Fail-open turns never claim their resident binding; persistent hosts re-inject the kernel every turn | in_progress | p1 | D | 0/3 | none |
| [AR-368](issue-AR-368-normalize-trust-chains-before-executing-probes.md) | AR-368: Normalize a host's trust chains before the probe that runs it | in_progress | p2 | D | 3/4 | none |
| [AR-369](issue-AR-369-stale-host-process-serves-a-superseded-kernel.md) | AR-369: A stale host process keeps serving a superseded kernel after deploy | in_progress | p1 | D | 0/3 | none |
| [AR-370](issue-AR-370-staffing-asks-the-wrong-question.md) | AR-370: Staffing asks the wrong question, so operational requests retrieve nothing | open | p1 | C | 5/6 | [record](acceptance/issue-AR-370.md) |
| [AR-371](issue-AR-371-stalled-binding-makes-the-header-claim-none.md) | AR-371: A stalled binding acknowledgement makes every later turn report 'loaded: none' | in_progress | p1 | D | 1/3 | none |
| [AR-372](issue-AR-372-windows-agency-process-leak.md) | AR-372: Windows accumulates live agency MCP/CLI processes until spawning fails | in_progress | p0 | D | 4/5 | none |
| [AR-374](issue-AR-374-host-capability-vocabulary-gap.md) | AR-374: Most of the roster is permanently ineligible because hosts prove 9 capabilities and the roster demands 246 | open | p1 | C | 3/4 | none |
| [AR-393](issue-AR-393-declared-gaps-leave-no-hiring-account.md) | AR-393: A declared capability gap can leave no hiring account at all, and when it leaves one the reasons need not explain it | open | p1 | C | 0/5 | [record](acceptance/issue-AR-393.md) |
| [AR-400](issue-AR-400-preserve-staffing-progress-across-empty-gaps.md) | AR-400: Preserve staffing progress across empty gaps | in_progress | p1 | A | 0/3 | none |
| [AR-401](issue-AR-401-enforce-preflight-deadlines-at-provider-boundaries.md) | AR-401: Enforce preflight deadlines at provider boundaries | in_progress | p1 | A | 0/3 | [record](acceptance/issue-AR-401.md) |
| [AR-402](issue-AR-402-separate-subject-domains-from-execution-eligibility.md) | AR-402: Separate subject domains from execution eligibility | in_progress | p1 | A | 0/3 | [record](acceptance/issue-AR-402.md) |
| [AR-403](issue-AR-403-reuse-roster-embeddings-across-hook-processes.md) | AR-403: Reuse roster embeddings across native hook processes | in_progress | p1 | A | 0/3 | [record](acceptance/issue-AR-403.md) |

## Reproduction

Enumerate docs/roadmap/issue-AR-*.md, parse YAML front matter and retain only
status open/in_progress. Count column-zero Acceptance checkboxes and test
whether acceptance/issue-AR-NN.md exists. The canonical registry and existing
verify_docs/verify_tracker scripts remain authority; this snapshot is not a
replacement registry and should not be edited to simulate completion.

