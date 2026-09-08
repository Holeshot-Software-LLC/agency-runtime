---
title: "AR-190 exact installed uv-tool plan evidence"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [evidence, release, updates, uv, linux, isolation]
related:
  - docs/roadmap/issue-AR-190-make-upgrade-plans-runnable-in-uv-tools.md
  - docs/roadmap/acceptance/issue-AR-190.md
  - docs/roadmap/handoffs/issue-AR-190.md
  - docs/decisions/0107-resolve-updates-immutably-and-keep-application-attended.md
  - docs/roadmap/acceptance/evidence/AR-183-AR-184-private-linux-producer-20260907.md
  - agency_runtime/core/update_service.py
  - agency_runtime/cli/upgrade_commands.py
  - tests/test_update_service.py
  - tests/test_cli_upgrade.py
supersedes: []
superseded_by: null
---

# Exact installed uv-tool plan evidence

## Outcome and scope

At 2026-09-07T23:31:01Z, a real installed uv-tool Agency CLI successfully
generated a nonexecuting plan to exact source commit
`c64ce3ce54c6e51280292298b5e3600611cb72fc`. The installed candidate was
independently built and verified from that SAME clean detached commit.
The plan selected `uv-tool`, emitted an exact-SHA command without pip and a
separate isolated Codex refresh command, and reported
`mutation_performed=false`. Neither displayed command was executed.

This is a legitimate default-directory uv tool installation in a disposable
local container, not a hand-written receipt, patched helper or owner AR-348
venv relabeled as uv-owned. The owner installation and profiles were untouched.
No runtime code change was necessary: the implementation already exists in
`8c7d8df44aa35d4bb7ab7698abaf0f7b2a93e47b`,
“fix(updates): bind attended installers to owning environment”.

Complete actual command stdout/stderr and before/after observations are retained
in [the final raw JSON](AR-190-uv-plan-final-20260907.json), SHA-256
`de329f48295e0f3af87bee1fa6df989f767121263b31a2ecf7bb03590697b74b`.
This receipt supplies builder evidence only, without a verdict or done flip.

## Canonical artifact identity

A new detached worktree at
`c64ce3ce54c6e51280292298b5e3600611cb72fc` was clean before and after
production: `git status --porcelain` empty; `git symbolic-ref -q HEAD`
exited 1 with empty output; `git rev-parse HEAD` returned the exact SHA.
The initially absent destination was under a new private directory outside
the checkout. The producer ran under `umask 077`.

Portable parameter names below denote that clean source, trusted interpreter
and private destination; no owner home variable is changed:

```bash
cd "$AR190_SOURCE_TREE"
umask 077
env PYTHONPATH=. "$AR190_PYTHON" -m scripts.build_distributions "$AR190_DIST_DIR" --create-private-parent --expected-commit c64ce3ce54c6e51280292298b5e3600611cb72fc
"$AR190_PYTHON" -m twine check --strict "$AR190_DIST_DIR/agency_runtime-0.1.0-py3-none-any.whl" "$AR190_DIST_DIR/agency_runtime-0.1.0.tar.gz"
env PYTHONPATH=. "$AR190_PYTHON" -m scripts.verify_distribution "$AR190_DIST_DIR" --expected-commit c64ce3ce54c6e51280292298b5e3600611cb72fc --artifact-set portable
```

All three commands exited zero. Actual builder/verifier stdout:

```text
Canonical distribution build passed: agency_runtime-0.1.0-py3-none-any.whl, agency_runtime-0.1.0.tar.gz
Distribution verification passed (artifact contents match release policy).
```

Strict Twine reported `PASSED` for each exact wheel and sdist. Producer:
Linux 7.0.0-29-generic x86_64/glibc 2.39, Python 3.12.3, build 1.5.0,
setuptools 83.0.0, wheel 0.47.0, Twine 6.2.0. Output directory mode `0700`;
artifact filesystem modes `0644`.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `agency_runtime-0.1.0-py3-none-any.whl` | 10,031,632 | `cbf2ce558636cc160c6f0656d6fb0760e0d368ca5d1619fc988596e306c91c7d` |
| `agency_runtime-0.1.0.tar.gz` | 30,609,743 | `d07c7e827074617ff2cd01306922537291b5004b2e96ead6944c08c1960a1392` |

Read-only archive inspection at 23:30:30 UTC counted 619 ordinary wheel members
at `0644`, one RECORD at `0664`, 2,306 sdist files at `0644` and 40 sdist
directories at `0755`. The independent verifier, not the mode census alone,
binds the payload to the exact committed source.

