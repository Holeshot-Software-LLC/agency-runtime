---
title: "AR-190 exact product-source candidate and second review evidence"
status: active
category: roadmap
created: 2026-09-08
updated: 2026-09-08
tags: [acceptance, evidence, updates, uv, isolation, provenance]
related:
  - docs/roadmap/issue-AR-190-make-upgrade-plans-runnable-in-uv-tools.md
  - docs/roadmap/acceptance/issue-AR-190.md
  - docs/roadmap/handoffs/issue-AR-190.md
  - docs/roadmap/acceptance/evidence/AR-190-installed-uv-plan-20260907.md
  - docs/roadmap/acceptance/README.md
  - docs/decisions/0107-resolve-updates-immutably-and-keep-application-attended.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
---

# AR-190 exact product-source candidate evidence

## Outcome and scope

At 2026-09-08T00:00:19.594344Z, the actual Agency entrypoint installed by uv
from a fresh canonical wheel of exact clean detached source
`d1a9260c08aad8eb871fd6bd1ab81c3aad5e524f` produced a successful nonexecuting
upgrade plan to that SAME full SHA. Installed planner file hashes equal the
source hashes below. The target is not a mutable branch name, and the wheel's
ordinary `source_revision=null` identity has not been relabeled as VCS identity.

The [unmodified raw receipt](AR-190-uv-plan-d1-20260908.json), SHA-256
`db365fef314e425c5a900ffa17c2dd7a205e019e30e95b7696215c521418059d`,
contains every subprocess argv/stdout/stderr, timestamps, actual uv receipt,
installed file hashes, returned plan and before/after comparison. It is a new
execution, not a rewritten version of either September 7 c64ce3ce receipt.
No owner package, host configuration, trust, credentials or profile changed.

## Original criterion and first result

The original criterion 5 is retained verbatim:

```text
- [ ] Focused update/CLI tests, lint, docs checks, and one live installed uv-tool
  plan pass from the exact final commit.
```

The first isolated run accepted criteria 1–4 but returned `absent` for 5:

```text
AR-190 criterion 5: absent (AR-190.5-20260907-42c2bd69)
```

Its exact reason was:

> The evidence doc's Focused checks, Record checks and source-equivalence sections show the 67 tests, Ruff, docs checks and live uv plan ran at c64ce3ce and ledger commit d28ccc23, not at candidate d1a9260c; the equivalence claim covers only product source and is unverifiable in the snapshot.

All five first verdicts, reasons and digests are preserved at commit
`a6efa01be2aec0f5bacfc02c2f865d8046bd1060`, ledger `0199f8d3`. No first verdict
is carried forward under a new candidate SHA. The acceptance runner binds its
candidate to every criterion digest; a new receipt candidate requires another
all-five review, not just a criterion-5 edit with reused verdicts.

## Product-source and receipt distinction

The owner requested this bounded clarification of obsolete evidence-commit
wording: “exact final product-source candidate identified by canonical build
provenance; subsequent evidence-only commits do not redefine the runtime under
test.” Tests, lint and the live installed plan still require an exact committed
runtime candidate; documentation checks still have to pass at the corresponding
evidence checkpoint. Criteria 1–4, exact-SHA commands, installer ownership,
fail-closed checks and nonexecution remain unchanged.

This applies the existing acceptance lifecycle, not a new installer authority:
an observed run is committed after it happens, and a commit cannot contain
its own future execution receipt or worklog SHA. The runtime under test is
explicitly d1a9260c; the later frozen receipt candidate only adds records.
It does not claim that its documentation-bearing wheel was built before that
commit existed. A second and final isolated all-five review is authorized;
there is no third unchanged-evidence retry.

## Canonical exact-source build

A fresh detached worktree resolved HEAD to
`d1a9260c08aad8eb871fd6bd1ab81c3aad5e524f`, with empty porcelain status before
and after production. `git symbolic-ref -q HEAD` exited 1 with empty output,
confirming detached HEAD. Parent and initially absent destination were private
`0700`; the canonical producer ran under `umask 077`.

Portable command parameters denote the actual private source, destination and
trusted development interpreter; they do not override HOME, UV or XDG targets:

```bash
cd "$AR190_SOURCE_TREE"
umask 077
env PYTHONPATH=. "$AR190_PYTHON" -m scripts.build_distributions "$AR190_DIST_DIR" --create-private-parent --expected-commit d1a9260c08aad8eb871fd6bd1ab81c3aad5e524f
"$AR190_PYTHON" -m twine check --strict "$AR190_DIST_DIR/agency_runtime-0.1.0-py3-none-any.whl" "$AR190_DIST_DIR/agency_runtime-0.1.0.tar.gz"
env PYTHONPATH=. "$AR190_PYTHON" -m scripts.verify_distribution "$AR190_DIST_DIR" --expected-commit d1a9260c08aad8eb871fd6bd1ab81c3aad5e524f --artifact-set portable
```

