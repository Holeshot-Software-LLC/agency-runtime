---
title: "AR-293: Allow safe inference profile config operations"
status: done
category: roadmap
created: 2026-08-25
updated: 2026-08-25
tags: [configuration, inference, profiles, security, cli, jina]
related:
  - docs/roadmap/issue-AR-289-native-reranker-transports.md
  - docs/roadmap/issue-AR-290-end-to-end-guided-setup.md
  - docs/roadmap/issue-AR-296-project-effective-inference-topology.md
  - docs/decisions/0006-config-first-redacted-configuration.md
  - docs/decisions/0153-adopt-per-stage-inference-profile-routes.md
  - docs/decisions/0171-separate-native-and-structured-reranker-transports.md
  - agency_runtime/core/configuration_patch.py
  - agency_runtime/core/configuration_service.py
  - tests/test_configuration.py
  - README.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: provider-configuration
issue_id: AR-293
priority: p0
tracker_url: null
depends_on: []
blocks: [AR-296]
---

# AR-293: Allow safe inference profile config operations

## Problem

AR-289 added the validated Jina transport and AR-290 tells a setup agent to
configure explicit per-stage inference routes, but `agency config set` rejected
both named `inference.profiles.<name>` updates and the `inference.routes` map as
unsupported operation paths. Manual YAML could express the schema, but the
guarded CLI and dashboard transaction surface could not apply the documented
configuration. That left the consumer walkthrough unable to finish safely.

## Current state

- Inference profile schema, routing, redaction, and runtime resolution already
  support local models, LiteLLM, HTTP API keys, subscription CLIs, embeddings,
  structured text rerankers, and native Jina reranking.
- The transactional writer accepts a closed scalar allowlist and write-only
  secrets, but it had no dynamic inference-profile or route operations.
- Direct profile keys are recursively redacted on display, but their presence
  was not exposed in the write-only secret-presence projection.
- Tracker creation was attempted after push/merge authorization, but the
  external approval boundary requires separate explicit tracker authorization.

## Approach

Accept one validated lowercase named profile at
`inference.profiles.<name>` and accept the complete bounded dotted route map at
`inference.routes`. Reject inline direct profile keys and add the exact
`inference.profiles.<name>.api_key` write-only secret target. Preserve an
existing direct key during non-secret profile edits unless the operator
deliberately switches to `api_key_env`. Keep final whole-document validation as
the authority for route/profile coherence and capability restrictions.

## Dependencies

- ADR-0006 owns config-first redaction and write-only secret handling.
- ADR-0153 owns per-stage named profiles and routes.
- AR-289 and ADR-0171 own the native Jina reranker boundary.
- AR-290 owns the consumer setup journey that exercises these operations.

## Acceptance

- [x] The guarded CLI creates validated Jina embedding and reranker profiles.
- [x] One atomic route-map update accepts dotted recall capability keys and
      rejects undefined or capability-incompatible profiles.
- [x] Inline direct keys are rejected; hidden-input secret operations are
      redacted and represented only by boolean secret presence.
- [x] Existing profile secrets survive ordinary profile edits unless the
      operator switches to an environment credential.
- [x] Focused configuration and security tests, Ruff, docs, and diff checks
      pass.
- [x] The installed CLI configures both Jina routes without storing the key in
      YAML; bounded live embedding and native reranker calls both apply with
      exact model identities.
- [x] Tracker creation and linkage remain pending explicit tracker
      authorization after the external approval boundary rejected the write.

## Verification evidence

The pre-fix installed CLI returned `operation path is not supported` for both
named profiles and the route map, leaving `inference.routes` empty. After the
repair, the same public commands wrote the two environment-referenced Jina
profiles and both recall routes while `workforce.dense_recall_mode` remained
`additive`. A bounded live transport check returned one 1,024-dimensional
embedding with actual model `jina-embeddings-v3` and an exact two-document
native rerank permutation with actual model `jina-reranker-v3.5`. No credential
value entered argv, YAML, Store evidence, repository files, or command output.
