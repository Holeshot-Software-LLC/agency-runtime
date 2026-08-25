---
title: "Exact-main Linux handoff for OpenClaw and Hermes"
status: active
category: roadmap
created: 2026-08-16
updated: 2026-08-25
tags: [roadmap, verification, hosts, openclaw, hermes, linux, AR-119]
related:
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/roadmap/AR-119-rule-host-evidence-matrix.md
  - docs/roadmap/AR-119-founding-vision.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0158-collect-child-canary-proof-inside-disposable-host-profiles.md
  - docs/roadmap/issue-AR-273-expose-openclaw-native-finalizer-tool.md
  - docs/roadmap/issue-AR-274-model-agnostic-structured-inference-profiles.md
  - docs/decisions/0164-keep-litellm-inference-profiles-model-agnostic.md
  - docs/roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md
  - docs/roadmap/issue-AR-280-exclude-hermes-internal-post-response-preflight.md
  - docs/roadmap/issue-AR-283-persist-openclaw-child-terminals-after-delivery.md
  - docs/roadmap/issue-AR-281-route-native-children-through-host-profiles.md
  - docs/roadmap/issue-AR-282-deliver-finalized-openclaw-child-announcements.md
  - docs/decisions/0167-refresh-openclaw-headers-through-awaited-tool-results.md
  - docs/decisions/0169-authorize-finalized-openclaw-child-announcements.md
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
3. Correlate the session and trace with runs, routing decisions, specialists,
   and resident binding evidence. Request-scoped OpenClaw/Hermes must carry the
   validated binding in `runs.preflight_result` and have no persistent binding
   row; only persistent hosts correlate a `resident_manager_bindings` row.
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

### Agency inference failure and AR-274 repair checkpoint

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

AR-274 traced the strict rejection to Agency's generic HTTP payload. The
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

### Post-AR-274 install and retained live result — 2026-08-22

Agency-only install `4dd7ee41-121f-4cde-a391-9cecd0665d72` projected the
AR-274 repair into the existing OpenClaw host. Bundle digest is
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
not skill loading. AR-275 owns the bridge defect: bounded serialization drops
`path`, and the adapter does not inventory-authorize native `read` as a
canonical skill event. No host canary ran and no AR-119 matrix cell moved.

### Pre-live AR-275 repair receipt

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


### Pre-live AR-276 planner diagnostic and repair receipt

The terminal receipts above are immutable and remain intentionally generic;
they were written before AR-276 and cannot be enriched after the fact. The new
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


### Exact substantive failure and AR-278 pre-install checkpoint

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
change, or safety relaxation is part of the AR-279 candidate.


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
follow_up_issue: AR-270
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
candidate_implementation_commit: e5ae8de1e278e2f6fcb40af818663c42186f7b42
candidate_ledger_commit: 7abf9b139bacac76dd56f7559c2e76ea70d45077
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

### OpenClaw tool-correlation install readiness bundle

~~~yaml
host: openclaw
checkout_sha: c0426ab967c102f25fb530bf6355f7f6ff11b45b
implementation_commit: e5ae8de1e278e2f6fcb40af818663c42186f7b42
host_version: OpenClaw 2026.7.1-2 (0790d9f)
install_result: 251c4349-f7e3-4640-980d-055b857c0abe; complete; Agency plugin only
bundle_digest: ba344b92ad80265a6807a6fda278c1c803af20d2b9767416d41a98901b2bae84
runtime_digest: 70239e65528b4828a3a992a0a857b0684976ec50d36c80c8d89bd0e4c0740d9d
launcher_manifest_sha256: 3090708c390ecb5c6619137e328bae076f7372cc114d4b55b230e27555472250
installer_restarted_gateway: false
native_restart_result: active; RPC green; OpenClaw 2026.7.1-2
plugin_contract: loaded/imported/activated; 11 hooks including before_tool_call; middleware=[openclaw]; no tools; zero diagnostics
native_config_before_sha256: 17784e2e1dc7a55530cb3853bb2b6eed2339c7d2a7928fa987026b4dfbec0b65
native_config_after_sha256: 3060c3ee95c193780eae92199516abf53525664b8d111c893cc349d4ca71d24b
native_config_delta: meta.lastTouchedAt only
native_primary: litellm/task-general
native_fallback_count: 6
agency_config_sha256_before_after: 43367ec9aa05a66fc2a60bb254f270836fb3616753769115fabb253a04d5d9f8 / unchanged
agency_inference_profile: linux-task-agency-router
agency_requested_alias: task-agency-router
agency_model_group: task-agency-router
credential_env_name: LITELLM_API_KEY
credential_present_in_gateway: true
contractors_before_after_install: 15/15
pre_install_store_integrity: ok
pre_install_store_schema: 47
pre_install_store_backup_sha256: 3cdf39fc6518bb2b70c1ed009dc5877648dce5c62a3676edbf6ae73cc785ba77
install_artifact: /tmp/ar278-openclaw-seventh-preinstall/install-summary-redacted.json
install_artifact_sha256: 0c7698b5e398ee8bc18e068d473901b0aa3ce1dfef5dd44d28c58e9a1cc1969d
readiness_artifact: /tmp/ar278-openclaw-seventh-preinstall/readiness-redacted.json
readiness_artifact_sha256: fa3e089dfb6f627434889367a0773bfefa0be2a960bd4fa6e05ef9b03c0157ca
first_post_restart_send: not observed at native Telegram inbound edge; no Agency trace
telegram_probe: configured/running/probe-green; API credential valid; zero queued updates
next_skill: tmux; native inventory eligible and model-visible
known_limit: fresh status, skill Store/header, and exact substantive restart-safety proofs pending
hermes_and_protected_hosts: untouched
~~~

### OpenClaw installed-repair fresh status bundle

~~~yaml
host: openclaw
checkout_sha: ab2862623f12fba9cf74634e637aed97a63b90bd
installed_checkout_sha: c0426ab967c102f25fb530bf6355f7f6ff11b45b
host_version: OpenClaw 2026.7.1-2 (0790d9f)
fresh_session_id: b815780c-23fb-4fdb-8731-aed6d162b769
agency_trace_id: 7f4aa31c-9d93-4199-bac0-b5818cea91de
store_run_id: 526c86bd-ddca-4878-93a4-8bd09ca029a6
store_session_key_sha256: d20c5bfbc17fd25b46d36898bccf90b16e7e54c7dc256dc9cce351542590e299
routing_decision_ids: [d8130eb2-d1fa-478e-84e3-bcff1dc6e0ed]
routing_result: abstained; deterministic control
resident_binding_id: none
specialists_loaded_ids: []
skill_name_and_store_row_id: none
model_receipts: []
native_parent_provider: litellm
native_parent_requested_alias: task-general
agency_requested_alias_used_this_turn: false
actual_model_and_receipt_source: unavailable; deterministic control has no Agency model receipt
finalization_id: 6ce7c157-98fd-4ab7-aabc-d4722e02a43b
finalization_status: accept; completed; no missing fields
response_chars: 476
response_sha256: a4c784dc9bf1025893bd04464da5c01ac7598b05a3a6fce480a74cd90577262c
native_transcript_sha256: a2ec1af7e3bbe02d7c3a21d92ea38787a21116ae8cea4ff1d69aa9a3eeff38f4
header_exact: agency-steward / none / none / requested execution alias task-general / deterministic
telegram_delivery: outbound followed inbound; owner pasted exact response
first_response_artifact: /tmp/ar278-openclaw-eighth-live/status-evidence-redacted.json
first_response_artifact_sha256: 0524fac40ff365aa48dca844f54489f3199468cfdb2e42714bd8a84e3408adf2
native_redacted_trajectory: /tmp/ar278-openclaw-eighth-status-b815780c
known_limit: control path only; changed skill and substantive task-agency-router proofs pending
hermes_and_protected_hosts: untouched
~~~

### OpenClaw installed-repair tmux skill bundle

~~~yaml
host: openclaw
checkout_sha: 891510f0
installed_checkout_sha: c0426ab967c102f25fb530bf6355f7f6ff11b45b
host_version: OpenClaw 2026.7.1-2 (0790d9f)
native_session_id: 31983848-8d75-4e8f-ae11-8b8087d8c429
native_session_note: OpenClaw rolled after the operator delay; Store channel-session SHA remained unchanged
agency_trace_id: adff32ff-bbd0-4afd-befd-e5c647ac76fc
store_run_id: bcbbebd5-b35e-445f-a066-0298c0f27d44
store_session_key_sha256: d20c5bfbc17fd25b46d36898bccf90b16e7e54c7dc256dc9cce351542590e299
routing_decision_ids: [dce3ca84-d8be-4f29-8636-2beb2abc32e0]
routing_result: accepted code-reviewer; confidence 1.0; zero fallback
resident_binding_id: none
specialists_loaded_ids: [a3c9d9ef-fdfe-4d02-b4f7-d0e7469f8ff2]
skill_name_and_store_row_id: tmux / 937189d5-d27c-4fea-8829-91e7995f2252
agency_inference_profile: linux-task-agency-router
provider_type: litellm
requested_alias: task-agency-router
model_group: task-agency-router
model_receipt_ids: [10dcc23f-7cb6-4bb1-a1e1-6eaffad3cb5d, e9fd64c1-7bf3-410c-b06b-b718ad159496, 492a3fd7-e841-4dec-ae0b-a1be846d6f80]
model_receipt_source: wrapper
actual_model_and_receipt_source: unavailable; wrapper receipts report requested Agency alias only
fallback_count: 0
native_parent_provider: litellm
native_parent_requested_alias: task-general
finalization_id: 3d5bdb26-881d-4759-9ded-2ae2ac167a44
finalization_status: accept; completed; no missing fields
response_sha256: 740382841b3f75bdc4e33324844ee98f95c333ea3c6b1bbb6854aaab9ba9a3de
native_transcript_sha256: da55b13b94b72d277b42150607980c7d4e7009cff76bff12b86f7d641e7b5f69
header_exact: agency-steward, code-reviewer / none / tmux / workforce inference task-agency-router to linux-task-agency-router/task-agency-router wrapper / inference
telegram_delivery: outbound followed inbound
evidence_artifact: /tmp/ar278-openclaw-eighth-live/tmux-skill-evidence-redacted.json
evidence_artifact_sha256: 005630dc6fb457d7635a4e262a912b4e23581d011f125fc898f7df55c20d6776
known_limit: exact substantive restart-safety proof and final integrity bundle pending
hermes_and_protected_hosts: untouched
~~~

### OpenClaw final scoped acceptance bundle

~~~yaml
host: openclaw
checkout_sha: 8357df3cc572c629975dd7f3f9e171408928c799
installed_checkout_sha: c0426ab967c102f25fb530bf6355f7f6ff11b45b
clean_tree_at_live_evidence_checkpoint: true
host_version: OpenClaw 2026.7.1-2 (0790d9f)
profile_identity: openclaw -> linux-task-agency-router
native_litellm_config_source_redacted: ~/.openclaw/openclaw.json; native provider and credential indirection retained; values excluded
native_primary: litellm/task-general
native_fallbacks: six original fallbacks unchanged
litellm_base_url_source: effective Agency config profile linux-task-agency-router
litellm_base_url: http://127.0.0.1:4000/v1
credential_env_name: LITELLM_API_KEY
credential_present_boolean: true
agency_inference_profile: linux-task-agency-router
agency_provider_type: litellm
requested_alias: task-agency-router
model_group: task-agency-router
actual_model_and_receipt_source: unavailable; wrapper receipts report the requested alias only; no answering-model claim
runtime_digest: 70239e65528b4828a3a992a0a857b0684976ec50d36c80c8d89bd0e4c0740d9d
store_schema: 47
install_result: 251c4349-f7e3-4640-980d-055b857c0abe; complete; Agency plugin only; installer did not restart gateway
bundle_digest: ba344b92ad80265a6807a6fda278c1c803af20d2b9767416d41a98901b2bae84
launcher_manifest_sha256: 3090708c390ecb5c6619137e328bae076f7372cc114d4b55b230e27555472250
fresh_session_id: b815780c-23fb-4fdb-8731-aed6d162b769
fresh_status_trace_id: 7f4aa31c-9d93-4199-bac0-b5818cea91de
fresh_status_run_id: 526c86bd-ddca-4878-93a4-8bd09ca029a6
first_response_artifact: /tmp/ar278-openclaw-eighth-live/status-evidence-redacted.json
first_response_artifact_sha256: 0524fac40ff365aa48dca844f54489f3199468cfdb2e42714bd8a84e3408adf2
first_response_sha256: a4c784dc9bf1025893bd04464da5c01ac7598b05a3a6fce480a74cd90577262c
first_response_transcript_sha256: a2ec1af7e3bbe02d7c3a21d92ea38787a21116ae8cea4ff1d69aa9a3eeff38f4
first_response_header_exact: agency-steward / none / none / requested execution alias task-general / deterministic
skill_native_session_id: 31983848-8d75-4e8f-ae11-8b8087d8c429
skill_trace_id: adff32ff-bbd0-4afd-befd-e5c647ac76fc
skill_run_id: bcbbebd5-b35e-445f-a066-0298c0f27d44
skill_name_and_store_row_id: tmux / 937189d5-d27c-4fea-8829-91e7995f2252
skill_response_artifact: /tmp/ar278-openclaw-eighth-live/tmux-skill-evidence-redacted.json
skill_response_artifact_sha256: 005630dc6fb457d7635a4e262a912b4e23581d011f125fc898f7df55c20d6776
skill_header_exact: agency-steward, code-reviewer / none / tmux / workforce inference task-agency-router to linux-task-agency-router/task-agency-router wrapper / inference
substantive_native_session_id: 84deda15-df94-4aa8-8ed4-853ecd56ff99
agency_trace_id: 5ba0b638-9db8-4144-8be0-2d9b17f6b51d
substantive_run_id: ad2b1238-dd8f-49c9-9b30-2107baf7b499
substantive_response_artifact: /tmp/ar278-openclaw-eighth-live/restart-safety-evidence-redacted.json
substantive_response_artifact_sha256: acf1461b2cc0f6e525378fecb8f3c281d2f9b0f2c8a82a139888cd9da4ef3c1b
substantive_response_sha256: 1bf6f61e571b74d1a6e5b42dddcc92f2341cba41b48ba7840800a8eda3522fb3
substantive_transcript_sha256: 176811b46e81eb7902c916bc837221ab4e0ebbac220e6fec328035833e46c379
header_exact: |-
  Agency/Agencies loaded: agency-steward, ai-evaluation-engineer, ai-data-remediation-engineer
  Agency/Agencies delegated: none
  Skills loaded: openclaw-operations
  Actual Model selected: workforce inference: [router] task-agency-router -> linux-task-agency-router/task-agency-router (wrapper)
  Recruited via: inference
