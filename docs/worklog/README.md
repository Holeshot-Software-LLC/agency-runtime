---
title: Worklog
status: active
category: worklog
created: 2026-07-10
updated: 2026-08-12
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
| `4928a873` | 2026-08-04 | AR-233: Architecture fixes â€” honest headers, wildcard distinction, strict default, metrics (#242) | null | null |
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
| `79295735` | 2026-08-05 | docs(roadmap): AR-253 â€” dynamic team dispatch on every harness | null | null |
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
<!-- worklog:end -->

## Provenance notes

- `2434f30` contains the name `Hermes` in its historical subject. The subject is retained exactly as committed for faithful provenance; the name does not create an active cross-repository link or dependency.
- `8f6d320` records a handoff document that was later removed. The subject remains part of the immutable commit record; no deleted document was restored for this worklog.
- `a183594` is a `docs(worklog):` ledger commit that also updated `docs/roadmap/handoffs/issue-AR-235.md`. The worklog-ledger exemption allows only `docs/worklog/**` and the reciprocal roadmap README cell. The capsule refresh should have been a separate `docs(roadmap):` commit. Retained as-is; no history rewrite.
- `56e7dee`, `410c1d1`, `66f62b9`, and `d38e08b` are published `docs(worklog):` commits that also updated `docs/roadmap/issue-AR-119-inference-first-workforce.md`. The mixed commits violate the narrow ledger exemption, but rewriting shared history would be destructive. AR-254 records their exact-SHA grandfathering; future mixed ledger commits still fail.
