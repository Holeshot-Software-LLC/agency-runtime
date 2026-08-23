---
title: "Exact-main Linux handoff for OpenClaw and Hermes"
status: active
category: roadmap
created: 2026-08-16
updated: 2026-08-23
tags: [roadmap, verification, hosts, openclaw, hermes, linux, AR-119]
related:
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/roadmap/AR-119-rule-host-evidence-matrix.md
  - docs/roadmap/AR-119-founding-vision.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0158-collect-child-canary-proof-inside-disposable-host-profiles.md
  - docs/roadmap/issue-AR-272-expose-openclaw-native-finalizer-tool.md
  - docs/roadmap/issue-AR-273-model-agnostic-structured-inference-profiles.md
  - docs/decisions/0163-keep-litellm-inference-profiles-model-agnostic.md
  - docs/roadmap/issue-AR-278-deliver-openclaw-finalizer-results.md
  - docs/decisions/0166-refresh-openclaw-headers-through-awaited-tool-results.md
supersedes: []
superseded_by: null
type: reference
issue_id: AR-119
---

# Exact-main Linux handoff for OpenClaw and Hermes

OpenClaw and Hermes are intentionally absent from the Windows evidence
workstation. This packet is the bounded transfer to the owner's Linux box. It
is a recipe, not installed or live evidence, and it moves no AR-119 matrix cell.

The implementation anchor is exact main f76050d7. The evidence-only branch
that refreshed this packet changes documentation, not runtime code. After its
[skip ci] pull request merges, use the resulting exact origin/main, record its
SHA, and prove that it contains the implementation anchor.

## 1. Freeze the Linux starting point

Run from the Linux checkout:

~~~bash
git fetch origin
git switch main
git pull --ff-only
git status --short
git rev-parse HEAD
git merge-base --is-ancestor f76050d7 HEAD
python -m agency_runtime.cli --version
python -m agency_runtime.cli doctor
python -m agency_runtime.cli status --json
~~~

The status output must be empty for git status --short, the ancestor check must
exit zero, and doctor must not report Store/runtime schema drift. Exact main
uses Store schema 47. Do not measure through an older PATH launcher or a
checkout whose imported agency_runtime.__file__ is ambiguous.

Before mutation, stop active host sessions and make a recoverable owner-Store
backup with SQLite integrity and SHA-256 recorded. Do not copy a live database
without its WAL state. Preserve the before-install host versions, Agency status,
Store contractor count, and current launcher manifests.

OpenClaw installation accepts only the audited stable 2026.7.x line, at least
2026.7.1. A prerelease, older release, newer release line, or live gateway is a
named stop condition. Stop the gateway through OpenClaw's native procedure; the
Agency installer must not restart it.

## 2. Install exact main, one host at a time

Use the checkout module, not a stale packaged executable:

~~~bash
python -m agency_runtime.cli install --agent openclaw --no-dashboard --json
python -m agency_runtime.cli status --json
python -m agency_runtime.cli install --agent hermes --no-dashboard --json
python -m agency_runtime.cli status --json
~~~

For each host retain the complete JSON result and record:

- checkout SHA and clean-tree state;
- native host version and profile identity;
- install status, registration, enablement, and restart requirement;
- ~/.agency-runtime/launchers/current-<host>.json;
- runtime digest, source root, bundle/manifest digest, and Store schema;
- every refusal or partial result exactly as emitted.

Both hosts must point at the runtime produced by the same checkout. Restart each
host and open a fresh session; a session opened before installation cannot
prove the installed projection. Do not reinstall merely to refresh a session.

## 3. First-response and skill evidence

In a completely new session for each host:

1. Send exact agency status as the first user message.
2. Preserve the first assistant response and host transcript before sending a
   second message.
3. Correlate the session and trace with runs, resident_manager_bindings,
   routing_decisions, and specialists_loaded.
4. Only if the response has a real Store-backed Agency header, load one harmless
   available skill through the host's installed Agency skill surface without
   spawning a child.
5. Preserve the updated five-line header and matching skills_loaded row.

No header plus no Store lifecycle row is activation unavailable, not
Agency/Agencies loaded: none. A Store row without the host-written response is
not response-delivery proof. If a host lacks the expected status or skill
surface, record the exact mismatch and stop that sub-proof.

## 4. Current exact-main child-proof boundary

Do not run either of these commands with --execute:

~~~bash
python -m agency_runtime.cli host-canary openclaw
python -m agency_runtime.cli host-canary hermes
~~~

The readiness reports are useful artifacts, but exact main intentionally limits
SAFE_CANARY_HOSTS to Codex and Claude. OpenClaw and Hermes reject live canary
execution because no proven bounded noninteractive native-child mode exists.
Do not bypass that gate or hand-construct a confirmation.

Exact main also has no supported child-artifact root/reader for either host.
Their bridges deliver child context in process, while ADR-0156 requires a
host-authored artifact containing the exact inference-selected card hashes
before first child speech. Therefore:

- installation, registration, parent header, skill, Store, or bridge stdout may
  support their own bounded claims but cannot prove Rule 4;
- an ordinary native child may diagnose the bridge payload, but it cannot move
  a Rule-4 cell without a supported host-authored artifact and matching
  native_child_delivery_verifications row;
- routing_decisions, specialists_loaded, copied plugin content, or model prose
  never substitute for that artifact.

If development continues on Linux, the first bounded diagnostic is to capture
the raw host-owned child-launch payload before Agency interprets it. Record
whether parent_session_id, parent_trace_id, worker_id, and native_run_id are all
present. Hermes may otherwise fall through as an ordinary user turn; OpenClaw
may take an early post-tool path before the shared child-start recorder.
Preserve a missing field or missing artifact as the product boundary rather
than patching evidence after the fact.

## 5. Live-work discipline

- Use genuinely new work units. Do not replay the consumed SAP, Erlang,
  COBOL/CICS/VSAM, Python-install-guide, or PostgreSQL-recovery units.
- Serialize hosts and provider calls. Keep every failed or timed-out attempt;
  never retry until green.
- Keep ordinary provider routing unchanged. The Windows Option A pins apply to
  Claude, Codex, and ZCode canaries only; they do not silently select a Linux
  host provider.
- Set a 420-second outer ceiling for any explicitly authorized live unit and
  terminate once at the ceiling. A killed or malformed upstream response is not
  a provider loss or successful staffing result.
- Never claim a contractor outcome, promotion, rule, or matrix movement from
  registration, a Store projection, or useful generic-child prose.
- Do not dispatch hosted Actions from this packet.

## 6. Evidence to return

Return one bundle per host containing:

~~~text
host:
checkout_sha:
clean_tree:
host_version:
profile:
runtime_digest:
store_schema:
install_result:
fresh_session_id:
agency_trace_id:
first_response_artifact:
header_exact:
resident_binding_id:
routing_decision_ids:
specialists_loaded_ids:
skill_name_and_row_id:
native_child_id:
raw_child_launch_payload_artifact:
child_artifact_path_and_sha256:
delivery_verification_id:
timeout_or_failure_receipt:
known_limit:
~~~

Also return the before/after contractor counts and Store integrity receipts.
Prompt and response bodies need not enter the durable roadmap; content-free IDs,
hashes, provider receipts, exact headers, and host artifact paths are enough.
Cells that this packet cannot reach remain unproven, which is the correct
result.


## 7. Current Linux OpenClaw checkpoint — 2026-08-21

OpenClaw was the only Agency-install target. Hermes remained the active
break-glass host and was not installed, stopped, restarted, or reconfigured.
Claude, ZCode, Codex, Codex OAuth, and the consumed Codex canary remained
outside the mutation boundary.

### Installation and invariants

The install checkout was clean at `a70131d63c511e418edcda2ccae1f8e45866a95a`.
OpenClaw remains the existing audited `2026.7.1-2 (0790d9f)` package with native
primary `litellm/task-general`, six fallbacks, 21 LiteLLM models, and 27 total
model entries. Only the existing gateway was stopped and restarted. Agency-only
install `479c1a47-7e89-4091-a0f4-548f6913db58` completed without restarting it
or changing contractors. The installer reported registered, enabled, and
runtime-verified Agency integration; dashboard installation was opted out.

The installed launcher resolves to this checkout. Bundle digest is
`475e56274dec5f7eb61b54a469489274247caa60a18910ff200ec7757bed59a4`, runtime
digest is `52724f5a8803d1662228a67c03c9a986a5eeebc2289ddb68cdad0306272de066`,
launcher SHA-256 is
`5539744ef47aa464921887ee067e3f3c54c9caeacac252259f5a5bb008d462cb`, and
install-manifest SHA-256 is
`8d25e7420dc7e8614e3981df0b20274d72add6617b7f899112c925287b82e8b6`.
The installed native plugin reports ten typed hooks, provider-safe tool
`agency_finalize`, conversation access enabled, zero diagnostics, and zero MCP
servers.

Latest pre-install online Store backup is
`~/.agency-runtime/backups/ar272-openclaw-nativehost-preinstall-Ah1yzQNU/agency.db`;
live and backup integrity are `ok`, and backup SHA-256 is
`64421c3fc50623940930d757f15f7cd5930537ea9f8d9dd682a5ca771c8ea66d`. Store
schema is 47 and contractor count is 15 before / 15 after. Redacted config
comparison proves native model, provider, credential, channel, and plugin-policy
semantics did not drift. Slack and Telegram report configured/running with an
empty current error.

Agency profile `linux-task-agency-router` uses provider type `litellm`, exact
requested alias/model-group `task-agency-router`, base
`http://127.0.0.1:4000/v1`, populated credential variable `LITELLM_API_KEY`, and
120000 ms. It is selected by the OpenClaw harness without changing the global,
Codex, or Claude routes. The OpenClaw gateway process has the credential
variable populated; no credential value is recorded.

### Exact-status control evidence

