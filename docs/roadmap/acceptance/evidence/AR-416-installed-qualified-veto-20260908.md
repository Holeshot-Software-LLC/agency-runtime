---
title: "AR-416 installed qualified-veto evidence"
status: active
category: roadmap
created: 2026-09-08
updated: 2026-09-08
tags: [acceptance, installation, critic, packaging]
related:
  - docs/roadmap/issue-AR-416-retain-qualified-critic-veto-causes.md
  - docs/roadmap/issue-AR-417-self-contained-qualified-veto-regression.md
  - docs/worklog/2026-09-08-installed-qualified-veto-verification.md
supersedes: []
superseded_by: null
---

# AR-416 installed qualified-veto evidence

## Candidate and build

Installed artifact source: 8629e2ed8006b2e3f7450d144e52abc9f0a9d31c.
Production package code equals merged b0dfd631; the subsequent delta makes the
regression self-contained and records the installation checkpoint. No provider,
validator, critic, retry, ownership or archive-policy change in this package.

Canonical builder from a clean clone, private umask077 and trusted release
interpreter exited0. Strict Twine passed both artifacts. Independent verifier
exited0: artifact contents match release policy.

| Artifact | SHA256 |
|---|---|
| Portable wheel | a36fa23834dcf1010f23e99e8ce787a0760e9247f50560228ded1d6ce6506bfa |
| Source archive | 483db06d138338bdf8b8cac7a1b13fd81f3eeafc4c73e5db648acd53be49bbd0 |

Separate fresh wheel and source installations both passed packaged smoke:
version0.1.0;10dashboard assets;265approved roster cards; offline inference
boundary cases passed; MCP8tools and real agency.status call passed;
authenticated loopback dashboard health passed. Both pip checks reported
`No broken requirements found.` These are isolated packaged checks, not native
host loading or staffing evidence. No public or cross-OS release claim.

## Packaged regression

The preliminary b0dfd631 source archive included the test but excluded its JSON
input under the existing allowlist. The actual extracted test command returned:

```text
FileNotFoundError: docs/roadmap/evidence/AR-414-native-critic-packet.json
1 failed, 7 passed in 0.38s
```

AR-417 changes only the test input to the exact captured verdict literal.
The rebuilt source archive was extracted with the data filter into an
owner-private directory outside the repository. Running
`python -m pytest <extracted-sdist>/tests/test_qualified_critic_reasons.py -q -W error`
returned:

```text
........                                                                 [100%]
8 passed in 0.49s
```

The excluded JSON file remains absent. Tests still exercise strict critic
rejection, durable routing/preflight codes, the real SQLite failure close and
finalizer, invalid inputs, ordinary codes and receipt/disclosure bounds.
The focused four-file critic/receipt/inference suite passed124tests after the
refinement. The fresh production spine passed1151tests with3skips in72.68s.

## Installed replay

The verified wheel was installed into the existing runtime with
`pip install --force-reinstall --no-deps <verified-wheel>`.
Installed `pip check` passed. All614package files matched wheel bytes exactly;
no mismatch. Owner agency.yaml bytes remained unchanged. CLI: `agency 0.1.0`.

A Python `-I` runner asserted that inference imports came from installed
site-packages. It supplied the captured critic response to the existing strict
inference test fixtures, then used installed routing/preflight projections,
Store failure close and finalize_response against a separate temporary database.
Upstream plan/nomination/provider receipts were synthetic fixtures; no live
provider call, native hook execution or native acceptance is claimed by replay.
Both a fresh wheel environment and the actual live installation returned:

```json
{
  "inference_sha256": "25f364e0d7440cc87373023bf8f1cf8e6b75fa9839bbcd3f944e15e454729114",
  "captured_response_sha256": "7cb2e56855c9ea72c117090c1411d81790d8ad8ea1a53eb8a9730af151d6ba16",
  "projected_codes": [
    "staffing_critic_rejected",
    "critic_wrong_neighbor_selection",
    "critic_reason_detail_omitted"
  ],
  "action": "continue",
  "status": "preflight_failed",
  "finalization_events": 0
}
```

The actual installed diagnostic text began:

```text
Agency/Agencies loaded: agency-steward
Agency/Agencies delegated: none
Skills loaded: none
Actual Model selected: none observed
Recruited via: failed; workforce_inference_failed; staffing_critic_rejected; critic_wrong_neighbor_selection; critic_reason_detail_omitted
```

The run remained failed, and zero accepted finalization events existed after
rendering. The standard cause survived while the named qualifier was explicitly
omitted. This does not rehabilitate or alter the historical native receipt.

## Native boundary

Before refresh, normal native hooks/list reported8trusted hooks. Refresh through
`agency install --agent codex --no-dashboard --json` exited0 and registered and
enabled plugin0.1.0+codex.823aab6fbe85. It returned activation_complete=false,
activation_required=true and restart_required=true; dashboard was opted out.
Bundle SHA256: dacc45819f314a775ed63f95cd51a6179215bb057ad128dd18b079ad60e2c6f3.
Binding SHA256: aaebed5d67a50c3871cd1cbd375a5feb065a1d3a7f4aeab2dfed8d312a9df2e3.

Fresh bounded hooks/list from the installed inspector then reported status
modified:8observed,8modified,0trusted,0missing. The owner was asked to review
these hooks through /hooks in a fresh TUI. No bypass, system managed-hook policy,
unattended trust retry or native inference attempt followed that observation.
Fresh current-artifact native headers, injection, staffing and finalization
remain unproven at this checkpoint. Prior native evidence belongs to the older
artifact and is not substituted here.

## Verification scope

Fresh focused124pass; production1151pass/3skip; UI224pass; Ruff779files pass;
release hygiene2508inputs pass; routing passes. Frozen-source conformance passes188/188 with source_unchanged=true.
Exact installed runtime dependency audit passes (PyYAML6.0.3, zero advisories).
Bandit exits1 with one High B202 at scripts/verify_acceptance.py:292, the unchanged
compatibility fallback without extraction filters. Current Python3.12 uses the
explicit data filter; the legacy finding is recorded, not repaired or waived.
No clean overall security-scan claim is made. This evidence supports installed diagnostic replay and packaged
regression claims only. Isolated acceptance verdicts are written by the verifier,
not by this builder. AR-414/415/416/417 remain open at this checkpoint.