resident_binding_id: none
routing_decision_ids:
  - d8130eb2-d1fa-478e-84e3-bcff1dc6e0ed
  - dce3ca84-d8be-4f29-8636-2beb2abc32e0
  - b5f22f42-4ddf-4a8b-85ed-8fb56c13e7b1
specialists_loaded_ids:
  - a3c9d9ef-fdfe-4d02-b4f7-d0e7469f8ff2
  - 2762c670-30bb-4b9b-b3ad-4de5e87ed0f4
  - 8367ed56-a2f2-43db-972f-423219b751e5
substantive_skill_name_and_store_row_id: openclaw-operations / a0b9a4ea-2a0c-441d-ae39-a946ff149c6f
provider_receipt_ids:
  - 10dcc23f-7cb6-4bb1-a1e1-6eaffad3cb5d
  - e9fd64c1-7bf3-410c-b06b-b718ad159496
  - 492a3fd7-e841-4dec-ae0b-a1be846d6f80
  - 2f56154a-1fbc-4c6d-a4dd-b3a7c4ba66df
  - bd407d85-5877-4400-8eee-4653728bf4a4
  - 5a85f98a-dbb7-40bf-9b90-06bd86e66d51
provider_attempt_status: applied; wrapper success; OpenClaw harness selected automatically
fallback_count: 0
delegation_rows: 0
native_child_rows: 0
timeout_or_failure_receipt: none for accepted proofs; earlier failures retained separately and not rewritten
contractors_before_after: 15/15
store_integrity_before_after: ok / ok
pre_install_store_backup_sha256: 3cdf39fc6518bb2b70c1ed009dc5877648dce5c62a3676edbf6ae73cc785ba77
final_store_backup_sha256: affd8f8ea4a5f8636e7a657b6314497267ff7d105fd1571e12dfa10bea836cdf
agency_config_sha256: 43367ec9aa05a66fc2a60bb254f270836fb3616753769115fabb253a04d5d9f8
openclaw_config_before_after_sha256: 17784e2e1dc7a55530cb3853bb2b6eed2339c7d2a7928fa987026b4dfbec0b65 / 3060c3ee95c193780eae92199516abf53525664b8d111c893cc349d4ca71d24b
openclaw_config_semantic_delta: meta.lastTouchedAt only
gateway_channels: RPC green; Telegram and Slack configured/enabled/connected/running/probe-green
known_limit: actual answering model unavailable; no Rule 4 native-child proof; no AR-119 matrix-cell movement
hermes_and_protected_hosts: untouched
~~~

### Hermes install-readiness bundle

~~~yaml
host: hermes
checkout_sha: f027dd44a1db17627d7cc51c3bd00150f25e7700
clean_tree_at_install: true
host_version: Hermes Agent v0.20.4 (2026.8.18)
effective_home: /home/holeshot/.hermes-nexus
native_litellm_config_source_redacted: /home/holeshot/.hermes-nexus/config.yaml and .env; values excluded
native_primary: task-general
native_provider: litellm
native_fallback_count: 5
native_plugins_before: 9
credential_env_names: [LITELLM_API_KEY, LITELLM_BASE_URL]
credential_present_boolean: true
agency_inference_profile: linux-task-agency-router
requested_alias: task-agency-router
model_group: task-agency-router
store_schema: 47
contractors_before_after_install: 15/15
pre_install_store_integrity: ok
pre_install_store_backup_sha256: affd8f8ea4a5f8636e7a657b6314497267ff7d105fd1571e12dfa10bea836cdf
agency_config_sha256: 43367ec9aa05a66fc2a60bb254f270836fb3616753769115fabb253a04d5d9f8
hermes_config_before_sha256: a984d9343cbd56b7ac3bb70586ce4db90a739d6a063a530b9183c5baca1e170d
hermes_env_before_after_sha256: 792fd43a5312d1c1d69f6afbeef3bbdd1a8198ee03ac06b4b3b6dfa20ec2f324 / unchanged
first_install_result: failed before plugin staging; private plugin parent not trusted
first_install_artifact: /tmp/ar278-hermes-preinstall.MZtRGk/install-result.json
first_install_artifact_sha256: 72c3a7acd361d03418fbd4a2f262b4cad90ce420c442821793234f6596bed3f0
failed_attempt_launcher_sha256: 7c033c97e7f4ce2108efcccfadc4f1c9e4511dc98afa11085adfd898f27585c3
failed_attempt_config_changed: false
changed_prerequisite: plugin parent mode 0775 -> 0700; process umask 0077
install_result: 06bd5aa2-c8c3-4321-90b2-e413a142c4a7; complete; Agency plugin only; installer did not restart Hermes
install_artifact: /tmp/ar278-hermes-preinstall.MZtRGk/install-result-private-parent.json
install_artifact_sha256: 93857d15f8009f38059d0b5137c8b58c8ab7da8f662b69e5e4fca4c162fab517
bundle_digest: 351a7108bfc4a8ffdd933261f9fe5bfe451886f88272b7bbaa8d4a2fa5377127
runtime_digest: 70239e65528b4828a3a992a0a857b0684976ec50d36c80c8d89bd0e4c0740d9d
launcher_manifest_sha256: 7c033c97e7f4ce2108efcccfadc4f1c9e4511dc98afa11085adfd898f27585c3
hermes_config_after_sha256: 95b87b7fc0427ad4e3da4f5f468054cf9f7ddba679d1bb606b782a13e1a0172d
hermes_config_semantic_delta: enable agency-preflight with allow_tool_override false only
native_model_provider_fallbacks_changed: false
prior_native_plugins_changed: false
plugin_contract: enabled; standalone discovery/import/registration pass; eight hooks; zero tools
gateway_restart: exact hermes-gateway-nexus.service active/running; successful service receipt
openclaw_status: active
fresh_session_id: pending
agency_trace_id: pending
actual_model_and_receipt_source: pending live turn; never infer from alias
known_limit: fresh status, Store-backed skill, substantive LiteLLM routing, and Telegram delivery pending
protected_hosts: Codex OAuth/config/canary, Claude, and ZCode untouched
~~~

## 2026-08-24 - OpenClaw operational child delivery with missed Agency end receipt

The `headerContextHash` correction/ledger `10ba4c84` / `8a2bf9b7` was
installed through Agency only while OpenClaw was natively stopped. Evidence is
owner-private under
`/home/holeshot/.agency-runtime/evidence/ar281-openclaw-10ba4c84-hSltm1Sn`.
No native host model or fallback configuration changed, Hermes remained active
and untouched, and protected hosts were not inspected or modified.

The fresh changed draw delivered successfully to Telegram. The exact response
header was:

~~~text
Agency/Agencies loaded: agency-steward, code-reviewer
Agency/Agencies delegated: none - executed worker has no validated Agency specialist
Skills loaded: none
Actual Model selected: workforce inference: [router] task-agency-router -> linux-task-agency-router/task-agency-router (wrapper)
Recruited via: inference
~~~

The body was the child's one-sentence finding that the generated plugin forwards
bounded `headerContextHash` into the Python bridge. OpenClaw's native task ledger
records the one child `succeeded` and its return `delivered`, and the Telegram
outbound receipt exists. Parent finalization completed, but Agency's delegation
and worker rows remained open. An isolated copy of the Store accepts the exact
terminal transition and closes both rows, ruling out Store identity mismatch.

The missed callback is an Agency plugin lifecycle defect. Observation-only
child ends were retained locally and swallowed instead of trying durable
launch-bound reconciliation. Failed trace-bound terminal persistence relied on
a duplicate host hook, including early-end and sparse reset/delete cases, but
OpenClaw provides only a one-shot callback. The new state-bound fallback was
covered by expected-red tests before completion, preserves exact accepted
requester/worker/native-run identity, and does not write a Rule-4 delivery row.
Focused 146/1, fast spine 849/3, docs 783/worklog 1,158, full Ruff 682,
dashboard 134, routing eval, and 160/160 conformance mutations pass under the
required private `0077` environment; source is unchanged. Independent re-review
found no Critical, High, or Medium issue.
The candidate is not installed and therefore has no live-fix claim.

~~~yaml
host: openclaw
checkout_sha: 10ba4c84dda32d74bf5fb2ac4358fc54768dd1e8
clean_tree_before_install: true
host_version: OpenClaw 2026.7.1-2
profile_identity: linux-task-agency-router
native_litellm_config_source_redacted: existing OpenClaw config; native primary litellm/task-general plus six unchanged fallbacks
litellm_base_url_source: effective Agency profile; loopback LiteLLM endpoint
credential_env_name: LITELLM_API_KEY
credential_present_boolean: true; value never read or retained
agency_inference_profile: linux-task-agency-router
requested_alias: task-agency-router
model_group: task-agency-router
actual_model_and_receipt_source: unavailable; provider telemetry supplied none
runtime_digest: 77e00aa229b9948a6e918bbcb546e9feaa25ac5cbdfa98b469e0ab40852cebf9
store_schema: 47
install_result: complete; Agency only; no dashboard; installer did not restart gateway
launcher_manifest_sha256: 3fc5e135131879fad712b4c067aae1dce018a96e41f8d14aa2929f1c484ec1b9
fresh_session_id: 7c3bacfd-6f05-4b0d-982c-5c3575bd8110
agency_trace_id: a5f6f53b-4d8f-446b-af98-049e5031599a
first_response_artifact: parent transcript sha256 97142fdba7619c662e10ffc37dab156ae6bbb982dec5642ec4d5b8e1eeb43aec
header_exact: agency-steward + code-reviewer / no validated Agency specialist delegation / no skills / workforce inference task-agency-router wrapper / inference
resident_binding_id: rmb-fef54dccff0a71da62d23ec36ae83a1b; validated preflight recipe projection
routing_decision_ids: 99f1388a-17eb-46e9-ab36-d9426fd05f24; native-child-4ef0e65f64b0725eac80bd3d644a7d0a
skill_name_and_store_row_id: none requested
provider_attempt_status: canonical three applied structured attempts; child one applied attempt
fallback_count: 0 cross-provider
timeout_or_failure_receipt: no timeout; OpenClaw succeeded/delivered but Agency delegation and worker remained open
before_after_contractor_count: 15 / 15
before_store_integrity_sha256: ok; 6aeaaad464d082dd1483891c0d3d4db64bc5334cace42f36252fa6876b4ebcc1
after_store_integrity_sha256: ok; 0a65fa88b08bfa297f2ed772dd3c36f08e82bcb1c17d49e7fab236da7f51d8bf
native_config_semantic_sha256_before_after: e42bf2181ef9c8d0639b281bfd9cbd27978c9b83ed607b8e660fc42eadf3add1 / same
hermes_state: active and untouched; no install or config mutation
candidate_state: locally green; not installed
local_gates: focused 146/1; fast spine 849/3; docs 783/worklog 1158; Ruff 682; dashboard 134; routing passed; conformance 160/160 killed
retained_eval_failures: isolated launcher lacked pytest; first private evaluator inherited unsafe umask 0002
known_limit: operational delivery passed but Agency child terminalization and ADR-0156 Rule 4 are unproven
matrix_cell_moved: false
protected_hosts: Codex OAuth/config/canary, Claude, and ZCode untouched
~~~

## Second changed OpenClaw native-child draw: completion hash omitted

After the installed ready-receipt correction, the operator submitted a
genuinely changed, bounded, one-child request. Parent run
`db9fb4f4-5eb1-40b4-a5e2-3ad2015835e1`, trace
`1dc07325-047e-471e-b7f6-5830b651463f`, and transcript
`ba29f451-b36e-4e71-bc8b-2c7fb241dfbe` spawned exactly one native child.
Session `82abcc6d-3131-49f9-88f4-f911296e3750`, native run
`cf704bcb-d0b0-4d89-9c85-3770f011adc6`, delegation
`0f2ea05c-4736-4e34-9f29-eed90d48b85c`, worker row
`native-child:0b0cf13329292b13ea2d4386a0c591e2ed60bc16b3dc4b218f7d3ab673289da0`,
and route `native-child-c8e004f5b93a1decf22bb9d9840ef0a9` correlate.

The child completed at `20:18:26Z`. Its first completion message failed
`FINALIZATION_UNAVAILABLE`; 12 further attempts were uncorrelated. No Telegram
send was queued and no finalization or delivery row exists. The Store parent,
delegation, and worker remain active/delegated/open, so the failed evidence is
not rewritten as a successful timeout, finalization, or delivery.

The child route records one applied attempt on automatically selected OpenClaw
profile `linux-task-agency-router`, provider type `litellm`, and exact requested
alias/model-group `task-agency-router`. Cross-provider fallback is zero;
provider telemetry supplied no actual answering model. Native OpenClaw
execution separately remained on `task-general`.

The exact bridge defect is that authorization supplied `headerContextHash`,
but `serializeBridgePayload` omitted the field before the Python finalizer that
requires it. A focused regression first reproduced that omission. A one-line
bounded-field forwarding change now passes the four-file focused suite at 145
passed and 1 existing skip under `umask 077`; targeted Ruff check, Ruff format,
and `git diff --check` pass, and independent Critical/High review is GREEN.
The candidate is not installed and has no live proof. The gateway stopped
cleanly after evidence capture; Hermes remained active and untouched.

~~~yaml
host: openclaw
attempt: second changed native-child draw
parent_run_id: db9fb4f4-5eb1-40b4-a5e2-3ad2015835e1
parent_trace_id: 1dc07325-047e-471e-b7f6-5830b651463f
parent_transcript_id: ba29f451-b36e-4e71-bc8b-2c7fb241dfbe
child_session_id: 82abcc6d-3131-49f9-88f4-f911296e3750
child_native_run_id: cf704bcb-d0b0-4d89-9c85-3770f011adc6
delegation_id: 0f2ea05c-4736-4e34-9f29-eed90d48b85c
worker_row_id: native-child:0b0cf13329292b13ea2d4386a0c591e2ed60bc16b3dc4b218f7d3ab673289da0
native_child_routing_decision_id: native-child-c8e004f5b93a1decf22bb9d9840ef0a9
child_completed_at: 20:18:26Z
first_completion_status: FINALIZATION_UNAVAILABLE
subsequent_completion_attempts: 12; uncorrelated
telegram_send: none
finalization_or_delivery_row: none
store_lifecycle: active / delegated / open
agency_inference_profile: linux-task-agency-router
provider_type: litellm
requested_alias_model_group: task-agency-router
cross_provider_fallback_count: 0
actual_model_and_receipt_source: unavailable; provider telemetry supplied none
native_openclaw_execution_alias: task-general
root_cause: serializeBridgePayload omitted authorized headerContextHash
candidate_change: forward one bounded headerContextHash field
focused_regression_order: failed before fix; passed after fix
focused_tests: 145 passed; 1 existing skip; umask 077
targeted_gates: Ruff check passed; Ruff format passed; git diff --check passed
independent_review: GREEN; no Critical or High finding
candidate_installed: false
gateway_state_after_capture: stopped cleanly
hermes_state: active; untouched
completion_delivery_proven: false
rule4_proven: false
matrix_cell_moved: false
protected_hosts: Codex OAuth/config/canary, Claude, and ZCode untouched
~~~