Fresh session `ba9ea05a-3694-4725-b2ea-0357bd16a112` began with exact first
message `agency status`. Native/Agency trace is
`c2574ce1-b81b-4e29-b66a-06293c6dde85`; Store run
`aedb79d3-79d9-428c-9eb3-90dbc8aac8c9` completed. The exact header was:

~~~text
Agency/Agencies loaded: agency-steward
Agency/Agencies delegated: none
Skills loaded: none
Actual Model selected: observed execution receipt: [general] task-general -> completed
Recruited via: deterministic
~~~

Accepted finalization `b0f9a0f4-8da2-4b54-b678-826b3a5b61bc` is labeled
`host=openclaw`. Response SHA-256
`bcba81da99187df1157a81e813538251e6108a853b2fb3265a21c9585a3794ca` exactly
matches the 680-byte assistant text in native transcript
`~/.openclaw/agents/nexus/sessions/ba9ea05a-3694-4725-b2ea-0357bd16a112.jsonl`,
whose SHA-256 is
`182788c62ac9dd84cd2c73390f10bbb0e4868826cdb0d9df67bbd7c7b1b980da`.
Routing decision `ea8821a5-b220-474b-9713-0fbb1e8d0498` abstained
deterministically. Request-scoped binding
`rmb-aa818901a43ad2bacee6d93edd010488` correctly has no durable resident row.
There are no specialist or skill rows. Native parent receipts used
`task-general` with zero fallback. This is status-control, finalization, and
delivery proof only.

### Agency inference failure and AR-273 repair checkpoint

The only harmless skill attempt used genuinely new text and was not retried.
Trace `9384d3a3-0a28-4150-a8fa-ab493efda7bf`, run
`a5504721-0aa9-4fa3-98df-f5667c933b5b`, and failure receipt
`3193483a-712b-4c1d-8f13-ccb6799433a1` record `preflight_failed` /
`workforce_inference_failed`. Both planner attempts automatically selected
harness `openclaw`, profile/provider name `linux-task-agency-router`, provider
type `litellm`, and exact requested model/model-group `task-agency-router`. Both
were rejected as `provider_response_contract_invalid`; no fallback to Codex,
Claude, or any other provider occurred. No Store-backed header, finalization,
skill row, routing decision, specialist, or model receipt was written. The bare
native word `Loaded.` is therefore not successful Agency skill evidence.

AR-273 traced the strict rejection to Agency's generic HTTP payload. The
LiteLLM/OpenAI-compatible path requested JSON-object mode but never supplied
the already bounded Agency schema to the model. It also recorded a configured
LiteLLM thinking level without forwarding it. The alias mapping was not the
defect and remains operator-owned and unchanged.

The retained pre-fix regression has six failures: two absent schema
instructions and four absent LiteLLM reasoning levels. The smallest repair
adds one deterministic schema instruction shared by compatible HTTP paths and
forwards `thinking_level` as LiteLLM's standardized `reasoning_effort`.
Strict local validation, bounded retries, fallback behavior, requested-alias
evidence, and actual-model reconciliation are unchanged. Exact regressions
pass 7/7; the affected warning-strict inference slice passes 134/134. No
shared-proxy, alias, host, credential, or host-native model configuration
changed. Live proof waits for the repository-required clean checkpoint.

No post-proof Telegram-scoped Store run has arrived. Operator `/new` plus exact
`agency status` is still required for Telegram delivery proof. No OpenClaw or
Hermes host canary ran, Rule 4 remains outside this package, and no AR-119 matrix
cell moved.

### Post-AR-273 install and retained live result — 2026-08-22

Agency-only install `4dd7ee41-121f-4cde-a391-9cecd0665d72` projected the
AR-273 repair into the existing OpenClaw host. Bundle digest is
`51320b45f63cc68db52b267928c1939ab908052f623900a51786228c5b978419`;
runtime digest is
`c71fbb41ca8780b5e5a5424ef240dbf92bdf56a36dbc9d2caac70dcfa22d3497`;
launcher SHA-256 is
`755ec953638d85b175f1b4aa705e9cc388cde3d5011520a6bfc7f2986528a78c`.
OpenClaw itself was not reinstalled. Its pre/current config comparison changes
only `meta.lastTouchedAt`; primary remains `litellm/task-general`.

Fresh exact first-message control session
`b610efe7-4e71-43c7-8011-fb13f2736f2b`, trace
`de166bdc-d649-462d-996b-b2b030a34a8e`, and run
`c5e8d0bd-99b5-431c-9bb3-6bead5d2eeef` completed. Routing decision
`bf93dd03-9d01-4043-a779-49ddee0adff8` abstained deterministically;
finalization `cbc9107f-a34a-4fad-b919-17f3e1ae1d44` accepted. The exact header
remains the five lines above with request-scoped binding
`rmb-5ccde2d9de6ac9c0ca8f254cb45e9a85`, which is correctly non-durable.
Transcript SHA-256 is
`2eeec604f55265e6c245944c2b7fa840c530efc50abb4ea37ac3cdab889049a3`.

The required distinct substantive session
`31f52706-f329-4640-a012-c9540e283770` reached the OpenClaw 180-second
provider-phase ceiling and is retained as a timeout, not a pass. Its transcript
SHA-256 is
`07257c4875c2526cbb7447be73ff74f2ea7333efd74b67925356dad812a70289`.
Agency trace `517c2c78-95e6-4dea-bfd7-b43f6d48671a`, run
`c080b393-72fd-4133-9485-d3e786e6c90a`, and failure receipt
`de5f98bc-ca21-4b9b-b881-d862bf5b4da8` record one
`provider_no_valid_response` attempt. It automatically selected harness
`openclaw`, profile/provider `linux-task-agency-router`, type `litellm`,
and exact requested alias/model-group `task-agency-router`, with zero
fallback. The OpenClaw process has `LITELLM_API_KEY`; LiteLLM returned HTTP
200 at the attempt boundary. No routing, finalization, skill, specialist, or
model row was created, and no actual answering model is available.

The proxy has no Agency callback. Exact response-envelope classification now
waits on explicit permission for one local diagnostic that uses the existing
credential only in memory and emits only field types, lengths, and parse
booleans. The rejected permission attempt sent no request and exposed no value.
The consumed substantive input will not be retried unchanged.

### Approved envelope classification and exact-schema repair

Lucas approved one content-free local diagnostic against the existing
`task-agency-router` alias. It read the populated `LITELLM_API_KEY` only
from OpenClaw process memory and never printed, wrote, or retained the value.
Only types, lengths, and parse booleans were emitted. The response was HTTP 200
and 477 bytes with a normal OpenAI choices/message envelope, no error, no tool
calls, and no separate reasoning content. Its 157-character content was braced
JSON and parsed as an object, but its four keys did not match the exact
two-property closed schema. The model field was present but its value was not
retained and is not actual-model evidence.

This proves endpoint reachability, authentication, alias acceptance, and
response-envelope compatibility. It also proves the remaining failure is not
an OpenClaw channel or LiteLLM transport defect: prompt-only schema delivery
does not enforce `additionalProperties: false` for the current routed model.

The installed LiteLLM 1.94.0 implementation maps the OpenAI-standard
`json_schema` response format to the routed provider's native schema format.
The focused repair therefore changes only LiteLLM Agency payloads to send the
exact bounded schema with `strict: true`; schema prompt delivery and strict
local validation remain. No target inspection, alias remap, retry, fallback,
proxy callback, host model, or credential configuration is added. Direct
OpenAI-compatible and other adapters remain unchanged.

The focused test failed before repair only on `json_object` versus exact
`json_schema` and is retained at
`/tmp/ar273-litellm-native-schema-red.xml`. The repair plus unchanged
OpenAI-compatible and reasoning behavior passes 6/6 at
`/tmp/ar273-litellm-native-schema-green.xml`. This is local code evidence;
the repair is installed but not yet live-proven.

### Exact-schema install and restart receipt

Local commits `fba12371` plus `6ad46fb4` were clean before mutation. Fresh
online backup
`~/.agency-runtime/backups/ar273-exact-schema-preinstall.TuZp2cjN/agency.db`
has schema 47, integrity `ok`, and SHA-256
`731934b20258feacf7d8835a9ba8e32d41844cd5685eef8ca65ad3dc1d51734f`.
Installer contractor count was 15 before and after.

Only `openclaw-gateway.service` was stopped. Agency install
`b526ecdc-a538-4797-a8e8-656ecb3b315b` completed with bundle
`94d87723b900387f9dbad0dda73613b449332c34683a4fd68674c0e354314a22`
and left the gateway inactive. The installed launcher references this checkout
and runtime digest
`71c917a91ed3527065447e6aa5ec4e36466d1710f7f5d0a41411a5ac585decda`;
launcher SHA is
`fe71017957b7060d7480fa80b222455b2cc69fe42d2f7b9c71e98ba65573b01b`;
install-manifest SHA is
`4760bbee202e904a81e54e8e41723bd52d18840906da409c9d4cb97d26624503`.

The same gateway service restarted RPC-green. The plugin is enabled,
activated, loaded, and imported with ten typed hooks, `agency_finalize`, and
zero diagnostics. Telegram and Slack are both running, connected, and
probe-green. OpenClaw config changed only at `/meta/lastTouchedAt`; native
primary remains `litellm/task-general`. Agency, Hermes, Codex, and Claude
hashes remain respectively `43367ec9`, `a984d934`, `8f375701`, and
`27dafb27`. Hermes gateway/dashboard and LiteLLM stayed active. Post-install
Store integrity is `ok`; fresh live turns remain pending.

### Post-install exact-status control

Fresh session `fe3ab39c-fea0-4974-82b2-c85478b10b8a` used exact
`agency status` as its first message. Trace
`3b26c907-2c9d-4240-8160-8c6d7cce6a08`, Store run
`7d9e7bc3-3268-419e-8358-a3ef2ccf93c7`, routing decision
`19de0955-1cb8-40b0-a307-69cf3e001242`, and finalization
`97eaacb8-9dcf-4431-8150-0e1d702e8ce3` completed. Transcript SHA is
`9f37ed86db9cd7ff600955a706c0d0e328ce6e79e85113bb5b8f649b503ba922`;
the sole 531-character assistant response hashes to Store response
`a1d0eba85a66bfa728275ce62f16e0566b7d5be563333ba4fc66303fadcc6ba6`.

