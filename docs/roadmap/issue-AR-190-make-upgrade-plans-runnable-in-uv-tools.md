---
title: "AR-190: Make attended upgrade plans runnable in uv tools"
status: in_progress
category: roadmap
created: 2026-07-28
updated: 2026-09-08
tags: [cli, updates, uv, packaging, security]
related:
  - docs/roadmap/acceptance/issue-AR-190.md
  - docs/roadmap/acceptance/evidence/AR-190-installed-uv-plan-20260907.md
  - docs/roadmap/acceptance/evidence/AR-190-product-source-candidate-20260908.md
  - docs/roadmap/handoffs/issue-AR-190.md
  - docs/roadmap/issue-AR-188-add-immutable-update-discovery.md
  - docs/decisions/0107-resolve-updates-immutably-and-keep-application-attended.md
  - README.md
  - CHANGELOG.md
  - docs/TROUBLESHOOTING.md
  - agency_runtime/core/update_service.py
  - tests/test_update_service.py
  - tests/test_cli_upgrade.py
supersedes: []
superseded_by: null
type: issue
epic: release
issue_id: AR-190
priority: p0
tracker_url: null
depends_on: [AR-188]
blocks: [AR-119]
---

# AR-190: Make attended upgrade plans runnable in uv tools

## Problem

The first immutable upgrade planner always emitted
`<current-python> -m pip install ...`. Agency Runtime's supported uv-tool
installation intentionally omits pip, so the command copied from the CLI or
dashboard could not run. The target commit remained correctly immutable and no
mutation occurred, but the plan was not operationally usable in the environment
that owns the installed Agency launcher.

## Current state

The implementation is already committed at
`8c7d8df44aa35d4bb7ab7698abaf0f7b2a93e47b`. On September 7 the missing live
installed-uv proof was captured safely in a disposable local container. A
fresh clean detached build at `c64ce3ce54c6e51280292298b5e3600611cb72fc`
passed strict Twine and the independent portable verifier. Installing that
exact wheel through uv's legitimate default tool directories, then running
`agency upgrade plan --ref c64ce3ce54c6e51280292298b5e3600611cb72fc --timeout 5 --json`,
returned `installer=uv-tool`, exact-SHA commands without pip, and
`mutation_performed=false`. No displayed upgrade or Codex refresh was executed.
The [portable receipt](acceptance/evidence/AR-190-installed-uv-plan-20260907.md)
preserves the complete raw outputs, candidate/target distinction, hashes,
namespace failure provenance and isolation bounds. The first isolated
verification accepted criteria 1–4 but returned `absent` for criterion 5's
exact-final-candidate provenance. Status remains `in_progress`; the criterion
has not been bypassed or retried on unchanged evidence. The owner authorized
one changed-evidence response: a fresh exact d1a9260c build, same-SHA installed
uv plan and focused checks, plus explicit product-source/receipt-commit wording.
That new plan passed at 2026-09-08T00:00:19Z; its second-review builder is
frozen at receipt commit `eac2d6a2`, ledger `e4941a75`, and no first verdict is
reused under the new receipt candidate.

Planning now proves which installer the exact executing environment can use.
A stable regular pip entry point inside the exact prefix retains an
interpreter-bound isolated-mode command only after a bounded isolated
`pip --isolated --disable-pip-version-check --version` probe succeeds. A no-pip
environment must contain one stable bounded `uv-receipt.toml` identifying the
Agency Runtime requirement and `agency` entry point; Agency also resolves `uv`
outside repository-controlled roots and proves its no-config tool/bin targets
match that prefix and entry point. Target-changing uv/XDG environment overrides
fail closed. Only then does it print an exact-commit `uv tool install --force
--refresh --no-config` command. A malformed, unrelated, linked, oversized,
unreadable, or missing receipt—or unavailable, unsafe, or misdirected uv
executable—returns an unavailable plan with no command. POSIX uv entrypoint
symlinks are accepted only when their stable executable target is inside the
exact prefix; Windows continues to require the copied non-link launcher.