### Clean correction install checkpoint

Clean implementation/ledger commits
`c7520586143d9a497dce37f32cad994de66ffb00` and
`2bf42059cb1e46fa2e25f2d7847c85b9cf1b9b84` were installed from the exact
checkout recorded by the launcher. Before mutation, the live Store was backed
up with SQLite's online backup mechanism; source and backup integrity were
`ok`, schema was 47, and backup SHA-256 was
`736434a7dffd310592661edf07af41ae2a62f347c1174e527ff34d3cdcdecd81`.
OpenClaw 2026.7.1-2 was stopped natively while Hermes remained active. The
Agency-only, no-dashboard install completed, created its native backup under
`~/.agency-runtime/backups/openclaw/20260824T195320.228690Z`, and did not
restart the gateway.

The installed bundle is
`ae5b0a3ed2b7d6f7a2a6e516a2a6f1e20bc2144a8fb560a61f0f1705bbece9bb`;
runtime digest is
`46ed926c5fac5066838ff6eea56d1cc866a3e9b2f99f474bfcd45d2ccfc99788`;
install ID is `ed2572b6-4d6b-4699-8e77-e82c49e4e48d`; and launcher SHA-256 is
`46c4fd6e67ceb3bfb36027c3e6f5183842f6cbaa01b1f25c31169e4554ace15d`.
The launcher source root is the exact correction checkout. Native restart then
restored an active service, RPC health, and a loaded, enabled, activated Agency
plugin with all 12 hooks.

Agency config SHA remains `43367ec9...`; authentication remains only the
`api_key_env` indirection, and `LITELLM_API_KEY` is present in the live process
without reading its value. OpenClaw semantic config SHA remains `5f806455...`;
native `litellm/task-general` and the exact six prior fallbacks are unchanged.
Contractors remain 15/15. Post-install Store integrity is `ok` at schema 47.
Hermes remained active with config `95b87b7f...`, environment `792fd43a...`, and
launcher `e65a0784...` unchanged; no Hermes install occurred. The clean install
checkout remained clean. `config validate` retains its expected degraded result
from cold inventory, protected hosts, and the legacy-provider warning; it is not
a new failure. No fresh Telegram draw has started. The next operator action is
`/new`.

~~~yaml
host: openclaw
implementation_commit: c7520586143d9a497dce37f32cad994de66ffb00
ledger_commit: 2bf42059cb1e46fa2e25f2d7847c85b9cf1b9b84
worktree_clean_at_install: true
evidence_dir: /home/holeshot/.agency-runtime/evidence/ar281-openclaw-c7520586-4ceF3vbq
preinstall_store_backup_sha256: 736434a7dffd310592661edf07af41ae2a62f347c1174e527ff34d3cdcdecd81
preinstall_store_source_integrity: ok
preinstall_store_backup_integrity: ok
preinstall_store_schema: 47
agency_config_sha256: 43367ec9...
agency_credential_storage: api_key_env indirection only
host_version: OpenClaw 2026.7.1-2
preinstall_host_state: OpenClaw stopped natively; Hermes active
install_result: complete; Agency only; no dashboard; installer did not restart gateway
native_backup_path: ~/.agency-runtime/backups/openclaw/20260824T195320.228690Z
bundle_digest: ae5b0a3ed2b7d6f7a2a6e516a2a6f1e20bc2144a8fb560a61f0f1705bbece9bb
runtime_digest: 46ed926c5fac5066838ff6eea56d1cc866a3e9b2f99f474bfcd45d2ccfc99788
install_id: ed2572b6-4d6b-4699-8e77-e82c49e4e48d
launcher_manifest_sha256: 46c4fd6e67ceb3bfb36027c3e6f5183842f6cbaa01b1f25c31169e4554ace15d
launcher_source_root: /tmp/agency-runtime-ar278.WpEBq4
gateway_restart: native; service active; RPC true
plugin_runtime: loaded, enabled, activated; 12 hooks
credential_env_name: LITELLM_API_KEY
credential_present_boolean: true in live process; value not read
openclaw_semantic_config_sha256: 5f806455...; unchanged
native_primary: litellm/task-general; unchanged
native_fallback_count: 6; exact prior list unchanged
contractors_before_after: 15 / 15
postinstall_store_integrity: ok
postinstall_store_schema: 47
hermes_state: active; no install
hermes_config_sha256: 95b87b7f...; unchanged
hermes_environment_sha256: 792fd43a...; unchanged
hermes_launcher_sha256: e65a0784...; unchanged
config_validate: expected degraded; cold inventory, protected hosts, legacy provider warning
fresh_telegram_draw: not started
next_operator_action: /new
operational_acceptance_green: false
rule4_proven: false
~~~

### OpenClaw native-error repair install bundle

~~~yaml
host: openclaw
checkout_sha: 484fe2ded93f235c396ecf82afdc14e8329b9d52
clean_tree_before_install: true
host_version: OpenClaw 2026.7.1-2
profile_identity: OpenClaw native task-general; Agency linux-task-agency-router
agency_inference_profile: linux-task-agency-router
requested_alias: task-agency-router
model_group: task-agency-router
provider_type: litellm
credential_env_name: LITELLM_API_KEY
credential_present_boolean: true in live OpenClaw process; value excluded
agency_config_sha256: 43367ec9aa05a66fc2a60bb254f270836fb3616753769115fabb253a04d5d9f8
store_backup_before_path: /tmp/ar119-openclaw-native-error-preinstall.iFUzG5/agency-store.before.db
store_backup_before_sha256: 07dbad1e3c310caa83da4f3504a3f5426bc5f7578373d411dd3fd5ecfe6dce2d
store_backup_after_install_sha256: 07dbad1e3c310caa83da4f3504a3f5426bc5f7578373d411dd3fd5ecfe6dce2d
store_integrity_before_after: ok / ok
store_schema: 47
contractors_before_after: 15 / 15
install_id: 6ede7fad-27bc-4b14-bb8c-595a01db2ec3
install_result: complete; Agency only; installer left gateway stopped
bundle_digest: 6f7e47bdb8a2396fc59d73344bcc60c88a90d78fc69a5e12d60fa94f2795e20a
runtime_digest: a3b8894f356e2af722f01e0d8bcba2882921df9a9729cd22d02e25c8feb3c459
launcher_manifest_sha256: 0fd98d4d0be402f85c0a474094ba51d7c5f351292aff1efd5a0d59ab4272d4cf
openclaw_config_before_sha256: ffce9d780a31c8ce2ff103398a40ddc2f2a8340b99f4fa4fdbe48bb61f0cb3ee
openclaw_config_after_sha256: b54228aeaede1ae13722abba21879bfd7f256d79dacee368d95323d7785b9810
openclaw_config_changed_leaf_count: 1
openclaw_config_changed_path: meta.lastTouchedAt
native_primary: litellm/task-general
native_fallback_count: 6; exact prior list unchanged
plugin_inventory_before_after: 75 / 75
agency_plugin: enabled, loaded, version 0.1.0
registered_hooks: 12; required set complete; agent_end present
plugin_diagnostics: none
gateway_restart: native start; RPC green; zero restarts
telegram: configured; running; no current error
slack: configured; running; no current error
hermes_break_glass: active and unchanged
live_error_delivery_proven: false
fresh_status_proven: false
substantive_openclaw_acceptance_proven: false
delegation_proven: false
matrix_cell_moved: false
protected_hosts: Codex OAuth/config/canary, Claude, and ZCode untouched
~~~

### OpenClaw post-install fresh reset bundle

~~~yaml
host: openclaw
checkout_sha: d348f7decf9eba12bab25399fc704b101bc14440
command: /new
acknowledgement_exact: ✅ New session started.
fresh_session_id: 447738d1-1871-411d-87b1-073387fb5560
fresh_session_total_tokens: 0
reply_payload_observed_before_authorization: true
before_reset_authorized: true
reply_payload_authorized: true
message_authorization_consumed: true
telegram_send_ok: true
first_response_artifact: /tmp/ar119-openclaw-native-error-preinstall.iFUzG5/openclaw-new-ack-redacted.json
first_response_artifact_sha256: 8fea7044d590067aa32f2e52b54f16cc5bf26b154c184e68f51aaf19e0b4bcce
agency_runs_created: 0
fresh_status_sent: false
telegram_identifiers: excluded
credential_values: excluded
delegation_proven: false
matrix_cell_moved: false
~~~

### OpenClaw fresh status stale-skill-header failure bundle

~~~yaml
host: openclaw
checkout_sha: 3d5b024f0d85355e7ce505ca1a1d9baf27d30907
fresh_session_id: 447738d1-1871-411d-87b1-073387fb5560
input_exact: agency status
run_id: a4b27543-7644-4cad-bd0d-2ef9ec9f7581
agency_trace_id: 7e7a6318-5b6a-4afc-b8a1-0ec57103bd1f
routing_decision_ids: [f7bc2f7e-555c-47d7-8f74-5a9c37b7f41e]
routing_status: abstained; deterministic control
specialists_loaded_ids: []
skill_name_and_store_row_id: openclaw-operations / 3b9037a9-6ea8-48e1-a9cf-39aeb520b744
updated_header_skills_loaded: openclaw-operations
authored_header_skills_loaded: none
header_exact: invalid; stale initial snapshot used after Store skill mutation
terminal_finalization_id: 25cf1630-de51-4f21-9050-9da41e01c0ae
terminal_status: response_invalid
terminal_missing: [skills_loaded]
resident_binding_id: none; authored prose claim is not Store evidence
provider_attempt_status: deterministic control; zero Agency model receipts
fallback_count: 0
worker_rows: 0
native_child_rows: 0
telegram_outbound_queued: false
native_transcript_sha256: 78d096d5d3def3d2ed779a72929078eb8932cef740f67d111bf8bdcc71c902b7
trace_artifact_sha256: 6c9bc3bc52933cd629285976007c95b909c6181ca13db59958dd933f9005d130
failure_artifact: /tmp/ar119-openclaw-native-error-preinstall.iFUzG5/openclaw-fresh-status-stale-skill-header-redacted.json
failure_artifact_sha256: 9a9e2a352dc203a152392961714049d60c42b9eef2d1c721160779cacf98bad7
retry_rule: preserve; do not retry exact input on unchanged code/state
delegation_proven: false
matrix_cell_moved: false
~~~

### Fresh dual-host status and regression-repair bundle

~~~yaml
openclaw:
  native_transcript_sha256: 939c2d147945ba8ba0658e02f2399068ca30e15f6c148c238cd3bbfd25593380
  exact_prompt_sha256: 8511ac8d8a7e05dc3769006189f14416e415315647551074844528fcdb17cb8c
  response_artifact: /tmp/ar278-hermes-preinstall.MZtRGk/openclaw-fresh-status-response.txt
  response_sha256: 46c65863d3ca933acadb3dab120cc023de378b03d1d3007ccf9ef9f8e7a68d3b
  trace_id: 889fd156-fbf9-4842-a43b-9c730abd919e
  run_id: 1a6634ce-3987-407f-b10f-1097cf2e0a6b
  routing_decision_ids: [6d9689d8-be86-4223-a441-cd5be621b85a]
  skill_name_and_store_row_id: openclaw-operations / 0a06b265-7895-4854-9362-338dd1fd33af
  finalization_id: 01376e98-984d-4fb3-8430-c7e7530ed69b
  finalization_status: response_invalid; missing actual_model_selected
  header_exact: agency-steward / none / openclaw-operations / none observed / deterministic
  telegram_delivery: unproven; final-only gate rejected the response
  root_cause: tool-result correlation omitted the preflight model used by the refreshed header
hermes:
  native_session_id: ...65697a38
  exact_prompt_sha256: 8511ac8d8a7e05dc3769006189f14416e415315647551074844528fcdb17cb8c
  native_transcript_artifact: /tmp/ar278-hermes-preinstall.MZtRGk/hermes-fresh-status-native-transcript.json
  native_transcript_sha256: 8bce3dbed99950e98c6fb79726d70ffb8c50edd5f3d43ef75d68f2878b928522
  response_sha256: da7f3f0c63d48cc05e4b6f8558753126e7be48e3ef33fa0eaa83b1ba70ca25ad
  trace_id: ...65697a38:...65697a38:301cda8d
  run_id: 1015aba7-172f-4a53-b88e-584846ea7ce5
  routing_decision_ids: [fe3a549f-51e2-4b70-969e-a4c6c35d55eb]
  skill_name_and_store_row_id: hermes-agent / e3805f74-b628-4346-b5d1-cb3f072a32d5
  finalization_id: 3cc70f32-e5e7-4069-8faf-ccc327bc3677
  finalization_status: accept; completed; incorrectly attributed to mcp
  header_exact: agency-steward / none / hermes-agent / observed native task-general host receipt / deterministic
  agency_workforce_receipts: 0
  native_parent_receipts: 12; task-general; zero fallback; not Agency workforce evidence
  delegation_rows: 0
  native_child_rows: 0
  telegram_delivery: not independently confirmed
  root_cause: generic agency.finalize hard-coded mcp instead of the Store-owned originating host
candidate:
  expected_red: both focused regressions failed before implementation
  repair: bounded OpenClaw model correlation plus Store-authoritative MCP finalization host
  focused_tests: 232 passed; 6 intentional skips; process umask 0077
  static_gates: focused ruff check and format, docs validation, git diff check pass
  installed: false
  host_native_configuration_changed: false
  delegation_proven: false
  matrix_cell_moved: false
protected_hosts: Codex OAuth/config/canary, Claude, and ZCode untouched
~~~

### OpenClaw attribution-repair install and reset-ack failure bundle