~~~text
Agency/Agencies loaded: agency-steward
Agency/Agencies delegated: none
Skills loaded: none
Actual Model selected: observed execution receipt: [general] task-general -> completed
Recruited via: deterministic
~~~

Request-scoped binding `rmb-1d107f497436b916ad7b32775b1a630d` correctly
has no durable resident row. No skill or specialist row exists. Model receipt
`25199eb6-6e9e-4b7b-a2d4-b365a9400053` records requested/model-group
`task-general`, zero fallback, and actual unavailable. This is control and
delivery proof, not LiteLLM workforce inference.

### Deferred Hermes bundle

Hermes effective home remains `/home/holeshot/.hermes-nexus`; its gateway and
dashboard stayed active. Redacted config SHA-256 remained
`a984d9343cbd56b7ac3bb70586ce4db90a739d6a063a530b9183c5baca1e170d`, and no
Agency launcher was created or changed for Hermes in this package. Install,
fresh session, Store, skill, provider, and child fields are deliberately
`not run — owner-directed break-glass preservation`, not failed or successful
evidence.

### Exact-schema workforce inference and native skill-evidence gap

The next genuinely new work unit remained in post-install OpenClaw session
`fe3ab39c-fea0-4974-82b2-c85478b10b8a` and produced Agency trace
`402e37f5-f38e-425b-95c6-62e911be2566`, completed Store run
`4963f31f-e114-4fa0-b051-8ded1ded51a1`, routing decision
`982f6c68-ac38-41a3-a84a-b7b60bee39cb`, and accepted finalization
`cfb2e3de-9a2b-4fda-9194-6edcb52ca3a5`.

The routing receipt records three applied structured provider stages. Each
selected harness `openclaw`, profile/provider `linux-task-agency-router`,
provider type `litellm`, and requested model/model-group
`task-agency-router`. Neither Codex, Claude, nor any alternate provider
identity appears. Wrapper receipts carry the requested alias but no
authoritative actual answering model, so actual model remains unavailable.
Specialist rows are:

- `80c52f54-3390-4f06-81e1-0ddca89ebe27` — `cms-developer`
- `866003fb-e74a-491c-a422-1ea64dd4c677` — `web-gis-developer`

Store response SHA-256
`7c785b301b68e65a42c6a69f01537821a398bca2d7a238c598a75890f2b8c2f5`
matches the 475-character native assistant response. The extended transcript
is
`~/.openclaw/agents/nexus/sessions/fe3ab39c-fea0-4974-82b2-c85478b10b8a.jsonl`,
SHA-256
`0ebf3b397080865fd6ffad8e289bd9558e8b646ff35a37c465ebd46b87f3560b`.
The delivered five-line header was:

~~~text
Agency/Agencies loaded: agency-steward, cms-developer, web-gis-developer
Agency/Agencies delegated: none
Skills loaded: none
Actual Model selected: workforce inference: [router] task-agency-router -> linux-task-agency-router/task-agency-router (wrapper)
Recruited via: inference
~~~

The transcript records native tool `read` with exact path
`/home/holeshot/.npm-global/lib/node_modules/openclaw/skills/weather/SKILL.md`,
which exactly matches the bundled, eligible, model-visible Weather inventory
entry returned by `openclaw skills info weather --json`. It then records
`agency_finalize`; no child or delegation tool ran.

The visible prose says Weather was loaded, but there is no `skills_loaded`
Store row and the authoritative header says `Skills loaded: none`. This turn
therefore proves exact-schema LiteLLM workforce inference and final delivery,
not skill loading. AR-274 owns the bridge defect: bounded serialization drops
`path`, and the adapter does not inventory-authorize native `read` as a
canonical skill event. No host canary ran and no AR-119 matrix cell moved.

### Pre-live AR-274 repair receipt

Expected-red JUnit `/tmp/ar274-openclaw-native-skill-read-red.xml` contains
exactly two failures: the adapter authorizer was never consulted and the
generated transport exited 37 because `path` was absent. The fixed focused
receipt `/tmp/ar274-openclaw-native-skill-read-green-v3.xml` passes 22 tests
with one skip. The affected warning-strict slice at
`/tmp/ar274-openclaw-skill-read-affected-slice.xml` passes 453 with one skip.

The repaired boundary is deliberately narrow:

- generated OpenClaw transport preserves only bounded `path` in addition to its existing allowlist;
- traversal, relative, hidden-key, and non-`SKILL.md` candidates are rejected before inventory dispatch;
- inventory uses fixed argv `openclaw skills info <key> --json`, bounded output, five seconds, owned-process containment, and the OpenClaw-only least-privilege environment;
- name, `skillKey`, `filePath`, `baseDir`, `eligible`, `modelVisible`, and all disable/block flags must match exactly;
- mismatch, malformed/truncated/failed inventory, and failed native reads create no Store skill row.

A read-only helper smoke matched the installed Weather inventory and returned
only `weather`. This is not a host skill proof. The next accepted evidence must
come from an Agency-only reinstall and a completely fresh OpenClaw session
using a genuinely different harmless skill. No host canary or protected-host
change occurred.


### Final OpenClaw-only result — blocked at alias planner contract

~~~yaml
host: openclaw
checkout_sha_at_final_live_turn: 5651d063
host_version: OpenClaw 2026.7.1-2 (0790d9f)
profile_identity: linux-task-agency-router
native_litellm_config_source_redacted: ~/.openclaw/openclaw.json; primary litellm/task-general unchanged
litellm_base_url_source: ~/.agency-runtime/agency.yaml
credential_env_name: LITELLM_API_KEY
credential_present_boolean: true in the OpenClaw service environment
agency_inference_profile: linux-task-agency-router
requested_alias: task-agency-router
model_group: task-agency-router
actual_model_and_receipt_source: unavailable; LiteLLM wrapper returned the alias and the shared proxy cannot load the Agency callback
runtime_digest: 6afbaf655371ae1007d3817baebb188f379c10f4b45ff8c8fe0c67503335adcb
store_schema: 47
install_result: 3aac2a46-e638-46d6-812d-d2df2ea3aa0b completed; OpenClaw package not reinstalled
launcher_manifest_sha256: f6962d190ee366d44724691fb01204c79bed3217ee615e83da6be7022845eb36
status_session_id: 94f92dc5-a0c5-44a7-bfa0-1663d948025e
status_trace_id: e5b43276-ff90-43a7-923e-9956ac278816
status_finalization_id: 30625a68-a8a5-479f-8cae-07396eec05d8
skill_name_and_store_row_id: healthcheck / 3dd34973-d2f5-4b38-adcf-51191f374214
skill_trace_id: 11707056-a490-4cbc-97b6-9a8e621caa79
skill_finalization_id: 47c0a487-916a-42cb-9d97-54ee205a0a7f
provider_attempt_status: three applied stages on the accepted skill turn; two rejected planner stages on each final substantive attempt
fallback_count: 0 for Agency inference attempts
timeout_or_failure_receipt: 7fba14ce-c3df-4459-8462-542f7272a426; fe0c2f6b-e9be-45a6-b15a-f450c7e8a154
known_limit: substantive acceptance blocked until the existing alias target returns a schema- and semantic-valid planner object
~~~

The status header delivered `agency-steward`, no delegation, no skill, native
`task-general`, and deterministic recruitment. The accepted skill header added
two specialists, `Skills loaded: healthcheck`, exact wrapper alias/profile, and
inference recruitment. The two substantive native answers are deliberately not
reproduced as headers because neither has a Store finalization row.

Before/after contractor count is 15/15. Store integrity is `ok` before and
after. Agency config SHA remains `43367ec9...`; OpenClaw `341edbcb...`, Hermes
`a984d934...`, Codex `8f375701...`, and Claude `27dafb27...` are unchanged.
Telegram and Slack are running, connected, and probe-green. Hermes remains
deferred and untouched as owner-directed break glass. Codex OAuth/model and the
consumed Codex canary were not touched; no host canary, push, PR, tracker write,
hosted workflow, alias-target change, or matrix movement occurred.


### Pre-live AR-275 planner diagnostic and repair receipt

The terminal receipts above are immutable and remain intentionally generic;
they were written before AR-275 and cannot be enriched after the fact. The new
expected-red slice retained four failures/four passes showing that exact local
planner codes stopped at the workforce attempt boundary. The repaired slice is
8/8 green, and the affected planner/intent/preflight/routing slice is 178
passed/1 skipped with process-local umask `0077`.

The candidate adds no provider, model, host, or alias specialization:

- plan-policy rejection records its exact closed-vocabulary violation codes;
- any other deterministic planner semantic rejection records only fixed code
  `plan_response_semantic_invalid` in the durable receipt;
- terminal projection rejects any unknown, malformed, or over-bound code list;
- the one existing repair call receives a complete-replacement compact-plan
  instruction that requires schema-only fields, all listed corrections,
  earlier-only dependencies, and unchanged assurance policy;
- strict local parsing remains authoritative and zero protected-provider
  fallback remains unchanged.

No Agency install or OpenClaw turn has used this candidate yet. The next proof
must come from this exact checkout after a clean local commit pair, an
Agency-only install while OpenClaw is stopped, native restart, and a genuinely
new substantive prompt. Hermes remains running and untouched break glass.

Pre-live gates are green for docs, full ruff, the 827-test production spine,
134 UI tests, and routing evaluation. Decision conformance did not execute its
mutations: the trusted isolated fixture selected `/usr/bin/python3.12`, which
lacks pytest, for both the default and changed system-Python invocations. That
platform limitation is retained and is not reported as a conformance pass.


### Post-repair OpenClaw input-gate installation and bounded result