## Isolation and execution bounds

Read-only discovery found the existing local Docker Unix socket and Engine
29.7.2. Every Docker command explicitly selected
`unix:///var/run/docker.sock` with remote context/host selectors removed.
No remote daemon, image pull, service configuration or daemon administration
was used. The exact already-local image was:

`sha256:c8e7a2654bcd382d56c07bdb04a3b3ae35de09fb0e69cf9bb825d72e14baacf7`
(`agency-ar297-codex:e0b0b25c`).

Network-disabled, read-only inventory overrode its entrypoint and found default
UID 0/home `/root`, Python 3.11.2, no uv, no pip/uv cache, no UV/XDG overrides
and no credential-like environment names. Only environment names and selected
version metadata were inspected; potential credential values were not printed.

The isolated proof used `--rm --pull never --cap-drop ALL`,
`--security-opt no-new-privileges`, 128 PIDs, 1 GiB memory, one CPU and a
five-second stop timeout. The host command had a 120-second outer bound.
There were no published ports, host networking, privileged mode, owner-home
mount or Docker-socket mount. Three exact files were mounted read-only: the
probe script, verified uv executable and canonical wheel. The normal writable
container layer, not owner storage, held the disposable installation.

The uv input SHA-256 was
`646adf5cf12ba17d1a41fa77c8dd6496f73651dcfeeed6b5f4ec019b36bc7153`.
The probe checked both input hashes, copied uv into the container's
`/usr/local/bin/uv`, and used uv's ordinary defaults under `umask 077`.
No HOME, UV or XDG variable was fabricated. Public PyPI dependency access and
the fixed official GitHub lookup were specifically authorized; no owner
credential was supplied. The uv install subprocess was bounded to 60 seconds,
identity probes to 10 seconds and the plan subprocess to 25 seconds with its
own `--timeout 5`; captured subprocess output was capped at 256 KiB.

The final probe script SHA-256 was
`475b04ea7658635bc369b4f2d481f5e37b58f9db61e8cd5db4559f192081370a`.
Its entire final container run spanned
23:30:59.401191–23:31:01.391506 UTC. This is observed elapsed container time,
not a staffing-performance measurement.

## Legitimate uv installation

Actual setup command inside the disposable container:

```bash
/usr/local/bin/uv tool install --no-config /ar190-input/agency_runtime-0.1.0-py3-none-any.whl
```

Stderr, exit 0, with only the mounted local-file URL replaced by a portable
label. The unmodified stderr is retained in the linked raw JSON:

```text
Resolved 2 packages in 170ms
Prepared 2 packages in 92ms
Installed 2 packages in 8ms
 + agency-runtime==0.1.0 (from <mounted-wheel-file-url>)
 + pyyaml==6.0.3
Installed 1 executable: agency
warning: `/root/.local/bin` is not on your PATH. To use installed tools, add the directory to your PATH.
```

The resulting environment contains only `agency-runtime==0.1.0` and
`PyYAML==6.0.3`; pip is absent. The tool uses Python 3.11.2 with prefix
`/root/.local/share/uv/tools/agency-runtime`. Home, tool root, exact prefix and
bin directory are all mode `0700`. The default entrypoint is a real uv-created
symlink from `/root/.local/bin/agency` into that exact prefix. The PATH warning
was handled by invoking that absolute entrypoint, not by a target override.

Actual uv-generated receipt, unchanged after planning:

```toml
[tool]
requirements = [{ name = "agency-runtime", path = "/ar190-input/agency_runtime-0.1.0-py3-none-any.whl" }]
entrypoints = [
    { name = "agency", install-path = "/root/.local/bin/agency", from = "agency-runtime" },
]
```

Receipt SHA-256:
`e78058bdd433bac622c76854183fe38c0ad99cb3070f91ae2e5d00e5036ca251`.

Installed identity honestly reports `install_kind=package`,
`build_identity=0.1.0`, `official_repository=false` and
`source_revision=null`: a local wheel has no VCS direct-url identity.
The full source binding comes from the separately verified exact wheel hash,
not an invented installed self-report.

## Final installed plan

Actual command, exit 0, empty stderr:

```bash
/root/.local/bin/agency upgrade plan --ref c64ce3ce54c6e51280292298b5e3600611cb72fc --timeout 5 --json
```

