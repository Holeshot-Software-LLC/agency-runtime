---
title: "AR-388: An unset credential variable reads as a provider outage, and nothing names it"
status: in_progress
category: roadmap
created: 2026-09-04
updated: 2026-09-04
tags: [workforce, inference, preflight, receipts, doctor, credentials]
related:
  - docs/decisions/0204-name-the-credential-the-launching-environment-never-carried.md
  - docs/roadmap/issue-AR-383-inferred-subject-context-fails-its-own-projection.md
  - docs/roadmap/issue-AR-387-recruiter-cards-carry-no-eligibility.md
  - docs/roadmap/issue-AR-307-project-canary-inference-credentials.md
  - docs/roadmap/issue-AR-356-disclose-fail-open-staffing-in-capsule.md
  - docs/roadmap/handoffs/issue-AR-383.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-388
priority: p1
tracker_url: null
depends_on: []
blocks: []
---

# AR-388: An unset credential variable reads as a provider outage, and nothing names it

## Problem

Every inference profile of the installed runtime authenticates through
`api_key_env: LITELLM_API_KEY`, read from the launching process's environment
and nowhere else. Nothing on the host exports that variable: not the login
profiles, not the systemd user environment, not the Claude Code process, and
not the shells the Bash tool opens. On 2026-09-03 every preflight of a
Claude session and the first two codex activation verifications after the
owner's trust step failed while the gateway answered a recruiter-route
completion in under a second.

What the runtime said about it, at every layer, was something else:

- the preflight receipt: stage `routing`, reason `workforce_provider_unavailable`,
  exception category `runtime_error`, `provider_attempts: []`;
- the fail-open disclosure line the model reads:
  `[Agency staffing failed this turn: workforce_provider_unavailable; staffing: inference_unavailable]`;
- the codex activation verification: `codex_collaboration_projection_unavailable`,
  and under it `preflight_failed` with the diagnostic
  `native_collaboration_topology_invalid` on complete spawn and wait counts;
- `agency doctor`: nothing about credentials at all, because its provider
  checks read only the legacy `providers` list, which this install does not
  use.

The mechanism is `_inference_declared`, which asked whether the legacy
`providers` chain or the judge existed. The judge's credential is borrowed
from `LITELLM_API_KEY` at config load, so with the variable present the judge
counted as a declared provider and routing went on to use the real profiles;
with it absent the same fully routed install was undeclared, and routing
returned `workforce_provider_unavailable` before making an attempt. The
profiles that actually staff every turn were never consulted for the
question, and the one fact that explained the evening, an unset variable, was
recorded by nothing.

## Current state

Verified on 2026-09-03 with the installed runtime at `56e0b6dd`:

- `load_config()` with and without the variable: `cfg.providers` is empty in
  both, `_inference_declared` is `False` without it and `True` with it, and
  `configured_workforce_providers` resolves `agency-planner` and
  `agency-recruiter` in both.
- `agency install --agent codex --verify-activation` failed from a shell
  without the variable and passed at once from a shell that had sourced
  `~/.config/ai-secrets/common.env`: `runtime-verified`, attestation persisted.
- `agency evidence rejections` lists twelve `preflight_failed` codex runs and
  the whole Claude session's turns; none carries a cause.

## Approach

ADR-0204. Ask the right question and name the fault where it is:

1. `_inference_declared` counts a resolved `workforce.planner` or
   `workforce.recruiter` route as declared inference, beside the legacy chain
   and the judge. Routing therefore reaches the stage loop.
2. The structured transport refuses to call a provider with an `api_key_env`
   and no direct key, on an adapter that needs one, whose variable the
   environment lacks, and answers with a result whose `failure_reason` is
   `provider_credential_env_unset` instead of sending an unauthenticated
   request. The stage loop records that answer as a failed attempt, gives the
   call budget back, and moves on; a stage whose every provider answered that
   way fails as `workforce_provider_unavailable`, the honest class. An
   injected invoker never sees the check, so fakes behave as before.
3. The failure outcome carries `workforce_credential_env_unset` on its
   abstention codes and as an abstention reason of the empty staffing
   decision, so the preflight receipt's `staffing_reason_codes` and the
   fail-open disclosure line both name it, and the attempt reaches the
   receipt's `provider_attempts` with its code.
4. `agency doctor` gains one check per credential variable the routed
   profiles name: `warn` with the variable and the profiles when it is unset
   in the inspected environment, `pass` when set, and the remedy in the
   detail. Keyless loopback providers, direct keys, and the `cli` and
   `ollama` adapters are not credential faults.

Nothing here selects, ranks or filters a specialist; the change is in what
the runtime says about why it could not ask.

## Dependencies

None. AR-307 projects canary credentials for the isolated profile and is
unchanged; this issue is about the current profile and the launching shell.

## Acceptance

- [x] A routed install with no legacy providers is declared inference in any
      environment, and an unconfigured install is still not.
- [x] The structured transport answers `provider_credential_env_unset` for a
      provider whose credential variable is unset instead of calling, the
      stage records it as a failed attempt with no budget spent, and the
      outcome carries `workforce_credential_env_unset`; keyless loopback,
      direct keys, `cli` and `ollama` are not credential faults.
- [x] The preflight receipt carries the attempt code and the staffing code,
      and the fail-open disclosure line renders
      `workforce_credential_env_unset` inside its budget.
- [x] `agency doctor` warns by variable name, naming the routed profiles,
      when the variable is unset in the inspected environment, and passes
      when it is set; shown live on the installed configuration.