~~~yaml
host: openclaw
checkout_sha: 77bfd2aed518bef194e1074d432749ae86b0dd28
clean_tree_at_install: true
host_version: OpenClaw 2026.7.1-2 (0790d9f)
profile_identity: linux-task-agency-router
native_litellm_config_source_redacted: ~/.openclaw/openclaw.json; primary litellm/task-general unchanged
litellm_base_url_source: ~/.agency-runtime/agency.yaml
credential_env_name: LITELLM_API_KEY
credential_present_boolean: true in the OpenClaw process; value never emitted
agency_inference_profile: linux-task-agency-router
requested_alias: task-agency-router
model_group: task-agency-router
actual_model_and_receipt_source: unavailable; response.body.model repeated the alias only
bundle_digest: 3139ec9cd2ea922efc17322bf065b94975fcbbbd5bd215d7b96fcd63fbcbbeac
runtime_digest: facf804723021f33d5f7443cb4741c12bf6476e5f262e23cc6133d257ae5515f
store_schema: 47
install_result: ba074210-c785-4d61-a014-c2f86dfdb571 complete; Agency plugin only
launcher_manifest_sha256: b67bb58962df97d83ce82aee4b52d046f48ed4ffb3cb6d4e62930a5ec20ba860
fresh_session_id: none; native turn withheld after failed Agency-only admission
agency_trace_ids:
  - 52223cc2-3249-42af-ba44-9d2dfb612a01
  - bd2feabc-98a4-48d5-a113-d9c8efd2f7c9
  - 71c4ad65-806e-4d36-87b7-91be135a3988
first_response_artifact: none
header_exact: none
resident_binding_id: none
routing_decision_ids: none; CLI diagnostic routing uses no Store writer
specialists_loaded_ids: none
skill_name_and_store_row_id: no new skill turn; prior healthcheck proof retained separately
provider_attempt_status:
  - planner applied; recruiter rejected then repair applied; safe abstention
  - planner dependency repair applied; recruiter returned no valid response
  - planner dependency rejection; repair rejected for missing codebase discovery
fallback_count: 0
timeout_or_failure_receipt:
  - /tmp/ar276-openclaw-agency-route-repository-map.json sha256 5ce8cbad926c8f98cc5a90671c73897529b73c0eb324f0f33dbff0d57f73b027
  - /tmp/ar276-openclaw-agency-route-onboarding.json sha256 35736b6a8de265dc5d72fbcc37dd02f9491b872bc6f77e4da0fb93a72bd92e88
known_limit: existing alias target did not produce an accepted strict team within fixed repair budgets
runtime_control: enabled; host-only soft-off was not authorized or applied
~~~

The post-install OpenClaw config SHA changed from `d30386ac...` to
`97b18a21...`; a comparator that emitted only JSON pointers found exactly
`/meta/lastTouchedAt`. Native providers, 21 LiteLLM aliases, primary, six
fallbacks, Telegram, Slack, and Agency's alias target were unchanged. Agency
config SHA remains `43367ec9...`; Codex remains `8f375701...`, including its
previously authorized disabled MCP flags. Hermes remained active break glass.

The first Agency-only trace was retained in the operator transcript. The two
file artifacts retain the later complete CLI results. All three automatically
selected OpenClaw and the exact Agency profile/provider/alias; none silently
fell back to Codex OAuth, Claude, Ollama, or another provider. Because these
diagnostic routes do not write the Store, they cannot prove a host header,
resident binding, routing row, skill row, or finalization.

Telegram and Slack transport probes are green, but Agency remains fail-closed
for substantive OpenClaw turns while the alias target cannot satisfy the
strict contracts. The exact reversible availability command is
`/usr/bin/python3 -m agency_runtime.cli off --agent openclaw --json`. Its dry
run passed; applying it was rejected because disabling enforcement requires
fresh explicit owner approval. No workaround was attempted.

Before/after contractors are 15/15. Store integrity is `ok` before and after;
the post-install online-backup SHA is `64c65d70...`. Codex OAuth/model/canary,
Claude, ZCode, Hermes, and their native configurations were untouched. No host
canary, push, PR, tracker mutation, hosted workflow, alias-target change, or
matrix movement occurred.


### Authorized free-model comparison and first native permission failure

~~~yaml
alias: task-agency-router
alias_deployment_id: d594b69b-26f8-4bec-8531-e6c191ab6f6c
litellm_deployment_count_before_after: 103/103
unrelated_db_rows_changed: 0
configured_target_sequence:
  - ollama/qwen3.5:2b
  - ollama/qwen3.5:9b
  - ollama/qwen3-coder-30b-a3b-128k-rocm
qwen35_9b_trace_ids:
  - 23da5198-3cbc-4771-9c8e-a2b144b2d2fe
  - a4121506-ec2a-4917-8cd8-dde045c555c4
qwen35_9b_results: critic veto; recruiter no-valid-response
qwen3_coder_exact_trace_id: 7a094495-edbc-471d-8c9d-9a557f3c7ac6
qwen3_coder_exact_result: accepted; planner/recruiter/critic applied
agency_profile: linux-task-agency-router
provider_type: litellm
requested_alias_and_model_group: task-agency-router
fallback_count: 0
actual_model_and_receipt_source: unavailable; response.body.model repeated alias
native_session_id: ar276-openclaw-nexus-status-20260822-160727
native_trace_id: 341ec5f5-9343-499f-8a73-d0c6cb08426c
native_store_run_id: 7daf7c70-c87b-4ed7-bf31-3e093bab73b5
native_store_status: response_invalid
native_runtime_context_chars: 0
native_model: litellm/task-general
header_exact: none
native_response_artifact_sha256: 32626d10a9ef3168b72832aa00dcb36302ba2670c04b90795e10aa4a9ee42247
native_transcript_sha256: e93fc7ec50f00828ec48aef60145b3c6fc0db7ee4fb088daae5e827597c1615b
known_limit: candidate prompt-injection permission repair not installed yet
~~~

The first CLI attempt is separately preserved as an OpenClaw-native failure:
the obsolete default agent `main` was rejected before Agency with artifact SHA
`8fb7be77...`. A changed command discovered and used configured default agent
`nexus`; it is not an unchanged retry.

The installed plugin entry currently grants only `allowConversationAccess`.
OpenClaw's installed 2026.7.1-2 type/schema contract says prompt mutation from
`before_prompt_build` requires `allowPromptInjection`. This accounts for the
otherwise contradictory evidence: Agency preflight created and stored the
exact run, but its finalization instructions never entered the model prompt.
The repair changes only Agency's OpenClaw registration command plan and tests;
it does not alter OpenClaw's primary/fallback models or any protected host.


### Permission-enabled failure and prompt-build-order candidate

~~~yaml
agency_install_id: 18b2d5f7-a931-4606-8d6f-9e30937cfbcc
bundle_digest: e882b13971f5449e2ee150fe78aee5077b3b533c710704deec0d6847611ab065
runtime_digest: 6837a9d8e16fe191618b9376268f3c39cd4e859f1f8fe09d498a80a9673beed1
launcher_sha256: 8c7f9d36e1d0fadc63c80c2c6281f12a5f58d05122d2fbb9a2b453a3fcf30769
openclaw_config_changed_pointers:
  - /meta/lastTouchedAt
  - /plugins/entries/agency-preflight/hooks/allowPromptInjection
agency_config_sha256: 43367ec9aa05a66fc2a60bb254f270836fb3616753769115fabb253a04d5d9f8
fresh_session_id: ar276-openclaw-nexus-status-promptfix-20260822-a
native_run_id: d343b0c0-68a9-4857-b8d3-41cd3125cd3a
native_status: ok
runtime_context_chars: 0
header_exact: none
response_artifact_sha256: d3fd3a019a41716ef53607b8e4e19e1fb98836044d907906a043e51a9fb132b6
transcript_sha256: 470ab1e23c02a8d5bdce58633763071f4596c2938849686beaf7affb272330b4
failure: installed host runs before_prompt_build before before_agent_run
expected_red: generated plugin exited 204 before repair
focused_green: 46 security-boundary; 36 native-installer; 24 adapter-parity; 1 host-boundary; 46 registration
known_limit: corrected prompt-build-order candidate not installed yet
~~~

The failure is independent of the Agency inference model. The native host used
its unchanged `task-general` route only because Agency context was absent. The
corrected candidate moves no LiteLLM alias, OpenClaw provider/model, channel,
Hermes, Codex, Claude, or ZCode setting.


### Prompt-build-order live proof and native-budget model pivot

