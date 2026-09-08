---
title: "AR-192 current-policy hook-trust evidence"
status: active
category: roadmap
created: 2026-09-08
updated: 2026-09-08
tags: [acceptance, evidence, codex, hooks, trust, performance]
related:
  - docs/roadmap/issue-AR-192-fail-fast-on-codex-hook-trust-drift.md
  - docs/roadmap/handoffs/issue-AR-192.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - docs/roadmap/acceptance/evidence/AR-180-current-profile-v6-delivery-20260907.md
  - agency_runtime/core/codex_hook_trust.py
  - agency_runtime/core/canary_backends.py
supersedes: []
superseded_by: null
---

# AR-192 current-policy hook-trust evidence

## Outcome and scope

This record distinguishes the already implemented fail-before-model boundary
from the July requirement for another TUI approval ceremony. It supplies
observations, not acceptance judgments. No runtime, native trust store,
owner profile, staffing authority or activation-grant code changed here.

ADR-0173 preserves attended trust for ordinary profiles and separately explicit
autonomous-bypass and managed-policy modes. Codex's current public documentation
likewise distinguishes hash-bound reviewed hooks, policy-trusted managed hooks,
and an invocation-only bypass that does not persist trust. Installation alone
does not trust a new definition. This contextual reference is not evidence of
the installed CLI's behavior: [Codex hooks](https://learn.chatgpt.com/docs/hooks#review-and-trust-hooks).

## Original criteria and explicit reconciliation

The July wording and checkbox states remain verbatim here:

> - [x] Current-profile Agency verification performs `hooks/list` before any
>   model-backed Codex execution.
> - [x] The preflight requires the exact canonical Agency event inventory and
>   rejects missing, duplicate, disabled, untrusted, or modified entries.
> - [ ] After an exact reinstall, one fresh TUI approval is confirmed by an
>   authoritative 8/8 trusted inspection before the live canary.

Criteria 1/2 are explicitly scoped to attended current-profile exact-activation
verification. The production predicate also checks `profile_scope`,
`require_exact_activation_rollout` and the two separately explicit trust modes.
Generic and isolated canaries are not silently claimed to use this preflight.

Criterion 6 retains exact reinstall, settled hashes, enabled/trusted 8/8,
ordered preflight and a real no-bypass canary. It requires fresh supported
approval only when the settled definitions are not already trusted. Repeating
approval for already trusted exact definitions is not additional activation
proof. Missing trust still stops the canary; no bypass/private mutation replaces
it. This applies existing policy; it does not authorize unattended persistent
approval on an ordinary owner profile.

AR-191's retired-grant lineage is not a staffing authority to restore. Current
native child delivery remains inference-owned and host-proven under AR-255;
AR-192 checks admission, not child-only delivery or all-harness readiness.

## Frozen product-source identity

Focused validation ran in a clean branch at
`f0e388633f9fa22d7d81e8a40e7265d3e5262d18`. The following command exited zero
with no output, establishing product-source equality to the parent's exact
installed candidate, not merely similarity of issue records:

```text
git diff 4db6be169a4f86185c261d93814f1106d79f0136 HEAD -- agency_runtime scripts tests pyproject.toml
```

Exact SHA-256 at that frozen source:

```text
6e50a50acf401e53abbc44555f028e2654b3d41038bcfc017c20bdc3e4b7d68f  agency_runtime/core/codex_hook_trust.py
947ca2605561f72d96fc9db4a5d150fb4535fbf208f0380709aa30c4e2c195c9  agency_runtime/core/canary_backends.py
45198a033861c9db37c97342f2c135bafa2e2f375d564a384cf7c5a51f8ce99a  agency_runtime/core/codex_activation_verification.py
3343a1b0cf8d30bebf0214e337eb625a909c1c6f1d835350041f471dd77309c4  agency_runtime/core/installer_contracts.py
1193379f54c828e6ec4ad4b4900b28fb101d147931d79064276eb2561671a272  tests/test_codex_hook_trust.py
4cf601b9546fc1fe2b753cfc4a3b616228e7f9bb7df6f30d2227c311648d159a  tests/test_host_canary.py
325c25248a87b4a27c7095007b1bc1fee1adfec5d4126f8c08f24fd4bc6417b3  tests/test_codex_activation_verification.py
2e2747b85670c097641c410684dfc5c4d322ad7e57060c9f49d211c4f8cbfc3d  tests/test_codex_activation_canary.py
```

Subsequent evidence-only commits do not redefine this runtime under test.
The authoritative worker is launched from the published projection, not from
an unchecked repository import. Missing projection returns the distinct
`worker_projection_unavailable` evidence instead of pretending hooks are
untrusted.

## Fresh focused checks