~~~yaml
host: openclaw
checkout_sha: f86bedb4da9734120c2a6b3fcb2fb3ce4e51c308
repair_commit: 21f2519d357b0f40892aba2d567fd97fccb23d8d
install_result: 776616e9-c086-4078-a9c3-b0875a5e6ebc; complete; Agency only; installer left gateway stopped
bundle_digest: dd5707e677057f707d896a964f2fc2bdf7855ed0f19387f9f1039dde78776dd5
runtime_digest: 0480db84301847c5a23064910deeaf089b8328cc4d6b83811cada870df43828c
launcher_manifest_sha256: 72420e546fb89b51d72e402ebf509beb0ca8fa5862ce979d90dfaadaa53c7d55
pre_install_store_backup: /tmp/ar119-openclaw-attribution.YImprt/agency-store.before.db
pre_install_store_backup_sha256: 5ca1ffbefdea30f8882445d448dee518ca0b6dc68d23b57adb5b64f5b74dcd75
store_integrity_source_backup: ok / ok
store_schema: 47
contractors_before_after_install: 15 / 15
agency_config_sha256: 43367ec9aa05a66fc2a60bb254f270836fb3616753769115fabb253a04d5d9f8
native_primary: litellm/task-general
native_fallback_count: 6; exact prior list unchanged
gateway_restart: active/running; RPC green; zero restarts
hermes_break_glass: active and unchanged
fresh_native_session_id: 241cbd97-ff10-49b8-b4bb-2458cb9c8937
operator_command: /new
native_reset_applied: true
acknowledgement_delivered: false
post_install_agency_turns: 0
native_log_event_sha256: 01b6f0cb7eec7ec610ef4f570a9edddb4e188be91b7f211d6e618c14f35c9032
failure_artifact: /tmp/ar119-openclaw-attribution.YImprt/openclaw-reset-ack-failure-redacted.json
failure_artifact_sha256: 063428388fb6f9436be5a3fbdd10bc7910fb6380312f390eef47c1d0a01a9761
root_cause: supported message_sending callback omitted optional sessionKey; exact Agency native-ack authorization required it
expected_red: sessionless acknowledgement race failed before implementation
candidate_rule: consume only one active exact unambiguous reset authorization when session context is absent
ambiguity_replay_wrong_text_expiry: fail closed
focused_tests: 245 passed; 1 intentional skip
candidate_installed: false
delegation_proven: false
matrix_cell_moved: false
protected_hosts: Codex OAuth/config/canary, Claude, ZCode, and Hermes untouched
~~~

### OpenClaw refreshed-header final live acceptance bundle

This bundle records fresh native proof after repair `d7187e80` and install
checkpoint `00d5ac27`. It supersedes only the preceding install bundle's
`pending` live-proof field; all earlier failed attempts remain evidence.

~~~yaml
host: openclaw
checkout_sha: ae2213a0266f4fc591ad77dd877210bc02c54699
installed_source_checkout_sha: 456a75b7e984c905c2331a7b938e10de67a4a2e5
repair_commit: d7187e809523503b5d8162d3334afc497fe1d3f6
install_checkpoint_commit: 00d5ac27
clean_tree: true for installed source checkout; runtime code unchanged during proof; documentation-only changes present while recording evidence
host_version: OpenClaw 2026.7.1-2 (0790d9f)
profile_identity: openclaw -> linux-task-agency-router
native_litellm_config_source_redacted: ~/.openclaw/openclaw.json; litellm/task-general primary and exact six prior fallbacks unchanged; credential values excluded
litellm_base_url_source: effective ~/.agency-runtime/agency.yaml profile linux-task-agency-router
litellm_base_url: http://127.0.0.1:4000/v1
credential_env_name: LITELLM_API_KEY
credential_present_boolean: true in live OpenClaw service; value never read or emitted
agency_inference_profile: linux-task-agency-router
agency_provider_type: litellm
requested_alias: task-agency-router
model_group: task-agency-router
actual_model_and_receipt_source: unavailable; wrapper receipts repeat requested alias, not backing model; LiteLLM callback absent although proxy can import checkout
runtime_digest: 573a6a140cb23a60b48ba4b6ce638cccba6854fa11acd701aa05c9cc47ce1ab4
store_schema: 47
install_result: fa68e6a4-75d9-4a47-8358-20b4e654b10e; complete; Agency only; installer left gateway stopped; OpenClaw not reinstalled
launcher_manifest_sha256: d65af026617abe5d836b9ba9ec3b6efe63d0815ef971c2b8f93bf7007e7771ef
fresh_session_id: 6360c186-7834-473e-9cb7-70e181581493
fresh_reset_result: /new -> ✅ New session started.; Telegram success in one chunk
first_response_artifact: native Nexus transcript at exact first agency status response
first_response_artifact_sha256: ee310dc47082f0e310797ec44d3363157f43b34269a9ce6a981110c0ffb21ced
first_response_header_exact: |-
  Agency/Agencies loaded: agency-steward
  Agency/Agencies delegated: none
  Skills loaded: none
  Actual Model selected: requested execution alias: task-general
  Recruited via: deterministic
status_run_trace_route_final: 86f838f0-aeca-4565-9474-7913b68f9d61 / ad834646-724f-4ea7-bce7-b13011c735e1 / a67e66ad-1aa2-471f-aabb-da75a3674867 / d84fc7d8-6f00-4daa-aeb9-3a99c96be8bb
skill_run_trace_route_final: 25fa081a-1ce6-4397-a234-9fc4283e6e74 / c1bbbdc7-c203-4ba2-942f-3c262bcf88f4 / 3548700e-a512-4cd1-8f3f-793b0061173d / 6907ed38-2fb8-4e87-ae53-22c2d6cb21c6
skill_name_and_store_row_id: node-connect / d02c71ae-e69b-412b-97a6-bde4e31d50f0
skill_specialist_id: 8e538079-1bb2-4178-8eae-b1929873d13b # code-reviewer
skill_read_exact: installed node-connect/SKILL.md; one native read; non-error
skill_provider_receipt_ids: [d1848be3-4a98-498e-9249-0bc0c23165c1, 891ea869-fad6-49e6-9fba-aa58b6fa6659, 68dd9d20-898e-490b-8de3-db1f0d6fa559]
skill_header_exact: agency-steward, code-reviewer / none / node-connect / workforce inference task-agency-router to linux-task-agency-router/task-agency-router wrapper / inference
skill_body_exact_summary: "Title: Node Connect; purpose limited to diagnosing OpenClaw mobile/macOS node pairing, setup-code, route, authentication, and connection failures"
skill_transcript_sha256: 92698a17450388c4a0d2de50ba5b967ff8ecdfff70bcfa0b037cd6b9d70c6c08
agency_trace_id: 50c11095-843d-4c2d-a6f4-dd140eb4a1bf
substantive_run_id: 72314429-1c90-4ef2-b087-18a7be37606e
substantive_finalization_id: 803465de-335f-42d8-9877-98a85eaab743
substantive_reads_exact: current-openclaw.json, openclaw.plugin.json, and agency-preflight/index.js; each read exactly once; no other tool or delegation call
header_exact: |-
  Agency/Agencies loaded: agency-steward, section-508-accessibility-specialist, ai-evaluation-engineer
  Agency/Agencies delegated: none
  Skills loaded: none
  Actual Model selected: workforce inference: [router] task-agency-router -> linux-task-agency-router/task-agency-router (wrapper)
  Recruited via: inference
substantive_body_exact_summary: three risks were process-local state loss, hard-coded version-specific paths, and conditional temporary-source recovery; response disclosed the truncated index.js read and absence of restart/path validation
resident_binding_id: none; request-scoped steward only; no persistent row
routing_decision_ids:
  - a67e66ad-1aa2-471f-aabb-da75a3674867 # deterministic status
  - 3548700e-a512-4cd1-8f3f-793b0061173d # skill
  - 21b8b545-05bc-4e8f-85b3-bc3a8738aa34 # substantive
specialists_loaded_ids:
  - 8e538079-1bb2-4178-8eae-b1929873d13b # code-reviewer
  - 4bb8ce63-7868-4f4d-9dfd-145132e94745 # section-508-accessibility-specialist
  - 1707c674-e2af-4392-af18-ca22590bd006 # ai-evaluation-engineer
provider_receipt_ids:
  - dd3c7a9f-90aa-4992-8504-a61d4179edcc # ordinal 1; applied
  - e0ac9e5a-2961-4eaa-bb57-980922b37af4 # ordinal 2; contract-invalid
  - 3c3e955f-f502-425a-9a60-43b630f0987f # ordinal 3; applied
  - 301f3cef-8480-449a-b800-920f93732b02 # ordinal 4; applied
provider_attempt_status: status deterministic/no receipt; skill 3/3 applied; substantive 3 applied and 1 retained contract-invalid; every inference attempt automatically selected OpenClaw, linux-task-agency-router, litellm, and task-agency-router
fallback_count: 0 cross-provider; wrapper ordinals stayed on one profile; native task-general plus six configured fallbacks unchanged
substantive_transcript_sha256: 93dcbc7659dde73cb3d9c49b79917fb7ba3a96a84e4eed93896973ca009de88c
substantive_trajectory_sha256: 0e4b57bb9f0cb199e608ff9cfdad1013421f26e069de3845127f508ba7da6821
telegram_delivery: reset, status, skill, and substantive responses each succeeded in one text chunk; no send failure in bounded journal windows
timeout_or_failure_receipt: e0ac9e5a-2961-4eaa-bb57-980922b37af4 retained contract-invalid on same profile; no final timeout or transport failure; earlier failures retained above
contractors_before_after: 15 / 15
store_integrity_before_after: ok / ok
pre_install_store_backup_sha256: abcc1396b46f7dd087f034f42b520d40fee9873b72e314d78621cdced0e470d2
post_live_store_backup_sha256: 02a76504f72946b7181619642e5b454ee49d0b9f9421632e1fe6f24a1b8ffbba
agency_config_sha256: 43367ec9aa05a66fc2a60bb254f270836fb3616753769115fabb253a04d5d9f8
openclaw_config_before_after_sha256: b54228aeaede1ae13722abba21879bfd7f256d79dacee368d95323d7785b9810 / 1c6f74936984f8c137c0d79016547a01e3bead7f6a9747ada4aa3b04c766f134
openclaw_config_semantic_delta: meta.lastTouchedAt only; native model/provider/fallback configuration unchanged
hermes_config_sha256: 95b87b7fc0427ad4e3da4f5f468054cf9f7ddba679d1bb606b782a13e1a0172d
hermes_environment_sha256: 792fd43a5312d1c1d69f6afbeef3bbdd1a8198ee03ac06b4b3b6dfa20ec2f324
hermes_launcher_sha256: 7c033c97e7f4ce2108efcccfadc4f1c9e4511dc98afa11085adfd898f27585c3
delegation_rows: 0
native_child_rows: 0
known_limit: actual answering model unavailable without callback telemetry; no delegation, native child, Rule 4 delivery, or AR-119 matrix-cell proof; Hermes and Codex OAuth/config/canary, Claude, and ZCode untouched
~~~

### OpenClaw native-error candidate install-readiness bundle

~~~yaml
host: openclaw
candidate_scope: Agency adapter/plugin/installer only; not installed
host_version: OpenClaw 2026.7.1-2
native_primary: litellm/task-general
native_fallback_count: 6; unchanged
agency_profile: linux-task-agency-router
requested_alias: task-agency-router
provider_type: litellm
native_error_contract: failed agent_end plus exact final isError payload
marker_contract: SHA-256 session/run keys; 30-second TTL; one use; maximum 128
store_terminal: response_invalid
store_missing_reason: native_host_error
raw_native_error_persisted: false
ordinary_answer_header_gate_changed: false
child_delivery_gate_changed: false
runtime_disabled_store_mutation: false
expected_red_1: agent_end registration absent; Node exit 45
expected_red_2: native_error bridge action absent
expected_red_3: response hash omitted from bridge serializer; Node exit 46
focused_tests: 251 passed; 1 intentional skip
focused_security_cases: exact correlation, replay, expiry, fallback clearing, malformed receipts, bridge failure, runtime-disable race
ruff_repository_check: passed
ruff_repository_format_check: passed
docs_metadata_check: passed
policy_worklog_docs_checks: passed with checkout import path supplied after retained initial module-import failure
git_diff_check: passed
independent_security_review: no blocking findings
installed: false
live_error_delivery_proven: false
substantive_openclaw_acceptance_proven: false
delegation_proven: false
matrix_cell_moved: false
hermes_break_glass: untouched
protected_hosts: Codex OAuth/config/canary, Claude, and ZCode untouched
~~~

### OpenClaw first post-reset substantive failure bundle

~~~yaml
host: openclaw
checkout_sha: 9c7c52c7608b25c4d3e8cd6767c13ebe1c725b9f
clean_tree_before_turn: true
host_version: OpenClaw 2026.7.1-2
profile_identity: OpenClaw native parent task-general; Agency workforce linux-task-agency-router
native_litellm_config_source_redacted: existing OpenClaw config; native primary and six fallbacks unchanged
litellm_base_url_source: effective Agency profile; loopback /v1 endpoint
credential_env_name: LITELLM_API_KEY
credential_present_boolean: true; value excluded
agency_inference_profile: linux-task-agency-router
requested_alias: task-agency-router
model_group: task-agency-router
actual_model_and_receipt_source: unavailable; wrapper alias is not actual-model telemetry
runtime_digest: 145ac94df2b3d4d2d0b356e0d6beb134a67ff3d956afb41926e6418ed53f9345
store_schema: 47
install_result: prior Agency-only install 97fd0d49-e833-458a-a4b6-fb818761f212 remains current
launcher_manifest_sha256: 9adc2a85f16f721aab0cdb6bd98ac1cc8544cc1c738b0e771dfa74c03e7b5051
fresh_session_id: 130e58cd-38c3-48de-baae-d124b4689ec2
agency_run_id: 324dcb7c-be31-4a84-abd2-cb111b4c6e8e
agency_trace_id: 755985e5-1fff-456c-ba2f-d55c30b87173
first_response_artifact: none; native parent produced no final response
header_exact: absent; all five required fields missing
resident_binding_id: none
routing_decision_ids: [436eaef9-80ef-40ad-859a-eb44843c919d]
specialists_loaded_ids: [e75c8757-214a-4e61-a2cf-6c77e4cec6cf, ade10b59-f68f-45be-9d61-55109ad84d53]
skill_name_and_store_row_id: openclaw-operations / ef7b8440-b476-4fed-ac9b-8af3b56a2e12
provider_attempt_status: 3 successful wrapper attempts; same profile and alias
fallback_count: 0 cross-provider; attempted_fallbacks 2/1/0 are ordinals
native_parent_error: context overflow during tool loop after 30 model calls and 108 distinct read-only tools
terminal_finalization: fba6d9db-cd7b-4a95-8666-9222ba12a6c7 / response_invalid
telegram_delivery: no outbound queued; channel connected and error-free
failure_capture_artifact: /tmp/ar119-openclaw-session-lifecycle-preinstall.jOnDJ8/openclaw-substantive-first-failure-redacted.json
failure_capture_sha256: d4e177d8d4e31bb9d23d9bcf6bc42e77b53d03fc36469ab3930ccf3d497c2924
failure_terminal_artifact: /tmp/ar119-openclaw-session-lifecycle-preinstall.jOnDJ8/openclaw-substantive-first-failure-terminal-redacted.json
failure_terminal_sha256: 31f864893a66f04d5f5342191425fe43f2ba5f5f9d496abff824d81615fa722f
native_transcript_sha256: 7a6addc653ec8e9ebd461a082c9398336d31ccc0fa691e39b7d68334818d780c
contractors_before_after: 15 / 15
store_integrity_before_after: ok / ok
delegation_events: 0
native_child_rows: 0
known_limit: Agency inference passed; parent completion, five-line header, and Telegram delivery did not
retry_rule: preserve this failure; do not retry the same input unchanged
protected_hosts: Codex OAuth/config/canary, Claude, ZCode, and Hermes untouched
matrix_cell_moved: false
~~~