Readable stdout projection below replaces the VCS repository portion of the
requirement with `<official-repository.git>`; the exact full SHA is preserved.
The unmodified source URL, argv, display command and stdout are retained in
the linked raw JSON. This substitution keeps the Markdown repository-link
validator from treating a pip VCS requirement as a different repository name.

```json
{
  "cache_hit": false,
  "checked": true,
  "checked_at": "2026-09-07T23:31:01.053664+00:00",
  "checking": false,
  "command": "agency upgrade --ref c64ce3ce54c6e51280292298b5e3600611cb72fc",
  "error": null,
  "installed": {
    "build_identity": "0.1.0",
    "install_kind": "package",
    "official_repository": false,
    "package_version": "0.1.0",
    "source_branch": null,
    "source_dirty": null,
    "source_revision": null
  },
  "plan": {
    "commands": [
      {
        "argv": [
          "/usr/local/bin/uv",
          "tool",
          "install",
          "--force",
          "--refresh",
          "--no-config",
            "agency-runtime @ git+<official-repository.git>@c64ce3ce54c6e51280292298b5e3600611cb72fc"
        ],
          "display": "/usr/local/bin/uv tool install --force --refresh --no-config 'agency-runtime @ git+<official-repository.git>@c64ce3ce54c6e51280292298b5e3600611cb72fc'"
      },
      {
        "argv": [
          "/root/.local/share/uv/tools/agency-runtime/bin/python",
          "-I",
          "-m",
          "agency_runtime.cli",
          "install",
          "--agent",
          "codex",
          "--no-dashboard"
        ],
        "display": "/root/.local/share/uv/tools/agency-runtime/bin/python -I -m agency_runtime.cli install --agent codex --no-dashboard"
      }
    ],
    "installer": "uv-tool",
    "mode": "attended-external",
    "mutation_performed": false,
    "reason": "Agency resolved an immutable source target but did not execute package or host mutations; review and run each command from an owner-controlled terminal",
    "requires_owner_execution": true,
    "requires_post_install_activation_check": true
  },
  "schema_version": "agency.update.v1",
  "selector": {
    "key": "ref:c64ce3ce54c6e51280292298b5e3600611cb72fc",
    "kind": "ref",
    "ref": "c64ce3ce54c6e51280292298b5e3600611cb72fc",
    "value": "c64ce3ce54c6e51280292298b5e3600611cb72fc"
  },
  "stale": false,
  "status": "unknown",
  "target": {
    "commit_sha": "c64ce3ce54c6e51280292298b5e3600611cb72fc",
    "kind": "ref",
    "label": "c64ce3ce54c6e51280292298b5e3600611cb72fc",
    "published_at": null,
    "ref": "c64ce3ce54c6e51280292298b5e3600611cb72fc",
    "url": "https://github.com/Holeshot-Software-LLC/agency-runtime/commit/c64ce3ce54c6e51280292298b5e3600611cb72fc",
    "version": null
  },
  "update_available": null
}
```

`checked=true`, `cache_hit=false` and the exact returned target SHA record
a fresh official lookup. `status=unknown` and `update_available=null` are
not failures: the ordinary wheel identity lacks a self-reported revision and
the planner does not invent a “newer” relationship. The install planner still
proved the real uv ownership and produced its exact-SHA command.

## No execution and before-after evidence

The setup uv install above happened before the measured planning interval.
The subsequent `agency upgrade plan` did not run either displayed command.
Its 669 non-bytecode prefix file hashes match before/after, as do its uv receipt
and resolved entrypoint. Entry-point SHA-256 before and after:

`0713dfe44c67da775470cd134fcc14f4c546f84798302b3cba39394418a89653`.

The byte comparison excludes `__pycache__`, and
`PYTHONDONTWRITEBYTECODE=1` was supplied to subprocesses; it is not presented
as an inode/mtime comparison or a blanket claim about all container cache files.
Update-discovery caching inside the disposable home is separate from package
or host mutation. No refresh, host install, service operation or model call ran.

The final named container was absent on readback after `--rm`. Owner Agency
wrapper SHA-256 was unchanged throughout:
`c31ca4d105085d95369c3704e82d9c6fd2ea12a9f2c1f021157da8984dc53974`.
The owner uv input and both mounted canonical wheel inputs also retained their
pre-run hashes. No owner CLI replacement or host uv-tool installation occurred.

## Earlier attempts retained

The ordinary owner Agency CLI is an AR-348 VCS installation, not a uv-owned
tool: its source revision is `0309f251c6cf1c6c22b3a4458302c8b2cad78734`,
and it has no `uv-receipt.toml`. That environment was not relabeled to satisfy
the uv criterion.

