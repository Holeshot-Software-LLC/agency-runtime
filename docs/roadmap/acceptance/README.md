---
title: "Acceptance verification records"
status: active
category: roadmap
created: 2026-09-01
updated: 2026-09-01
tags: [acceptance, evidence, verification, governance]
related:
  - docs/roadmap/issue-AR-361-builder-evidence-isolated-verification.md
  - docs/roadmap/AR-256-done-acceptance-reconciliation.md
  - docs/roadmap/pre-verification-history.txt
  - scripts/verify_docs.py
  - scripts/verify_acceptance.py
  - scripts/roadmap_history.py
supersedes: []
superseded_by: null
---

# Acceptance verification records

A checked Acceptance box is a claim by whoever did the work. Since AR-361 a
`done` flip also needs one record per issue at
`docs/roadmap/acceptance/issue-AR-NN.md` that separates two roles:

1. **Builder evidence.** The builder cites concrete evidence for every
   column-0 criterion of the issue's `## Acceptance` section and never
   judges. Missing evidence is stated plainly with kind `absent`.
2. **Isolated verification.** A verifier with a deliberately minimal
   read-only toolset judges exactly one criterion per run, sees only that
   criterion and its own builder rows, and returns a verdict through a JSON
   schema. The runner records it bound to a digest of what was judged.

`scripts/verify_docs.py` re-validates every record on every run, so the
record is the durable authority that CI checks, not a chat transcript.

## Lifecycle

- A record starts as a **pending draft**: `candidate_commit: pending`. Its
  builder rows are validated against the working tree, so the builder can
  write them in the same commit as the implementation. Verification rows
  are not allowed while pending; a verdict binds to a commit.
- Once the implementation exists in an ancestor commit, the builder
  **freezes** the record by setting `candidate_commit` to that full SHA.
  Sources are then resolved with `git show <candidate>:<path>` and stay
  valid forever, whatever later commits do to those files.
- `scripts/verify_acceptance.py` runs the verifier and writes one
  `## Verification` row per criterion. A frozen record whose every criterion
  is `satisfied` unlocks the done flip; `absent`, `contradicted`, or a
  missing row blocks it.

Because a commit cannot contain its own SHA, the frozen record and the done
flip always land at least one commit after the implementation they cite,
exactly like the worklog ledger row records the preceding commit. Merges of
this repository preserve branch commits, so a candidate may be any commit
that is an ancestor of `HEAD` when the gate runs.

## Format

Front matter: `type: acceptance-verification`, `status: active`,
`issue_id`, `candidate_commit` (`pending` or a 40-hex ancestor of `HEAD`),
`evidence_cutoff` (no observation may be later), `tracker_url` equal to the
issue's, and `related` containing the canonical issue path.

`## Builder evidence` — `| Criterion | Kind | Artifact | Observed | Source |`

- `Criterion`: the 1-based index of the column-0 task marker in the issue's
  `## Acceptance`. Nested or indented markers are not criteria and are
  rejected for done issues.
- `Kind`: `command-output`, `file`, `receipt`, `tracker`, `test`, `absent`.
- `Source` per kind: `test` cites `tests/...:line[-line]` or `#heading`;
  `file` and `command-output` cite `path:line[-line]`, `path#heading`, or
  (`file` only) a full commit SHA that is an ancestor of `HEAD`; `tracker`
  cites this repository's issue or pull URL; `receipt` cites a bounded run
  or receipt id; `absent` cites `none` and names Artifact `none`, and must
  be the only row for its criterion. Several rows per criterion are fine.

`## Verification` — `| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |`

- Exactly one row per criterion. `Verdict` is `satisfied`, `contradicted`,
  or `absent`; absent builder evidence forces an `absent` verdict.
- `Verifier run` is unique across the record: one run judges one criterion.
- `Evidence digest` is the SHA-256 of the canonical JSON of the candidate
  commit, the criterion index, its whitespace-normalized text, and the
  builder rows (`kind`, `artifact`, `observed`, `source`) for that
  criterion. The validator recomputes it, so editing a builder row or
  rewording a criterion after verification invalidates the verdict.

Tables inside fences, HTML comments, or indented code are invisible; a
spoofed table reads as a missing table.

## Runner

```bash
python3 scripts/verify_acceptance.py --issue AR-361 --criterion 1
python3 scripts/verify_acceptance.py --issue AR-361 --all --provider claude
python3 scripts/verify_acceptance.py --issue AR-361 --criterion 2 --dry-run
```

The runner refuses pending records and invalid builder rows, and for each
criterion builds a prompt holding only that criterion's text, its builder
rows, and bounded excerpts of the cited sources at the candidate. On
`claude` it exports the candidate tree into a private temporary directory
and invokes the CLI through `invoke_cli_structured` in safe mode with
`--tools=Read,Grep,Glob --restricted --add-dir <snapshot>`, no session, no
MCP, `dontAsk` permissions, and a bounded turn cap. On `codex` the existing
read-only, shell-free sandbox applies, so the verifier judges the inlined
excerpts only. An unavailable verifier, or an answer outside the closed
vocabulary, records nothing and exits `2`; nothing ever passes silently.

## Grandfathered history

`docs/roadmap/pre-verification-history.txt` lists every issue that was
already `done` or `wont_do` when the gate landed. `scripts/roadmap_history.py`
pins that set by digest and rejects any ID newer than the newest
grandfathered item, stale entries whose issue was reopened, and orphan
entries, so the list can only shrink and every later done flip needs a
record. A record written for a grandfathered issue is authoritative anyway.

## Limits

The verifier judges what it can see; a cited artifact that lives outside the
repository (a receipt id, a tracker) is checked for form, not content. The
gate proves that an isolated run recorded a verdict on exact evidence; it
cannot prove the verifier's judgement was right, which is why verdicts,
reasons, and run ids stay in Git for review.