Actual command, private umask, exit zero:

```text
umask 077
env PYTHONPATH=. /tmp/agency-ar404-venv.AUBJlC/bin/python -m pytest tests/test_codex_hook_trust.py tests/test_codex_activation_verification.py tests/test_codex_activation_canary.py tests/test_host_canary.py -q -W error
........................................................................ [ 40%]
........................................................................ [ 80%]
....................................                                     [100%]
180 passed in 11.34s
```

Actual focused lint/format commands and raw result:

```text
/tmp/agency-ar404-venv.AUBJlC/bin/ruff check agency_runtime/core/codex_hook_trust.py agency_runtime/core/canary_backends.py tests/test_codex_hook_trust.py tests/test_host_canary.py tests/test_codex_activation_verification.py tests/test_codex_activation_canary.py
All checks passed!
/tmp/agency-ar404-venv.AUBJlC/bin/ruff format --check agency_runtime/core/codex_hook_trust.py agency_runtime/core/canary_backends.py tests/test_codex_hook_trust.py tests/test_host_canary.py tests/test_codex_activation_verification.py tests/test_codex_activation_canary.py
6 files already formatted
```

The stale-inventory backend test uses actual production dispatch with a fake
read-only inspector returning `modified`; the process-runner call list stays
empty. It checks exact cwd/executable, a timeout of at most ten seconds and
structured `model_invocation_attempted=false`, attended mode, no bypass and no
persistent trust change. Other focused cases exercise malformed counts/hashes,
missing/duplicate/unexpected events, modified/untrusted/disabled hooks,
warnings/errors, process timeout, output truncation, frozen worker/executable
identity, command redaction and explicit managed/autonomous mode separation.
These deterministic cases are not represented as a deliberately damaged
owner profile or as a native stale-hook experiment.

## Earlier installed read-only observation

The parent ran this actual command from `/tmp`, exit zero:

```text
umask 077
/home/holeshot/.local/share/agency-runtime/venvs/ar348-20260905.qq1DjJ/bin/python -I -c 'import json,time; from pathlib import Path; from agency_runtime.core.codex_hook_trust import inspect_codex_hook_trust; start=time.monotonic(); report=inspect_codex_hook_trust(Path("/home/holeshot/code/agency-runtime"),timeout=10.0); print(json.dumps({"elapsed_seconds":round(time.monotonic()-start,3),"report":report},sort_keys=True))'
```

The observed window was 2026-09-07T23:33:14Z–23:34:02Z, not a claimed exact
instant. Elapsed inspection time was **0.569 seconds**. The following is a
selected-field projection supplied by the parent, **not full raw stdout**:

```text
status=trusted
expected_count=8 observed_count=8 trusted_count=8
managed=modified=untrusted=disabled=missing=unexpected=duplicate=warning=error=0
all eight events: enabled=true, trustStatus=trusted
postCompact sha256:56978008b2b188c3e3a24f71c25a6a660c97ee27a8a299fe6087bd21a15517f7
postToolUse sha256:15b5bef77d3107eef0e4cea0db76df71af2de7574fdb6d855f844db2a08dacd9
preToolUse sha256:95fa0a6b95469ecacb6fd71c5e31fd77606c8c15dbfbca9c8d8a771160823f04
sessionStart sha256:cfc1c6960664b39c21f57076ae573c7b8c4e6819dc9ca7b7e0bfc178b3a02510
stop sha256:a9ca9cf8f498bf9a1ce534bca3b41432df6b3aa126684d55fbf916c1b525d1b0
subagentStart sha256:b9295ec99d4142c1580f09ecabcb620b5407177af6f750d0efa3172398d7c950
subagentStop sha256:a9965b4d3e449d1117c3cee794dffd0357d9454db718968701670c53f54e1f6f
userPromptSubmit sha256:f550e8316a0bec881bd824d303f5e82229f8abd0b2dbe03891e73c3c7315f190
```

This is genuine installed inspection, but it occurred after the earlier
22:04 current-profile canary. It cannot prove probe-before-canary ordering,
a new native approval, unchanged owner-profile bytes or the newly installed
4db6be16 candidate. Those claims require their own later evidence.

## Remaining evidence boundary

The fresh ordered proof below establishes the refusal path. Criterion 6 still
requires supported native approval of the newly settled definitions, another
authoritative 8/8 trusted inspection and successful attended no-bypass canary.
No approval was attempted and no acceptance run or completion claim is made.
Native Windows, TUI/Desktop
child delivery, multi-card staffing, signing, exhaustive coverage and the
compatibility matrix are outside this bounded Linux hook-trust package.

## Fresh installed trust refusal after exact refresh