The planner still performs no install, dashboard mutation, Codex refresh, or
operator-presence action. The operator reviews and runs each command in a normal
owner-controlled terminal.

## Approach

Keep installer selection local and fail closed. Bind pip capability to its
stable entry point inside the exact prefix and invoke it with Python isolated
mode plus pip isolated configuration for both capability proof and the
displayed install. Read the uv receipt
through the shared bounded stable regular-file boundary, accept only the narrow
Agency requirement/entry-point shape, and reuse repository-aware executable
resolution for uv. Preserve the same full immutable Git commit in both pip and
uv plans and retain the separate attended Codex refresh step.
Render Windows commands as inert PowerShell invocations and require the
operator to run each displayed plan unchanged in the same environment.

## Dependencies

AR-188 owns immutable update discovery. ADR-0107 owns the separation between
read-only planning and owner-executed application. Tracker creation remains
pending explicit authorization for that outward-facing write.

## Acceptance

- [x] A pip-capable environment retains an exact-SHA interpreter-bound command.
- [x] A valid Agency uv-tool receipt plus safe uv resolution emits an exact-SHA
  uv-tool command containing no pip invocation.
- [x] A missing, malformed, unrelated, unsafe, or unresolvable uv environment
  fails closed with no command.
- [x] Upgrade planning and the dashboard remain copy-only and execute no package
  or host mutation.
- [ ] Focused update/CLI tests and lint pass for the exact final product-source
  candidate identified by canonical build provenance, and a live installed
  uv-tool plan passes from that candidate. Documentation checks pass at the
  corresponding evidence checkpoint; subsequent evidence-only commits do not
  redefine the runtime under test.

## Implementation evidence

### September 8 exact product-source clarification and new proof

The [second-review receipt](acceptance/evidence/AR-190-product-source-candidate-20260908.md)
preserves the original criterion 5 verbatim and the first absent reason. The
owner clarified exact final **product-source** identity rather than requiring
a documentation commit to contain its own future execution receipt. Criteria
1–4 and all installer/trust/nonexecution guards are unchanged. Documentation
still has to pass its actual corresponding record gate.

A new clean detached build at d1a9260c passed the canonical builder, strict
Twine and independent portable verification. Its exact wheel SHA-256 is
`98b87cf098bf0b35b4a266d8ee35288e1a366914b7e19f9c6a8579c2ce23e457`.
The real default-directory uv installation generated a plan to the same full
d1a9260c SHA at 00:00:19 UTC. Installed planner file digests match the recorded
source digests; all 669 compared prefix files, receipt and entrypoint remain
unchanged. Fresh source tests pass 67 cases in 0.83 seconds; Ruff checks pass.
The new receipt candidate requires a fresh all-five digest-bound review;
the first four verdicts cannot be transplanted across a candidate change.

### September 8 verifier admission failure

The second-review candidate is frozen at `eac2d6a2`, with clean checkpoint
`14f332ec`. At 00:08:38 UTC the default Claude launch refused the executable:
its exact package directory was `0775` while the npm bin directory was `0755`.
Claude Code itself reported version 2.1.263, but the production resolver
returned `executable_prepared=false` and the precise reason
`executable refused as untrusted: its parent namespace permits substitution`.

The all-five runner returned exit 2 and printed `verifier unavailable or
outside the vocabulary; nothing recorded` for every criterion. No second-review
verdict rows were produced, so this was failed admission, not five judgments.
The worker did not chmod owner paths or retry unchanged. The actor changing
the directory mode is unproved.

The owner requested the supported `--provider codex` alternative for the second
actual all-five review, after verifying its executable and authentication
status. The candidate and criterion evidence remain unchanged; no trust rule,
owner configuration or credential is modified to admit an untrusted binary.

### September 7 exact installed-candidate proof