### OpenClaw reset-lifecycle repair install-readiness bundle

~~~yaml
host: openclaw
checkout_sha: 278705da
repair_commit: c671dd35159adebb4899447a59e8aa52c6c24191
host_version: OpenClaw 2026.7.1-2
pre_install_store_backup: /tmp/ar119-openclaw-session-lifecycle-preinstall.jOnDJ8/agency-store.before.db
pre_install_store_backup_sha256: 5ca1ffbefdea30f8882445d448dee518ca0b6dc68d23b57adb5b64f5b74dcd75
store_integrity_source_backup: ok / ok
store_schema: 47
contractors_before_after_install: 15 / 15
install_id: 97fd0d49-e833-458a-a4b6-fb818761f212
install_result: complete; Agency only; installer left gateway stopped
bundle_digest: 97f95751e11c7f7b58e892d2a7eeb79479bbf2142056ba5ae104ce3929d288d8
runtime_digest: 145ac94df2b3d4d2d0b356e0d6beb134a67ff3d956afb41926e6418ed53f9345
launcher_manifest_sha256: 9adc2a85f16f721aab0cdb6bd98ac1cc8544cc1c738b0e771dfa74c03e7b5051
agency_config_sha256: 43367ec9aa05a66fc2a60bb254f270836fb3616753769115fabb253a04d5d9f8
openclaw_config_before_after_sha256: cfdacc1dff2ffb403b5bdce8af5c1934f19186b5cd0d85d446b73f4497cb7889 / ffce9d780a31c8ce2ff103398a40ddc2f2a8340b99f4fa4fdbe48bb61f0cb3ee
native_primary: litellm/task-general
native_fallback_count: 6; exact prior list unchanged
registered_hooks: 11; required set complete
gateway_restart: active/running; RPC green; zero restarts
telegram_probe: configured; running; credential probe ok
hermes_break_glass: active and unchanged
fresh_changed_new: delivered; content-free trace proves reply verify plus one-use final consume
fresh_session_id: 130e58cd-38c3-48de-baae-d124b4689ec2
agency_status_run_id: 7e907028-5ffb-4639-8b89-08f1c96001ab
agency_trace_id: 58bce9a1-0272-4076-a640-652f633e6e37
routing_decision_ids: [92befae5-f8e5-41ca-9442-d4ab9cd1534c]
routing_status: abstained; deterministic control
resident_binding_id: none
specialists_loaded_ids: []
skill_name_and_store_row_id: openclaw-operations / b2d2f4b8-dcce-443b-9678-0a1af706b75d
finalization_id_status: 9d7d7372-c0ce-4125-bd4f-7c93fae2458a / accept completed
header_exact: agency-steward / none / openclaw-operations / requested execution alias task-general / deterministic
agency_model_receipts: 0; expected for deterministic status control
native_telegram_delivery: outbound timestamp followed completion; no channel error
first_response_artifact: /tmp/ar119-openclaw-session-lifecycle-preinstall.jOnDJ8/openclaw-fresh-status-response.txt
first_response_sha256: ecac2803012cd780e3a00aee2e81d9f82bdcc47bc0aa6d78288b4902b01fc17d
native_transcript_sha256: 4c1cc3f7913c49ec497e29f41d2f39273ba4ebf72be1eb1d37d8f7a25b1e6e57
store_integrity_after_status: ok
substantive_task_agency_router_proof: pending
delegation_proven: false
matrix_cell_moved: false
protected_hosts: Codex OAuth/config/canary, Claude, ZCode, and Hermes untouched
~~~

### OpenClaw two-gate repair install and third reset failure bundle

~~~yaml
host: openclaw
checkout_sha: ff1e9594a91a8e2dd9d57e5df6db53b59b58d6f5
repair_commit: 3e71247a660ade4322af52b1446dc6fe99581db9
host_version: OpenClaw 2026.7.1-2
pre_install_store_backup: /tmp/ar119-openclaw-two-gate-preinstall.DBTHn0/agency-store.before.db
pre_install_store_backup_sha256: 5ca1ffbefdea30f8882445d448dee518ca0b6dc68d23b57adb5b64f5b74dcd75
store_integrity_source_backup: ok / ok
store_schema: 47
contractors_before_after_install: 15 / 15
install_id: 711f3174-88b1-4b9a-948d-a47f316e6744
install_result: complete; Agency only; installer left gateway stopped
bundle_digest: d1a5ef80b00c53ff6db9b01e20aaa5378f29a19b570f9f11ee9c257efe578091
runtime_digest: 70328489d4a8d8a2e508f17ceb5eaaccca09be5e79b0c1d9777d0c95c5a6ccf1
launcher_manifest_sha256: ae41c0be1390432c3d3853c2bd593ace907cc25290327575eba8c4fbb17d7987
agency_config_sha256: 43367ec9aa05a66fc2a60bb254f270836fb3616753769115fabb253a04d5d9f8
openclaw_config_before_after_sha256: 049aacc863b99343abc4bed221213ba185fee472be9e292783c779cfcbab8a76 / 562c0c4e2f09844afb0ffa7858f413d8b478f698340a3dda7c7b88e89ee9949e
native_primary: litellm/task-general
native_fallback_count: 6; exact prior list unchanged
gateway_restart: active/running; RPC green; zero restarts
telegram_probe: configured; running; credential probe ok
hermes_break_glass: active and unchanged
fresh_native_session_id: 25ed26a0-8dc8-433d-9bc1-3afdbe503ffd
operator_command: /new
native_ingress_and_reset_applied: true
acknowledgement_delivered: false; operator confirmed
outbound_receipts: 0
post_send_agency_runs: 0
native_log_event_sha256: 716f2bd1be880c670f169e8e55a2e97285923d441e91a6fb6ab6dafdb0a00a5e
command_log_event_sha256: c8b214cf5e39a112238a5076a59ca6655bdf0c511c429748dd624fdc8a36d3ce
failure_artifact: /tmp/ar119-openclaw-two-gate-preinstall.DBTHn0/openclaw-two-gate-third-failure-redacted.json
failure_artifact_sha256: ea9d4c9e8b4483339d309ab61ee918df819d465a80cfd05888d25bdb13405ed8
known_fact: static two-gate flow passes but live callback sequence still differs
diagnostic_candidate: bounded content-free hook phase and state counters only
diagnostic_exclusions: message text, identifiers, credentials, and payloads
focused_tests: 246 passed; 1 intentional skip
diagnostic_installed: false
delegation_proven: false
matrix_cell_moved: false
protected_hosts: Codex OAuth/config/canary, Claude, ZCode, and Hermes untouched
~~~

### OpenClaw content-free reset diagnostic install-readiness bundle

~~~yaml
host: openclaw
checkout_sha: b8c3b155f1585d34dae0a7a6575237e54600b5a4
diagnostic_commit: 675fb22a03b9d6e10462a4d1ada688b018ac8f4f
host_version: OpenClaw 2026.7.1-2
pre_install_store_backup: /tmp/ar119-openclaw-phase-trace-preinstall.VGtfCi/agency-store.before.db
pre_install_store_backup_sha256: 5ca1ffbefdea30f8882445d448dee518ca0b6dc68d23b57adb5b64f5b74dcd75
store_integrity_source_backup: ok / ok
store_schema: 47
contractors_before_after_install: 15 / 15
install_id: 2949e798-5500-45c9-956b-4b5a97aa802b
install_result: complete; Agency only; installer left gateway stopped
bundle_digest: 72c40ad41bb5663419b97d846ccb745f5c82965b743a561c351f2bc33317e388
runtime_digest: fb71984154500cd456b9bf2a99e133bbdd18a8f1f512e5a2066aa572389762bc
launcher_manifest_sha256: 859139b015d687b0c85457ebcdc6a3461cb811fefac21d2fec526ed9b762aedb
agency_config_sha256: 43367ec9aa05a66fc2a60bb254f270836fb3616753769115fabb253a04d5d9f8
openclaw_config_before_after_sha256: 562c0c4e2f09844afb0ffa7858f413d8b478f698340a3dda7c7b88e89ee9949e / cfdacc1dff2ffb403b5bdce8af5c1934f19186b5cd0d85d446b73f4497cb7889
native_primary: litellm/task-general
native_fallback_count: 6; exact prior list unchanged
registered_hooks: 11; required set complete
gateway_restart: active/running; RPC green; zero restarts
telegram_probe: configured; running; credential probe ok
credential_env_name: LITELLM_API_KEY
credential_present_source: configured env reference plus populated service environment file; value excluded
hermes_break_glass: active and unchanged
diagnostic_content: phase, booleans, surface count, content length, authorization count only
diagnostic_exclusions: message text, identifiers, credentials, and payloads
failed_backup_attempts: system sqlite3 unavailable; nonexistent contractor SQL table; literal tilde path hash
backup_recovery: Python SQLite backup API; checkout contractor CLI; normalized native config path
fresh_changed_new: failed; operator received no acknowledgement
openclaw_runs_since_send: 0
routing_decisions_since_send: 0
phase_sequence: reply_payload observed without authorization; before_reset authorized 2 ms later; reply_payload timed out after 1 second
session_shape: both callbacks supplied a session; lifecycle identities differed; identifiers excluded
failure_artifact: /tmp/ar119-openclaw-phase-trace-preinstall.VGtfCi/openclaw-native-control-fourth-failure-redacted.json
failure_artifact_sha256: 0fe6ae7a54ea0047422d0a4560b71027e18f2cc3b95ac27f3be281bf6cc16ed1
expected_red: distinct pre-reset/post-reset/delivery session regression failed at exit 30
candidate_rule: exact session first; otherwise require one recent exact unambiguous authorization
ambiguity_replay_wrong_text_expiry: fail closed
focused_tests: 246 passed; 1 intentional skip
candidate_installed: false
delegation_proven: false
matrix_cell_moved: false
protected_hosts: Codex OAuth/config/canary, Claude, ZCode, and Hermes untouched
~~~

### OpenClaw sessionless repair install and earlier-gate failure bundle

~~~yaml
host: openclaw
checkout_sha: 99b1380d445aac111bef5c477f2850b320bfdf8d
repair_commit: d4d4b8294346df8d063703bd27d27e394fa81d24
host_version: OpenClaw 2026.7.1-2
pre_install_store_backup: /tmp/ar119-openclaw-sessionless-preinstall.CObn63/agency-store.before.db
pre_install_store_backup_sha256: 5ca1ffbefdea30f8882445d448dee518ca0b6dc68d23b57adb5b64f5b74dcd75
store_integrity_source_backup: ok / ok
store_schema: 47
contractors_before_after_install: 15 / 15
install_id: 5e1a074e-81a6-4fdf-a464-937c66d9b400
install_result: complete; Agency only; installer left gateway stopped
bundle_digest: b0010f677c300fc43b86819d3b3d199065f49d65f067caaa10895d358e1098c8
runtime_digest: ebbf13cdf5827160d2e6daf314c79e3b2e07b030c792ff81e244ab72cc04bc59
launcher_manifest_sha256: 7f393f2acbd61db5e293dffa45b6ed73ad22218d158e76be85cb353223ec41d9
agency_config_sha256: 43367ec9aa05a66fc2a60bb254f270836fb3616753769115fabb253a04d5d9f8
openclaw_config_before_after_sha256: 205465ad1ffeff70cee246a4a6001533fc063e88485ae0d81a090143634539b6 / 049aacc863b99343abc4bed221213ba185fee472be9e292783c779cfcbab8a76
native_primary: litellm/task-general
native_fallback_count: 6; exact prior list unchanged
gateway_restart: first warm-up RPC miss retained; second RPC green; zero restarts
telegram_probe: configured; running; credential probe ok
hermes_break_glass: active and unchanged
fresh_native_session_id: 1b4c7016-cac1-4aca-8639-075038d5b982
operator_command: /new
native_reset_applied: true
acknowledgement_delivered: false
post_send_agency_runs: 0
native_log_event_sha256: e66fb2926e04a48840632eff96aa3469b4a4f4d3d592292fe2f35fa662d30dfb
failure_artifact: /tmp/ar119-openclaw-sessionless-preinstall.CObn63/openclaw-reset-ack-second-failure-redacted.json
failure_artifact_sha256: 22f88b593872ecac16718454f75947d639b00601beae67b4019c42ded684ff93
root_cause: native acknowledgement crosses reply_payload_sending before message_sending; only the latter had the exact reset exception
expected_red: complete two-gate flow failed at exit 30 before implementation
candidate_rule: first gate verifies without consuming; final message gate remains the one-use consumer
ambiguity_replay_wrong_text_expiry: fail closed
focused_tests: 246 passed; 1 intentional skip
candidate_installed: false
delegation_proven: false
matrix_cell_moved: false
protected_hosts: Codex OAuth/config/canary, Claude, ZCode, and Hermes untouched
~~~

### OpenClaw refreshed-header truncation candidate

The retained fresh-status failure is now isolated to OpenClaw's model-visible
tool-result projection. A 100,000-character native read result and separate
878-character Agency update entered the host's 4,000-character,
`minKeepChars=0` recovery path. The smaller block lost the exact five header
lines before the parent model ran; Store mutation and fail-closed finalization
were correct.

The reviewed Agency-only candidate prefixes the update into the first native
text block and splits only a cloned result at UTF-16-safe 100,000-character
boundaries. Against installed OpenClaw 2026.7.1-2, the observed shape validates
as blocks of 100,000 and 880 characters. All native text remains reconstructable
after removing the prefix. The exact recovery projection yields 3,965 and 71
model-visible characters, with every exact updated header line in the dominant
first block. At an exhausted 200-block boundary the candidate returns no
replacement and preserves fail-closed finalization instead of trimming native
evidence.

