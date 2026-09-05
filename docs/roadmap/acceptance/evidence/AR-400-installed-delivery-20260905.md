---
title: "AR-400 independent review and installed delivery evidence"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [review, verification, installation, performance]
related:
  - docs/roadmap/issue-AR-400-preserve-staffing-progress-across-empty-gaps.md
  - docs/roadmap/issue-AR-401-enforce-preflight-deadlines-at-provider-boundaries.md
  - docs/roadmap/issue-AR-402-separate-subject-domains-from-execution-eligibility.md
  - docs/roadmap/issue-AR-403-reuse-roster-embeddings-across-hook-processes.md
  - docs/roadmap/handoffs/issue-AR-400.md
supersedes: []
superseded_by: null
---

# Independent review and installed delivery, 2026-09-05

## Findings and fixes

Reviewed from main e6531004, using the incoming capsule as leads, not verdicts.
The code was self-implemented. No implementation specialist was delegated.

| Finding | Reproduction and repair | Record |
|---|---|---|
| Successful hires disappear while another gap has an empty ranking | Four initially failing composed hiring cases; retain declared gaps and successful assignments, preserve other nominations on amendment, reverify against current contracts | AR-400 |
| Provider stages repeatedly spend fresh timeouts after consuming the lease | Real three-stage hiring under a simulated 75-second lease now stops at 65 seconds, leaving terminal-recording margin; one absolute deadline reaches planning, repair, fallback, HTTP, embeddings, reranking and native CLI launch | AR-401 |
| Descriptive domain tags act as execution authority | Packaged backend work was constrained to an unrelated worker; domain overlap now informs recall, while real authority/capability/tool/platform/exclusion checks remain | AR-402 |
| Fresh native hook processes re-embed the unchanged entire roster | Lossless, private, bounded, expiring roster-only vectors survive processes; every query remains freshly embedded and all staffing/hiring judgments remain active | AR-403 |

## Code and installation identity

- Implementation merged through [PR #669](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/669).
- Main merge: 1de05aead322dbbf359a0a5f3ab19dcbb7cdeff9.
- Non-editable VCS package: 0.1.0+g1de05aead322, installed from that exact Git commit.
- Runtime projection: 349f1ae7fc749c57405f78b7204e36158a67ea70c815b31afacd0d053ef50ef1.
- Wheel SHA-256: 4be394b28b58e33520be3a1a8b84b7806d7ffe9fc605dc81f696ce95426fcddf.
- Commands ran outside the source checkout, so installed results cannot import the development tree.
- agency install --json ran at 16:43Z. Overall result: partial, complete=false; OpenClaw restart consent and Codex activation remain outstanding.
- Dashboard service: installed, enabled, active, restarted and reachable.
- PATH launcher previously named the old 04adb230 interpreter; it now names the pinned 1de05aea interpreter. Its exact old contents were backed up beside the new venv as previous-agency-launcher. No old venv was deleted.

## Deterministic all-host smoke

agency smoke --all --json: passed=true, passed_count=8, failed_count=0,
skipped_count=0. Host parity evaluation: five passed, zero failed.

| Check | Result | Observed scope |
|---|---|---|
| SQLite store | pass | Disposable store initialized |
| Roster available | pass | 265 starter roster entries available |
| Host parity | pass | Five host contracts |
| Claude plugin | pass | Bundle, lifecycle events and MCP server |
| Codex plugin | pass | Eight hook events and MCP server |
| Hermes plugin | pass | HermesBridge and agency_finalize tool |
| OpenClaw plugin | pass | JavaScript syntax |
| ZCode hooks | pass | Process invocation, idempotence, preserved config and toggle |

This smoke generates disposable adapters; it is not proof of five live host sessions.

## Native installation and live scope

| Host | Installed result | Live attempt / blocker |
|---|---|---|
| Claude | Registered and enabled, current immutable launcher | Isolated Agency canary passed at 16:51:15Z; details below |
| Codex | Registered and enabled; activation incomplete | Current-profile activation verification attempted; eight changed hooks, zero trusted; stopped before model invocation with codex_hook_trust_not_ready |
| Hermes | Registered and enabled, current immutable launcher | Readiness blocked: no proven read-only bounded native-child noninteractive canary mode; an ordinary fresh host session remains operator work |
| OpenClaw | Update refused before mutation | Live gateway requires stop/restart consent; readiness also reports no proven bounded native-child canary mode; old running integration is not claimed current |
| ZCode | Seven handlers registered/enabled, existing global switch preserved | No discovered CLI/version and no proven bounded native-child noninteractive canary; fresh desktop session remains operator work |

Claude command: agency host-canary claude --execute --confirm 'RUN LIVE claude CANARY'
--timeout 240. Existing configured credentials were sourced; none were created,
printed, or committed. Observed JSON: canary_passed=true, live_attempted=true,
profile_scope=isolated-profile, attestation_persisted=false, trust_bypass_used=false.
Invocation: completed, exit_code=0, timed_out=false, header_valid=true,
isolated_plugin.loaded=true, isolated_plugin.invoked=true.
Native child delivery: code-reviewer; verified_delivery=true; pre_speech=true;
runtime_digest and candidate_digest equal the projection above.
Parent trace eed4cc65-266e-4322-91b2-b53cd81f573b; child a71c15e8835290d91;
artifact digest d6e512518a6efbade9ccfa0555c1f53bf221ed4728343ae4c261585bbe11e176.
This proves one isolated native-child delivery, not an ordinary production task,
gap hiring, all-host live parity, or the accepted-outcome producer/verifier canary.

Codex recovery: review changed hooks in a fresh terminal TUI using /hooks, then
agency install --agent codex --verify-activation. Changed definitions require new
review under the [official hook trust contract](https://learn.chatgpt.com/docs/hooks#review-and-trust-hooks).
No hashes were manually trusted and no bypass flag was used. Existing sessions
can still hold an old kernel after files are updated.

## Verification and performance scope

- Named fast Python spine: 1004 passed, three skipped.
- Final deadline/CLI/hiring/credential/conformance follow-up: 135 passed.
- JavaScript tests: 138 passed; routing evaluation passed.
- Decision-conformance: baseline passed, 182 mutations killed, zero invalid/surviving, source unchanged. This preceded the final tiny launch-deadline follow-up, which received the focused checks above.
- Ruff check/format and metadata/policy/worklog/docs checks passed before merge.
- Live recall pair: 63.620 s cold versus 8.804 s warm; embedding 49.759 s / 283 inputs versus 2.804 s / one input.
- Full reports: AR-403-recall-performance-20260905.json in this directory. Fifteen of sixteen additions overlap, reranked lists differ. One pair is not an end-to-end latency distribution or proof of equivalent live staffing quality.
- No exhaustive warning-strict corpus, coverage shards, compatibility matrix or workflow dispatch was run.
- Strict tracker checks initially found only the known AR-397/398/399 parity debt. Subsequent owner-requested backlog reconciliation is separately recorded.

## Remaining work

Attended Codex trust, consented OpenClaw restart/install, and fresh Hermes/ZCode
ordinary sessions remain distinct operator/platform gates. The review fixes are
implemented and merged; broad staffing quality and backlog completion are not
claimed by this bounded delivery.

