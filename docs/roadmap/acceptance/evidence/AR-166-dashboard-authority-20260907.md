---
title: "AR-166 current dashboard authority and disclosure evidence"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [dashboard, security, acceptance, evidence]
related:
  - docs/roadmap/issue-AR-166-truthful-dashboard-disclosure-and-correlation.md
  - docs/decisions/0229-reconcile-dashboard-disclosure-with-owner-authority.md
  - docs/decisions/0117-unify-owner-control-authority.md
  - docs/roadmap/issue-AR-298-expose-complete-workforce-prompts.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
---

# AR-166 current dashboard authority and disclosure evidence

## Reproduction and repair

Baseline main 520a10e36893977101494193852f370968f05cd2; merge ledger
44c94c925f815cc18aefb1299f856cd19c844228. Against the unchanged renderer, the
updated key-redaction test and new two-provider interaction test both fail:
expected selector.disabled=false, actual true. The focused Node command with
name pattern 'provider configuration without|provider secret selector follows'
returns exit 1, zero passes/two failures, 62.333575 ms.

The sole product edit changes the nonempty-list assignment from true to false.
Empty/non-array/unparseable lists still disable it. The new test selects index 1,
preserves it through re-render, and stages only a providers.1.api_key secret
operation. Four invalid/empty states and stale-selection recovery are covered.
Stored keys never enter the JSON control. The test allows no fetch or persistence.

## Fresh verification

Linux, checkout-local Python imports, no new skips/xfails or lowered thresholds:

- Selector checkpoint UI: 189 passes, no skips/failures, 240.844917 ms.
- After the null-error repair: full UI 190 passes, no skips/failures,
  231.878074 ms. All three 401/403/503 null-body cases retain status and ID.
- Production UI coverage: 96.93 percent lines, 86.71 branches, 95.71 functions;
  unchanged 95/86/93 thresholds and dashboard-JavaScript-only scope.
- Warning-strict test_dashboard_auth_boundary_regression,
  test_dashboard_transaction_refactors, test_cli_owner_authority,
  test_workforce_cli and test_dashboard: 235 passes, no skips/failures, 46.37s.
- Named production spine: 1085 passes/three existing skips at the selector
  checkpoint (67.88s), and again after the null-error correction (66.99s).
- Focused dashboard/asset packaging contracts: three pass/187 deselected, 0.28s.
- Ruff check/format: 766 files pass. Scoped diff check passes.

UUIDv4 validation, safe errors, exact response correlation, validated Route Lab
IDs, runtime-capture privacy labels and Store-backed definition provenance
remain. No backend, authentication, broker policy, retention or capture setting
changed. Exact Git comparison against a4be59b0 of backend/core, their tested
modules, scripts, pyproject and AGENTS returns zero bytes of diff. These tests
are not native-host or real-provider staffing evidence.

Final source-served browser verification passes 20 checks, including terminal
null-401 notices with safe request IDs at both viewport widths; see the bounded
browser receipt below.

## Requirement reconciliation

ADR-0229 explicitly changes only criterion 1 under accepted ADR-0117.
Original wording remains in the canonical issue; the other five are unchanged.
AR-298's current bounded definition is at most 262144 characters, not the
historical 8192-character preview. Stored definition is not runtime capture or
delivery proof. The governed legacy tracker exemption applies while unmapped.

## Browser checkpoint

The source-served selector fixture passes 18 checks at 1280/375 pixels on
Chromium 152.0.7977.64, with zero POST requests. The served selector SHA-256
matches a4be59b0: c75dc679ac2508d9c97fa10811620bb474bfc0aaaa64563ea24957eb74ff0dbf.
An initial timeout and diagnostic run reached an authenticated dashboard but
only one empty-list option: the fixture targeted the old standalone config
endpoint. Injecting synthetic provider drafts into the current combined control
snapshot fixes the fixture, without changing production code. The initial
zero-check report remains in AR-166-browser-20260907/report.json.

No installed-wheel, native Windows, attended-host or full accessibility claim.
The browser uses a private five-agent Store, stubbed host inspection, denied
server outbound connections and synthetic provider drafts; no owner profile.

After both repairs, the clean f9c55ada/eb92b936 source passes the final fixture:

```json
{"passed":true,"checks":20,"post_requests":0,"browser":"152.0.7977.64","config_sha256":"c75dc679ac2508d9c97fa10811620bb474bfc0aaaa64563ea24957eb74ff0dbf","stage":"provider_options_ready"}
```

The [raw final report](AR-166-browser-20260907/final/report.json) records ten
checks at each of 1280 and 375 pixels: second-provider selection, stable
selection after secret input, explicit runtime privacy, four disabled-list
states, valid recovery, served-module identity, and terminal null-401 notice
with a canonical request ID. Both served modules match this source; core hash
233c5e9c070f6544af26f26c5c976e5f9b04b826196b150e0cccc83c934d02b5.
Two screenshots and their hashes are retained beside that report. They use
fictional provider drafts only; the owner bearer is never in the URL or output.

## Null HTTP error correction

Inspection of criterion 2 finds a second same-scope gap: valid JSON null with
an HTTP error throws TypeError before APIError can retain status/request ID.
The new 401/403/503 test fails against a4be59b0 on the first case, with
TypeError reading error from null (one failure, 64.829985 ms). Optional chaining
preserves the existing HTTP fallback message and safe browser request ID.
This changes no response-correlation, authentication or broker policy.
The refreshed 190-case UI suite and final 20-check source-served browser receipt
pass before freeze. This is still the first isolated acceptance review.

## Publication validation

Fresh metadata and strict docs with required trackers pass for 1188 Markdown
files. Strict tracker passes for 397 mapped records with two historical
PR-tracked exceptions. Policy availability is current; the exact worklog
indexes 1985 substantive commits before this repair. Diff check returns zero.
AR-166 is governed pre-tracker history, not an unrecorded remote closure.

After the null-error repair and builder record, metadata/strict docs pass 1190
files; strict tracker still passes 397 mapped records/two historical PR items.
Policy, exact worklog (1986 substantive commits before this checkpoint), Ruff
766 files and diff checks pass.