~~~yaml
host: openclaw
candidate_base_checkout: 01a8ad240267
host_version_contract: OpenClaw 2026.7.1-2
failure_run_id: a4b27543-7644-4cad-bd0d-2ef9ec9f7581
failure_trace_id: 7e7a6318-5b6a-4afc-b8a1-0ec57103bd1f
failure_skill_row_id: 3b9037a9-6ea8-48e1-a9cf-39aeb520b744
failure_terminal_id: 25cf1630-de51-4f21-9050-9da41e01c0ae
root_cause: separate refreshed context lost to zero-minimum proportional recovery projection
expected_red: exit 236; separate block did not satisfy dominant-block framing contract
rejected_draft: exceeded native 100000-character post-middleware text-block limit
candidate_behavior: prefix first text; UTF-16-safe split; preserve native content/details; fail closed at exhausted 200-block cap
installed_validator_blocks: [100000, 880]
recovery_projection_cap: 4000
recovery_projection_minimum: 0
recovery_projection_blocks: [3965, 71]
updated_five_line_header_survived: true
focused_tests: 251 passed; 1 intentional skip
targeted_ruff_and_diff: pass
independent_review: no blocker
candidate_installed: false
native_primary: litellm/task-general; unchanged
agency_profile_alias: linux-task-agency-router / task-agency-router; unchanged
hermes_break_glass: active and untouched
delegation_proven: false
matrix_cell_moved: false
protected_hosts: Codex OAuth/config/canary, Claude, ZCode, and Hermes untouched
~~~

### OpenClaw refreshed-header repair install bundle

~~~yaml
host: openclaw
checkout_sha: 456a75b7e984c905c2331a7b938e10de67a4a2e5
repair_commit: d7187e809523503b5d8162d3334afc497fe1d3f6
clean_tree_before_install: true
host_version: OpenClaw 2026.7.1-2
active_queued_tasks_before_stop: 0 / 0
preinstall_artifact_root: /tmp/ar119-openclaw-header-preinstall.DV7PrH
store_backup_sha256_before_after_install: abcc1396b46f7dd087f034f42b520d40fee9873b72e314d78621cdced0e470d2 / same
store_integrity_before_after: ok / ok
store_schema: 47
contractors_before_after: 15 / 15
install_id: fa68e6a4-75d9-4a47-8358-20b4e654b10e
install_result: complete; Agency only; installer left gateway stopped
bundle_digest: 36619063a5483f258abd55abc97e516d37870b921878bc12c32c5c7bd0212e07
runtime_digest: 573a6a140cb23a60b48ba4b6ce638cccba6854fa11acd701aa05c9cc47ce1ab4
launcher_manifest_sha256: d65af026617abe5d836b9ba9ec3b6efe63d0815ef971c2b8f93bf7007e7771ef
launcher_source_root: checkout agency_runtime package
agency_config_sha256: 43367ec9aa05a66fc2a60bb254f270836fb3616753769115fabb253a04d5d9f8
openclaw_config_before_after_sha256: b54228aeaede1ae13722abba21879bfd7f256d79dacee368d95323d7785b9810 / 1c6f74936984f8c137c0d79016547a01e3bead7f6a9747ada4aa3b04c766f134
openclaw_config_changed_leaf: meta.lastTouchedAt only
native_primary: litellm/task-general
native_fallback_count: 6; exact prior list unchanged
agency_profile: linux-task-agency-router
requested_alias_model_group: task-agency-router
credential_env_name: LITELLM_API_KEY
credential_present_in_live_process: true
gateway_restart: native start; active/running; RPC health ok; zero restarts
plugin_runtime: enabled, activated, loaded; version 0.1.0; zero diagnostics
registered_hooks: 12; required set complete; awaited tool-result middleware present
slack_telegram: configured, enabled, running, connected; token indirection available; no current error
hermes_service: active and untouched
hermes_config_sha256: 95b87b7fc0427ad4e3da4f5f468054cf9f7ddba679d1bb606b782a13e1a0172d
hermes_environment_sha256: 792fd43a5312d1c1d69f6afbeef3bbdd1a8198ee03ac06b4b3b6dfa20ec2f324
hermes_launcher_sha256: 7c033c97e7f4ce2108efcccfadc4f1c9e4511dc98afa11085adfd898f27585c3
fresh_session_status_skill_substantive_proof: passed; see refreshed-header final live acceptance bundle above
delegation_proven: false
matrix_cell_moved: false
protected_hosts: Codex OAuth/config/canary, Claude, ZCode, and Hermes untouched
~~~

### Current scoped verdict after refreshed-header live proof

The authoritative OpenClaw bundle is
`OpenClaw refreshed-header final live acceptance bundle` above. Fresh reset,
status, native skill loading, bounded substantive parent routing, Store-backed
first-pass headers, and Telegram delivery pass on installed repair `d7187e80`.
Every Agency inference attempt stayed on `linux-task-agency-router`, provider
type `litellm`, and exact alias/model-group `task-agency-router`; cross-provider
fallback was zero. The proxy callback is absent, so no actual answering model
is claimed. No delegation, native child, Rule 4 delivery, or matrix-cell proof
exists. Hermes is the only next host package; protected hosts remain untouched.

### Hermes current-checkout Agency install checkpoint

~~~yaml
host: hermes
checkout_sha: 80d686a27f9955e1d2c9aa5f454947c45145b052
host_version: Hermes Agent v0.20.4 (2026.8.18)
effective_home: /home/holeshot/.hermes-nexus
owning_service: hermes-gateway-nexus.service
native_primary: task-general
native_fallback_count: 5; exact prior list unchanged
native_config_sha256: 95b87b7fc0427ad4e3da4f5f468054cf9f7ddba679d1bb606b782a13e1a0172d; unchanged
native_environment_sha256: 792fd43a5312d1c1d69f6afbeef3bbdd1a8198ee03ac06b4b3b6dfa20ec2f324; unchanged
plugin_inventory_before_after: 59 discovered / 6 enabled; unchanged
plugin_inventory_before_after_sha256: a675e84579e0b48097e0ea2d3a3df7f5532615f79a47af7e0bfce70c11b0e9b1 / same
store_backup_before_after_sha256: 02a76504f72946b7181619642e5b454ee49d0b9f9421632e1fe6f24a1b8ffbba / same
store_integrity_before_after: ok / ok
store_schema: 47
contractors_before_after: 15 / 15
service_before_install: owning custom service stopped; gateway exited, while systemd retained failed/exit-code for the stop receipt
install_id: 0a3d141a-4e32-40d2-8c3d-6a7e296eb55f
install_result: complete; Agency only; --no-dashboard; installer did not restart Hermes
bundle_digest: 45b76c0e45cddaa0f0d6caec1855db93013bdf0fb78ec6616827abde8d7322c7
runtime_digest: 573a6a140cb23a60b48ba4b6ce638cccba6854fa11acd701aa05c9cc47ce1ab4
launcher_manifest_sha256: e65a078479cc4f6196b3b5b61f15c15ffd36bf9cda0f5082b8bc844b7a4ed9e7
launcher_source_root: current checkout agency_runtime package
plugin_doctor: 8 hooks; 0 tools; installed inventory recognized
service_after_restart: same owning service active/running; NRestarts=0; Result=success
credential_env_name: LITELLM_API_KEY
credential_present_boolean: true in live Hermes service; value never read or emitted
agency_inference_profile: linux-task-agency-router
agency_provider_type: litellm
requested_alias_model_group: task-agency-router
fresh_reset_status_skill_substantive_proof: pending
attribution_proven: false
delegation_proven: false
rule4_proven: false
matrix_cell_moved: false
known_limit: installation and restart only; no live Hermes header, Store routing, skill, substantive response, or transport-delivery proof yet
protected_evidence: OpenClaw accepted proof and all earlier failures preserved; Codex OAuth/config/canary, Claude, and ZCode untouched
~~~

### Hermes final host-scoped parent acceptance bundle

~~~yaml
host: hermes
checkout_sha: a6a45d91c1a3ef21c4aa857c3f11c09b497bce90
installed_source_checkout_sha: 80d686a27f9955e1d2c9aa5f454947c45145b052
clean_tree: true at Agency install; runtime code unchanged during live proof; evidence-document changes present while recording
host_version: Hermes Agent v0.20.4 (2026.8.18)
profile_identity: hermes -> linux-task-agency-router
native_litellm_config_source_redacted: /home/holeshot/.hermes-nexus/config.yaml and .env; native task-general plus five exact prior fallbacks unchanged; values excluded
litellm_base_url_source: effective ~/.agency-runtime/agency.yaml profile linux-task-agency-router
litellm_base_url: http://127.0.0.1:4000/v1
credential_env_name: LITELLM_API_KEY
credential_present_boolean: true in live Hermes service; value never read or emitted
agency_inference_profile: linux-task-agency-router
agency_provider_type: litellm
requested_alias: task-agency-router
model_group: task-agency-router
actual_model_and_receipt_source: Hermes host receipts observe native task-general alias; Agency wrapper receipts repeat task-agency-router alias; actual upstream model unavailable because proxy callback is absent; neither alias is promoted
runtime_digest: 573a6a140cb23a60b48ba4b6ce638cccba6854fa11acd701aa05c9cc47ce1ab4
store_schema: 47
install_result: 0a3d141a-4e32-40d2-8c3d-6a7e296eb55f; complete; Agency only; no dashboard; installer did not restart Hermes
launcher_manifest_sha256: e65a078479cc4f6196b3b5b61f15c15ffd36bf9cda0f5082b8bc844b7a4ed9e7
fresh_session_id: ...65697a38
fresh_reset_result: acknowledged; fresh session created
status_run_id: 116caa4a-d364-4269-9903-ca49d8de90f5
status_trace_id: ...65697a38:...65697a38:b446051a
status_routing_decision_id: b6ace409-07e7-4d91-af26-c21480b197a4
status_finalization_id: dee42fb2-8877-4dc6-ad22-f50d16fbac2b
first_response_artifact: Hermes native response plus transcript manifest; exact header embedded below
first_response_artifact_sha256: 5b9fd3f22718ac6ab1ffa8efc1b646320b3225af1715067d302f696a4e6ba3c3
first_response_manifest_sha256: 886d32acd851d450f1f3aa5a1e0075598a7387706d44207048138f7a00889bc7
first_response_header_exact: |-
  Agency/Agencies loaded: agency-steward
  Agency/Agencies delegated: none
  Skills loaded: hermes-agent
  Actual Model selected: observed execution receipt: [general] task-general -> task-general (host)
  Recruited via: deterministic
first_response_delivery: Telegram; 1,140 characters; 223.6 seconds
skill_run_id: e328626d-011a-4cb2-a797-ea6ff7499897
skill_trace_suffix: 432b78d6
skill_routing_decision_id: d1da7fd7-b4a2-4df3-b056-d6cd866c6789
skill_specialist_id: b2385c80-6267-41d9-81f0-78fc8dce7787 # technical-writer
skill_name_and_store_row_id: codebase-inspection / [a070accc-2c7e-45c8-aac8-cb680896c935, 8218bddf-acc1-426e-8b11-94d5c51eed9c]
skill_finalization_id: 53a5245b-2146-480e-a51e-f58dcd470d6c
skill_provider_receipt_ids: [35eaf475-0ccd-4a22-a614-5c76ee99d0b0, 26280cdc-5ecc-48f0-8deb-c391d9ebdfdb, d712bd47-5f32-42d6-97f0-e662107b147a]
skill_header_exact: |-
  Agency/Agencies loaded: agency-steward, technical-writer
  Agency/Agencies delegated: none
  Skills loaded: codebase-inspection
  Actual Model selected: observed execution receipt: [general] task-general -> task-general (host)
  Recruited via: inference
skill_delivery: Telegram; 427 characters; 58.2 seconds; response SHA-256 25b5be683b454d7e221701d944b8a9ed138fbd9acdc5a2c1b859117d78d1c09d
retained_typo_evidence: run dedbed83-db25-4813-bb50-627328d27409; input missing leading R; selected senior-secops-engineer; read-only; no delegation; terminal d010887b-0794-4d3a-9579-7f279d11d142; Telegram 4,928 characters / 676.1 seconds; response SHA-256 6026fbe062248f69cba73112eda70655d28ba28b1fd59bc72a5e7d071276a06e; not substituted for exact draw
agency_trace_id: ...65697a38:...65697a38:b2e909cf
substantive_prompt_sha256: d79ece6296b0a792ee4ff6d9bad6fb655fe610812a111cc74ccff599d5c12fb1
substantive_run_id: d29c4652-46a9-41db-938c-d3b3bfdf3726
substantive_finalization_id: 543adf12-bac1-4588-8f00-a53c54b305f3
header_exact: |-
  Agency/Agencies loaded: agency-steward, ai-evaluation-engineer
  Agency/Agencies delegated: none
  Skills loaded: agent-runtime-operations, pr-review-workflow, hermes-agent
  Actual Model selected: observed execution receipt: [general] task-general -> task-general (host)
  Recruited via: inference
resident_binding_id: none
routing_decision_ids:
  - b6ace409-07e7-4d91-af26-c21480b197a4 # deterministic status abstention
  - d1da7fd7-b4a2-4df3-b056-d6cd866c6789 # codebase-inspection skill turn
  - 1bc084f2-5fc4-4832-b77b-f82352b4840f # exact substantive turn
specialists_loaded_ids:
  - b2385c80-6267-41d9-81f0-78fc8dce7787 # technical-writer; skill turn
  - b952d046-e5c8-4a30-9e60-bcce44db252b # ai-evaluation-engineer; substantive
substantive_skills_loaded_ids:
  - 2e62f150-cda0-490e-952a-2feb6d410bb6 # agent-runtime-operations
  - 6cac7dc0-7228-42e8-841f-4d239a4712ba # pr-review-workflow
  - 0bde577c-803d-4ff2-bdf8-86b68350f280 # hermes-agent
provider_receipt_ids:
  - 72c45dae-ae57-482c-a41f-85ad3ef5009b # ordinal 1; applied
  - 5c096da9-6a82-415c-855e-87a1f5fd9948 # ordinal 2; applied
  - 6286cc80-d5ea-49e1-9d47-f0af4d89f096 # ordinal 3; applied
provider_attempt_status: all three applied; Hermes selected automatically; exact linux-task-agency-router / litellm / task-agency-router alias and model-group
fallback_count: 0 cross-provider; every Agency wrapper attempt stayed on the same profile
substantive_response_sha256: 1381e301f248417c4480ce4da51af35fc8c1b001443b0514a37e55df2532b7fc
substantive_transcript_manifest_sha256: 12637e2a6c30718c62a8234a6f13632cc124aa16007e690e8c2eb85eb0ab9a25
substantive_delivery: Telegram; 5,274 characters; 263.9 seconds
delegation_worker_activation_child_rows: 0 / 0 / 0 / 0
timeout_or_failure_receipt:
  - a9874148-d04a-440c-a964-a7ed39572c31 / 2934adb1-bc02-4001-abf9-87863b006006
  - e38ecc07-9698-4144-91c1-2a0b01d2c1e3 / 60547574-02a1-4b2e-928c-4c23f8a5ae72
  - 3608e1d2-dfbf-4884-b6fa-0edefc16a895 / 3f54ebbc-86b8-4ad7-be2b-2ecd704fccd9
