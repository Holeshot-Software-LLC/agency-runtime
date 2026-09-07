---
title: "AR-180 current-profile Codex v6 delivery reconciliation"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [codex, live-evidence, native-child, backlog]
related:
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/issue-AR-185-bind-codex-activation-verification.md
  - docs/roadmap/issue-AR-191-support-codex-v2-hook-identity.md
  - docs/roadmap/acceptance/evidence/AR-404-live-header-audit-20260907.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/decisions/0193-admit-newer-codex-releases-under-the-newest-proven-child-contract.md
supersedes: []
superseded_by: null
---

# AR-180 current-profile Codex v6 delivery reconciliation

## Outcome and scope

AR-180 remains **open**. The existing September 7 current-profile activation
run has an exact host-written, pre-speech v6 card, completed native child,
accepted parent finalization and installation-bound v4 attestation. This is
Linux Codex CLI 0.153.4, exec depth one, exactly one code-reviewer card.
It is not a new canary, an ordinary encrypted-spawn proof, Desktop/TUI coverage,
multi-card delivery, or certification of the currently running parent.

The August 25 capsule's blanket current-version activation blocker is no
longer accurate for this restricted canary: ADR-0179 supplies its causal
binding and ADR-0193 admits compatible newer release structure. Ordinary
unproven encrypted assignments still remain unstaffed under ADR-0159.
No acceptance checkboxes or isolated verifier verdicts are changed here.

## Exact identity

| Field | Value |
|---|---|
| Trace | `01a07de5-15c3-7350-86c4-b38e886caa61` |
| Parent host session | `01a07de5-1566-75f3-b394-e8bac4f71979` |
| Child / launch / binding | `01a07de6-532b-7e10-927e-fa1b2e7cc17d` |
| Delivery decision | `native-child-dd1196aa18b8730b82d83f449ec1a47f` |
| Run | `94b3ad7a-f34f-412a-a534-bd7bb9b15fe8` |
| Accepted finalization | `e14db5ed-3754-4a11-98dc-d96b38ad93e3` |
| Installed runtime | `4329d76058d18eaa6b02f0b5750ff5533462064028c1178a8b5e913364774fac` |
| Install | `c482c4e2-186e-4dce-9692-98bbf22f2696` |
| Bundle | `0734429d1ba57907910723b4faaf7ec50f981513dccd0502b4518399034436b2` |

The original live invocation is recorded in the linked AR-404 live audit.
The current-profile run used the existing client credential in its child
environment and no trust bypass. No credential value or card body is retained
in this public receipt.

## Host-written card and ordering

The child artifact is the host's canonical September 7 rollout with basename
`rollout-2026-09-07T18-04-01-01a07de6-532b-7e10-927e-fa1b2e7cc17d.jsonl`.
Its zero-based developer record 8 at **22:04:05.696Z** contains one complete
4,806-character v6 envelope. The first non-input response follows at
22:04:05.698Z and the assistant final at 22:04:21.161Z.

The exact card contains 2,379 characters / 2,381 UTF-8 bytes:

- Version: `sha256:863182746a035e4b011fe28f9c86c931f3a11dde53e654429c635248a7a22297`.
- Body SHA-256: `e409b2c8b42430b9e69b1e0a93a42e8b790e6ae86c1a3e3e31c03ea0ed9820bd`.
- Envelope SHA-256: `12ee4ccef13879bb013df9420d06b02e7a2725d05e46699d8991f553fe33cd07`.

Parsed parent, child, launch, install, decision, card hashes and nonce agree
with the persisted delivery. Actual card bytes hash to the declared body
digest; a header claiming a load is not the basis of that check.

The immutable receipt's host-artifact SHA-256 is
`14124e1bf5a5e9c58ea03a56e6fb11f94a2aef1aaf03814066877483b3b0e353`.
It matches the first **99,897 bytes through zero-based record 16**.
The subsequently appended artifact was 100,774 bytes with SHA-256
`2fbb92952a80d3542a6de3117073bb0b91e0cca1f6f93c82d755033c919e9adf`.
The sealed prefix still matches; append-only terminal output is not evidence
that the original receipt was modified.