The final proof used a fresh canonical wheel from clean detached source
`c64ce3ce54c6e51280292298b5e3600611cb72fc`, SHA-256
`cbf2ce558636cc160c6f0656d6fb0760e0d368ca5d1619fc988596e306c91c7d`,
and resolved the same exact full SHA through the official public GitHub API.
The installed package correctly reports `source_revision=null` for a wheel;
the independent artifact/source verification, not that self-report, binds its
candidate identity. The real uv-generated receipt and in-prefix entrypoint
symlink were unchanged after the plan, as were all 669 compared non-bytecode
prefix files. uv 0.11.8 installed only Agency Runtime 0.1.0 and PyYAML 6.0.3,
with no pip in the tool environment. No UV/XDG target override, HOME spoof,
owner-home mount, owner credential, image pull or privileged container was used.

The final plan exited zero at 23:31:01 UTC. An earlier successful plan used
the verified `08fab1c4` wheel to resolve `c64ce3ce`; its narrower provenance is
retained separately and not substituted for the final same-SHA candidate.
Fresh focused update/CLI tests pass **67 tests in 0.83 seconds**; targeted
Ruff lint and formatting pass. Normal merge-ledger reconciliation at
`d28ccc23` restored passing docs, metadata, policy-availability and worklog
checks. The builder is frozen at evidence commit `d1a9260c` with ledger
`ae1fe0fc`. Its documentation candidate preserves identical
runtime, producer, test and packaging-configuration Git objects; the receipt
distinguishes that record-only candidate from the exact live c64ce3ce artifact.

The ordinary owner installation is an AR-348 VCS package, not a uv tool;
its identity was not relabeled to manufacture this proof. Both disposable
containers were removed after capture, and owner Agency/uv wrapper hashes
remained unchanged. The earlier bubblewrap uid-map failure is retained as a
failed capability attempt, not retried or hidden.

### September 7 isolated verification

The default isolated verifier ran once from clean frozen checkpoint `45716bd5`
under `umask 077`, using Claude Code 2.1.263 and its read-only snapshot toolset:

```bash
env PYTHONPATH=. "$AR190_PYTHON" -u scripts/verify_acceptance.py --issue AR-190 --all
```

Actual stdout (exit zero means every check returned a verdict, not all passed):

```text
AR-190 criterion 1: satisfied (AR-190.1-20260907-60591b35)
AR-190 criterion 2: satisfied (AR-190.2-20260907-fb1c97e0)
AR-190 criterion 3: satisfied (AR-190.3-20260907-f77273e4)
AR-190 criterion 4: satisfied (AR-190.4-20260907-04be4364)
AR-190 criterion 5: absent (AR-190.5-20260907-42c2bd69)
```

The fifth verdict found that tests, lint, docs and the live plan were recorded
at c64ce3ce/d28ccc23, not frozen documentation candidate d1a9260c, and said the
product-source equivalence was unverifiable inside that snapshot. Its exact
reason and evidence digest remain in the acceptance record. No verdict was
handwritten, no passing criterion was rerun, and the fifth checkbox remains
open. Subsequent documentation validation passes for 1,240 Markdown files.

### Historical recovery evidence

The recovery candidate passes 65 focused update/CLI tests in 2.68 seconds on
Windows, with one intentional POSIX-only symlink test skipped. Targeted Ruff,
format, and diff checks pass. Repository metadata/policy checks and the full
documentation validator pass for 487 Markdown files. Independent security and
operational rereviews report no remaining blocker in this scope. A bounded
read-only probe using this candidate against the actual uv 0.10.9 installation
selects the expected uv-tool environment and emits valid PowerShell commands.
At that historical checkpoint, exact committed-install and Codex-refresh
evidence were still pending. The fresh proof above supplies the installed
uv-plan criterion; it neither executes nor claims the separately displayed
upgrade, refresh or host-activation steps. Those actions are not required to
demonstrate this issue's nonexecuting plan. See the
[active recovery capsule](handoffs/issue-AR-190.md) for the current boundary.
