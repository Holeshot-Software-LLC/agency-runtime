---
title: "Name the credential the launching environment never carried"
status: accepted
category: decisions
created: 2026-09-04
updated: 2026-09-04
tags: [workforce, inference, preflight, receipts, doctor, credentials]
related:
  - docs/roadmap/issue-AR-388-unset-credential-reads-as-provider-unavailable.md
  - docs/roadmap/issue-AR-383-inferred-subject-context-fails-its-own-projection.md
  - docs/roadmap/issue-AR-356-disclose-fail-open-staffing-in-capsule.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0153-adopt-per-stage-inference-profile-routes.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0204
type: decision
deciders: [owner]
---

# ADR-0204: Name the credential the launching environment never carried

## Status

**Accepted 2026-09-04.** Item 2 of the AR-383 capsule's next package, filed
as AR-388.

## Context

Every inference profile of the installed runtime authenticates through an
`api_key_env` variable read from the launching process's environment. Hooks
inherit that environment from the host they run under, and the host inherits
it from the shell that launched it. Nothing on the machine exported the
variable, so on 2026-09-03 every preflight of a Claude session and two codex
activation verifications failed while the gateway was healthy.

The runtime described the failure as an outage. `_inference_declared` asked
whether the legacy `providers` chain or the judge existed; the judge's
credential is borrowed from the same variable at config load, so the answer
tracked the environment and not the configuration, and a fully routed
install read as undeclared. Routing then returned
`workforce_provider_unavailable` with no attempt, the receipt recorded a
runtime error, the disclosure line told the model that staffing was
unavailable, the codex canary called it a missing collaboration projection,
and `agency doctor` said nothing because its provider checks read only the
legacy list. Recovering the cause took a live experiment against the
gateway; the runtime held every fact needed to state it.

## Decision

1. **A resolved route is declared inference.** `_inference_declared` counts
   a `workforce.planner` or `workforce.recruiter` route that resolves to a
   provider, beside the legacy chain and the judge. Whether the credential
   is present is a separate question, answered where the call is made.
2. **The transport refuses and says why.** The structured transport answers
   a provider with an `api_key_env`, no direct key, on an adapter that needs a
   key, whose variable the environment lacks, with a result whose
   `failure_reason` is `provider_credential_env_unset` and makes no request.
   The stage loop records that answer as a failed attempt, returns the call
   budget it had reserved, and moves to the next provider; a stage whose every
   provider answered that way fails as `workforce_provider_unavailable`, which
   is the honest class. The check lives in the transport because the
   credential is the transport's need: an injected invoker never sees it.
3. **The cause travels to every surface that already reports the failure.**
   The failure outcome carries `workforce_credential_env_unset` on its
   abstention codes and as an abstention reason of the empty staffing
   decision, so the preflight receipt's `staffing_reason_codes`, the fail-open
   disclosure line, and the attempt row in `provider_attempts` all name it
   from the existing closed vocabularies and bounds. No variable name enters
   a receipt or the capsule; the codes are fixed tokens.
4. **Doctor names the variable.** One check per credential variable the
   routed profiles name: `warn` with the variable and the dependent profiles
   when it is unset in the inspected environment, `pass` when set, the remedy
   in the detail. Keyless loopback providers, direct keys, and the `cli` and
   `ollama` adapters are not credential faults.

## Consequences

- A session launched without the key still fails open, exactly as before,
  but the model reads `workforce_credential_env_unset` in its disclosure,
  the receipt carries the attempt, and `agency evidence rejections` can
  separate a missing key from a gateway outage without a live re-run.
- Doctor's inspected environment is the operator's shell, which may differ
  from a host's; the check says "in this environment" and names what to
  export, and the receipt covers the host's own environment.
- The transport's check is one dictionary read per call; no request is
  added or removed when the variable is set, and stubs that replace the
  transport are untouched.
- ADR-0118 is untouched: nothing here selects, ranks, filters or staffs.

## Alternatives

- **Read the key from a file when the variable is unset.** Rejected: it
  moves a secret into runtime-owned state and hides the operator's launch
  fault instead of naming it.
- **Fail the config load when the variable is unset.** Rejected: the
  config is valid; the launching environment is not, and a load failure would
  take doctor and the dashboard down with it.
- **Carry the variable name into the receipt and the disclosure.** Rejected:
  both are closed, content-free vocabularies by design (AR-356); the name
  belongs to the operator surface, which doctor is.