~~~yaml
host: openclaw
checkout_sha: 1a737ef8c02323b49dd3f21562910b5327243b88
host_version: OpenClaw 2026.7.1-2
install_result: 1eeba99b-49a1-4db5-b561-9d985c30d29e complete; Agency plugin only
launcher_manifest_sha256: 391a57596565b3682aa7250b0af1ff4594aed1aea914b3df47a3636e7242d0de
runtime_digest: 5b67d882db947e9b29c62e1cde0b7f15c5202cac009c4ff4168d511fb3ffe0b3
contractors_before_after: 15/15
fresh_session_id: ar276-openclaw-nexus-status-promptorder-20260822-a
status_trace_id: bf21e9a8-a9f0-442b-9d75-78dab94687d6
status_store_run_id: c571cf9b-a990-4551-ba76-f0cb27e137ce
status_routing_id: e2a41ef8-15cd-4242-8b6d-11a720227728
status_finalization_id: dec9e3fb-c8fc-4b14-a072-794171263f8b
status_response_sha256: b02a2f18dc4fa8c1a87cb42197cf2016d4136e8776f4b19fce214101269f3e5d
status_transcript_sha256: e009951b3824ba0df128c493c1063c6fb2dd278bf9984a7d3e7fab7d245a8331
header_exact: five lines; agency-steward, no delegation, no skill, task-general control receipt, deterministic
skill_request: loop-library; read-only, no execution/network/delegation
skill_trace_id: 2c4e81be-05b7-41a0-a570-34a1ae639a70
skill_store_run_id: eeb31163-27d8-4091-986f-35d03a8e64b2
skill_result: hook_block after 80744 ms; no skill row or success claim
skill_response_sha256: d8e84b4ada75d6dded2993c84679a5c44a1faa26e6928c99f3f2e83c8c358e58
alias_deployment_id: d594b69b-26f8-4bec-8531-e6c191ab6f6c
alias_current_configured_target: ollama/qwen3-14b-abliterated
alias_reasoning_effort: none
unrelated_deployment_identity_hash_before_after: ca74e5979051b908bf1e8f42529a5595b2155750dc63c602777191bb5d2d6b42 / same
litellm_deployment_count_before_after: 103/103
first_14b_diagnostic_trace: 6a761259-b7e1-49fc-b4c9-ecaa18cd6da7
first_14b_diagnostic_result: zero attempts because credential absent in diagnostic process; not a model verdict
accepted_14b_diagnostic_trace: 2317d975-c960-4020-8755-f32308ffe94b
accepted_14b_diagnostic_result: planner/recruiter/critic applied in 37768 ms; exact profile/provider/alias; no provider fallback
accepted_14b_diagnostic_sha256: 673c5ae7bb36047ea08f1ab672ee674007060c190e8d0e4e9aa02c1170eb6f61
native_skill_session_id: ar276-openclaw-nexus-tmux-qwen14b-20260822-a
native_skill_trace_id: 79abdac7-42f1-44e9-afad-bf5556df62aa
native_skill_store_run_id: 6b7651b6-7d9d-472f-a900-6bf16f8b7b2f
native_skill_routing_id: 1908650f-a11f-4fbb-ba87-5759c530fc66
native_skill_binding_id: rmb-1910789900fdbb5e90e52eed3f4c3874
native_skill_specialist_id: 5f11b004-926f-450b-8561-c8e9aca643a4
native_skill_name_and_row_id: tmux / b54c5916-f86d-450f-b2e8-b9007137b489
native_skill_finalization_id: 64a97d43-d992-44eb-8912-de164a1dc923
native_skill_header: five lines; code-reviewer, tmux, no delegation, wrapper alias, inference
native_skill_response_sha256: 7f9a4674fce7de9ecacb339b12377769c494bb782e302d155715d1782c73696e
native_skill_transcript_sha256: 499187e8d776a117bfe374d8951c1dabead7a62d8266360547afabd2fd774afa
telegram_slack: running, connected, probe-green
actual_model_and_receipt_source: unavailable; never inferred from alias
known_limit: exact substantive native acceptance and post-live Store backup remain pending
~~~

The successful control header is real host delivery but deterministic routing.
The subsequent timeout proves fail-closed behavior and the practical native
latency limit; it does not prove LiteLLM workforce success. OpenClaw native
model configuration, Hermes, Codex OAuth/model/canary, Claude, and ZCode were
not changed.


### Exact substantive failure and AR-277 pre-install checkpoint

~~~yaml
host: openclaw
fresh_session_id: ar276-openclaw-nexus-restart-qwen14b-20260822-a
agency_trace_id: 35efa94c-d8d9-4354-863f-d22ad852ca22
store_run_id: e2e9e65d-540c-4aa7-86c5-b945cbc6ac62
routing_decision_id: c6e5e20a-af1c-454b-8344-cc66b2b9f187
routing_result: accepted; three LiteLLM stages; exact profile/alias; fallback_applied false
specialists_loaded_ids:
  - 264de90e-98d6-4c0f-8d8d-a715a3d2d64b
  - eb405fb2-4a10-48b2-acba-68743ae39c61
skill_name_and_store_row_id: openclaw-operations / 050e585d-f042-46f8-8b24-95b656e605b2
finalization_id: 7d5428e7-469f-45cd-9920-da553e4cfa7e
finalization_status: response_invalid; all required header fields missing
native_failure: task-general omitted agency_finalize after read-only tools
response_sha256: f4f6d7b7fb311119ce53ca9e58a87e3c83e450ca184eb8f335f255aaf834e256
transcript_sha256: f0f9e3596666c779c7a555368f1b1c3971323800cbe41c67e5b7011c86639f04
telegram_delivery: none claimed; invalid response is blocked before queueing
rejected_candidate: one host revision; never committed or installed; conflicts with ADR-0120
replacement_expected_red: exit 219; sha256 1c2f962e1c1e9d1bb412a79a064cfc90659e8f9d14d477c5ad5c5e986e17a05d
replacement_focused_green: 2 passed
affected_green: 47 security-boundary; 36 OpenClaw installer; 24 OpenClaw adapter-parity
candidate_install: pending clean local checkpoint
actual_model_and_receipt_source: unavailable; alias is not promoted to actual model
known_limit: fresh changed substantive first-pass delivery and post-live Store backup remain pending
~~~


### First-pass installation and changed native timeout

~~~yaml
host: openclaw
checkout_sha: 7be371d28ea4c16cc9b30c87df4a2336dd56eb50
clean_tree_at_install: true
host_version: OpenClaw 2026.7.1-2 (0790d9f)
profile_identity: linux-task-agency-router
native_litellm_config_source_redacted: ~/.openclaw/openclaw.json; primary litellm/task-general and six fallbacks unchanged
litellm_base_url_source: ~/.agency-runtime/agency.yaml
credential_env_name: LITELLM_API_KEY
credential_present_boolean: true in the OpenClaw process; value never emitted
agency_inference_profile: linux-task-agency-router
requested_alias: task-agency-router
model_group: task-agency-router
actual_model_and_receipt_source: unavailable; alias is not promoted to actual model
bundle_digest: 521b1480e190a1d0219c5ac5c691d4bf7ed32be609c61ec7f4ef495fb59ae78d
runtime_digest: b5d546a66231123190d8830737aa371d9ef6e3388ce92ea0e44195d5c87c4d17
store_schema: 47
install_result: e834190a-0dfe-4fba-a0cd-df2d7d75e250 complete; Agency plugin only
launcher_manifest_sha256: 41415e79f5ef50c817b56d09b3917c0ceceb681bed320347dbe5ba107d92c368
fresh_session_id: ar277-openclaw-nexus-recovery-qwen14b-20260822-a
agency_trace_id: 07e5ec33-7f33-4a0f-966e-d93ff4361b68
store_run_id: 6726b5ce-c632-4af4-8f37-5a99301835d0
first_response_artifact: /tmp/ar277-openclaw-live-recovery.json
header_exact: none
resident_binding_id: rmb-b4e69972cc5b6a018df30f58d2895df9; request-scoped
routing_decision_ids:
  - f609772b-7536-4eef-8af8-e510cefe20a0
specialists_loaded_ids:
  - 2a883959-9995-4ca7-aede-82c7a9d2aec9
  - 88aeef59-5462-400f-b491-23352d359091
skill_name_and_store_row_id: openclaw-operations / 3a57642c-907c-4350-b681-9665ac1ac718
provider_attempt_status: planner, recruiter, and critic applied through exact profile/provider/alias
fallback_count: 0
native_provider: litellm/task-general; unchanged host primary
native_tool_calls: 31 successful read-only calls; 0 agency_finalize calls
timeout_or_failure_receipt: /tmp/ar277-openclaw-live-recovery.json sha256 493a60291e32e487b47fc7ccd99625d8c8aff5a6412982dcc24f86e2fb256ec4
native_transcript_sha256: 40fac07879e601e2be0cabc2d85b64f9e3c528d96f14badd5ad6efd2819117f0
store_terminal_state: none; active/ready retained as timeout evidence
telegram_delivery: none claimed
known_limit: native host provider timed out before first-pass finalization; tighter changed proof and post-live backup remain pending
~~~

The process exited normally with a structured `timeout` result after 240.461
seconds. Agency preflight had already completed, so this does not implicate the
14B alias target. It also cannot prove delivery: no five-line header was
written and the Store has no terminal finalization for this run. The exact
input will not be retried unchanged.


### Final OpenClaw first-pass evidence bundle

~~~yaml
host: openclaw
checkout_sha: 7be371d28ea4c16cc9b30c87df4a2336dd56eb50
clean_tree: true at install and before live proof
host_version: OpenClaw 2026.7.1-2 (0790d9f)
profile_identity: linux-task-agency-router
native_litellm_config_source_redacted: ~/.openclaw/openclaw.json; primary litellm/task-general and six fallbacks unchanged
litellm_base_url_source: ~/.agency-runtime/agency.yaml
credential_env_name: LITELLM_API_KEY
credential_present_boolean: true in the OpenClaw service; value never emitted
agency_inference_profile: linux-task-agency-router
requested_alias: task-agency-router
model_group: task-agency-router
actual_model_and_receipt_source: unavailable; three Store model receipts are source=wrapper and resolved_model=task-agency-router alias only
runtime_digest: b5d546a66231123190d8830737aa371d9ef6e3388ce92ea0e44195d5c87c4d17
store_schema: 47
install_result: e834190a-0dfe-4fba-a0cd-df2d7d75e250 complete; Agency plugin only; OpenClaw not reinstalled
launcher_manifest_sha256: 41415e79f5ef50c817b56d09b3917c0ceceb681bed320347dbe5ba107d92c368
fresh_session_id: ar277-openclaw-nexus-finalizer-bounded-20260822-a
agency_trace_id: 9bea1a3f-67cc-4add-971f-d61aa23dcdea
store_run_id: c24afc99-8508-47b8-b09e-79fb9b317cea
first_response_artifact: ~/.agency-runtime/backups/ar277-openclaw-final-postlive-20260822T1922Z/openclaw-live-finalizer-redacted.json
first_response_artifact_sha256: 9ac29dd1543f3cbfa54b3a40d414e708024fc206bc008948bfff269f6cc4c2ac
full_cli_artifact_sha256: e53fdf956a44c697872549736044814f2ddb68bda1394ea662bd5eb71c2d905f
native_transcript_sha256: 5251eec00be78ab3ca5d7e0c81477c278f6673961f7322102b00effcbfbc4a43
header_exact: |-
  Agency/Agencies loaded: agency-steward, code-reviewer
  Agency/Agencies delegated: none
  Skills loaded: none
  Actual Model selected: workforce inference: [router] task-agency-router -> linux-task-agency-router/task-agency-router (wrapper)
  Recruited via: inference
