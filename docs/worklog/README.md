---
title: Worklog
status: active
category: worklog
created: 2026-07-10
updated: 2026-08-29
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
| `5eb4de18` | 2026-07-08 | Add complexity tier to model header + fix post_api_request race condition | null | null |
| `cfc7d381` | 2026-07-08 | Fix dynamic model resolution: capture actual model from response, not SpendLogs | null | null |
| `886d6cfa` | 2026-07-08 | Fix: post_tool_call hook captures specialist loads, not just skills | null | null |
| `2434f309` | 2026-07-08 | Wire portable agency_runtime into live Hermes plugin (Step 2-3 cutover) | null | null |
| `3b39f582` | 2026-07-09 | config-first secrets, doctor auth, packaging hardening, portability fixes | null | null |
| `c2d1274b` | 2026-07-09 | fix: pre_llm_call always injects routing, pre_verify enforces specialist loading | null | null |
| `dc0be8d2` | 2026-07-09 | feat: multi-provider fallback chain with config-first auth | null | null |
| `a7bba3af` | 2026-07-09 | feat: one-command install, on/off toggle, comprehensive README | null | null |
| `8f6d3205` | 2026-07-09 | docs: add agency-runtime session handoff | null | null |
| `8b377b1c` | 2026-07-09 | feat: harden agency runtime delegation evidence | null | null |
| `442b91aa` | 2026-07-09 | chore: untrack generated code indexes | null | null |
| `3b24614c` | 2026-07-09 | feat: harden yolo roster sync and specialist preflight | null | null |
| `42f65803` | 2026-07-10 | feat: add routing explain receipts | null | null |
| `6dc35cd2` | 2026-07-10 | fix: repair mcp finalization tool | null | null |
| `bb0c12d8` | 2026-07-10 | fix: keep http finalize evidence on session id | null | null |
| `9e57cf1f` | 2026-07-10 | fix: sanitize http server error responses | null | null |
| `4f477f64` | 2026-07-10 | fix: preserve delegate type errors | null | null |
| `3954d35c` | 2026-07-10 | fix: bound cli delegation waits | null | null |
| `d9379f3c` | 2026-07-10 | feat: add json delegate results | null | null |
| `2235d7e0` | 2026-07-10 | fix: avoid shelling out for adapter availability | null | null |
| `901a8807` | 2026-07-10 | fix: lower trivial_msg_threshold to 8 + persist nontrivial via store | null | null |
| `be4f52f6` | 2026-07-10 | fix: trivial threshold, removed 'next'/'status' from trivial patterns, added DEFAULT orchestrators | null | null |
| `31443bc7` | 2026-07-10 | feat: bundle full 16-action companion policy, add agency policy CLI, surface companions in route | null | null |
| `badb1802` | 2026-07-10 | fix: DEFAULT companions load even for trivial messages (ping/ok/yes) | null | null |
| `63b75eec` | 2026-07-10 | Fix agency preflight host plugin wiring | null | null |
| `4d176686` | 2026-07-10 | docs: establish linked roadmap worklog and decision system | null | null |
| `a896c817` | 2026-07-10 | fix: isolate generated plugin tests from user home | null | null |
| `17a62dd5` | 2026-07-11 | feat: harden runtime and ship local operations dashboard | null | null |
| `d1275c37` | 2026-07-11 | feat: add optional dashboard service and config parity | null | null |
| `afdf8d1b` | 2026-07-11 | docs: sync AR-13 tracker mapping | null | null |
| `63ea805b` | 2026-07-11 | feat: turn dashboard into a live signal observatory | null | null |
| `2515bfc1` | 2026-07-12 | feat(runtime): complete cross-platform production hardening | null | null |
| `e4a846d6` | 2026-07-13 | feat(runtime): finish production hardening and release gates | null | null |
| `a60b41c4` | 2026-07-13 | fix(ci): preserve dependency audit without paid security | null | null |
| `852359d4` | 2026-07-13 | fix(ci): harden hosted cross-platform verification | null | null |
| `c7e06fd6` | 2026-07-13 | fix(ci): close final hosted portability gaps | null | null |
| `a096236c` | 2026-07-13 | fix(runtime): close hosted portability and overload gaps | null | null |
| `26fd65a2` | 2026-07-13 | fix(runtime): close final hosted Windows and ledger gaps | null | null |
| `11387ad6` | 2026-07-13 | test(ci): stabilize hosted Windows PowerShell gate | null | null |
| `d9f6d37b` | 2026-07-13 | fix(evidence): stabilize same-timestamp event order | null | null |
| `55157574` | 2026-07-14 | Merge pull request #18 from Holeshot-Software-LLC/codex/production-readiness-dashboard | null | null |
| `6756b87b` | 2026-07-14 | docs(roadmap): reconcile merged release state | null | null |
| `e5f4a8c2` | 2026-07-18 | feat(runtime): harden dynamic agency orchestration | null | null |
| `a022b5dc` | 2026-07-18 | fix(dashboard): validate installed control identity | null | null |
| `cbe9bc9b` | 2026-07-18 | fix(runtime): harden installed control transitions | null | null |
| `c8ebbfaf` | 2026-07-19 | test(runtime): cover defensive control branches | null | null |
| `3ded6a45` | 2026-07-19 | test(dashboard): cover delegation plan fallback | null | null |
| `164188bc` | 2026-07-19 | fix(roster): reconcile legacy bundled contracts | null | null |
| `664fcf18` | 2026-07-19 | test(ci): import Windows ctypes types portably | null | null |
| `11a2c861` | 2026-07-19 | fix(runtime): close ingestion and hosted portability gaps | null | null |
| `0df5050b` | 2026-07-19 | fix(ci): harden hosted runtime portability | null | null |
| `0c41fbdf` | 2026-07-19 | fix(ci): preserve durable hosted runtime authority | null | null |
| `89576f07` | 2026-07-19 | fix(windows): report protected root receipt failures | null | null |
| `07de83ca` | 2026-07-19 | fix(windows): accept protected canonical ACL receipts | null | null |
| `a1c67447` | 2026-07-19 | fix(windows): classify canonical ACL receipt failures | null | null |
| `31516d13` | 2026-07-19 | fix(windows): scope trusted bootstrap root ownership | null | null |
| `b05b180a` | 2026-07-19 | fix(windows): normalize hosted private root ownership | null | null |
| `361962f7` | 2026-07-19 | fix(windows): normalize private executable owner identity | null | null |
| `9400f760` | 2026-07-19 | fix(codex): report all installed hook events | null | null |
| `3f9eb967` | 2026-07-19 | fix(dashboard): redact failed manager probe output | null | null |
| `22434e81` | 2026-07-19 | fix(mcp): validate injected Store identities | null | null |
| `fdaad175` | 2026-07-19 | docs: reconcile runtime identity and routing contracts | null | null |
| `987c32ae` | 2026-07-19 | fix(portability): close Windows ingestion and CI gaps | null | null |
| `be4b3fff` | 2026-07-19 | Merge pull request #104 from Holeshot-Software-LLC/codex/turn-scoped-agency-lifecycle | null | null |
| `46f203aa` | 2026-07-20 | fix(release): build artifacts from canonical Git blobs | null | null |
| `bb8ce932` | 2026-07-20 | fix(portability): harden hosted release proofs | null | null |
| `9f98db3b` | 2026-07-20 | fix(release): canonicalize generated metadata | null | null |
| `3515d4e1` | 2026-07-20 | fix(release): verify backend manifest order | null | null |
| `98430255` | 2026-07-20 | test(portability): make process fixtures race-free | null | null |
| `4dccae79` | 2026-07-20 | fix(preflight): preserve lease safety margin | null | null |
| `e6e1b258` | 2026-07-20 | Merge pull request #111 from Holeshot-Software-LLC/codex/canonical-release-source | null | null |
| `0f374b41` | 2026-07-20 | fix(dashboard): preserve WSL systemd config trust | null | null |
| `615d88c8` | 2026-07-20 | fix(canary): bind isolated runs to global mode | null | null |
| `f5fe9724` | 2026-07-20 | fix(canary): bind hook control capability | null | null |
| `b8f80bd5` | 2026-07-20 | fix(hooks): bind authoritative master control | null | null |
| `cb17e0d0` | 2026-07-20 | test(portability): normalize hook control contracts | null | null |
| `123910a4` | 2026-07-20 | test(coverage): exercise hook control rejection paths | null | null |
| `edb922c9` | 2026-07-20 | docs(roadmap): complete isolated canary control | null | null |
| `a869e511` | 2026-07-20 | Merge pull request #114 from Holeshot-Software-LLC/codex/wsl-private-tmp-namespace | null | null |
| `55c4dfec` | 2026-07-20 | docs(roadmap): close merged readiness gates | null | null |
| `4635a0bd` | 2026-07-20 | docs: rewrite README for public users | null | null |
| `de875f6b` | 2026-07-20 | docs(roadmap): track public README rewrite | null | null |
| `280b0b72` | 2026-07-20 | Merge pull request #116 from Holeshot-Software-LLC/codex/pr114-merge-ledger | null | null |
| `9d4e55b8` | 2026-07-20 | fix(ci): isolate wall-clock performance gates | null | null |
| `c9948828` | 2026-07-20 | docs(roadmap): complete performance gate isolation | null | null |
| `a7510462` | 2026-07-20 | Merge pull request #121 from Holeshot-Software-LLC/codex/performance-gate-isolation | null | null |
| `58026a57` | 2026-07-20 | fix(installer): require verified Codex hook activation | null | null |
| `527659d1` | 2026-07-20 | Merge pull request #124 from Holeshot-Software-LLC/codex/ar-114-guided-codex-activation | null | null |
| `7e243232` | 2026-07-21 | fix(installer): identify Codex terminal hook review | null | null |
| `5d2bafb9` | 2026-07-21 | Merge pull request #125 from Holeshot-Software-LLC/codex/ar-114-codex-tui-hook-trust | null | null |
| `5467026f` | 2026-07-21 | docs(roadmap): record verified Codex hook activation | null | null |
| `0d892e8c` | 2026-07-21 | Merge pull request #126 from Holeshot-Software-LLC/codex/ar-114-activation-proof | null | null |
| `673988dc` | 2026-07-21 | feat(routing): bound native child inference and expose account models | null | null |
| `49e8f996` | 2026-07-21 | fix(routing): bound child inference and parallelize CI | null | null |
| `e0870fa0` | 2026-07-21 | test(coverage): cover model cache waiter reuse | null | null |
| `1b28e89d` | 2026-07-21 | test(delegation): allow concurrent unit completion order | null | null |
| `e2cb50dd` | 2026-07-21 | test(routing): cover child coalescing timeout | null | null |
| `6f97dcc0` | 2026-07-21 | ci: defer full compatibility matrix to main | null | null |
| `aefeb288` | 2026-07-21 | ci: validate PR ledgers at canonical head | null | null |
| `afd7199b` | 2026-07-21 | style(ci): format workflow contract assertion | null | null |
| `795deefe` | 2026-07-21 | fix(routing): enforce safe selection and child evidence | null | null |
| `0b21bdb1` | 2026-07-21 | test(routing): cover recovery edge paths | null | null |
| `78afe967` | 2026-07-21 | fix(routing): preserve current child and provider evidence | null | null |
| `2c404f45` | 2026-07-21 | fix(routing): validate policy before host filtering | null | null |
| `4f20f005` | 2026-07-21 | fix(routing): publish validated child assignment bundles | null | null |
| `71faeef4` | 2026-07-21 | fix(dashboard): preserve provider protocol coverage | null | null |
| `4e0b0a71` | 2026-07-21 | docs(roadmap): define inference-first workforce delivery | null | null |
| `71405fad` | 2026-07-21 | feat(workforce): establish governed staffing foundation | null | null |
| `743a9827` | 2026-07-22 | feat(workforce): build inference-first routing foundation | null | null |
| `ca893fed` | 2026-07-22 | feat(eval): add matched upstream selection benchmark | null | null |
| `9d415bbd` | 2026-07-23 | feat(workforce): harden matched selection semantics | null | null |
| `86fba477` | 2026-07-23 | fix(workforce): harden matched corpus normalization | null | null |
| `8af4cf09` | 2026-07-23 | docs(roadmap): record matched corpus variance | null | null |
| `e697f231` | 2026-07-23 | docs(roadmap): record matched selection stability | null | null |
| `85afc03f` | 2026-07-23 | docs(roadmap): record matched selection reruns | null | null |
| `a27f3406` | 2026-07-23 | docs(roadmap): record complete matched selection rerun | null | null |
| `9c6c1ae1` | 2026-07-23 | docs(roadmap): record matched selection variance | null | null |
| `4cc59ba3` | 2026-07-23 | docs(roadmap): record matched selection confirmations | null | null |
| `a7787486` | 2026-07-23 | docs(roadmap): record matched selection recovery | null | null |
| `d6923797` | 2026-07-23 | docs(roadmap): record matched selection recovery evidence | null | null |
| `ef24960a` | 2026-07-23 | docs(roadmap): record matched selection recovery evidence | null | null |
| `2f2cfbb3` | 2026-07-23 | docs(roadmap): record matched selection recovery evidence | null | null |
| `c1582109` | 2026-07-23 | docs(roadmap): record matched selection recovery evidence | null | null |
| `71f77755` | 2026-07-23 | docs(roadmap): record matched selection recovery evidence | null | null |
| `4687a7bf` | 2026-07-23 | docs(roadmap): record matched selection recovery evidence | null | null |
| `47ff115d` | 2026-07-23 | docs(roadmap): record broad selection recovery evidence | null | null |
| `8a0e75d9` | 2026-07-23 | docs(roadmap): record matched selection confidence recovery | null | null |
| `1c91945d` | 2026-07-23 | docs(roadmap): record 19-case Agency selection pass | null | null |
| `978e02ce` | 2026-07-23 | docs(roadmap): record matched incident selection variance | null | null |
| `a5844dc1` | 2026-07-23 | docs(roadmap): record repeated matched incident variance | null | null |
| `c1efcafe` | 2026-07-23 | docs(roadmap): record instrumented incident recovery and corpus variance | null | null |
| `355c05a7` | 2026-07-23 | docs(governance): bound autonomous context handoffs | null | null |
| `1d3059dc` | 2026-07-23 | docs(roadmap): record installed-release plan-shape variance | null | null |
| `a6007afc` | 2026-07-23 | docs(roadmap): record installed-release instrumented recovery | null | null |
| `b927266f` | 2026-07-23 | fix(governance): enforce persistent goal context continuity | null | null |
| `4a19e230` | 2026-07-23 | fix(governance): keep context checkpoints in-task | null | null |
| `06d12cf6` | 2026-07-23 | docs(roadmap): record complete-corpus confidence variance | null | null |
| `be1ec78c` | 2026-07-23 | docs(roadmap): prepare confidence-abstention capture | null | null |
| `3d0ee636` | 2026-07-23 | fix(governance): remove live context admission gate | null | null |
| `fc9c453b` | 2026-07-23 | docs(roadmap): record confidence-abstention recovery | null | null |
| `90179d8b` | 2026-07-23 | docs(roadmap): record further matched corpus variance | null | null |
| `b8c1eca4` | 2026-07-23 | docs(roadmap): record bounded selection recovery | null | null |
| `89180406` | 2026-07-23 | docs(roadmap): record matched latency recovery | null | null |
| `6049510e` | 2026-07-23 | docs(roadmap): record four-case selection variance | null | null |
| `48e30228` | 2026-07-23 | docs(roadmap): record four-case selection recovery | null | null |
| `0dfe777e` | 2026-07-23 | docs(roadmap): record second 19-case Agency pass | null | null |
| `518d2272` | 2026-07-23 | docs(roadmap): record post-pass corpus variance | null | null |
| `4f850c7e` | 2026-07-23 | docs(governance): complete context checkpoint tracking | null | null |
| `effa10b7` | 2026-07-23 | Merge pull request #129 from Holeshot-Software-LLC/codex/ar-115-live-routing-trust | null | null |
| `7e8609d9` | 2026-07-24 | feat(workforce): inference-first specialist selection (ADR-0087) + green main recovery (#140) | null | null |
| `c6bc9539` | 2026-07-24 | feat: ZCode 5th host + Codex/Claude child-routing plumbing + AR-120..125 acceptance evidence (#141) | null | null |
| `4f69eeb7` | 2026-07-25 | docs(readme): cleaner hub-and-spoke logo + intent-aware sample teams (#142) | null | null |
| `67c88a10` | 2026-07-25 | fix(workforce): enrich security specialists with threat-modeling/audit/risk-analysis capabilities (#143) | null | null |
| `f61a8c2a` | 2026-07-25 | fix(bootstrap): restore venv site-packages under -I -S so ZCode hooks actually fire (#144) | null | null |
| `e8b0ba3a` | 2026-07-25 | fix(installer): ZCode hooks use type 'process' (shell-free) not 'command' (#145) | null | null |
| `d9ce781a` | 2026-07-25 | fix(zcode): Stop rejections emit decision:block on every path (AR-127) (#150) | null | null |
| `184be93f` | 2026-07-25 | fix(security): withhold bearer token from non-TTY stdout; suppress runtime-control error detail (SEC-01, L2-05) (#146) | null | null |
| `a1c4c476` | 2026-07-25 | perf(hot-path): build route request once per turn; cache storage trust verdict (PERF-01, PERF-02) (#147) | null | null |
| `ffd51d0a` | 2026-07-25 | chore: remove 8 dead-code items with test ports (audit wave 3) (#148) | null | null |
| `e1ece24f` | 2026-07-25 | fix(hardening): isolate bad host records; fail-closed MCP maxLength; broker allowlist tests; git-refusal clarity (audit wave 4) (#149) | null | null |
| `5001d787` | 2026-07-25 | docs(ar-127): backfill tracker issue #151, mark done, reconcile worklog ledger (#152) | null | null |
| `c5e3575b` | 2026-07-25 | docs(roadmap): checkpoint production-readiness audit bootstrap | null | null |
| `a32e4e6a` | 2026-07-25 | docs(roadmap): govern production-readiness audit backlog | null | null |
| `24948a0e` | 2026-07-26 | fix(runtime): harden production readiness wave one | null | null |
| `c741b240` | 2026-07-26 | fix(runtime): complete production readiness hardening wave two | null | null |
| `0b9849c9` | 2026-07-26 | fix(runtime): repair integrated production regressions | null | null |
| `ad0a1bae` | 2026-07-26 | test(cli): align wizard fixture with zcode | null | null |
| `bcba556c` | 2026-07-26 | docs(roadmap): record complete python gate | null | null |
| `567bd231` | 2026-07-26 | test(dashboard): restore ui release coverage | null | null |
| `c3ffe6a7` | 2026-07-26 | fix(release): restore coverage contracts and cursor paging | null | null |
| `63cf7967` | 2026-07-26 | fix(security): parse complete Windows ACL descriptors | null | null |
| `0c0299a4` | 2026-07-26 | perf(runtime): reduce stable routing startup work | null | null |
| `09324103` | 2026-07-26 | fix(store): enforce exact schema authority contracts | null | null |
| `3f80af70` | 2026-07-26 | docs(roadmap): checkpoint deep production review | null | null |
| `a1efe31a` | 2026-07-26 | refactor(workforce): remove dead private inference paths | null | null |
| `eec52071` | 2026-07-26 | perf(selector): preserve 10k routing headroom | null | null |
| `2437068e` | 2026-07-26 | docs(roadmap): govern final traceability defects | null | null |
| `4620204d` | 2026-07-26 | docs(security): reconcile fail-closed release contract | null | null |
| `e62230c9` | 2026-07-26 | docs(roadmap): govern bounded hiring evidence | null | null |
| `6a3bdaa0` | 2026-07-26 | fix(dashboard): seal traced response contracts | null | null |
| `babc45a9` | 2026-07-26 | docs(roadmap): govern cost-bounded verification | null | null |
| `92adf2fb` | 2026-07-26 | perf(dashboard): restore durable asset headroom | null | null |
| `8236a169` | 2026-07-26 | perf(workforce): batch packaged contractor lookup | null | null |
| `fbbc5127` | 2026-07-26 | ci: restore cost-bounded pull request cadence | null | null |
| `90ce2724` | 2026-07-26 | docs(audit): reconcile production evidence | null | null |
| `c5d56314` | 2026-07-26 | feat(testing): add secure parallel change loop | null | null |
| `d2ab19b2` | 2026-07-26 | fix(testing): harden parallel loop self-hosting | null | null |
| `7d113135` | 2026-07-26 | fix(testing): bound Windows self-host paths | null | null |
| `74468aa6` | 2026-07-26 | docs(roadmap): record parallel evidence and HTTP gap | null | null |
| `12640d06` | 2026-07-26 | fix(http): stop after client disconnects | null | null |
| `49aafe1a` | 2026-07-26 | test(change-loop): use bounded runtime homes | null | null |
| `900f8d33` | 2026-07-26 | docs(security): correct presence and timing evidence | null | null |
| `58aee8b5` | 2026-07-26 | perf(testing): measure and trim the Windows tail | null | null |
| `62d90ca6` | 2026-07-26 | fix(testing): isolate timing plugin self-test | null | null |
| `11241e61` | 2026-07-26 | perf(testing): bind measured Windows sharding | null | null |
| `aad29018` | 2026-07-26 | test(observability): disambiguate surface evidence | null | null |
| `85549a4d` | 2026-07-26 | perf(testing): add measured Windows shard profile | null | null |
| `10eb595a` | 2026-07-27 | perf(testing): enforce measured shard defaults | null | null |
| `dca7af56` | 2026-07-27 | ci: gate expensive fanout behind quality | null | null |
| `e3284bf8` | 2026-07-27 | perf(testing): expose and reduce fixture cost | null | null |
| `f64ba1e5` | 2026-07-27 | feat(production): close native and workflow trust gaps | null | null |
| `0fd79e07` | 2026-07-27 | docs(roadmap): checkpoint native trust package | null | null |
| `c844498d` | 2026-07-27 | fix(release): normalize Windows executable source modes | null | null |
| `1ecc4e5b` | 2026-07-27 | fix(release): seal Windows executable handles | null | null |
| `c067c6aa` | 2026-07-27 | fix(release): canonicalize reviewed Windows PE mode | null | null |
| `1ad1cbcf` | 2026-07-27 | fix(release): rebuild canonical sdist source manifest | null | null |
| `2f801181` | 2026-07-27 | fix(release): exclude native PE from portable wheel | null | null |
| `3e14f740` | 2026-07-27 | fix(production): close final traceability and CI gaps | null | null |
| `637900db` | 2026-07-27 | docs(checkpoint): seal final layered review package | null | null |
| `b520fa76` | 2026-07-27 | fix(testing): align hardened full-gate contracts | null | null |
| `e0dca709` | 2026-07-27 | docs(checkpoint): seal full-gate contract repair | null | null |
| `60543e16` | 2026-07-27 | ci: run exhaustive Python verification on demand | null | null |
| `6cb8406c` | 2026-07-27 | docs(evaluation): defer one-shot applications post-production | null | null |
| `c2ebfc67` | 2026-07-27 | fix(routing): fail regulated assurance gaps closed | null | null |
| `99b51bdc` | 2026-07-27 | docs(production): record fresh artifact and live evidence | null | null |
| `4dd1aa05` | 2026-07-27 | docs(checkpoint): seal fresh live readiness evidence | null | null |
| `52150e35` | 2026-07-27 | docs(production): bind artifact evidence to revision | null | null |
| `e0bbe70f` | 2026-07-27 | docs(production): record cross-platform candidate evidence | null | null |
| `dfe6f46e` | 2026-07-27 | docs(production): record failed Codex activation proof | null | null |
| `30d5fc0b` | 2026-07-27 | feat(install): add attended Codex refresh transaction | null | null |
| `85428e63` | 2026-07-27 | docs(production): record attended Codex refresh proof | null | null |
| `cb06c73c` | 2026-07-27 | docs(production): record Codex activation canary gap | null | null |
| `77ec4f62` | 2026-07-27 | feat(canary): prove exact Codex child activation | null | null |
| `54d82a99` | 2026-07-27 | docs(production): record exact Codex activation recheck | null | null |
| `9aa317cd` | 2026-07-27 | fix(dashboard): collapse mobile header flex basis | null | null |
| `630db7b5` | 2026-07-27 | docs(production): record responsive dashboard live QA | null | null |
| `c625bc76` | 2026-07-27 | perf(smoke): reuse one attested launcher | null | null |
| `1676f6a0` | 2026-07-27 | perf(testing): cache immutable workforce evidence | null | null |
| `b95d78a4` | 2026-07-27 | docs(roadmap): close locally accepted audit items | null | null |
| `283e3f9c` | 2026-07-27 | docs(checkpoint): seal final-candidate preparation | null | null |
| `bba2b436` | 2026-07-27 | refactor(security): consolidate runtime authority helpers | null | null |
| `4e39d4c1` | 2026-07-27 | fix(codex): bind hook trust inventory | null | null |
| `d07f4d86` | 2026-07-27 | fix(release): normalize private POSIX wheel modes | null | null |
| `828f747b` | 2026-07-27 | fix(release): normalize private POSIX sdist modes | null | null |
| `6bbf29b4` | 2026-07-27 | docs(checkpoint): refresh AR-119 recovery capsule | null | null |
| `bc6589b0` | 2026-07-27 | fix(codex): bind activation verification to fresh proof | null | null |
| `110dfd11` | 2026-07-27 | docs(governance): bound delivery to live demo checkpoints | null | null |
| `63a1f5f2` | 2026-07-27 | fix(installer): isolate native host lifecycle cwd | null | null |
| `640b6c52` | 2026-07-27 | docs(checkpoint): record exact Codex operator gate | null | null |
| `23dd496a` | 2026-07-27 | fix(canary): request exact Codex child activation | null | null |
| `5d390424` | 2026-07-27 | fix(canary): preserve one-unit Codex delegation | null | null |
| `9c7a3d3c` | 2026-07-27 | fix(canary): isolate activation from planner fanout | null | null |
| `8f4c3b75` | 2026-07-27 | docs(production): record current Codex hook trust proof | null | null |
| `8fdc186f` | 2026-07-27 | fix(canary): persist Codex activation proof | null | null |
| `55a03e13` | 2026-07-27 | docs(production): record packaged Codex canary candidate | null | null |
| `29fd9a9b` | 2026-07-27 | docs(production): record isolated Codex canary boundary | null | null |
| `e21eab35` | 2026-07-28 | feat(updates): add immutable attended upgrade discovery | null | null |
| `7d6558a1` | 2026-07-28 | feat(installer): add attended owned host uninstall | null | null |
| `1011a89c` | 2026-07-28 | docs(demo): record live uninstall preview | null | null |
| `8c7d8df4` | 2026-07-28 | fix(updates): bind attended installers to owning environment | null | null |
| `380f8992` | 2026-07-28 | fix(codex): bind V2 hooks to native child evidence | null | null |
| `d6611caa` | 2026-07-28 | fix(codex): fail fast on stale hook trust | null | null |
| `9e86898e` | 2026-07-28 | fix(windows): preserve owner control and service runtimes | null | null |
| `42da9907` | 2026-07-28 | fix(codex): separate activation child goal | null | null |
| `81365108` | 2026-07-28 | docs(architecture): retire Agency Windows Hello | null | null |
| `f5ca1729` | 2026-07-28 | feat(installer): install applicable suite by default | null | null |
| `da012abc` | 2026-07-28 | docs(checkpoint): record full-suite installer verification | null | null |
| `6fc31739` | 2026-07-28 | Merge pull request #157 from Holeshot-Software-LLC/codex/full-suite-install | null | null |
| `02f4cfb5` | 2026-07-28 | docs(routing): record Codex workforce evidence regression | null | null |
| `518ad620` | 2026-07-28 | fix(routing): restore atomic Codex workforce evidence | null | null |
| `2c914b75` | 2026-07-28 | Merge pull request #158 from Holeshot-Software-LLC/codex/ar-199-restore-codex-workforce | null | null |
| `e6865843` | 2026-07-28 | fix(codex): preserve encrypted child activation input | null | null |
| `3382b18e` | 2026-07-28 | Merge pull request #159 from Holeshot-Software-LLC/codex/ar-199-restore-codex-workforce | null | null |
| `ea73dd50` | 2026-07-29 | fix(codex): preserve exact child context framing | null | null |
| `f2f901d9` | 2026-07-29 | Merge pull request #160 from Holeshot-Software-LLC/codex/ar-199-restore-codex-workforce | null | null |
| `a05549ff` | 2026-07-29 | fix(routing): bind hired specialists to live gaps | null | null |
| `279ef9e3` | 2026-07-29 | Merge pull request #162 from Holeshot-Software-LLC/codex/ar-199-live-selection-followup | null | null |
| `0d8cce1e` | 2026-07-29 | fix(codex): complete isolated activation canary | null | null |
| `2e6a1448` | 2026-07-29 | Merge pull request #163 from Holeshot-Software-LLC/codex/ar-199-isolated-canary-route | null | null |
| `01150cdd` | 2026-07-29 | fix(codex): accept documented spawn nickname | null | null |
| `34e3180e` | 2026-07-29 | Merge pull request #164 from Holeshot-Software-LLC/codex/ar-199-codex-spawn-nickname | null | null |
| `f28b98a8` | 2026-07-29 | fix(codex): consume activation before child delivery | null | null |
| `3cea397e` | 2026-07-29 | fix(codex): accept isolated trust bypass notice | null | null |
| `ef41cff4` | 2026-07-29 | fix(codex): reconcile consumed child callback | null | null |
| `e41df933` | 2026-07-29 | fix(codex): reconcile missing post-tool identity | null | null |
| `cc4ab2fb` | 2026-07-29 | fix(codex): resolve post-tool unit from output | null | null |
| `f03fcfa9` | 2026-07-29 | chore(codex): expose canary reconcile rejection | null | null |
| `c256571a` | 2026-07-29 | docs(roadmap): mark Codex diagnostic checkpoint | null | null |
| `b276fcaf` | 2026-07-29 | fix(codex): persist canary reconcile rejection | null | null |
| `2e5eb452` | 2026-07-29 | fix(codex): promote real child activation lineage | null | null |
| `c74c389f` | 2026-07-29 | fix(codex): finalize successful native child | null | null |
| `237bf8a6` | 2026-07-29 | fix(codex): retain finalization mismatch evidence | null | null |
| `591879a2` | 2026-07-29 | fix(codex): restore Stop correction continuation | null | null |
| `f09bc04a` | 2026-07-29 | fix(codex): accept one correction in canary proof | null | null |
| `0521c8d5` | 2026-07-29 | docs(roadmap): record accepted Codex source canary | null | null |
| `46f03b2d` | 2026-07-29 | docs(roadmap): record AR-199 fast verification | null | null |
| `816db5b2` | 2026-07-29 | Merge pull request #165 from Holeshot-Software-LLC/codex/ar-199-subagent-start-consumption | null | null |
| `422bf32c` | 2026-07-29 | docs(roadmap): record installed Codex proof | null | null |
| `6ce4391b` | 2026-07-29 | Merge pull request #166 from Holeshot-Software-LLC/codex/ar-199-installed-proof | null | null |
| `f9cbca20` | 2026-07-29 | fix(codex): pin resident managers in first header | null | null |
| `8a96818c` | 2026-07-29 | docs(roadmap): record first-header fast spine | null | null |
| `5a19586a` | 2026-07-29 | Merge pull request #167 from Holeshot-Software-LLC/codex/ar-199-deterministic-manager-header | null | null |
| `210538f2` | 2026-07-29 | fix(header): derive seven-line correction count | null | null |
| `6910edab` | 2026-07-29 | docs(roadmap): record seven-field fast spine | null | null |
| `85069f3b` | 2026-07-29 | Merge pull request #168 from Holeshot-Software-LLC/codex/ar-199-seven-field-header | null | null |
| `a23f42ab` | 2026-07-29 | fix(codex): require zero-correction canary header | null | null |
| `aa0d9497` | 2026-07-29 | Merge pull request #169 from Holeshot-Software-LLC/codex/ar-199-zero-correction-canary | null | null |
| `26aaecf9` | 2026-07-29 | docs(roadmap): record zero-correction installed proof | null | null |
| `511c3894` | 2026-07-29 | docs(roadmap): record ordinary route boundary | null | null |
| `48516b40` | 2026-07-29 | Merge pull request #170 from Holeshot-Software-LLC/codex/ar-199-zero-correction-canary | null | null |
| `196dedc4` | 2026-07-29 | fix(workforce): restore ordinary software team anchors | null | null |
| `2ee03065` | 2026-07-29 | docs(roadmap): record ordinary software team proof | null | null |
| `c02a10af` | 2026-07-29 | fix(evidence): report workforce eligibility counts | null | null |
| `0d6b0117` | 2026-07-29 | docs(roadmap): record truthful eligibility proof | null | null |
| `a465f382` | 2026-07-29 | docs(roadmap): record ordinary repair verification | null | null |
| `fbed63ab` | 2026-07-29 | Merge pull request #171 from Holeshot-Software-LLC/codex/ar-199-ordinary-continuation | null | null |
| `57c48291` | 2026-07-29 | docs(roadmap): record exact installed canary proof | null | null |
| `b8c0a8d6` | 2026-07-29 | fix(workforce): bind software architecture units | null | null |
| `bef8eaa1` | 2026-07-29 | docs(roadmap): record architecture selection blocker | null | null |
| `4513b3a6` | 2026-07-29 | docs(roadmap): record architecture repair verification | null | null |
| `6ca745d0` | 2026-07-29 | refactor(workforce): keep architecture recall contract-driven | null | null |
| `882b9203` | 2026-07-29 | fix(workforce): keep online selection inference-owned | null | null |
| `78d6c219` | 2026-07-29 | docs(roadmap): record inference-only selection repair | null | null |
| `e167964d` | 2026-07-29 | docs(roadmap): record inference repair fast gate | null | null |
| `9b509932` | 2026-07-29 | Merge pull request #172 from Holeshot-Software-LLC/codex/ar-199-fbed-canary | null | null |
| `96d25e0f` | 2026-07-29 | docs(roadmap): record exact inference repair install | null | null |
| `68263f43` | 2026-07-29 | fix(workforce): repair ordinary staffing failure edges | null | null |
| `4b422896` | 2026-07-29 | Merge pull request #173 from Holeshot-Software-LLC/codex/ar-199-fbed-canary | null | null |
| `51d9b6f6` | 2026-07-29 | docs(roadmap): record ordinary staffing repair install | null | null |
| `05ec457b` | 2026-07-29 | docs(roadmap): record terminal ordinary product proof | null | null |
| `22db114f` | 2026-07-29 | Merge pull request #174 from Holeshot-Software-LLC/codex/ar-199-fbed-canary | null | null |
| `687078e7` | 2026-07-29 | fix(workforce): make decisions diagnosable and mutation-conformant | null | null |
| `52d56353` | 2026-07-29 | Merge pull request #176 from Holeshot-Software-LLC/codex/ar-200-decision-conformance | null | null |
| `7b09eb68` | 2026-07-29 | docs(roadmap): checkpoint AR-200 merge and install | null | null |
| `99db59c5` | 2026-07-29 | fix(workforce): bind and bound inferred amendments | null | null |
| `8bb504ce` | 2026-07-29 | Merge pull request #177 from Holeshot-Software-LLC/codex/ar-200-live-evidence | null | null |
| `e1a2f2d2` | 2026-07-29 | docs(roadmap): record amendment repair install | null | null |
| `fcc68122` | 2026-07-30 | docs(roadmap): record terminal AR-200 canary | null | null |
| `f02b1af6` | 2026-07-30 | Merge pull request #178 from Holeshot-Software-LLC/codex/ar-200-final-evidence | null | null |
| `f98fc0b3` | 2026-07-30 | fix(workforce): preserve explicit inference gap decisions | null | null |
| `57c34e60` | 2026-07-30 | Merge pull request #179 from Holeshot-Software-LLC/agent/ar-200-selection-hiring-proof | null | null |
| `c604c476` | 2026-07-30 | fix(workforce): fund the default inference repair | null | null |
| `d942b24d` | 2026-07-30 | docs(roadmap): record AR-201 fast verification | null | null |
| `ed4450e9` | 2026-07-30 | Merge pull request #181 from Holeshot-Software-LLC/agent/ar-201-default-repair-budget | null | null |
| `097ce06e` | 2026-07-30 | docs(roadmap): checkpoint AR-201 terminal trial | null | null |
| `9f3d72a7` | 2026-07-30 | fix(runtime): converge recruiter and product proof | null | null |
| `d6b131a5` | 2026-07-30 | docs(roadmap): record AR-202 and AR-203 fast gate | null | null |
| `dbd55028` | 2026-07-30 | Merge pull request #184 from Holeshot-Software-LLC/agent/ar-202-recruiter-repair-convergence | null | null |
| `baaf603f` | 2026-07-30 | docs(roadmap): record final AR-203 canary | null | null |
| `ee7adea6` | 2026-07-30 | Merge pull request #185 from Holeshot-Software-LLC/agent/ar-202-recruiter-repair-convergence | null | null |
| `4314b8f6` | 2026-07-30 | fix(runtime): restore product hook activation boundary | null | null |
| `e3d2aeab` | 2026-07-30 | fix(evidence): harden hook stage diagnostics | null | null |
| `0c41a53f` | 2026-07-30 | docs(roadmap): record AR-203 fast verification | null | null |
| `830b8788` | 2026-07-30 | Merge pull request #186 from Holeshot-Software-LLC/agent/ar-203-hook-start-workspace | null | null |
| `e38f69d6` | 2026-07-30 | docs(roadmap): checkpoint README story activation boundary | null | null |
| `1e54967e` | 2026-07-30 | docs(roadmap): checkpoint README story recruiter failure | null | null |
| `d4709938` | 2026-07-30 | fix(workforce): make recruiter repair partial and traceable | null | null |
| `26a3911e` | 2026-07-30 | Merge pull request #187 from Holeshot-Software-LLC/agent/ar-203-readme-story-proof | null | null |
| `b45bd28f` | 2026-07-30 | fix(workforce): bind recruiter repair evidence | null | null |
| `c8bed05e` | 2026-07-30 | docs(roadmap): checkpoint PR 187 review repair | null | null |
| `5e3fab62` | 2026-07-30 | Merge pull request #188 from Holeshot-Software-LLC/agent/ar-203-readme-story-live-proof | null | null |
| `9ec3c3d0` | 2026-07-30 | docs(roadmap): checkpoint PR 188 install boundary | null | null |
| `c387b650` | 2026-07-30 | docs(product): lock the executable README story | null | null |
| `1d7b019b` | 2026-07-30 | docs(roadmap): checkpoint AR-204 contract | null | null |
| `ffec1027` | 2026-07-30 | fix(authority): restore owner control dispatch | null | null |
| `9212e525` | 2026-07-30 | docs(roadmap): checkpoint owner authority | null | null |
| `c8c8020e` | 2026-07-30 | fix(dashboard): restore owner control parity | null | null |
| `f8607dd3` | 2026-07-30 | docs(roadmap): checkpoint dashboard owner parity | null | null |
| `e1451ea9` | 2026-07-30 | fix(routing): require inference-owned staffing | null | null |
| `76210961` | 2026-07-30 | docs(roadmap): checkpoint inference-owned staffing | null | null |
| `03dba753` | 2026-07-30 | fix(activation): bind autonomous proof to inferred replay | null | null |
| `e0c66f9f` | 2026-07-30 | docs(roadmap): checkpoint autonomous activation replay | null | null |
| `3ec69c7f` | 2026-07-30 | fix(finalization): require first-pass evidence headers | null | null |
| `6956edb8` | 2026-07-30 | docs(evidence): record AR-204 mutation gate | null | null |
| `67f0b96f` | 2026-07-30 | docs(evidence): prove dashboard configuration round trip | null | null |
| `9e3ca7fc` | 2026-07-30 | fix(routing): preserve inference authority through evaluation | null | null |
| `0b372706` | 2026-07-30 | docs(evidence): record AR-204 38-mutation gate | null | null |
| `57f82c7f` | 2026-07-31 | feat(workforce): require an exact specialist for every task | null | null |
| `38d3e0aa` | 2026-07-31 | docs(evidence): checkpoint AR-205 specialist boundary | null | null |
| `35e1db58` | 2026-07-31 | test(preflight): preserve fingerprint retry under specialist gate | null | null |
| `1591cb84` | 2026-07-31 | docs(evidence): admit AR-205 local verification | null | null |
| `cc322381` | 2026-07-31 | Merge pull request #191 from Holeshot-Software-LLC/codex/ar-203-readme-story-final-proof | null | null |
| `38e7e1c7` | 2026-07-31 | fix(workforce): align inferred plans with safety policy | null | null |
| `a5b0c332` | 2026-07-31 | docs(evidence): record inferred staffing conformance | null | null |
| `0ecf1d9e` | 2026-07-31 | fix(workforce): close inferred plan review gaps | null | null |
| `81b887f5` | 2026-07-31 | fix(workforce): close final review safety gaps | null | null |
| `662faba7` | 2026-07-31 | docs(evidence): record final PR 192 verification | null | null |
| `94610994` | 2026-07-31 | Merge pull request #192 from Holeshot-Software-LLC/codex/ar-203-product-planner-repair | null | null |
| `271e5a01` | 2026-07-31 | fix(activation): bind indivisible review canary plan | null | null |
| `4460e100` | 2026-07-31 | docs(roadmap): checkpoint activation planner repair | null | null |
| `f0fde9ee` | 2026-07-31 | Merge pull request #193 from Holeshot-Software-LLC/codex/ar-203-activation-planning-contract | null | null |
| `40560aa6` | 2026-07-31 | docs(roadmap): checkpoint product hiring suppression | null | null |
| `f349c21c` | 2026-07-31 | fix(preflight): separate product hiring and compact unit goals | null | null |
| `28a5f122` | 2026-07-31 | docs(roadmap): checkpoint repeated context ceiling | null | null |
| `8b8c7800` | 2026-07-31 | fix(evidence): accept bounded ready routing receipts | null | null |
| `7b6e9219` | 2026-07-31 | docs(roadmap): checkpoint ready receipt verifier | null | null |
| `839ddee4` | 2026-07-31 | fix(preflight): admit complete persistent-host teams | null | null |
| `6efd9281` | 2026-07-31 | docs(roadmap): checkpoint approved persistent context | null | null |
| `81711c70` | 2026-07-31 | docs(evidence): admit persistent context fast gate | null | null |
| `6fdb26cb` | 2026-07-31 | docs(roadmap): bind proof checkpoint to PR branch | null | null |
| `b9d9ec4d` | 2026-07-31 | fix(preflight): bound encoded context and legacy replay | null | null |
| `9683a892` | 2026-07-31 | docs(evidence): admit encoded context fast gate | null | null |
| `7727c0cd` | 2026-07-31 | fix(hooks): bound final Codex header metadata | null | null |
| `581891c1` | 2026-07-31 | docs(evidence): admit final Codex header fast gate | null | null |
| `6b49f17d` | 2026-07-31 | Merge pull request #195 from Holeshot-Software-LLC/codex/ar-204-readme-product-proof | null | null |
| `dd3ca769` | 2026-07-31 | docs(roadmap): checkpoint AR-207 product execution failure | null | null |
| `6e2b3f46` | 2026-07-31 | fix(product): prove exact multi-unit specialist execution | null | null |
| `3b5a00f7` | 2026-07-31 | Merge pull request #197 from Holeshot-Software-LLC/codex/ar-204-readme-product-proof | null | null |
| `fb797f9e` | 2026-07-31 | fix(codex): classify non-critical host notices | null | null |
| `ab5812fd` | 2026-07-31 | docs(evidence): admit Codex host notice fast gate | null | null |
| `5328070c` | 2026-07-31 | Merge pull request #198 from Holeshot-Software-LLC/codex/ar-207-codex-host-notice | null | null |
| `7ce640a3` | 2026-07-31 | fix(codex): accept exact 2 percent skill notice | null | null |
| `5ad4aef8` | 2026-07-31 | Merge pull request #199 from Holeshot-Software-LLC/codex/ar-207-codex-host-notice-percent | null | null |
| `ea376a5f` | 2026-07-31 | docs(roadmap): checkpoint exact product routing failure | null | null |
| `947dafbf` | 2026-07-31 | fix(product): preserve exact Codex host notices | null | null |
| `bb1122cc` | 2026-07-31 | docs(roadmap): record exact routing replay | null | null |
| `096570af` | 2026-07-31 | docs(roadmap): record fast-green product repair | null | null |
| `dd85e7d9` | 2026-07-31 | Merge pull request #201 from Holeshot-Software-LLC/codex/ar-207-product-routing-validation | null | null |
| `53755321` | 2026-07-31 | docs(roadmap): checkpoint exact merged activation | null | null |
| `82fc1e74` | 2026-07-31 | docs(roadmap): checkpoint accepted-route spawn failure | null | null |
| `420356a5` | 2026-07-31 | fix(product): authorize exact Codex delegation plan | null | null |
| `146aa1d6` | 2026-07-31 | docs(evidence): admit Codex delegation authority fast gate | null | null |
| `584b949d` | 2026-07-31 | Merge pull request #202 from Holeshot-Software-LLC/codex/ar-207-live-product-proof | null | null |
| `5f0523d4` | 2026-07-31 | docs(roadmap): checkpoint exact merged authority install | null | null |
| `b9d75b38` | 2026-07-31 | docs(roadmap): checkpoint exact authority activation | null | null |
| `95162592` | 2026-07-31 | docs(roadmap): checkpoint first-spawn product failure | null | null |
| `e4ceb896` | 2026-07-31 | fix(product): fail closed on invalid notice proof | null | null |
| `552eb05a` | 2026-07-31 | fix(codex): bind opaque child launches to exact plan rows | null | null |
| `5bed3081` | 2026-07-31 | test(codex): align canary proof with opaque child contract | null | null |
| `ae850527` | 2026-07-31 | fix(codex): scope and serialize opaque child grants | null | null |
| `5144cc9a` | 2026-07-31 | docs(roadmap): checkpoint exact Codex grant gate | null | null |
| `40d10994` | 2026-07-31 | fix(codex): preserve path case and plaintext concurrency | null | null |
| `075bc560` | 2026-07-31 | test(codex): keep plaintext slot regression bounded | null | null |
| `bc6d15bb` | 2026-07-31 | fix(eval): honor per-test conformance deadlines | null | null |
| `361d1e14` | 2026-07-31 | docs(roadmap): checkpoint per-test conformance repair | null | null |
| `169a8260` | 2026-07-31 | docs(roadmap): record 73-mutation conformance proof | null | null |
| `156eb5b5` | 2026-07-31 | docs(roadmap): record exact local merge gate | null | null |
| `207b1506` | 2026-07-31 | Merge pull request #204 from Holeshot-Software-LLC/codex/ar-207-exact-product-proof | null | null |
| `a9a332b6` | 2026-07-31 | fix(update): bound immutable commit responses | null | null |
| `8d51553b` | 2026-07-31 | docs(roadmap): checkpoint bounded update resolution | null | null |
| `7bd64fab` | 2026-07-31 | docs(roadmap): record bounded update merge gate | null | null |
| `e62d0adc` | 2026-07-31 | Merge pull request #207 from Holeshot-Software-LLC/codex/ar-211-bounded-commit-resolution | null | null |
| `df1579bd` | 2026-07-31 | docs(roadmap): checkpoint verifier repair boundary | null | null |
| `c31e715b` | 2026-07-31 | fix(workforce): repair verifier-rejected recruiter proposals | null | null |
| `53d4ebd1` | 2026-07-31 | docs(roadmap): record verifier repair fast gate | null | null |
| `b2ea6342` | 2026-07-31 | fix(workforce): preserve verifier rejection evidence | null | null |
| `81b442a9` | 2026-07-31 | docs(roadmap): record reviewed verifier evidence gate | null | null |
| `1694d6e0` | 2026-07-31 | Merge pull request #210 from Holeshot-Software-LLC/codex/ar-212-repair-recruiter-verification | null | null |
| `c5c8d2ed` | 2026-07-31 | docs(roadmap): checkpoint merged activation proof | null | null |
| `b3513f3c` | 2026-07-31 | docs(roadmap): record context-delivery product failure | null | null |
| `0d27cd69` | 2026-07-31 | Merge pull request #212 from Holeshot-Software-LLC/codex/ar-212-live-product-proof | null | null |
| `e1f543e5` | 2026-07-31 | fix(codex): preserve product plan authority | null | null |
| `23f0b1fe` | 2026-08-01 | test(ar-214): format schema migration fixture | null | null |
| `d6ba36a5` | 2026-08-01 | Merge pull request #213 from Holeshot-Software-LLC/codex/ar-214-context-delivery-authority | null | null |
| `4fe19c07` | 2026-08-01 | fix(workforce): repair critic-rejected contractor proposals | null | null |
| `9c2e9f8f` | 2026-08-01 | Merge pull request #215 from Holeshot-Software-LLC/codex/ar-215-repair-contractor-critic-rejection | null | null |
| `aaf80f76` | 2026-08-01 | fix(workforce): bind gap evidence into contractor critics | null | null |
| `8cfd9751` | 2026-08-01 | Merge pull request #218 from Holeshot-Software-LLC/codex/ar-217-bind-gap-evidence-to-hiring-critic | null | null |
| `583ebc8e` | 2026-08-01 | fix(workforce): fund one repair per inference stage | null | null |
| `ebeeeab2` | 2026-08-01 | docs(ar-218): record exact local verification | null | null |
| `4bd350c8` | 2026-08-01 | fix(config): preserve legacy balanced budget caps | null | null |
| `3a11f299` | 2026-08-01 | docs(ar-218): record reviewed compatibility gate | null | null |
| `f8e607d3` | 2026-08-01 | Merge pull request #220 from Holeshot-Software-LLC/codex/ar-218-fund-stage-repairs | null | null |
| `c28223ee` | 2026-08-01 | docs(ar-219): record multi-unit product boundary | null | null |
| `cf033964` | 2026-08-01 | Merge pull request #222 from Holeshot-Software-LLC/codex/ar-219-record-product-boundary | null | null |
| `e04397b7` | 2026-08-01 | fix(product): preserve turn-scoped specialist execution | null | null |
| `386afca2` | 2026-08-01 | Merge pull request #223 from Holeshot-Software-LLC/codex/ar-219-preserve-product-execution | null | null |
| `232a0eab` | 2026-08-01 | docs(ar-219): checkpoint contractor approval boundary | null | null |
| `b258cfb6` | 2026-08-01 | fix(hiring): bind contractor risk to verified authority | null | null |
| `5c45f154` | 2026-08-01 | Merge pull request #224 from Holeshot-Software-LLC/codex/ar-219-live-product-proof | null | null |
| `c521c388` | 2026-08-01 | docs(ar-220): record recruiter abstention boundary | null | null |
| `824bb8bb` | 2026-08-01 | Merge pull request #225 from Holeshot-Software-LLC/codex/ar-219-recruiter-abstention-proof | null | null |
| `4db9c008` | 2026-08-01 | fix(hiring): converge verified contractor gaps | null | null |
| `ff39761c` | 2026-08-01 | Merge pull request #226 from Holeshot-Software-LLC/codex/ar-220-gap-hiring-convergence | null | null |
| `58cad67b` | 2026-08-01 | docs(ar-221): record product execution boundary | null | null |
| `1771b45a` | 2026-08-01 | docs(ar-222): record legacy work-unit test drift | null | null |
| `adad7329` | 2026-08-01 | fix(product): bind Codex wait and workspace authority | null | null |
| `0f3dfbe5` | 2026-08-01 | docs(ar-221): checkpoint product execution repair | null | null |
| `9c2f4212` | 2026-08-01 | docs(ar-221): record green product repair gate | null | null |
| `43870c8b` | 2026-08-01 | Merge pull request #227 from Holeshot-Software-LLC/codex/ar-221-product-execution-boundary | null | null |
| `27195ce4` | 2026-08-01 | docs(ar-223): freeze Codex child execution failure | null | null |
| `42357453` | 2026-08-01 | fix(ar-223): require explicit Codex child execution | null | null |
| `aff807fd` | 2026-08-01 | docs(ar-223): record tracker and green local gate | null | null |
| `ba76ce79` | 2026-08-01 | Merge pull request #229 from Holeshot-Software-LLC/codex/ar-223-codex-child-task-activation | null | null |
| `873552b7` | 2026-08-01 | docs(ar-223): checkpoint installed merge | null | null |
| `fd8f3a41` | 2026-08-01 | docs(ar-223): record rejected execution followup | null | null |
| `6be9f0f0` | 2026-08-01 | fix(ar-223): bind opaque Codex execution followups | null | null |
| `00cd2b24` | 2026-08-01 | docs(ar-223): record green opaque followup gate | null | null |
| `a2d1a7c8` | 2026-08-01 | Merge pull request #230 from Holeshot-Software-LLC/codex/ar-223-live-proof | null | null |
| `e267a180` | 2026-08-01 | docs(ar-223): checkpoint installed opaque followup merge | null | null |
| `e2cb3408` | 2026-08-01 | docs(ar-223): checkpoint encrypted child evidence boundary | null | null |
| `65ee2986` | 2026-08-01 | fix(ar-223): bind encrypted Codex child execution | null | null |
| `5ff4a08e` | 2026-08-01 | Merge pull request #231 from Holeshot-Software-LLC/codex/ar-223-post-merge-live-proof | null | null |
| `56adc425` | 2026-08-01 | docs(ar-223): checkpoint installed encrypted execution merge | null | null |
| `5849ff68` | 2026-08-01 | docs(ar-223): record missing second Codex stop | null | null |
| `62ea12a2` | 2026-08-01 | fix(ar-223): reconcile Codex completion at parent stop | null | null |
| `34e36c01` | 2026-08-01 | docs(ar-223): record green parent-stop gate | null | null |
| `b2be0775` | 2026-08-01 | Merge pull request #232 from Holeshot-Software-LLC/codex/ar-223-post-merge-live-proof | null | null |
| `614a1a77` | 2026-08-01 | docs(ar-223): checkpoint installed parent-stop merge | null | null |
| `48aa3709` | 2026-08-01 | docs(ar-223): record green parent-stop activation | null | null |
| `c109b92c` | 2026-08-01 | docs(ar-223): checkpoint product parent authority failure | null | null |
| `730bd035` | 2026-08-01 | fix(ar-223): install Codex delegation guidance | null | null |
| `dbf4e0cf` | 2026-08-01 | docs(ar-223): record green Codex guidance gate | null | null |
| `8097e770` | 2026-08-01 | [AR-223] Install Codex delegation guidance (#233) | null | null |
| `b3b2d4f2` | 2026-08-01 | docs(ar-223): checkpoint installed Codex guidance merge | null | null |
| `aa459fb6` | 2026-08-01 | docs(ar-223): checkpoint exact activation proof | null | null |
| `3a0d691b` | 2026-08-01 | docs(ar-223): checkpoint product guidance failure | null | null |
| `4e348c1f` | 2026-08-01 | fix(ar-223): keep Codex delegation plan inline | null | null |
| `529c7eed` | 2026-08-01 | docs(ar-223): record green inline-plan gate | null | null |
| `eb8e0777` | 2026-08-01 | Merge pull request #234 from Holeshot-Software-LLC/codex/ar-223-post-merge-live-proof | null | null |
| `ba82b923` | 2026-08-01 | docs(ar-223): checkpoint installed inline-plan merge | null | null |
| `75d2d716` | 2026-08-01 | docs(ar-223): record green inline-plan activation | null | null |
| `c5563b1f` | 2026-08-01 | docs(ar-223): checkpoint writer-child product failure | null | null |
| `f39dd0ae` | 2026-08-02 | fix(ar-223): make Codex execution turns self-contained | null | null |
| `b497b834` | 2026-08-02 | docs(ar-223): record failed self-contained writer sentinel | null | null |
| `335496e9` | 2026-08-02 | fix(ar-223): use Codex stable multi-agent feature | null | null |
| `0151581a` | 2026-08-02 | fix(ar-223): gate writer proof on Agency plans | null | null |
| `5067b7a0` | 2026-08-02 | fix(ar-223): wait for terminal product children | null | null |
| `1743a22f` | 2026-08-02 | docs(ar-223): record green terminal child gate | null | null |
| `55c52b9f` | 2026-08-02 | docs(ar-223): record failed terminal writer | null | null |
| `8c67cc27` | 2026-08-02 | fix(ar-223): execute Codex specialists on initial spawn | null | null |
| `aef9399d` | 2026-08-02 | docs(ar-223): record failed direct activation | null | null |
| `0cddcafa` | 2026-08-02 | fix(ar-223): certify live Codex callback order | null | null |
| `f14017e1` | 2026-08-02 | docs(ar-223): record failed planner activation | null | null |
| `2d8661c0` | 2026-08-02 | docs(ar-223): classify planner activation failure | null | null |
| `d12041b2` | 2026-08-02 | docs(ar-223): record green callback-order activation | null | null |
| `50fa5056` | 2026-08-02 | docs(ar-223): record failed exact writer sentinel | null | null |
| `10c047f2` | 2026-08-02 | fix(ar-223): bind exact writer planning evidence | null | null |
| `d866b64c` | 2026-08-02 | docs(ar-223): record green exact writer gate | null | null |
| `3e2be294` | 2026-08-02 | docs(ar-223): record exact candidate activation | null | null |
| `502c44f2` | 2026-08-02 | docs(ar-223): record rejected one-unit planner trial | null | null |
| `73f99896` | 2026-08-02 | fix(ar-223): preserve inferred indivisible plans | null | null |
| `bc5bdf81` | 2026-08-02 | docs(ar-223): record indivisible planner diagnosis | null | null |
| `59f85141` | 2026-08-02 | docs(ar-223): record green indivisible plan gate | null | null |
| `9ab2b57a` | 2026-08-02 | docs(ar-223): record exact planner candidate | null | null |
| `ebbac769` | 2026-08-02 | docs(ar-223): record exact candidate activation | null | null |
| `787cd4a2` | 2026-08-02 | docs(ar-223): record failed staffing assurance trial | null | null |
| `3f63d55e` | 2026-08-02 | fix(ar-223): honor indivisible staffing topology | null | null |
| `9f66c865` | 2026-08-02 | docs(ar-223): record green staffing topology gate | null | null |
| `13991fc8` | 2026-08-02 | docs(ar-223): record exact staffing candidate activation | null | null |
| `f647eab1` | 2026-08-02 | docs(ar-223): record failed exact writer execution | null | null |
| `260865ec` | 2026-08-02 | fix(ar-223): prove delegated child execution context | null | null |
| `87a9786d` | 2026-08-02 | docs(ar-223): record failed child-context writer proof | null | null |
| `a854e8e0` | 2026-08-02 | fix(ar-223): require workspace write receipts | null | null |
| `f91c94a9` | 2026-08-02 | docs(ar-223): record parent finalization writer failure | null | null |
| `3b35ae04` | 2026-08-02 | fix(ar-223): reject incomplete workspace finalization | null | null |
| `9891970f` | 2026-08-02 | docs(ar-223): record finalization guard proof | null | null |
| `c6c02d03` | 2026-08-02 | fix(ar-223): order exact child execution last | null | null |
| `e67b4064` | 2026-08-02 | docs(ar-223): record green execution ordering gate | null | null |
| `eb34922b` | 2026-08-02 | docs(ar-223): record failed v4 writer proof | null | null |
| `3cc852f0` | 2026-08-02 | fix(ar-223): preserve child tool outcomes | null | null |
| `a56b6ebf` | 2026-08-02 | docs(ar-223): checkpoint child tool outcome evidence | null | null |
| `2a19c79a` | 2026-08-02 | fix(ar-223): persist child tool evidence in Store | null | null |
| `26cda4bd` | 2026-08-02 | docs(ar-223): checkpoint durable Store diagnostics | null | null |
| `c37b8e4c` | 2026-08-02 | docs(ar-223): record green Store-backed gate | null | null |
| `72043c9f` | 2026-08-02 | docs(ar-223): checkpoint nested tool evidence gap | null | null |
| `95aec42d` | 2026-08-02 | fix(ar-223): classify nested exec tool evidence | null | null |
| `1815a98c` | 2026-08-02 | docs(ar-223): checkpoint nested exec diagnostics | null | null |
| `1d050e01` | 2026-08-02 | docs(ar-223): checkpoint nested wrapper failure | null | null |
| `e0912521` | 2026-08-02 | fix(ar-223): isolate Codex product temp writes | null | null |
| `8322398c` | 2026-08-02 | docs(ar-223): checkpoint temp-rebase writer failure | null | null |
| `e90af864` | 2026-08-02 | fix(ar-223): classify Codex wrapper failures | null | null |
| `b0719878` | 2026-08-02 | docs(ar-223): checkpoint wrapper failure diagnostics | null | null |
| `9f6d52c2` | 2026-08-02 | docs(ar-223): checkpoint Store v3 writer failure | null | null |
| `745f765d` | 2026-08-02 | fix(ar-223): correlate Codex wrapper tool outcomes | null | null |
| `53cfcfbc` | 2026-08-02 | docs(ar-223): checkpoint Store v4 tool outcomes | null | null |
| `1b09fb64` | 2026-08-02 | docs(ar-223): checkpoint Store v4 writer boundary | null | null |
| `263e3f59` | 2026-08-02 | fix(ar-223): auto-review product workspace writes | null | null |
| `46af36d3` | 2026-08-02 | docs(ar-223): checkpoint auto-reviewed writer proof | null | null |
| `f741a67b` | 2026-08-02 | docs(ar-223): normalize recovery evidence commit | null | null |
| `6754a195` | 2026-08-02 | docs(ar-223): record immutable writer pass | null | null |
| `a931bb82` | 2026-08-03 | docs(ar-225): checkpoint product validator mismatch | null | null |
| `ecc3966d` | 2026-08-03 | fix(ar-225): publish task cli validator contract | null | null |
| `370adbdd` | 2026-08-03 | docs(ar-225): checkpoint named fast verification | null | null |
| `ce01d390` | 2026-08-03 | docs(ar-204): record README reality pass | null | null |
| `3381f684` | 2026-08-03 | merge: reconcile README reality proof with main | null | null |
| `55a00db2` | 2026-08-03 | fix(ci): repair automatic PR verification | null | null |
| `1e1bd3e0` | 2026-08-03 | fix(ci): use OS-owned process test interpreter | null | null |
| `4e957e8b` | 2026-08-03 | fix(ci): trust exact Linux supervisor interpreter | null | null |
| `36a29b31` | 2026-08-03 | fix(ci): invoke private quality runtime | null | null |
| `b1241098` | 2026-08-03 | fix(ci): bind quality tests to private temp | null | null |
| `ae3df2f9` | 2026-08-03 | test(ci): create private security fixtures | null | null |
| `0add6c82` | 2026-08-03 | test(ci): harden activation baseline store | null | null |
| `bff75d36` | 2026-08-03 | test(ci): harden generated provider configs | null | null |
| `916a995e` | 2026-08-03 | fix(eval): retain bounded baseline diagnostics | null | null |
| `eea7c457` | 2026-08-03 | test(ci): declare evaluator host platform | null | null |
| `93c2ecab` | 2026-08-03 | fix(eval): bind private fixture interpreter | null | null |
| `95890a15` | 2026-08-03 | fix(ci): align audited dashboard coverage gates | null | null |
| `75d7d9f0` | 2026-08-03 | fix(ci): respect tracker write authority | null | null |
| `83b6af23` | 2026-08-03 | fix(ci): align downstream inference contracts | null | null |
| `c5b2e5e0` | 2026-08-03 | fix(eval): retain exact downstream failures | null | null |
| `d278a325` | 2026-08-03 | fix(eval): align measured retrieval budget | null | null |
| `8eb17466` | 2026-08-03 | docs(ar-226): close automatic PR verification | null | null |
| `ae335d96` | 2026-08-03 | docs(ar-226): use canonical done status | null | null |
| `c01f178f` | 2026-08-03 | Merge pull request #235 from Holeshot-Software-LLC/codex/ar-203-readme-reality | null | null |
| `14a34aef` | 2026-08-04 | AR-227: Expand the specialist roster (#236) | null | null |
| `45be7ea5` | 2026-08-04 | AR-228: Fail open with honest header + fix deterministic gates hiding specialists (#237) | null | null |
| `781e83e5` | 2026-08-04 | AR-229: Fix README specialist count and two pre-existing test failures (#238) | null | null |
| `21c0aaa8` | 2026-08-04 | AR-230: Close completed issues and stale PR (#239) | null | null |
| `def4f8bf` | 2026-08-04 | AR-231: Resource-file filtering, multi-host upgrade, ZCode delegation note, close AR-210 (#240) | null | null |
| `7c33b35f` | 2026-08-04 | AR-232: Remove MAX_PLAN_LIST_ITEMS cap that truncated resource scopes (#241) | null | null |
| `4928a873` | 2026-08-04 | AR-233: Architecture fixes — honest headers, wildcard distinction, strict default, metrics (#242) | null | null |
| `f6e65ea2` | 2026-08-04 | AR-234: Drop round-trip evidence fields from recruiter schema (#243) | null | null |
| `e87747d8` | 2026-08-04 | docs: commit analysis handoffs and uv.lock | null | null |
| `c1fbfbe2` | 2026-08-04 | docs(roadmap): AR-235 plan autonomous gap hiring with isolated security review and amend-first staffing | null | null |
| `f629b639` | 2026-08-04 | docs(roadmap): AR-236 plan full CLI and dashboard functional and presentational parity | null | null |
| `38bb16a0` | 2026-08-04 | docs(roadmap): fix AR-236 capsule relative path to parity analysis | null | null |
| `b98f22b3` | 2026-08-04 | chore(scripts): add transient AR-236 issue-body extraction helper | null | null |
| `66a066ff` | 2026-08-04 | AR-235 slice 1: per-stage inference profile schema and route resolver | null | null |
| `064162d9` | 2026-08-04 | docs(roadmap): plan AR-237 hiring list and show parity (sub-issue 1 of AR-236) | null | null |
| `5dc59259` | 2026-08-04 | AR-237 sub-issue 1: bring hiring list and show to full CLI / dashboard parity | null | null |
| `b5423cef` | 2026-08-04 | docs(roadmap): drop AR-237 depends_on AR-236 to respect the planning pair lesson | null | null |
| `a3316300` | 2026-08-04 | docs(roadmap): plan AR-238 isolated security review with bounded repair (slices 2-3 of AR-235) | null | null |
| `b5bd5496` | 2026-08-04 | AR-238: isolated security review with bounded repair (slices 2-3 of AR-235) | null | null |
| `0b6c0598` | 2026-08-04 | AR-240: amend-first staffing default (slice 4 of AR-235) | null | null |
| `e750593d` | 2026-08-04 | AR-241: hiring cap removal and dashboard visibility (slice 5 of AR-235) | null | null |
| `f85074fe` | 2026-08-04 | AR-242: autonomous promotion with review window (slice 6 of AR-235) | null | null |
| `6b6b5058` | 2026-08-04 | fix(eval): align decision-conformance anchor for max_hires_per_turn rename (AR-241) | null | null |
| `bdc24bec` | 2026-08-04 | AR-243: workforce promotion readiness parity (sub-issue 2 of AR-236) | null | null |
| `b4f7a2b8` | 2026-08-04 | AR-244: workforce duplicates and consolidate parity (sub-issue 3 of AR-236) | null | null |
| `a7a1f614` | 2026-08-04 | docs(roadmap): record tracker URLs for AR-238/240/241/242/243/244 | null | null |
| `da4d9e7f` | 2026-08-04 | AR-245/246/247/248: roster diff, scans, sources, and db-stats dashboard endpoints | null | null |
| `c333f0c4` | 2026-08-04 | docs(roadmap): record tracker URLs for AR-245/246/247/248 | null | null |
| `dff722b2` | 2026-08-04 | AR-249/250/251: explain, upgrade, CLI presentation richness + ADR-0154 | null | null |
| `aa984513` | 2026-08-04 | docs(roadmap): record tracker URLs for AR-249/250/251 | null | null |
| `ca114f62` | 2026-08-04 | docs(roadmap): mark AR-212/215/217/218/228/235-251 as done and close tracker parity | null | null |
| `a498ceb1` | 2026-08-05 | AR-224: simplify Agency evidence header to five factual fields | null | null |
| `41cd2014` | 2026-08-05 | docs(roadmap): record AR-224 tracker URL and done status | null | null |
| `9ff23e80` | 2026-08-05 | AR-222: reconcile legacy work-unit integrity tests | null | null |
| `42971426` | 2026-08-05 | docs(roadmap): record AR-222 tracker URL | null | null |
| `a8913b50` | 2026-08-05 | AR-216: preserve required files in product scenario scopes | null | null |
| `a772ef88` | 2026-08-05 | docs(roadmap): reframe 10 open issues from Codex-specific to multi-harness acceptance | null | null |
| `a5ce51b8` | 2026-08-05 | docs(roadmap): add tracker URLs for AR-220/221 and push multi-harness reframe | null | null |
| `e48f7f8f` | 2026-08-05 | fix(installer): resolve conflict markers in installer_contracts.py | null | null |
| `b7ce8dd9` | 2026-08-05 | docs(roadmap): check ZCode exact-installed boxes for AR-208 and AR-209 | null | null |
| `0d1cf1f3` | 2026-08-05 | fix(structured-provider): inject JSON schema into Anthropic system prompt with assistant prefill | null | null |
| `1a6a68e1` | 2026-08-05 | fix(inference): raise profile timeout cap from 60s to 120s | null | null |
| `7f4583c9` | 2026-08-05 | fix(structured-provider): disable thinking for Anthropic JSON, raise timeout caps | null | null |
| `4e5b4773` | 2026-08-05 | fix(cli-transport): make claude structured transport invocable on Windows | null | null |
| `7d400c13` | 2026-08-05 | feat(inference): per-harness route sections and CLI-transport profiles | null | null |
| `233a5808` | 2026-08-05 | fix(claude-plugin): load on Claude 2.x and make install/canary idempotent | null | null |
| `dbcf67d6` | 2026-08-05 | feat(hiring): wire the owner-approval gate for high-risk domain contracts | null | null |
| `08d6e1ef` | 2026-08-05 | feat(promotion): run the auto-promotion policy on the live outcome path | null | null |
| `fd444fce` | 2026-08-05 | feat(routing): surface deterministic repository stack detection to inference | null | null |
| `8d6c26fd` | 2026-08-05 | feat(installer): ship the Agency MCP server with Hermes and OpenClaw bundles | null | null |
| `3b34a3dd` | 2026-08-05 | feat(eval): add smoke --agent and a ranking-order conformance mutation | null | null |
| `c49b9028` | 2026-08-05 | test(cli): update parser golden manifest for smoke --agent | null | null |
| `dd881fc8` | 2026-08-05 | docs(readme): align delegation, header, recall, canary, and config docs with code | null | null |
| `c4649b59` | 2026-08-05 | fix(eval): repoint the stale high-risk conformance mutation at the live gate | null | null |
| `539cdfa9` | 2026-08-05 | fix(eval): restore the AR-240-orphaned gap-amendment mutation and pin node existence | null | null |
| `99e27dab` | 2026-08-05 | fix(claude-hooks): deliver the response header on Claude turns | null | null |
| `4e55f77a` | 2026-08-05 | fix(staffing): stop treating missing stack enrichment as proof of a gap | null | null |
| `5783bdfe` | 2026-08-05 | feat(staffing): adopt the staff-first doctrine | null | null |
| `79295735` | 2026-08-05 | docs(roadmap): AR-253 — dynamic team dispatch on every harness | null | null |
| `80b91d46` | 2026-08-05 | fix(codex-trust): inspect real hook state and match remediation to it | null | null |
| `334ddddb` | 2026-08-05 | fix(codex-trust): stop overclaiming settled trust in the disabled action | null | null |
| `bb8aab89` | 2026-08-06 | fix(hiring): reject relationship targets unknown to the roster | null | null |
| `2c6fbd7f` | 2026-08-06 | fix(delegation): widen prose-derived write scopes instead of failing issuance | null | null |
| `13561891` | 2026-08-06 | fix(workforce): mint one canonical contractor version across both paths | null | null |
| `6257a51c` | 2026-08-06 | fix(delegation): stop hosts passing specialist slugs as subagent_type | null | null |
| `12f521f0` | 2026-08-06 | feat(runtime): report stale hook runtimes and instrument evidence persistence | null | null |
| `5e83734d` | 2026-08-06 | fix(scripts): refuse the half-migration that bricks the active roster | null | null |
| `37b83bdf` | 2026-08-06 | feat(hooks): give evidence-contract diagnostics somewhere to go | null | null |
| `027c1ec7` | 2026-08-06 | feat(runtime): report source that has moved ahead of the installed hooks | null | null |
| `1f02e718` | 2026-08-06 | feat(header): report the specialist launch model instead of implying a gap | null | null |
| `31befa52` | 2026-08-06 | feat(delegation): record the decline receipt when PreToolUse denies a launch | null | null |
| `c4e6e2ab` | 2026-08-06 | fix(runtime): stop reporting drift between two different environments | null | null |
| `17fbbde5` | 2026-08-06 | fix(status): stop reporting healthy inference as degraded | null | null |
| `1db28724` | 2026-08-06 | fix(store): migrate existing databases onto the launch_model column | null | null |
| `bd227b65` | 2026-08-07 | fix(workforce): let AR-240 amend-first staffing reach the runtime | null | null |
| `2d0c4108` | 2026-08-07 | feat(turn-intent): classify status questions as conversation, not new intent | null | null |
| `0fcd34f6` | 2026-08-07 | feat(delivery): stop requiring delegation and let specialists load into the caller | null | null |
| `cd56471d` | 2026-08-07 | feat(hooks): staff harness-spawned children just in time | null | null |
| `9bef4658` | 2026-08-07 | fix(ci): keep the declared Python 3.10 floor actually runnable | null | null |
| `f495b832` | 2026-08-07 | test(jit): prove just-in-time staffing on every host that has hooks | null | null |
| `d9f6e6be` | 2026-08-07 | refactor(delivery): delete the isolated delivery mode and its enforcement | null | null |
| `40f86603` | 2026-08-07 | test(delivery): drop coverage for the deleted isolated delivery mode | null | null |
| `a3e359b4` | 2026-08-07 | test(canary): retire the Codex delegation-activation proof harness | null | null |
| `1024d94c` | 2026-08-07 | fix(preflight): bound the encoded hook envelope for direct delivery | null | null |
| `a7ebb502` | 2026-08-07 | feat(specialists): state card expiry instead of only recording it | null | null |
| `7c89dcae` | 2026-08-08 | feat(selector): ask inference whether plural cards actually conflict | null | null |
| `1bbf6582` | 2026-08-08 | feat(hooks): hand harness-spawned children cards, plural | null | null |
| `203aabe8` | 2026-08-08 | fix(installer): restore the v2 Codex activation proof contract | null | null |
| `9afe14fe` | 2026-08-08 | refactor(specialists): delete the dead isolated specialist context | null | null |
| `fca6b552` | 2026-08-08 | test(job-b): retire the last delegation-plan proofs and pin the new default | null | null |
| `8c93b096` | 2026-08-08 | feat(hiring): refuse a second contractor for a role that already exists | null | null |
| `e4ce8823` | 2026-08-08 | refactor(inference): delete the recruitment schema nothing could reach | null | null |
| `44f83755` | 2026-08-08 | refactor(units): stop planning delegations a verified route can never make | null | null |
| `b55fdc88` | 2026-08-08 | refactor(evals): drop the delegation eval cases for a retired protocol | null | null |
| `eab8c085` | 2026-08-09 | refactor(mcp): retire the three delegate-branch MCP tools | null | null |
| `047ce723` | 2026-08-09 | test(mcp): retire the coverage tests for the deleted delegate tools | null | null |
| `c0599b0d` | 2026-08-09 | refactor(preflight): delete the unreachable parent_unit_reuse activation path | null | null |
| `902a923d` | 2026-08-09 | feat(hooks): always staff a harness-spawned child, never deny it | null | null |
| `d8ffe91e` | 2026-08-09 | refactor(hooks): delete the dead Codex planned-child activation block | null | null |
| `341723f8` | 2026-08-09 | feat(hooks): stop denying Codex follow-up turns and delete the dead gate | null | null |
| `4bb6d028` | 2026-08-09 | refactor(hooks): delete the planned-child assignment resolution | null | null |
| `861df725` | 2026-08-09 | refactor(hooks): delete the orphaned planned-child delivery helpers | null | null |
| `b222414b` | 2026-08-09 | feat(store): delete the one-use activation grant organ | null | null |
| `4807b29e` | 2026-08-09 | feat(canary): prove card delivery instead of the Job B chain | null | null |
| `b456d0c1` | 2026-08-09 | feat(units): stop planning work units for the host to execute | null | null |
| `9b3b0dd0` | 2026-08-09 | feat(installer): bump the Codex proof contract to v3 | null | null |
| `eeaa6245` | 2026-08-09 | test(header): drop the writer-side launch-model shape test | null | null |
| `5caf3b51` | 2026-08-09 | test(canary): cover the card-delivery proof directly | null | null |
| `5f5e72c5` | 2026-08-09 | test(rule4): prove card delivery against the real store and roster | null | null |
| `a5d57592` | 2026-08-09 | test(lifecycle): retire the one-use execution dispatch test | null | null |
| `20f006b6` | 2026-08-09 | feat(hooks): never deny a child launch Agency cannot verify | null | null |
| `337132a0` | 2026-08-09 | feat(selection): stop letting keywords veto an inferred plan | null | null |
| `7de64fe8` | 2026-08-09 | feat(guidance): stop telling hosts to spawn and stop blocking turns that did not | null | null |
| `5e6aad79` | 2026-08-09 | feat(header): stop rejecting a turn that honestly loaded nothing | null | null |
| `441b8850` | 2026-08-09 | feat(dashboard): delete the unit-agent delegation plan panel | null | null |
| `a1722b8f` | 2026-08-09 | fix(tests): settle the fallout from removing the delegation nudges | null | null |
| `b1ebbab5` | 2026-08-09 | feat(header): delete the dead workspace-write execution gate | null | null |
| `40c608dc` | 2026-08-10 | refactor(units): delete the unit_agent_plan field plumbing | null | null |
| `929c0599` | 2026-08-10 | feat(evidence): prove card delivery from the host's own artifacts | null | null |
| `2624050f` | 2026-08-10 | fix(installer): derive the Claude plugin version from bundle content | null | null |
| `1396ab76` | 2026-08-10 | feat(evidence): report when a host runs code the installer never wired | null | null |
| `b92cd4c9` | 2026-08-10 | fix(providers): say an executable was refused instead of not found | null | null |
| `b7ef11d1` | 2026-08-10 | docs: hand off the rule-4 evidence work | null | null |
| `94610d27` | 2026-08-10 | feat(hooks): stop withholding a turn Agency could not verify | null | null |
| `6e1b28ac` | 2026-08-10 | feat(hooks): staff a harness child even when the parent turn failed preflight | null | null |
| `04db68ae` | 2026-08-10 | docs(threat-model): record that Agency's own unavailability no longer blocks | null | null |
| `9d7ddb27` | 2026-08-10 | feat(workforce): report when a packaged worker has been amended | null | null |
| `e1c26510` | 2026-08-10 | feat(workforce): show packaged divergence when reviewing a worker | null | null |
| `49b6a6be` | 2026-08-10 | test(scratch): reclaim the Windows pytest scratch tree after every run | null | null |
| `c0adbb8b` | 2026-08-10 | docs(scratch): retract the claim that tree size caused the identity failures | null | null |
| `71833c5c` | 2026-08-10 | fix(release): stop a staging directory losing its identity by being used | null | null |
| `20737a7a` | 2026-08-10 | test(release): pin the path-to-handle identity assumption | null | null |
| `c850fe9b` | 2026-08-11 | fix(rule8): stop Agency withholding a turn because Agency is unavailable | null | null |
| `00e15c7d` | 2026-08-11 | fix(ci): clear the three layers blocking a green quality job | null | null |
| `448fd641` | 2026-08-11 | fix(ci): green the fast production spine | null | null |
| `a2634886` | 2026-08-11 | fix(conformance): make three curated mutations actually prove their invariants | null | null |
| `c47b06e6` | 2026-08-11 | fix(preflight): stop the current resident kernel failing its own projection | null | null |
| `01bd5d04` | 2026-08-11 | docs(roadmap): retire the product-trial direction as superseded by the vision | null | null |
| `1a6d3612` | 2026-08-11 | feat(steward): restate the resident kernel as a frame, not a gag order | null | null |
| `c6666369` | 2026-08-11 | docs(roadmap): restate AR-119 as the vision it was always trying to describe | null | null |
| `ecfce69b` | 2026-08-11 | docs(roadmap): unblock the codex rule-4 bench and record why it stalled | null | null |
| `bf2888a9` | 2026-08-11 | docs(roadmap): root-cause codex hook-trust inspection_failed | null | null |
| `6989ecb1` | 2026-08-11 | docs(roadmap): rule 4 on codex measured negative, AR-209 confirmed | null | null |
| `228c720c` | 2026-08-11 | docs(roadmap): census all 1181 rollouts; encryption is universal | null | null |
| `2865493d` | 2026-08-11 | fix(codex): let hook-trust inspection actually launch its worker | null | null |
| `8b92a5b9` | 2026-08-11 | fix(install): record the installed runtime per host, not once per box | null | null |
| `541b2a68` | 2026-08-11 | docs(roadmap): re-prove rule 4 on claude against the refreshed adapter | null | null |
| `17982654` | 2026-08-11 | docs(roadmap): close the codex TUI gap; claude confirmed interactively | null | null |
| `782bff48` | 2026-08-11 | docs(roadmap): record the surface re-scope and the latency blind spot | null | null |
| `3708c96d` | 2026-08-11 | feat(evidence): surface what Agency's routing costs a turn | null | null |
| `f0a6e470` | 2026-08-11 | docs(roadmap): locate the routing latency, and why it stops being attributable | null | null |
| `7d6780bd` | 2026-08-11 | feat(store): record per-call provider latency so the turn cost splits | null | null |
| `57c67047` | 2026-08-11 | docs(roadmap): the routing cache has never hit once, and cannot | null | null |
| `f1fd9064` | 2026-08-11 | feat(selector): give the routing cache a lifetime the hook model provides | null | null |
| `9b3a4828` | 2026-08-11 | fix(dashboard): count a routed turn as successful inference | null | null |
| `eac5df8e` | 2026-08-11 | Merge pull request #266 from Holeshot-Software-LLC/work/rule4-latency-and-cache | null | null |
| `db51dab3` | 2026-08-11 | docs(roadmap): audit what a model change actually breaks | null | null |
| `4d4c5741` | 2026-08-11 | fix(inference): decide the token parameter once, from the provider | null | null |
| `05bc4583` | 2026-08-11 | fix(header): report only model identities Agency observed | null | null |
| `ccf36517` | 2026-08-11 | docs(roadmap): the planner staffs work assigned to someone else | null | null |
| `10093a1e` | 2026-08-11 | docs(roadmap): selection tracks activity, not domain | null | null |
| `5cea1a4d` | 2026-08-11 | feat(evidence): make selection auditable, by explicit opt-in | null | null |
| `abb300a8` | 2026-08-11 | fix(config): let an operator actually set the retention flag | null | null |
| `eb532ff2` | 2026-08-11 | fix(config): refuse a config the installed hooks cannot read | null | null |
| `da6d66b6` | 2026-08-11 | fix(config): write only the paths an operation changed | null | null |
| `ebc741e8` | 2026-08-11 | docs(roadmap): the config rewrite came from validation, not the renderer | null | null |
| `ff986eff` | 2026-08-11 | fix(workforce): give domain enough resolution to separate engineers | null | null |
| `b7d78832` | 2026-08-11 | fix(store): let `agency db trim` reach the routing_intent table | null | null |
| `c0e42931` | 2026-08-11 | refactor(cli)!: cut the CLI back to what the vision asks for | null | null |
| `be246e33` | 2026-08-11 | docs(roadmap): record the CLI half of the vision re-scope | null | null |
| `5ba6a717` | 2026-08-11 | test(hosts): check rule 9 per capability, not per verb | null | null |
| `b7832a03` | 2026-08-11 | Merge pull request #267 from Holeshot-Software-LLC/cli-vision-rescope | null | null |
| `a34aac87` | 2026-08-11 | docs(agents): require a worktree, a branch, and a PR | null | null |
| `5c046fbf` | 2026-08-11 | feat(config): give the operator a policy channel of their own | null | null |
| `28a9a0d1` | 2026-08-11 | fix(config): a context budget must never be able to withhold a turn | null | null |
| `8aa8861d` | 2026-08-11 | feat(install): refuse house rules that would never be applied, and harden the footer | null | null |
| `d5aafc86` | 2026-08-11 | refactor(adapters): drop the surface that let Agency drive a host CLI | null | null |
| `ec135b43` | 2026-08-11 | test(portability): name the real Windows containment module | null | null |
| `f6313749` | 2026-08-11 | Merge pull request #268 from Holeshot-Software-LLC/work/worktree-branching-rule | null | null |
| `9c4112c3` | 2026-08-11 | Merge pull request #269 from Holeshot-Software-LLC/work/operator-policy | null | null |
| `fb34191f` | 2026-08-11 | refactor(delegation)!: delete the work-unit planner, worker pool, and ledger | null | null |
| `b785e42b` | 2026-08-12 | fix(adapters): restore run_preflight, and retire tests of deleted behaviour | null | null |
| `202a7d5a` | 2026-08-12 | style: apply ruff format after the test retirements | null | null |
| `92e4e076` | 2026-08-12 | Merge pull request #271 from Holeshot-Software-LLC/work/delegation-jobb-prune | null | null |
| `c7cf1d96` | 2026-08-12 | Merge pull request #273 from Holeshot-Software-LLC/work/delegation-jobb-prune-2 | null | null |
| `c8038785` | 2026-08-11 | docs(roadmap): refresh the dashboard parity execution handoff | null | null |
| `e69574f1` | 2026-08-11 | feat(dashboard): align operator evidence with staffing vision | null | null |
| `cf2639a5` | 2026-08-11 | feat(dashboard): add bounded vision evidence parity | null | null |
| `de7d72ab` | 2026-08-11 | docs(roadmap): checkpoint AR-236 vision evidence | null | null |
| `99345651` | 2026-08-11 | docs(roadmap): record AR-236 browser verification | null | null |
| `7b3c382a` | 2026-08-11 | test(release): budget AR-236 dashboard evidence | null | null |
| `4822f9b3` | 2026-08-11 | docs(roadmap): checkpoint AR-236 CI budget repair | null | null |
| `61a89828` | 2026-08-11 | test(dashboard): cover AR-236 evidence boundaries | null | null |
| `6213cb1e` | 2026-08-11 | docs(roadmap): checkpoint AR-236 coverage repair | null | null |
| `d1f8ed28` | 2026-08-11 | fix(docs): reconcile canonical worklog history | null | null |
| `b980e608` | 2026-08-11 | docs(roadmap): checkpoint AR-254 history repair | null | null |
| `a78653ce` | 2026-08-11 | fix(docs): make worklog IDs clone independent | null | null |
| `a45422d1` | 2026-08-11 | docs(roadmap): checkpoint deterministic worklog IDs | null | null |
| `cfa67e4b` | 2026-08-12 | docs(roadmap): reframe dashboard parity after Job B | null | null |
| `d9458890` | 2026-08-12 | feat(dashboard): align owner UI with post-Job-B vision | [AR-236](../roadmap/issue-AR-236-achieve-full-cli-dashboard-parity.md) | null |
| `6ce0c37f` | 2026-08-12 | fix(dashboard): enforce truthful evidence parity | [AR-236](../roadmap/issue-AR-236-achieve-full-cli-dashboard-parity.md) | null |
| `15911085` | 2026-08-12 | docs(roadmap): record post-Job-B dashboard verification | [AR-236](../roadmap/issue-AR-236-achieve-full-cli-dashboard-parity.md) | null |
| `1c03a40b` | 2026-08-12 | fix(docs): decode worklog history as UTF-8 | [AR-254](../roadmap/issue-AR-254-reconcile-canonical-worklog-history.md) | null |
| `9ac9d295` | 2026-08-12 | docs(roadmap): checkpoint green dashboard gates | [AR-236](../roadmap/issue-AR-236-achieve-full-cli-dashboard-parity.md) | null |
| `e392c040` | 2026-08-12 | Merge pull request #270 from Holeshot-Software-LLC/codex/dashboard-vision-parity | null | null |
| `64705f1b` | 2026-08-12 | docs(roadmap): put nine-rule mitigations on the P0 path | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | null |
| `b2e728b1` | 2026-08-12 | AR-256: enforce the nine-rule completion contract | [AR-256](../roadmap/issue-AR-256-canonical-nine-rule-completion-contract.md) | null |
| `4acd4951` | 2026-08-12 | docs(roadmap): checkpoint AR-256 completion | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | null |
| `7e1b3603` | 2026-08-12 | fix(native-child): require host-proven inference delivery | [AR-255](../roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md) | null |
| `7f637cb6` | 2026-08-12 | docs(roadmap): checkpoint AR-255 host delivery proof | [AR-255](../roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md) | null |
| `ccb1802c` | 2026-08-12 | docs(architecture): bind Codex plaintext spawn provenance | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | [ADR-0159](../decisions/0159-authenticate-codex-plaintext-spawns-from-host-transcripts.md) |
| `cb5b34aa` | 2026-08-12 | docs(roadmap): checkpoint AR-180 capability preflight | [AR-180](../roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md) | null |
| `ae72fba4` | 2026-08-12 | docs(roadmap): correct AR-180 preflight evidence | [AR-180](../roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md) | null |
| `966845cc` | 2026-08-13 | feat(codex): authenticate plaintext child spawns | [AR-255](../roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md) | [ADR-0159](../decisions/0159-authenticate-codex-plaintext-spawns-from-host-transcripts.md) |
| `81f7d411` | 2026-08-13 | docs(roadmap): checkpoint Codex spawn attestation | [AR-255](../roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md) | [ADR-0159](../decisions/0159-authenticate-codex-plaintext-spawns-from-host-transcripts.md) |
| `3a66ee80` | 2026-08-13 | docs(roadmap): record Codex attestation review findings | [AR-255](../roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md) | [ADR-0159](../decisions/0159-authenticate-codex-plaintext-spawns-from-host-transcripts.md) |
| `2fe5e9ec` | 2026-08-13 | fix(codex): bind spawn ancestry transactionally | [AR-255](../roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md) | [ADR-0159](../decisions/0159-authenticate-codex-plaintext-spawns-from-host-transcripts.md) |
| `9557521e` | 2026-08-13 | docs(roadmap): checkpoint Codex ancestry repair | [AR-255](../roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md) | [ADR-0159](../decisions/0159-authenticate-codex-plaintext-spawns-from-host-transcripts.md) |
| `e8b60f64` | 2026-08-13 | fix(codex): seal exact spawn outcomes | [AR-255](../roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md) | [ADR-0159](../decisions/0159-authenticate-codex-plaintext-spawns-from-host-transcripts.md) |
| `9b2065e1` | 2026-08-13 | docs(roadmap): checkpoint exact Codex outcome review | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | [ADR-0159](../decisions/0159-authenticate-codex-plaintext-spawns-from-host-transcripts.md) |
| `45b21cdc` | 2026-08-13 | fix(codex): authenticate cross-file spawn ancestry | [AR-180](../roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md) | [ADR-0159](../decisions/0159-authenticate-codex-plaintext-spawns-from-host-transcripts.md) |
| `e051dcc0` | 2026-08-13 | docs(roadmap): checkpoint cross-file Codex ancestry | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | [ADR-0159](../decisions/0159-authenticate-codex-plaintext-spawns-from-host-transcripts.md) |
| `922442e0` | 2026-08-13 | docs(roadmap): record complete Codex conformance proof | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | [ADR-0159](../decisions/0159-authenticate-codex-plaintext-spawns-from-host-transcripts.md) |
| `211563c7` | 2026-08-13 | fix(codex): authenticate Desktop alpha ancestry | [AR-180](../roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md) | [ADR-0159](../decisions/0159-authenticate-codex-plaintext-spawns-from-host-transcripts.md) |
| `1a6e4887` | 2026-08-13 | docs(roadmap): checkpoint Desktop alpha ancestry | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | [ADR-0159](../decisions/0159-authenticate-codex-plaintext-spawns-from-host-transcripts.md) |
| `d9344156` | 2026-08-13 | docs(roadmap): checkpoint Desktop evaluator restart | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | [ADR-0159](../decisions/0159-authenticate-codex-plaintext-spawns-from-host-transcripts.md) |
| `217fb78f` | 2026-08-13 | fix(evals): observe the Codex identity domain without filename masking | null | null |
| `fc5749c3` | 2026-08-13 | docs(roadmap): checkpoint the repaired conformance gate and exec census | null | null |
| `e80cb40c` | 2026-08-13 | fix(hosts)!: never withhold a Hermes or OpenClaw turn for Agency blindness | null | null |
| `339875f9` | 2026-08-13 | docs(roadmap): checkpoint the Rule-8 repair at candidate e80cb40c | null | null |
| `967b0a2c` | 2026-08-13 | fix(evals): let the host-parity suite own its master switch, and prove rule 7 | null | null |
| `8d086651` | 2026-08-13 | docs(roadmap): checkpoint rule 7 and the hermetic parity suite at 967b0a2c | null | null |
| `31c21d79` | 2026-08-13 | docs(roadmap): record the conformance result for 967b0a2c | null | null |
| `cb6808fe` | 2026-08-13 | feat(evals): observe zcode in the host-parity sweep through its own boundary | null | null |
| `c578fde6` | 2026-08-13 | docs(roadmap): prove rule 7 on zcode at candidate cb6808fe | null | null |
| `42c1354b` | 2026-08-13 | test(rules): prove cards reach the parent caller on every host | null | null |
| `d995981f` | 2026-08-13 | docs(roadmap): record rules 2 and 3 as proven at candidate 42c1354b | null | null |
| `75663ed0` | 2026-08-13 | test(rules): prove contractor minting inside a real turn on every host | null | null |
| `a4d4b7fe` | 2026-08-13 | docs(roadmap): record rule 6 as proven in simulation at candidate 75663ed0 | null | null |
| `d4b64c35` | 2026-08-13 | test(rules): measure that agency never decides to spawn, on every host | null | null |
| `ebfdeab5` | 2026-08-13 | docs(roadmap): record rule 5 simulation and codex/zcode simulation parity | null | null |
| `be18a9b0` | 2026-08-13 | test(rules): close the last three simulation gaps | null | null |
| `f90995c1` | 2026-08-13 | docs(roadmap): record complete simulation parity at candidate be18a9b0 | null | null |
| `cec10b02` | 2026-08-13 | docs(roadmap): scope the installed-projection reconciliation as AR-258 | null | null |
| `74589af7` | 2026-08-13 | test(selector): retire two assertions the prune and the kernel split orphaned | null | null |
| `a25ec350` | 2026-08-13 | test(resident-managers): split the kernel lifetime contract by whether Agency can run | null | null |
| `b60fa62b` | 2026-08-13 | docs(roadmap): bump the candidate to a25ec350 and record its conformance run | null | null |
| `4ade96a3` | 2026-08-14 | docs(handoff): point the capsule at the live worktree, PR, and candidate | null | null |
| `25bdec39` | 2026-08-14 | fix(tests): substitute rollout files by rename so the identity seal is testable on Linux | null | null |
| `e0d88ee4` | 2026-08-14 | fix(openclaw)!: deny an outbound payload a terminalized trace never committed | null | null |
| `2138fdc1` | 2026-08-14 | docs(ar119): bind the matrix to candidate 9724820e and correct the R8 openclaw evidence | null | null |
| `4081215d` | 2026-08-14 | docs(ar119): point the capsule at candidate 9724820e and the CI repairs | null | null |
| `be209e7a` | 2026-08-14 | Merge pull request #274 from Holeshot-Software-LLC/codex/ar119-vision-mitigation-handoff | null | null |
| `1f60159c` | 2026-08-14 | docs(ar119)!: R4 claude simulation is unproven, and R9 claude follows it down | null | null |
| `a9d84a27` | 2026-08-14 | fix(tests): stub the complete-scope judge with its real zero top score | null | null |
| `38ea6aeb` | 2026-08-14 | docs(ar119): rebind to a9d84a27 and restore R4 claude simulation | null | null |
| `6fa4a782` | 2026-08-14 | docs(ar119): point the capsule at main, generation 56, and a9d84a27 | null | null |
| `e216670a` | 2026-08-14 | feat(evals): prove at the source that only the host may start an agent | null | null |
| `62f6ba48` | 2026-08-14 | docs(ar119): prove Rule 5 at the source and rebind to e216670a | null | null |
| `540a0bfc` | 2026-08-14 | docs(ar119): the capsule's source-only work is finished | null | null |
| `f0e09997` | 2026-08-14 | fix(zcode): see Agency's own older handlers, and honour a forced refresh | null | null |
| `03fdcff1` | 2026-08-14 | ci: run the AR-119 matrix evidence, and tie the list to the matrix | null | null |
| `8f0059f3` | 2026-08-14 | fix(tests): assert the five header fields AR-224 actually ships | null | null |
| `778f4c67` | 2026-08-14 | fix(tests): assert the openclaw fail-open and the turn guard that ship today | null | null |
| `03f8ab48` | 2026-08-14 | style: format the matrix-evidence contract | null | null |
| `917c9b60` | 2026-08-14 | fix(canary): log the invocation traceback instead of discarding it | null | null |
| `1fe68701` | 2026-08-14 | feat(evals): measure staffing rate, recruiter cost, and the cold budget | null | null |
| `9ade8261` | 2026-08-14 | fix(security)!: require integrity, not secrecy, of files hosts wrote | null | null |
| `1e8552a7` | 2026-08-14 | docs(ar119): record the Linux parity gap under Rule 4 and rebind | null | null |
| `9e29aabe` | 2026-08-14 | feat(workforce)!: count only host-evidenced acceptances toward promotion | null | null |
| `63f60171` | 2026-08-14 | docs(ar119): bind the acceptance core to 9e29aabe and run its evidence in CI | null | null |
| `90756987` | 2026-08-14 | docs(ar252): record the three constraints a collector has to answer | null | null |
| `2f46767c` | 2026-08-14 | docs(ar253): locate the latency overrun in the recruiter, not startup | null | null |
| `59da40ae` | 2026-08-14 | feat(preflight): make a terminal failure receipt explain itself | null | null |
| `f7cae78f` | 2026-08-14 | docs(ar119): locate R4 claude Live at one missing activation receipt | null | null |
| `129f2a6a` | 2026-08-14 | docs(ar119)!: native-child staffing has been dead here since 2026-08-07 | null | null |
| `437eb783` | 2026-08-14 | docs(ar119)!: retract the staffing-outage claim; the accounting was retired | null | null |
| `8e0fba31` | 2026-08-14 | feat(rule4): make the collector name the stage that refused | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-252](../roadmap/issue-AR-252-record-verified-acceptance-outcomes.md) | [detail](2026-08-14-8e0fba31-self-diagnosing-rule4-collector.md) |
| `5c654408` | 2026-08-14 | docs(ar119)!: the profile was never the variable; `claude -p` runs no hooks | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-252](../roadmap/issue-AR-252-record-verified-acceptance-outcomes.md) | [detail](2026-08-14-8e0fba31-self-diagnosing-rule4-collector.md) |
| `519f48f7` | 2026-08-14 | fix(doctor)!: fail on schema drift; retract the `claude -p` claim | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-252](../roadmap/issue-AR-252-record-verified-acceptance-outcomes.md) | [detail](2026-08-14-8e0fba31-self-diagnosing-rule4-collector.md) |
| `190f31d8` | 2026-08-14 | docs(ar119): record the runtime republish that restored hook staffing | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | [detail](2026-08-14-8e0fba31-self-diagnosing-rule4-collector.md) |
| `687b4f95` | 2026-08-14 | docs(ar119): the repaired canary records, and fails at the recruiter instead | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-253](../roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md) | [detail](2026-08-14-8e0fba31-self-diagnosing-rule4-collector.md) |
| `6b7eb1c0` | 2026-08-15 | docs(ar253): the recruiter rejection is a plan defect wearing a recruiter's name | [AR-253](../roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md), [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | null |
| `6e490801` | 2026-08-15 | fix(planning): refuse an invented domain at the plan boundary | [AR-253](../roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md), [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | [detail](2026-08-15-6e490801-refuse-invented-plan-domains.md) |
| `6be0977c` | 2026-08-15 | docs(ar253): record the shipped domain boundary and two corrections | [AR-253](../roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md) | [detail](2026-08-15-6e490801-refuse-invented-plan-domains.md) |
| `a75a906f` | 2026-08-15 | feat(evidence): name the requirement axis a staffing failure could not cover | [AR-253](../roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md), [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | [detail](2026-08-15-a75a906f-name-the-uncoverable-requirement-axis.md) |
| `89aca8a2` | 2026-08-15 | docs(ar253): record the axis naming and its fault-classifier meaning | [AR-253](../roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md) | [detail](2026-08-15-a75a906f-name-the-uncoverable-requirement-axis.md) |
| `88378cb8` | 2026-08-15 | fix(tests): repair the stale recruitment row and put its file in CI | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | null |
| `548bba3a` | 2026-08-15 | docs(ar119): bring the recovery capsule current | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | null |
| `30ab92f9` | 2026-08-15 | ci(workflows): stop billing a hosted run for every push to main | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | [detail](2026-08-15-30ab92f9-local-gates-replace-push-ci.md) |
| `bddd3b8c` | 2026-08-15 | ci(hooks): gate every push on the fast local checks | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | [detail](2026-08-15-30ab92f9-local-gates-replace-push-ci.md) |
| `bdfb535a` | 2026-08-15 | docs(ar119): open the capsule on the live Claude canary | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | null |
| `b6230f83` | 2026-08-15 | feat(evidence): record which candidates the recruiter actually ranked | [AR-253](../roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md), [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | null |
| `e2c4e32f` | 2026-08-15 | docs(ar253): retract the plan-defect diagnosis the canary refuted | [AR-253](../roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md) | null |
| `bfed8d45` | 2026-08-16 | docs(ar255): confirm child abstention is what fails as inference_invalid | null | null |
| `15ca819c` | 2026-08-16 | fix(native-child): record a solicited abstention as abstention | null | null |
| `7541a093` | 2026-08-16 | fix(native-child): prove child capability instead of leaving it unknown | null | null |
| `1e884497` | 2026-08-16 | fix(receipts): keep ranked agent ids flat so the evidence store stays readable | null | null |
| `0754c2ae` | 2026-08-16 | docs(ar253): the recruiter ranks the right specialist first and still declines | null | null |
| `c701b6fe` | 2026-08-16 | docs(ar253): the canary's three prerequisites are one recruiter fault | null | null |
| `7a399415` | 2026-08-16 | feat(evidence): name why the top-ranked candidate was not executable | null | null |
| `136cddfe` | 2026-08-16 | docs(ar119): separate the planner's intent reading from its constraint synthesis | null | null |
| `e2b0ce29` | 2026-08-16 | docs(ar253): the ranked set misses an axis the roster can cover | null | null |
| `ac1f95c6` | 2026-08-16 | fix(recruiter): scope the uncoverable axis to what was actually ranked | null | null |
| `23b123a6` | 2026-08-16 | fix(canary): report a Claude host deadline as a timeout, not a refusal | null | null |
| `4bb04a66` | 2026-08-16 | fix(recruiter): score the uncoverable axis over the executable ranked set | null | null |
| `82404c34` | 2026-08-16 | docs(ar253): the ranked set covers the unit and the team is still empty | null | null |
| `a93fcce5` | 2026-08-16 | docs(ar119): point the capsule at the current projection and the real blocker | null | null |
| `a3820ad0` | 2026-08-16 | fix(recruiter): score the axis on the whole ranking, record only the prefix | null | null |
| `375ea790` | 2026-08-16 | docs(ar255): parent staffing is proven live and Rule 4 blocks on one judgment | null | null |
| `f5442023` | 2026-08-16 | fix(canary): give both backends one protocol-error contract | null | null |
| `5bb3502e` | 2026-08-16 | ci(spine): derive the production spine from one source and gate the canary records | null | null |
| `8c7d218f` | 2026-08-16 | feat(evidence): record which specialists the child judge was shown | null | null |
| `ded7751e` | 2026-08-16 | docs(ar255): record the offered-universe evidence and the abstained source | null | null |
| `c91f0e07` | 2026-08-16 | docs(ar255): the child judge was shown code-reviewer and declined it | null | null |
| `3a14a7b9` | 2026-08-16 | feat(evidence): record how much assignment the declining child was given | null | null |
| `a432b181` | 2026-08-16 | docs(ar255): record the task-shape ceiling and the two rejected instruments | null | null |
| `3a337b00` | 2026-08-16 | docs(ar255): ten child decisions, ten declines, and size does not explain it | null | null |
| `9cfb6247` | 2026-08-16 | fix(privacy): redact captured user messages on the host-hook path | null | null |
| `b0940136` | 2026-08-16 | docs(ar255): the child is not evaluated the way the parent is | null | null |
| `a32c4d91` | 2026-08-16 | fix(judge): tell a complete-universe judge what was already verified | null | null |
| `a30c432d` | 2026-08-16 | docs(ar255): design for giving the child the parent's evaluation pattern | null | null |
| `81934a97` | 2026-08-16 | docs(ar119): overnight autonomous brief, and P1 measured inconclusive at n=1 | null | null |
| `dfe4b8bc` | 2026-08-16 | docs(ar119): aim the overnight brief at cells proven, not at Rule 4 alone | null | null |
| `3db18069` | 2026-08-16 | docs(ar119): run the overnight session in a worktree on a branch, never main | null | null |
| `e34ea035` | 2026-08-16 | docs(ar119): leave the owner on a known-good runtime, and mark branch evidence | null | null |
| `a2d956aa` | 2026-08-16 | docs(ar119): box every blocker and forbid spinning overnight | null | null |
| `6d075c53` | 2026-08-16 | docs(ar119): prefer merge-first over branch installs, per the owner | null | null |
| `966e8bae` | 2026-08-16 | feat(ar255): fund one repair call before a child abstention is final | null | null |
| `cb86e939` | 2026-08-16 | docs(ar119): open the overnight report with the runtime the machine is on | null | null |
| `347f2982` | 2026-08-16 | docs(ar119): record the sweep verdicts and the completed baseline series | null | null |
| `61c3aec3` | 2026-08-16 | docs(ar119): give the owner a runnable openclaw and hermes packet | null | null |
| `e5016733` | 2026-08-16 | docs(ar119): refute the zcode-CLI stage for this box, by measurement | null | null |
| `e41ac039` | 2026-08-16 | fix(hiring): record the security verdict from the gate signal | null | null |
| `4d48d937` | 2026-08-16 | docs(ar119): record the hiring verdict repair in the report | null | null |
| `c77c67a4` | 2026-08-16 | Merge pull request #275 from Holeshot-Software-LLC/claude/remote-control-14de96 | null | null |
| `73152816` | 2026-08-16 | docs(ar119): the machine is on the post-P2 main build | null | null |
| `2cd71694` | 2026-08-16 | docs(ar119): post-P2 run 1 per-run split and the repair observability gap | null | null |
| `9dc5d64a` | 2026-08-16 | docs(ar119): run 2 legacy again, over-budget repair hypothesis refuted | null | null |
| `ac292357` | 2026-08-16 | docs(ar255): the repair path is proven live and the judge declines on the merits | null | null |
| `4223d52e` | 2026-08-16 | docs(ar119): hook-window cancellation erases staffing and its evidence | null | null |
| `b3b11011` | 2026-08-17 | docs(ar119): R2 and R3 live evidence secured on claude at the exact candidate | null | null |
| `e37c4ed5` | 2026-08-17 | docs(ar119): R7 complete and R6 fired organically on the exact candidate | null | null |
| `aff5fe6a` | 2026-08-17 | docs(ar119): R6 pool reuse held without a rehire | null | null |
| `f2f3ca88` | 2026-08-17 | docs(ar119): record the installed and live evidence at candidate c77c67a4 | null | null |
| `21b43506` | 2026-08-17 | docs(ar119): first Installed and Live layers - R2 R3 R6 R7 proven on claude | null | null |
| `c1c978e3` | 2026-08-17 | docs(ar119): refresh the capsule and finish the morning report | null | null |
| `48f25270` | 2026-08-17 | feat(ar255): record the redacted child assignment under the owner's capture flag | null | null |
| `38f20e43` | 2026-08-17 | Merge pull request #276 from Holeshot-Software-LLC/claude/remote-control-14de96 | null | null |
| `6fbc6313` | 2026-08-17 | docs(ar119): the capture wiring shipped; correct the report | null | null |
| `227ab06b` | 2026-08-17 | Merge pull request #277 from Holeshot-Software-LLC/claude/remote-control-14de96 | null | null |
| `34b6c09f` | 2026-08-17 | docs(ar119): the machine wakes on main tip 227ab06b | null | null |
| `f057ffb7` | 2026-08-17 | Merge pull request #278 from Holeshot-Software-LLC/claude/remote-control-14de96 | null | null |
| `d7ecbc55` | 2026-08-17 | docs(ar119): warn that the owner's eval_commands WIP left the working tree | null | null |
| `5d9f7ecf` | 2026-08-17 | Merge pull request #279 from Holeshot-Software-LLC/claude/remote-control-14de96 | null | null |
| `c916e96d` | 2026-08-17 | docs(ar119): the owner resolved the WIP question; retire the warning | null | null |
| `a13f6556` | 2026-08-17 | Merge pull request #280 from Holeshot-Software-LLC/claude/remote-control-14de96 | null | null |
| `5c027afe` | 2026-08-17 | docs(ar119): retract my own claim that the capture flag was off | null | null |
| `e737e335` | 2026-08-17 | docs(ar255): the capture wiring records nothing and my test could not see it | null | null |
| `0f0d07a0` | 2026-08-17 | feat(ar255): give the captured child assignment its own content lane | null | null |
| `dfd482d0` | 2026-08-17 | Merge pull request #281 from Holeshot-Software-LLC/claude/remote-control-14de96 | null | null |
| `53088a93` | 2026-08-17 | docs(ar255): the capture settled it -- the judge was right about errands | null | null |
| `be8b8df4` | 2026-08-17 | docs(ar119): point the capsule at the settled verdict and the instrument fix | null | null |
| `520ad0c1` | 2026-08-17 | Merge pull request #282 from Holeshot-Software-LLC/claude/remote-control-14de96 | null | null |
| `b480cc9a` | 2026-08-17 | fix(canary): hand the child the work unit verbatim in the activation prompt | null | null |
| `a7ff98c3` | 2026-08-17 | fix(canary): demand exclusive verbatim handoff and pin the prompt text | null | null |
| `7c3f1fac` | 2026-08-17 | style(tests): sort the activation-canary contract import block | null | null |
| `28f5e835` | 2026-08-17 | Merge pull request #283 from Holeshot-Software-LLC/claude/remote-control-14de96 | null | null |
| `1796283e` | 2026-08-17 | fix(canary): v3 instrument -- the prompt is planner input, stop naming expertise | null | null |
| `58af4d0c` | 2026-08-17 | Merge pull request #284 from Holeshot-Software-LLC/claude/remote-control-14de96 | null | null |
| `4cc94e09` | 2026-08-17 | docs(ar119): instrument-series verdict -- handoff proven, recruiter is the blocker | null | null |
| `7cab979f` | 2026-08-17 | Merge pull request #285 from Holeshot-Software-LLC/claude/remote-control-14de96 | null | null |
| `37e2cb46` | 2026-08-17 | docs(ar119): re-measured v3 verdict -- the judge's threshold is the R4 blocker | null | null |
| `897af162` | 2026-08-17 | Merge pull request #286 from Holeshot-Software-LLC/claude/remote-control-14de96 | null | null |
| `6878954f` | 2026-08-17 | feat(selector): owner policy -- small units still get cards | null | null |
| `99a7b3ac` | 2026-08-17 | Merge pull request #287 from Holeshot-Software-LLC/claude/remote-control-14de96 | null | null |
| `254ecdd5` | 2026-08-17 | docs(ar119): policy series addendum -- parent chain fully green, child draw provider-killed | null | null |
| `da380c2f` | 2026-08-17 | Merge pull request #288 from Holeshot-Software-LLC/claude/remote-control-14de96 | null | null |
| `08cba732` | 2026-08-17 | docs(ar119): vision-completion autonomous loop brief | null | null |
| `94489201` | 2026-08-17 | Merge pull request #289 from Holeshot-Software-LLC/claude/remote-control-14de96 | null | null |
| `99be892a` | 2026-08-17 | docs(ar119): open the vision-loop status ledger -- core.worktree repair, provider backoff | null | null |
| `965daa1f` | 2026-08-17 | docs(ar119): record the first live v6 child delivery and the green probe | null | null |
| `2c4af855` | 2026-08-17 | docs(ar119): series runs 1-2 provider-killed; 30-minute backoff ruling | null | null |
| `3d70a2e9` | 2026-08-17 | docs(ar119): verify the live v6 chain end to end across three surfaces | null | null |
| `d2c0e961` | 2026-08-17 | docs(ar252): settle the joint-verdict shape as a delegated ruling | null | null |
| `f980f27e` | 2026-08-17 | Merge pull request #290 from Holeshot-Software-LLC/codex/ar119-vision-mitigation-handoff | null | null |
| `ed7ca319` | 2026-08-17 | docs(ar119): series 0/3 provider-killed; draft the f980f27e candidate evidence | null | null |
| `72a3756f` | 2026-08-17 | Merge origin/main (PR #290) back into the working branch | null | null |
| `3269ff67` | 2026-08-17 | docs(ar119): finalize the 99a7b3ac runtime evidence document | null | null |
| `b192dead` | 2026-08-17 | docs(ar119): advance the matrix to candidate 3269ff67 -- first R1 and R4 installed+live anywhere | null | null |
| `a7ce34eb` | 2026-08-17 | Merge pull request #291 from Holeshot-Software-LLC/codex/ar119-vision-mitigation-handoff | null | null |
| `63dd2800` | 2026-08-17 | docs(ar119): cycle 4 -- advance merged on CLEAN rollup, organic hire recurs | null | null |
| `31704027` | 2026-08-17 | Merge origin/main (PR #291) back into the working branch | null | null |
| `69f1ba40` | 2026-08-17 | docs(ar119): series 2 run 2 -- parent chain green, child draw provider-killed again | null | null |
| `369665bf` | 2026-08-18 | docs(ar119): refresh the capsule at the 3269ff67 candidate | null | null |
| `242418fe` | 2026-08-18 | docs(ar119): refresh the capsule at the 3269ff67 candidate | null | null |
| `e642f73e` | 2026-08-18 | docs(ar253): file the overnight stage-roving provider receipts | null | null |
| `9efe9e21` | 2026-08-18 | Merge pull request #292 from Holeshot-Software-LLC/codex/ar119-vision-mitigation-handoff | null | null |
| `1bd7e37c` | 2026-08-18 | docs(ar119): R6 re-proof -- organic mint and pool reuse on the installed runtime | null | null |
| `5964618b` | 2026-08-18 | docs(ar119): flip R6 claude at candidate 1bd7e37c -- seven of eight rules full | null | null |
| `2195e738` | 2026-08-18 | Merge pull request #293 from Holeshot-Software-LLC/codex/ar119-vision-mitigation-handoff | null | null |
| `35f679e9` | 2026-08-18 | docs(ar119): capsule reflects the R6 re-proof and candidate 1bd7e37c | null | null |
| `405c65e7` | 2026-08-18 | docs(ar119): series 3 run 1 -- new failure class, instrument disobedience | null | null |
| `172a1624` | 2026-08-18 | docs(ar119): series 3 run 2 -- best parent chain yet, third child-stage kill | null | null |
| `548d61f3` | 2026-08-18 | docs(ar119): the acceptance draw landed -- post-policy judge abstains on the pure unit | null | null |
| `9f1b8871` | 2026-08-18 | docs(ar255): record the post-policy abstention on the pure unit | null | null |
| `3c389e14` | 2026-08-18 | docs(ar119): retract R1, R4, R5 and R6 claude installed+live after adversarial review | null | null |
| `b2b19727` | 2026-08-18 | docs(ar119): final status for the vision-completion loop run | null | null |
| `32586610` | 2026-08-18 | docs(ar119): capsule reflects the retractions and the real Rule 4 blocker | null | null |
| `643e74ab` | 2026-08-18 | Merge pull request #294 from Holeshot-Software-LLC/codex/ar119-vision-mitigation-handoff | null | null |
| `19b75aa3` | 2026-08-18 | docs(ar119): retract the missing-receipts claim; name R4's real blocker | null | null |
| `28eda25b` | 2026-08-18 | docs(ar119): the child-to-receipt join needs no code change; revert the field I added | null | null |
| `b8284c9b` | 2026-08-18 | feat(evidence): resolve an outcome for every harness-spawned child launch | null | null |
| `f2ba7dd7` | 2026-08-18 | feat(cli): add evidence child-launches, the per-launch outcome report | null | null |
| `867fcba8` | 2026-08-18 | docs(ar119): record the first reproducible child-delivery rate | null | null |
| `4939466d` | 2026-08-18 | Merge pull request #295 from Holeshot-Software-LLC/codex/ar119-vision-mitigation-handoff | null | null |
| `c2100761` | 2026-08-18 | fix(evidence): resolve launches whose artifact copy is shortened or quotes a marker | null | null |
| `cac2ead1` | 2026-08-18 | refactor(evidence): extract the launch-to-decision matcher | null | null |
| `e7b2b5cd` | 2026-08-18 | docs(ar119): record the completion-scope ruling and arm the openclaw/hermes packet | null | null |
| `52903976` | 2026-08-18 | docs(ar119): openclaw and hermes have no Rule 4 route today -- say so before he installs | null | null |
| `6f820d0a` | 2026-08-18 | docs(ar119): box the push blocker -- shared bare=true exposed by removing the hijack | null | null |
| `b8a519bc` | 2026-08-18 | docs(ar119): the push path writes core.bare=true into the real config | null | null |
| `2adb42e6` | 2026-08-18 | fix(tests): stop the CI-scope fixture from re-initializing the real repository | null | null |
| `aebad9c1` | 2026-08-18 | fix(tests): make the CI-scope suite hermetic against an inherited git env | null | null |
| `6ba837fa` | 2026-08-18 | Merge pull request #296 from Holeshot-Software-LLC/codex/ar119-vision-mitigation-handoff | null | null |
| `895d952c` | 2026-08-18 | docs(ar119): refresh the capsule for a fresh session | null | null |
| `dc0f077d` | 2026-08-18 | Merge pull request #297 from Holeshot-Software-LLC/codex/ar119-vision-mitigation-handoff | null | null |
| `cf14d939` | 2026-08-19 | docs(ar119): record the codex canary series, the seal decision, and R8 from disk | null | null |
| `67acca48` | 2026-08-19 | docs(ar119): settle the 7.1 acceptance draw and re-cost Option A | null | null |
| `8607eadf` | 2026-08-19 | docs(ar119): record that the canary work unit is deliberately not configurable | null | null |
| `7d361a7a` | 2026-08-19 | docs(ar119): the canary fixture coupling is separable per host | null | null |
| `9e8f8b79` | 2026-08-19 | docs(ar119): retract the 7.1 settlement -- the control unit staffs | null | null |
| `adc412a7` | 2026-08-19 | docs(ar119): refresh the capsule for a new session | null | null |
| `4f34c113` | 2026-08-19 | docs(ar119): correct the capsule's unpushed-branch state | null | null |
| `976f666a` | 2026-08-19 | docs(ar119): use the full SHA for evidence_commit | null | null |
| `bb33a102` | 2026-08-19 | docs(ar119): capsule reflects the pushed branch state | null | null |
| `05f76fe3` | 2026-08-19 | feat(ar119): commit the child-judge probe and confirm the decline is provider-conditional | null | null |
| `c0069997` | 2026-08-19 | feat(canary): pin child judges per harness | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | [detail](2026-08-19-c0069997-pin-child-judge-providers-per-canary-harness.md) |
| `cc618e4a` | 2026-08-19 | test(canary): align pin verification contracts | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | [detail](2026-08-19-cc618e4a-align-pin-verification-contracts.md) |
| `ed5545f7` | 2026-08-19 | docs(ar119): scope codex parent and three-host phase | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | null |
| `36cb081c` | 2026-08-19 | feat(canary): reuse inference profiles for zcode judges | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | [detail](2026-08-19-36cb081c-reuse-zcode-glm-canary-profile.md) |
| `1d5bb4b9` | 2026-08-19 | fix(canary): carry profile pins through host preparation | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | [detail](2026-08-19-1d5bb4b9-carry-profile-pins-through-host-preparation.md) |
| `14de2f74` | 2026-08-19 | fix(canary): correlate Claude proof to child route | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | [detail](2026-08-19-14de2f74-correlate-claude-proof-to-child-route.md) |
| `dd3dbdcc` | 2026-08-19 | docs(ar119): checkpoint installed Option A evidence | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | null |
| `7088b55c` | 2026-08-19 | docs(ar119): keep recovery capsule bounded | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | null |
| `0c73db8f` | 2026-08-19 | docs(ar119): checkpoint repaired Option A refresh | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | null |
| `351f39e3` | 2026-08-19 | docs(ar119): record attended zcode option a proof | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | null |
| `3baef26f` | 2026-08-19 | fix(native-child): hydrate prefixed prompt identities | [AR-135](../roadmap/issue-AR-135-complete-zcode-integration.md), [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-253](../roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md) | null |
| `dac11c16` | 2026-08-19 | docs(ar119): record repaired zcode delivery and completion plan | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-135](../roadmap/issue-AR-135-complete-zcode-integration.md), [AR-253](../roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md) | null |
| `29a710ab` | 2026-08-19 | docs(ar119): admit owner-authorized main rollout | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | null |
| `91d1299d` | 2026-08-19 | docs(ar119): bind the rollout to local gates | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | null |
| `ae1964fa` | 2026-08-19 | Merge pull request #298 from Holeshot-Software-LLC/codex/ar119-vision-mitigation-handoff [skip ci] | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | null |
| `5ed33a17` | 2026-08-19 | docs(ar119): checkpoint merged-main installation | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | null |
| `a1acc8a1` | 2026-08-19 | docs(ar119): record merged-main Claude smoke | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | null |
| `16e55c9d` | 2026-08-19 | docs(ar119): record Codex parent abstention | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | null |
| `6d378c2e` | 2026-08-19 | docs(ar119): record Codex parent header proof | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | null |
| `bc74a33c` | 2026-08-19 | docs(ar119): record merged-main Codex child rerun | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | null |
| `88fc1956` | 2026-08-19 | fix(zcode): deliver authoritative parent header snapshots | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | [detail](2026-08-19-88fc1956-zcode-authoritative-parent-headers.md) |
| `f203dc66` | 2026-08-20 | Merge pull request #299 from Holeshot-Software-LLC/codex/ar119-main-rollout-evidence [skip ci] | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | null |
| `895b8c70` | 2026-08-20 | docs(ar119): record exact-main zcode cli proof | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | null |
| `b908b747` | 2026-08-20 | Merge pull request #300 from Holeshot-Software-LLC/codex/ar119-main-rollout-evidence [skip ci] | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | null |
| `8e87b7a7` | 2026-08-20 | feat(outcomes): bind verifier semantics to host artifacts | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-252](../roadmap/issue-AR-252-record-verified-acceptance-outcomes.md) | [detail](2026-08-20-8e87b7a7-bind-verifier-semantics-to-host-artifacts.md) |
| `aa6439b1` | 2026-08-20 | feat(outcomes): collect atomic producer verifier pairs | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-252](../roadmap/issue-AR-252-record-verified-acceptance-outcomes.md) | [detail](2026-08-20-aa6439b1-collect-atomic-producer-verifier-pairs.md) |
| `87d87b99` | 2026-08-20 | feat(outcomes): wire isolated Claude acceptance canary | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-252](../roadmap/issue-AR-252-record-verified-acceptance-outcomes.md) | [detail](2026-08-20-87d87b99-wire-isolated-claude-acceptance-canary.md) |
| `6cc6601c` | 2026-08-20 | docs(ar119): record Codex 0.148 pre-spawn draw | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | null |
| `5a1d863c` | 2026-08-20 | Merge pull request #301: bind accepted outcomes to host artifacts [skip ci] | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-252](../roadmap/issue-AR-252-record-verified-acceptance-outcomes.md) | null |
| `3a3191da` | 2026-08-20 | docs(ar119): record Claude outcome preflight failure | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-252](../roadmap/issue-AR-252-record-verified-acceptance-outcomes.md) | null |
| `3bad5302` | 2026-08-20 | fix(canary): keep Claude outcome preflight indivisible | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-252](../roadmap/issue-AR-252-record-verified-acceptance-outcomes.md) | [detail](2026-08-20-3bad5302-keep-claude-outcome-preflight-indivisible.md) |
| `a102a932` | 2026-08-20 | Merge pull request #302: keep Claude outcome preflight indivisible [skip ci] | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-252](../roadmap/issue-AR-252-record-verified-acceptance-outcomes.md) | null |
| `fc6aa539` | 2026-08-20 | docs(ar119): checkpoint merged Claude preflight repair | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-252](../roadmap/issue-AR-252-record-verified-acceptance-outcomes.md) | null |
| `fb256660` | 2026-08-20 | docs(ar119): record Claude recruiter boundary | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-252](../roadmap/issue-AR-252-record-verified-acceptance-outcomes.md) | null |
| `53c3d53b` | 2026-08-20 | fix(ar119): pin accepted-outcome parent recruiter [skip ci] | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-252](../roadmap/issue-AR-252-record-verified-acceptance-outcomes.md) | [detail](2026-08-20-53c3d53b-pin-accepted-outcome-parent-recruiter.md) |
| `eff66c67` | 2026-08-20 | Merge pull request #303: pin accepted-outcome parent recruiter [skip ci] | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-252](../roadmap/issue-AR-252-record-verified-acceptance-outcomes.md) | null |
| `e7e4e285` | 2026-08-20 | fix(ar119): make recruiter safe-team repairs actionable | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-253](../roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md) | [detail](2026-08-20-e7e4e285-make-recruiter-safe-team-repairs-actionable.md) |
| `8db9700b` | 2026-08-20 | docs(ar119): checkpoint recruiter contract gates | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) | null |
| `c279bca9` | 2026-08-20 | Merge pull request #304: make recruiter safe-team repairs actionable [skip ci] | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-253](../roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md) | null |
| `de9ef543` | 2026-08-20 | fix(ar259): preserve terminal hiring state in failure receipts | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-259](../roadmap/issue-AR-259-preserve-terminal-hiring-state.md) | [detail](2026-08-20-de9ef543-preserve-terminal-hiring-state.md) |
| `b265981a` | 2026-08-20 | docs(ar119): checkpoint hiring receipt gates | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-259](../roadmap/issue-AR-259-preserve-terminal-hiring-state.md) | null |
| `a5b40eb6` | 2026-08-20 | docs(ar259): link authorized tracker issue | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-259](../roadmap/issue-AR-259-preserve-terminal-hiring-state.md) | null |
| `06f10171` | 2026-08-20 | Merge pull request #306: preserve terminal hiring evidence [skip ci] | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-259](../roadmap/issue-AR-259-preserve-terminal-hiring-state.md) | null |
| `95356cfa` | 2026-08-20 | fix(ar260): accept verified launch bindings in outcome canary | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-252](../roadmap/issue-AR-252-record-verified-acceptance-outcomes.md), [AR-260](../roadmap/issue-AR-260-accept-verified-launch-bindings-in-outcome-canary.md) | [detail](2026-08-20-95356cfa-accept-verified-launch-bindings.md) |
| `817418d9` | 2026-08-20 | docs(ar119): checkpoint AR-260 reporter gates | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-260](../roadmap/issue-AR-260-accept-verified-launch-bindings-in-outcome-canary.md) | null |
| `00c4dc7e` | 2026-08-20 | Merge pull request #308: accept verified launch bindings [skip ci] | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-252](../roadmap/issue-AR-252-record-verified-acceptance-outcomes.md), [AR-260](../roadmap/issue-AR-260-accept-verified-launch-bindings-in-outcome-canary.md) | null |
| `3f20a761` | 2026-08-20 | docs(ar119): record exact-main Claude outcome proof | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-252](../roadmap/issue-AR-252-record-verified-acceptance-outcomes.md), [AR-260](../roadmap/issue-AR-260-accept-verified-launch-bindings-in-outcome-canary.md) | null |
| `0b48bb51` | 2026-08-20 | fix(ar261): disambiguate technical diagnosis risk | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-261](../roadmap/issue-AR-261-disambiguate-technical-diagnosis-risk.md) | [detail](2026-08-20-0b48bb51-disambiguate-technical-diagnosis-risk.md) |
| `44596e90` | 2026-08-20 | docs(ar119): bind technical diagnosis recovery pair | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-261](../roadmap/issue-AR-261-disambiguate-technical-diagnosis-risk.md) | null |
| `2a5feaa5` | 2026-08-21 | docs(ar261): link authorized tracker records | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-259](../roadmap/issue-AR-259-preserve-terminal-hiring-state.md), [AR-261](../roadmap/issue-AR-261-disambiguate-technical-diagnosis-risk.md) | null |
| `692a9257` | 2026-08-21 | Merge pull request #310: fix technical diagnosis hiring risk [skip ci] | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-261](../roadmap/issue-AR-261-disambiguate-technical-diagnosis-risk.md) | null |
| `3752ef99` | 2026-08-21 | docs(ar119): record expired Claude auth boundary | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-261](../roadmap/issue-AR-261-disambiguate-technical-diagnosis-risk.md) | null |
| `1a8071ca` | 2026-08-21 | fix(dashboard): preserve slow host inspection parity | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-236](../roadmap/issue-AR-236-achieve-full-cli-dashboard-parity.md), [AR-262](../roadmap/issue-AR-262-preserve-slow-host-dashboard-parity.md) | null |
| `204ca567` | 2026-08-21 | docs(ar119): record Codex Desktop activation gap | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-262](../roadmap/issue-AR-262-preserve-slow-host-dashboard-parity.md), [AR-263](../roadmap/issue-AR-263-restore-codex-desktop-parent-hook-delivery.md) | null |
| `0d8a2355` | 2026-08-21 | Merge pull request #312: preserve slow host inspection parity [skip ci] | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-236](../roadmap/issue-AR-236-achieve-full-cli-dashboard-parity.md), [AR-262](../roadmap/issue-AR-262-preserve-slow-host-dashboard-parity.md) | null |
| `54b7143b` | 2026-08-21 | docs(ar264): define governed contractor execution profiles | [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md) | null |
| `c4677a41` | 2026-08-21 | feat(workforce): compile actionable contractor profiles | [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md) | null |
| `16b43b7c` | 2026-08-21 | fix(workforce): finalize contractor profile gates | [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md) | null |
| `c563587c` | 2026-08-21 | docs(ar264): link tracker issue 313 | [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md) | null |
| `d5eec96b` | 2026-08-21 | docs(ar264): record pull request 314 | [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md) | null |
| `fa5137b3` | 2026-08-21 | docs(ar264): record merge authorization | [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md) | null |
| `da851c65` | 2026-08-21 | Merge pull request #314: compile actionable contractor execution profiles [skip ci] | [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md) | null |
| `e796b56b` | 2026-08-21 | fix(workforce): migrate shipped package v1 identities | [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md) | null |
| `b19b8495` | 2026-08-21 | docs(ar264): record historical package repair gates | [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md) | null |
| `f76050d7` | 2026-08-21 | Merge pull request #315: migrate shipped package-v1 contractor identities [skip ci] | null | null |
| `5ee15c5e` | 2026-08-21 | docs(ar264): checkpoint exact-main host smoke | null | null |
| `0599959b` | 2026-08-21 | docs(ar263): record fresh Desktop hook gap [skip ci] | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-263](../roadmap/issue-AR-263-restore-codex-desktop-parent-hook-delivery.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md) | null |
| `4e5f0ca2` | 2026-08-21 | docs(ar264): record authenticated host evidence [skip ci] | null | null |
| `4a326773` | 2026-08-21 | Merge pull request #316: record authenticated exact-main host evidence [skip ci] | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md) | null |
| `85ad8d88` | 2026-08-21 | fix(openclaw): harden Linux installation and bridge | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-285](../roadmap/issue-AR-285-accept-openclaw-stopped-gateway-status.md), [AR-267](../roadmap/issue-AR-267-accept-openclaw-numeric-package-revision.md), [AR-268](../roadmap/issue-AR-268-create-nested-config-parents-privately.md), [AR-269](../roadmap/issue-AR-269-accept-null-openclaw-control-errors.md), [AR-270](../roadmap/issue-AR-270-bind-openclaw-installed-copy-provenance.md), [AR-271](../roadmap/issue-AR-271-accept-stopped-openclaw-uninstall-status.md) | null |
| `0c5b2b2a` | 2026-08-21 | fix(openclaw): preserve model receipt fields | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-272](../roadmap/issue-AR-272-preserve-openclaw-model-receipt-fields.md) | null |
| `33d2f4ab` | 2026-08-21 | fix(openclaw): expose native Agency finalizer | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-273](../roadmap/issue-AR-273-expose-openclaw-native-finalizer-tool.md) | null |
| `2d7c055a` | 2026-08-21 | fix(openclaw): preserve native finalizer host | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-273](../roadmap/issue-AR-273-expose-openclaw-native-finalizer-tool.md) | null |
| `c860e958` | 2026-08-21 | docs(ar119): record OpenClaw router evidence | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-273](../roadmap/issue-AR-273-expose-openclaw-native-finalizer-tool.md) | null |
| `1b789ac3` | 2026-08-21 | fix(inference): keep LiteLLM profiles model-agnostic | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-274](../roadmap/issue-AR-274-model-agnostic-structured-inference-profiles.md) | null |
| `62759fd6` | 2026-08-21 | docs(roadmap): checkpoint OpenClaw live inference failure | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-274](../roadmap/issue-AR-274-model-agnostic-structured-inference-profiles.md) | null |
| `fba12371` | 2026-08-21 | fix(inference): delegate exact schemas through LiteLLM | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-274](../roadmap/issue-AR-274-model-agnostic-structured-inference-profiles.md) | null |
| `68f8074c` | 2026-08-21 | docs(ar119): checkpoint exact-schema OpenClaw install | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-274](../roadmap/issue-AR-274-model-agnostic-structured-inference-profiles.md) | null |
| `ba9bb6af` | 2026-08-21 | docs(ar119): record exact-schema status control | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-274](../roadmap/issue-AR-274-model-agnostic-structured-inference-profiles.md) | null |
| `610f2691` | 2026-08-21 | docs(ar119): record OpenClaw inference and skill gap | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-274](../roadmap/issue-AR-274-model-agnostic-structured-inference-profiles.md), [AR-275](../roadmap/issue-AR-275-record-openclaw-native-skill-reads.md) | null |
| `7fcd828d` | 2026-08-22 | fix(openclaw): record authorized native skill reads | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-274](../roadmap/issue-AR-274-model-agnostic-structured-inference-profiles.md), [AR-275](../roadmap/issue-AR-275-record-openclaw-native-skill-reads.md) | [detail](2026-08-22-7fcd828d-record-authorized-openclaw-skill-reads.md) |
| `60c72239` | 2026-08-22 | docs(decisions): authorize OpenClaw skill evidence | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-275](../roadmap/issue-AR-275-record-openclaw-native-skill-reads.md) | null |
| `74cc11fb` | 2026-08-22 | docs(ar119): checkpoint OpenClaw skill install | null | null |
| `c812d80e` | 2026-08-22 | docs(ar119): checkpoint OpenClaw finalization evidence | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-275](../roadmap/issue-AR-275-record-openclaw-native-skill-reads.md) | null |
| `7919f3fa` | 2026-08-22 | docs(ar119): retain OpenClaw restart review timeout | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-274](../roadmap/issue-AR-274-model-agnostic-structured-inference-profiles.md) | null |
| `d469d099` | 2026-08-22 | docs(ar119): record OpenClaw alias blocker | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-274](../roadmap/issue-AR-274-model-agnostic-structured-inference-profiles.md), [AR-275](../roadmap/issue-AR-275-record-openclaw-native-skill-reads.md) | null |
| `4bd18867` | 2026-08-22 | fix(inference): preserve planner repair diagnostics | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-274](../roadmap/issue-AR-274-model-agnostic-structured-inference-profiles.md), [AR-276](../roadmap/issue-AR-276-preserve-planner-repair-diagnostics.md) | [detail](2026-08-22-4bd18867-preserve-planner-repair-diagnostics.md) |
| `a0ff74d4` | 2026-08-22 | fix(openclaw): gate provider calls on agency preflight | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-276](../roadmap/issue-AR-276-preserve-planner-repair-diagnostics.md), [AR-277](../roadmap/issue-AR-277-gate-openclaw-provider-calls-on-agency-preflight.md) | [detail](2026-08-22-a0ff74d4-gate-openclaw-provider-on-preflight.md) |
| `1730abfb` | 2026-08-22 | docs(ar119): record OpenClaw input-gate blocker | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-276](../roadmap/issue-AR-276-preserve-planner-repair-diagnostics.md), [AR-277](../roadmap/issue-AR-277-gate-openclaw-provider-calls-on-agency-preflight.md) | [detail](2026-08-22-1730abfb-record-openclaw-input-gate-blocker.md) |
| `b4c27089` | 2026-08-22 | fix(openclaw): grant agency prompt injection | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-277](../roadmap/issue-AR-277-gate-openclaw-provider-calls-on-agency-preflight.md) | [detail](2026-08-22-b4c27089-grant-openclaw-prompt-injection.md) |
| `d9a1a7ce` | 2026-08-22 | fix(openclaw): preflight during prompt build | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-277](../roadmap/issue-AR-277-gate-openclaw-provider-calls-on-agency-preflight.md) | [detail](2026-08-22-d9a1a7ce-preflight-openclaw-during-prompt-build.md) |
| `dbf0a673` | 2026-08-22 | docs(roadmap): checkpoint OpenClaw prompt delivery | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-277](../roadmap/issue-AR-277-gate-openclaw-provider-calls-on-agency-preflight.md) | null |
| `4d2a75ab` | 2026-08-22 | docs(roadmap): checkpoint OpenClaw native skill proof | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-277](../roadmap/issue-AR-277-gate-openclaw-provider-calls-on-agency-preflight.md) | null |
| `0833884a` | 2026-08-22 | fix(openclaw): reinforce first-pass finalization | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-273](../roadmap/issue-AR-273-expose-openclaw-native-finalizer-tool.md), [AR-277](../roadmap/issue-AR-277-gate-openclaw-provider-calls-on-agency-preflight.md), [AR-278](../roadmap/issue-AR-278-keep-openclaw-finalization-first-pass.md) | [detail](2026-08-22-0833884a-reinforce-openclaw-first-pass-finalization.md) |
| `902afdb2` | 2026-08-22 | docs(roadmap): retain OpenClaw recovery timeout | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-277](../roadmap/issue-AR-277-gate-openclaw-provider-calls-on-agency-preflight.md), [AR-278](../roadmap/issue-AR-278-keep-openclaw-finalization-first-pass.md) | [detail](2026-08-22-902afdb2-retain-openclaw-recovery-timeout.md) |
| `34c84446` | 2026-08-22 | docs(roadmap): record OpenClaw first-pass proof | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-277](../roadmap/issue-AR-277-gate-openclaw-provider-calls-on-agency-preflight.md), [AR-278](../roadmap/issue-AR-278-keep-openclaw-finalization-first-pass.md) | [detail](2026-08-22-34c84446-record-openclaw-first-pass-proof.md) |
| `1ca46cc9` | 2026-08-22 | fix(openclaw): prevent silent finalizer delivery | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-279](../roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md) | null |
| `a8022a92` | 2026-08-22 | fix(openclaw): bind finalized outbound payloads | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-279](../roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md) | null |
| `13d80bd4` | 2026-08-22 | docs(roadmap): record OpenClaw payload repair install | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-279](../roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md) | null |
| `b1bd07c6` | 2026-08-22 | fix(openclaw): correlate native reset acknowledgements | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-279](../roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md) | null |
| `620b8f19` | 2026-08-23 | docs(roadmap): record OpenClaw Agency disable recovery | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-270](../roadmap/issue-AR-270-bind-openclaw-installed-copy-provenance.md), [AR-279](../roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md) | null |
| `59a9b409` | 2026-08-23 | docs(roadmap): record OpenClaw ordinary reply recovery | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-270](../roadmap/issue-AR-270-bind-openclaw-installed-copy-provenance.md), [AR-279](../roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md) | null |
| `da184b4f` | 2026-08-23 | fix(openclaw): refresh headers through awaited tool results | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-279](../roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md) | [detail](2026-08-23-da184b4f-refresh-openclaw-headers-through-awaited-tool-results.md) |
| `a9276e00` | 2026-08-23 | fix(openclaw): exclude alias-only completion evidence | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-279](../roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md) | [detail](2026-08-23-a9276e00-exclude-alias-only-openclaw-completion-evidence.md) |
| `71cb0975` | 2026-08-23 | fix(openclaw): carry preflight model through final gates | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-279](../roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md) | [detail](2026-08-23-71cb0975-carry-openclaw-preflight-model-through-final-gates.md) |
| `7a4a56e4` | 2026-08-23 | docs(roadmap): record OpenClaw status delivery | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-279](../roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md) | null |
| `e5ae8de1` | 2026-08-23 | fix(openclaw): correlate native tool result evidence | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-275](../roadmap/issue-AR-275-record-openclaw-native-skill-reads.md), [AR-279](../roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md) | [detail](2026-08-23-e5ae8de1-correlate-openclaw-native-tool-result-evidence.md) |
| `f96065e6` | 2026-08-23 | docs(roadmap): checkpoint OpenClaw tool correlation | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-275](../roadmap/issue-AR-275-record-openclaw-native-skill-reads.md), [AR-279](../roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md) | null |
| `8043ab43` | 2026-08-23 | docs(roadmap): record OpenClaw correlation install | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-275](../roadmap/issue-AR-275-record-openclaw-native-skill-reads.md), [AR-279](../roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md) | null |
| `79c4fdf9` | 2026-08-23 | docs(roadmap): record fresh OpenClaw status proof | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-275](../roadmap/issue-AR-275-record-openclaw-native-skill-reads.md), [AR-279](../roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md) | null |
| `c315551a` | 2026-08-23 | docs(roadmap): record OpenClaw tmux skill proof | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-275](../roadmap/issue-AR-275-record-openclaw-native-skill-reads.md), [AR-279](../roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md) | null |
| `00f06644` | 2026-08-23 | docs(roadmap): finalize OpenClaw live evidence | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-275](../roadmap/issue-AR-275-record-openclaw-native-skill-reads.md), [AR-279](../roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md) | null |
| `ef79579c` | 2026-08-23 | docs(roadmap): checkpoint Hermes Agency install | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md) | null |
| `21f2519d` | 2026-08-23 | fix(runtime): preserve native finalization attribution | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-275](../roadmap/issue-AR-275-record-openclaw-native-skill-reads.md), [AR-279](../roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md) | [detail](2026-08-23-21f2519d-preserve-native-finalization-attribution.md) |
| `d4d4b829` | 2026-08-23 | fix(openclaw): correlate sessionless reset acknowledgements | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-279](../roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md) | [detail](2026-08-23-d4d4b829-correlate-sessionless-openclaw-reset-acknowledgements.md) |
| `3e71247a` | 2026-08-23 | fix(openclaw): pass reset acknowledgements through both gates | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-279](../roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md) | [detail](2026-08-23-3e71247a-pass-openclaw-reset-acknowledgements-through-both-gates.md) |
| `675fb22a` | 2026-08-23 | diagnose(openclaw): trace native reset acknowledgement phases | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-279](../roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md) | [detail](2026-08-23-675fb22a-trace-openclaw-native-reset-acknowledgement-phases.md) |
| `efcd1e0f` | 2026-08-23 | docs(roadmap): checkpoint OpenClaw reset diagnostic install | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-279](../roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md) | null |
| `c671dd35` | 2026-08-23 | fix(openclaw): correlate reset lifecycle sessions | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-279](../roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md) | [detail](2026-08-23-c671dd35-correlate-openclaw-reset-lifecycle-sessions.md) |
| `cab9cf33` | 2026-08-23 | docs(roadmap): checkpoint OpenClaw reset lifecycle install | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-279](../roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md) | null |
| `4a0248cf` | 2026-08-24 | docs(roadmap): record OpenClaw reset and status delivery | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-279](../roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md) | null |
| `1d0026fd` | 2026-08-24 | docs(openclaw): retain native context overflow failure | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-279](../roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md) | null |
| `630fc148` | 2026-08-24 | fix(openclaw): deliver correlated native errors | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-279](../roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md) | [detail](2026-08-24-630fc148-deliver-correlated-openclaw-native-errors.md) |
| `1f21ee4d` | 2026-08-24 | docs(roadmap): record OpenClaw native error install | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-279](../roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md) | null |
| `a5a697bd` | 2026-08-24 | docs(roadmap): record fresh OpenClaw reset | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-279](../roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md) | null |
| `efe00ae9` | 2026-08-24 | docs(openclaw): retain stale skill header failure | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-279](../roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md) | null |
| `d7187e80` | 2026-08-24 | fix(openclaw): preserve refreshed headers through truncation | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-279](../roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md) | [detail](2026-08-24-d7187e80-preserve-openclaw-refreshed-headers-through-truncation.md) |
| `00d5ac27` | 2026-08-24 | docs(roadmap): checkpoint OpenClaw header framing install | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-279](../roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md) | [detail](2026-08-24-00d5ac27-checkpoint-openclaw-header-framing-install.md) |
| `5b29cb05` | 2026-08-24 | docs(roadmap): record OpenClaw live acceptance | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-279](../roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md) | [detail](2026-08-24-5b29cb05-record-openclaw-live-acceptance.md) |
| `c9edf468` | 2026-08-24 | docs(roadmap): checkpoint Hermes current runtime install | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md) | [detail](2026-08-24-c9edf468-checkpoint-hermes-current-runtime-install.md) |
| `0fec30ac` | 2026-08-24 | docs(roadmap): record dual-host live acceptance | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-280](../roadmap/issue-AR-280-exclude-hermes-internal-post-response-preflight.md) | [detail](2026-08-24-0fec30ac-record-dual-host-live-acceptance.md) |
| `f5b60fde` | 2026-08-24 | fix(native-child): bind host profiles and child identities | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-253](../roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-281](../roadmap/issue-AR-281-route-native-children-through-host-profiles.md) | [detail](2026-08-24-f5b60fde-bind-native-child-profiles-and-identities.md) |
| `d04d1d6b` | 2026-08-24 | fix(openclaw): deliver finalized native child results | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-279](../roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md), [AR-281](../roadmap/issue-AR-281-route-native-children-through-host-profiles.md), [AR-282](../roadmap/issue-AR-282-deliver-finalized-openclaw-child-announcements.md) | [detail](2026-08-24-d04d1d6b-deliver-finalized-openclaw-native-child-results.md) |
| `c7520586` | 2026-08-24 | fix(openclaw): validate native-child routing receipts | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-279](../roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md), [AR-281](../roadmap/issue-AR-281-route-native-children-through-host-profiles.md), [AR-282](../roadmap/issue-AR-282-deliver-finalized-openclaw-child-announcements.md) | [detail](2026-08-24-c7520586-validate-openclaw-native-child-routing-receipts.md) |
| `fbc619e7` | 2026-08-24 | docs(openclaw): checkpoint routing receipt install | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-279](../roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md), [AR-281](../roadmap/issue-AR-281-route-native-children-through-host-profiles.md), [AR-282](../roadmap/issue-AR-282-deliver-finalized-openclaw-child-announcements.md) | [detail](2026-08-24-fbc619e7-checkpoint-openclaw-routing-receipt-install.md) |
| `10ba4c84` | 2026-08-24 | fix(openclaw): forward child completion context hash | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-279](../roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md), [AR-281](../roadmap/issue-AR-281-route-native-children-through-host-profiles.md), [AR-282](../roadmap/issue-AR-282-deliver-finalized-openclaw-child-announcements.md) | [detail](2026-08-24-10ba4c84-forward-openclaw-child-completion-context-hash.md) |
| `933d9f4a` | 2026-08-24 | fix(openclaw): reconcile one-shot child terminal receipts | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-279](../roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md), [AR-281](../roadmap/issue-AR-281-route-native-children-through-host-profiles.md), [AR-282](../roadmap/issue-AR-282-deliver-finalized-openclaw-child-announcements.md) | [detail](2026-08-24-933d9f4a-reconcile-openclaw-one-shot-child-terminal-receipts.md) |
| `faba05bb` | 2026-08-24 | fix(routing): specialize contextual advisory turns | [AR-265](../roadmap/issue-AR-265-contextual-turn-classification.md) | [detail](2026-08-24-faba05bb-specialize-contextual-advisory-turns.md) |
| `f6da8cf9` | 2026-08-24 | docs(ar265): checkpoint contextual routing gates | [AR-265](../roadmap/issue-AR-265-contextual-turn-classification.md) | null |
| `ca517872` | 2026-08-24 | fix(routing): close contextual advisory grammar | [AR-265](../roadmap/issue-AR-265-contextual-turn-classification.md) | [detail](2026-08-24-ca517872-close-contextual-advisory-grammar.md) |
| `b2c34a6d` | 2026-08-24 | docs(ar265): checkpoint reviewed routing repair | [AR-265](../roadmap/issue-AR-265-contextual-turn-classification.md) | null |
| `9c1a18fc` | 2026-08-24 | docs(ar265): link tracker issue 317 | [AR-265](../roadmap/issue-AR-265-contextual-turn-classification.md) | null |
| `871e3eb7` | 2026-08-24 | docs(ar265): record pull request 318 | null | null |
| `48cd2383` | 2026-08-24 | fix(openclaw): gate child terminals on post-send receipts | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-279](../roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md), [AR-281](../roadmap/issue-AR-281-route-native-children-through-host-profiles.md), [AR-282](../roadmap/issue-AR-282-deliver-finalized-openclaw-child-announcements.md), [AR-283](../roadmap/issue-AR-283-persist-openclaw-child-terminals-after-delivery.md) | [detail](2026-08-24-48cd2383-gate-openclaw-child-terminals-on-post-send-receipts.md) |
| `90b852bd` | 2026-08-24 | Merge pull request #318 from Holeshot-Software-LLC/codex/ar265-contextual-turn-classification | null | null |
| `dfe8cb26` | 2026-08-24 | docs(ar265): record merged contextual routing canary | [AR-265](../roadmap/issue-AR-265-contextual-turn-classification.md) | null |
| `fc077039` | 2026-08-24 | Merge pull request #319 from Holeshot-Software-LLC/codex/ar265-live-evidence | [AR-265](../roadmap/issue-AR-265-contextual-turn-classification.md) | null |
| `5511300e` | 2026-08-24 | merge: integrate contextual routing with OpenClaw delivery | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-265](../roadmap/issue-AR-265-contextual-turn-classification.md), [AR-283](../roadmap/issue-AR-283-persist-openclaw-child-terminals-after-delivery.md) | [detail](2026-08-24-5511300e-integrate-contextual-routing-with-openclaw-delivery.md) |
| `bb048696` | 2026-08-24 | docs(openclaw): record post-send child acceptance | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-283](../roadmap/issue-AR-283-persist-openclaw-child-terminals-after-delivery.md) | null |
| `9629cc8e` | 2026-08-24 | docs(ar266): plan dense hybrid workforce recall | [AR-266](../roadmap/issue-AR-266-dense-hybrid-workforce-recall.md) | null |
| `3b1f9783` | 2026-08-24 | docs(roadmap): record provider fallback receipt ambiguity | [AR-284](../roadmap/issue-AR-284-disambiguate-provider-fallback-receipts.md) | null |
| `51c7a8ec` | 2026-08-24 | feat(workforce): add dense hybrid candidate recall | [AR-266](../roadmap/issue-AR-266-dense-hybrid-workforce-recall.md) | null |
| `fee0a116` | 2026-08-24 | docs(ar266): checkpoint verified hybrid recall | [AR-266](../roadmap/issue-AR-266-dense-hybrid-workforce-recall.md) | null |
| `9b51aa18` | 2026-08-24 | docs(openclaw): close merged install acceptance | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md), [AR-283](../roadmap/issue-AR-283-persist-openclaw-child-terminals-after-delivery.md) | null |
| `f2c472b5` | 2026-08-25 | docs(hermes): checkpoint current install and status | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md) | null |
| `c42018e1` | 2026-08-25 | docs(ar266): link tracker and pull request | [AR-266](../roadmap/issue-AR-266-dense-hybrid-workforce-recall.md) | null |
| `ddea73fb` | 2026-08-25 | docs(hermes): record substantive router acceptance | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md) | null |
| `042b5ed9` | 2026-08-25 | Merge pull request #321 from Holeshot-Software-LLC/codex/ar266-dense-hybrid-workforce-recall | [AR-266](../roadmap/issue-AR-266-dense-hybrid-workforce-recall.md) | null |
| `0ac2089e` | 2026-08-25 | docs(ar266): record merged hybrid recall | [AR-266](../roadmap/issue-AR-266-dense-hybrid-workforce-recall.md) | null |
| `4d2f8889` | 2026-08-25 | Merge pull request #322 from Holeshot-Software-LLC/codex/ar266-merge-ledger | [AR-266](../roadmap/issue-AR-266-dense-hybrid-workforce-recall.md) | null |
| `14ee6074` | 2026-08-25 | docs(hermes): preserve failed native-child proof | [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md), [AR-264](../roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md) | null |
| `382fb4d9` | 2026-08-25 | merge: integrate dense recall with current host runtime | [AR-266](../roadmap/issue-AR-266-dense-hybrid-workforce-recall.md), [AR-285](../roadmap/issue-AR-285-accept-openclaw-stopped-gateway-status.md) | [detail](2026-08-25-382fb4d9-integrate-dense-recall-with-current-host-runtime.md) |
| `2bea0c76` | 2026-08-25 | feat(workforce): configure bounded embedding dimensions | [AR-286](../roadmap/issue-AR-286-configure-bounded-embedding-dimensions.md) | [detail](2026-08-25-2bea0c76-configure-bounded-embedding-dimensions.md) |
| `fc5847e6` | 2026-08-25 | docs(ar266): checkpoint local retrieval smoke | [AR-266](../roadmap/issue-AR-266-dense-hybrid-workforce-recall.md), [AR-286](../roadmap/issue-AR-286-configure-bounded-embedding-dimensions.md) | null |
| `3cb2da6c` | 2026-08-25 | fix(hosts): bind hook timeouts to inference budgets | [AR-266](../roadmap/issue-AR-266-dense-hybrid-workforce-recall.md), [AR-287](../roadmap/issue-AR-287-bind-host-hook-timeouts-to-inference-budgets.md) | [detail](2026-08-25-3cb2da6c-bind-hook-timeouts-to-inference-budgets.md) |
| `7cea4c7c` | 2026-08-25 | docs(ar266): checkpoint Hermes timeout repair | [AR-266](../roadmap/issue-AR-266-dense-hybrid-workforce-recall.md), [AR-287](../roadmap/issue-AR-287-bind-host-hook-timeouts-to-inference-budgets.md) | null |
| `05024565` | 2026-08-25 | fix(hermes): expose native Agency finalizer | [AR-266](../roadmap/issue-AR-266-dense-hybrid-workforce-recall.md), [AR-288](../roadmap/issue-AR-288-expose-hermes-native-finalizer-tool.md) | [detail](2026-08-25-05024565-expose-hermes-native-finalizer.md) |
| `09d86e9f` | 2026-08-25 | docs(hermes): record native retrieval checkpoint | [AR-266](../roadmap/issue-AR-266-dense-hybrid-workforce-recall.md), [AR-288](../roadmap/issue-AR-288-expose-hermes-native-finalizer-tool.md) | null |
| `18ac01d0` | 2026-08-25 | docs(openclaw): record native retrieval smoke | [AR-266](../roadmap/issue-AR-266-dense-hybrid-workforce-recall.md) | null |
| `8d8a7d5e` | 2026-08-25 | feat(workforce): add shadow recall promotion gate | [AR-266](../roadmap/issue-AR-266-dense-hybrid-workforce-recall.md) | [detail](2026-08-25-8d8a7d5e-shadow-recall-promotion-gate.md) |
| `ca48c3fa` | 2026-08-25 | docs(ar266): record additive promotion evidence | [AR-266](../roadmap/issue-AR-266-dense-hybrid-workforce-recall.md) | [detail](2026-08-25-ca48c3fa-record-additive-promotion-evidence.md) |
| `e1d783ff` | 2026-08-25 | Merge pull request #323 from Holeshot-Software-LLC/codex/ar266-local-retrieval-smoke | [AR-266](../roadmap/issue-AR-266-dense-hybrid-workforce-recall.md) | null |
| `65a4ad76` | 2026-08-25 | docs(ar266): record merged additive recall | [AR-266](../roadmap/issue-AR-266-dense-hybrid-workforce-recall.md) | null |
| `04057072` | 2026-08-25 | Merge pull request #324 from Holeshot-Software-LLC/codex/ar266-merge-record | [AR-266](../roadmap/issue-AR-266-dense-hybrid-workforce-recall.md) | null |
| `95402d56` | 2026-08-25 | docs(ar289): plan native reranker transports | [AR-289](../roadmap/issue-AR-289-native-reranker-transports.md) | null |
| `cc41b21f` | 2026-08-25 | fix(codex): keep 0.149 opaque children unstaffed | [AR-180](../roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md), [AR-255](../roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md) | [detail](2026-08-25-cc41b21f-codex-0149-opaque-compatibility.md) |
| `03a01fda` | 2026-08-25 | feat(ar289): add native Jina reranker transport | [AR-289](../roadmap/issue-AR-289-native-reranker-transports.md) | null |
| `f6969862` | 2026-08-25 | docs(codex): record 0.149 hook activation gap | [AR-180](../roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md), [AR-255](../roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md) | [detail](2026-08-25-f6969862-codex-hook-activation-gap.md) |
| `04a23ebe` | 2026-08-25 | docs(codex): isolate 0.149 spawn hook gap | [AR-180](../roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md), [AR-255](../roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md) | [detail](2026-08-25-04a23ebe-isolate-codex-spawn-hook-gap.md) |
| `53350797` | 2026-08-25 | docs(codex): close 0.149 hook compatibility probe | [AR-180](../roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md), [AR-255](../roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md) | [detail](2026-08-25-53350797-close-codex-hook-compatibility-probe.md) |
| `4a71c0da` | 2026-08-25 | docs(ar290): plan guided setup | [AR-290](../roadmap/issue-AR-290-end-to-end-guided-setup.md) | null |
| `a19a1669` | 2026-08-25 | Merge pull request #325 from Holeshot-Software-LLC/codex/ar180-codex-0149-subagent-context | null | null |
| `21243e7e` | 2026-08-25 | feat(ar290): add guided setup journey | [AR-290](../roadmap/issue-AR-290-end-to-end-guided-setup.md) | [detail](2026-08-25-21243e7e-add-guided-setup-journey.md) |
| `4a72bbb1` | 2026-08-25 | fix(ar291): isolate smoke runtime pointers | [AR-291](../roadmap/issue-AR-291-isolate-smoke-runtime-pointers.md) | [detail](2026-08-25-4a72bbb1-isolate-smoke-runtime-pointers.md) |
| `af2f872f` | 2026-08-25 | fix(ar292): preserve setup activation degradation | [AR-292](../roadmap/issue-AR-292-classify-setup-activation-pending.md) | [detail](2026-08-25-af2f872f-preserve-setup-activation-degradation.md) |
| `ea5eca3c` | 2026-08-25 | docs(ar290): record installed setup acceptance | [AR-290](../roadmap/issue-AR-290-end-to-end-guided-setup.md) | [detail](2026-08-25-ea5eca3c-record-installed-setup-acceptance.md) |
| `bb610528` | 2026-08-25 | fix(ar293): allow safe inference profile config operations | [AR-293](../roadmap/issue-AR-293-safe-inference-profile-config-operations.md) | [detail](2026-08-25-bb610528-allow-safe-inference-profile-config-operations.md) |
| `7487b31b` | 2026-08-25 | merge: reconcile guided setup with current main | [AR-289](../roadmap/issue-AR-289-native-reranker-transports.md), [AR-290](../roadmap/issue-AR-290-end-to-end-guided-setup.md), [AR-291](../roadmap/issue-AR-291-isolate-smoke-runtime-pointers.md), [AR-292](../roadmap/issue-AR-292-classify-setup-activation-pending.md), [AR-293](../roadmap/issue-AR-293-safe-inference-profile-config-operations.md) | [detail](2026-08-25-7487b31b-reconcile-guided-setup-with-current-main.md) |
| `257fe30f` | 2026-08-25 | test(ar294): restore expanded configuration regressions | [AR-294](../roadmap/issue-AR-294-restore-expanded-configuration-regressions.md) | [detail](2026-08-25-257fe30f-restore-expanded-configuration-regressions.md) |
| `80a3095e` | 2026-08-25 | docs(ar290): record merged Windows and Linux handoff | [AR-290](../roadmap/issue-AR-290-end-to-end-guided-setup.md), [AR-294](../roadmap/issue-AR-294-restore-expanded-configuration-regressions.md) | [detail](2026-08-25-80a3095e-record-merged-windows-and-linux-handoff.md) |
| `80d89880` | 2026-08-25 | test(ar295): audit guided dashboard asset budget | [AR-295](../roadmap/issue-AR-295-audit-guided-dashboard-asset-budget.md), [AR-290](../roadmap/issue-AR-290-end-to-end-guided-setup.md) | [detail](2026-08-25-80d89880-audit-guided-dashboard-asset-budget.md) |
| `05291b0e` | 2026-08-25 | feat(ar296): project effective inference topology | [AR-296](../roadmap/issue-AR-296-project-effective-inference-topology.md), [AR-290](../roadmap/issue-AR-290-end-to-end-guided-setup.md) | [detail](2026-08-25-05291b0e-project-effective-inference-topology.md) |
| `0a5bdb06` | 2026-08-25 | docs(ar296): record installed inference topology | [AR-296](../roadmap/issue-AR-296-project-effective-inference-topology.md), [AR-290](../roadmap/issue-AR-290-end-to-end-guided-setup.md) | [detail](2026-08-25-0a5bdb06-record-installed-inference-topology.md) |
| `3023f055` | 2026-08-25 | feat(ar297): complete unattended bootstrap and prompt visibility | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-298](../roadmap/issue-AR-298-expose-complete-workforce-prompts.md) | [detail](2026-08-25-3023f055-complete-unattended-bootstrap-and-prompt-visibility.md) |
| `803e2c0f` | 2026-08-25 | docs(ar297): record Windows verification and Linux handoff | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-298](../roadmap/issue-AR-298-expose-complete-workforce-prompts.md) | [detail](2026-08-25-803e2c0f-record-windows-verification-and-linux-handoff.md) |
| `da7d883b` | 2026-08-26 | docs(tracker): link AR-289 through AR-298 | [AR-289](../roadmap/issue-AR-289-native-reranker-transports.md), [AR-290](../roadmap/issue-AR-290-end-to-end-guided-setup.md), [AR-291](../roadmap/issue-AR-291-isolate-smoke-runtime-pointers.md), [AR-292](../roadmap/issue-AR-292-classify-setup-activation-pending.md), [AR-293](../roadmap/issue-AR-293-safe-inference-profile-config-operations.md), [AR-294](../roadmap/issue-AR-294-restore-expanded-configuration-regressions.md), [AR-295](../roadmap/issue-AR-295-audit-guided-dashboard-asset-budget.md), [AR-296](../roadmap/issue-AR-296-project-effective-inference-topology.md), [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-298](../roadmap/issue-AR-298-expose-complete-workforce-prompts.md) | [detail](2026-08-26-da7d883b-link-ar289-through-ar298-trackers.md) |
| `0a23983a` | 2026-08-26 | Merge pull request #326 from Holeshot-Software-LLC/codex/ar290-guided-setup-readme | null | null |
| `c395bf4a` | 2026-08-26 | docs(ar297): checkpoint Linux production preflight | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `f58842b2` | 2026-08-26 | feat(ar299): allow local Ollama canary judges | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-299](../roadmap/issue-AR-299-local-ollama-canary-child-judge.md) | null |
| `2b16a88b` | 2026-08-26 | fix(ar300): bind production canary config | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-300](../roadmap/issue-AR-300-bind-explicit-install-config-to-managed-canary.md) | [detail](2026-08-26-2b16a88b-bind-production-canary-config.md) |
| `802a4b4f` | 2026-08-26 | docs(ar297): checkpoint Linux production evidence | [AR-290](../roadmap/issue-AR-290-end-to-end-guided-setup.md), [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-298](../roadmap/issue-AR-298-expose-complete-workforce-prompts.md), [AR-299](../roadmap/issue-AR-299-local-ollama-canary-child-judge.md), [AR-300](../roadmap/issue-AR-300-bind-explicit-install-config-to-managed-canary.md), [AR-301](../roadmap/issue-AR-301-private-systemd-dashboard-namespace.md) | null |
| `c8b97ee3` | 2026-08-26 | docs(ar297): checkpoint Linux verification gates | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-302](../roadmap/issue-AR-302-owner-private-local-verification.md) | null |
| `05c9485c` | 2026-08-26 | docs(ar297): record terminal Linux no-go | [AR-290](../roadmap/issue-AR-290-end-to-end-guided-setup.md), [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-298](../roadmap/issue-AR-298-expose-complete-workforce-prompts.md), [AR-299](../roadmap/issue-AR-299-local-ollama-canary-child-judge.md), [AR-300](../roadmap/issue-AR-300-bind-explicit-install-config-to-managed-canary.md), [AR-301](../roadmap/issue-AR-301-private-systemd-dashboard-namespace.md), [AR-302](../roadmap/issue-AR-302-owner-private-local-verification.md) | null |
| `14a4346c` | 2026-08-26 | fix(workforce): bound full-roster embedding recall | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-303](../roadmap/issue-AR-303-bound-full-roster-embedding-requests.md), [AR-304](../roadmap/issue-AR-304-preserve-recruiter-critic-validation-diagnostics.md) | null |
| `dbd3eda9` | 2026-08-26 | fix(workforce): reserve embedding response nodes | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-303](../roadmap/issue-AR-303-bound-full-roster-embedding-requests.md) | null |
| `5acfbf41` | 2026-08-26 | fix(workforce): clarify recruiter repair contracts | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-304](../roadmap/issue-AR-304-preserve-recruiter-critic-validation-diagnostics.md) | null |
| `e10284ec` | 2026-08-26 | docs(ar297): record bounded recall live verdict | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-303](../roadmap/issue-AR-303-bound-full-roster-embedding-requests.md), [AR-304](../roadmap/issue-AR-304-preserve-recruiter-critic-validation-diagnostics.md) | [ADR-0175](../decisions/0175-batch-complete-embedding-input-sets.md) |
| `bb6bd74f` | 2026-08-26 | fix(workforce): ignore false novelty sentinels | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-305](../roadmap/issue-AR-305-normalize-planner-novelty-absence.md) | null |
| `bd4e7f75` | 2026-08-26 | fix(workforce): bind strict critic semantics | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-305](../roadmap/issue-AR-305-normalize-planner-novelty-absence.md), [AR-306](../roadmap/issue-AR-306-bind-strict-critic-semantics.md) | null |
| `3e188c9f` | 2026-08-26 | fix(workforce): clarify critic approval contract | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-306](../roadmap/issue-AR-306-bind-strict-critic-semantics.md) | null |
| `926aef81` | 2026-08-26 | docs(ar297): record direct workforce acceptance | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-305](../roadmap/issue-AR-305-normalize-planner-novelty-absence.md), [AR-306](../roadmap/issue-AR-306-bind-strict-critic-semantics.md) | null |
| `5c86aae4` | 2026-08-26 | fix(linux): harden service and verification namespaces | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-301](../roadmap/issue-AR-301-private-systemd-dashboard-namespace.md), [AR-302](../roadmap/issue-AR-302-owner-private-local-verification.md) | [detail](2026-08-26-5c86aae4-harden-linux-service-and-verification-namespaces.md) |
| `2a9dc984` | 2026-08-26 | fix(release): admit cooperative sdist modes | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-302](../roadmap/issue-AR-302-owner-private-local-verification.md) | [detail](2026-08-26-2a9dc984-admit-cooperative-sdist-modes.md) |
| `b54a9f1e` | 2026-08-26 | docs(ar297): checkpoint exact Linux installs | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-301](../roadmap/issue-AR-301-private-systemd-dashboard-namespace.md), [AR-302](../roadmap/issue-AR-302-owner-private-local-verification.md) | null |
| `a13e3cf8` | 2026-08-26 | fix(canary): project declared inference credentials | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-300](../roadmap/issue-AR-300-bind-explicit-install-config-to-managed-canary.md), [AR-307](../roadmap/issue-AR-307-project-canary-inference-credentials.md) | [ADR-0178](../decisions/0178-project-config-declared-credentials-into-tool-reduced-canaries.md) |
| `389fbfdf` | 2026-08-26 | docs(ar297): checkpoint post-fix container evidence | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-307](../roadmap/issue-AR-307-project-canary-inference-credentials.md) | null |
| `33f71975` | 2026-08-26 | fix(workforce): bind activation canary delivery | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-308](../roadmap/issue-AR-308-bind-activation-canary-delegation.md) | [ADR-0118](../decisions/0118-require-inference-owned-staffing.md), [ADR-0173](../decisions/0173-complete-production-container-installation-with-managed-activation.md) |
| `105ce021` | 2026-08-26 | test(conformance): bind activation delivery mutation | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-308](../roadmap/issue-AR-308-bind-activation-canary-delegation.md) | [ADR-0118](../decisions/0118-require-inference-owned-staffing.md), [ADR-0173](../decisions/0173-complete-production-container-installation-with-managed-activation.md) |
| `6c01811a` | 2026-08-26 | docs(ar309): checkpoint codex 0.149 proof gap | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-309](../roadmap/issue-AR-309-restore-codex-0149-activation-proof.md) | [ADR-0156](../decisions/0156-host-artifacts-prove-native-child-delivery.md), [ADR-0173](../decisions/0173-complete-production-container-installation-with-managed-activation.md) |
| `907436e2` | 2026-08-26 | docs(ar309): rule out stable codex delegation | null | null |
| `3930eb56` | 2026-08-26 | fix(ar309): prove codex subagent start delivery | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-309](../roadmap/issue-AR-309-restore-codex-0149-activation-proof.md) | [ADR-0179](../decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md) |
| `131f57e5` | 2026-08-26 | docs(ar297): persist Linux GO recovery ledger | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `6bf3b5ec` | 2026-08-26 | fix(ar310): require managed canary Store | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-309](../roadmap/issue-AR-309-restore-codex-0149-activation-proof.md), [AR-310](../roadmap/issue-AR-310-require-managed-codex-canary-store.md) | [ADR-0173](../decisions/0173-complete-production-container-installation-with-managed-activation.md), [ADR-0179](../decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md) |
| `ee357a27` | 2026-08-26 | fix(ar311): inject exact Codex canary plan | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-309](../roadmap/issue-AR-309-restore-codex-0149-activation-proof.md), [AR-310](../roadmap/issue-AR-310-require-managed-codex-canary-store.md), [AR-311](../roadmap/issue-AR-311-inject-exact-codex-canary-native-plan.md) | [ADR-0173](../decisions/0173-complete-production-container-installation-with-managed-activation.md), [ADR-0179](../decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md) |
| `0accd39e` | 2026-08-26 | fix(codex): bind exact host artifact role shape | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-309](../roadmap/issue-AR-309-restore-codex-0149-activation-proof.md), [AR-311](../roadmap/issue-AR-311-inject-exact-codex-canary-native-plan.md), [AR-312](../roadmap/issue-AR-312-validate-explicit-production-config.md), [AR-313](../roadmap/issue-AR-313-trust-normal-umask-codex-artifacts.md), [AR-314](../roadmap/issue-AR-314-bind-codex-default-canary-role.md) | [detail](2026-08-26-0accd39e-bind-exact-host-artifact-role-shape.md) |
| `e718dca0` | 2026-08-26 | docs(ar297): record exact Codex staffing abstention | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `4b346af8` | 2026-08-26 | fix(ar315): project Codex canary install home | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-309](../roadmap/issue-AR-309-restore-codex-0149-activation-proof.md), [AR-315](../roadmap/issue-AR-315-project-codex-canary-install-home.md) | [detail](2026-08-26-4b346af8-project-codex-canary-install-home.md) |
| `2fa5013f` | 2026-08-26 | docs(ar297): checkpoint exact Codex child judge blocker | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-315](../roadmap/issue-AR-315-project-codex-canary-install-home.md) | [detail](2026-08-26-2fa5013f-checkpoint-exact-codex-child-judge-blocker.md) |
| `6a363bd1` | 2026-08-26 | docs(ar316): record Ollama judge context blocker | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-299](../roadmap/issue-AR-299-local-ollama-canary-child-judge.md), [AR-316](../roadmap/issue-AR-316-size-ollama-selector-judge-context.md) | null |
| `61ee2428` | 2026-08-26 | feat(ar317): admit LiteLLM canary judge aliases | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-316](../roadmap/issue-AR-316-size-ollama-selector-judge-context.md), [AR-317](../roadmap/issue-AR-317-route-agency-inference-through-litellm-aliases.md) | [detail](2026-08-26-61ee2428-admit-litellm-canary-judge-aliases.md) |
| `c283efac` | 2026-08-26 | docs(ar317): checkpoint LiteLLM alias evidence | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-317](../roadmap/issue-AR-317-route-agency-inference-through-litellm-aliases.md) | null |
| `860790ff` | 2026-08-26 | docs(ar317): bind exact LiteLLM-only config | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-317](../roadmap/issue-AR-317-route-agency-inference-through-litellm-aliases.md) | null |
| `bd990c4a` | 2026-08-26 | docs(ar297): checkpoint exact LiteLLM artifacts | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `4d6d4930` | 2026-08-26 | docs(ar318): record Codex activation wait race | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-318](../roadmap/issue-AR-318-bound-codex-activation-child-wait.md) | [ADR-0182](../decisions/0182-bound-codex-activation-child-wait.md) |
| `42642aab` | 2026-08-26 | fix(ar318): bound Codex activation child wait | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-318](../roadmap/issue-AR-318-bound-codex-activation-child-wait.md) | [ADR-0182](../decisions/0182-bound-codex-activation-child-wait.md) |
| `542e2dd2` | 2026-08-26 | docs(ar318): checkpoint rebuilt Codex candidate | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-318](../roadmap/issue-AR-318-bound-codex-activation-child-wait.md) | [ADR-0182](../decisions/0182-bound-codex-activation-child-wait.md) |
| `15fb6dd5` | 2026-08-26 | docs(ar319): record pinned judge timeout conflict | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-319](../roadmap/issue-AR-319-honor-pinned-canary-judge-timeout.md) | [ADR-0183](../decisions/0183-honor-pinned-canary-judge-timeout.md) |
| `785070f6` | 2026-08-26 | fix(ar319): honor pinned canary judge timeout | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-319](../roadmap/issue-AR-319-honor-pinned-canary-judge-timeout.md) | [ADR-0183](../decisions/0183-honor-pinned-canary-judge-timeout.md) |
| `633b0e84` | 2026-08-26 | docs(ar319): checkpoint rebuilt timeout candidate | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-319](../roadmap/issue-AR-319-honor-pinned-canary-judge-timeout.md) | [ADR-0183](../decisions/0183-honor-pinned-canary-judge-timeout.md) |
| `761a279d` | 2026-08-26 | docs(ar320): record full child staffing wait gap | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-320](../roadmap/issue-AR-320-bound-codex-wait-to-full-child-staffing.md) | [ADR-0184](../decisions/0184-bound-codex-wait-to-full-child-staffing.md) |
| `1989d111` | 2026-08-26 | fix(ar320): cover full child staffing wait | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-320](../roadmap/issue-AR-320-bound-codex-wait-to-full-child-staffing.md) | [ADR-0184](../decisions/0184-bound-codex-wait-to-full-child-staffing.md) |
| `74794970` | 2026-08-26 | docs(ar320): checkpoint full staffing wait repair | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-320](../roadmap/issue-AR-320-bound-codex-wait-to-full-child-staffing.md) | [ADR-0184](../decisions/0184-bound-codex-wait-to-full-child-staffing.md) |
| `04b6b1a5` | 2026-08-26 | docs(ar320): checkpoint exact staffing candidate | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-320](../roadmap/issue-AR-320-bound-codex-wait-to-full-child-staffing.md) | [ADR-0184](../decisions/0184-bound-codex-wait-to-full-child-staffing.md) |
| `94741593` | 2026-08-26 | docs(ar321): record free child judge blocker | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-317](../roadmap/issue-AR-317-route-agency-inference-through-litellm-aliases.md), [AR-320](../roadmap/issue-AR-320-bound-codex-wait-to-full-child-staffing.md), [AR-321](../roadmap/issue-AR-321-select-reliable-free-litellm-child-judge.md) | [ADR-0181](../decisions/0181-use-litellm-aliases-as-host-inference-control-plane.md) |
| `f8348ab0` | 2026-08-27 | docs(ar321): checkpoint free judge candidates | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-321](../roadmap/issue-AR-321-select-reliable-free-litellm-child-judge.md) | [ADR-0181](../decisions/0181-use-litellm-aliases-as-host-inference-control-plane.md) |
| `cc24d403` | 2026-08-27 | docs(ar321): record Ministral judge rejection | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-321](../roadmap/issue-AR-321-select-reliable-free-litellm-child-judge.md) | [ADR-0181](../decisions/0181-use-litellm-aliases-as-host-inference-control-plane.md) |
| `e631d776` | 2026-08-27 | docs(ar321): checkpoint Granite judge candidate | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-321](../roadmap/issue-AR-321-select-reliable-free-litellm-child-judge.md) | [ADR-0181](../decisions/0181-use-litellm-aliases-as-host-inference-control-plane.md) |
| `0baeb22f` | 2026-08-27 | docs(ar321): checkpoint Qwen 2.5 judge candidate | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-321](../roadmap/issue-AR-321-select-reliable-free-litellm-child-judge.md) | [ADR-0181](../decisions/0181-use-litellm-aliases-as-host-inference-control-plane.md) |
| `ecac503c` | 2026-08-27 | docs(ar321): checkpoint Llama judge candidate | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-321](../roadmap/issue-AR-321-select-reliable-free-litellm-child-judge.md) | [ADR-0181](../decisions/0181-use-litellm-aliases-as-host-inference-control-plane.md) |
| `b89a637f` | 2026-08-27 | docs(ar321): checkpoint schema-bound Mistral | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-321](../roadmap/issue-AR-321-select-reliable-free-litellm-child-judge.md) | [ADR-0181](../decisions/0181-use-litellm-aliases-as-host-inference-control-plane.md) |
| `bed213cd` | 2026-08-27 | docs(ar321): restore recovery capsule bound | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-321](../roadmap/issue-AR-321-select-reliable-free-litellm-child-judge.md) | null |
| `8859bfc3` | 2026-08-27 | docs(ar321): checkpoint GPT-OSS judge candidate | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-321](../roadmap/issue-AR-321-select-reliable-free-litellm-child-judge.md) | [ADR-0181](../decisions/0181-use-litellm-aliases-as-host-inference-control-plane.md) |
| `0f086498` | 2026-08-27 | docs(ar321): checkpoint GPT-OSS reasoning repair | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-321](../roadmap/issue-AR-321-select-reliable-free-litellm-child-judge.md) | [ADR-0181](../decisions/0181-use-litellm-aliases-as-host-inference-control-plane.md) |
| `17decade` | 2026-08-27 | docs(ar321): checkpoint Mistral repeat candidate | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-321](../roadmap/issue-AR-321-select-reliable-free-litellm-child-judge.md) | [ADR-0181](../decisions/0181-use-litellm-aliases-as-host-inference-control-plane.md) |
| `d05a13ae` | 2026-08-27 | docs(ar321): promote schema-bound Mistral judge | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-321](../roadmap/issue-AR-321-select-reliable-free-litellm-child-judge.md) | [ADR-0181](../decisions/0181-use-litellm-aliases-as-host-inference-control-plane.md), [ADR-0185](../decisions/0185-enforce-child-judge-schema-at-litellm-alias.md) |
| `a5c1ad53` | 2026-08-27 | fix(codex): bind canary children by request digest | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-310](../roadmap/issue-AR-310-require-managed-codex-canary-store.md), [AR-314](../roadmap/issue-AR-314-bind-codex-default-canary-role.md), [AR-322](../roadmap/issue-AR-322-bind-codex-child-session-to-canary-parent.md), [AR-323](../roadmap/issue-AR-323-remove-stale-ledger-schema-literals.md) | [detail](2026-08-27-a5c1ad53-bind-codex-canary-child-by-request-digest.md) |
| `77cd30ae` | 2026-08-27 | docs(ar297): checkpoint Codex child correlation repair | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-321](../roadmap/issue-AR-321-select-reliable-free-litellm-child-judge.md), [AR-322](../roadmap/issue-AR-322-bind-codex-child-session-to-canary-parent.md) | null |
| `70516542` | 2026-08-27 | docs(ar297): checkpoint exact AR-322 artifacts | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-322](../roadmap/issue-AR-322-bind-codex-child-session-to-canary-parent.md) | null |
| `66b889a2` | 2026-08-27 | fix(codex): bind canary child through host lineage | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-310](../roadmap/issue-AR-310-require-managed-codex-canary-store.md), [AR-313](../roadmap/issue-AR-313-trust-normal-umask-codex-artifacts.md), [AR-314](../roadmap/issue-AR-314-bind-codex-default-canary-role.md), [AR-322](../roadmap/issue-AR-322-bind-codex-child-session-to-canary-parent.md), [AR-324](../roadmap/issue-AR-324-bind-codex-canary-child-through-host-lineage.md) | [detail](2026-08-27-66b889a2-bind-codex-canary-child-through-host-lineage.md) |
| `b7f9d324` | 2026-08-27 | docs(ar297): checkpoint Codex host-lineage repair | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-324](../roadmap/issue-AR-324-bind-codex-canary-child-through-host-lineage.md) | null |
| `34f41532` | 2026-08-27 | fix(codex): separate hook parent and child identities | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-310](../roadmap/issue-AR-310-require-managed-codex-canary-store.md), [AR-313](../roadmap/issue-AR-313-trust-normal-umask-codex-artifacts.md), [AR-314](../roadmap/issue-AR-314-bind-codex-default-canary-role.md), [AR-322](../roadmap/issue-AR-322-bind-codex-child-session-to-canary-parent.md), [AR-324](../roadmap/issue-AR-324-bind-codex-canary-child-through-host-lineage.md) | [detail](2026-08-27-34f41532-separate-codex-hook-parent-and-child-identities.md) |
| `7f760a59` | 2026-08-27 | docs(ar297): checkpoint separate Codex hook identities | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-324](../roadmap/issue-AR-324-bind-codex-canary-child-through-host-lineage.md) | null |
| `e15d841f` | 2026-08-27 | docs(ar297): checkpoint exact child compatibility blocker | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-321](../roadmap/issue-AR-321-select-reliable-free-litellm-child-judge.md), [AR-324](../roadmap/issue-AR-324-bind-codex-canary-child-through-host-lineage.md) | null |
| `4902da2e` | 2026-08-27 | docs(ar321): checkpoint exact stable over-selection | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-321](../roadmap/issue-AR-321-select-reliable-free-litellm-child-judge.md) | null |
| `21c735d8` | 2026-08-27 | docs(ar321): close deterministic Mistral retry | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-321](../roadmap/issue-AR-321-select-reliable-free-litellm-child-judge.md) | null |
| `c805b910` | 2026-08-27 | docs(ar321): checkpoint compatibility repair abstention | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-321](../roadmap/issue-AR-321-select-reliable-free-litellm-child-judge.md) | null |
| `da906bfc` | 2026-08-27 | docs(ar321): close same-model judge repairs | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-321](../roadmap/issue-AR-321-select-reliable-free-litellm-child-judge.md) | null |
| `a0acac1a` | 2026-08-27 | docs(ar321): reject Gemma child judge trial | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-321](../roadmap/issue-AR-321-select-reliable-free-litellm-child-judge.md) | null |
| `c72e99b2` | 2026-08-27 | docs(ar321): checkpoint Qwen judge candidate | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-321](../roadmap/issue-AR-321-select-reliable-free-litellm-child-judge.md) | null |
| `1bb2c659` | 2026-08-27 | docs(ar321): promote exact Qwen judge | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-321](../roadmap/issue-AR-321-select-reliable-free-litellm-child-judge.md) | null |
| `5025390e` | 2026-08-27 | docs(ar321): prove stable Qwen judge route | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-321](../roadmap/issue-AR-321-select-reliable-free-litellm-child-judge.md) | null |
| `56de576c` | 2026-08-27 | docs(ar297): checkpoint clean Qwen Codex container | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `ced83631` | 2026-08-27 | fix(codex): reconcile canary callback order | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-321](../roadmap/issue-AR-321-select-reliable-free-litellm-child-judge.md), [AR-324](../roadmap/issue-AR-324-bind-codex-canary-child-through-host-lineage.md), [AR-325](../roadmap/issue-AR-325-restore-codex-first-complete-callback-reconciliation.md) | [detail](2026-08-27-ced83631-reconcile-codex-canary-callback-order.md) |
| `8eb18009` | 2026-08-27 | docs(roadmap): record terminal Codex collection gate | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-325](../roadmap/issue-AR-325-restore-codex-first-complete-callback-reconciliation.md), [AR-326](../roadmap/issue-AR-326-admit-terminal-codex-host-artifact-collection.md) | [detail](2026-08-27-8eb18009-record-terminal-codex-collection-gate.md) |
| `592f4a6b` | 2026-08-27 | fix(codex): collect accepted terminal canary artifacts | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-326](../roadmap/issue-AR-326-admit-terminal-codex-host-artifact-collection.md) | [detail](2026-08-27-592f4a6b-collect-accepted-terminal-canary-artifacts.md) |
| `08264555` | 2026-08-27 | docs(ar297): checkpoint exact terminal collector candidate | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-326](../roadmap/issue-AR-326-admit-terminal-codex-host-artifact-collection.md) | [detail](2026-08-27-08264555-checkpoint-exact-terminal-collector-candidate.md) |
| `9061733d` | 2026-08-27 | docs(ar297): record bounded Codex timeout | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-326](../roadmap/issue-AR-326-admit-terminal-codex-host-artifact-collection.md) | [detail](2026-08-27-9061733d-record-bounded-codex-timeout.md) |
| `70ff4ec4` | 2026-08-27 | docs(ar327): record append-only receipt blocker | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-326](../roadmap/issue-AR-326-admit-terminal-codex-host-artifact-collection.md), [AR-327](../roadmap/issue-AR-327-replay-codex-delivery-receipts-across-append-only-completion.md) | [ADR-0190](../decisions/0190-bind-codex-receipt-replay-to-an-exact-append-only-prefix.md) |
| `636ce34b` | 2026-08-27 | fix(codex): replay immutable delivery prefixes | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-327](../roadmap/issue-AR-327-replay-codex-delivery-receipts-across-append-only-completion.md) | [detail](2026-08-27-636ce34b-replay-immutable-codex-delivery-prefixes.md) |
| `61d29b65` | 2026-08-27 | docs(ar327): prove exact Qwen2 source replay | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-326](../roadmap/issue-AR-326-admit-terminal-codex-host-artifact-collection.md), [AR-327](../roadmap/issue-AR-327-replay-codex-delivery-receipts-across-append-only-completion.md) | [ADR-0190](../decisions/0190-bind-codex-receipt-replay-to-an-exact-append-only-prefix.md) |
| `68db5076` | 2026-08-27 | docs(ar297): checkpoint exact AR327 candidate | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-327](../roadmap/issue-AR-327-replay-codex-delivery-receipts-across-append-only-completion.md) | [detail](2026-08-27-68db5076-checkpoint-exact-ar327-candidate.md) |
| `4b6890ae` | 2026-08-27 | docs(ar297): prove exact Codex production install | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-326](../roadmap/issue-AR-326-admit-terminal-codex-host-artifact-collection.md), [AR-327](../roadmap/issue-AR-327-replay-codex-delivery-receipts-across-append-only-completion.md) | [detail](2026-08-27-4b6890ae-prove-exact-codex-production-install.md) |
| `5e1decf8` | 2026-08-27 | docs(ar297): prove exact multi-harness installs | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | [detail](2026-08-27-5e1decf8-prove-exact-multi-harness-installs.md) |
| `11dcced4` | 2026-08-27 | docs(ar297): correct OpenClaw generation alias | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `e56d1f4b` | 2026-08-27 | docs(ar297): diagnose Hermes tool transport | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | [detail](2026-08-27-e56d1f4b-diagnose-hermes-tool-transport.md) |
| `9a7a99bf` | 2026-08-27 | docs(ar297): isolate Hermes tool admission gap | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | [detail](2026-08-27-9a7a99bf-isolate-hermes-tool-admission-gap.md) |
| `831ac8f1` | 2026-08-27 | docs(ar297): reject unreliable Hermes Mistral route | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | [detail](2026-08-27-831ac8f1-reject-unreliable-hermes-mistral-route.md) |
| `3fdb4218` | 2026-08-27 | docs(ar297): checkpoint ordinary harness diagnostics | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | [detail](2026-08-27-3fdb4218-checkpoint-ordinary-harness-diagnostics.md) |
| `c5749a29` | 2026-08-27 | docs(ar297): prove ordinary Codex completion | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | [detail](2026-08-27-c5749a29-prove-ordinary-codex-completion.md) |
| `6d32c459` | 2026-08-27 | docs(ar297): prove exact host dashboard install | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | [detail](2026-08-27-6d32c459-prove-exact-host-dashboard-install.md) |
| `c914cc46` | 2026-08-27 | docs(ar297): close named repository gates | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | [detail](2026-08-27-c914cc46-close-named-repository-gates.md) |
| `606ce9e5` | 2026-08-27 | docs(ar297): checkpoint refreshed Claude preflight | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | [detail](2026-08-27-606ce9e5-checkpoint-refreshed-claude-preflight.md) |
| `609e2dd6` | 2026-08-27 | docs(ar297): retain refreshed Claude OAuth failure | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `abb79e1f` | 2026-08-27 | docs(ar297): checkpoint approved harness aliases | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `e23f45c6` | 2026-08-27 | docs(ar297): retain Hermes tool visibility repair | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `5d478c33` | 2026-08-27 | fix(hermes): replay accepted native finalizer result | [AR-288](../roadmap/issue-AR-288-expose-hermes-native-finalizer-tool.md), [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `aa834796` | 2026-08-27 | docs(ar297): prove exact accepted replay installs | [AR-288](../roadmap/issue-AR-288-expose-hermes-native-finalizer-tool.md), [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `f88369bc` | 2026-08-27 | docs(ar297): seal current Hermes ordinary proof | [AR-288](../roadmap/issue-AR-288-expose-hermes-native-finalizer-tool.md), [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `65ef42f2` | 2026-08-27 | docs(ar297): prove current Codex ordinary loading | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `bd9966d3` | 2026-08-27 | docs(ar297): prove current OpenClaw ordinary loading | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `de991dc0` | 2026-08-27 | fix(installer): seal Hermes bytecode cache [AR-328] | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-328](../roadmap/issue-AR-328-seal-hermes-install-tree.md) | [ADR-0191](../decisions/0191-seal-managed-hermes-python-bundles.md) |
| `97fc64c0` | 2026-08-27 | docs(ar297): checkpoint exact AR328 candidate | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-328](../roadmap/issue-AR-328-seal-hermes-install-tree.md) | [ADR-0191](../decisions/0191-seal-managed-hermes-python-bundles.md) |
| `d2ae9b57` | 2026-08-27 | docs(ar297): checkpoint final non-Codex installs | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-328](../roadmap/issue-AR-328-seal-hermes-install-tree.md) | [ADR-0191](../decisions/0191-seal-managed-hermes-python-bundles.md) |
| `4bc8bd97` | 2026-08-27 | docs(ar297): prove four final candidate installs | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | [ADR-0173](../decisions/0173-complete-production-container-installation-with-managed-activation.md), [ADR-0191](../decisions/0191-seal-managed-hermes-python-bundles.md) |
| `14cab69b` | 2026-08-27 | docs(ar297): checkpoint final ordinary rows | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `3ea0886b` | 2026-08-27 | docs(ar297): prove final OpenClaw ordinary loading | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `b998ad22` | 2026-08-27 | docs(ar297): prove final host and repository gates | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `b3238fb2` | 2026-08-27 | docs(ar297): prove final Claude ordinary loading | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `e48f08be` | 2026-08-27 | docs(ar297): issue Linux GO and record teardown | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `3155fc5f` | 2026-08-27 | fix(smoke): unseal disposable Hermes guard [AR-328] | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-328](../roadmap/issue-AR-328-seal-hermes-install-tree.md) | [detail](2026-08-27-3155fc5f-unseal-disposable-hermes-guard.md) |
| `0ef2e8cb` | 2026-08-27 | docs(ar297): prove repaired distribution smoke | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-328](../roadmap/issue-AR-328-seal-hermes-install-tree.md) | null |
| `591aad20` | 2026-08-27 | Merge pull request #337 from Holeshot-Software-LLC/codex/ar297-production-container-live-evidence | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-328](../roadmap/issue-AR-328-seal-hermes-install-tree.md) | null |
| `e5e5e7e4` | 2026-08-27 | docs(ar297): record merged Linux delivery | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-328](../roadmap/issue-AR-328-seal-hermes-install-tree.md) | null |
| `87231198` | 2026-08-28 | Merge pull request #338 from Holeshot-Software-LLC/codex/ar297-publish-closure | null | null |
| `aead84d0` | 2026-08-28 | fix(codex): freeze inspector bootstrap as persistent input [AR-329] | [AR-329](../roadmap/issue-AR-329-freeze-codex-inspector-bootstrap-as-persistent-input.md) | null |
| `c1b4e713` | 2026-08-28 | docs(ar297): checkpoint attended Codex trust gate | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-329](../roadmap/issue-AR-329-freeze-codex-inspector-bootstrap-as-persistent-input.md) | null |
| `58301299` | 2026-08-28 | docs(ar297): bound trust-gate capsule | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-329](../roadmap/issue-AR-329-freeze-codex-inspector-bootstrap-as-persistent-input.md) | null |
| `522102f7` | 2026-08-28 | fix(codex): support 0.150 collaboration rollouts [AR-330] | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-313](../roadmap/issue-AR-313-trust-normal-umask-codex-artifacts.md), [AR-330](../roadmap/issue-AR-330-support-codex-0150-collaboration-rollouts.md) | [detail](2026-08-28-522102f7-support-codex-0150-collaboration-rollouts.md) |
| `f6870aa6` | 2026-08-28 | fix(codex): admit 0.150 child lineage [AR-330] | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-330](../roadmap/issue-AR-330-support-codex-0150-collaboration-rollouts.md) | [detail](2026-08-28-f6870aa6-admit-codex-0150-child-lineage.md) |
| `af8ffbdd` | 2026-08-28 | docs(ar297): checkpoint repaired Codex host canary | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md), [AR-330](../roadmap/issue-AR-330-support-codex-0150-collaboration-rollouts.md) | null |
| `f53b4fd4` | 2026-08-28 | docs(ar297): prove ordinary Codex host loading | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `9ba5bce0` | 2026-08-28 | docs(ar297): prove ordinary Claude host loading | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `3982e05c` | 2026-08-28 | docs(ar297): checkpoint Hermes host negative | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `2c52e99a` | 2026-08-28 | docs(ar297): retain second Hermes host negative | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `01598467` | 2026-08-28 | docs(ar297): prove scoped Hermes host loading | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `6d8c97d0` | 2026-08-28 | docs(ar297): prove ordinary OpenClaw host loading | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `a4db8468` | 2026-08-28 | docs(ar297): prove authenticated host dashboard | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `43b67657` | 2026-08-28 | docs(ar297): record final repository gates | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `988a8f0c` | 2026-08-28 | docs(ar297): record final parity audit | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `dc8bbde6` | 2026-08-28 | Merge pull request #339 from Holeshot-Software-LLC/codex/ar297-host-live-closure | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `7b7fd6a7` | 2026-08-28 | docs(ar297): record merged-main host installation | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `1e6f5d07` | 2026-08-28 | Merge pull request #340 from Holeshot-Software-LLC/codex/ar297-main-install-proof | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `69daa994` | 2026-08-28 | docs(ar297): checkpoint manual Codex credential repair | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `3b4a0b5c` | 2026-08-28 | docs(ar297): record manual generation route comparison | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `508bf3ce` | 2026-08-28 | docs(ar297): compact manual route checkpoint | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `c3387faa` | 2026-08-28 | docs(ar297): checkpoint preflight latency screen | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `6ef1ea24` | 2026-08-28 | docs(ar297): checkpoint subscription model screen | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `87e600f9` | 2026-08-28 | docs(ar297): checkpoint Spark and fallback screen | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `09233ec4` | 2026-08-28 | docs(ar297): checkpoint approved embedding candidate | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `ad06379f` | 2026-08-28 | docs(ar297): checkpoint fast local embedding proof | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `a4ba51bd` | 2026-08-28 | docs(ar297): retire Spark and bound route benchmark | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `e7695c27` | 2026-08-28 | docs(ar297): freeze per-stage model benchmark | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `4c2721f8` | 2026-08-28 | docs(ar297): checkpoint OpenAI stage matrix | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `2faf4f8e` | 2026-08-28 | docs(ar297): checkpoint MiniMax stage matrix | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `773e9089` | 2026-08-28 | docs(ar297): checkpoint ZAI stage matrix | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `055009af` | 2026-08-28 | docs(ar297): checkpoint local stage matrix | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `1984791d` | 2026-08-28 | docs(ar297): record stage confirmations | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `b8d8abd7` | 2026-08-28 | docs(ar297): publish stage benchmark report | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `d4c31023` | 2026-08-28 | fix(ar297): clarify unresolved stage contracts | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `09498980` | 2026-08-29 | docs(ar297): record bounded model remediation | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `668e38cb` | 2026-08-29 | fix(ar297): close remaining hiring prompt shapes | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `6b6c31c0` | 2026-08-29 | docs(ar297): record six-call follow-up | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `24892c4a` | 2026-08-29 | docs(ar297): publish follow-up benchmark report | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `2f3b19dc` | 2026-08-29 | fix(ar297): project safety repair runtime facts | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `5d90ac90` | 2026-08-29 | docs(ar297): record route-closure trials | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `eeed5f92` | 2026-08-29 | fix(ar297): require complete safety repair shapes | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `208041c1` | 2026-08-29 | docs(ar297): record hot route closure | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `b171985a` | 2026-08-29 | docs(ar297): record final-pair trials | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `c857fe19` | 2026-08-29 | fix(ar297): suppress ignored planner injections | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `4ed586ff` | 2026-08-29 | docs(ar297): record MiniMax fallback proof | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `b09b4f6f` | 2026-08-29 | fix(ar297): pin complete hiring evidence shapes | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `763186d1` | 2026-08-29 | docs(ar297): record generator closure defects | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `d22a9da2` | 2026-08-29 | fix(ar297): close hiring host output shape | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `32a76281` | 2026-08-29 | docs(ar297): record final generator marker gate | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `2f24748a` | 2026-08-29 | fix(ar297): project content-free hiring request | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `f40dde6d` | 2026-08-29 | docs(ar297): record content-free generator proof | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `ac80900f` | 2026-08-29 | docs(ar297): reject MiniMax generation fallback | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `400ac3e5` | 2026-08-29 | docs(ar297): reject ZAI generation fallback | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `39e621e5` | 2026-08-29 | docs(ar297): close nine-stage model matrix | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `3ab2d6f0` | 2026-08-29 | fix(ar297): honor safety repair route | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `3013d387` | 2026-08-29 | fix(ar297): enforce zero LiteLLM retries | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `9d6b19c0` | 2026-08-29 | docs(ar297): checkpoint ordered route proof | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `1c8a2ad2` | 2026-08-29 | docs(ar297): checkpoint eight ordered aliases | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `beb97435` | 2026-08-29 | docs(ar297): reject unstable safety fallback | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `e43e4df8` | 2026-08-29 | fix(ar297): bound safety repair rationale | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `d2bc9991` | 2026-08-29 | docs(ar297): qualify repaired safety fallback | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `b5a766e6` | 2026-08-29 | fix(ar297): pin governed safety arrays | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `ce29396f` | 2026-08-29 | docs(ar297): close ordered stage matrix | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `2300596b` | 2026-08-29 | docs(ar297): record final named gates | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `341f472b` | 2026-08-29 | Merge pull request #341 from Holeshot-Software-LLC/codex/ar297-manual-live-fix | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `e755ab53` | 2026-08-29 | docs(ar297): checkpoint exact main installation | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `e2fb464c` | 2026-08-29 | Merge pull request #342 from Holeshot-Software-LLC/codex/ar297-main-install-checkpoint | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `71e3d8ca` | 2026-08-29 | docs(ar297): record speed-first route proof | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `1583934a` | 2026-08-29 | Merge pull request #343 from Holeshot-Software-LLC/codex/ar297-speed-tiebreak | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `fe71b5fb` | 2026-08-29 | docs(ar297): checkpoint manual preflight failures | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `f91f73a1` | 2026-08-29 | docs(ar297): isolate malformed planner output | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
| `35716ce8` | 2026-08-29 | docs(ar297): checkpoint full planner bakeoff | [AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md) | null |
<!-- worklog:end -->

## Provenance notes

- `2434f30` contains the name `Hermes` in its historical subject. The subject is retained exactly as committed for faithful provenance; the name does not create an active cross-repository link or dependency.
- `8f6d320` records a handoff document that was later removed. The subject remains part of the immutable commit record; no deleted document was restored for this worklog.
- `a183594` is a `docs(worklog):` ledger commit that also updated `docs/roadmap/handoffs/issue-AR-235.md`. The worklog-ledger exemption allows only `docs/worklog/**` and the reciprocal roadmap README cell. The capsule refresh should have been a separate `docs(roadmap):` commit. Retained as-is; no history rewrite.
- `56e7dee`, `410c1d1`, `66f62b9`, and `d38e08b` are published `docs(worklog):` commits that also updated `docs/roadmap/issue-AR-119-inference-first-workforce.md`. The mixed commits violate the narrow ledger exemption, but rewriting shared history would be destructive. AR-254 records their exact-SHA grandfathering; future mixed ledger commits still fail.