post_response_failure_scope: internal non-user preflights; two strict contract-invalid planner attempts each; same Agency profile; delivered replies unaffected; no accepted user turn timed out
plugin_doctor_failed_attempt: bare cwd-sensitive invocation retained as failed environment evidence
plugin_doctor_corrected: HERMES_HOME=/home/holeshot/.hermes-nexus hermes plugins doctor agency-preflight --ci; 8 hooks; 0 tools; pass
plugin_inventory: 59 discovered / 6 enabled / 4 non-bundled; unchanged
contractors_before_after: 15 / 15
store_integrity_before_after: ok / ok
post_live_store_backup_sha256: bdf1a6e66136b80cfa7ea736c81cceaee45a53aa6951388869d32087515b2654
agency_config_sha256: 43367ec9aa05a66fc2a60bb254f270836fb3616753769115fabb253a04d5d9f8
native_config_sha256: 95b87b7fc0427ad4e3da4f5f468054cf9f7ddba679d1bb606b782a13e1a0172d
native_environment_sha256: 792fd43a5312d1c1d69f6afbeef3bbdd1a8198ee03ac06b4b3b6dfa20ec2f324
known_limit: actual upstream model unavailable without callback telemetry; post-response internal strict-planner failures remain lifecycle debt; no delegation, native child, Rule 4 delivery, or AR-119 matrix-cell proof
protected_evidence: OpenClaw acceptance and all retained failures unchanged; Codex OAuth/config/canary, Claude, and ZCode untouched
~~~

### Final evidence-record validation receipts

The first final policy-availability check lacked the checkout on
`PYTHONPATH` and failed import before evaluation; the corrected checkout-bound
invocation passed. Bare `ruff` was unavailable in the ambient shell (exit 127);
the checkout's `.venv/bin/ruff` passed both lint and format checks.

The first post-live focused pytest rerun inherited a shared temporary namespace
whose generated configuration parent was `0775`; 118 tests failed the intended
cross-account substitution guard. A changed-input rerun used an owner-private
temporary root, reducing the result to 50 failures because the virtual
environment resolved its fixture launcher through an untrusted group-writable
UV interpreter identity. The final changed-input run kept umask `0077`, used a
new private temporary root, and set the CI-only fixture launcher to root-owned
`/usr/bin/python3.12`; it passed 304 tests with one intentional skip. No runtime,
host, Agency, LiteLLM, Codex, Claude, or ZCode configuration changed between
these validation attempts.

### OpenClaw failed child delivery and locally green correction (AR-281/AR-282)

The retained first OpenClaw draw executed a real `sessions_spawn` worker and
completed its read-only task. Delivery nevertheless failed: completion entered
a synthetic `announce:v1:...` run, attempted a targeted message send, and was
suppressed by Agency before Telegram queueing. That draw also exposed the
unprojected host timeout and process-local end correlation. It proves child
execution only, not parent return or transport delivery.

The Agency-only repair projects the OpenClaw harness timeout into native-child
staffing, reconciles lifecycle from durable exact parent/worker/run/launch
bindings, and prepares/finalizes completion against the original parent trace.
The completion contract permits exactly one implicit-target, one-use
`message(action=send)` containing the finalized parent five-line header and
body. Wrong requester, worker, run, launch, header, target, replay, restart, or
ambiguous correlation fails closed. The completion path creates no synthetic
announcement run and records no Agency inference receipt.

The focused profile, installer, adapter, lifecycle, and security gate passes
299 tests with 1 existing skip. Clean checkout
`27e9ec6267522f7ad2d23695737c6a69b9d052f1` was installed through Agency's
OpenClaw installer only while the audited 2026.7.1-2 gateway was natively
stopped. The installer did not restart it. Native restart then restored RPC
health and a loaded, enabled, activated Agency plugin with all 12 hooks.

Native `litellm/task-general` and all six fallbacks remain exact; the semantic
config diff after excluding OpenClaw's host-managed timestamp is empty. The
live process has `LITELLM_API_KEY` populated, but its value was neither read
nor retained. Contractors remain 15 before and after; pre-install Store
integrity is `ok` and schema remains 47. Hermes remained active as break glass
with config, environment, and launcher hashes unchanged and no install or
configuration change.

The changed live draw is preserved as another failed delivery, not acceptance.
Telegram `/new` was acknowledged, then parent run
`a0f349c8-712d-4702-bc14-ac2e8e0e4ee1`, trace
`856341f9-40f0-49f7-99fd-ba39a4a4a6c8`, and native transcript
`4ad38fad-d167-4310-a4e7-2a0c8f189646` launched exactly one OpenClaw child.
Worker `agent:nexus:subagent:e0ee5df5-a66e-4085-b7e1-19bb41dbfed5`, native run
`b182db5c-1764-4d83-a0be-c5a0575ac828`, launch
`call_Ax3H8A73e4NA174ifqGEEYSh`, work unit `unit-7899e62213`, and child
transcript `bf9127d3-6436-49a6-bf28-9af373ab371e` prove that the child executed
and completed its read-only review. Delegation
`35572adf-23a2-4764-94a9-632965182ea8` and worker row
`native-child:8819ea2f6e84896205ad25b2e853b4ed63aaa7d7bf66e0abd8d91d17a6b3d7fb`
remain open. The exact host completion identity was
`announce:v1:agent:nexus:subagent:e0ee5df5-a66e-4085-b7e1-19bb41dbfed5:b182db5c-1764-4d83-a0be-c5a0575ac828`;
the bridge did not create a synthetic Store run for it. Completion was blocked
as uncorrelated before Telegram queueing, so the operator received no reply and
the parent lifecycle never finalized.

The parent canonical route
`ba9e00d0-b2ac-4ffb-a1ce-7b2c27a53d4c` and auxiliary native-child route
`native-child-eaa40e37d3a5dad02a475e9a38fca63d` are both valid. The latter has
one applied `litellm` attempt on `linux-task-agency-router`, exact requested
alias/model-group `task-agency-router`, zero cross-provider fallback, and no
provider-supplied actual-model receipt. Cleanup happened after the block; no
gateway restart/reload, timeout, TTL expiry, or parent/child/launch identity
mismatch occurred. Every durable completion-resolver identity predicate passed.

The exact defect is in ready-receipt integrity validation: the canonical
preflight routing checker required exactly one total `routing_decisions` row,
while successful native-child staffing validly appends a second
`native_child_inference` row to the same parent trace. The ready receipt was
therefore rejected, completion preparation returned no context, and the bridge
emitted its generic uncorrelated denial. The locally green Agency-only candidate
accepts exactly one canonical route plus unique auxiliary routes that strictly
re-project as complete native-child successes. It validates exact route IDs,
canonical Store timestamps and context digests, exact numeric types, canonical
JSON fields, and unique host/launch identities. Duplicate canonical or
auxiliary routes and malformed, unrecognized, timestamp-shifted, numeric- or
JSON-type-shifted rows continue to fail closed.

Independent Critical/High review is green after closing the duplicate,
timestamp, numeric, JSON, context-digest, and route-ID integrity gaps. Focused
validation passes 113 tests with 1 existing skip; the named fast Python spine
passes 848 with 3 skips. Metadata, policy availability, worklog, and
documentation checks pass across 780 Markdown files with a 1,155-commit worklog.
Full Ruff lint and format pass across 682 files; dashboard UI passes 134 tests;
the routing evaluation passes. Full decision conformance passes baseline and
kills 160/160 mutations with zero survived or invalid mutations, leaving the
source unchanged. `git diff --check` passes.

The first full-evaluation attempt used a private default home without `pytest`.
The changed `.venv` retry correctly failed the trusted persistent-interpreter
boundary. The final changed-input owner-private evaluation environment based on
`/usr/bin/python3` passed. These failed attempts remain part of the record. The
exhaustive workflow-dispatch corpus was not run. That locally green candidate
was then recorded in clean implementation/ledger commits and installed through
Agency only; the exact install checkpoint is retained separately in this
packet. It is still unproven live. Even a later operational completion and Telegram delivery
cannot satisfy ADR-0156 Rule 4 without an immutable host-authored
`native_child_delivery_verifications` receipt.

~~~yaml
host: openclaw
checkout_sha: 27e9ec6267522f7ad2d23695737c6a69b9d052f1
clean_tree_before_install: true
host_version: OpenClaw 2026.7.1-2
install_result: complete; Agency only; no dashboard; gateway natively stopped; installer did not restart it
bundle_digest: 0c2bb3fc55ac94a79fc88db76549a5aef3d76124f85ef347e9fb023e01bf8999
runtime_digest: 0c2bb3fc55ac94a79fc88db76549a5aef3d76124f85ef347e9fb023e01bf8999
launcher_manifest_sha256: e9169d044ba88a28a23b51b342d14e2031864a4e5ccdc7afa3d30386fbfa8cdc
gateway_restart: native; RPC true
plugin_runtime: loaded, enabled, activated; 12 hooks
credential_env_name: LITELLM_API_KEY
credential_present_boolean: true in live OpenClaw process; value never read or retained
native_primary: litellm/task-general
native_fallback_count: 6; exact prior list unchanged
native_config_semantic_diff_excluding_timestamp: empty
agency_profile: linux-task-agency-router
requested_alias_model_group: task-agency-router
contractors_before_after: 15 / 15
preinstall_store_integrity: ok
store_schema: 47
hermes_service: active; no install or change
hermes_config_sha256: 95b87b7fc0427ad4e3da4f5f468054cf9f7ddba679d1bb606b782a13e1a0172d; unchanged
hermes_environment_sha256: 792fd43a5312d1c1d69f6afbeef3bbdd1a8198ee03ac06b4b3b6dfa20ec2f324; unchanged
hermes_launcher_sha256: e65a078479cc4f6196b3b5b61f15c15ffd36bf9cda0f5082b8bc844b7a4ed9e7; unchanged
fresh_telegram_reset: acknowledged
parent_run_id: a0f349c8-712d-4702-bc14-ac2e8e0e4ee1
parent_trace_id: 856341f9-40f0-49f7-99fd-ba39a4a4a6c8
parent_transcript_id: 4ad38fad-d167-4310-a4e7-2a0c8f189646
child_worker_id: agent:nexus:subagent:e0ee5df5-a66e-4085-b7e1-19bb41dbfed5
child_native_run_id: b182db5c-1764-4d83-a0be-c5a0575ac828
child_launch_id: call_Ax3H8A73e4NA174ifqGEEYSh
child_work_unit_id: unit-7899e62213
child_transcript_id: bf9127d3-6436-49a6-bf28-9af373ab371e
delegation_id: 35572adf-23a2-4764-94a9-632965182ea8
worker_row_id: native-child:8819ea2f6e84896205ad25b2e853b4ed63aaa7d7bf66e0abd8d91d17a6b3d7fb
child_execution: completed read-only task
completion_delivery: blocked before Telegram queueing; no operator response
canonical_routing_decision_id: ba9e00d0-b2ac-4ffb-a1ce-7b2c27a53d4c
native_child_routing_decision_id: native-child-eaa40e37d3a5dad02a475e9a38fca63d
native_child_provider_attempt: applied; linux-task-agency-router; litellm; task-agency-router
native_child_fallback_count: 0
actual_model_and_receipt_source: unavailable; provider telemetry supplied none
failure_cause: ready-routing receipt required one total route after valid native_child_inference route append
candidate_validation_state: locally green
independent_review: GREEN; no Critical or High findings open
focused_tests: 113 passed; 1 skipped
named_fast_spine: 848 passed; 3 skipped
docs_validation: 780 documents; worklog current at 1155 commits
ruff: check and format passed; 682 files
dashboard_ui: 134 passed
routing_eval: passed
decision_conformance: baseline passed; 160/160 killed; 0 survived; 0 invalid; source unchanged
failed_eval_attempts: private HOME lacked pytest; checkout .venv failed trusted-persistent-interpreter boundary
passing_eval_environment: owner-private venv based on /usr/bin/python3
exhaustive_workflow_corpus: not run
native_child_spawn_execution_proven: true
completion_delivery_proven: false
operational_acceptance_green: false
rule4_proven: false
matrix_cell_moved: false
protected_hosts: Codex OAuth/config/canary, Claude, and ZCode untouched
~~~

## 2026-08-24 - Latest bounded checkpoint

Installed correction/ledger `933d9f4a` / `84e85a4c` produced another changed
OpenClaw child whose response reached Telegram, but Agency lifecycle remained
open. Parent run `0191a16c-d5cf-485b-bfa0-70199097ef95`, trace
`29e96603-cfdc-4ec4-8c86-993b6c9179b7`, native run
`368bcc67-c1ef-43a7-bf3e-28bd751e8648`, and delegation
`d6ceb33a-cf76-4c23-aee5-4d221f35255b` are the retained correlation. With
`cleanup: delete`, OpenClaw removed the host registry entry before its deferred
`subagent_ended` check could emit the receipt Agency expected. This is a failed
Agency-terminalization draw, not acceptance.

Workforce inference still selected the OpenClaw harness automatically and used
`linux-task-agency-router` / `litellm` / exact requested alias/model-group
`task-agency-router` with zero cross-provider fallback. OpenClaw's distinct
native execution stayed on `task-general`; provider telemetry supplied no
actual answering model.

AR-283's uninstalled candidate advances the Store from schema 47 to 48. Child
`agent_end` records the first immutable outcome and delivery `pending` without
closing lifecycle. `message_sending` records every allowed text send in a
bounded attempt ledger but is pre-transport. Only OpenClaw 2026.7.1-2's
post-adapter `message_sent(success=true)` with one unique active attempt
atomically records `delivered` and closes worker and delegation. Explicit
failure records `failed` and remains open. `gateway_start` reconciles only
durable receipt-backed pending/failed rows as `interrupted` lifecycle failures
while preserving observed execution outcome; it does not sweep unobserved open
work. Generic end/stop handling cannot bypass the delivery gate.

The host exposes no shared immutable send identifier. Correlation therefore
requires every supplied target/channel/account/conversation/session/run field
and the finalized response hash to match one active ledger attempt. Active
attempts remain at least one hour and consumed ambiguity tombstones 24 hours;
stale, delayed, replayed, ordinary-identical, zero, multiple, or conflicting
matches fail closed. A crash after platform acceptance but before the Store
success commit remains irreducibly ambiguous and resolves as interrupted,
never delivered.