resident_binding_id: rmb-7c2121c70d27094b999d6f95ab5b9ce8; request-scoped; no persistent row expected
routing_decision_ids:
  - ec9366fd-8a95-46c8-951f-069204d3d453
specialists_loaded_ids:
  - 21a36c8a-f5d0-4018-b6d8-83fb7ef1dce2 # code-reviewer
skill_name_and_store_row_id: current trace intentionally none; prior accepted skill proof is tmux / b54c5916-f86d-450f-b2e8-b9007137b489
provider_attempt_status:
  - ordinal 1; linux-task-agency-router; litellm; task-agency-router; task-agency-router; applied
  - ordinal 2; linux-task-agency-router; litellm; task-agency-router; task-agency-router; applied
  - ordinal 3; linux-task-agency-router; litellm; task-agency-router; task-agency-router; applied
fallback_count: 0; routing fallback_applied=false
finalization_id: 07759321-7b9f-42b9-bb4f-4086d3ecd167
finalization_status: accept; completed
native_host_provider_model: litellm/task-general; unchanged; fallbackUsed=false
native_tool_summary: one agency_finalize call; zero other tools; zero failures
duration_ms: 46635
timeout_or_failure_receipt: none for final proof; earlier response_invalid and timeout receipts retained separately
contractors_before_after: 15/15 exact-current packaged contractors
store_integrity_before_after: ok/ok
post_live_store_backup_sha256: 47d868f5db1350abafb8c2a4d45c56e697b83c3759e86ce2aa8169e40ce474ec
agency_config_sha256: 43367ec9aa05a66fc2a60bb254f270836fb3616753769115fabb253a04d5d9f8
openclaw_config_sha256: 8f5896749b17a7a49bbf36a8b18607c4b510cbb608627507b5068d2034c7581b
native_plugin: loaded, enabled, activated, imported; ten hooks; agency_finalize; zero diagnostics
telegram_slack: configured, running, probe-green, no reported error; event loop not degraded
channel_receipt_sha256: fef5bb702de127ef4a6291298f3b2288a0187ddedf098007261c2b4dc29a9996
telegram_delivery: automated control rejected before execution by external-message authorization boundary; user-initiated round trip remains optional
known_limit: actual backing model is unavailable; no Rule 4 child canary or matrix-cell claim; config validate/doctor remain cold-inventory degraded while live exact evidence passes
~~~

OpenClaw's scoped parent-runtime acceptance set now passes. The final proof is
both host-written and Store-terminal: one native finalizer result matches the
visible response and the Store completion. The three Agency stages used no
Codex OAuth, Claude, native Ollama bypass, or other protected fallback.
`task-agency-router` remains an opaque alias; its configured free target is a
control-plane fact, not an actual answering-model receipt.

The checkout-module `config validate` returns degraded exit 2 because cold
inventory cannot prove live plugin loading and the global legacy provider list
is intentionally unset. Native runtime inspection independently reports the
plugin loaded with zero diagnostics, and the live Store routing rows prove the
harness-scoped profile was operational. No global default was added to silence
the cold diagnostic.


### Telegram post-finalizer suppression bundle (supersedes channel-success claim)

~~~yaml
host: openclaw
installed_checkout_sha: 7be371d28ea4c16cc9b30c87df4a2336dd56eb50
candidate_base_sha: ce3cfc01e65b48f7333a5f4ce53d75aa67317d1b
host_version: OpenClaw 2026.7.1-2 (0790d9f)
native_primary: litellm/task-general; unchanged
agency_inference_profile: linux-task-agency-router; unchanged
requested_alias: task-agency-router; unchanged
fresh_session_id: 6d16c446-4d60-460d-b1ad-d534c72327db
agency_trace_id: 9ac12abc-211d-4d4d-9bd1-036b67bda388
store_run_id: 669d28d1-8ec1-4a2d-a7fa-4c6e195d1da7
resident_binding_id: rmb-fef54dccff0a71da62d23ec36ae83a1b
routing_decision_ids:
  - 3c9e6fd8-3fce-4d49-92de-d465c30cf238
finalization_id: 63140215-61d6-45ee-9d5a-7f92955569d8
finalization_status: accept; Store run completed
header_exact: |-
  Agency/Agencies loaded: agency-steward
  Agency/Agencies delegated: none
  Skills loaded: none
  Actual Model selected: none observed
  Recruited via: deterministic
provider_attempt_status: deterministic control; no LiteLLM inference claim
fallback_count: 0
native_tool_summary: one successful agency_finalize call
native_terminal_text: NO_REPLY
delivery_result: suppressed before reply_payload_sending/message_sending; nothing queued
native_transcript_sha256: fd8dc85493720c24d6a233a1b7e0449d88a1f5fa4b0f1c5e73236bc2238e7321
expected_red: focused regression exit 223
candidate_focused_green: three finalizer checks; generated-installer parity
timeout_or_failure_receipt: accepted Store result plus suppressed native terminal event; retained as delivery failure
known_limit: candidate not installed; fresh changed Telegram proof pending
hermes_and_protected_hosts: untouched
~~~

### Third Telegram failure and host-capability boundary

~~~yaml
host: openclaw
installed_checkout_sha: a8022a92ed303c6dbd41fdfa2a0f652239070a99
host_version: OpenClaw 2026.7.1-2 (0790d9f)
native_primary: litellm/task-general; six original fallbacks unchanged
agency_inference_profile: linux-task-agency-router
requested_alias: task-agency-router
model_group: task-agency-router
fresh_session_id: ac750af6-7adf-41b9-ba8a-9feee76539e4
agency_trace_id: 4552b87d-5ee3-45a3-ba61-6629bbb20e99
store_run_id: 86d3c0a2-79f0-4ea6-aa0a-adcb4056d25b
resident_binding_id: none persisted for this trace
routing_decision_ids:
  - bbf1d404-bb7b-4eb6-be3d-3b27aaf00786
specialists_loaded_ids:
  - 37ad1cc1-72c3-4d9d-b824-0b6eecd482ca # code-reviewer
provider_attempt_status: three Agency wrapper-stage receipts succeeded
profile_resolution: automatic OpenClaw harness; linux-task-agency-router; litellm
fallback_count: zero protected-host fallback; routing fallback_applied=false
actual_model_and_receipt_source: unavailable; provider telemetry reports alias only
pending_finalizer_id: f9138f55-baca-4982-9070-09dd94bb4121
terminal_finalization_id: 9599d181-a104-42a1-b166-8412add9c1d0
terminal_status: response_invalid
native_terminal_text_sha256: b07800ad4773f8feebc6d0467596ecdf82f855d96b1b1a860e4f51462d288f89
native_transcript_sha256: 81b54934daed9e1e4fc9c85d9f93dcea876328afade7c0de1f624f090982731e
native_trajectory_sha256: 38f1e716c9518deb439509a8377ef7f83157ca29e92e18649b9ee8fc2579b750
delivery_result: exact NO_REPLY normalized before reply_payload_sending; no Telegram outbound
reset_result: no acknowledgement; native command bypassed message_received and raced before_reset
reset_candidate: before_reset correlation plus bounded wait for exact native acknowledgement
focused_green: 218 passed
installed_contract_artifacts:
  hook_types_sha256: fbb4cd0a6254050fa377d4aa97b2d8176caeddea7fead3dbcfba35a987aa10c0
  agent_tool_types_sha256: 5c8487f8478b9d7aad744c0cb74ad85b445e567197591dfb4e53b2f35b44aceb
  selection_runtime_sha256: ccff13111aa60369ac9d88b526a58a7df1f733f1d99d205c01c6186036957e66
  reply_dispatcher_sha256: 5d8286ffa192f4558153b92474a53927fc190d9b2dcf780fc83a8ff0e89b487a
missing_prerequisite: supported plugin return-direct/terminal-presentation or post-model payload replacement
known_limit: reset fix not installed; substantive Telegram proof blocked on host capability
hermes_and_protected_hosts: untouched
~~~


### Full-payload repair pre-live installation bundle

~~~yaml
host: openclaw
checkout_sha: 4fab954b0224883439b978adccf95d515f753b3b
clean_tree_at_install: true
host_version: OpenClaw 2026.7.1-2 (0790d9f)
install_result: 87b518e8-dfee-4759-af7d-565705d09afa complete; Agency plugin only; installer left gateway stopped
bundle_digest: 7f94acf0178a3f4bcd5c516ec6e9e1a451e7b6222dd5006d011bc2691b834e3d
runtime_digest: 1816b6ad4bddb584a1daee6920a05fe19e7d5bbe7fcb3486fed379b5db862b55
launcher_manifest_sha256: c34c66be747a72ccdbf2a5af8df57f47957ea79c6f4128a7f46bd3deb65c166c
agency_config_sha256: 43367ec9aa05a66fc2a60bb254f270836fb3616753769115fabb253a04d5d9f8
openclaw_config_semantic_diff: /meta/lastTouchedAt only versus last-good
native_primary: litellm/task-general; six original fallbacks unchanged
agency_profile: linux-task-agency-router; litellm; task-agency-router; 120000 ms
credential_env_name: LITELLM_API_KEY
credential_present_boolean: true in restarted OpenClaw process; value never emitted
contractors_before_after_install: 15/15
store_schema: 47
pre_install_store_integrity: ok
pre_install_store_backup_sha256: 6b3b8794ccbda7f6e5777186ca88a4cd78f97a630b884b503733438eb91d3c6a
native_restart: running; RPC probe ok
plugin_inventory: enabled/loaded; 11 hooks; agency_finalize; zero diagnostics
telegram_slack: configured, running, probe-green
known_limit: fresh /reset acknowledgement and changed substantive Telegram delivery pending
hermes_and_protected_hosts: untouched
~~~

