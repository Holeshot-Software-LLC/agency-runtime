---
title: "Native terminal repair and four-host verification"
status: active
category: worklog
created: 2026-09-08
updated: 2026-09-08
tags: [openclaw, hermes, claude, zcode, finalization]
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/799
related:
  - docs/roadmap/issue-AR-419-finalize-openclaw-cli-responses.md
  - docs/roadmap/issue-AR-418-preserve-hermes-truncation-terminal-evidence.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/handoffs/issue-AR-404.md
supersedes: []
superseded_by: null
---

# Native terminal repair and four-host verification

## Outcome and approach

Starting main and origin match97e269ec, clean. Owned branch
`codex/ar418-ar419-native-terminal-20260908` replaces the merged historical
capsule branch. Observable outcome: an ordinary accepted native turn with exact
headers, injection evidence and central finalization, then Claude/Zcode proof.
Phase: live_demo. The exact ordinary OpenClaw terminal handoff is proven;
exact card injection remains unproven, so AR-419 stays open.

The OpenClaw awaited `before_agent_finalize` hook exposes internal delivery as
`ctx.channel=webchat`. A positive pre-verify result now passes its exact text,
session and trace to the existing outbound gate. Other channels still await
complete payload sealing. No staffing, critic, model, token budget or validator
changes. Existing first-invalid policy, native errors and outbound seals remain.

## Evidence and limitations

Twelve executed generated-Node cases cover positive, rejected and unavailable
policy results across webchat, external and missing channels. Focused adapter,
correlation and boundary checks:153passed/one skipped in20.17seconds.
Production spine:1151passed/three skipped in72.28seconds; UI224passed.
Docs1342files, Ruff780files and metadata pass. Routing passes. Decision conformance passes188/188, source unchanged; the
first baseline run failed private-directory creation under the default umask,
then the same source passed with the required private umask077. A missing shell Ruff
command is an environment lookup failure, not a lint result; use the existing
private development environment. No exhaustive workflow was dispatched.

Hermes native source has early truncated-result returns outside normal output
transformation and session-end hooks. Both a provider length condition and
malformed tool arguments can produce the same message. The outer runner and
one-shot CLI can report success for printable partial output. No supported
terminal-result hook covers these paths; an adapter-only cleanup change would
not prove repair. The original receipt and unknown provider cause are preserved.

Claude is found on PATH, but inventory rejects its executable parent namespace
permissions. Zcode's configuration hooks are registered/enabled without an
executable, version or proven native capabilities. Both remain in scope.

The current Codex turn is honestly unstaffed: planner, reranker and recruiter
response-contract failures are recorded in its current snapshot. The prior
handoff turn's critic veto is a different receipt and is not reclassified here.
A fresh CLI wiring read reports Codex not_measured; that is not fresh hook proof.

## Next bounded package

Complete fast checks, install the immutable OpenClaw candidate through normal
gateway maintenance, and capture one fresh native result. Preserve all failed
receipts and keep AR-404/418/419 open until isolated criteria have evidence.

## Installed native terminal evidence

Immutable candidate308b670a (production change94b9eb28) built successfully from
an isolated local clone after the shared clone exceeded the bounded Git-config
inspection size. No build bound was changed. Independent artifact verification
and Twine pass; all614installed package files match the wheel. Normal gateway
stop/install/start restored RPC health and retained every configuration section.

Fresh ordinary OpenClaw session `agent:openclaw:ar419-native-20260908`, trace
`b2f9ef9e-1280-4c28-9934-6b094bdfcf6a`, returned in195.996seconds. Staffing
accepted code-reviewer in159.779seconds; native answering model task-general.
One central accept event binds exact response SHA256
81356a9c914b08463d76681650c7daf4ae24ad6d4236a880dff15df54066c466.
Store is completed/ready; no tool call, external delivery or manual finalization.
The five-field header was validated by the central gate. The header builder
correctly refuses a new evaluation after the turn is terminal; the authoritative
accepted digest is the completion evidence.

The session-scoped optional input observer failed native capability consent before
installation; no observer remained installed and native configuration sections
match the backup. The owner has been asked once about that separate consent.
Exact injection remains unproven; this is terminal-handoff proof only. See
`docs/roadmap/evidence/AR-419-openclaw-terminal-20260908.json`.

Claude's two group-writable executable parent directories were tightened from775
to755; native inventory now proves2.1.265 registered/enabled. Normal refresh from
the candidate succeeds. Native turn proof follows. Zcode has a3.10.2Linux AppImage
and desktop launcher, but no supported CLI command discovered yet; the extracted
bundle is being inspected rather than assuming the desktop app is absent.

The prior exact Codex handoff receipt was read: session
01a08200-6530-79a3-a19c-4fb24b1983ae, trace
01a082b9-e7df-70e2-b76c-b8be7e01ad5a, preflight_failed. Subject/reranker contract
rejections and staffing_critic_rejected/critic_wrong_neighbor_selection are
recorded. No old transport failure or erroneous critic verdict is inferred.


## Claude evidence and Zcode entrypoint repair

Claude completed a fresh ordinary turn with full selected code-reviewer card in
both native hook content and its rendered model context. Exact response SHA256
9edfb785eab7bc2cbcf4232d0141dfa123c169e0d5584ac35a9e6cc6ec99607f
matches authoritative accept32588a29-1317-4e28-9911-eaa5ef863666; Store completed.
Session31b0b550-d076-447c-8e68-bd070674a907, trace
16079749-cfc9-4d90-b4d4-6f6ce8104eec. Total63.879s, staffing43.063s,
exit0, permission denials empty. No permission bypass or model override.

Zcode3.10.2 AppImage includes a working0.16.5 node bundle under resources/glm;
native doctor confirms node-bundle packaging. Copied that unchanged resource
directory to an owner-only-write stable installation and installed a thin PATH
launcher. Bundle SHA2563597160465b67da248fa3fb919920ca30d4e093003a4d70cde2a2e33903cbabc.
Normal Agency Zcode refresh succeeds. Existing desktop launcher is untouched;
its sandbox flags are not used. Trial will explicitly use native build permissions
because headless prompt default is yolo. This records discovery/install only.


## Hermes native and adapter candidate

Native owned-worktree commit59e52e556a, exact subject
`fix(lifecycle): preserve failure diagnostics on truncated turns`, based on
7cd91114b4, is preserved as AR-418-hermes-native-terminal.patch. Two actual loop
regressions fail on unpatched source with missing failed state. Patched34native
tests pass through the canonical hermetic runner. First test iteration exposed
a fixture home-selection error; corrected without weakening assertions. Native
failure callback preserves observed finish_reason and source branch, not an
inferred token cap. No native installed checkout was edited. Upstream publication
and adoption are separate from this same-repository delivery.

Agency's optional failure hook formats exact Store-backed diagnostic headers;
session-end failed=true closes only the exact active session/trace as failed.
It never accepts partial text. Focused94tests pass. Initial adapter fixtures lacked
request_kind and an existing hook inventory expected the old list; corrected
fixtures and the inventory. Existing correlation, ordinary acceptance and outbound
checks remain. Refreshed production spine1151passed/three skipped in71.23s; Ruff780files,
metadata, policy availability and docs1342pass. Conformance follows this clean
checkpoint; the earlier188/188 verdict applies only to the earlier source.

Zcode native parser advertises but rejects --max-turns; the parser-only attempt
made no inference call. Removing that flag reaches a real configuration gate:
CLI config has only hooks and no answering provider. Desktop separately selects
Z.AI coding-plan OAuth. Provider choice was requested once; no credentials or
models were substituted. Native executable is now available but no accepted turn.