Builder and independent verifier stdout, both exit zero:

```text
Canonical distribution build passed: agency_runtime-0.1.0-py3-none-any.whl, agency_runtime-0.1.0.tar.gz
Distribution verification passed (artifact contents match release policy).
```

Strict Twine returned `PASSED` for both artifacts. Actual SHA-256 values:

| Artifact | SHA-256 |
|---|---|
| `agency_runtime-0.1.0-py3-none-any.whl` | `98b87cf098bf0b35b4a266d8ee35288e1a366914b7e19f9c6a8579c2ce23e457` |
| `agency_runtime-0.1.0.tar.gz` | `498f02203cb32156383d6dd61eeebc1b43163c76a3ef8a0cec95082783f9d083` |

## Concrete source identity

Actual `sha256sum` stdout from the detached d1a9260c source:

```text
e73df6c5c626041e3917b707cbd0a2cbc863bf6f5f6b1c27848515758959eddb  agency_runtime/core/update_service.py
4bf96a05ff0fee2c26ee4c576e651dde47678fdf1c8a6da58bdc8fb4cdce1ae2  agency_runtime/cli/upgrade_commands.py
c9bc50bdc1e711576667b815905b3a2ed253cc1bf359a1907d49383a4d3e1e6d  tests/test_update_service.py
0961a810bc758841b8bf645a505059cf242066be707ccc6d3f0675a790c4279e  tests/test_cli_upgrade.py
a40e10a5c28455f60af136cc380177aea6d399180114e5c67b93f397f8b863bf  scripts/build_distributions.py
fe7372b0bf79a89c3771122faa4c3ab32081506d8421c1973d475d6d682e384f  scripts/verify_distribution.py
37a230423c5ec9950a31f9ba7e540fca74e06476ac28ef45ec05acf75c618303  scripts/canonicalize_distributions.py
ad7572e4c8c9e98eb868ba0f68b438d3b8b0fe324b055c23b1b2e06ec36a9125  pyproject.toml
```

The installed probe reads the two executing planner files from the actual
uv prefix, independently hashes them and asserts their equality to these
source values before invoking the plan. Its raw `installed_product_sha256`
contains those same two digests. This is in addition to the exact wheel hash
assertion and independent canonical payload verifier, not an installed
version-string inference.

The following actual command exited zero with empty stdout/stderr:

```bash
git diff --exit-code c64ce3ce54c6e51280292298b5e3600611cb72fc..d1a9260c08aad8eb871fd6bd1ab81c3aad5e524f -- agency_runtime scripts tests pyproject.toml
```

The same path-scoped comparison from d1a9260c to the later evidence worktree
is checked before freezing; only documentation paths are changed. Source
object identities remain the four exact objects listed in the September 7
receipt, while the fresh installed hashes provide concrete executing-file
corroboration rather than relying only on a prose equivalence claim.

## Legitimate uv installation

The already-local exact image is
`sha256:c8e7a2654bcd382d56c07bdb04a3b3ae35de09fb0e69cf9bb825d72e14baacf7`.
It used its ordinary UID 0/home `/root`; no owner home or credentials were
mounted, and no HOME/UV/XDG target override was provided. The verified uv input
SHA-256 is `646adf5cf12ba17d1a41fa77c8dd6496f73651dcfeeed6b5f4ec019b36bc7153`.

Actual container setup command:

```bash
/usr/local/bin/uv tool install --no-config /ar190-input/agency_runtime-0.1.0-py3-none-any.whl
```

It exited zero and reported two installed packages: Agency Runtime 0.1.0 and
PyYAML 6.0.3. Actual distribution inventory independently reported only those
two packages, with Python 3.11.2 and prefix
`/root/.local/share/uv/tools/agency-runtime`; pip is absent. uv 0.11.8 created
the real receipt and in-prefix symlink `/root/.local/bin/agency`. Default home,
tool root, exact prefix and bin directory were all `0700`. The ordinary PATH
warning was handled by invoking the absolute entrypoint, not changing targets.

## Same-candidate installed plan

Actual command, exit zero and empty stderr:

```bash
/root/.local/bin/agency upgrade plan --ref d1a9260c08aad8eb871fd6bd1ab81c3aad5e524f --timeout 5 --json
```

Raw stdout is preserved without substitutions in the linked JSON. Selected
actual returned fields (this is a projection, not the full raw output):

