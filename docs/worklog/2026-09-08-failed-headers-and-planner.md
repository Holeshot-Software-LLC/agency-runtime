---
title: "AR-414 failed headers and planner repair"
status: active
category: worklog
created: 2026-09-08
updated: 2026-09-08
tags: [headers, staffing, live-evidence, codex]
related:
  - docs/roadmap/issue-AR-414-reliable-staffing-failure-headers.md
  - docs/roadmap/handoffs/issue-AR-414.md
  - docs/decisions/0239-render-failed-turn-diagnostics-without-acceptance.md
supersedes: []
superseded_by: null
type: worklog
commit: 992d148d
short: 992d148d
date: 2026-09-08
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/774
related_issues: [docs/roadmap/issue-AR-414-reliable-staffing-failure-headers.md]
---

# AR-414 failed headers and planner repair

## Outcome

PR774 merged as905d37b8. The failed-turn renderer reads immutable failure
evidence without accepting or reopening the run. Request-scoped failure closes
persist their validated steward binding. Initial hook snapshots expose the real
session/trace pair instead of requiring a guess from the hashed manager ID.

## Exact verification

- Focused header/store/preflight117passed,1skipped; hook/context112passed.
- Named Python production spine1151passed,3skipped; dashboard224passed.
- Decision conformance188mutations killed,0survived,0invalid; source unchanged.
  Initial invocations failed in isolated test setup; umask077 and the established
  copied-interpreter environment produced the passing result.
- Metadata, policy availability, exact worklog, docs/tracker parity, Ruff and
  diff checks pass at the header checkpoint. No exhaustive coverage/matrix run.
- Canonical build, Twine and independent distribution verification passed for
  992d148d8ae60e82dc5856de1af4df2c1a4c015c. All614installed package files match.
  WheelSHA256:6b5e4aebddb60dd90a6e4080702b3e60effeca00aba8857123f4ab31f7bf3615.
- Installed Python, actual SQLite and actual MCP stdio return a five-line
  diagnostic header: loaded agency-steward; delegated none; skills none;
  actual model none observed; recruitment failed with
  workforce_provider_unavailable and planner:provider_call_timed_out.
  Finalizer actioncontinue, preflight_failed true, no missing response fields;
  the stored run remains preflight_failed. This is an injected failure fixture,
  not a successful native staffing run.

## Planner cause and experiment

The existing planner deployment ed1b5bbc-bbb7-533a-b3d8-5873a004e4c1 is configured
as openai/glm-5-turbo. Recent responses identify GLM5.3Flash. Its installed
gateway OpenAIGPTConfig supported-parameter list omits reasoning_effort, so
earlier request-only low comparisons did not prove that low reached upstream.
[Current vendor documentation](https://docs.z.ai/guides/llm/glm-5.3) specifies
low/high/max, with max as default. The configured medium is not one of those.

One request-only extra_body.reasoning_effort=low probe returned a valid complete
five-unit plan after a17.1second semantic repair. The approved bounded gateway
experiment changes only that existing deployment's order2to0 and
extra_body from empty to {reasoning_effort: low}. Exact readback confirms all
other parameters unchanged; no credential, service restart or other route change.
The correction is retained after the accepted staffing sample below. Restore
order2 and empty extra_body to reverse it; no secret-bearing backup is required.

Ordinary installed staffing then returned quickly but rejected novel_capability
null followed by an invalid identifier (33.12seconds total). These are actual
schema/semantic failures, not evidence that selection should be weakened.
An exact-prompt rerun hit gateway cache (0.071seconds), so it is diagnostic
replay evidence only, not a latency improvement sample.

The planner said to set novelty only for a real gap, while its schema requires
the field even when absent. Both first-pass and repair instructions now name
the exact eight fields and say to use empty-string novelty, never null/false/N/A.
Identifier constraints and the compiler remain unchanged.

With those instructions, one installed real-provider call accepted staffing in
25.078seconds: subject16ms (warm response), planner7702ms, embedding3299ms,
reranker7809ms, recruiter3546ms, critic2501ms. Every stage applied; no semantic
repair, abstention, or manual worker nomination. The request was one indivisible
review of a supplied average function, no repository mutation. This probe used
the candidate instruction text through an invoker wrapper; it is not yet a
stock installed/native-host proof. No cold-latency or percentile claim is made.

## Native boundary and next action

The992d148d package was installed and agency install --agent codex --no-dashboard
completed. New bundle7994faf6c2458bd3af84e8bbe6b15a4791b652bec8d0ca4ecdbc7227a29db750
has plugin0.1.0+codex.b035c27ba32f. Unlike the previously trusted bundle, actual
hooks/list inspection now reports all8modified,0trusted. No bypass was used.
A fresh ordinary Codex run15:04:48UTC completed in16.213seconds with MCP tools
but0Agency runs and0header fields, session01a0818c-e121-74e1-8b86-7958f7f786fa.
It proves no native activation. Further native attempts stop until owner trust.

Finish the instruction follow-up, reinstall that final artifact, preserve exact
new hashes, and ask once for fresh /hooks approval. Then perform one normal
activation and ordinary turn with no override, verify headers/injection/receipts,
and collect a small cold/warm sample. AR414/AR404 remain open. Windows and other
harness native claims are untouched; no OpenClaw or dashboard restart occurred.