The child has zero function calls. Its lifecycle starts at 22:04:05.647Z and
ends at 22:04:21.554Z with exit code zero.

## Independent read-only correlation

The diagnostic loaded bounded artifact records and used SQLite URI
`mode=ro` plus `PRAGMA query_only=ON`. A facade exposed only the two already
read evidence getters; it did not construct Store, create evidence, call a
provider, install hooks or alter a profile.

It parsed with `parse_inference_team_delivery` in
`core/native_child_prompt_delivery.py` and replayed the existing immutable
receipt verification in `core/child_delivery_evidence.py`, with the
restricted-canary structural-hook origin already established by the exact
host artifact. It did not grant that origin to an ordinary caller's text.

The read-only verification returned:

~~~json
{
  "staffed": true,
  "verified_delivery": true,
  "v6_delivery": true,
  "pre_speech": true,
  "verification_reason": "verified_existing_receipt",
  "card_count": 1
}
~~~

This is a verification of the existing receipt, not a newly issued attestation.
Raw private rollouts are not repository dependencies; this portable projection
retains exact identities, hashes, ordering and limitations for the finding.

## Actual parent output and finalization

The parent artifact basename is
`rollout-2026-09-07T18-02-40-01a07de5-1566-75f3-b394-e8bac4f71979.jsonl`.
It was 92,286 bytes, SHA-256
`28f7cae86650efda90026ee4c94356c29ad233522fd8dab776d9fd2bd969a314`.

Its actual final output begins:

~~~text
Agency/Agencies loaded: agency-steward, code-reviewer
Agency/Agencies delegated: code-reviewer via generic-worker/spawn_agent
Skills loaded: none
Actual Model selected: workforce inference: task-agency-critic-v2 -> agency-recruiter-critic/task-agency-critic-v2 (wrapper)
Recruited via: inference
~~~

The final body SHA-256
`3194d3719a0e33408380eb5d61a73f264a6f8b365c576434df381e23b9abaf8f`
matches the sole accepted finalization. That record completed at
22:04:40.176176Z; the installation-bound attestation persisted at
22:04:41.025371Z with v4 proof digest
`0bf5239c2caa6ca6b98f1346d697b07ae0009c46dcebacc50dc3f867fb55c7d6`.

These are this canary's actual fields, not the header of the ongoing review
session, whose current staffing remains unverified.

## Literal acceptance limitations

| Original criterion | Current evidence / limitation |
|---|---|
| 4: current-profile supported native child | Exact restricted exec depth-one run is positively evidenced above. |
| 5: supported TUI and exec shapes | Exec depth one only; no fresh TUI or deeper-shape proof here. |
| 7: Desktop host-written delivery | Not exercised. |
| 8: before speech and only in child context | Before speech is proven. The exact same 2,379-character card also occurs in parent developer record 10 at 22:03:48.776Z, so **only in child context is not literally satisfied**. |
| 9: two or more compatible cards | Exactly one card. The restricted activation contract deliberately allows only code-reviewer with no companions; repeating that unchanged canary cannot prove this criterion. |
| 10: completion, finalization, attestation | All exact identities correlate as recorded above. |

The existing historical checks remain historical; this receipt does not
manufacture new acceptance verdicts. A separate bounded reconciliation must
decide whether child-only placement is still the intended product contract,
and genuine multi-card / TUI / Desktop evidence needs its own appropriate
surface. Neither is satisfied by relabeling one-card restricted canary proof.

## Validation and next package

Read-only artifact and immutable-receipt correlation completed successfully.
The latest AR-407 source package already passed the named 1,085-test fast
spine (three existing skips), UI 224 and installed artifact smoke; those are
explicitly reused checks, not newly run AR-180 tests. This change is records
only. Metadata, policy, worklog, documentation, tracker, Ruff and whitespace
checks are run for this publication.

Continue oldest-first with AR-181. Do not rerun the same restricted canary to
chase an acceptance shape it cannot express, alter trust, restore removed
one-use grant machinery, or claim all harnesses are proven.