At 22:47 UTC an isolated bubblewrap preflight exited 1 with empty stdout and:

```text
bwrap: setting up uid map: Permission denied
```

No uv installation, upgrade plan, network call or owner profile write occurred
in that failed attempt. It was not retried unchanged or bypassed; the later
local Docker route was separately authorized.

At 23:28:13 UTC the first successful container plan installed the independently
verified `08fab1c4fb9b7f8ed167f0aa4366182960f6eada` wheel
(SHA-256 `228ab9c0eac70764ce515fbd6ce2829437a7f78d081f702d790175c1033ac650`)
and resolved target c64ce3ce. Its [raw receipt](AR-190-uv-plan-initial-20260907.json),
SHA-256 `6c9e0ea96bc45d9c2af761da80283f88de04734efb17d887e83c1c3b01f743f2`,
is distinct. Relevant update-service/CLI source was unchanged between those
commits, but that first pass did not establish a whole-candidate same-SHA
installation. The fresh detached c64ce3ce build and final run above do.

## Focused checks

Actual fresh source-tree command at c64ce3ce:

```bash
env PYTHONPATH=. "$AR190_PYTHON" -m pytest tests/test_update_service.py tests/test_cli_upgrade.py -q -W error --tb=short
```

Actual stdout, exit 0:

```text
...................................................................      [100%]
67 passed in 0.83s
```

This includes exact-SHA pip behavior, real-receipt shape and uv target binding,
unsafe/missing/ambiguous receipt refusal, POSIX entrypoint symlink handling,
no-execution CLI behavior, and synthetic PowerShell-safe rendering. It is not
a native Windows live installation. Targeted Ruff commands over
`update_service.py`, `upgrade_commands.py` and these two test modules returned:

```text
All checks passed!
4 files already formatted
```

## Record checks

After fast-forwarding the evidence worktree to the existing shared ledger
commit `d28ccc232dcc00af0162a2409930dd272bf97b5f`, actual checks exited zero:

```text
checked 1239 Markdown documents
documentation validation passed for 1239 Markdown files
worklog index is current (2066 commits)
```

Commands were `python scripts/docs_metadata.py --check`,
`python scripts/verify_docs.py` and `python scripts/update_worklog.py --check`.
`python scripts/update_policy_availability.py --check` and `git diff --check`
also exited zero with no output. Targeted Ruff lint returned
`All checks passed!`; formatting returned `4 files already formatted`.

For provenance, before that normal ledger reconciliation the documentation
check failed only these inherited missing/inaccurate merge-row errors:


```text
ERROR: docs/worklog/README.md: indexed commits do not match history (missing=['c64ce3ce'], extra=[])
ERROR: docs/worklog/README.md: inaccurate row for c64ce3ce
documentation validation failed with 2 error(s)
```

The existing ledger commit resolved them without modifying runtime or tests.
No acceptance verdict is recorded here.

## Record candidate source equivalence

The final live installed artifact and target are both exactly
`c64ce3ce54c6e51280292298b5e3600611cb72fc`. The later acceptance candidate
adds only documentation evidence and ledger records; it is not a claim that
the later commit's entire documentation-bearing wheel was rebuilt. At the
evidence checkpoint the following command exited zero with no output:

```bash
git diff --exit-code c64ce3ce54c6e51280292298b5e3600611cb72fc -- agency_runtime scripts tests pyproject.toml setup.cfg setup.py
```

The unchanged Git tree/blob identities are:

| Source | Git object |
|---|---|
| `agency_runtime` | `77eb2f3c7f3959180203e97f0da2f3cd9d6fb451` |
| `scripts` | `fb26cb64d27210895e95966abeef75044e8f8ac8` |
| `tests` | `9d9bdfab8702f5e08eed1de2a606d7b1a9bf922d` |
| `pyproject.toml` | `b84ace23045070575c57f6ba1917cc1324fb68af` |

Thus the executed planner, producer, focused tests and packaging configuration
are source-identical at the record-only candidate; newly added prose is not
misrepresented as live-executed product code.

## Limits

No displayed upgrade or Codex refresh was executed, and no installed host
activation/header claim follows from this plan. The ephemeral plan commands
were valid in their generating container; that container is deliberately gone,
so the displayed paths are evidence rather than instructions for the owner
to paste into a different environment. Native Windows, exhaustive corpus,
coverage shards, compatibility matrix, signing and package publication did not
run. No new product authority or implementation change is part of this package.