The parent upgraded the existing CLI environment to full source
`4db6be169a4f86185c261d93814f1106d79f0136` at
00:18:33.222144–00:18:39.688271 UTC on September 8, exit zero. Its selected
Codex refresh then exited zero at 00:19:12.161427–00:19:17.108567 UTC:

```text
/home/holeshot/.local/share/agency-runtime/venvs/ar348-20260905.qq1DjJ/bin/python3 -I -m agency_runtime.cli install --agent codex --no-dashboard --json
```

This retained venv directory name is historical, not a claim that its package
still contains AR-348. The parent independently compared all **613/613 wheel
payload files** against the fresh exact-source wheel. Current Codex identity
in the actual verification output is install ID
`0bcd48c2-374a-48b9-8327-80c46c9fa158`, bundle digest
`de0ad33410b550feae573076f40e04498902327d17f851dca5177f0e04cc9f2f`,
managed plugin version `0.1.0`, native host `codex-cli 0.153.4`.

Actual read-only inspection, no PYTHONPATH override, timeout ten seconds:

```text
/home/holeshot/.local/share/agency-runtime/venvs/ar348-20260905.qq1DjJ/bin/python3 -I -c 'import json; from pathlib import Path; from agency_runtime.core.codex_hook_trust import inspect_codex_hook_trust; print(json.dumps(inspect_codex_hook_trust(Path("/home/holeshot/code/agency-runtime"), timeout=10.0)))'
```

Its capture window is **00:30:44.246566–00:30:44.789038 UTC**, elapsed
**0.542472 seconds**, exit 0, no timeout and zero stderr bytes. Actual output
reports `status=modified`, expected/observed 8, trusted 0, modified 8 and all
other counters zero. Every event is enabled. The complete sanitized JSON,
including all eight exact hashes, is preserved byte-for-byte in
[raw trust stdout](AR-192-fresh-installed-trust-20260908.json); its SHA-256 is
`40d4bf57218f645a9523b3eaa33584d0db0cdab9319f97bc4233f6067fd880b1`.
The [capture receipt](AR-192-fresh-installed-trust-capture-20260908.json)
preserves exact argv, times, exit code, output lengths and digests.

The parent next ran the real installed verification command with an outer
420-second capture bound and no PYTHONPATH injection:

```text
agency install --agent codex --verify-activation --activation-timeout 180 --json
```

It finished **00:30:45.752193–00:30:49.240622 UTC**, elapsed
**3.488429 seconds**, exit **1**. The full
[actual CLI JSON](AR-192-installed-verification-refusal-20260908.json), SHA-256
`683b6f10e57f4fffda5b282939e2710bc16ee69e47a645d6769b33331ea6b347`,
contains the decisive fields:

```text
verification_only=true installation_attempted=false complete=false
activation.trust_mode=attended activation.trust_bypass_used=false
verification.profile_scope=current-profile
verification.canary_passed=false verification.attestation_persisted=false
verification.invocation.failure_reason=codex_hook_trust_not_ready
verification.invocation.model_invocation_attempted=false
verification.invocation.hook_trust.status=modified
verification.invocation.hook_trust.modified_count=8
```

These are selected fields from the preserved complete output, not a fabricated
standalone JSON object. `verification.live_attempted=true` means the canary
coordinator was entered; the nested explicit model flag is false. It must not
be described as a model-backed native turn, missing child injection after a
model call, or successful activation. The CLI returns the supported fresh-TUI
approval instructions; neither the parent nor worker performed that action.
The [capture summary](AR-192-installed-verification-capture-20260908.json)
omits some fields and therefore has nulls where the full JSON proves false;
the complete JSON remains authoritative.

This real ordered refusal proves the installed fail-fast path in seconds
without spending a model invocation. It does not carry the old eight trusted
hashes across the reinstall, claim a before/after profile-byte audit, or remove
the owner trust gate. No child, final header or activation attestation was
produced or claimed. No unchanged retry or bypass was performed.

## Named production spine provenance

The parent-approved combined AR-408/409 source checkpoint `f670e6b5` passed
the repository's named warning-strict production spine: **1085 passed,
3 skipped in 69.50 seconds**, and 210 related focused cases in 3.89 seconds.
The faithful command/result record is the
[AR-409 worklog](../../../worklog/2026-09-07-9946461a-ar409-reservation-checkpoint.md).
Comparison from `f670e6b5` to this package's source finds no product or script
change. The only test-file addition is the separately owned AR-189 private
uninstall regression, outside that named spine and this focused package.
Thus this is reused current-source spine evidence, not a claimed fresh rerun.
The fresh 180-case trust package above runs on the complete installed-source
equivalent checkpoint. The exhaustive corpus and Windows matrix were not run.
