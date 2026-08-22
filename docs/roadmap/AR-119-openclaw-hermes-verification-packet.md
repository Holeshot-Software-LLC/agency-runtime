---
title: "Exact-main Linux handoff for OpenClaw and Hermes"
status: active
category: roadmap
created: 2026-08-16
updated: 2026-08-21
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