```json
{
  "checked": true,
  "cache_hit": false,
  "checked_at": "2026-09-08T00:00:19.594344+00:00",
  "error": null,
  "target_commit_sha": "d1a9260c08aad8eb871fd6bd1ab81c3aad5e524f",
  "installer": "uv-tool",
  "mutation_performed": false,
  "requires_owner_execution": true,
  "requires_post_install_activation_check": true
}
```

The raw first command argv is `/usr/local/bin/uv tool install --force
--refresh --no-config` followed by the official repository's pip VCS
requirement pinned to the exact full d1a9260c SHA. It contains no pip
invocation. The second command is exactly:

```text
/root/.local/share/uv/tools/agency-runtime/bin/python -I -m agency_runtime.cli install --agent codex --no-dashboard
```

Neither command was executed. `status=unknown`/`update_available=null` are the
honest wheel-without-VCS-identity projection, not a false “newer” claim.

## No plan mutations and isolation bounds

The real setup install precedes the measured plan interval. After the plan,
all 669 compared non-bytecode prefix file hashes are unchanged. The entrypoint
hash before/after is
`0713dfe44c67da775470cd134fcc14f4c546f84798302b3cba39394418a89653`,
and the real uv receipt hash before/after is
`e78058bdd433bac622c76854183fe38c0ad99cb3070f91ae2e5d00e5036ca251`.
The comparison excludes `__pycache__`; subprocesses used
`PYTHONDONTWRITEBYTECODE=1`. Discovery cache files are not package or host
mutation and are not falsely included in the prefix comparison.

The local Unix-socket Docker command used `--rm --pull never`, all capabilities
dropped, no-new-privileges, 128 PIDs, 1 GiB, one CPU and a five-second stop
timeout, with a 120-second outer bound. Only exact probe/uv/wheel files were
read-only bind mounts; no daemon socket, home or credentials were mounted.
No remote daemon, image pull, service/admin change or model invocation occurred.
Public dependency retrieval and official fixed-origin GitHub resolution were
authorized. Installation was bounded to 60 seconds, identities to 10 seconds,
the plan to 25 seconds with its own five-second lookup bound, and output to
256 KiB per subprocess. The container span was
00:00:17.944856–00:00:20.046362 UTC; it was absent on readback after `--rm`.

Probe script SHA-256:
`1cc6c7b2345fb84543730dfdee5c7685dc0bae1c52de414d12ce0200adb05efd`.
Owner Agency wrapper before/after:
`c31ca4d105085d95369c3704e82d9c6fd2ea12a9f2c1f021157da8984dc53974`.
The owner uv executable and mounted wheel retained their pre-run hashes too.

## Fresh focused checks

Actual fresh command in the clean detached d1a9260c tree:

```bash
env PYTHONPATH=. "$AR190_PYTHON" -m pytest tests/test_update_service.py tests/test_cli_upgrade.py -q -W error --tb=short
"$AR190_RUFF" check agency_runtime/core/update_service.py agency_runtime/cli/upgrade_commands.py tests/test_update_service.py tests/test_cli_upgrade.py
"$AR190_RUFF" format --check agency_runtime/core/update_service.py agency_runtime/cli/upgrade_commands.py tests/test_update_service.py tests/test_cli_upgrade.py
```

Actual stdout, all exit zero:

```text
...................................................................      [100%]
67 passed in 0.83s
All checks passed!
4 files already formatted
```

The source SHA and exact hash table above bind these tests to the newly built
and actually installed d1a9260c package. Native Windows, exhaustive corpus,
coverage shards and compatibility-matrix runs were not performed.

## Record checkpoint gates

Actual fresh record commands in the evidence worktree, all exit zero:

```bash
"$AR190_PYTHON" scripts/docs_metadata.py --check
"$AR190_PYTHON" scripts/verify_docs.py
"$AR190_PYTHON" scripts/update_worklog.py --check
"$AR190_PYTHON" scripts/update_policy_availability.py --check
git diff --check
```

Actual stdout (the last two commands emitted none):

```text
checked 1241 Markdown documents
documentation validation passed for 1241 Markdown files
worklog index is current (2069 commits)
```

The pending record and explicit clarified criterion were present during these
checks. A separate actual `git diff --exit-code d1a9260c08aad8eb871fd6bd1ab81c3aad5e524f
-- agency_runtime scripts tests pyproject.toml` returned zero with no output;
the evidence-worktree SHA-256 output matched every detached-source digest above.
Neither this receipt nor a zero verifier-process exit alone is an acceptance
verdict. The second review remains pending until its own rows are recorded.