The prior final evidence bundle remains valid for CLI-only host/Store
correlation and exact Agency LiteLLM routing. It does not prove Telegram
delivery. No direct send, second model pass, invalid-draft rewrite, host config
change, or safety relaxation is part of the AR-278 candidate.


### Telegram exact-text/full-payload conflict bundle

~~~yaml
host: openclaw
installed_checkout_sha: 320dc7cf99c977edf45a3e7ad68b3c7f4d9b6f93
host_version: OpenClaw 2026.7.1-2 (0790d9f)
install_result: 74b4c0bc-8da5-4bfb-ac91-08c6e770c7ea complete; Agency plugin only
native_primary: litellm/task-general; six fallbacks unchanged
agency_inference_profile: linux-task-agency-router
requested_alias: task-agency-router
model_group: task-agency-router
fresh_session_id: 80c9c847-ff6d-4d16-b913-50e96b981a42
agency_trace_id: 2eaaf8e9-07f0-475c-89dc-f811553339ed
store_run_id: 27faf92b-4c60-430d-8401-358831c60f29
resident_binding_id: none persisted for this trace
routing_decision_ids:
  - 9528aa21-6cce-4a2c-87d8-1e4ba7722b00
specialists_loaded_ids:
  - f7ac8ffb-33af-4d93-8e54-d39471463ad1 # ai-data-remediation-engineer
  - 68d0a65b-c1da-4beb-b071-0fc7695a15b3 # technical-writer
skill_name_and_store_row_id: openclaw-operations / 0f548ebf-c080-4733-b981-5b21481fd7eb
provider_attempt_status: three wrapper receipts; linux-task-agency-router; exact task-agency-router requested/resolved; success
fallback_count: zero cross-provider or protected-host fallback; routing fallback_applied=false
actual_model_and_receipt_source: unavailable; wrapper reports alias only
finalization_id: 9b2d4c3a-121e-4043-8c72-640ebde48e74
finalization_status: accept/completed at policy-text boundary
final_text_sha256: 202f0d5817642ebd8db337179a003898474593014b54145d44b32eb918400dc6
native_transcript_sha256: e4c2d1bd606190ed5c0d06db2de3cd6ed91a52a2d381270a37047cbabd91e34a
native_trajectory_sha256: 86adbcc0ffcfe276026a94fab494758424c6abd1a46cf69821da09d1554f4976
native_terminal_text: exact finalizer result; not NO_REPLY
delivery_result: canonical outbound payload conflicted with premature text-hash terminal; fail-closed cancellation; no Telegram outbound
reset_control_result: exact /new ingress observed; acknowledgement blocked as unmarked output
candidate_behavior: defer only OpenClaw terminal commit to full-payload gate; exact one-use reset acknowledgement
focused_green: 386 passed, 1 skipped
known_limit: candidate not installed; fresh /reset acknowledgement and changed substantive Telegram delivery pending
hermes_and_protected_hosts: untouched
~~~

### Temporary OpenClaw Agency-disable recovery bundle

~~~yaml
host: openclaw
host_version: OpenClaw 2026.7.1-2 (0790d9f)
recovery_authority: Lucas selected temporary remove/disable option
agency_uninstall_dry_run: blocked before mutation
uninstall_operation_id: 952ff8f6-a660-4309-ac54-191481944440
uninstall_plan_digest: a497a256064f2ececd2f27d11993cb681628e4094d2309b398c039d89ec7e2aa
uninstall_error: Native plugin identity is not bound to the managed target
follow_up_issue: AR-269
recovery_action: stopped openclaw-gateway; native plugins disable agency-preflight; native restart
agency_native_state: registered=true; staged=true; enabled=false; effective_enabled=false; hook_count=0
gateway_state: active/running; RPC probe ok
channels: Telegram and Slack configured/running/probe-ok; Telegram inbound/outbound observed
recovery_request: exact reply with pong
recovery_response: exact pong
native_transcript_session_id: redacted by policy
native_transcript_sha256: 0420d72c8b151f3d2fb09ce0cae219b100de100db447b717089157b77386417e
native_transcript_checks: exact user request=true; exact assistant pong=true
native_primary: litellm/task-general
native_fallbacks: six original fallbacks unchanged
config_sha256_before: 1c86bf6dd5db71e49b93cc70a5e1844e03bcddeb1280f36d5bccd9d0c5c52291
config_sha256_after: b2d644ddba5c3f0eccd86eb4fa777bbb134fd2ed5e598ae892cdaa9d279c8d3c
normalized_config_sha256: 0a054704b3c999d8f220477a56764f15eb4a44aec1c9df1d82dec6a3da5ca86b
normalized_exclusions: meta.lastTouchedAt; plugins.entries.agency-preflight.enabled
launcher_manifest_sha256: c34c66be747a72ccdbf2a5af8df57f47957ea79c6f4128a7f46bd3deb65c166c
post_disable_store_integrity: ok
post_disable_store_backup_sha256: 9c193d2ed5ba8f6af266d5a72eb14ba4e6aaff25abd05478a25d95157fd2943a
known_limit: ordinary OpenClaw Telegram recovery passes; Agency acceptance remains blocked
hermes_and_protected_hosts: untouched
~~~


### OpenClaw awaited tool-result candidate - pre-live bundle

~~~yaml
host: openclaw
candidate_branch: codex/ar278-openclaw-one-pass
baseline_checkout_sha: 8d707a2b4417d42b8236c358080f92be90711c06
origin_main_sha: 4a3267738bb20519500513ea1498fc68f8ea9443
implementation_anchor_ancestor: true
host_version: OpenClaw 2026.7.1-2 (0790d9f)
current_host_state: active/RPC-green; Telegram and Slack probe-green
current_agency_state: registered/staged; natively disabled
native_primary: litellm/task-general
native_fallbacks: six original fallbacks unchanged
agency_inference_profile: linux-task-agency-router
provider_type: litellm
requested_alias: task-agency-router
model_group: task-agency-router
credential_env_name: LITELLM_API_KEY
credential_present: true
actual_model_claim: unavailable from provider telemetry
disproved_path: terminal agency_finalize tool result is non-deliverable without host terminal delivery
selected_path: awaited registerAgentToolResultMiddleware scoped to openclaw
initial_header_source: exact correlated Store snapshot at preflight
updated_header_source: exact correlated Store snapshot after awaited post_tool_call recording
natural_finalization: one first response; no finalizer tool; no NO_REPLY; no correction
final_validation: existing before_agent_finalize first-pass check
outbound_authorization: existing full-payload Store-backed reply gate
manifest_contract: agentToolResultMiddleware=[openclaw]
expected_red: exit 232 retained
focused_tests: 72 passed, 148 deselected
proportionate_tests: 289 passed, 2 skipped
install_state: candidate not installed
known_limit: live Telegram response and post-live Store/config receipts remain pending
hermes_and_protected_hosts: untouched
~~~

### OpenClaw awaited-middleware fourth failure bundle

~~~yaml
host: openclaw
candidate_branch: codex/ar278-openclaw-one-pass
installed_checkpoint: da184b4fc6170ff1bffcff8d827910e09b848f6a
ledger_checkpoint: 773d90807ce17378753af834ce93b1882f31de68
host_version: OpenClaw 2026.7.1-2 (0790d9f)
install_result: 514528d9-e373-4f87-b1c0-9d53edb9401b; complete; Agency plugin only
bundle_digest: 07189d93a9be9ea85ddd7ad396b0dacef8de6af8d6aa5904318efc35bcc442d0
runtime_digest: f0a563d9cfdc40499975c1556d25ae1e62dfc298022a2d670444646917811bad
launcher_manifest_sha256: 668ff55d04608fd599de4a81c27cee0a2af6a0d6cacb925d78bd07dc75018c99
plugin_contract: loaded; ten hooks; agentToolResultMiddleware=[openclaw]; no tools; zero diagnostics
gateway_channels: RPC green; Telegram and Slack configured/running/probe-green
native_config_delta: meta.lastTouchedAt; plugins.entries.agency-preflight.enabled only
native_primary: litellm/task-general
native_fallbacks: six original fallbacks unchanged
agency_inference_profile: linux-task-agency-router
agency_requested_alias: task-agency-router
credential_env_name: LITELLM_API_KEY
credential_present: true
reset_acknowledgement: absent; failure retained
fresh_session_id: 8936e747-e420-4801-9c0c-6d85fc9fe41a
agency_trace_id: a9afc0e8-c998-4bff-9c9e-6dce27628bb2
store_run_id: 24104a10-ad68-43a3-9a79-92603687cd1b
resident_binding_id: none
routing_decision_ids:
  - 30f6b37b-610e-4f4c-8fce-593fe4cd6d8f
specialists_loaded_ids: []
skill_name_and_store_row_id: none
routing_mode: deterministic control; abstained; workforce inference not attempted
native_parent_model_calls: three task-general calls; HTTP 200
actual_model_and_receipt_source: unavailable; sanitized OpenClaw hook reports requested alias only
native_response_chars: 665
header_exact: agency-steward / none / none / requested execution alias task-general / deterministic
finalization_id: 625e3e8c-e82c-4918-a23e-5c180760676b
finalization_status: response_invalid
finalization_missing: actual_model_selected
native_transcript_sha256: 13300aefd4fc61cefb9f789d255a0f98b376ec5c0864761cbfbc549c93c1b0a5
delivery_result: no queued reply payloads; no Telegram response
root_cause: alias-only model receipt arrived after header authorship and changed authoritative evidence
expected_red: focused regression failed on persisted alias-only receipt
focused_green: 31 passed, 1 skipped
fix_scope: Agency OpenClaw bridge only; no shared policy or other-harness change
store_schema: 47
post_failure_store_integrity: ok
post_failure_store_snapshot_sha256: df57b6a323a42dfd7e2cfa4cf97906f7960442781716c8e70ba832b778fb1509
known_limit: fix not installed; fresh changed Telegram proof pending
hermes_and_protected_hosts: untouched
~~~