~~~yaml
host: openclaw
installed_checkout_sha: 933d9f4a5bb3dcade7ad6dc726b0d267f0582cde
installed_ledger_sha: 84e85a4ca681394416ac3c0a1b23e73e707f32f3
host_version: OpenClaw 2026.7.1-2
installed_store_schema: 47
candidate_store_schema: 48
parent_run_id: 0191a16c-d5cf-485b-bfa0-70199097ef95
parent_trace_id: 29e96603-cfdc-4ec4-8c86-993b6c9179b7
child_native_run_id: 368bcc67-c1ef-43a7-bf3e-28bd751e8648
delegation_id: d6ceb33a-cf76-4c23-aee5-4d221f35255b
host_delivery: child response reached Telegram
agency_terminalization: failed; worker and delegation remained open
failure_cause: cleanup delete removed registry before deferred child-end receipt
agency_profile: linux-task-agency-router
provider_type: litellm
requested_alias_model_group: task-agency-router
native_execution_alias: task-general
fallback_count: 0 cross-provider
actual_model_and_receipt_source: unavailable; provider telemetry supplied none
candidate_state: uninstalled; 294 focused tests passed, 1 unrelated skip; independent review GO
candidate_delivery_success_gate: message_sent success only
candidate_explicit_failure: failed; lifecycle remains open
candidate_restart_reconciliation: receipt-backed pending/failed become interrupted lifecycle failures; observed child outcome preserved separately
candidate_attempt_correlation: one active match across supplied target/channel/account/conversation/session/run plus exact response hash; active >=1h; consumed tombstone 24h; capacity fail closed
crash_after_platform_acceptance_before_store_commit: interrupted; never delivered
hermes: active break glass; untouched in this package
operational_agency_terminalization_proven: false
rule4_proven: false
matrix_cell_moved: false
tracker_state: AR-283 creation pending separate authorization
protected_hosts: Codex OAuth/config/canary, Claude, and ZCode untouched
~~~

The schema-48 candidate still requires a clean local substantive/ledger
checkpoint, Agency-only installation while
OpenClaw is natively stopped, and one genuinely changed live draw. Hermes stays
break glass until OpenClaw passes. No Rule 4 or matrix claim moves.

## Merged schema-48 OpenClaw post-send acceptance

~~~yaml
host: openclaw
checkout_sha: 5511300ebc20af31cd6488a009f21f878326c231
minimum_ledger_sha: 7295f28980316739af83ba8fa55c91667022cba1
clean_tree_at_install: true
origin_main_sha: fc0770392b5a2cc38c589d2411698d0a0ac602ae
host_version: OpenClaw 2026.7.1-2
native_model_primary: litellm/task-general
native_model_fallback_count: 6; unchanged
agency_inference_profile: linux-task-agency-router
provider_type: litellm
requested_alias: task-agency-router
model_group: task-agency-router
fallback_count: 0 cross-provider
actual_model_and_receipt_source: unavailable; provider telemetry supplied none
launcher_manifest_sha256: 0ddbe52da806327d18091009bf79cdaf889899e6e41a525f1edd16715ca0ce50
store_schema: 48
store_integrity_live: ok
contractor_count: 15; unchanged
fresh_status_run_id: cc936edb-021d-4e32-bcb5-8771f180f972
fresh_status_trace_id: 6f57aca7-0073-4824-ab77-db68f471ae0d
fresh_status_routing_decision_id: a38adb08-3db4-4ba8-a1f5-f3a213a22336
fresh_status_finalization_id: ea3c8a3f-c612-447a-bcbc-28749e2ced43
fresh_status_route: deterministic; inference not attempted
fresh_status_header: agency-steward / none / none / requested execution alias task-general / deterministic
resident_binding_id: rmb-fef54dccff0a71da62d23ec36ae83a1b
resident_binding_scope: request_scoped / request; retained in runs.preflight_result
resident_manager_bindings_row: none expected for OpenClaw request-scoped contract
child_parent_run_id: c067362a-8bf1-46db-a6d5-85f21a847744
child_parent_trace_id: 079b9ba8-6dd6-4885-be6e-ad51db7ddc03
child_parent_routing_decision_id: fcdb5d39-fdc3-4765-81e4-3545d7f80ca9
specialist_loaded_id: 1b3db69a-dd17-4c04-8b7d-31e5fbf3e125
specialist_slug: code-reviewer
native_child_route_id: native-child-d7bc5cfc0114541571cb9e0202cc1701
native_run_id: dc60b3b9-916e-4d4a-99f7-0e0786d3ebdc
worker_id: native-child:9b3d120aa95786f6230cd1636eb913372d6c8b87210cf9cbdbb691263eae0320
delegation_id: 0d9f02a8-3610-4367-93b8-90a68fe62835
backend: sessions_spawn
native_terminal_outcome: ok
native_delivery_status: delivered
worker_exit_code: 0
worker_ended: true
delegation_status: completed
parent_finalization_id: c46d714d-92f0-4276-ae30-d75dbde5ba8a
parent_provider_attempts: 3 applied on linux-task-agency-router / litellm / task-agency-router
child_provider_attempts: 1 applied on linux-task-agency-router / litellm / task-agency-router
telegram_delivery: exact Store-backed header and file-line finding observed by operator
native_transcript_sha256: e2295eedcf915499b7b8c27261e95f83047885a29536c5e892fdc8d69220166c
native_trajectory_sha256: 9163d31805dc35929783703467e2b8c6f0f8a0ed3f277c0da287584dd8b4b459
operational_native_child_acceptance: pass
rule4_proven: false
matrix_cell_moved: false
remaining_openclaw_checks: none; completed in final parent checks below
fallback_evidence_limit: AR-284; attempted_fallbacks contains stage ordinals, so routing flags and provider identities prove zero cross-provider fallback
hermes: untouched break glass during this package
protected_hosts: Codex OAuth/config/canary, Claude, and ZCode untouched
~~~

### Final OpenClaw parent checks

~~~yaml
skill_run_id: 53f6d825-ca0d-4046-981a-194cbf0c061e
skill_trace_id: 3645e474-80a7-4c19-a1d5-f11acbaa1747
skill_routing_decision_id: 739b6d73-79d1-470d-8b15-66bffb37985b
skill_specialist_id: 477ff2c2-2bd6-49bb-970c-63081a38d116
skill_specialist_slug: codebase-onboarding-engineer
skill_store_row_id: 3e57162a-d280-422c-918a-d73e5cd7ae53
skill_name: openclaw-operations
skill_finalization_id: 18b8f125-9ef9-4237-adc8-a2da35ba8d63
skill_header: agency-steward, codebase-onboarding-engineer / none / openclaw-operations / task-agency-router wrapper / inference
skill_worker_count: 0
skill_delegation_count: 0
skill_transcript_sha256_at_delivery: 03660f3d2da3c6addade2de9b5ce169e2bc1071a38ec2491ca6a55a6bcd18730
skill_trajectory_sha256_at_delivery: e21700a609e107b5324fd997ea9ae13bd683fe49c9e4f163a7cbf59aab711057
substantive_run_id: 2b0033c9-a640-4275-8573-467b313d2411
substantive_trace_id: 06785961-364e-4d52-a2ce-e2c26921dacf
substantive_routing_decision_id: 6eb8f30d-8186-4e27-9ac8-79f117872d73
substantive_specialist_id: cce108ba-216a-4578-a651-fea47a5e4bc2
substantive_specialist_slug: code-reviewer
substantive_skill_store_row_id: 6512dcab-2777-4273-a2d8-bd181c708511
substantive_finalization_id: a6833f9a-cdeb-4498-849b-c32289d03232
substantive_header: agency-steward, code-reviewer / none / openclaw-operations / task-agency-router wrapper / inference
substantive_provider_attempts: 3 applied; openclaw / linux-task-agency-router / litellm / task-agency-router
substantive_fallback_considered: false
substantive_fallback_applied: false
substantive_actual_model: unavailable; zero LiteLLM callback receipts
substantive_worker_count: 0
substantive_delegation_count: 0
substantive_transcript_sha256: 8437676addffa339fb73d80f3cc1d65928372000e6de0141c8d69fa582c06955
substantive_trajectory_sha256: 4cfdbc295798c1e0de70f6cb9dd1d3aec74810ee69bc65343d7ad5662e4f9901
native_model_invariant: litellm/task-general plus six unchanged fallbacks; exact semantic equality to prework
final_store_backup: /home/holeshot/.agency-runtime/evidence/ar283-openclaw-final-qy36G1/agency-final.db
final_store_backup_sha256: a0d558a330c94b341e7624d455fe0c7ef257bd992a5903c8592e7a3f5de4f188
final_store_backup_integrity: ok
final_store_backup_schema: 48
final_store_contractors: 15; unchanged
remaining_openclaw_checks: none
openclaw_scoped_acceptance: pass
rule4_proven: false
matrix_cell_moved: false
~~~

## Current Hermes install and first-response checkpoint

~~~yaml
host: hermes
checkout_sha: 7a012d4772362ed7ba5b3c305cf13501f7f8d591
clean_tree_at_install: true
origin_main_sha: fc0770392b5a2cc38c589d2411698d0a0ac602ae
host_version: Hermes Agent v0.20.4 (2026.8.18)
effective_hermes_home: /home/holeshot/.hermes-nexus
profile_identity: hermes harness default -> linux-task-agency-router
native_litellm_config_source_redacted: /home/holeshot/.hermes-nexus/config.yaml; SHA-256 95b87b7fc0427ad4e3da4f5f468054cf9f7ddba679d1bb606b782a13e1a0172d; unchanged
native_environment_source_redacted: /home/holeshot/.hermes-nexus/.env; SHA-256 792fd43a5312d1c1d69f6afbeef3bbdd1a8198ee03ac06b4b3b6dfa20ec2f324; unchanged
native_service_manifest_sha256: 404d3227f17143a215613a2e215883c1f18553aea023da8f7872ce8c9f526d21; unchanged
native_plugin_inventory_sha256: b2f761002439d0a6de57638038d414efeda7d8567808c8a346b257cc821b8cfa; 59 total and 6 enabled; unchanged
agency_config_source: /home/holeshot/.agency-runtime/agency.yaml; SHA-256 43367ec9aa05a66fc2a60bb254f270836fb3616753769115fabb253a04d5d9f8; unchanged
litellm_base_url_source: agency inference profile base_url; http://127.0.0.1:4000/v1; includes /v1
credential_env_name: LITELLM_API_KEY
credential_present_boolean: true
agency_inference_profile: linux-task-agency-router
provider_type: litellm
requested_alias: task-agency-router
model_group: task-agency-router
actual_model_and_receipt_source: unavailable for Agency/upstream; status has only native task-general host receipts
runtime_digest: ecc0b1cb8859e9bb78ef9b394a312e10a2b9b6bed3ff2260a85b0e3fb502de59
bundle_digest: 05bada2969b77bc4d64111c1cc105b506bfdbab546a8298df3519995f9dc44fd
store_schema: 48
install_result: complete; ok true; partial false; install 4e97f5a6-7df9-42da-8f6f-b285b7d2f1a2; installer did not restart host
launcher_manifest: /home/holeshot/.agency-runtime/launchers/current-hermes.json
launcher_manifest_sha256: 3544cff1ebb441673aeefcb92cb101f4106995fea8bd564889ed61d5a9038592
native_stop_result: gateway not running; systemd retained process exit 1
native_restart_result: active; systemd Result success; unchanged plugin inventory
fresh_session_id: 20260825_065425_f0b77171
agency_run_id: 42b23dfd-f2ad-430f-b9e2-fc604f4defcd
agency_trace_id: 20260825_065425_f0b77171:20260825_065425_f0b77171:7948cbf5
first_response_artifact: /home/holeshot/.hermes-nexus/state.db messages projection, sequence 44; content SHA-256 243e806c6904fe3b3de95bbb417b0c3a9baccb041ba3feb5bd4671b4ac591873
native_transcript_redacted_artifact: /home/holeshot/.agency-runtime/evidence/ar119-hermes-status-MrOUoGJ4/native-transcript-redacted-index.json
native_transcript_redacted_artifact_sha256: 22e13b75173a8bfed4ace2decebf535e33fe7fdd068fb36e9e726ba75eb1954c
native_transcript_projection_sha256: 337443446718356544f8a593ecd1018640a9ea7f00ef4b6f4dbf6406938e4259
header_exact: |
  Agency/Agencies loaded: agency-steward
  Agency/Agencies delegated: none
  Skills loaded: hermes-agent
  Actual Model selected: observed execution receipt: [general] task-general -> task-general (host)
  Recruited via: deterministic
resident_binding_id: rmb-c5df89aa144e55adba09b6f1b684cf0b
resident_binding_scope: request_scoped / request; retained in runs.preflight_result
resident_manager_bindings_row: none expected for Hermes request-scoped contract
routing_decision_ids: [03143a75-a097-4644-b575-ffe8866feac5]
specialists_loaded_ids: []
skill_name_and_store_row_id: hermes-agent / 6a8cbe40-daef-4296-90a3-24b6038f96fd
provider_attempt_status: Agency workforce inference not attempted; deterministic control route
fallback_count: 0 applied; routing fallback flags false
telegram_delivery: exact response observed by operator
failed_native_attempt: one read-only config-existence command falsely blocked by Hermes gateway self-stop guard; not retried
internal_post_response_failure_run: efaba29e-ed22-48df-b204-a682ad200475
internal_post_response_failure_trace: 20260825_065425_f0b77171:8fba6441-67da-4a7b-a2eb-6b7a9e648b80:ecf4c5d1
internal_post_response_failure_receipt: 1919eeca-a951-4b32-9c5b-c65a8ee8545c
internal_post_response_failure: two planner contract-invalid rejections on linux-task-agency-router / litellm / exact task-agency-router; blank non-user message; no route/header/finalization/specialist/skill/worker/delegation; delivered user turn unaffected
before_store_backup_sha256: a0d558a330c94b341e7624d455fe0c7ef257bd992a5903c8592e7a3f5de4f188
before_store_integrity: ok
after_status_store_backup: /home/holeshot/.agency-runtime/evidence/ar119-hermes-status-MrOUoGJ4/agency-after-status.db
after_status_store_backup_sha256: d1ab6cfd6a2881f17aae17bc4e835f7df0971ec02bb328d20cb3df088ca51794
after_status_store_integrity: ok
contractor_count: 15 before / 15 after
known_limit: status proves control activation and skill delivery, not Agency workforce inference or provider actual model; current substantive and operational native-child checks remain
rule4_proven: false
matrix_cell_moved: false
protected_hosts: Codex OAuth/config/canary, Claude, and ZCode untouched
~~~
