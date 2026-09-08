---
title: "AR-280 current native Hermes invocation-purpose boundary"
status: active
category: roadmap
created: 2026-09-08
updated: 2026-09-08
tags: [evidence, hermes, lifecycle, performance, security]
related:
  - docs/roadmap/issue-AR-280-exclude-hermes-internal-post-response-preflight.md
  - docs/decisions/0064-classify-turn-intent-from-durable-state.md
  - agency_runtime/core/installer_payload_hermes.py
  - agency_runtime/adapters/hermes/bridge.py
  - tests/test_hermes_turn_trace_payload.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
---

# AR-280 current native Hermes invocation-purpose boundary

## Scope and identity

This is a read-only source inspection, not a native invocation, latency
measurement, test result or acceptance verdict. Agency inspection started at
`7c0c1221226cdf388f886e4ce18e9554d3d56204`; the inherited AR-410 ledger
`51a84b9cdadc486ff14f5b251912900de1b6caf9` changes no runtime source.

The installed Hermes command wrapper resolves to its native venv launcher.
That launcher's editable `hermes_agent-0.21.0` finder maps `hermes_cli`, `agent`,
`run_agent` and `tools` to the inspected clean source repository. Native Git
HEAD is `7cd91114b462b7af76e558cc4e97f82201d2e884`; version files both report
0.21.0. `git status --short` returned no changes. No native code, configuration,
provider, plugin registration, profile or owner Store was modified.

Native paths below identify source files within that exact upstream revision;
this receipt is self-contained and does not require a sibling checkout.

| Native source file | SHA256 of inspected complete file |
|---|---|
| `agent/turn_context.py` | `c735ad3c7926104adc4ec8f2d5cbe1bac29f9fea54f005dc59a61dc0eb8776e4` |
| `agent/background_review.py` | `1770aa5554068bdde521753e3147f45259d5d0edeaceadbff5da0bf14034df9e` |
| `agent/title_generator.py` | `d8eda583b71f23de424dd4373fa068f62b5f53172b3857edd046a8913d84055f` |
| `agent/auxiliary_client.py` | `8527605e0d9d56e3bb549f63a860d3e83002703f014a57e6f97853d0d5a4fb92` |
| `agent/subagent_lifecycle.py` | `2f7068fc7523ff9f025d883abc8a8817a275803fa70774da3f5514271a1625a1` |
| `tools/skill_provenance.py` | `aab95e676e8013b1c5def7e66f48a15bdd19a5c8257f27cb530ef30e571110a1` |
| `hermes_cli/plugins.py` | `63cef01ae81a23c859170d36860c9ac257f320266a88640a8b9690952728bba6` |

## Exact current hook contract

The production `pre_llm_call` emitter in native `agent/turn_context.py:1402`
passes these keyword names:

```text
session_id, task_id, turn_id, user_message, conversation_history,
is_first_turn, model, platform, parent_session_id, sender_id
```

Native lifecycle dispatch forwards the payload. Plugin dispatch adds
`telemetry_schema_version` with `setdefault`; its current value is
`hermes.observer.v1`. This is a schema label, not authenticated origin evidence.
There is no invocation-purpose field or fresh internal-invocation receipt.
The generic `run_conversation` API also has no invocation-purpose parameter.

Agency's generated plugin forwards bounded correlation, user/model and native
child fields to the bridge, but no caller-supplied purpose or origin marker.
The bridge's existing exception is exact durable
`resolve_pending_internal_retry(session_id, trace_id) == trace_id`; it seals
`internal_retry` and returns before creating a new preflight. Every other
invocation remains on the existing preflight path. This inspection neither
certifies all downstream fail-closed behavior nor changes that boundary.

## Correctly distinguish native paths

1. `agent/title_generator.py:403` calls `auxiliary_client.call_llm` with
   `task="title_generation"`. That auxiliary-client path has no production
   `pre_llm_call` emitter. The current title generator is therefore not the
   demonstrated duplicate Agency call; the historical issue's general
   title/summary examples are not fresh caller attribution.
2. Native `agent/turn_summary.py` is display bookkeeping, not an inference
   invocation. This does not classify every other summarization facility.
3. `agent/background_review.py:1627` calls the ordinary
   `review_agent.run_conversation`. Its fork deliberately reuses the parent's
   session ID and platform, sets persistence disabled, and sets private
   `_memory_write_origin` to `background_review`. This is a concrete source
   path capable of reaching preflight, not proof that it caused a particular
   retained live run. No prompt body was inspected to infer its purpose.
4. Standalone curator review also calls `run_conversation` and assigns that
   private origin; delegated children and user-directed side questions use
   the generic loop too. None may be skipped simply because it is a second
   invocation or has a parent session.

## Why there is no safe bounded bypass in this package

`tools.skill_provenance.get_current_write_origin()` returns a bare ContextVar
string for skill-write provenance. It carries no session, turn, issuer, expiry
or consumed-invocation identity. It is not a plugin invocation-purpose receipt.
Hermes relay context does expose current session/turn lifecycle, but not the
purpose. Combining these unrelated signals would create a new implicit
authority contract instead of consuming one the host supplies.

The native subagent API's module contract directs plugins to immutable
`PluginContext.subagent_lifecycle` contracts, not live `AIAgent` objects. Its
supported service supplies child launch/status/wait/cancel/result/reconnect;
it does not attest the purpose of the current parent invocation. Inspecting
private agent fields, monkeypatching host emitters, trusting a serialized
marker, classifying prompt wording, or treating the same-session parent as
internal would not satisfy AR-280/ADR-0064. No such shortcut is implemented.

The prerequisite remains a supported native purpose authority bound to the
active session and turn, with malformed, stale, replayed and cross-session
rejection. A future adapter must consume it before opening a run while
preserving real user status/skill/substantive routing and finalization.
Changing native Hermes to provide this contract requires a separate scoped
implementation; it was not authorized in this inspection.

## Verification boundary and next package

Twenty-one cases were added to `tests/test_hermes_turn_trace_payload.py`:
three user-request classes crossed with seven absent, claimed, unknown,
malformed, internal-boolean or replayed/cross-session marker payloads. The
fixture begins with a stale active trace and checks that the generated plugin
still calls the bridge using the fresh turn and does not forward the marker.
The bridge seam is replaced only to capture calls; no model or Store is used.

These cases are **written but unrun** by owner direction. They protect the
no-implicit-bypass boundary; they are not the red/green repair proof requested
by criterion 1, a provider-receipt check, native header evidence or full replay
verification. No acceptance builder or verdict was created. No runtime source
changed. All six original requirements remain unchecked.

Targeted Ruff check returned `All checks passed!`; Ruff format check returned
`1 file already formatted`; `git diff --check` was clean. Metadata and static
documentation validation both passed for 1,275 Markdown files. These commands
do not execute the new regressions or native providers. After the owner
authorizes verification and a native authority
contract exists, run the focused tests and then one exact installed Hermes
fresh-session check. Do not spend another provider run merely to rediscover
the known missing origin discriminator.