### OpenClaw final-hook model-context fifth failure bundle

~~~yaml
host: openclaw
candidate_branch: codex/ar278-openclaw-one-pass
installed_checkpoint: a9276e00d1dc6862fb0f93085069c4fd5ff27ce9
ledger_checkpoint: 4b1172be4a0912eb5d12ba7bb27cf6faf95fc5d8
host_version: OpenClaw 2026.7.1-2 (0790d9f)
install_result: 175adc13-ef5f-4286-ac39-0a7584e9a982; complete; Agency plugin only
bundle_digest: 7a36d4df440e4639c8ded06664a33ba971d3be9aea5cc0e3c5bdb8c195f33e3f
runtime_digest: 8ec9583967d5d239318808b263c6236511728c67051114d34bc85a530dde9ba3
launcher_manifest_sha256: 30c5760b7032cf949b944f335f082679247e6160bd539531ef7c898ff5701a8d
plugin_contract: loaded; ten hooks; agentToolResultMiddleware=[openclaw]; no tools; zero diagnostics
gateway_channels: RPC green; Telegram and Slack configured/running/probe-green
native_config_delta: meta.lastTouchedAt only versus exact pre-install backup
native_primary: litellm/task-general
native_fallbacks: six original fallbacks unchanged
agency_inference_profile: linux-task-agency-router
agency_requested_alias: task-agency-router
credential_env_name: LITELLM_API_KEY
credential_present: true
reset_acknowledgement: absent; failure retained
fresh_session_id: cdc3a36b-e683-4c8e-bace-2545f01bd2c0
agency_trace_id: f946f532-4b53-4695-b660-36be48500dc3
store_run_id: 79a11206-3c58-4ed0-b2b8-121bf3d0fdb9
resident_binding_id: none
routing_decision_ids:
  - 50c37f62-8278-4e35-99a2-7985b97cb4f9
specialists_loaded_ids: []
skill_name_and_store_row_id: none
routing_mode: deterministic control; abstained; workforce inference not attempted
native_parent_model_calls: six task-general calls; HTTP 200
actual_model_and_receipt_source: no receipt; preflight requested alias only
native_response_chars: 1274
header_exact: agency-steward / none / none / requested execution alias task-general / deterministic
finalization_id: ae002770-f47f-4c84-890f-9ccfd37fd06b
finalization_status: response_invalid
finalization_missing: actual_model_selected
native_transcript_sha256: deeb9040a5d5036d816794ba7ba5581fb834f4948f64adee3a8d45fcdd0b6aa1
delivery_result: no queued reply payloads; no Telegram response
root_cause: OpenClaw supplies modelId at preflight but omits it from both final-hook contexts
expected_red: exit 17 retained for final-hook identity loss
focused_green: 90 passed, 1 skipped, 148 deselected
fix_scope: bounded preflight model correlation inside generated Agency OpenClaw plugin only
store_schema: 47
post_failure_store_integrity: ok
post_failure_store_snapshot_sha256: 93dc0be2c55af0930e5c54753adc70aec76eaaf57974f60a516a66820e4a7c47
known_limit: fix not installed; genuinely changed fresh Telegram delivery proof pending
hermes_and_protected_hosts: untouched
~~~

### OpenClaw installed-correlation status success bundle

~~~yaml
host: openclaw
checkout_sha: a518ed236b71774f218b6dff92222d9e4c53144c
clean_tree_at_install: true
implementation_commit: 71cb09751bc3b1f81cf4e0312765c616c305780c
host_version: OpenClaw 2026.7.1-2 (0790d9f)
install_result: c3b124d6-6a88-46b4-8c5a-706c5187457b; complete; Agency plugin only
bundle_digest: fcc48773100e557596bb449cde9a51e1e345586d4ef8813023d72db7ba74ad00
runtime_digest: 0b05a4995291b06bad15a401f68213629dbc17c7cf6fc323a302c05807866166
launcher_manifest_sha256: 317045e7e508b5577aa3b2e0e01f995d8fa630d011a1172dcb0b1de92a6be72b
plugin_contract: loaded/imported/activated; ten hooks; agentToolResultMiddleware=[openclaw]; no tools; zero diagnostics
gateway_channels: RPC green; Telegram and Slack configured/running/probe-green
native_config_before_sha256: 0f30f12d9f789da20f2e19fe92c3d3825bb93f2eb4cf707b179ee85c0f4ee8d1
native_config_after_sha256: 17784e2e1dc7a55530cb3853bb2b6eed2339c7d2a7928fa987026b4dfbec0b65
native_config_delta: meta.lastTouchedAt only
native_primary: litellm/task-general
native_fallbacks: six original fallbacks unchanged
agency_inference_profile: linux-task-agency-router
agency_requested_alias: task-agency-router
agency_model_group: task-agency-router
credential_env_name: LITELLM_API_KEY
credential_present_in_gateway: true
fresh_session_id: 5570abb9-eecc-4d77-be4b-bb9636bdf886
agency_trace_id: 78a68fdc-e192-4098-b8c7-58d20cf3bd8a
store_run_id: 6f446944-da85-4eda-8049-227bf268775e
store_session_key: retained by SHA only
store_session_key_sha256: d20c5bfbc17fd25b46d36898bccf90b16e7e54c7dc256dc9cce351542590e299
resident_binding_id: none
routing_decision_ids:
  - da98bac1-c78a-4be7-9a6b-a121386fdaf7
specialists_loaded_ids: []
skill_name_and_store_row_id: none
routing_mode: deterministic control; abstained; workforce inference not attempted
model_receipts: []
native_parent_provider: litellm
native_parent_requested_alias: task-general
agency_requested_alias_used_this_turn: false
actual_model_and_receipt_source: unavailable; no answering-model claim
first_response_artifact: /tmp/ar278-openclaw-sixth-live/status-evidence-redacted.json
first_response_chars: 489
first_response_sha256: 1e8c1df550fad3f42c8b859028de9890bbb54dc4fd8ee6526822ae9f8a1c2123
header_exact: agency-steward / none / none / requested execution alias task-general / deterministic
native_transcript_sha256: 593ddef8bbaaaa6a56e9fd4dad96ba4e0c21c3e3872584d91058641613838f70
finalization_id: 9398965e-550c-452d-9f85-3e59f2ecd029
finalization_status: accept; completed; no missing fields
telegram_delivery: outbound timestamp follows inbound; owner confirmed response
contractors_before_after_install: 15/15
pre_install_store_integrity: ok
pre_install_store_backup_sha256: d00c86f94db1910a27da13a8bece9c14c0d94f1c558354376e67653ac8f7bc7d
post_status_store_integrity: ok
post_status_store_backup_sha256: 470aa2fd018dc96ea750a953a792d7490d2e760788d8b6714dcd6d883554aeec
store_schema: 47
known_limit: control path only; skill and substantive task-agency-router proof pending
hermes_and_protected_hosts: untouched
~~~

### OpenClaw delivered skill-correlation failure bundle

~~~yaml
host: openclaw
installed_checkout_sha: a518ed236b71774f218b6dff92222d9e4c53144c
host_version: OpenClaw 2026.7.1-2 (0790d9f)
native_session_id: 5570abb9-eecc-4d77-be4b-bb9636bdf886
agency_trace_id: 6b18f9f0-a8bb-4a68-b70b-45ec7cdfe454
store_run_id: afc905ca-f68b-40c7-b694-b1842e7277c7
routing_decision_ids:
  - 26492374-3d54-4da2-8bc6-0381e83813f4
specialists_loaded_ids:
  - 5b2f0fbd-445d-41f5-9d4c-1e2a99f3ff09
model_receipt_ids:
  - db7c5f8d-43f3-48af-b185-30dd6d37eeac
  - b1b6381a-ddb5-4e93-9445-9e15ca1fa475
  - e4f42453-3ef8-41c7-9653-899dc7a0aa5d
agency_inference_profile: linux-task-agency-router
provider_type: litellm
requested_alias: task-agency-router
model_group: task-agency-router
fallback_count: 0
native_parent_provider: litellm
native_parent_requested_alias: task-general
actual_model_and_receipt_source: unavailable; wrapper receipts report requested Agency alias only
skill_read: exact native-inventory-authorized healthcheck SKILL.md
skill_path_sha256: 51ba91eb9d45fed765b8f3aca056e9f38886ca5702d3bfab41e69ba958608834
skill_name_and_store_row_id: none; failed evidence retained
header_exact: agency-steward, code-reviewer / none / none / workforce inference task-agency-router to linux-task-agency-router/task-agency-router wrapper / inference
finalization_id: d6ae9ade-b124-46b5-8822-7457a177f526
finalization_status: accept; completed; no missing fields
response_sha256: e98c6c18abdb11cf957eb2ad88b3f7d9e7913daf1bfb63fd4ba3f686ca787763
native_transcript_sha256: 76826043528f53ce1b791202c3dbdbd63a6a07d440e7e0b6baccdb090b8a1d39
delivery_result: Telegram outbound followed inbound
failure_artifact: /tmp/ar278-openclaw-sixth-live/healthcheck-correlation-diagnosis-redacted.json
failure_artifact_sha256: c742cbe4cd24c713fdbb29f25fc2ecef1221664d28bf019ac6d935be3283db05
root_cause: installed awaited middleware callback has tool args but no session/run correlation; prior Agency test invented those context fields
expected_red: generated-plugin exit 245
candidate_scope: bounded one-use before_tool_call correlation inside generated Agency OpenClaw plugin only
focused_green: 374 passed, 1 skipped
known_limit: candidate not installed; skill Store/header proof and exact substantive restart-safety request pending
hermes_and_protected_hosts: untouched
~~~
